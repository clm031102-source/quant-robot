"""Four-asset USD conditional ledger. Public entry accepts invented data only.

No source files, broker accounts or orders are opened here. A private immutable
context identifies normalized historical input; its external controller owns
the once-only financial permission and guards.
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import (Decimal as D, Context, localcontext, ROUND_HALF_UP,
                     ROUND_FLOOR, ROUND_CEILING, InvalidOperation, DivisionByZero, Overflow)
from pathlib import Path

ASSETS = ("SPY", "EFA", "IEF", "GLD")
POLICIES = ("rotation", "positive_equal", "fixed_quarters")
COSTS = tuple((m, s) for m in ("0.35", "1.00", "2.50") for s in (0, 10, 30))
METHOD_SHA = "dbc19912feded581fd55c4a5e0aa992140e3dfa4743586df2cd3a00c83e04a30"
ZERO, CENT, INITIAL, BUFFER = D(0), D(".01"), D("1000.00"), D("10.00")
CONTEXT = Context(prec=40, rounding=ROUND_HALF_UP, Emin=-999999, Emax=999999, capitals=1, clamp=0)
for _s in CONTEXT.traps:
    CONTEXT.traps[_s] = _s in (InvalidOperation, DivisionByZero, Overflow)
CONTEXT.clear_flags()


def serial(value):
    if isinstance(value, D): return str(value)
    if isinstance(value, dict): return {k: serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [serial(v) for v in value]
    return value


def canonical(value):
    return json.dumps(serial(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def context_record(c):
    return dict(prec=c.prec, rounding=c.rounding, Emin=c.Emin, Emax=c.Emax, capitals=c.capitals,
                clamp=c.clamp, traps={k.__name__: v for k, v in c.traps.items()},
                flags={k.__name__: v for k, v in c.flags.items()})


def _require(condition, reason):
    if not condition: raise ValueError(reason)


def _number(value, *, positive=False):
    _require(type(value) is str, "decimal_string_required")
    result = D(value)
    _require(result.is_finite() and (result > 0 if positive else result >= 0), "invalid_decimal_value")
    return result


def _hash(value):
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


@dataclass(frozen=True)
class _ExecutionContext:
    evidence_kind: str
    method_sha256: str
    fixture_sha256: str
    provenance_sha256: str
    registration_sha256: str | None = None
    test_values: bool = False

    def __post_init__(self):
        _require(self.evidence_kind in ("artificial", "known_history_conditional")
                 and self.method_sha256 == METHOD_SHA and type(self.test_values) is bool,
                 "fixed_evidence_context")
        _require(_hash(self.fixture_sha256) and _hash(self.provenance_sha256), "context_hash_required")
        if self.evidence_kind == "known_history_conditional":
            _require(_hash(self.registration_sha256), "registration_hash_required")
        else:
            _require(self.registration_sha256 is None and not self.test_values, "artificial_context_identity")

    @property
    def historical(self):
        return self.evidence_kind == "known_history_conditional" and not self.test_values

    @property
    def output_kind(self):
        return "artificial_values_true_calendar" if self.test_values else self.evidence_kind


@dataclass(frozen=True)
class Prepared:
    fixture_sha256: str
    normalized: dict
    normalized_sha256: str


def prepare(fixture, *, context):
    with localcontext(CONTEXT):
        _require(type(context) is _ExecutionContext and digest(fixture) == context.fixture_sha256
                 and digest(fixture["provenance"]) == context.provenance_sha256, "bound_fixture_context_required")
        _require(fixture.get("schema") == "us_monthly_rotation_fixture_v1"
                 and fixture.get("method_sha256") == METHOD_SHA
                 and fixture.get("evidence_kind") == context.output_kind
                 and fixture.get("assets") == list(ASSETS), "fixed_fixture_identity")
        provenance = fixture["provenance"]
        _require(provenance.get("split_policy_verified") is True
                 and provenance.get("capital_gains_present") is False, "split_and_capital_gains_policy_required")
        if context.evidence_kind == "artificial" or context.test_values:
            _require(provenance.get("constructed_from_market_data") is False, "invented_values_required")
        else:
            _require(provenance.get("constructed_from_market_data") is True, "real_source_identity_required")
        rows = fixture["days"]
        dates = [r["date"] for r in rows]
        _require(len(dates) >= 30 and dates == sorted(set(dates)), "ordered_complete_common_calendar")
        parsed = [date.fromisoformat(d) for d in dates]
        _require(all(d.isoformat() == text for d, text in zip(parsed, dates)), "canonical_dates")
        if context.evidence_kind == "artificial":
            _require(all(2000 <= d.year <= 2004 for d in parsed), "public_artificial_years_only")
        terminal = dates.index(fixture["terminal_date"])
        _require(terminal == len(rows)-1, "no_post_terminal_input")
        if context.historical:
            _require(dates[0] >= "2004-12-01" and dates[0][:7] == "2004-12"
                     and dates[terminal] == "2024-12-31", "fixed_historical_window")
        bars, execution = [], []
        for i, row in enumerate(rows):
            _require(set(row["prices"]) == set(ASSETS), "four_same_session_assets")
            new = {}
            for a in ASSETS:
                old = row["prices"][a]
                new[a] = {"open": _number(old["open"], positive=True)}
                if i == terminal:
                    _require(row.get("terminal_open_only") is True and all(old.get(k) is None for k in
                             ("high", "low", "close", "adj_close", "volume")), "terminal_open_only")
                    new[a].update({k: None for k in ("high", "low", "close", "adj_close", "volume")})
                else:
                    new[a].update({k: _number(old[k], positive=k != "volume") for k in
                                   ("high", "low", "close", "adj_close", "volume")})
                    _require(new[a]["low"] <= min(new[a]["open"], new[a]["close"])
                             <= max(new[a]["open"], new[a]["close"]) <= new[a]["high"], "OHLC_rectangle")
            flags = row.get("execution", {a: dict(suspended=None, buy_blocked=None, sell_blocked=None) for a in ASSETS})
            _require(set(flags) == set(ASSETS), "execution_assets")
            for f in flags.values():
                _require(set(f) == {"suspended", "buy_blocked", "sell_blocked"}
                         and all(v is None or type(v) is bool for v in f.values()), "explicit_execution_flags")
            bars.append(new); execution.append(copy.deepcopy(flags))
        month_ends = [i for i in range(terminal) if dates[i][:7] != dates[i+1][:7]]
        serials = [parsed[i].year*12+parsed[i].month for i in month_ends]
        _require(len(month_ends) >= 13 and all(b-a == 1 for a, b in zip(serials, serials[1:])), "consecutive_monthly_endpoints")
        first = dates.index(fixture["first_decision_date"])
        _require(first == month_ends[12] and first+4 < terminal and first >= 20, "first_decision_thirteen_months")
        if context.historical:
            _require(dates[first][:7] == "2005-12", "fixed_first_decision")
        dividends, ids = [], set()
        for item in fixture["dividends"]:
            _require(type(item["id"]) is str and item["id"] not in ids and item["symbol"] in ASSETS, "unique_dividend_identity")
            ids.add(item["id"])
            _require(item["ex_date"] in dates, "ex_date_in_common_calendar")
            dividends.append(dict(id=item["id"], symbol=item["symbol"], ex_index=dates.index(item["ex_date"]),
                amount_per_share=_number(item["amount_per_share"]),
                earliest_payment_date=(date.fromisoformat(item["ex_date"])+timedelta(days=45)).isoformat()))
        signals = {}
        for j in range(12, len(month_ends)):
            i, prior = month_ends[j], month_ends[j-12]
            returns = {a: bars[i][a]["adj_close"]/bars[prior][a]["adj_close"]-1 for a in ASSETS}
            positive = [a for a in ASSETS if returns[a] > 0]
            ranked = sorted(positive, key=lambda a: (-returns[a], ASSETS.index(a)))
            gross = D(min(len(positive), 2))/2
            weights = {"rotation": {a: D(".5") if a in ranked[:2] else ZERO for a in ASSETS},
                       "positive_equal": {a: gross/len(positive) if a in positive else ZERO for a in ASSETS},
                       "fixed_quarters": dict.fromkeys(ASSETS, D(".25"))}
            signals[i] = dict(index=i, date=dates[i], prior_date=dates[prior], returns=returns,
                              positive=positive, ranked_positive=ranked, intended_gross=gross, weights=weights,
                              ordinary_execution_possible=i+4 < terminal)
        normalized = dict(dates=dates, bars=bars, execution=execution,
            dividends=dividends, signals=signals, first=first, terminal=terminal)
        return Prepared(context.fixture_sha256, normalized, digest(normalized))


def _price(value, side, slip):
    return (value*(1+D(slip)/10000*(1 if side == "buy" else -1))).quantize(
        CENT, rounding=ROUND_CEILING if side == "buy" else ROUND_FLOOR)


def _fee(q, minimum):
    return max(D(minimum), D(q)*D(".005")).quantize(CENT, rounding=ROUND_CEILING)


def _floor(value):
    return max(0, int(value.to_integral_value(rounding=ROUND_FLOOR)))


class _Account:
    def __init__(self, prepared, policy, minimum, slip):
        _require(policy in (*POLICIES, "cash") and type(minimum) is str and type(slip) is int
                 and (minimum, slip) in COSTS, "fixed_policy_cost_identity")
        self.p = prepared.normalized
        self.policy, self.minimum, self.slip = policy, minimum, slip
        self.cash, self.q, self.locks, self.receivables = INITIAL, dict.fromkeys(ASSETS, 0), [], {}
        self.peak = self.reference = self.previous = INITIAL
        self.previous_dd = self.max_dd = ZERO
        self.paused, self.cooldown, self.risk_due = False, 0, None
        self.pending = None
        self.days, self.fills, self.intents, self.rejections, self.risks, self.actions, self.events = [], [], [], [], [], [], []
        self.observations, self.unknowns, self.annual = [], [], {}
        self.lots = {a: [] for a in ASSETS}
        self.total_fee = self.total_levy = self.total_slip = self.total_net_dividend = ZERO
        self.i = self.p["first"]
        self.day_active = self.triggered = False

    def balances(self):
        return dict(spendable_cash=self.cash, locked_cash=sum((x["amount"] for x in self.locks), ZERO),
                    locks=copy.deepcopy(self.locks), quantities=dict(self.q), receivables=copy.deepcopy(self.receivables))

    def marks(self, field):
        return {a: self.p["bars"][self.i][a][field] for a in ASSETS}

    def nav(self, marks):
        return self.cash+sum((x["amount"] for x in self.locks), ZERO)+sum((x["amount"] for x in self.receivables.values()), ZERO)+sum((self.q[a]*marks[a] for a in ASSETS), ZERO)

    def capacity(self, a, before):
        _require(before >= 20, "twenty_completed_volume_days")
        return _floor(sum((self.p["bars"][j][a]["volume"] for j in range(before-20, before)), ZERO)/20*D(".01"))

    def observe(self, marks, phase):
        nav = self.nav(marks)
        _require(nav > 0 and self.cash >= 0 and all(q >= 0 for q in self.q.values()), "wallet_invariant")
        self.day_active = self.day_active or any(self.q.values())
        self.peak = max(self.peak, nav)
        dd = (self.peak-nav)/self.peak
        loss = (self.reference-nav)/self.reference
        fresh = self.previous_dd < D(".40") <= dd
        dd_trigger = dd >= D(".40") and (self.day_active or fresh)
        daily_trigger = loss >= D(".02")
        trigger = dd_trigger or daily_trigger
        row = dict(index=self.i, date=self.p["dates"][self.i], phase=phase, marks=marks,
                   balances=self.balances(), NAV=nav, reference_NAV=self.reference, peak=self.peak,
                   DD=dd, daily_loss=loss, fresh_DD_cross=fresh, day_active=self.day_active,
                   DD_trigger=bool(dd_trigger), daily_trigger=bool(daily_trigger), trigger=bool(trigger))
        self.observations.append(row)
        if dd >= D(".40") or daily_trigger: self.risks.append(copy.deepcopy(row))
        if trigger:
            self.paused, self.cooldown, self.triggered = True, 0, True
            if any(self.q.values()):
                self.risk_due = min(self.risk_due, self.i+1) if self.risk_due is not None else self.i+1
            if self.pending:
                self.pending["status"] = "cancelled_increases_by_risk"
                self.pending["buy_orders"] = []
        self.previous_dd, self.max_dd = dd, max(self.max_dd, dd)
        return nav

    def opening_actions(self):
        net_entitlement = ZERO
        for lock in list(self.locks):
            if lock["release_index"] <= self.i:
                before = self.balances(); self.cash += lock["amount"]; self.locks.remove(lock)
                self.actions.append(dict(index=self.i, kind="sale_cash_release", item=lock, before=before, after=self.balances()))
        for key, item in list(self.receivables.items()):
            if item["earliest_payment_date"] <= self.p["dates"][self.i]:
                before = self.balances(); self.cash += item["amount"]; del self.receivables[key]
                self.actions.append(dict(index=self.i, kind="dividend_payment", id=key, item=item, before=before, after=self.balances()))
        for d in self.p["dividends"]:
            if d["ex_index"] == self.i and self.q[d["symbol"]] > 0:
                before = self.balances(); q = self.q[d["symbol"]]
                gross = q*d["amount_per_share"]; net = (gross*D(".70")).quantize(CENT)
                item = dict(symbol=d["symbol"], quantity=q, gross=gross, amount=net,
                            modeled_withholding=gross-net, earliest_payment_date=d["earliest_payment_date"])
                self.receivables[d["id"]] = item
                net_entitlement += net; self.total_net_dividend += net
                self.actions.append(dict(index=self.i, kind="ex_entitlement", id=d["id"], item=copy.deepcopy(item), before=before, after=self.balances()))
        return net_entitlement

    def decision(self, index):
        signal = self.p["signals"][index]
        event = dict(decision_index=index, date=self.p["dates"][index], signal=copy.deepcopy(signal),
                     policy=self.policy, status="created", targets={}, sell_orders=[], buy_orders=[])
        self.events.append(event)
        if self.policy == "cash" or self.paused or self.risk_due is not None or not signal["ordinary_execution_possible"]:
            event["status"] = "skipped_cash_risk_or_terminal"; return
        _require(self.pending is None, "overlapping_monthly_plan")
        nav = self.previous
        targets = {a: _floor(max(nav-BUFFER, ZERO)*signal["weights"][self.policy][a]/self.p["bars"][index][a]["close"]) for a in ASSETS}
        event.update(targets=targets, decision_NAV=nav, sell_index=index+1, plan_index=index+3, buy_index=index+4,
                     status="sell_intents_frozen", pre_decision_balances=self.balances())
        for a in ASSETS:
            cap = self.capacity(a, index+1)
            event["sell_orders"].append(dict(asset=a, side="sell", quantity=min(max(self.q[a]-targets[a], 0), cap),
                capacity=cap, planned_price=self.p["bars"][index][a]["close"], phase="monthly_sell", budget=None,
                planned_index=index, due_index=index+1))
        self.pending = event

    def plan_buys(self, event):
        if self.paused or self.risk_due is not None:
            event["status"] = "cancelled_increases_by_risk"; event["buy_orders"] = []; return
        due = sum((x["amount"] for x in self.locks if x["release_index"] <= self.i+1), ZERO)
        available = max(self.cash+due-BUFFER, ZERO)
        needs, costs, prices = {}, {}, {}
        for a in ASSETS:
            needs[a] = min(max(event["targets"][a]-self.q[a], 0), self.capacity(a, self.i+1))
            prices[a] = _price(self.p["bars"][self.i][a]["close"], "buy", self.slip)
            costs[a] = needs[a]*prices[a]+_fee(needs[a], self.minimum) if needs[a] else ZERO
        total = sum(costs.values(), ZERO)
        orders = []
        for a in ASSETS:
            budget = (available*costs[a]/total).quantize(CENT, rounding=ROUND_FLOOR) if total else ZERO
            q = min(needs[a], _floor(budget/prices[a]))
            while q and q*prices[a]+_fee(q, self.minimum) > budget: q -= 1
            orders.append(dict(asset=a, side="buy", quantity=q, capacity=self.capacity(a, self.i+1),
                planned_price=prices[a], phase="monthly_buy", budget=budget, planned_index=self.i, due_index=self.i+1))
        event.update(buy_orders=orders, status="buy_intents_frozen", buy_planning_index=self.i,
                     buy_planning_balances=self.balances(), exact_next_open_due_cash=due,
                     buy_available_after_buffer=available, planned_costs=costs)

    def fill(self, order):
        intent = dict(order, intent_id=len(self.intents)); self.intents.append(intent)
        a, side, q = order["asset"], order["side"], order["quantity"]
        if not q: return False
        _require(type(q) is int and 0 < q <= order["capacity"] and order["planned_index"] < self.i
                 and order["due_index"] == self.i, "causal_fixed_integer_order")
        flags = self.p["execution"][self.i][a]
        if flags["suspended"] or flags[side+"_blocked"]:
            self.rejections.append(dict(index=self.i, intent_id=intent["intent_id"], reason="known_execution_constraint")); return False
        for k in ("suspended", side+"_blocked"):
            if flags[k] is None: self.unknowns.append(dict(index=self.i, asset=a, flag=k, intent_id=intent["intent_id"]))
        raw = self.p["bars"][self.i][a]["open"]
        price = _price(raw, side, self.slip)
        fee = _fee(q, self.minimum); notional = q*price
        levy = (notional*D(".0005")).quantize(CENT, rounding=ROUND_CEILING) if side == "sell" else ZERO
        reason = None
        if price <= 0: reason = "nonpositive_adverse_price"
        elif side == "buy" and self.paused: reason = "risk_cancelled_increase"
        elif side == "buy" and (notional+fee > order["budget"] or notional+fee > self.cash): reason = "frozen_budget_or_spendable_cash"
        elif side == "sell" and q > self.q[a]: reason = "quantity_no_longer_available"
        elif side == "sell" and notional-fee-levy < -self.cash: reason = "free_cash_insufficient_exit_fee"
        if side == "buy" and reason is None:
            marks = self.marks("open")
            after_exposure = sum((self.q[s]*marks[s] for s in ASSETS), ZERO)+q*raw
            after_nav = self.nav(marks)-(notional+fee)+q*raw
            if after_exposure > after_nav: reason = "marked_exposure_exceeds_NAV"
        if reason:
            self.rejections.append(dict(index=self.i, intent_id=intent["intent_id"], reason=reason,
                                       actual_price=price, actual_notional=notional, fee=fee, levy=levy)); return False
        before = self.balances(); fifo = []
        if side == "buy":
            self.cash -= notional+fee; self.q[a] += q
            self.lots[a].append(dict(index=self.i, initial=q, remaining=q, original_cost=notional+fee, remaining_cost=notional+fee))
        else:
            self.q[a] -= q
            net = notional-fee-levy
            if net > 0:
                due = self.i+3
                self.locks.append(dict(id="sale_"+str(intent["intent_id"]), amount=net, sale_index=self.i,
                                       release_index=due, release_date=self.p["dates"][due] if due < len(self.p["dates"]) else None))
            else: self.cash += net
            left = q
            for lot in self.lots[a]:
                take = min(left, lot["remaining"])
                if not take: continue
                cost = lot["remaining_cost"] if take == lot["remaining"] else lot["remaining_cost"]*take/lot["remaining"]
                lot["remaining"] -= take; lot["remaining_cost"] -= cost; left -= take
                fifo.append(dict(buy_index=lot["index"], quantity=take, released_cost=cost))
                if not left: break
            _require(left == 0, "FIFO_quantity_identity")
        slippage = q*((price-raw) if side == "buy" else (raw-price))
        self.total_fee += fee; self.total_levy += levy; self.total_slip += slippage
        self.fills.append(dict(index=self.i, date=self.p["dates"][self.i], intent_id=intent["intent_id"],
            asset=a, side=side, quantity=q, phase=order["phase"], raw_open=raw, price=price, notional=notional,
            fee=fee, sell_levy=levy, slippage_cost=slippage, frozen_budget=order["budget"], FIFO=fifo,
            before=before, after=self.balances(), observed_full_day_volume=self.p["bars"][self.i][a]["volume"],
            volume_observation_clock="after_completed_session_not_available_to_order" if self.i != self.p["terminal"] else "unavailable_at_terminal_open"))
        self.observe(self.marks("open"), "post_fill_"+str(intent["intent_id"]))
        return True

    def exit_orders(self, phase):
        for a in ASSETS:
            self.fill(dict(asset=a, side="sell", quantity=min(self.q[a], self.capacity(a, self.i)),
                capacity=self.capacity(a, self.i), planned_price=self.p["bars"][self.i-1][a]["close"],
                phase=phase, budget=None, planned_index=self.i-1, due_index=self.i))

    def run(self):
        self.decision(self.p["first"])
        for i in range(self.p["first"]+1, self.p["terminal"]+1):
            self.i = i; terminal = i == self.p["terminal"]
            self.reference = self.previous
            start, prior_q = self.balances(), dict(self.q)
            prior_marks = {a: self.p["bars"][i-1][a]["close"] for a in ASSETS}
            self.day_active, self.triggered = bool(any(self.q.values())), False
            if self.paused and self.cooldown >= 5 and not any(self.q.values()):
                self.paused, self.cooldown = False, 0
                self.risks.append(dict(index=i, kind="resume_only_at_next_monthly_decision"))
            carried_risk = self.risk_due is not None and self.risk_due <= i
            first_fill = len(self.fills); first_obs = len(self.observations)
            entitled = self.opening_actions()
            self.observe(self.marks("open"), "prior_held_open")
            if terminal or carried_risk:
                if self.pending: self.pending["status"] = "cancelled_by_terminal_or_prior_risk"
                self.pending = None
                self.exit_orders("terminal" if terminal else "risk_exit")
                self.risk_due = i+1 if any(self.q.values()) else None
            elif self.pending:
                event = self.pending
                if i == event["sell_index"]:
                    for o in event["sell_orders"]: self.fill(o)
                if i == event["buy_index"]:
                    for o in event["buy_orders"]: self.fill(o)
                    if event["status"] != "cancelled_increases_by_risk": event["status"] = "completed_monthly_attempt"
                    self.pending = None
            if not any(self.q.values()) and self.risk_due is not None: self.risk_due = None
            marks = self.marks("open" if terminal else "close")
            nav = self.observe(marks, "terminal_open_end" if terminal else "completed_close")
            if not terminal:
                no_increase = self.pending is None or not any(o["quantity"] for o in self.pending.get("buy_orders", []))
                if self.paused:
                    self.cooldown = self.cooldown+1 if not self.day_active and not self.triggered and no_increase and not any(self.q.values()) else 0
                if self.pending and i == self.pending["plan_index"]: self.plan_buys(self.pending)
            fills = self.fills[first_fill:]
            attribution = dict(carried_exposure=sum((prior_q[a]*(marks[a]-prior_marks[a]) for a in ASSETS), ZERO),
                trade_timing=sum(((f["quantity"] if f["side"] == "buy" else -f["quantity"])*(marks[f["asset"]]-f["raw_open"]) for f in fills), ZERO),
                net_dividend_entitlement=entitled, commissions=-sum((f["fee"] for f in fills), ZERO),
                sell_levies=-sum((f["sell_levy"] for f in fills), ZERO), slippage=-sum((f["slippage_cost"] for f in fills), ZERO))
            _require(sum(attribution.values(), ZERO) == nav-self.previous, "daily_NAV_attribution_identity")
            year = self.p["dates"][i][:4]
            self.annual[year] = self.annual.get(year, ZERO)+(nav-self.previous)
            self.days.append(dict(index=i, date=self.p["dates"][i], terminal_open_only=terminal, before=start, after=self.balances(),
                previous_marks=prior_marks, marks=marks, previous_NAV=self.previous, NAV=nav, PnL=nav-self.previous,
                peak=self.peak, observed_maxDD=self.max_dd, paused=self.paused, cooldown=self.cooldown,
                risk_exit_due_index=self.risk_due, observation_range=[first_obs, len(self.observations)], attribution=attribution))
            self.previous = nav
            if not terminal and i in self.p["signals"]: self.decision(i)
        marks = self.marks("open")
        locked = sum((x["amount"] for x in self.locks), ZERO)
        receivable = sum((x["amount"] for x in self.receivables.values()), ZERO)
        inventory = sum((self.q[a]*marks[a] for a in ASSETS), ZERO)
        elapsed = (date.fromisoformat(self.p["dates"][self.p["terminal"]])-date.fromisoformat(self.p["dates"][self.p["first"]])).days
        cagr = (self.previous/INITIAL)**(D("365.25")/elapsed)-1
        attrs = {k: sum((d["attribution"][k] for d in self.days), ZERO) for k in self.days[0]["attribution"]}
        _require(sum(attrs.values(), ZERO) == self.previous-INITIAL and sum(self.annual.values(), ZERO) == self.previous-INITIAL, "whole_account_reconciliation")
        summary = dict(initial_cash=INITIAL, terminal_book_NAV=self.previous, terminal_book_cash=self.cash+locked,
            terminal_spendable_cash=self.cash, terminal_locked_cash=locked, terminal_receivables=receivable,
            terminal_inventory_value=inventory, terminal_quantities=self.q,
            terminal_book_net_profit=self.previous-INITIAL, terminal_cash_only_net_profit=self.cash+locked-INITIAL,
            terminal_spendable_cash_net_profit=self.cash-INITIAL,
            terminal_cash_only_definition="includes contracted locked sale proceeds; excludes dividend receivables and remaining inventory; not immediately withdrawable cash",
            terminal_inventory_closed=not any(self.q.values()), terminal_fully_settled=not any(self.q.values()) and not self.locks and not self.receivables,
            observed_maxDD=self.max_dd, book_CAGR=cagr, CAGR_years=D(elapsed)/D("365.25"),
            total_commission=self.total_fee, total_sell_levy=self.total_levy, total_slippage=self.total_slip,
            total_net_dividend=self.total_net_dividend, same_path_trading_cost_drag=self.total_fee+self.total_levy+self.total_slip,
            same_path_before_trading_cost_net_profit=self.previous-INITIAL+self.total_fee+self.total_levy+self.total_slip,
            cost_headroom_meaning="accounting attribution on the same trades, not a fee-reoptimized portfolio",
            fills=len(self.fills), rejections=len(self.rejections), accounting_reconciled=True, qualified=False)
        return dict(policy=self.policy, cost_id=f"min{self.minimum}_slip{self.slip}", minimum_commission=self.minimum,
            slippage_bps=self.slip, commission_per_share=".005", sell_levy_bps="5", summary=summary,
            days=self.days, fills=self.fills, intents=self.intents, signals=list(self.p["signals"].values()),
            monthly_events=self.events, actions=self.actions, rejections=self.rejections, risk_records=self.risks,
            risk_observations=self.observations, unknown_execution_constraints=self.unknowns, annual_contributions=self.annual,
            attribution=attrs, terminal_locks=self.locks, terminal_receivable_items=self.receivables,
            pending=self.pending, FIFO_lots=self.lots)


def run_prepared(prepared, policy, minimum, slip, *, context):
    _require(type(context) is _ExecutionContext and type(prepared) is Prepared
             and prepared.fixture_sha256 == context.fixture_sha256
             and digest(prepared.normalized) == prepared.normalized_sha256, "prepared_context_binding")
    with localcontext(CONTEXT) as ctx:
        ctx.clear_flags(); initial = context_record(ctx)
        result = _Account(prepared, policy, minimum, slip).run()
        _require(digest(prepared.normalized) == prepared.normalized_sha256, "prepared_input_changed_during_run")
        result.update(schema="us_monthly_rotation_account_v1", evidence_kind=context.output_kind,
            historical_returns_computed=context.historical, test_injected_values=context.test_values,
            qualified=False, real_forward=0, method_sha256=METHOD_SHA, fixture_sha256=context.fixture_sha256,
            provenance_sha256=context.provenance_sha256, registration_sha256=context.registration_sha256,
            runtime=dict(module_file=str(Path(__file__).resolve()), module_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         context_initial=initial, context_final=context_record(ctx)))
        return serial(result)


def run_artificial(fixture, policy="rotation", minimum="1.00", slip=10):
    _require(fixture.get("evidence_kind") == "artificial", "public_artificial_only")
    context = _ExecutionContext("artificial", METHOD_SHA, digest(fixture), digest(fixture["provenance"]))
    return run_prepared(prepare(fixture, context=context), policy, minimum, slip, context=context)


def fixed_statistics(annual_by_cost, *, context):
    import numpy as np
    _require(type(context) is _ExecutionContext, "statistics_context_required")
    with localcontext(CONTEXT):
        years, columns, keys = None, [], []
        for minimum, slip in COSTS:
            key = f"min{minimum}_slip{slip}"; group = annual_by_cost[key]
            current = sorted(group["rotation"])
            years = current if years is None else years
            _require(all(sorted(group[p]) == years for p in POLICIES), "paired_annual_years")
            for endpoint, baseline in (("net", None), ("minus_positive_equal", "positive_equal"), ("minus_fixed_quarters", "fixed_quarters")):
                keys.append(key+"/"+endpoint)
                columns.append([float(D(group["rotation"][y])-(D(group[baseline][y]) if baseline else ZERO)) for y in years])
        if len(years) != 19: return dict(status="not_computed_requires19years", annual_years=years, qualified=False)
        if context.historical: _require(years == [str(y) for y in range(2006, 2025)], "fixed_historical_annual_years")
        matrix = np.asarray(columns, dtype="float64").T
        _require(matrix.shape == (19, 27) and bool(np.isfinite(matrix).all()), "finite19by27matrix")
        rng = np.random.Generator(np.random.PCG64(20261107)); means = np.empty((5000, 27), dtype="float64")
        for i in range(5000):
            starts = rng.integers(0, 19, size=10)
            indices = ((starts[:, None]+np.arange(2)) % 19).reshape(-1)[:19]
            means[i] = matrix[indices].mean(axis=0)
        intervals = np.quantile(means, [.025, .975], axis=0, method="linear")
        _require(bool(np.isfinite(intervals).all()), "finite_bootstrap")
        return dict(status="computed_seen_trace_sensitivity", evidence_kind=context.output_kind,
            historical_returns_computed=context.historical, qualified=False, N=19, years=years, block=2,
            seed=20261107, generator="PCG64", replications=5000, starts_per_replication=10, truncate_rows_to=19,
            shared_indices_for_all27=True, endpoint_keys=keys, units="USD_per_observed_year", statistic="arithmetic_mean_annual_PnL",
            lower=dict(zip(keys, intervals[0].tolist())), upper=dict(zip(keys, intervals[1].tolist())),
            observed_means=dict(zip(keys, matrix.mean(axis=0).tolist())), quantiles=[.025, .975], quantile_method="linear",
            replicate_means_sha256=hashlib.sha256(means.astype("<f8").tobytes()).hexdigest(), numpy_version=np.__version__)
