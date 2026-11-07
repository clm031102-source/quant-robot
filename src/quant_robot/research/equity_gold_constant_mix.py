"""Artificial-only constant-mix ledger. No market, broker or admission interface."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from datetime import date, timedelta
from decimal import (Decimal, Context, localcontext, ROUND_HALF_UP, ROUND_CEILING,
                     ROUND_FLOOR, InvalidOperation, DivisionByZero, Overflow)
from pathlib import Path

ASSETS = ("ARTIFICIAL_EQUITY", "ARTIFICIAL_GOLD")
SOURCE = "artificial_generated_not_market_data"
METHOD_SHA = "08c3b31007598c339ef679ca0f3fb7bb022a9116789b8724c59f2b1bd51bb5c5"
ZERO, CENT, TICK = Decimal(0), Decimal(".01"), Decimal(".001")
CONTEXT = Context(prec=40, rounding=ROUND_HALF_UP, Emin=-999999, Emax=999999,
                  capitals=1, clamp=0)
for _signal in CONTEXT.traps:
    CONTEXT.traps[_signal] = _signal in (InvalidOperation, DivisionByZero, Overflow)
CONTEXT.clear_flags()
COSTS = tuple((minimum, slip) for minimum in (0, 5, 10) for slip in (0, 10, 30))


def _number(x):
    if isinstance(x, bool) or not isinstance(x, (str, int, Decimal)):
        raise ValueError("exact_decimal_string_or_integer_required")
    try:
        value = Decimal(x)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid_decimal") from exc
    if not value.is_finite() or abs(value) > Decimal("1e12"):
        raise ValueError("finite_bounded_artificial_number_required")
    if len(value.as_tuple().digits) > 28:
        raise ValueError("artificial_numeric_precision_exceeded")
    return value


def _integer(x):
    if type(x) is not int or x < 0:
        raise ValueError("nonnegative_integer_required")
    return x


def _json(x):
    if isinstance(x, Decimal):
        return str(x)
    if isinstance(x, dict):
        return {k: _json(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [_json(v) for v in x]
    return x


def digest(x):
    return hashlib.sha256(json.dumps(_json(x), sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _context_record(ctx):
    return dict(prec=ctx.prec, rounding=ctx.rounding, Emin=ctx.Emin, Emax=ctx.Emax,
                capitals=ctx.capitals, clamp=ctx.clamp,
                traps={k.__name__: v for k, v in ctx.traps.items()},
                flags={k.__name__: v for k, v in ctx.flags.items()})


def _fee(value, minimum):
    return max(Decimal(minimum), value * Decimal(".0005")).quantize(CENT)


def _price(raw, side, slip):
    factor = 1 + Decimal(slip) / 10000 * (1 if side == "buy" else -1)
    return (raw * factor).quantize(TICK, rounding=ROUND_CEILING if side == "buy" else ROUND_FLOOR)


def _floor_lot(x):
    return max(0, int(x // 100) * 100)


def _reserve(equity):
    return 4 * max(Decimal(10), Decimal(".0005") * max(equity, ZERO)).quantize(CENT, rounding=ROUND_CEILING)


def _prepare(fixture):
    if (fixture.get("artifact_type") != "artificial_constant_mix_fixture_v1"
            or fixture.get("source_nature") != SOURCE
            or fixture.get("assets") != list(ASSETS)
            or fixture.get("constructed_from_market_data") is not False):
        raise ValueError("artificial_identity_required")
    dates = fixture["dates"]
    if (not isinstance(dates, list) or len(dates) < 23 or len(dates) > 4000
            or dates != sorted(set(dates))):
        raise ValueError("unique_ordered_artificial_calendar_required")
    for value in dates:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value or not 2000 <= parsed.year <= 2011:
            raise ValueError("artificial_2000_to_2011_calendar_only")
    terminal = _integer(fixture["terminal_index"])
    events = fixture["event_indices"]
    if terminal >= len(dates) or not events or events != sorted(set(events)):
        raise ValueError("terminal_and_unique_events_required")
    for index in events:
        _integer(index)
        if not 20 <= index < terminal:
            raise ValueError("event_needs_twenty_prior_sessions_and_successor")
    if any(b - a < 2 for a, b in zip(events, events[1:])):
        raise ValueError("overlapping_two_phase_events")
    bars = {}
    if set(fixture["bars"]) != set(ASSETS):
        raise ValueError("artificial_asset_set_required")
    for asset in ASSETS:
        rows = fixture["bars"][asset]
        if len(rows) != terminal + 1:
            raise ValueError("complete_price_calendar_exactly_through_terminal_required")
        bars[asset] = []
        for row in rows:
            new = {k: _number(row[k]) for k in ("open", "close", "volume")}
            if min(new["open"], new["close"]) <= 0 or new["volume"] < 0:
                raise ValueError("positive_price_nonnegative_volume_required")
            for k in ("suspended", "buy_blocked", "sell_blocked"):
                if k not in row or (row[k] is not None and type(row[k]) is not bool):
                    raise ValueError("explicit_execution_constraint_required")
                new[k] = row[k]
            bars[asset].append(new)
    actions, seen = [], set()
    for action in fixture.get("actions", []):
        a = copy.deepcopy(action)
        if a["event_id"] in seen or a["asset"] not in ASSETS:
            raise ValueError("unique_action_asset_required")
        seen.add(a["event_id"])
        for k in ("known_index", "record_index", "ex_index", "pay_index"):
            if _integer(a[k]) >= len(dates):
                raise ValueError("action_date_not_in_explicit_calendar")
        if not a["known_index"] <= a["record_index"] < a["ex_index"] <= a["pay_index"]:
            raise ValueError("explicit_known_record_ex_pay_sequence_required")
        if _number(a.get("share_multiplier", "0")) != 1:
            raise ValueError("share_conversion_not_supported_by_cash_only_contract")
        a["cash_per_share"] = _number(a["cash_per_share"])
        if a["cash_per_share"] < 0:
            raise ValueError("negative_distribution")
        actions.append(a)
    return dict(dates=dates, bars=bars, events=events, terminal=terminal,
                first=events[0], actions=actions, fixture_sha256=digest(fixture))


def validate_synthetic_fixture(fixture):
    with localcontext(CONTEXT):
        p = _prepare(fixture)
        return dict(valid=True, source_nature=SOURCE, financial_values_read=False,
                    dates=len(p["dates"]), fixture_sha256=p["fixture_sha256"])


class _Account:
    def __init__(self, prepared, policy, minimum, slip):
        if policy not in ("constant_mix", "drift", "cash") or (minimum, slip) not in COSTS:
            raise ValueError("fixed_policy_and_nine_cost_identity_required")
        self.p, self.policy, self.minimum, self.slip = prepared, policy, minimum, slip
        self.cash, self.unavailable = Decimal(10000), ZERO
        self.q = dict.fromkeys(ASSETS, 0)
        self.rights, self.receivables = {}, {}
        self.peak = self.previous = Decimal(10000)
        self.max_dd = ZERO
        self.paused, self.mandatory, self.flat_index = False, False, None
        self.pending = None
        self.fills, self.intents, self.rejections, self.risks, self.action_log = [], [], [], [], []
        self.events, self.days, self.cap_failures, self.unknowns = [], [], [], []
        self.lots = {a: [] for a in ASSETS}
        self.completed_lots, self.completed_cycles = 0, 0
        self.cycle_active = False
        self.initial_snapshot, self.annual = None, {}
        self.total_fees = self.total_slip = ZERO
        self.i = prepared["first"]

    def marks(self, index, field):
        return {a: self.p["bars"][a][index][field] for a in ASSETS}

    def nav(self, marks):
        return self.cash + sum((x["amount"] for x in self.receivables.values()), ZERO) + sum((self.q[a] * marks[a] for a in ASSETS), ZERO)

    def capacity(self, asset, index):
        return _floor_lot(sum((x["volume"] for x in self.p["bars"][asset][index-20:index]), ZERO) / 20 * Decimal(".01"))

    def balances(self):
        return dict(book_cash=self.cash, spendable_cash=self.cash-self.unavailable,
                    locked_sale_cash=self.unavailable, quantities=dict(self.q),
                    rights=copy.deepcopy(self.rights), receivables=copy.deepcopy(self.receivables))

    def reject(self, asset, side, quantity, reason, phase, **extra):
        self.rejections.append(dict(index=self.i, asset=asset, side=side,
                                    quantity=quantity, reason=reason, phase=phase, **extra))

    def fill(self, asset, side, quantity, phase, budget=None):
        intent_id = len(self.intents)
        self.intents.append(dict(intent_id=intent_id, index=self.i, asset=asset, side=side,
                                 quantity=quantity, phase=phase, frozen_budget=budget,
                                 prior_close=self.p["bars"][asset][self.i-1]["close"],
                                 prior_capacity=self.capacity(asset, self.i)))
        if quantity <= 0:
            return False
        row = self.p["bars"][asset][self.i]
        if quantity % 100 or quantity > self.capacity(asset, self.i):
            raise AssertionError("illegal_predeclared_quantity")
        if row["suspended"] is True or row[side + "_blocked"] is True:
            self.reject(asset, side, quantity, "known_execution_constraint", phase)
            return False
        for flag in ("suspended", side + "_blocked"):
            if row[flag] is None:
                self.unknowns.append(dict(index=self.i, asset=asset, flag=flag, phase=phase))
        price = _price(row["open"], side, self.slip)
        if price <= 0:
            self.reject(asset, side, quantity, "nonpositive_adverse_tick_price", phase)
            return False
        notional, before = quantity * price, self.balances()
        fee = _fee(notional, self.minimum)
        fee_from_locked_sale = ZERO
        fee_from_free_cash = fee if side == "buy" else ZERO
        if side == "buy":
            cost = notional + fee
            if budget is None or cost > budget or cost > self.cash-self.unavailable:
                self.reject(asset, side, quantity, "frozen_budget_or_spendable_cash", phase,
                            frozen_budget=budget, actual_cost=cost, spendable_cash=self.cash-self.unavailable)
                return False
            marks = self.marks(self.i, "open")
            exposure_after = sum((self.q[a] * marks[a] for a in ASSETS), ZERO) + quantity * marks[asset]
            nav_after = self.nav(marks) - cost + quantity * marks[asset]
            if exposure_after > nav_after:
                self.reject(asset, side, quantity, "marked_exposure_limit", phase)
                return False
            self.cash -= cost
            self.q[asset] += quantity
            self.lots[asset].append(dict(start_index=self.i, initial=quantity, remaining=quantity))
            self.cycle_active = True
        else:
            if quantity > self.q[asset]:
                raise AssertionError("oversell")
            proceeds = notional - fee
            if self.cash + proceeds < 0:
                self.reject(asset, side, quantity, "cannot_finance_exit_fee", phase)
                return False
            if proceeds < 0:
                # The lock prevents new purchases, not settlement of exit fees.
                # Pay the net fee deficit from free cash first, then reduce the
                # locked-sale subledger. Never create spendable sale proceeds.
                shortfall = -proceeds
                fee_from_free_cash = min(shortfall, self.cash-self.unavailable)
                fee_from_locked_sale = shortfall-fee_from_free_cash
                self.unavailable -= fee_from_locked_sale
            else:
                self.unavailable += proceeds
            self.cash += proceeds
            self.q[asset] -= quantity
            remainder = quantity
            for lot in self.lots[asset]:
                take = min(remainder, lot["remaining"])
                lot["remaining"] -= take
                remainder -= take
                if take and lot["remaining"] == 0:
                    self.completed_lots += 1
                if not remainder:
                    break
            if remainder:
                raise AssertionError("fifo_quantity_identity")
            if self.cycle_active and not any(self.q.values()):
                self.completed_cycles += 1
                self.cycle_active = False
        slip_loss = quantity * ((price - row["open"]) if side == "buy" else (row["open"] - price))
        self.total_fees += fee
        self.total_slip += slip_loss
        if not ZERO <= self.unavailable <= self.cash:
            raise AssertionError("nonnegative_cash_subledger_identity")
        self.fills.append(dict(intent_id=intent_id, index=self.i, date=self.p["dates"][self.i],
                               asset=asset, side=side, quantity=quantity, raw_open=row["open"], price=price,
                               notional=notional, fee=fee, slippage_cost=slip_loss, phase=phase,
                               fee_payment=dict(from_current_sale=min(fee, notional) if side == "sell" else ZERO,
                                                from_free_cash=fee_from_free_cash,
                                                from_locked_sale=fee_from_locked_sale),
                               frozen_budget=budget, before=before, after=self.balances()))
        return True

    def begin_event(self):
        index = self.i
        event = dict(index=index, date=self.p["dates"][index], targets={},
                     sell_fills=0, buy_fills=0, buy_orders=[], status="created")
        self.events.append(event)
        if self.policy == "cash" or self.paused or self.mandatory:
            event["status"] = "skipped_cash_or_not_eligible_at_previous_close"
            return
        if self.policy == "drift" and any(self.q.values()):
            event["status"] = "drift_holds_actual_basket"
            return
        marks = self.marks(index-1, "close")
        equity = self.previous  # Frozen prior close, before today's ex-date receivable.
        reserve = _reserve(equity)
        targets = {a: _floor_lot(max(equity-reserve, ZERO) / 2 / marks[a]) for a in ASSETS}
        event.update(targets=targets, reserve=reserve, previous_NAV=equity,
                     pre_event_quantities=dict(self.q), status="sell_phase")
        self.pending = event
        for asset in ASSETS:
            quantity = min(max(self.q[asset]-targets[asset], 0), self.capacity(asset, index))
            event["sell_fills"] += int(self.fill(asset, "sell", quantity, "quarter_sell"))

    def plan_buys(self, event):
        if self.paused or self.mandatory:
            event["status"] = "buy_phase_cancelled_by_risk"
            event["buy_orders"] = []
            return
        index = self.i
        need, prices, costs = {}, {}, {}
        for asset in ASSETS:
            need[asset] = min(max(event["targets"][asset]-self.q[asset], 0), self.capacity(asset, index+1))
            prices[asset] = _price(self.p["bars"][asset][index]["close"], "buy", self.slip)
            costs[asset] = (need[asset]*prices[asset]+_fee(need[asset]*prices[asset], self.minimum)) if need[asset] else ZERO
        total = sum(costs.values(), ZERO)
        available = max(self.cash-self.unavailable-event["reserve"], ZERO)
        event.update(buy_planning_index=index, buy_planning_cash=self.cash,
                     buy_planning_spendable=self.cash-self.unavailable, buy_available_after_reserve=available)
        orders = []
        for asset in ASSETS:
            budget = (available*costs[asset]/total).quantize(CENT, rounding=ROUND_FLOOR) if total else ZERO
            quantity = min(need[asset], _floor_lot(budget/prices[asset]))
            while quantity and quantity*prices[asset]+_fee(quantity*prices[asset], self.minimum) > budget:
                quantity -= 100
            orders.append(dict(asset=asset, quantity=quantity, frozen_budget=budget,
                               planning_price=prices[asset], target_quantity=event["targets"][asset]))
        event["buy_orders"] = orders
        event["status"] = "frozen_buy_orders"

    def action_open(self):
        recognised = ZERO
        for action in self.p["actions"]:
            key = action["event_id"]
            if action["ex_index"] == self.i and key in self.rights:
                before = self.balances()
                right = self.rights.pop(key)
                amount = (right["quantity"] * action["cash_per_share"]).quantize(CENT)
                self.receivables[key] = dict(amount=amount, quantity=right["quantity"], pay_index=action["pay_index"])
                recognised += amount
                self.action_log.append(dict(index=self.i, event_id=key, kind="ex_receivable", amount=amount,
                                            before=before, after=self.balances()))
        return recognised

    def action_close(self):
        for action in self.p["actions"]:
            key, asset = action["event_id"], action["asset"]
            if action["record_index"] == self.i and self.q[asset] > 0:
                before = self.balances()
                self.rights[key] = dict(asset=asset, quantity=self.q[asset], ex_index=action["ex_index"],
                                       pay_index=action["pay_index"], included_in_NAV=False)
                self.action_log.append(dict(index=self.i, event_id=key, kind="record_right", quantity=self.q[asset],
                                            before=before, after=self.balances()))
            if action["pay_index"] == self.i and key in self.receivables:
                before = self.balances()
                item = self.receivables.pop(key)
                self.cash += item["amount"]
                self.action_log.append(dict(index=self.i, event_id=key, kind="pay_after_fills", amount=item["amount"],
                                            before=before, after=self.balances()))

    def risk_close(self, equity, had_exposure):
        self.peak = max(self.peak, equity)
        dd = (self.peak-equity)/self.peak
        self.max_dd = max(self.max_dd, dd)
        reasons = []
        if self.previous-equity >= self.previous*Decimal(".02"):
            reasons.append("daily_2percent_pause")
        if had_exposure and dd >= Decimal(".40"):
            reasons.append("global_40percent_pause")
        for reason in reasons:
            self.paused, self.flat_index = True, None
            self.risks.append(dict(index=self.i, kind=reason, previous_NAV=self.previous,
                                   NAV=equity, peak=self.peak, DD=dd))
        self.mandatory = self.paused and any(self.q.values())
        if self.paused and not any(self.q.values()) and self.flat_index is None:
            self.flat_index = self.i
            self.risks.append(dict(index=self.i, kind="flat_cooldown_started", earliest_open_index=self.i+6))
        if self.paused and not any(self.q.values()) and self.flat_index is not None and self.i >= self.flat_index+5:
            self.paused = False
            self.risks.append(dict(index=self.i, kind="eligible_from_next_session_only_next_quarter"))
            self.flat_index = None
        return dd

    def run(self):
        for index in range(self.p["first"], self.p["terminal"]+1):
            self.i = index
            terminal = index == self.p["terminal"]
            start_balances = self.balances()
            q_start = dict(self.q)
            previous_marks = self.marks(index-1, "close")
            start_fill = len(self.fills)
            recognised = self.action_open()
            old_pending = self.pending
            if terminal or self.mandatory:
                if old_pending and old_pending["index"]+1 == index:
                    old_pending["status"] = "cancelled_by_terminal_or_carried_risk"
                    self.pending = None
                for asset in ASSETS:
                    quantity = min(self.q[asset], self.capacity(asset, index))
                    self.fill(asset, "sell", quantity, "terminal" if terminal else "risk_exit")
                if index in self.p["events"]:
                    self.events.append(dict(index=index, date=self.p["dates"][index], status="terminal_or_risk_priority", sell_fills=0, buy_fills=0))
            elif old_pending and old_pending["index"]+1 == index:
                for order in old_pending["buy_orders"]:
                    old_pending["buy_fills"] += int(self.fill(order["asset"], "buy", order["quantity"], "quarter_buy", order["frozen_budget"]))
                if old_pending["status"] != "buy_phase_cancelled_by_risk":
                    old_pending["status"] = "completed_two_phase_attempt"
                self.pending = None
            if not terminal and index in self.p["events"] and not self.mandatory:
                self.begin_event()
            self.action_close()
            # Current full-day volume is diagnostics only, after all opening fills.
            for fill in self.fills[start_fill:]:
                observed_volume = self.p["bars"][fill["asset"]][index]["volume"]
                if Decimal(fill["quantity"]) > observed_volume * Decimal(".01"):
                    self.cap_failures.append(dict(index=index, asset=fill["asset"], quantity=fill["quantity"],
                                                 phase=fill["phase"], audit_clock="after_full_day_volume_available",
                                                 reason="ex_post_day_volume_failed_trade_retained"))
            cash_before_release = self.balances()
            self.unavailable = ZERO
            marks = self.marks(index, "open" if terminal else "close")
            equity = self.nav(marks)
            fills = self.fills[start_fill:]
            components = dict(carried_exposure=sum((q_start[a]*(marks[a]-previous_marks[a]) for a in ASSETS), ZERO),
                              trade_timing=sum(((f["quantity"] if f["side"] == "buy" else -f["quantity"])*(marks[f["asset"]]-f["raw_open"]) for f in fills), ZERO),
                              dividend_entitlement=recognised,
                              commission=-sum((f["fee"] for f in fills), ZERO),
                              slippage=-sum((f["slippage_cost"] for f in fills), ZERO))
            if sum(components.values(), ZERO) != equity-self.previous:
                raise AssertionError("daily_attribution_NAV_identity")
            had = any(q_start.values()) or any(f["side"] == "buy" for f in fills)
            dd = self.risk_close(equity, had)
            if self.pending and self.pending["index"] == index:
                self.plan_buys(self.pending)
            if index == self.p["first"]+1:
                self.initial_snapshot = dict(cash=self.cash, quantities=dict(self.q), rights=copy.deepcopy(self.rights),
                                             receivables=copy.deepcopy(self.receivables), fees=self.total_fees)
            year = self.p["dates"][index-1 if terminal else index][:4]
            self.annual[year] = self.annual.get(year, ZERO)+(equity-self.previous)
            self.days.append(dict(index=index, date=self.p["dates"][index], terminal_open_stub=terminal,
                                  before=start_balances, after=self.balances(), previous_raw_marks=previous_marks,
                                  before_close_cash_release=cash_before_release, marks=marks,
                                  NAV=equity, previous_NAV=self.previous, peak=self.peak, DD=dd,
                                  had_exposure=had, paused=self.paused, mandatory_exit=self.mandatory,
                                  flat_index=self.flat_index, attribution=components))
            self.previous = equity
        unsettled = bool(any(self.q.values()) or self.rights or self.receivables or self.pending)
        total = {key: sum((day["attribution"][key] for day in self.days), ZERO) for key in self.days[0]["attribution"]}
        if sum(total.values(), ZERO) != self.previous-10000 or sum(self.annual.values(), ZERO) != self.previous-10000:
            raise AssertionError("whole_account_attribution_identity")
        return dict(artifact_type="artificial_constant_mix_account_v1", source_nature=SOURCE,
                    qualified=False, historical_returns_computed=False, real_forward=0,
                    policy=self.policy, cost_id=f"min{self.minimum}_slip{self.slip}",
                    minimum_commission=self.minimum, slippage_bps=self.slip, commission_bps=5,
                    minimum0_counterfactual=self.minimum == 0, method_sha256=METHOD_SHA,
                    fixture_sha256=self.p["fixture_sha256"], fills=self.fills, intents=self.intents, rejections=self.rejections,
                    event_attempts=self.events, days=self.days, risk_records=self.risks,
                    action_records=self.action_log, capacity_failures=self.cap_failures,
                    unknown_execution_constraints=self.unknowns, initial_snapshot=self.initial_snapshot,
                    annual_contributions=self.annual, attribution=total, FIFO_lots=self.lots,
                    summary=dict(terminal_cash=self.cash, terminal_book_NAV=self.previous,
                                 terminal_quantities=self.q, terminal_receivables=self.receivables,
                                 terminal_unexercised_rights=self.rights,
                                 unexercised_rights_included_in_NAV=False,
                                 terminal_unsettled=unsettled, terminal_cash_netPnL=self.cash-10000,
                                 terminal_cash_netPnL_is_fully_settled=not unsettled,
                                 book_netPnL=self.previous-10000, observed_maxDD=self.max_dd,
                                 risk_ceiling_pass=self.max_dd <= Decimal(".40"),
                                 fill_count=len(self.fills), completed_FIFO_purchase_lots=self.completed_lots,
                                 complete_policy_exposure_cycles=self.completed_cycles,
                                 two_sided_rebalance_events=sum(bool(e.get("sell_fills")) and bool(e.get("buy_fills")) for e in self.events),
                                 initial_two_assets_filled=bool(self.initial_snapshot and all(self.initial_snapshot["quantities"].values())),
                                 total_commission=self.total_fees, total_slippage=self.total_slip,
                                 attribution_reconciled=True, capacity_pass=not self.cap_failures,
                                 financial_verdict="not_evaluated_artificial_engineering_only"))


def _run_prepared(prepared, policy, minimum, slip):
    with localcontext(CONTEXT) as ctx:
        initial = _context_record(ctx)
        result = _Account(prepared, policy, minimum, slip).run()
        result["runtime"] = dict(module_file=str(Path(__file__).resolve()), context_initial=initial,
                                 module_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                 context_final=_context_record(ctx))
        return _json(result)


def run_account(fixture, policy="constant_mix", minimum=5, slip=10):
    with localcontext(CONTEXT):
        prepared = _prepare(fixture)
        return _run_prepared(prepared, policy, minimum, slip)


def paired_annual_bootstrap(annual_by_cost):
    """Ten annual vectors, shared paired circular two-year blocks, no path rerun."""
    import numpy as np
    keys, values = [], []
    years = None
    for minimum, slip in COSTS:
        key = f"min{minimum}_slip{slip}"
        pair = annual_by_cost[key]
        current_years = sorted(pair["constant_mix"])
        if years is None:
            years = current_years
        if current_years != years or sorted(pair["drift"]) != years:
            raise ValueError("same_annual_buckets_required")
        for endpoint in ("net", "increment"):
            keys.append(key+"/"+endpoint)
            with localcontext(CONTEXT):
                values.append([float(Decimal(pair["constant_mix"][y]) - (Decimal(pair["drift"][y]) if endpoint == "increment" else 0)) for y in years])
    if len(years) != 10:
        return dict(status="not_computed_requires_ten_annual_buckets", annual_buckets=len(years), source_nature=SOURCE, qualified=False)
    data = np.asarray(values, dtype="float64").T
    if data.shape != (10, 18) or not np.isfinite(data).all():
        raise ValueError("finite_10_by_18_annual_vectors_required")
    rng = np.random.Generator(np.random.PCG64(20261107))
    means = np.empty((5000, 18), dtype="float64")
    for replicate in range(5000):
        starts = rng.integers(0, 10, size=5)
        indices = ((starts[:, None] + np.arange(2)) % 10).reshape(-1)
        means[replicate] = data[indices].mean(axis=0)
    lower = np.quantile(means, .05/18, axis=0, method="linear")
    return dict(status="computed_artificial_fixed_trace_sensitivity", source_nature=SOURCE,
                qualified=False, N=10, years=years, replications=5000, seed=20261107,
                block=2, starts_per_replication=5, shared_indices_for_all18=True,
                units="CNY_per_artificial_year", statistic="arithmetic_mean_annual_PnL",
                endpoint_keys=keys, lower=dict(zip(keys, lower.tolist())),
                observed_means=dict(zip(keys, data.mean(axis=0).tolist())),
                replicate_means_sha256=hashlib.sha256(means.astype("<f8").tobytes()).hexdigest(),
                quantile=.05/18, quantile_method="linear", numpy_version=np.__version__,
                historical_returns_computed=False)


def _matrix_checks(summaries, annual, events, statistics):
    """Evaluate only the fixed artificial trace, never issue qualification."""
    with localcontext(CONTEXT):
        risky = [s for key, s in summaries.items() if not key.endswith("/cash")]
        checks = dict(all18_initial_two_assets=all(s["initial_two_assets_filled"] for s in risky),
                      all18_settled=all(not s["terminal_unsettled"] for s in risky),
                      all18_capacity=all(s["capacity_pass"] for s in risky),
                      all18_observed_DD_within40=all(s["risk_ceiling_pass"] for s in risky),
                      all27_accounting=all(s["attribution_reconciled"] for s in summaries.values()))
        for cost in ("min5_slip10", "min10_slip30"):
            cm, drift = summaries[cost+"/constant_mix"], summaries[cost+"/drift"]
            checks[cost+"_net_cash_positive"] = Decimal(cm["terminal_cash_netPnL"]) > 0
            checks[cost+"_cash_increment_positive"] = Decimal(cm["terminal_cash"])-Decimal(drift["terminal_cash"]) > 0
        years = sorted(annual["min5_slip10"]["constant_mix"])
        primary = annual["min5_slip10"]
        if len(years) == 10:
            first, later = years[:6], years[6:]
            for label, selected in (("first6", first), ("later4", later)):
                increment = sum((Decimal(primary["constant_mix"][y])-Decimal(primary["drift"][y]) for y in selected), ZERO)
                checks[label+"_primary_increment_positive"] = increment > 0
                checks[label+"_mechanism_exercised"] = any(
                    e["date"][:4] in selected and e.get("sell_fills", 0) and e.get("buy_fills", 0)
                    for e in events["min5_slip10/constant_mix"])
            checks["all18_40_opportunities"] = all(len(v) == 40 for k, v in events.items() if not k.endswith("/cash"))
            checks["ten_annual_buckets"] = True
        else:
            checks["ten_annual_buckets"] = False
        checks["primary_net_adjusted_lower_positive"] = statistics.get("lower", {}).get("min5_slip10/net", float("-inf")) > 0
        checks["primary_increment_adjusted_lower_positive"] = statistics.get("lower", {}).get("min5_slip10/increment", float("-inf")) > 0
        return dict(checks=checks, all_artificial_checks_pass=all(checks.values()),
                    source_nature=SOURCE, qualified=False, real_forward=0,
                    financial_verdict="not_evaluated_artificial_engineering_only",
                    interpretation="Whole-policy trace checks, including cash reinvestment and risk exposure; not evidence of market profitability.")


def _write(path, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
    with path.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def run_matrix(fixture, output_dir=None):
    with localcontext(CONTEXT):
        prepared = _prepare(fixture)
    directory = Path(output_dir) if output_dir is not None else None
    if directory:
        directory.mkdir(parents=True, exist_ok=False)
        fixture_ref = _write(directory/"artificial_fixture.json", fixture)
    else:
        fixture_ref = None
    accounts, annual, initial_matches, differences = {}, {}, {}, {}
    summaries, events = {}, {}
    for minimum, slip in COSTS:
        cost = f"min{minimum}_slip{slip}"
        pair, annual[cost] = {}, {}
        for policy in ("constant_mix", "drift", "cash"):
            result = _run_prepared(prepared, policy, minimum, slip)
            key = cost+"/"+policy
            summaries[key], events[key] = result["summary"], result["event_attempts"]
            annual[cost][policy] = result["annual_contributions"]
            if policy != "cash":
                pair[policy] = {k: result[k] for k in ("initial_snapshot", "attribution", "summary")}
            if directory:
                ref = _write(directory/(cost+"_"+policy+".json"), result)
                accounts[key] = dict(artifact=ref, summary=result["summary"])
            else:
                accounts[key] = result
        initial_matches[cost] = pair["constant_mix"]["initial_snapshot"] == pair["drift"]["initial_snapshot"]
        if not initial_matches[cost]:
            raise AssertionError("same_actual_initial_basket_required")
        with localcontext(CONTEXT):
            delta = {k: Decimal(pair["constant_mix"]["attribution"][k])-Decimal(pair["drift"]["attribution"][k]) for k in pair["drift"]["attribution"]}
            difference = Decimal(pair["constant_mix"]["summary"]["terminal_book_NAV"])-Decimal(pair["drift"]["summary"]["terminal_book_NAV"])
            if sum(delta.values(), ZERO) != difference:
                raise AssertionError("policy_difference_attribution_identity")
            differences[cost] = _json(dict(components=delta, book_NAV_difference=difference,
                                          meaning="whole_policy_includes_dividend_reinvestment_and_risk_exposure"))
    statistics = paired_annual_bootstrap(annual)
    checks = _matrix_checks(summaries, annual, events, statistics)
    stats_ref = _write(directory/"statistics.json", statistics) if directory else None
    result = dict(artifact_type="artificial_constant_mix_matrix_v1", source_nature=SOURCE,
                  qualified=False, historical_returns_computed=False, real_forward=0,
                  accounts=accounts, account_count=27, fixture=fixture_ref,
                  fixture_sha256=prepared["fixture_sha256"], statistics=stats_ref or statistics,
                  same_actual_initial_baskets=initial_matches, policy_difference_attribution=differences,
                  artificial_method_checks=checks,
                  financial_verdict="not_evaluated_artificial_engineering_only")
    if directory:
        _write(directory/"result.json", result)
    return result


def make_fixture(sessions=100, events=None):
    """Fixed invented values; custom test edits remain artificial assertions."""
    dates = []
    day = date(2001, 1, 1)
    while len(dates) < sessions:
        if day.weekday() < 5:
            dates.append(day.isoformat())
        day += timedelta(days=1)
    rows = [{"open": "1.20", "close": "1.20", "volume": "10000000",
             "suspended": False, "buy_blocked": False, "sell_blocked": False} for _ in dates]
    return dict(artifact_type="artificial_constant_mix_fixture_v1", source_nature=SOURCE,
                constructed_from_market_data=False, assets=list(ASSETS), dates=dates,
                bars={a: copy.deepcopy(rows) for a in ASSETS}, event_indices=events or [20, 50],
                terminal_index=sessions-1, actions=[])


def make_full_demo_fixture():
    dates = []
    day, end = date(2000, 12, 4), date(2011, 1, 3)
    while day <= end:
        if day.weekday() < 5:
            dates.append(day.isoformat())
        day += timedelta(days=1)
    events = []
    for year in range(2001, 2011):
        for month in (1, 4, 7, 10):
            events.append(next(i for i, d in enumerate(dates) if d.startswith(f"{year}-{month:02d}-")))
    fixture = make_fixture(len(dates), events)
    fixture["dates"] = dates
    with localcontext(CONTEXT):
        for i in range(len(dates)):
            triangle = min(i % 240, 240-i % 240)
            a = (Decimal("1.20")+Decimal(triangle)*Decimal(".004")).quantize(TICK)
            b = (Decimal("1.30")-Decimal(triangle)*Decimal(".001")).quantize(TICK)
            for asset, price in zip(ASSETS, (a, b)):
                fixture["bars"][asset][i].update(open=str(price), close=str(price))
    fixture["actions"] = [dict(event_id="artificial_cash_distribution", asset=ASSETS[0],
                                known_index=20, record_index=130, ex_index=132, pay_index=135,
                                cash_per_share=".002", share_multiplier="1")]
    return fixture
