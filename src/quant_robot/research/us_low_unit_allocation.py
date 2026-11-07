"""Fixed old/new whole-share allocation; pure conditional ledger, no IO.

The sibling ledger preserves the previous monthly arithmetic while adding an
explicit asset tuple, conservative nominal capacity and a reverse-split event.
Its external controller exclusively owns source and numeric authorization.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal as D, localcontext, ROUND_FLOOR, ROUND_CEILING

from quant_robot.research.us_monthly_rotation import (
    CONTEXT, ZERO, CENT, INITIAL, BUFFER, _price, _fee, _floor,
    _require, serial, digest, context_record,
)

OLD_ASSETS = ("SPY", "EFA", "IEF", "GLD")
NEW_ASSETS = ("SPYM", "EFA", "IEF", "GLDM")
ROLES = ("old_primary", "old_stress", "new_primary", "new_stress", "cash")
NUMBER = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z")


def _number(value, *, positive=False):
    _require(type(value) is str and NUMBER.fullmatch(value), "strict_decimal_string")
    result = D(value)
    _require(result.is_finite() and (result > 0 if positive else result >= 0), "decimal_domain")
    return result


def _hex(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


@dataclass(frozen=True)
class Prepared:
    assets: tuple[str, ...]
    role: str
    normalized: dict
    normalized_sha256: str


def prepare(fixture, role, *, historical=False):
    """Pure validation; caller must have obtained permission before decoding."""
    with localcontext(CONTEXT):
        _require(role in ROLES and type(historical) is bool, "fixed_role")
        _require(fixture.get("currency", "USD") == "USD", "USD_only")
        assets = NEW_ASSETS if role.startswith("new_") else OLD_ASSETS
        _require(fixture.get("assets") == list(assets), "real_asset_identity")
        rows = fixture["days"]
        dates = [r["date"] for r in rows]
        _require(len(dates) >= 30 and dates == sorted(set(dates)), "ordered_dates")
        parsed = [date.fromisoformat(d) for d in dates]
        _require(all(d.isoformat() == text for d, text in zip(parsed, dates)), "canonical_dates")
        first = dates.index(fixture["first_decision_date"])
        terminal = dates.index(fixture["terminal_date"])
        _require(first >= 20 and first + 4 < terminal == len(rows)-1, "warmup_terminal")
        if historical:
            _require(dates[0] == "2020-12-01" and dates[first] == "2020-12-31"
                     and dates[-1] == "2025-12-31", "fixed_2021_2025_window")
            _require(fixture.get("evidence_kind") == "known_history_conditional"
                     and fixture.get("provenance", {}).get("constructed_from_market_data") is True,
                     "historical_identity")
        else:
            _require(all(2000 <= d.year <= 2004 for d in parsed), "artificial_years_only")
            _require(fixture.get("provenance", {}).get("constructed_from_market_data", False) is False,
                     "artificial_values_only")
        month_ends = [i for i in range(terminal) if dates[i][:7] != dates[i+1][:7]]
        _require(first in month_ends and all(d[:7] == dates[first][:7] for d in dates[:first+1]),
                 "one_month_capacity_warmup")
        endpoints = [i for i in month_ends if i >= first]
        serials = [parsed[i].year*12+parsed[i].month for i in endpoints]
        _require(all(b-a == 1 for a, b in zip(serials, serials[1:])), "consecutive_months")
        if historical:
            _require(len(endpoints) == 60 and dates[endpoints[-1]][:7] == "2025-11", "sixty_decisions")
        bars, execution, cap_volumes = [], [], []
        for i, row in enumerate(rows):
            _require(set(row["prices"]) == set(assets)
                     and set(row["capacity_volume"]) == set(assets), "same_asset_rows")
            new, cap = {}, {}
            for a in assets:
                values = row["prices"][a]
                new[a] = {"open": _number(values["open"], positive=True)}
                if i == terminal:
                    _require(row.get("terminal_open_only") is True
                             and all(values.get(k) is None for k in ("high", "low", "close", "volume"))
                             and row["capacity_volume"][a] is None, "terminal_open_only")
                    new[a].update({k: None for k in ("high", "low", "close", "volume")})
                    cap[a] = None
                else:
                    new[a].update({k: _number(values[k], positive=k != "volume")
                                   for k in ("high", "low", "close", "volume")})
                    cap[a] = _number(row["capacity_volume"][a])
                    _require(new[a]["low"] <= min(new[a]["open"], new[a]["close"])
                             <= max(new[a]["open"], new[a]["close"]) <= new[a]["high"], "OHLC_rectangle")
            flags = row.get("execution", {a: dict(suspended=None, buy_blocked=None, sell_blocked=None)
                                           for a in assets})
            _require(set(flags) == set(assets), "execution_assets")
            _require(all(set(f) == {"suspended", "buy_blocked", "sell_blocked"}
                         and all(v is None or type(v) is bool for v in f.values())
                         for f in flags.values()), "explicit_execution_flags")
            bars.append(new); cap_volumes.append(cap); execution.append(copy.deepcopy(flags))
        dividends, splits, ids = [], [], set()
        for item in fixture["dividends"]:
            _require(type(item["id"]) is str and item["id"] not in ids
                     and item["symbol"] in assets and item["ex_date"] in dates, "dividend_identity")
            ids.add(item["id"])
            index = dates.index(item["ex_date"])
            _require(first < index <= terminal, "no_warmup_dividend_right")
            dividends.append(dict(id=item["id"], symbol=item["symbol"], ex_index=index,
                amount_per_share=_number(item["amount_per_share"]),
                earliest_payment_date=(date.fromisoformat(item["ex_date"])+timedelta(days=45)).isoformat()))
        for item in fixture["splits"]:
            _require(type(item["id"]) is str and item["id"] not in ids and "GLDM" in assets
                     and item["symbol"] == "GLDM" and item["effective_date"] in dates
                     and type(item["numerator"]) is int and item["numerator"] == 1
                     and type(item["denominator"]) is int and item["denominator"] == 2,
                     "fixed_reverse_split")
            ids.add(item["id"])
            index = dates.index(item["effective_date"])
            _require(first < index <= terminal, "split_in_account_window")
            if historical:
                _require(item["effective_date"] == "2022-02-23", "split_effective_date")
            splits.append(dict(item, index=index, ratio=D(".5")))
        _require(len(splits) <= 1, "single_confirmed_split")
        if historical:
            _require(len(splits) == (1 if assets == NEW_ASSETS else 0), "complete_fixed_split_identity")
        signals = {i: dict(index=i, date=dates[i], weights={"fixed_quarters": dict.fromkeys(assets, D(".25"))},
                           ordinary_execution_possible=i+4 < terminal) for i in endpoints}
        normalized = dict(dates=dates, bars=bars, execution=execution, capacity_volume=cap_volumes,
                          dividends=dividends, splits=splits, signals=signals, first=first, terminal=terminal)
        return Prepared(assets, role, normalized, digest(normalized))


class _Account:
    def __init__(self, prepared, policy, minimum, slip):
        _require(policy in ("fixed_quarters", "cash") and type(minimum) is str and type(slip) is int
                 and (minimum, slip) in (("1.00",10),("2.50",30),("0.35",0)), "fixed_policy_cost_identity")
        self.p = prepared.normalized
        self.assets, self.role = prepared.assets, prepared.role
        self.cil_delay = 90 if self.role.endswith("stress") else 45
        self.total_cil_cost = ZERO
        self.split_factors = dict.fromkeys(self.assets, D(1))
        self.day_cil = []
        self.policy, self.minimum, self.slip = policy, minimum, slip
        self.cash, self.q, self.locks, self.receivables = INITIAL, dict.fromkeys(self.assets, 0), [], {}
        self.peak = self.reference = self.previous = INITIAL
        self.previous_dd = self.max_dd = ZERO
        self.paused, self.cooldown, self.risk_due = False, 0, None
        self.pending = None
        self.days, self.fills, self.intents, self.rejections, self.risks, self.actions, self.events = [], [], [], [], [], [], []
        self.observations, self.unknowns, self.annual = [], [], {}
        self.lots = {a: [] for a in self.assets}
        self.total_fee = self.total_levy = self.total_slip = self.total_net_dividend = ZERO
        self.i = self.p["first"]
        self.day_active = self.triggered = False

    def balances(self):
        return dict(spendable_cash=self.cash, locked_cash=sum((x["amount"] for x in self.locks), ZERO),
                    locks=copy.deepcopy(self.locks), quantities=dict(self.q), receivables=copy.deepcopy(self.receivables))

    def marks(self, field):
        return {a: self.p["bars"][self.i][a][field] for a in self.assets}

    def nav(self, marks):
        return self.cash+sum((x["amount"] for x in self.locks), ZERO)+sum((x["amount"] for x in self.receivables.values()), ZERO)+sum((self.q[a]*marks[a] for a in self.assets), ZERO)

    def capacity(self, a, before):
        _require(before >= 20, "twenty_completed_volume_days")
        price = self.p["bars"][before-1][a]["close"]
        if before == self.i:
            price /= self.split_factors[a]
        return _floor(self.capacity_notional(a, before)/price)

    def capacity_notional(self, a, before):
        _require(before >= 20, "twenty_completed_volume_days")
        return sum((self.p["bars"][j][a]["close"]*self.p["capacity_volume"][j][a]
                    for j in range(before-20, before)), ZERO)/20*D(".01")

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
                kind = "cash_in_lieu_payment" if item.get("kind") == "cash_in_lieu" else "dividend_payment"
                self.actions.append(dict(index=self.i, kind=kind, id=key, item=item, before=before, after=self.balances()))
        self.apply_splits()
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

    def apply_splits(self):
        """Mechanical unit transition and an explicitly modeled CIL receivable."""
        for event in self.p["splits"]:
            if event["index"] != self.i:
                continue
            a, ratio = event["symbol"], event["ratio"]
            before = self.balances()
            total_right = D(self.q[a])*ratio
            whole = _floor(total_right)
            fraction = total_right-whole
            self.split_factors[a] *= ratio
            self.q[a] = whole
            for lot in self.lots[a]:
                lot["initial"] = D(lot["initial"])*ratio
                lot["remaining"] = D(lot["remaining"])*ratio
            # Deemed fractional disposal uses oldest FIFO units; exchange
            # orders remain whole shares even when individual lots are not.
            left, released_cost, fifo = fraction, ZERO, []
            for lot in self.lots[a]:
                take = min(left, lot["remaining"])
                if not take:
                    continue
                basis = (lot["remaining_cost"] if take == lot["remaining"]
                         else lot["remaining_cost"]*take/lot["remaining"])
                lot["remaining"] -= take; lot["remaining_cost"] -= basis
                left -= take; released_cost += basis
                fifo.append(dict(buy_index=lot["index"], quantity=take, released_cost=basis))
                if not left:
                    break
            _require(left == 0 and sum((x["remaining"] for x in self.lots[a]), ZERO) == whole,
                     "split_FIFO_quantity")
            pending_before = copy.deepcopy(self.pending)
            if self.pending:
                if a in self.pending["targets"]:
                    self.pending["targets"][a] = _floor(D(self.pending["targets"][a])*ratio)
                for orders_key in ("sell_orders", "buy_orders"):
                    for order in self.pending.get(orders_key, []):
                        if order["asset"] == a:
                            order["quantity"] = _floor(D(order["quantity"])*ratio)
                            order["capacity"] = _floor(D(order["capacity"])*ratio)
                            order["planned_price"] /= ratio
                            if "capacity_reference_price" in order:
                                order["capacity_reference_price"] /= ratio
                            order["split_adjusted_at"] = self.i
            raw = self.p["bars"][self.i][a]["open"]
            price = _price(raw, "sell", self.slip)
            gross = fraction*price
            fee = _fee(fraction, self.minimum) if fraction else ZERO
            levy = (gross*D(".0005")).quantize(CENT, rounding=ROUND_CEILING) if fraction else ZERO
            net = max(ZERO, gross-fee-levy).quantize(CENT, rounding=ROUND_FLOOR)
            cost = fraction*raw-net
            self.total_cil_cost += cost
            record = dict(index=self.i, id=event["id"], asset=a, ratio=ratio,
                          old_quantity=before["quantities"][a], total_right=total_right,
                          whole_quantity=whole, fractional_right=fraction, raw_open=raw,
                          modeled_price=price, modeled_gross=gross, assessed_fee=fee,
                          assessed_levy=levy, modeled_net=net, NAV_cost=cost,
                          assessed_cost_above_gross=max(ZERO, fee+levy-gross),
                          FIFO=fifo, released_fraction_cost=released_cost,
                          payment_delay_calendar_days=self.cil_delay,
                          pending_before=pending_before, pending_after=copy.deepcopy(self.pending))
            if fraction:
                key = "cil:"+event["id"]
                _require(key not in self.receivables, "unique_CIL_right")
                payment = (date.fromisoformat(self.p["dates"][self.i])
                           +timedelta(days=self.cil_delay)).isoformat()
                self.receivables[key] = dict(kind="cash_in_lieu", symbol=a, amount=net,
                    fractional_right=fraction, earliest_payment_date=payment,
                    valuation_clock="effective_session_open", official_payment_verified=False)
                record["receivable_id"] = key
                record["earliest_payment_date"] = payment
            self.day_cil.append(record)
            self.actions.append(dict(index=self.i, kind="reverse_split_cash_in_lieu", item=record,
                                     before=before, after=self.balances()))

    def decision(self, index):
        signal = self.p["signals"][index]
        event = dict(decision_index=index, date=self.p["dates"][index], signal=copy.deepcopy(signal),
                     policy=self.policy, status="created", targets={}, sell_orders=[], buy_orders=[])
        self.events.append(event)
        if self.policy == "cash" or self.paused or self.risk_due is not None or not signal["ordinary_execution_possible"]:
            event["status"] = "skipped_cash_risk_or_terminal"; return
        _require(self.pending is None, "overlapping_monthly_plan")
        nav = self.previous
        targets = {a: _floor(max(nav-BUFFER, ZERO)*signal["weights"][self.policy][a]/self.p["bars"][index][a]["close"]) for a in self.assets}
        event.update(targets=targets, decision_NAV=nav, sell_index=index+1, plan_index=index+3, buy_index=index+4,
                     status="sell_intents_frozen", pre_decision_balances=self.balances())
        for a in self.assets:
            cap = self.capacity(a, index+1)
            event["sell_orders"].append(dict(asset=a, side="sell", quantity=min(max(self.q[a]-targets[a], 0), cap),
                capacity=cap, capacity_notional=self.capacity_notional(a, index+1),
                capacity_reference_price=self.p["bars"][index][a]["close"],
                planned_price=self.p["bars"][index][a]["close"], phase="monthly_sell", budget=None,
                planned_index=index, due_index=index+1))
        self.pending = event

    def plan_buys(self, event):
        if self.paused or self.risk_due is not None:
            event["status"] = "cancelled_increases_by_risk"; event["buy_orders"] = []; return
        due = sum((x["amount"] for x in self.locks if x["release_index"] <= self.i+1), ZERO)
        available = max(self.cash+due-BUFFER, ZERO)
        needs, costs, prices = {}, {}, {}
        for a in self.assets:
            needs[a] = min(max(event["targets"][a]-self.q[a], 0), self.capacity(a, self.i+1))
            prices[a] = _price(self.p["bars"][self.i][a]["close"], "buy", self.slip)
            costs[a] = needs[a]*prices[a]+_fee(needs[a], self.minimum) if needs[a] else ZERO
        total = sum(costs.values(), ZERO)
        orders = []
        for a in self.assets:
            budget = (available*costs[a]/total).quantize(CENT, rounding=ROUND_FLOOR) if total else ZERO
            cap = _floor(self.capacity_notional(a, self.i+1)/prices[a])
            q = min(needs[a], cap, _floor(budget/prices[a]))
            while q and q*prices[a]+_fee(q, self.minimum) > budget: q -= 1
            orders.append(dict(asset=a, side="buy", quantity=q, capacity=cap,
                capacity_notional=self.capacity_notional(a, self.i+1),
                capacity_reference_price=prices[a],
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
        elif q*raw > order["capacity_notional"]: reason = "frozen_nominal_capacity"
        elif side == "buy" and self.paused: reason = "risk_cancelled_increase"
        elif side == "buy" and (notional+fee > order["budget"] or notional+fee > self.cash): reason = "frozen_budget_or_spendable_cash"
        elif side == "sell" and q > self.q[a]: reason = "quantity_no_longer_available"
        elif side == "sell" and notional-fee-levy < -self.cash: reason = "free_cash_insufficient_exit_fee"
        if side == "buy" and reason is None:
            marks = self.marks("open")
            after_exposure = sum((self.q[s]*marks[s] for s in self.assets), ZERO)+q*raw
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
        for a in self.assets:
            self.fill(dict(asset=a, side="sell", quantity=min(self.q[a], self.capacity(a, self.i)),
                capacity=self.capacity(a, self.i), capacity_notional=self.capacity_notional(a, self.i),
                capacity_reference_price=self.p["bars"][self.i-1][a]["close"]/self.split_factors[a],
                planned_price=self.p["bars"][self.i-1][a]["close"]/self.split_factors[a],
                phase=phase, budget=None, planned_index=self.i-1, due_index=self.i))

    def run(self):
        self.decision(self.p["first"])
        for i in range(self.p["first"]+1, self.p["terminal"]+1):
            self.i = i; terminal = i == self.p["terminal"]
            self.split_factors = dict.fromkeys(self.assets, D(1))
            self.day_cil = []
            self.reference = self.previous
            start, prior_q = self.balances(), dict(self.q)
            prior_marks = {a: self.p["bars"][i-1][a]["close"] for a in self.assets}
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
            attribution = dict(carried_exposure=sum((prior_q[a]*(self.split_factors[a]*marks[a]-prior_marks[a]) for a in self.assets), ZERO),
                trade_timing=sum(((f["quantity"] if f["side"] == "buy" else -f["quantity"])*(marks[f["asset"]]-f["raw_open"]) for f in fills), ZERO),
                cash_in_lieu_timing=-sum((x["fractional_right"]*(marks[x["asset"]]-x["raw_open"]) for x in self.day_cil), ZERO),
                cash_in_lieu_cost=-sum((x["NAV_cost"] for x in self.day_cil), ZERO),
                net_dividend_entitlement=entitled, commissions=-sum((f["fee"] for f in fills), ZERO),
                sell_levies=-sum((f["sell_levy"] for f in fills), ZERO), slippage=-sum((f["slippage_cost"] for f in fills), ZERO))
            _require(sum(attribution.values(), ZERO) == nav-self.previous, "daily_NAV_attribution_identity")
            year = self.p["dates"][i][:4]
            self.annual[year] = self.annual.get(year, ZERO)+(nav-self.previous)
            self.days.append(dict(index=i, date=self.p["dates"][i], terminal_open_only=terminal, before=start, after=self.balances(),
                previous_marks=prior_marks, marks=marks, previous_NAV=self.previous, NAV=nav, PnL=nav-self.previous,
                split_factors=dict(self.split_factors),
                peak=self.peak, observed_maxDD=self.max_dd, paused=self.paused, cooldown=self.cooldown,
                risk_exit_due_index=self.risk_due, observation_range=[first_obs, len(self.observations)], attribution=attribution))
            self.previous = nav
            if not terminal and i in self.p["signals"]: self.decision(i)
        marks = self.marks("open")
        locked = sum((x["amount"] for x in self.locks), ZERO)
        receivable = sum((x["amount"] for x in self.receivables.values()), ZERO)
        inventory = sum((self.q[a]*marks[a] for a in self.assets), ZERO)
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
        summary.update(total_cash_in_lieu_cost=self.total_cil_cost,
            terminal_settled_cash=self.cash, strict_available_cash=self.cash,
            terminal_dividend_receivable=sum((x["amount"] for x in self.receivables.values()
                                               if x.get("kind") != "cash_in_lieu"), ZERO),
            terminal_cash_in_lieu_receivable=sum((x["amount"] for x in self.receivables.values()
                                                   if x.get("kind") == "cash_in_lieu"), ZERO),
            cash_and_locked_sale_proceeds_net_profit=self.cash+locked-INITIAL,
            withdrawal_clock_verified=False,
            same_path_total_execution_cost=self.total_fee+self.total_levy+self.total_slip+self.total_cil_cost,
            average_cash_and_locked_ratio=sum(((d["after"]["spendable_cash"]+d["after"]["locked_cash"])/d["NAV"]
                                               for d in self.days), ZERO)/len(self.days),
            average_market_deployment_ratio=sum((sum((d["after"]["quantities"][a]*d["marks"][a]
                                                       for a in self.assets), ZERO)/d["NAV"]
                                                  for d in self.days), ZERO)/len(self.days),
            asset_unheld_days={a: sum(d["after"]["quantities"][a] == 0 for d in self.days) for a in self.assets},
            zero_target_legs=sum(q == 0 for e in self.events for q in e["targets"].values()),
            cash_in_lieu_scenario="effective_open_adverse_net_nonnegative_"+str(self.cil_delay)+"_calendar_days")
        return dict(policy=self.policy, cost_id=f"min{self.minimum}_slip{self.slip}", minimum_commission=self.minimum,
            slippage_bps=self.slip, commission_per_share=".005", sell_levy_bps="5", summary=summary,
            days=self.days, fills=self.fills, intents=self.intents, signals=list(self.p["signals"].values()),
            monthly_events=self.events, actions=self.actions, rejections=self.rejections, risk_records=self.risks,
            risk_observations=self.observations, unknown_execution_constraints=self.unknowns, annual_contributions=self.annual,
            attribution=attrs, terminal_locks=self.locks, terminal_receivable_items=self.receivables,
            pending=self.pending, FIFO_lots=self.lots)


def _run(fixture, role, *, historical, method_sha256=None,
         registration_sha256=None, numeric_marker_sha256=None):
    with localcontext(CONTEXT) as ctx:
        ctx.clear_flags()
        initial_context = context_record(ctx)
        fixture_sha = digest(fixture)
        prepared = prepare(fixture, role, historical=historical)
        if role == "cash":
            policy, minimum, slip = "cash", "0.35", 0
        else:
            policy = "fixed_quarters"
            minimum, slip = ("2.50", 30) if role.endswith("stress") else ("1.00", 10)
        result = _Account(prepared, policy, minimum, slip).run()
        _require(digest(fixture) == fixture_sha
                 and digest(prepared.normalized) == prepared.normalized_sha256, "immutable_input")
        result.update(schema="us_low_unit_allocation_account_v1", role=role,
            assets=list(prepared.assets), evidence_kind="known_history_conditional" if historical else "artificial",
            historical_returns_computed=historical, test_injected_values=not historical,
            qualified=False, real_forward=0, fixture_sha256=fixture_sha,
            method_sha256=method_sha256, registration_sha256=registration_sha256,
            numeric_marker_sha256=numeric_marker_sha256,
            capacity_basis="previous20completed_lower_two_convention_nominal_mean_one_percent",
            runtime_context=dict(initial=initial_context, final=context_record(ctx)))
        return serial(result)


def run_artificial(fixture, role="new_primary"):
    """Only invented values on years2000..2004, never source or account IO."""
    return _run(fixture, role, historical=False)


def run_known_history(fixture, role, *, method_sha256, registration_sha256, numeric_marker_sha256):
    """Already-decoded fixed input; hashes record the external controller's claim.

    This pure entry does not grant permission or authenticate a release. The
    controller validates the release and writes its durable marker before any
    financial conversion, then passes precisely this immutable decoded fixture.
    """
    _require(all(_hex(x) for x in (method_sha256, registration_sha256, numeric_marker_sha256)),
             "external_numeric_claim_hashes")
    return _run(fixture, role, historical=True, method_sha256=method_sha256,
                registration_sha256=registration_sha256, numeric_marker_sha256=numeric_marker_sha256)

