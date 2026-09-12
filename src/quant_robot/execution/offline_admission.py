"""Transaction-local risk checks using supplied synthetic, point-in-time inputs."""
from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from .offline_intent_contract import SHANGHAI, day, instant
from .offline_order_state import ACTIVE, VALUATION_UNAVAILABLE, AdmissionRejected, ZERO, dividend_receivable, money_context, reservations
from .offline_portfolio_risk import portfolio_totals


def deny(message, *, stop=False):
    raise AdmissionRejected(message, risk_stop=stop)


def _check_context(state, packet, now, *, opening=False):
    policy = state.get("admission_policy")
    if policy is None:
        deny("guarded admission policy is required")
    now = instant(now)
    local = now.astimezone(SHANGHAI)
    session_date = packet["session_date"]
    if session_date != local.date().isoformat() or session_date not in policy["session_dates"]:
        deny("unknown or mismatched session date")
    if not any(time.fromisoformat(start) <= local.time().replace(tzinfo=None) < time.fromisoformat(end)
            for start, end in policy["trading_windows"]):
        deny("outside configured trading session")
    age = (now - instant(packet["as_of"])).total_seconds()
    if age < 0 or age > policy["max_context_age_seconds"]:
        deny("stale or future risk context")
    if packet["journal_sequence"] != state["sequence"] or packet["journal_hash"] != state["journal_hash"]:
        deny("risk context has a stale journal anchor")
    valuation = state.get("portfolio_valuation", {}).get("last_valid")
    if valuation and not opening:
        previous = valuation["context"]
        if (now < instant(valuation["decision_at"]) or instant(packet["as_of"]) < instant(previous["as_of"])
                or any(key in previous["quotes"] and instant(row["timestamp"]) < instant(previous["quotes"][key]["timestamp"])
                    for key, row in packet["quotes"].items())):
            deny("risk context predates the latest valuation")
    faults = state["faults"] - {VALUATION_UNAVAILABLE} if opening else state["faults"]
    if faults or state["kill_switch"]:
        deny("journal paused; reconcile or release operator stop")
    return policy, now


@money_context
def _marks(policy, packet, now, required, *, state=None):
    if state is not None:
        from .offline_dividends import check_dividend_basis
        check_dividend_basis(state, packet, now, required)
    if not set(required).issubset(packet["quotes"]):
        deny("missing quote for order or portfolio risk")
    marks = {}
    for code, row in packet["quotes"].items():
        if code not in policy["allowed_symbols"]:
            deny("quote outside configured universe")
        if code in required and row["trade_status"] != "TRADING":
            deny("instrument is not trading; no supported valuation quote for non-trading instrument")
        age = (now - instant(row["timestamp"])).total_seconds()
        if age < 0 or age > policy["max_quote_age_seconds"] or instant(row["timestamp"]) > instant(packet["as_of"]):
            deny("stale or future quote")
        bid, ask = Decimal(row["bid"]), Decimal(row["ask"])
        if bid > ask or (ask - bid) / ((ask + bid) / 2) * 10000 > Decimal(policy["max_spread_bps"]):
            deny("crossed or excessive quote spread")
        marks[code] = (ask + bid) / 2
    return marks


@money_context
def begin_session_event(state, packet, now):
    policy, now = _check_context(state, packet, now, opening=True)
    current = state.get("risk_session")
    if current and packet["session_date"] <= current["session_date"]:
        deny("session baseline cannot be reset or rolled backward")
    if any(row["status"] in ACTIVE for row in state["orders"].values()):
        deny("unfinished DAY orders must be reconciled before session roll")
    if set(packet["instruments"]) != set(policy["allowed_symbols"]):
        deny("incomplete instrument metadata")
    session_date = day(packet["session_date"])
    for row in packet["instruments"].values():
        if not day(row["valid_from"]) <= session_date <= day(row["valid_until"]):
            deny("instrument metadata not effective for session")
        age = (session_date - day(row["adv_as_of"])).days
        if age <= 0 or age > policy["max_adv_age_days"]:
            deny("liquidity evidence must use recent completed sessions")
    if any(qty > state["positions"].get(code, 0) for code, qty in packet["sellable_positions"].items()):
        deny("opening sellable position exceeds holdings")
    held = {key for key, qty in state["positions"].items() if qty}
    if not held.issubset(policy["allowed_symbols"]):
        deny("holding outside configured universe")
    marks = _marks(policy, packet, now, held, state=state)
    equity = state["cash"] + dividend_receivable(state) + sum((qty * marks[key] for key, qty in state["positions"].items() if qty), ZERO)
    if equity <= 0:
        deny("nonpositive opening equity")
    return {"kind": "RISK_SESSION", "data": {**packet, "decision_at": now.isoformat(),
        "opening_equity": str(equity), "opening_positions": dict(state["positions"]), "risk_stop": False,
        "carryover_fill_shares": {}}}


