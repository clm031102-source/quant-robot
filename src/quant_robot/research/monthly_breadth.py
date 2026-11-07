"""Fixed monthly two-ETF breadth ledger; public APIs accept artificial input only.

Private known-history contexts preserve identity and hashes but confer no admission.
The external once-only controller owns authorization, decode claims and source guards.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date
from decimal import (Decimal, Context, localcontext, ROUND_HALF_UP, ROUND_CEILING,
                     ROUND_FLOOR, InvalidOperation, DivisionByZero, Overflow)
from pathlib import Path

ASSETS = ("ARTIFICIAL_EQUITY", "ARTIFICIAL_GOLD")
REAL_ASSETS = ("CN_ETF_XSHG_510300", "CN_ETF_XSHG_518880")
SOURCE = "artificial_generated_not_market_data"
METHOD_SHA = "f3d77564288628ebd67e37bd36735197d7f49f9fab63d65398ee28a1a9d16a89"
POLICIES = ("breadth", "monthly_50_50", "own_trend")
COSTS = tuple((m, s) for m in (0, 5, 10) for s in (0, 10, 30))
ZERO, CENT, TICK = Decimal(0), Decimal(".01"), Decimal(".001")
COMMISSION_RATE = Decimal(".0001")
CONTEXT = Context(prec=40, rounding=ROUND_HALF_UP, Emin=-999999, Emax=999999,
                  capitals=1, clamp=0)
for _signal in CONTEXT.traps:
    CONTEXT.traps[_signal] = _signal in (InvalidOperation, DivisionByZero, Overflow)
CONTEXT.clear_flags()


@dataclass(frozen=True)
class _ArtificialContext:
    assets: tuple = ASSETS
    source_nature: str = SOURCE
    historical: bool = False
    test_values: bool = True

    @property
    def returns_computed(self):
        return False

    @property
    def verdict(self):
        return "not_evaluated_artificial_engineering_only"

    def artifact(self, kind):
        return "artificial_monthly_breadth_" + kind + "_v1"


@dataclass(frozen=True)
class _KnownHistoryContext:
    assets: tuple
    source_nature: str
    registration_sha256: str
    normalized_input_sha256: str
    provenance_sha256: str
    test_values: bool = False

    def __post_init__(self):
        expected = ("test_artificial_values_true_calendar" if self.test_values else
                    "known_history_provider_wire_with_retrospective_announced_actions")
        if type(self.test_values) is not bool or self.assets != REAL_ASSETS or type(self.assets) is not tuple or self.source_nature != expected:
            raise ValueError("known_history_context_identity")
        for value in (self.registration_sha256, self.normalized_input_sha256, self.provenance_sha256):
            if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
                raise ValueError("known_history_fingerprint")

    @property
    def historical(self):
        return True

    @property
    def returns_computed(self):
        return not self.test_values

    @property
    def verdict(self):
        return ("conditional_historical_diagnostic_only" if self.returns_computed else
                "not_evaluated_artificial_engineering_only")

    def artifact(self, kind):
        return ("conditional_historical_monthly_breadth_" if self.returns_computed else
                "artificial_true_calendar_monthly_breadth_") + kind + "_v1"


_SYNTHETIC_CONTEXT = _ArtificialContext()


def _context(value):
    if value is None:
        return _SYNTHETIC_CONTEXT
    if type(value) is not _KnownHistoryContext:
        raise ValueError("exact_known_history_context_required")
    return value


def _number(value):
    if not isinstance(value, (str, Decimal)) or isinstance(value, bool):
        raise ValueError("decimal_string_required")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("finite_decimal_required")
    return result


def _integer(value):
    if type(value) is not int or value < 0:
        raise ValueError("nonnegative_integer_required")
    return value


def _json(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json(v) for v in value]
    return value


def digest(value):
    return hashlib.sha256(json.dumps(_json(value), sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _context_record(ctx):
    return dict(prec=ctx.prec, rounding=ctx.rounding, Emin=ctx.Emin, Emax=ctx.Emax,
                capitals=ctx.capitals, clamp=ctx.clamp,
                traps={k.__name__: v for k, v in ctx.traps.items()},
                flags={k.__name__: v for k, v in ctx.flags.items()})


def _fee(value, minimum):
    return max(Decimal(minimum), value * COMMISSION_RATE).quantize(CENT)


def _price(raw, side, slip):
    factor = 1 + Decimal(slip) / 10000 * (1 if side == "buy" else -1)
    return (raw * factor).quantize(TICK, rounding=ROUND_CEILING if side == "buy" else ROUND_FLOOR)


def _floor_lot(value):
    return max(0, int(value // 100) * 100)


def _reserve(equity):
    return 4 * max(Decimal(10), COMMISSION_RATE * max(equity, ZERO)).quantize(CENT, rounding=ROUND_CEILING)


def _weights(signs, policy):
    if policy == "breadth":
        return (Decimal(sum(signs)) / 4,) * 2
    if policy == "monthly_50_50":
        return (Decimal(".5"),) * 2
    if policy == "own_trend":
        return tuple(Decimal(s) / 2 for s in signs)
    if policy == "cash":
        return (ZERO, ZERO)
    raise ValueError("fixed_policy_required")


def _prepare(fixture, *, context=None):
    """Validation and all numeric work are local-context isolated, even on failure."""
    with localcontext(CONTEXT):
        return _prepare_inner(fixture, context=_context(context))


def _prepare_inner(fixture, *, context):
    assets = context.assets
    if context.historical:
        if (fixture.get("artifact_type") != "admitted_monthly_breadth_fixture_v1"
                or fixture.get("source_nature") != context.source_nature
                or fixture.get("constructed_from_market_data") is not context.returns_computed
                or digest(fixture) != context.normalized_input_sha256):
            raise ValueError("known_history_input_binding")
    elif (fixture.get("artifact_type") != "artificial_monthly_breadth_fixture_v1"
          or fixture.get("source_nature") != SOURCE
          or fixture.get("constructed_from_market_data") is not False):
        raise ValueError("artificial_only_public_input")
    if fixture.get("assets") != list(assets) or fixture.get("actions_complete") is not True:
        raise ValueError("exact_assets_complete_conditional_action_table_required")
    dates = fixture["dates"]
    if type(dates) is not list or len(dates) < 23 or dates != sorted(set(dates)):
        raise ValueError("explicit_complete_calendar_required")
    parsed = [date.fromisoformat(d) for d in dates]
    if any(d.isoformat() != s for d, s in zip(parsed, dates)):
        raise ValueError("canonical_dates_required")
    if not context.historical and any(not 2000 <= d.year <= 2011 for d in parsed):
        raise ValueError("artificial_years_2000_to_2011_only")
    terminal = _integer(fixture["terminal_index"])
    if terminal >= len(dates):
        raise ValueError("terminal_calendar_bound")
    ends = fixture["month_end_sessions"]
    if type(ends) is not list or len(ends) < 13 or ends != sorted(set(ends)):
        raise ValueError("thirteen_explicit_month_ends_required")
    indices = [dates.index(d) for d in ends]
    serials = [date.fromisoformat(d).year * 12 + date.fromisoformat(d).month for d in ends]
    if any(b-a != 1 for a, b in zip(serials, serials[1:])):
        raise ValueError("consecutive_month_ends_required")
    for i in indices:
        if i >= terminal or i+1 >= len(dates) or dates[i][:7] == dates[i+1][:7]:
            raise ValueError("declared_month_end_not_last_session")
    first_signal = _integer(fixture["first_signal_index"])
    if first_signal != indices[12] or first_signal+2 >= terminal or first_signal < 20:
        raise ValueError("first_signal_requires_thirteen_months_and_two_phases")
    if context.historical and (ends[0] != "2013-12-31" or ends[-1] != "2023-12-29"
                              or len(ends) != 121 or dates[first_signal] != "2014-12-31"
                              or dates[terminal] != "2024-01-02"):
        raise ValueError("fixed_historical_monthly_calendar")
    bars = {}
    if set(fixture["bars"]) != set(assets):
        raise ValueError("bar_assets")
    for asset in assets:
        rows = fixture["bars"][asset]
        if len(rows) != terminal+1:
            raise ValueError("bars_exactly_through_terminal")
        bars[asset] = []
        for i, row in enumerate(rows):
            new = {k: _number(row[k]) for k in ("open", "volume")}
            if i == terminal:
                if row.get("close") is not None or row.get("terminal_close_not_observed") is not True:
                    raise ValueError("terminal_open_only_required")
                new["close"] = ZERO
            else:
                new["close"] = _number(row["close"])
            if new["open"] <= 0 or new["volume"] < 0 or (i != terminal and new["close"] <= 0):
                raise ValueError("invalid_bar_numeric")
            for flag in ("suspended", "buy_blocked", "sell_blocked"):
                if flag not in row or (row[flag] is not None and type(row[flag]) is not bool):
                    raise ValueError("explicit_execution_constraints")
                new[flag] = row[flag]
            bars[asset].append(new)
    actions, seen = [], set()
    for original in fixture.get("actions", []):
        a = copy.deepcopy(original)
        if a["event_id"] in seen or a["asset"] not in assets:
            raise ValueError("unique_action_asset")
        seen.add(a["event_id"])
        for k in ("known_index", "record_index", "ex_index", "pay_index"):
            if _integer(a[k]) >= len(dates):
                raise ValueError("action_date_not_in_calendar")
        if not a["known_index"] <= a["record_index"] < a["ex_index"] <= a["pay_index"]:
            raise ValueError("known_record_ex_pay_sequence")
        if _number(a.get("share_multiplier", "0")) != 1:
            raise ValueError("share_conversion_unsupported")
        a["cash_per_share"] = _number(a["cash_per_share"])
        if a["cash_per_share"] < 0:
            raise ValueError("negative_distribution")
        actions.append(a)
    dividends = {a: {} for a in assets}
    for action in actions:
        i, a = action["ex_index"], action["asset"]
        dividends[a][i] = dividends[a].get(i, ZERO) + action["cash_per_share"]
    signal_rows, levels = [], {a: Decimal(100) for a in assets}
    monthly = {a: [] for a in assets}
    ends_set = set(indices)
    for i in range(indices[0], indices[-1]+1):
        if i > indices[0]:
            for a in assets:
                levels[a] = levels[a] * (bars[a][i]["close"]+dividends[a].get(i, ZERO)) / bars[a][i-1]["close"]
                if not levels[a].is_finite() or levels[a] <= 0:
                    raise ValueError("nonpositive_or_nonfinite_TR")
        if i in ends_set:
            for a in assets:
                monthly[a].append(levels[a])
            if len(monthly[assets[0]]) >= 13:
                signs = tuple(int(monthly[a][-1] > monthly[a][-13]) for a in assets)
                signal_rows.append(dict(index=i, date=dates[i], month_count=13,
                                        prior_month_date=dates[indices[len(monthly[assets[0]])-13]],
                                        TR={a: monthly[a][-1] for a in assets},
                                        TR_prior12={a: monthly[a][-13] for a in assets},
                                        signs=list(signs), exposure=Decimal(sum(signs))/2,
                                        weights={p: dict(zip(assets, _weights(signs, p))) for p in POLICIES},
                                        terminal_overrides=i+1 >= terminal))
    signals = {s["index"]+1: s for s in signal_rows if s["index"]+2 < terminal}
    if (fixture.get("event_indices") != sorted(signals)
            or fixture.get("monthly_decision_indices") != [i-1 for i in sorted(signals)]):
        raise ValueError("exact_monthly_decision_and_sell_indices_required")
    if context.historical and (len(signals) != 108 or dates[min(signals)] != "2015-01-05"):
        raise ValueError("fixed_108_events_required")
    return dict(dates=dates, bars=bars, actions=actions, terminal=terminal,
                first=first_signal+1, first_signal=first_signal, events=sorted(signals), signals=signals,
                signal_rows=signal_rows, fixture_sha256=digest(fixture))


def validate_synthetic_fixture(fixture):
    prepared = _prepare(fixture)
    return dict(status="artificial_valid", fixture_sha256=prepared["fixture_sha256"], qualified=False)


def signal_frame(fixture):
    return _json(_prepare(fixture)["signal_rows"])


class _Account:
    def __init__(self, prepared, policy, minimum, slip, *, context=_SYNTHETIC_CONTEXT):
        self.context, self.assets = context, context.assets
        if policy not in (*POLICIES, "cash") or type(minimum) is not int or type(slip) is not int or (minimum, slip) not in COSTS:
            raise ValueError("fixed_policy_and_nine_cost_identity_required")
        self.p, self.policy, self.minimum, self.slip = prepared, policy, minimum, slip
        self.cash, self.unavailable = Decimal(10000), ZERO
        self.q = dict.fromkeys(self.assets, 0)
        self.rights, self.receivables = {}, {}
        self.peak = self.previous = Decimal(10000)
        self.max_dd = ZERO
        self.paused, self.mandatory, self.flat_index = False, False, None
        self.pending = None
        self.fills, self.intents, self.rejections, self.risks, self.action_log = [], [], [], [], []
        self.events, self.days, self.cap_failures, self.unknowns = [], [], [], []
        self.lots = {a: [] for a in self.assets}
        self.completed_lots, self.completed_cycles = 0, 0
        self.cycle_active = False
        self.initial_snapshot, self.annual = None, {}
        self.total_fees = self.total_slip = ZERO
        self.i = prepared["first"]

    def marks(self, index, field):
        return {a: self.p["bars"][a][index][field] for a in self.assets}

    def nav(self, marks):
        return self.cash + sum((x["amount"] for x in self.receivables.values()), ZERO) + sum((self.q[a] * marks[a] for a in self.assets), ZERO)

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
            exposure_after = sum((self.q[a] * marks[a] for a in self.assets), ZERO) + quantity * marks[asset]
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
        signal = self.p["signals"][index]
        event = dict(index=index, date=self.p["dates"][index], targets={},
                     signal_index=signal["index"], signal_date=signal["date"],
                     signs=list(signal["signs"]), weights=dict(zip(self.assets, _weights(signal["signs"], self.policy))),
                     sell_fills=0, buy_fills=0, buy_orders=[], status="created")
        self.events.append(event)
        if self.policy == "cash" or self.paused or self.mandatory:
            event["status"] = "skipped_cash_or_not_eligible_at_previous_close"
            return
        marks = self.marks(index-1, "close")
        equity = self.previous
        reserve = _reserve(equity)
        targets = {a: _floor_lot(max(equity, ZERO)*event["weights"][a]/marks[a]) for a in self.assets}
        event.update(targets=targets, reserve=reserve, previous_NAV=equity,
                     pre_event_quantities=dict(self.q), status="sell_phase")
        self.pending = event
        for asset in self.assets:
            quantity = min(max(self.q[asset]-targets[asset], 0), self.capacity(asset, index))
            event["sell_fills"] += int(self.fill(asset, "sell", quantity, "monthly_sell"))

    def plan_buys(self, event):
        if self.paused or self.mandatory:
            event["status"] = "buy_phase_cancelled_by_risk"
            event["buy_orders"] = []
            return
        index = self.i
        need, prices, costs = {}, {}, {}
        for asset in self.assets:
            need[asset] = min(max(event["targets"][asset]-self.q[asset], 0), self.capacity(asset, index+1))
            prices[asset] = _price(self.p["bars"][asset][index]["close"], "buy", self.slip)
            costs[asset] = (need[asset]*prices[asset]+_fee(need[asset]*prices[asset], self.minimum)) if need[asset] else ZERO
        total = sum(costs.values(), ZERO)
        available = max(self.cash-self.unavailable-event["reserve"], ZERO)
        event.update(buy_planning_index=index, buy_planning_cash=self.cash,
                     buy_planning_spendable=self.cash-self.unavailable, buy_available_after_reserve=available)
        orders = []
        for asset in self.assets:
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
            self.risks.append(dict(index=self.i, kind="eligible_from_next_session_only_next_month"))
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
                for asset in self.assets:
                    quantity = min(self.q[asset], self.capacity(asset, index))
                    self.fill(asset, "sell", quantity, "terminal" if terminal else "risk_exit")
                if index in self.p["events"]:
                    self.events.append(dict(index=index, date=self.p["dates"][index], status="terminal_or_risk_priority", sell_fills=0, buy_fills=0))
            elif old_pending and old_pending["index"]+1 == index:
                for order in old_pending["buy_orders"]:
                    old_pending["buy_fills"] += int(self.fill(order["asset"], "buy", order["quantity"], "monthly_buy", order["frozen_budget"]))
                if old_pending["status"] != "buy_phase_cancelled_by_risk":
                    old_pending["status"] = "completed_two_phase_attempt"
                self.pending = None
            if not terminal and index in self.p["events"] and not self.mandatory:
                self.begin_event()
            if not terminal:
                self.action_close()
            # Current full-day volume is diagnostics only, after all opening fills.
            for fill in self.fills[start_fill:]:
                observed_volume = self.p["bars"][fill["asset"]][index]["volume"]
                if Decimal(fill["quantity"]) > observed_volume * Decimal(".01"):
                    self.cap_failures.append(dict(index=index, asset=fill["asset"], quantity=fill["quantity"],
                                                 phase=fill["phase"], audit_clock="after_full_day_volume_available",
                                                 reason="ex_post_day_volume_failed_trade_retained"))
            cash_before_release = self.balances()
            if not terminal:
                self.unavailable = ZERO
            marks = self.marks(index, "open" if terminal else "close")
            equity = self.nav(marks)
            fills = self.fills[start_fill:]
            components = dict(carried_exposure=sum((q_start[a]*(marks[a]-previous_marks[a]) for a in self.assets), ZERO),
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
        return dict(artifact_type=self.context.artifact("account"), source_nature=self.context.source_nature,
                    qualified=False, historical_returns_computed=self.context.returns_computed, real_forward=0,
                    policy=self.policy, cost_id=f"min{self.minimum}_slip{self.slip}",
                    minimum_commission=self.minimum, slippage_bps=self.slip, commission_bps=1,
                    minimum0_counterfactual=self.minimum == 0, method_sha256=METHOD_SHA,
                    fixture_sha256=self.p["fixture_sha256"], signal_frame=self.p["signal_rows"], fills=self.fills, intents=self.intents, rejections=self.rejections,
                    event_attempts=self.events, days=self.days, risk_records=self.risks,
                    action_records=self.action_log, capacity_failures=self.cap_failures,
                    unknown_execution_constraints=self.unknowns, initial_snapshot=self.initial_snapshot,
                    annual_contributions=self.annual, attribution=total, FIFO_lots=self.lots,
                    summary=dict(terminal_cash=self.cash, terminal_book_NAV=self.previous,
                                 terminal_spendable_cash=self.cash-self.unavailable,
                                 terminal_locked_sale_cash=self.unavailable,
                                 terminal_quantities=self.q, terminal_receivables=self.receivables,
                                 terminal_unexercised_rights=self.rights,
                                 unexercised_rights_included_in_NAV=False,
                                 terminal_unsettled=unsettled, terminal_cash_netPnL=self.cash-10000,
                                 terminal_cash_netPnL_is_fully_settled=not unsettled and self.unavailable == ZERO,
                                 terminal_inventory_and_rights_closed=not unsettled,
                                 book_netPnL=self.previous-10000, observed_maxDD=self.max_dd,
                                 risk_ceiling_pass=self.max_dd <= Decimal(".40"),
                                 fill_count=len(self.fills), completed_FIFO_purchase_lots=self.completed_lots,
                                 complete_policy_exposure_cycles=self.completed_cycles,
                                 two_sided_rebalance_events=sum(bool(e.get("sell_fills")) and bool(e.get("buy_fills")) for e in self.events),
                                 initial_two_assets_filled=bool(self.initial_snapshot and all(self.initial_snapshot["quantities"].values())),
                                 total_commission=self.total_fees, total_slippage=self.total_slip,
                                 attribution_reconciled=True, capacity_pass=not self.cap_failures,
                                 financial_verdict=self.context.verdict))


def _run_prepared(prepared, policy, minimum, slip, *, context=None):
    """Run a bound, previously normalized input. This API does not grant admission."""
    execution = _context(context)
    if execution.historical and prepared["fixture_sha256"] != execution.normalized_input_sha256:
        raise ValueError("prepared_input_context_binding")
    with localcontext(CONTEXT) as ctx:
        ctx.clear_flags()
        initial = _context_record(ctx)
        result = _Account(prepared, policy, minimum, slip, context=execution).run()
        if execution.historical:
            result.update(registration_sha256=execution.registration_sha256,
                          normalized_input_sha256=execution.normalized_input_sha256,
                          provenance_sha256=execution.provenance_sha256,
                          evidence_class=execution.source_nature,
                          test_injected_values=execution.test_values)
        result["runtime"] = dict(module_file=str(Path(__file__).resolve()),
                                 module_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                                 context_initial=initial, context_final=_context_record(ctx))
        return _json(result)


def run_account(fixture, policy="breadth", minimum=5, slip=10):
    """Public artificial-only entry; real inputs require the separate claim controller."""
    with localcontext(CONTEXT):
        return _run_prepared(_prepare(fixture), policy, minimum, slip)


ENDPOINTS = ("breadth_net", "breadth_minus_monthly_50_50", "breadth_minus_own_trend")


def paired_annual_bootstrap(annual_by_cost, *, context=None):
    """Nine annual vectors; shared paired circular 2-year blocks, no path rerun."""
    import numpy as np
    execution = _context(context)
    with localcontext(CONTEXT):
        keys, columns, years = [], [], None
        for minimum, slip in COSTS:
            cost = f"min{minimum}_slip{slip}"
            pair = annual_by_cost[cost]
            current = sorted(pair["breadth"])
            if years is None:
                years = current
            if any(sorted(pair[p]) != years for p in POLICIES):
                raise ValueError("same_annual_buckets_required")
            for endpoint, baseline in zip(ENDPOINTS, (None, "monthly_50_50", "own_trend")):
                keys.append(cost+"/"+endpoint)
                columns.append([float(_number(pair["breadth"][y])-(
                    _number(pair[baseline][y]) if baseline else ZERO)) for y in years])
        if len(years) != 9:
            return dict(status="not_computed_requires_nine_annual_buckets", annual_buckets=len(years),
                        source_nature=execution.source_nature, qualified=False)
        if execution.historical and years != [str(y) for y in range(2015, 2024)]:
            raise ValueError("fixed_historical_annual_buckets")
        data = np.asarray(columns, dtype="float64").T
        if data.shape != (9, 27) or not np.isfinite(data).all():
            raise ValueError("finite_9_by_27_annual_vectors_required")
        rng = np.random.Generator(np.random.PCG64(20261107))
        means = np.empty((5000, 27), dtype="float64")
        for replicate in range(5000):
            starts = rng.integers(0, 9, size=5)
            rows = ((starts[:, None]+np.arange(2)) % 9).reshape(-1)[:9]
            means[replicate] = data[rows].mean(axis=0)
        lower = np.quantile(means, .05/27, axis=0, method="linear")
        if not np.isfinite(means).all() or not np.isfinite(lower).all():
            raise ValueError("nonfinite_bootstrap_result")
        return dict(status=("computed_conditional_historical_trace_sensitivity" if execution.returns_computed
                            else "computed_artificial_fixed_trace_sensitivity"),
                    source_nature=execution.source_nature, qualified=False, N=9, years=years,
                    replications=5000, seed=20261107, block=2, starts_per_replication=5,
                    truncate_rows_to=9, shared_indices_for_all27=True,
                    units=("CNY_per_observed_year" if execution.returns_computed else "CNY_per_artificial_year"),
                    statistic="arithmetic_mean_annual_PnL", endpoint_keys=keys,
                    lower=dict(zip(keys, lower.tolist())), observed_means=dict(zip(keys, data.mean(axis=0).tolist())),
                    replicate_means_sha256=hashlib.sha256(means.astype("<f8").tobytes()).hexdigest(),
                    quantile=.05/27, quantile_method="linear", numpy_version=np.__version__,
                    historical_returns_computed=execution.returns_computed)


def _matrix_checks(summaries, annual, events, statistics, *, context=None,
                   exposure_rows=None, signal_rows=None):
    """Fixed-method checks on saved outputs; all failed cases remain in the result."""
    execution = _context(context)
    expected = {f"min{m}_slip{s}/{p}" for m, s in COSTS for p in POLICIES} | {"cash"}
    with localcontext(CONTEXT):
        checks = dict(all28_completed=set(summaries) == expected,
                      all28_accounting=set(summaries) == expected and all(s["attribution_reconciled"] for s in summaries.values()))
        for cost in ("min5_slip10", "min10_slip30"):
            group = {p: summaries[cost+"/"+p] for p in POLICIES}
            checks[cost+"_all3_settled"] = all(not s["terminal_unsettled"] for s in group.values())
            checks[cost+"_all3_capacity"] = all(s["capacity_pass"] for s in group.values())
            checks[cost+"_breadth_observed_DD_within40"] = _number(group["breadth"]["observed_maxDD"]) <= Decimal(".40")
            checks[cost+"_breadth_net_cash_positive"] = _number(group["breadth"]["terminal_cash_netPnL"]) > 0
            for baseline in ("monthly_50_50", "own_trend"):
                checks[cost+"_cash_increment_vs_"+baseline+"_positive"] = (
                    _number(group["breadth"]["terminal_cash"]) > _number(group[baseline]["terminal_cash"]))
        primary = annual["min5_slip10"]
        years = sorted(primary["breadth"])
        checks["nine_annual_buckets"] = len(years) == 9
        sign_counts = {"00": 0, "01": 0, "10": 0, "11": 0}
        regular = [r for r in signal_rows or [] if not r["terminal_overrides"]]
        for row in regular:
            sign_counts["".join(map(str, row["signs"]))] += 1
        for label, selected in (("earlier5", years[:5]), ("later4", years[5:])):
            for baseline in ("monthly_50_50", "own_trend"):
                delta = sum((_number(primary["breadth"][y])-_number(primary[baseline][y]) for y in selected), ZERO)
                checks[label+"_increment_vs_"+baseline+"_positive"] = len(years) == 9 and delta > 0
            discordant = any(r["date"][:4] in selected and r["signs"][0] != r["signs"][1] for r in regular)
            different = False
            if exposure_rows is not None:
                left = exposure_rows["min5_slip10/breadth"]
                right = exposure_rows["min5_slip10/own_trend"]
                if [(r["index"], r["date"]) for r in left] != [(r["index"], r["date"]) for r in right]:
                    raise ValueError("paired_exposure_rows_required")
                different = any(l["date"][:4] in selected and l["quantities"] != r["quantities"]
                                for l, r in zip(left, right))
            checks[label+"_discordant_signal_and_actual_exposure"] = len(years) == 9 and discordant and different
        for endpoint in ENDPOINTS:
            checks["primary_"+endpoint+"_adjusted_lower_positive"] = statistics.get("lower", {}).get("min5_slip10/"+endpoint, float("-inf")) > 0
        return dict(checks=checks, all_conditional_checks_pass=all(checks.values()),
                    source_nature=execution.source_nature, qualified=False, real_forward=0,
                    financial_verdict=execution.verdict, ordinary_signal_counts=sign_counts,
                    account_execution_disclosures={k: {f: s[f] for f in ("terminal_unsettled", "capacity_pass", "observed_maxDD")}
                                                   for k, s in summaries.items()},
                    interpretation="Paired seen-history policy diagnostics, including risk and cash exposure differences; never qualification.")


def _write(path, value):
    path = Path(path)
    raw = (json.dumps(_json(value), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
    intended = hashlib.sha256(raw).hexdigest()
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise ValueError("persisted_output_drift")
    return dict(path=str(path.resolve()), sha256=intended, bytes=len(raw))


def _run_matrix(fixture, *, context=None, output_dir=None):
    execution = _context(context)
    prepared = _prepare(fixture, context=context)
    directory = Path(output_dir) if output_dir else None
    if directory:
        directory.mkdir(parents=True, exist_ok=False)
    accounts, annual, summaries, events, exposure = {}, {}, {}, {}, {}
    for minimum, slip, policy in [(m, s, p) for m, s in COSTS for p in POLICIES]+[(0, 0, "cash")]:
        result = _run_prepared(prepared, policy, minimum, slip, context=context)
        cost = f"min{minimum}_slip{slip}"
        key = "cash" if policy == "cash" else cost+"/"+policy
        summaries[key], events[key] = result["summary"], result["event_attempts"]
        exposure[key] = [dict(index=d["index"], date=d["date"], quantities=d["after"]["quantities"]) for d in result["days"]]
        if policy != "cash":
            annual.setdefault(cost, {})[policy] = result["annual_contributions"]
        accounts[key] = (dict(artifact=_write(directory/(key.replace("/", "_")+".json"), result), summary=result["summary"])
                         if directory else result)
    statistics = paired_annual_bootstrap(annual, context=context)
    checks = _matrix_checks(summaries, annual, events, statistics, context=context,
                            exposure_rows=exposure, signal_rows=_json(prepared["signal_rows"]))
    result = dict(artifact_type=execution.artifact("matrix"), source_nature=execution.source_nature,
                  qualified=False, historical_returns_computed=execution.returns_computed, real_forward=0,
                  accounts=accounts, account_count=28, fixture_sha256=prepared["fixture_sha256"],
                  statistics=_write(directory/"statistics.json", statistics) if directory else statistics,
                  fixed_method_checks=checks, financial_verdict=execution.verdict)
    if directory:
        result["fixture"] = _write(directory/"fixture.json", fixture)
        _write(directory/"result.json", result)
    return result


def run_matrix(fixture, output_dir=None):
    """Public matrix entry is artificial only; it never opens source files."""
    return _run_matrix(fixture, output_dir=output_dir)


def run_loaded(fixture, *, context, output_dir=None):
    """Private controller convenience; once-only guards belong to that controller.

    The production controller uses _prepare/_run_prepared per account to apply
    its before/after source guards, rather than this in-memory convenience.
    """
    if type(context) is not _KnownHistoryContext:
        raise ValueError("known_history_context_required")
    return _run_matrix(fixture, context=context, output_dir=output_dir)

