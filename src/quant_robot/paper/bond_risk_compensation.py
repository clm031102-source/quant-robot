"""Artificial-only implementation of the separate long-term bond contract.

No historical input loader, data admission, source access or qualification. The
old annual account loop and its float serializer are deliberately not used.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext

from quant_robot.paper.annual_allocation import _capacity, _decimal, _fee, _price
from quant_robot.paper.daily_recovery import DailyRecovery, RECOVERY_40_DAILY_RETRY

ARTIFICIAL = "synthetic_artificial_2001"
ASSET = "SYNTHETIC_CN_BOND_ETF"
COST_CASES = tuple((minimum, slip) for minimum in (0, 5, 10) for slip in (0, 10, 30))
CONTEXT = Context(prec=40, rounding=ROUND_HALF_UP)
INITIAL = Decimal("10000")
FLAGS = ("suspended", "limit_up", "limit_down")
SPLIT_MODE = "exact_integer_split10_record_close_v1"


@dataclass(frozen=True)
class EvidenceContext:
    asset_id: str
    evidence_class: str
    first_year: int
    last_year: int
    max_sessions: int


ARTIFICIAL_CONTEXT = EvidenceContext(ASSET, ARTIFICIAL, 2001, 2001, 365)
HISTORICAL_CONTEXT = EvidenceContext('CN_ETF_XSHG_511220', 'retained_known_historical_sources', 2020, 2024, 1087)


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _money(value):
    _require(isinstance(value, (str, int, Decimal)) and not isinstance(value, bool), "Exact decimal/string input required")
    return _decimal(value)


def _day(value, context=ARTIFICIAL_CONTEXT):
    _require(isinstance(value, str) and date.fromisoformat(value).isoformat() == value
             and context.first_year <= date.fromisoformat(value).year <= context.last_year,
             "Date outside explicit evidence context; public artificial entry is2001only")
    return value


def _exact(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {key: _exact(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_exact(item) for item in value]
    _require(not isinstance(value, float), "No float output in exact synthetic ledger")
    return value


def _prepare(fixture, split_mode=None, *, context=ARTIFICIAL_CONTEXT):
    _require(context in (ARTIFICIAL_CONTEXT, HISTORICAL_CONTEXT), "Exact explicit evidence context required")
    _require(split_mode in (None, SPLIT_MODE), "Unknown split mode")
    _require(split_mode is not None or "split_events" not in fixture,
             "Split events require explicit opt-in; never silently ignored")
    _require(isinstance(fixture, dict) and fixture.get("evidence_class") == context.evidence_class
             and fixture.get("asset_id") == context.asset_id
             and fixture.get("invented_values") is (context == ARTIFICIAL_CONTEXT),
             "Explicit source identity must match entry context")
    _require(fixture.get("price_unit") == "CNY_per_share" and fixture.get("volume_unit") == "shares"
             and fixture.get("price_basis") == "raw_unadjusted",
             "Explicit unadjusted price/share units required")
    _require(fixture.get("corporate_actions_complete") is True and isinstance(fixture.get("actions"), list),
             "Explicit complete artificial action list required; missing is not zero")
    sessions = tuple(_day(day, context) for day in fixture["sessions"])
    _require(22 <= len(sessions) <= context.max_sessions and list(sessions) == sorted(set(sessions)), "Unique bounded complete context calendar required")
    _require(isinstance(fixture["bars"], list) and len(fixture["bars"]) == len(sessions), "Every synthetic session needs a bar")
    bars = {}
    for source in fixture["bars"]:
        day = _day(source["date"], context)
        _require(source.get("asset_id") == context.asset_id and day in sessions and day not in bars, "Unexpected/duplicate context asset-date")
        values = {key: _money(source[key]) for key in ("open", "high", "low", "close", "volume")}
        _require(all(values[key] > 0 for key in ("open", "high", "low", "close")) and values["volume"] >= 0, "Invalid OHLC/volume")
        _require(values["low"] <= min(values["open"], values["close"]) <= max(values["open"], values["close"]) <= values["high"], "Invalid OHLC order")
        _require(all(key in source and (source[key] is None or type(source[key]) is bool) for key in FLAGS),
                 "Execution flags must be explicit true/false/unknown")
        bars[day] = {**values, **{key: source[key] for key in FLAGS}}
    actions, seen = [], set()
    for source in fixture["actions"]:
        identity = source.get("event_id")
        _require(isinstance(identity, str) and identity and identity not in seen and source.get("asset_id") == context.asset_id, "Unique context action identity required")
        _require("share_multiplier" in source and _money(source["share_multiplier"]) == 1,
                 "Explicit unchanged shares required; share conversion unsupported, never ignored")
        dates = {key: _day(source[key], context) for key in ("record_date", "ex_date", "pay_date")}
        _require(dates["record_date"] < dates["ex_date"] <= dates["pay_date"], "Action clocks require record<ex<=pay")
        _require(all(day in sessions for day in dates.values() if sessions[0] <= day <= sessions[-1]), "Action day missing from calendar")
        amount = _money(source["cash_per_unit"])
        _require(amount >= 0, "Nonnegative cash distribution required")
        actions.append({"event_id": identity, **dates, "cash_per_unit": amount})
        seen.add(identity)
    return sessions, bars, tuple(actions)


def _prepare_split(fixture, prepared, mode, *, context=ARTIFICIAL_CONTEXT):
    if mode is None:
        return None
    sessions, bars, actions = prepared
    events = fixture.get("split_events")
    _require(isinstance(events, list) and len(events) == 1, "Exactly one artificial split event required")
    source = events[0]
    identity = source.get("event_id")
    valid_id = (isinstance(identity, str) and identity.startswith("invented_")) if context == ARTIFICIAL_CONTEXT else identity == '511220_share_split_20230113_20230116_1_to_10'
    _require(valid_id
             and identity not in {a["event_id"] for a in actions}
             and source.get("asset_id") == context.asset_id, "Unique context split identity required")
    _require(_money(source["share_multiplier"]) == 10
             and source.get("registry_phase") == "record_day_end", "Exact split10 record-close phase required")
    record, ex, known = (_day(source[k], context) for k in ("record_date", "ex_date", "known_date"))
    _require(known < record < ex and record in sessions, "Explicit prior-known artificial split clocks required")
    following = [day for day in sessions if day > record]
    _require(not following or following[0] == ex, "First session after registration must use ex-date units")
    split = {"event_id": identity, "record_date": record, "ex_date": ex, "known_date": known,
             "share_multiplier": 10, "registry_phase": "record_day_end"}
    for raw in fixture["bars"]:
        _require(raw.get("share_unit") == _trade_unit(raw["date"], split), "Raw bar split-unit mapping missing/conflicting")
    for raw, action in zip(fixture["actions"], actions, strict=True):
        unit = _trade_unit(action["record_date"], split)
        basis = raw.get("cash_per_unit_basis")
        _require(raw.get("record_quantity_unit") == unit and basis in ("pre_split", "post_split"),
                 "Explicit record and cash amount units required in split mode")
        original = action["cash_per_unit"]
        if basis != unit:
            _require(raw.get("cash_basis_mapping") == "explicit_split10_conversion",
                     "Cross-unit dividend needs explicit mapping evidence")
            action["cash_per_unit"] = original * 10 if unit == "pre_split" else original / 10
        action.update(record_quantity_unit=unit, cash_per_unit_basis=basis,
                      original_cash_per_unit=original, normalized_cash_unit=unit)
    return split


def _trade_unit(day, split):
    return "pre_split" if day < split["ex_date"] else "post_split"


def _view_factor(source_day, execution_day, split):
    return 10 if split and source_day < split["ex_date"] <= execution_day else 1


def _close_view(day, raw_close, split):
    factor = 10 if split["record_date"] <= day < split["ex_date"] else 1
    return {"raw_close": raw_close, "raw_quote_unit": _trade_unit(day, split),
            "position_unit": "post_split" if day >= split["record_date"] else "pre_split",
            "post_registration_quote_unit_factor": factor, "valuation_price": raw_close / factor}


def _register_split(quantity, split, day, applied, *, theoretical=False):
    _require(not applied and day == split["record_date"], "Duplicate/out-of-phase split registration")
    _require((isinstance(quantity, Decimal) if theoretical else type(quantity) is int)
             and quantity >= 0, "Exact integer held shares required; no fractional-holder rule")
    new_quantity = quantity * 10
    return new_quantity, {"date": day, "kind": "split_registration", "event_id": split["event_id"],
        "phase": "record_day_end", "quantity_before": quantity, "quantity_after": new_quantity,
        "conversion_delta": new_quantity - quantity, "before_unit": "pre_split", "after_unit": "post_split",
        "CNY_cash_or_cost_changed": False, "theoretical_fractional_reference": theoretical}


def _cash_units(action):
    return {k: action[k] for k in ("record_quantity_unit", "cash_per_unit_basis",
        "original_cash_per_unit", "normalized_cash_unit") if k in action}


def _settings(minimum, slip):
    _require(type(minimum) is int and type(slip) is int and (minimum, slip) in COST_CASES, "One of the exact nine CN cost cases required")
    return {"commission_bps": Decimal("5"), "minimum_commission": Decimal(minimum),
            "slippage_bps": Decimal(slip), "participation": Decimal("0.01")}


def _prior_capacity(sessions, bars, index, settings, split=None):
    _require(index >= 20, "Twenty complete capacity sessions required")
    return _capacity([bars[sessions[n]]["volume"] * _view_factor(sessions[n], sessions[index], split)
                      for n in range(index - 20, index)], settings)


def _pending_record_rights(actions, entitlements, terminal):
    """Recorded rights before ex-date are disclosure, not extra NAV or cash."""
    return [{"event_id": action["event_id"], "record_date": action["record_date"],
             "ex_date": action["ex_date"], "pay_date": action["pay_date"],
             "record_quantity": entitlements[action["event_id"]],
             "declared_cash_per_unit": action["cash_per_unit"],
             "state": "recorded_not_yet_ex_receivable", "included_in_NAV": False,
             "spendable_cash": False, **_cash_units(action)}
            for action in actions if action["ex_date"] > terminal
            and entitlements.get(action["event_id"], 0) > 0]


def _account(prepared, minimum, slip, split=None, *, context=ARTIFICIAL_CONTEXT):
    sessions, bars, actions = prepared
    settings = _settings(minimum, slip)
    recovery = DailyRecovery(RECOVERY_40_DAILY_RETRY)
    cash = previous = peak = INITIAL
    quantity = 0
    entitlements, receivables = {}, {}
    rows, fills, attempts, action_journal, execution_uncertainty = [], [], [], [], []
    total_buy = total_sell = total_fee = received = price_impact = Decimal(0)
    buys = sells = 0
    max_dd = Decimal(0)
    entry_index = None
    episodes = 0
    completed_episodes = 0
    max_holding = 0
    conversion_delta, split_applied = 0, False
    for index, day in enumerate(sessions):
        bar = bars[day]
        at_start = quantity
        recovery.before_open(index, day, positions={context.asset_id: quantity} if quantity else {}, permanently_halted=False)
        terminal = index == len(sessions) - 1
        prior_cap = _prior_capacity(sessions, bars, index, settings, split) if index >= 20 else 0
        plan = None
        if index >= 20 and not terminal and not at_start and not recovery.paused:
            budget = min(cash, previous)
            prior_price = bars[sessions[index - 1]]["close"]
            if split:
                prior_price /= _view_factor(sessions[index - 1], day, split)
            planned_price = _price(prior_price, 1, settings)
            planned = min(int(budget / planned_price / 100) * 100, prior_cap // 100 * 100)
            while planned > 0 and planned * planned_price + _fee(planned * planned_price, settings) > budget:
                planned -= 100
            plan = {"side": "buy", "quantity": planned, "budget": budget,
                    "planned_price": planned_price, "price_known_date": sessions[index - 1],
                    "capacity_dates": [sessions[index - 20], sessions[index - 1]], "prior_capacity": prior_cap}
            if split:
                plan.update(execution_share_unit=_trade_unit(day, split),
                    prior_price_unit_factor=_view_factor(sessions[index - 1], day, split),
                    source_close_raw=bars[sessions[index - 1]]["close"],
                    capacity_unit_factors=[{"date": sessions[n], "factor": _view_factor(sessions[n], day, split)}
                                           for n in range(index - 20, index)], split_event_id=split["event_id"])
        for action in actions:
            identity = action["event_id"]
            if action["ex_date"] == day:
                credit = (entitlements.get(identity, 0) * action["cash_per_unit"]).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
                receivables[identity] = credit
                action_journal.append({"date": day, "event_id": identity, "kind": "receivable_created", "amount": credit, **_cash_units(action)})
        side, requested, reason = None, 0, None
        if at_start and (terminal or recovery.paused):
            side = "sell"
            requested = min(at_start, prior_cap // 100 * 100)
            reason = "terminal_exit" if terminal else "risk_exit"
        elif plan is not None:
            side, requested, reason = "buy", plan["quantity"], "ordinary_flat_entry"
        if side:
            sign = 1 if side == "buy" else -1
            execution_price = _price(bar["open"], sign, settings)
            notional = requested * execution_price
            fee = _fee(notional, settings) if requested else Decimal(0)
            unknown = [key for key in FLAGS if bar[key] is None]
            rejected = ("below_one_lot_or_prior_capacity" if requested <= 0 else
                        "known_execution_constraint" if bar["suspended"] is True or bar["limit_up" if side == "buy" else "limit_down"] is True else
                        "entry_budget_or_cash" if side == "buy" and notional + fee > min(cash, plan["budget"]) else
                        "exit_fee_exceeds_cash" if side == "sell" and cash + notional < fee else None)
            attempt = {"date": day, "side": side, "reason": reason, "requested_quantity": requested,
                       "execution_price": execution_price, "notional": notional, "fee": fee,
                       "plan": plan, "unknown_flags": unknown, "rejected": rejected}
            if split:
                attempt.update(trade_share_unit=_trade_unit(day, split), prior_capacity=prior_cap,
                    exit_intent="all_remaining_holdings_subject_to_capacity" if side == "sell" else None,
                    split_event_id=split["event_id"],
                    capacity_unit_factors=[{"date": sessions[n], "factor": _view_factor(sessions[n], day, split)}
                                           for n in range(max(0, index - 20), index)])
            attempts.append(attempt)
            if not rejected:
                before_cash = cash
                cash += -notional - fee if side == "buy" else notional - fee
                quantity += requested if side == "buy" else -requested
                total_fee += fee
                impact = requested * (execution_price - bar["open"]) * sign
                price_impact += impact
                if side == "buy":
                    total_buy += notional; buys += requested; entry_index = index; episodes += 1
                else:
                    total_sell += notional; sells += requested
                    if not quantity:
                        completed_episodes += 1
                        entry_index = None
                _require(cash >= 0 and quantity >= 0, "No borrowing or negative positions")
                fill = {**attempt, "quantity": requested, "cash_before": before_cash, "cash_after": cash,
                        "raw_open_price": bar["open"], "slippage_and_tick_cost_CNY": impact,
                        "position_after": quantity, "capacity_basis": "only_prior20_complete_sessions",
                        "current_day_volume_used_to_decide_fill": False}
                fills.append(fill)
                # This observation is explicitly later than the modeled open fill.
                retrospective_capacity = _capacity([bar["volume"]], settings)
                if requested > retrospective_capacity:
                    execution_uncertainty.append({"date": day, "reason": "ex_post_full_day_capacity_not_met",
                        "quantity": requested, "realized_day_capacity": retrospective_capacity,
                        "fill_retained": True, "economic_path_rolled_back": False})
                if unknown:
                    execution_uncertainty.append({"date": day, "reason": "unknown_execution_flags",
                                                   "flags": unknown, "fill_retained_as_conditional": True})
        before_payment = cash
        for action in actions:
            identity = action["event_id"]
            if action["record_date"] == day:
                entitlements[identity] = quantity
                action_journal.append({"date": day, "event_id": identity, "kind": "record_entitlement", "quantity": quantity, **_cash_units(action)})
            if action["pay_date"] == day:
                amount = receivables.pop(identity, Decimal(0))
                cash += amount; received += amount
                action_journal.append({"date": day, "event_id": identity, "kind": "paid_after_fills", "amount": amount, **_cash_units(action)})
        if split and day == split["record_date"]:
            quantity, registration = _register_split(quantity, split, day, split_applied)
            conversion_delta += registration["conversion_delta"]
            split_applied = True
            action_journal.append(registration)
        close_view = _close_view(day, bar["close"], split) if split else None
        pending = sum(receivables.values(), Decimal(0))
        market_value = quantity * (close_view["valuation_price"] if split else bar["close"])
        equity = cash + pending + market_value
        _require(equity > 0 and market_value <= equity and cash >= 0, "Positive NAV and100percent account exposure required")
        peak = max(peak, equity)
        dd = 1 - equity / peak
        max_dd = max(max_dd, dd)
        recovery.after_close(index, day, previous=previous, equity=equity,
            positions={context.asset_id: quantity} if quantity else {}, drawdown=dd, had_exposure=bool(at_start or quantity))
        holding_sessions = index - entry_index + 1 if entry_index is not None else 0
        max_holding = max(max_holding, holding_sessions)
        rows.append({"date": day, "index": index, "cash": cash, "cash_before_distribution_payment": before_payment,
            "quantity": quantity, "market_value": market_value, "dividend_receivable": pending,
            "equity": equity, "previous_close_NAV": previous, "global_peak": peak,
            "daily_loss_CNY": max(previous - equity, Decimal(0)), "sampled_close_drawdown": dd,
            "paused_after_close": recovery.paused, "cooldown_flat_index": recovery.flat_index,
            "holding_sessions": holding_sessions, "terminal_session": terminal})
        if split:
            rows[-1].update(**close_view, split_mode=SPLIT_MODE, split_event_applied=split_applied,
                           cumulative_conversion_delta=conversion_delta)
        previous = equity
    reconciled = (INITIAL - total_buy + total_sell - total_fee + received == cash
                  and buys - sells + conversion_delta == quantity
                  and cash + market_value + sum(receivables.values(), Decimal(0)) == previous)
    _require(reconciled, "Exact cash/quantity/NAV reconciliation failed")
    pending_record_rights = _pending_record_rights(actions, entitlements, sessions[-1])
    result = {"artifact_type": "synthetic_bond_risk_compensation_account_v1", "evidence_class": context.evidence_class,
        "source_module": __file__, "initial_cash_CNY": INITIAL, "cost_case": {"commission_bps_each": 5,
        "minimum_commission_CNY": minimum, "slippage_bps_each": slip},
        "rows": rows, "fills": fills, "attempts": attempts, "actions": action_journal,
        "risk_journal": recovery.journal, "execution_uncertainty": execution_uncertainty,
        "unknown_flag_rows": sum(any(bar[key] is None for key in FLAGS) for bar in bars.values()),
        "summary": {"cash": cash, "remaining_quantity": quantity, "dividend_receivable": sum(receivables.values(), Decimal(0)),
            "terminal_book_NAV": previous, "net_book_PnL": previous - INITIAL, "cash_PnL": cash - INITIAL,
            "total_commission_CNY": total_fee, "dividend_cash_received": received,
            "total_slippage_and_tick_cost_CNY": price_impact,
            "pending_record_entitlements": pending_record_rights,
            "terminal_value_scope": "cash_holdings_and_ex_receivables_only; pending_record_rights_excluded; if_pending_not_complete_settled_return",
            "terminal_unsettled": quantity != 0 or any(receivables.values()) or bool(pending_record_rights),
            "daily_close_model_max_drawdown": max_dd, "observed_drawdown_over_40pct": max_dd > Decimal(".40"),
            "episodes_started": episodes, "completed_roundtrips": completed_episodes,
            "maximum_holding_sessions": max_holding, "cash_quantity_NAV_reconciled": reconciled,
            "execution_uncertainty_count": len(execution_uncertainty), "conditional_model_complete": True},
        "assumptions": {"prior_complete_daily_bar_available_before_next_open": True,
            "payment_available_after_session_trading_only": True,
            "open_print_is_conditional_fill_not_orderbook_certification": True,
            "intraday_drawdown_or_liquidity_path_certified": False,
            "fund_lookthrough_leverage_at_most_one_certified": False},
        "cost_attribution": "Slippage/tick impact is already included in fill notional; never deduct it twice",
        "qualified": False, "alpha_eligible": False, "historical_returns_computed": False,
        "real_forward_days": 0}
    if split:
        result.update(split_mode=SPLIT_MODE, split_event=split,
            quantity_reconciliation="raw_stage_trade_changes_plus_nontrade_conversion_delta; not_same_unit_volume",
            split_known_before_plan_is_artificial_assumption=True)
        result["summary"]["nontrade_conversion_delta"] = conversion_delta
    if context == HISTORICAL_CONTEXT:
        result.update(artifact_type='conditional_historical_bond_risk_compensation_account_v1',
                      asset_id=context.asset_id, historical_returns_computed=True)
        result['split_known_before_plan_is_artificial_assumption'] = False
        result['split_known_before_plan_is_historical_conditional_assumption'] = True
    return result


def run_synthetic_account(fixture, *, minimum_commission=5, slippage_bps=10, split_mode=None):
    """Only explicit artificial2001 fixtures; all numerical stages share context40."""
    with localcontext(CONTEXT):
        prepared = _prepare(fixture, split_mode)
        split = _prepare_split(fixture, prepared, split_mode)
        return _exact(_account(prepared, minimum_commission, slippage_bps, split))


def _reference(prepared, split=None, *, context=ARTIFICIAL_CONTEXT):
    sessions, bars, actions = prepared
    q_ref = INITIAL / bars[sessions[20]]["open"]
    quantity, cash = Decimal(0), INITIAL
    entitlements, receivables, rows, journal = {}, {}, [], []
    split_journal, split_applied = [], False
    for index, day in enumerate(sessions):
        for action in actions:
            key = action["event_id"]
            if action["ex_date"] == day:
                receivables[key] = entitlements.get(key, Decimal(0)) * action["cash_per_unit"]
        if index == 20:
            quantity, cash = q_ref, Decimal(0)
        if index == len(sessions) - 1:
            cash += quantity * bars[day]["open"]
            quantity = Decimal(0)
        for action in actions:
            key = action["event_id"]
            if action["record_date"] == day:
                entitlements[key] = quantity
            if action["pay_date"] == day:
                payment = receivables.pop(key, Decimal(0))
                cash += payment
                journal.append({"date": day, "event_id": key, "cash_distribution": payment})
                if split:
                    journal[-1].update(**_cash_units(action))
        if split and day == split["record_date"]:
            quantity, registration = _register_split(quantity, split, day, split_applied, theoretical=True)
            split_journal.append(registration)
            split_applied = True
        close_view = _close_view(day, bars[day]["close"], split) if split else None
        pending = sum(receivables.values(), Decimal(0))
        rows.append({"date": day, "quantity": quantity, "cash": cash, "dividend_receivable": pending,
                     "economic_value": cash + pending + quantity * (close_view["valuation_price"] if split else bars[day]["close"])})
        if split:
            rows[-1].update(**close_view, split_event_applied=split_applied)
    pending_record_rights = _pending_record_rights(actions, entitlements, sessions[-1])
    result = {"artifact_type": "synthetic_nontrading_same_ETF_reference_v1", "not_an_executable_account": True,
        "source_class": context.evidence_class, "first_entry_date": sessions[20], "terminal_date": sessions[-1],
        "entry_and_terminal_price_basis": "fixed_raw_open", "fixed_theoretical_quantity": q_ref,
        "distribution_rounding": "context40_theoretical_fractional_units_not_cent_payment_simulation",
        "distribution_cash_reinvested": False, "fees_capacity_risk_exit_rules_applied": False,
        "same_product_not_dynamic_exposure_matched": True, "rows": rows, "payments": journal,
        "summary": {"terminal_economic_value": rows[-1]["economic_value"], "terminal_cash": cash,
                    "terminal_unpaid_receivable": sum(receivables.values(), Decimal(0)),
                    "pending_record_entitlements": pending_record_rights,
                    "terminal_value_scope": "theoretical_cash_and_ex_receivables_only; pending_record_rights_excluded; if_pending_not_complete_settled_return",
                    "terminal_unsettled": bool(quantity) or any(receivables.values()) or bool(pending_record_rights)},
        "qualified": False}
    if split:
        result.update(split_mode=SPLIT_MODE, split_event=split, split_registrations=split_journal,
            theoretical_initial_quantity_unit=_trade_unit(sessions[20], split),
            conversion_convention="ideal_fractional_units_times10_not_actual_holder_rounding")
    if context == HISTORICAL_CONTEXT:
        result.update(artifact_type='conditional_historical_nontrading_same_ETF_reference_v1',
                      asset_id=context.asset_id, historical_returns_computed=True)
    return result


def run_synthetic_bundle(fixture, *, split_mode=None):
    with localcontext(CONTEXT):
        prepared = _prepare(fixture, split_mode)
        split = _prepare_split(fixture, prepared, split_mode)
        accounts = [_account(prepared, minimum, slip, split) for minimum, slip in COST_CASES]
        cash = {"artifact_type": "synthetic_zero_interest_cash_control_v1", "evidence_class": ARTIFICIAL,
                "initial_cash_CNY": INITIAL, "rows": [{"date": day, "cash": INITIAL, "equity": INITIAL}
                                                      for day in prepared[0]],
                "interest": Decimal(0), "not_a_riskfree_rate_or_income_target": True, "qualified": False}
        return _exact({"artifact_type": "synthetic_bond_contract_bundle_v1", "source_module": __file__,
            "evidence_class": ARTIFICIAL, "fee_accounts": accounts, "cash_control": cash,
            "account_count": 10, "additional_nontrading_reference_count": 1, "reference": _reference(prepared, split),
            "qualified": False, "historical_returns_computed": False, "financial_admission": False,
            "new_financial_studies": 0, "real_forward_days": 0})


def fixed_artificial_fixture(sessions_count=72):
    """Invented calendar sessions and values, never market observations."""
    _require(type(sessions_count) is int and 22 <= sessions_count <= 365, "Bounded artificial session count")
    sessions = [(date(2001, 1, 1) + timedelta(days=n)).isoformat() for n in range(sessions_count)]
    bars = []
    for index, day in enumerate(sessions):
        opening = Decimal("91") if index <= 25 else Decimal("86")
        close = Decimal("91") if index < 25 else Decimal("86")
        if index >= 46:
            opening = close = Decimal("85.8")
        bars.append({"date": day, "asset_id": ASSET, "open": str(opening), "close": str(close),
            "high": str(max(opening, close)), "low": str(min(opening, close)), "volume": "100000",
            "suspended": False, "limit_up": False, "limit_down": False})
    actions = []
    if sessions_count > 48:
        actions.append({"event_id": "invented_cash_distribution", "asset_id": ASSET,
            "record_date": sessions[45], "ex_date": sessions[46], "pay_date": sessions[48],
            "cash_per_unit": "0.2", "share_multiplier": "1"})
    return {"evidence_class": ARTIFICIAL, "asset_id": ASSET, "invented_values": True,
            "price_unit": "CNY_per_share", "volume_unit": "shares", "price_basis": "raw_unadjusted",
            "corporate_actions_complete": True,
            "sessions": sessions, "bars": bars, "actions": actions}


def fixed_split_artificial_fixture():
    """A36session invented unit bridge and cash payment, no historical inputs."""
    fixture = fixed_artificial_fixture(36)
    sessions = fixture["sessions"]
    fixture["split_events"] = [{"event_id": "invented_split10", "asset_id": ASSET,
        "record_date": sessions[25], "ex_date": sessions[26], "known_date": sessions[22],
        "share_multiplier": "10", "registry_phase": "record_day_end"}]
    for index, bar in enumerate(fixture["bars"]):
        price = "91" if index < 26 else "9.1" if index < 27 else "9.08"
        bar.update({key: price for key in ("open", "high", "low", "close")})
        bar.update(share_unit="pre_split" if index < 26 else "post_split",
                   volume="100000" if index < 26 else "1000000")
    fixture["actions"] = [{"event_id": "invented_old_unit_distribution", "asset_id": ASSET,
        "record_date": sessions[24], "ex_date": sessions[27], "pay_date": sessions[29],
        "cash_per_unit": "0.2", "share_multiplier": "1", "record_quantity_unit": "pre_split",
        "cash_per_unit_basis": "pre_split"}]
    return fixture