def _check_intent(state, order, packet, policy, now):
    if (order["client_intent_id"] in state["orders"] or order["client_intent_id"] in state["attempted_intent_ids"]
            or order["idempotency_key"] in state["attempted_idempotency_keys"]
            or any(o["idempotency_key"] == order["idempotency_key"] for o in state["orders"].values())):
        deny("duplicate intent identity or idempotency key")
    session = state.get("risk_session")
    if session is None or session["session_date"] != packet["session_date"]:
        deny("risk session must be initialized")
    if session["risk_stop"]:
        deny("session risk stop remains active")
    if order["strategy_id"] != policy["strategy_id"] or order["strategy_version"] != policy["strategy_version"]:
        deny("strategy identity or version mismatch")
    if order["side"] not in {"BUY", "SELL"} or order["order_type"] != "LIMIT" or order["time_in_force"] != "DAY":
        deny("only BUY/SELL LIMIT DAY intents are supported")
    if order["symbol"] not in policy["allowed_symbols"]:
        deny("instrument outside configured universe")
    signal, expiry = instant(order["signal_timestamp"]), instant(order["expires_at"])
    age = (now - signal).total_seconds()
    end = datetime.combine(day(packet["session_date"]), time.fromisoformat(policy["trading_windows"][-1][1]), SHANGHAI)
    if (age < 0 or age > policy["max_signal_age_seconds"] or signal.astimezone(SHANGHAI).date() != day(packet["session_date"])
            or expiry <= now or expiry > end):
        deny("future, stale or expired signal/intent")


@money_context
def _check_instrument(state, order, packet, policy):
    code, qty = order["symbol"], order["quantity"]
    metadata = state["risk_session"]["instruments"][code]
    price, quote = Decimal(order["limit_price"]), packet["quotes"][code]
    if quote["trade_status"] != "TRADING":
        deny("instrument is not trading")
    if price % Decimal(metadata["price_tick"]):
        deny("limit price violates instrument tick")
    _, reserved_shares = reservations(state)
    sellable = state["sellable_positions"].get(code, 0) - reserved_shares.get(code, 0)
    if order["side"] == "SELL" and qty > sellable:
        deny("insufficient unreserved sellable position")
    if qty % metadata["lot_size"]:
        if not (order["side"] == "SELL" and metadata["odd_lot_sell_allowed"] and qty == sellable):
            deny("quantity violates lot or full odd-lot sale rule")
    slippage = Decimal(order["max_slippage_bps"])
    if slippage > Decimal(policy["max_slippage_bps"]):
        deny("intent slippage exceeds policy")
    if ((order["side"] == "BUY" and price > Decimal(quote["ask"]) * (1 + slippage / 10000))
            or (order["side"] == "SELL" and price < Decimal(quote["bid"]) * (1 - slippage / 10000))):
        deny("limit price exceeds slippage bound")


def _active_orders(state, session_date):
    return [row for row in state["orders"].values()
        if row.get("admission", {}).get("session_date") == session_date]


@money_context
def _risk_totals(state, order, marks, policy):
    current = _active_orders(state, state["risk_session"]["session_date"])
    code = order["symbol"]
    committed = sum(row["filled_quantity"] + (row["quantity"] - row["filled_quantity"] if row["status"] in ACTIVE else 0)
        for row in current if row["symbol"] == code and row["side"] == order["side"])
    committed += state["risk_session"]["carryover_fill_shares"].get(code, {}).get(order["side"], 0)
    adv = Decimal(state["risk_session"]["instruments"][code]["adv_shares"])
    if committed + order["quantity"] > adv * Decimal(policy["max_adv_participation"]):
        deny("daily one-way ADV participation exceeded")
    candidate = {**order, "filled_quantity": 0, "filled_notional": ZERO, "commission": ZERO, "status": "PENDING",
        "limit_price": Decimal(order["limit_price"])}
    totals = portfolio_totals(state, marks, [candidate])
    gross, exposure = totals["gross"], totals["exposure"]
    if order["side"] == "BUY":
        if gross > Decimal(policy["capital_limit_cny"]):
            deny("capital exposure limit exceeded")
        if any(value > Decimal(policy["max_position_cny"]) for value in exposure.values()):
            deny("single position limit exceeded")
    equity, projected_loss = totals["equity"], totals["projected_loss"]
    if projected_loss >= Decimal(policy["max_daily_loss_cny"]):
        deny("daily loss limit including pending costs reached", stop=True)
    return {"current_equity": str(equity), "projected_daily_loss": str(projected_loss),
        "gross_committed_exposure": str(gross), "one_way_committed_shares": committed + order["quantity"]}


@money_context
def admission_event(state, order, packet, now):
    policy, now = _check_context(state, packet, now)
    _check_intent(state, order, packet, policy, now)
    required = {key for key, qty in state["positions"].items() if qty} | {order["symbol"]}
    required |= {row["symbol"] for row in state["orders"].values() if row["status"] in ACTIVE}
    marks = _marks(policy, packet, now, required, state=state)
    _check_instrument(state, order, packet, policy)
    totals = _risk_totals(state, order, marks, policy)
    return {"kind": "REGISTER", "data": {"order_id": order["client_intent_id"], "idempotency_key": order["idempotency_key"],
        "symbol": order["symbol"], "side": order["side"], "quantity": order["quantity"], "limit_price": order["limit_price"],
        "admission": {"intent": order, "context": packet, "session_date": packet["session_date"],
            "decision_at": now.isoformat(), "policy_fingerprint": state["admission_policy_fingerprint"], "risk": totals}}}
