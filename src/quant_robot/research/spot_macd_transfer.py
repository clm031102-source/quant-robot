"""Frozen spot ledger with an unchanged invented-input public interface.

The separate claimed historical controller supplies explicit evidence identity
before a ledger runs. This module itself never reads market source files.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import (Decimal, Context, localcontext, ROUND_HALF_EVEN, ROUND_FLOOR,
                     ROUND_CEILING, InvalidOperation, DivisionByZero, Overflow, FloatOperation)
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

D = Decimal
ZERO, ONE = D(0), D(1)
STEP, QUANTUM, MINIMUM = D(".00001"), D(".00000001"), D(5)
INITIAL = D(1000)
METHOD_SHA = "6ec96945600c35d7c4f8c31fcd3c4d090535517a9d41948faa6387827953b9f0"
ARTIFICIAL = "invented_spot_transfer_fixture_v1"
SYMBOL = "ARTIFICIAL_BTCUSDT"
ORIGIN = date(2001, 1, 1)
ROLES = ("strategy", "holding", "cash")
CASES = tuple((f, s) for f in (5, 10, 20) for s in (0, 10, 30))


def context(precision=40):
    c = Context(prec=precision, rounding=ROUND_HALF_EVEN, Emin=-999999,
                Emax=999999, capitals=1, clamp=0)
    for signal in c.traps:
        c.traps[signal] = signal in (InvalidOperation, DivisionByZero, Overflow, FloatOperation)
    c.clear_flags()
    return c


def context_record(c):
    return dict(prec=c.prec, rounding=c.rounding, Emin=c.Emin, Emax=c.Emax,
                capitals=c.capitals, clamp=c.clamp,
                traps={k.__name__: v for k, v in c.traps.items()},
                flags={k.__name__: v for k, v in c.flags.items()})


def number(value, *, positive=False):
    if not isinstance(value, str):
        raise ValueError("Financial inputs must be decimal strings")
    result = D(value)
    if not result.is_finite() or result < 0 or (positive and result <= 0):
        raise ValueError("Invalid artificial numeric input")
    return result


def floor_step(q):
    return (q / STEP).to_integral_value(rounding=ROUND_FLOOR) * STEP


def up(q):
    return q.quantize(QUANTUM, rounding=ROUND_CEILING)


def down(q):
    return q.quantize(QUANTUM, rounding=ROUND_FLOOR)


def serial(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, dict):
        return {str(k): serial(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [serial(v) for v in value]
    return value


def canonical(value):
    return json.dumps(serial(value), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def macd_frame(close_strings):
    """Original forward-ratio/cumprod/ewm sequence, with an explicit context."""
    with localcontext(context(28)) as signal_ctx:
        closes = [number(v, positive=True) for v in close_strings]
        if not closes:
            raise ValueError("At least one artificial close required")
        ratios = [1.0] + [float(a / b) for a, b in zip(closes[1:], closes[:-1])]
        price = float(closes[0]) * pd.Series(ratios, dtype="float64").cumprod()
        if not np.isfinite(price).all() or (price <= 0).any():
            raise ValueError("Signal floating representation invalid")
        macd = price.ewm(span=12, adjust=False, min_periods=12).mean() - price.ewm(
            span=26, adjust=False, min_periods=26).mean()
        histogram = (macd - macd.ewm(span=9, adjust=False, min_periods=9).mean()) / price
        # Only the first33 observations may be unknown from frozen EMA warmup.
        # An overflow (or unexpected NaN) after that boundary is not a signal.
        if not np.isfinite(histogram.iloc[33:]).all():
            raise ValueError("Nonfinite computed MACD histogram")
        desired = pd.Series(pd.NA, index=price.index, dtype="boolean")
        known = histogram.notna()
        desired.loc[known] = histogram.loc[known] > 0
        result = pd.DataFrame(dict(signal_price=price, macd_histogram=histogram, desired=desired))
        result.attrs["decimal_context"] = context_record(signal_ctx)
        result.attrs["float_environment"] = dict(dtype="float64", numpy=np.__version__, pandas=pd.__version__)
        return result


@dataclass(frozen=True)
class Daily:
    day: str
    open: D
    high: D
    low: D
    close: D
    volume: D


@dataclass(frozen=True)
class Minute:
    day: str
    open: D
    volume: D


@dataclass(frozen=True)
class Prepared:
    daily: tuple[Daily, ...]
    execution: tuple[Minute, ...]
    warmup: int
    states: tuple[bool, ...]
    fixture_sha256: str
    signal_context_json: str


@dataclass(frozen=True)
class _HistoricalEvidence:
    source_nature: str
    registration_sha256: str
    normalized_input_sha256: str
    provenance_sha256: str

    def fields(self, artifact):
        actual = self.source_nature == "retained_official_history"
        return dict(artifact_type="conditional_historical_spot_"+artifact+"_v1",
            evidence_class="conditional_historical" if actual else "artificial_historical_adapter_test",
            historical_returns_computed=actual, source_nature=self.source_nature,
            registration_sha256=self.registration_sha256,
            normalized_input_sha256=self.normalized_input_sha256,
            provenance_sha256=self.provenance_sha256, real_forward_days_added=0)


def _claimed_evidence(claim, normalized_input_sha256, provenance_sha256):
    from quant_robot.research.spot_macd_transfer_admission import _Claim
    if (not isinstance(claim, _Claim) or not claim.active or not claim.decoding_started
            or claim.source_nature not in ("retained_official_history", "artificial_protocol_fixture")):
        raise ValueError("Active decoded claim required before historical ledger identity")
    for value in (normalized_input_sha256, provenance_sha256):
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("Exact normalized evidence digest required")
    return _HistoricalEvidence(claim.source_nature, claim.packet["registration_sha256"],
                               normalized_input_sha256, provenance_sha256)


def validate_synthetic_fixture(fixture):
    # Decimal parsing can signal InvalidOperation before any account exists.
    # Restore the caller's context on validation success AND exceptional exit.
    with localcontext(context()):
        return _validate_synthetic_fixture(fixture)


def _validate_synthetic_fixture(fixture):
    if (not isinstance(fixture, dict) or set(fixture) != {
            "artifact_type", "asset_id", "calendar_origin", "warmup_days", "daily", "execution"}
            or fixture["artifact_type"] != ARTIFICIAL or fixture["asset_id"] != SYMBOL
            or fixture["calendar_origin"] != ORIGIN.isoformat()):
        raise ValueError("Only declared invented2001-origin fixtures; no historical source/evidence")
    warmup = fixture["warmup_days"]
    if type(warmup) is not int or not 34 <= warmup <= 366:
        raise ValueError("Artificial warmup must be34..366complete observations")
    rows, minutes = fixture["daily"], fixture["execution"]
    if (not isinstance(rows, list) or not isinstance(minutes, list) or not 2 <= len(minutes) <= 1827
            or len(rows) != warmup + len(minutes) - 1):
        raise ValueError("Exact complete artificial daily and terminal-minute coverage required")
    daily, execution = [], []
    for i, r in enumerate(rows):
        if set(r) != {"date", "open", "high", "low", "close", "volume"} or r["date"] != (ORIGIN + timedelta(days=i)).isoformat():
            raise ValueError("Invented daily calendar/schema mismatch")
        o, h, l, c = (number(r[k], positive=True) for k in ("open", "high", "low", "close"))
        v = number(r["volume"])
        if l > min(o, c) or h < max(o, c) or h < l:
            raise ValueError("Inconsistent artificial OHLC")
        daily.append(Daily(r["date"], o, h, l, c, v))
    for i, r in enumerate(minutes):
        day = (ORIGIN + timedelta(days=warmup + i)).isoformat()
        if (set(r) != {"date", "open_time", "close_time", "open", "volume"}
                or r["date"] != day or r["open_time"] != day + "T00:03:00Z"
                or r["close_time"] != day + "T00:03:59.999Z"):
            raise ValueError("Exact invented00:03minute required")
        execution.append(Minute(day, number(r["open"], positive=True), number(r["volume"])))
    frame = macd_frame([r["close"] for r in rows])
    states = tuple(False if pd.isna(v) else bool(v) for v in frame.desired)
    return Prepared(tuple(daily), tuple(execution), warmup, states, hashlib.sha256(canonical(fixture)).hexdigest(),
                    json.dumps(dict(decimal=frame.attrs["decimal_context"], floating=frame.attrs["float_environment"]), sort_keys=True))


def fixed_artificial_fixture(*, sessions=1827, warmup=366):
    """Deterministic invented triangular prices, not a historical-date transform."""
    rows = []
    with localcontext(context()):
        for i in range(warmup + sessions - 1):
            phase = i % 60
            close = D(100) + D(min(phase, 60-phase)) / D(5)
            day = (ORIGIN + timedelta(days=i)).isoformat()
            rows.append(dict(date=day, open=str(close), high=str(close + 1), low=str(close - 1),
                             close=str(close), volume="100000"))
    minutes = []
    for i in range(sessions):
        day = (ORIGIN + timedelta(days=warmup+i)).isoformat()
        minutes.append(dict(date=day, open_time=day+"T00:03:00Z", close_time=day+"T00:03:59.999Z",
                            open=rows[warmup+i-1]["close"], volume="100000"))
    return dict(artifact_type=ARTIFICIAL, asset_id=SYMBOL, calendar_origin=ORIGIN.isoformat(),
                warmup_days=warmup, daily=rows, execution=minutes)


class _Account:
    """Internal state machine; public runs require validated invented input."""

    def __init__(self, case, role):
        if case not in CASES or role not in ROLES:
            raise ValueError("Frozen cases and roles only")
        self.case, self.role = case, role
        self.fee, self.slip = D(case[0])/10000, D(case[1])/10000
        self.cash, self.q, self.price = INITIAL, ZERO, ONE
        self.peak, self.reference, self.previous_dd, self.max_dd = INITIAL, INITIAL, ZERO, ZERO
        self.paused, self.cooldown, self.day_active, self.day_eligible = False, 0, False, True
        self.exited_residual, self.exit_reason, self.buy_index, self.active_cycle = False, None, None, None
        self.fills, self.rejections, self.risks, self.observations, self.curve = [], [], [], [], []
        self.cycles, self.lots, self.transitions, self.capacity_failures = [], [], [], []
        self.buy_debits, self.sell_credits, self.base_fees, self.quote_fees = ZERO, ZERO, ZERO, ZERO
        self.base_fee_value, self.rounding_cost = ZERO, ZERO
        self.tradable_exits = 0

    @property
    def nav(self):
        return self.cash + self.q*self.price

    @property
    def economic_flat(self):
        return self.q == 0 or (self.exited_residual and 0 < self.q < STEP)

    def tradable(self):
        q = floor_step(self.q)
        return q >= STEP and q*self.price*(ONE-self.slip) >= MINIMUM

    def observe(self, price, index, phase):
        self.price = price
        self.day_active = self.day_active or self.tradable()
        value = self.nav
        if self.cash < 0 or self.q < 0 or value <= 0 or self.q*price > value:
            raise ValueError("Invalid financial wallet")
        self.peak = max(self.peak, value)
        dd = ONE - value/self.peak
        loss = (self.reference-value)/self.reference
        self.max_dd = max(self.max_dd, dd)
        fresh = self.previous_dd < D(".40") <= dd
        dd_event = dd >= D(".40") and (self.day_active or fresh)
        daily_event = loss >= D(".02")
        trigger = dd_event or daily_event
        row = dict(index=index, phase=phase, price=price, cash=self.cash, BTC=self.q,
                   NAV=value, peak=self.peak, DD=dd, daily_loss=loss, day_active=self.day_active,
                   fresh_DD_cross=fresh, DD_event=dd_event, daily_event=daily_event, trigger=trigger)
        self.observations.append(row)
        if dd >= D(".40") or daily_event:
            self.risks.append(dict(row))
        if trigger:
            self.paused, self.cooldown, self.day_eligible = True, 0, False
            if self.q and not self.economic_flat:
                self.exit_reason = "risk"
        if not self.economic_flat or self.exit_reason:
            self.day_eligible = False
            self.cooldown = 0
        self.previous_dd = dd
        return trigger

    def start_day(self, index):
        self.reference = self.nav
        self.day_active = False
        self.day_eligible = self.economic_flat and self.exit_reason is None
        if self.paused and self.cooldown >= 5 and self.day_eligible:
            self.paused = False
            self.transitions.append(dict(index=index, kind="resume_after_five_complete_days", cooldown=self.cooldown))
            self.cooldown = 0

    def end_day(self, index, day):
        if self.paused:
            if self.day_eligible and self.economic_flat and self.exit_reason is None:
                self.cooldown += 1
            else:
                self.cooldown = 0
        prior = self.curve[-1]["NAV"] if self.curve else INITIAL
        self.curve.append(dict(index=index, date=day, kind="completed_daily", NAV=self.nav,
            PnL=self.nav-prior, cash=self.cash, BTC=self.q, mark=self.price,
            active_exposure=self.day_active, positive_inventory=self.q > 0,
            paused=self.paused, cooldown=self.cooldown, economic_flat=self.economic_flat))

    def plan(self, side, capacity, reason, index, cycle=None):
        p = self.price*(ONE+self.slip if side == "buy" else ONE-self.slip)
        q = floor_step(min(capacity, self.cash/p if side == "buy" else self.q))
        if side == "buy":
            while q > 0 and up(q*p) > self.cash:
                q -= STEP
        if q < STEP or q*p < MINIMUM or (side == "buy" and q-up(q*self.fee) <= 0):
            self.rejections.append(dict(index=index, phase="00:02", side=side, reason="planned_quantity_or_notional",
                                        intent=reason, planned_quantity=q, cycle=cycle))
            return None
        return dict(index=index, side=side, quantity=q, capacity=capacity, reason=reason, cycle=cycle,
                    planned_price=p, decision_time="00:02", execution_time="00:03")

    def _fifo_sale(self, q, gross, fee):
        remain, allocations = q, []
        for lot in self.lots:
            sold = min(remain, lot["remaining_BTC"])
            if sold <= 0:
                continue
            cost = lot["remaining_cost"] if sold == lot["remaining_BTC"] else lot["remaining_cost"]*sold/lot["remaining_BTC"]
            lot["remaining_BTC"] -= sold
            lot["remaining_cost"] -= cost
            remain -= sold
            allocations.append((lot, sold, cost))
            if remain == 0:
                break
        if remain:
            raise ValueError("FIFO inventory mismatch")
        gross_left, fee_left, output = gross, fee, []
        for i, (lot, sold, cost) in enumerate(allocations):
            last = i == len(allocations)-1
            g = gross_left if last else down(gross*sold/q)
            f = fee_left if last else down(fee*sold/q)
            gross_left -= g; fee_left -= f
            lot["realized_PnL"] += g-f-cost
            output.append(dict(cycle=lot["cycle"], quantity=sold, gross=g, quote_fee=f, released_cost=cost))
        return output

    def fill(self, order, raw_open, index):
        side, q = order["side"], order["quantity"]
        p = raw_open*(ONE+self.slip if side == "buy" else ONE-self.slip)
        debit = up(q*p)
        invalid = (q < STEP or q != floor_step(q) or q > order["capacity"] or q*p < MINIMUM
                   or (side == "buy" and (debit > self.cash or q-up(q*self.fee) <= 0))
                   or (side == "sell" and (q > self.q or down(q*p)-up(q*p*self.fee) < 0)))
        if invalid or (side == "buy" and self.paused):
            self.rejections.append(dict(order, phase="00:03", reject="execution_constraint_or_risk", actual_price=p))
            return None
        row = dict(order, actual_price=p, raw_open=raw_open, cash_before=self.cash, BTC_before=self.q)
        if side == "buy":
            fee = up(q*self.fee)
            net = q-fee
            self.cash -= debit; self.q += net
            self.buy_debits += debit; self.base_fees += fee; self.base_fee_value += fee*p
            self.rounding_cost += debit-q*p
            self.lots.append(dict(cycle=order["cycle"], buy_index=index, net_BTC=net, remaining_BTC=net,
                                  original_cost=debit, remaining_cost=debit, realized_PnL=ZERO))
            self.exited_residual, self.buy_index, self.active_cycle = False, index, order["cycle"]
            self.day_active, self.day_eligible = True, False
            row.update(base_fee=fee, quote_fee=ZERO, cash_debit=debit, net_BTC=net)
        else:
            gross, fee = down(q*p), up(q*p*self.fee)
            row["FIFO"] = self._fifo_sale(q, gross, fee)
            self.cash += gross-fee; self.q -= q
            self.sell_credits += gross-fee; self.quote_fees += fee
            self.rounding_cost += q*p-gross
            row.update(base_fee=ZERO, quote_fee=fee, gross_proceeds=gross, cash_credit=gross-fee)
            if self.q < STEP:
                self.exited_residual, self.exit_reason, self.buy_index = True, None, None
                self.tradable_exits += 1
        # An exit day is never a complete flat day, even after a dust-only close.
        self.day_eligible = False
        row.update(cash_after=self.cash, BTC_after=self.q)
        self.fills.append(row)
        self.observe(raw_open, index, "00:03_postfill")
        return row

    def finish(self, index, day):
        mark_nav = self.nav
        economic = self.cash if self.q < STEP else mark_nav
        after_dd = max(self.max_dd, ONE-economic/self.peak)
        prior = self.curve[-1]["NAV"] if self.curve else INITIAL
        self.curve.append(dict(index=index, date=day, kind="terminal_partial_interval", NAV=economic,
            mark_NAV=mark_nav, PnL=economic-prior, cash=self.cash, BTC=self.q, mark=self.price,
            active_exposure=self.day_active, positive_inventory=self.q > 0,
            paused=self.paused, cooldown=self.cooldown, economic_flat=self.economic_flat))
        cash_ok = self.cash == INITIAL-self.buy_debits+self.sell_credits
        qty_ok = self.q == sum((v["remaining_BTC"] for v in self.lots), ZERO)
        if not cash_ok or not qty_ok:
            raise ValueError("Account reconciliation failure")
        settled = self.economic_flat and self.exit_reason is None
        return dict(initial_cash=INITIAL, cash=self.cash, remaining_BTC=self.q, remaining_mark_value=self.q*self.price,
            mark_NAV=mark_nav, terminal_evaluation_NAV=economic, net_PnL=economic-INITIAL,
            dust_fully_haircut_cash_terminal=self.cash if self.q < STEP else None,
            exact_inventory_zero=self.q == 0, terminal_strict_unsettled=self.q != 0,
            terminal_economic_flat=settled, pending_exit=self.exit_reason,
            sampled_DD_before_haircut=self.max_dd, sampled_DD_including_terminal_haircut=after_dd,
            strict_completed_episodes=sum(lot["remaining_BTC"] == 0 for lot in self.lots),
            tradable_exit_episodes=self.tradable_exits, buy_fee_BTC=self.base_fees,
            buy_fee_quote_reporting=self.base_fee_value, sell_fee_USDT=self.quote_fees,
            quote_rounding_cost=self.rounding_cost, fill_count=len(self.fills), rejection_count=len(self.rejections),
            skipped_entry_cycles=sum(c["entry_status"] != "planned" for c in self.cycles),
            account_reconciled=cash_ok and qty_ok,
            execution_capacity_unverified=bool(self.capacity_failures),
            full_cash_days=sum(row["BTC"] == 0 for row in self.curve),
            nontradable_days=sum(not row["active_exposure"] for row in self.curve),
            average_cash=sum((row["cash"] for row in self.curve), ZERO)/len(self.curve),
            common_valid=settled and after_dd <= D(".4") and not self.capacity_failures and cash_ok and qty_ok)


def _run_prepared(prepared, case, role, *, evidence=None):
    if evidence is not None and (not isinstance(evidence, _HistoricalEvidence)
            or evidence.normalized_input_sha256 != prepared.fixture_sha256):
        raise ValueError("Historical prepared identity mismatch")
    with localcontext(context()) as ctx:
        a = _Account(case, role)
        previous_desired, episode = False, 0
        n, w = len(prepared.execution), prepared.warmup
        for i, minute in enumerate(prepared.execution):
            prior = prepared.daily[w+i-1]
            if i:
                a.observe(prior.close, i-1, "next00:02_completed_close")
                a.end_day(i-1, prior.day)
            else:
                a.price = prior.close
            a.start_day(i)
            desired = prepared.states[w+i-1]
            new_signal_cycle = desired and not previous_desired
            previous_desired = desired
            if new_signal_cycle:
                episode += 1
            is_entry = (new_signal_cycle if role == "strategy" else i % 253 == 0) and role != "cash"
            cycle = f"signal_{episode}" if role == "strategy" else f"holding_{i//253}"
            terminal = i == n-1
            # Establish terminal intent before any ordinary-entry boundary.
            reason = None
            if terminal:
                reason = "terminal"
            elif a.exit_reason == "risk":
                reason = "risk"
            elif a.buy_index is not None and i >= a.buy_index+252:
                reason = "252_due"
            elif role == "holding" and i % 253 == 252:
                reason = "holding_fixed_end"
            elif role == "strategy" and not desired and not a.economic_flat:
                reason = "signal_off"
            elif a.exit_reason:
                reason = a.exit_reason
            if reason and not a.economic_flat:
                a.exit_reason = reason
            capacity = sum((b.volume for b in prepared.daily[w+i-20:w+i]), ZERO)/20*D(".01")
            order = None
            if a.exit_reason and a.q:
                order = a.plan("sell", capacity, a.exit_reason, i, a.active_cycle)
            if is_entry:
                allowed = not terminal and a.economic_flat and not a.paused and not a.exit_reason and order is None
                entry_plan = a.plan("buy", capacity, "new_cycle", i, cycle) if allowed else None
                status = "planned" if entry_plan else ("plan_rejected" if allowed else "blocked_cycle_consumed")
                a.cycles.append(dict(index=i, cycle=cycle, entry_status=status, paused=a.paused,
                                     terminal=terminal, prior_desired=desired))
                if entry_plan:
                    order = entry_plan
            a.observe(minute.open, i, "00:03_prefill")
            fill = a.fill(order, minute.open, i) if order else None
            if order and order["side"] == "buy" and not fill:
                a.cycles[-1]["entry_status"] = "execution_rejected"
            if fill and fill["quantity"] > minute.volume*D(".01"):
                a.capacity_failures.append(dict(index=i, known_at="00:04", filled_quantity=fill["quantity"],
                                               minute_volume=minute.volume, conditional_fill_retained=True))
            if terminal:
                summary = a.finish(i, minute.day)
        identity = (dict(artifact_type="invented_spot_account_v1", evidence_class="synthetic_only",
            historical_returns_computed=False, fixture_sha256=prepared.fixture_sha256)
            if evidence is None else evidence.fields("account"))
        return serial(dict(**identity, qualified=False, method_sha256=METHOD_SHA,
            case_id=f"fee{case[0]}_slip{case[1]}",
            fee_bps=case[0], slippage_bps=case[1], role=role, summary=summary,
            daily_NAV=a.curve, fills=a.fills, rejections=a.rejections, risk_records=a.risks,
            observed_wallets=a.observations, cycles=a.cycles, lots=a.lots,
            recovery_transitions=a.transitions, capacity_failures=a.capacity_failures,
            signal_arithmetic=json.loads(prepared.signal_context_json), decimal_context=context_record(ctx)))


def run_account(fixture, *, case=(10, 10), role="strategy"):
    return _run_prepared(validate_synthetic_fixture(fixture), case, role)


def paired_bootstrap(accounts, *, evidence=None):
    """One shared index stream; no large replication/observation/endpoint tensor."""
    columns, keys, identity = [], [], None
    for f, s in CASES:
        key = f"fee{f}_slip{s}"
        strategy, holding = (accounts[f"{key}/{r}"] for r in ("strategy", "holding"))
        id_key = "fixture_sha256" if evidence is None else "normalized_input_sha256"
        expected_class = "synthetic_only" if evidence is None else evidence.fields("account")["evidence_class"]
        identity = strategy[id_key] if identity is None else identity
        if strategy[id_key] != identity:
            raise ValueError("Different source identity across cost cases")
        if any(a["evidence_class"] != expected_class or len(a["daily_NAV"]) != 1827 for a in (strategy, holding)):
            raise ValueError("Bootstrap requires1827 same-evidence intervals for every fixed account")
        if evidence is not None and any(any(a.get(k) != v for k,v in evidence.fields("account").items()) for a in (strategy,holding)):
            raise ValueError("Statistical evidence binding changed")
        for role in ("strategy", "holding"):
            if accounts[f"{key}/{role}"][id_key] != strategy[id_key]:
                raise ValueError("Different source identity")
        sv, hv = (np.array([float(row["PnL"]) for row in a["daily_NAV"]]) for a in (strategy, holding))
        columns.extend((sv, sv-hv)); keys.extend((key+"/net", key+"/minus_holding"))
    values = np.column_stack(columns)
    if values.shape != (1827, 18) or not np.isfinite(values).all():
        raise ValueError("Finite fixed statistical matrix required")
    rng, means = np.random.Generator(np.random.PCG64(20261107)), np.empty((5000, 18))
    offsets = np.arange(20)
    for replication in range(5000):
        starts = rng.integers(0, 1827, size=92)
        indexes = ((starts[:, None]+offsets) % 1827).ravel()[:1827]
        means[replication] = values[indexes].mean(axis=0)
    lower = np.quantile(means, .05/18, axis=0, method="linear")
    return dict(N=1827, replications=5000, block=20, starts_per_replication=92,
        seed=20261107, shared_indices_for_all18=True, units="USDT/observed interval",
        statistic="arithmetic_mean", endpoint_keys=keys, lower=dict(zip(keys, lower.tolist())),
        observed_means=dict(zip(keys, values.mean(axis=0).tolist())),
        replicate_means_sha256=hashlib.sha256(means.astype("<f8").tobytes()).hexdigest(),
        final_interval_is_partial=True, qualified=False)


def _persist(path, value):
    raw = canonical(value)+b"\n"
    with path.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    return dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def _conditional_checks(accounts, bootstrap):
    with localcontext(context()):
        checks = {"all18_common_valid": all(a["summary"]["common_valid"] for a in accounts.values() if a["role"] != "cash"),
                  "all9_cash_identity": all(D(a["summary"]["cash"]) == INITIAL and all(D(r["cash"]) == INITIAL and D(r["BTC"]) == 0 for r in a["daily_NAV"]) and not a["fills"] for a in accounts.values() if a["role"] == "cash")}
        if bootstrap:
            primary = accounts["fee10_slip10/strategy"]
            holding = accounts["fee10_slip10/holding"]
            pnl = [D(r["PnL"]) for r in primary["daily_NAV"]]
            annual = [sum(pnl[a:b], ZERO) for a, b in ((0,364),(364,730),(730,1095),(1095,1460),(1460,1825))]
            checks.update(primary_net_positive=D(primary["summary"]["net_PnL"]) > 0,
                primary_later_positive=sum(pnl[365:], ZERO) > 0,
                primary_beats_holding=D(primary["summary"]["net_PnL"]) > D(holding["summary"]["net_PnL"]),
                at_least_three_positive_attribution_years=sum(v > 0 for v in annual) >= 3,
                primary_strict_completed30=primary["summary"]["strict_completed_episodes"] >= 30,
                highcost_positive=D(accounts["fee20_slip30/strategy"]["summary"]["net_PnL"]) > 0,
                primary_net_lower_positive=bootstrap["lower"]["fee10_slip10/net"] > 0,
                primary_delta_lower_positive=bootstrap["lower"]["fee10_slip10/minus_holding"] > 0)
        else:
            annual = []
    return checks, annual


def run_synthetic_suite(fixture, *, output_dir=None):
    prepared = validate_synthetic_fixture(fixture)
    target = Path(output_dir) if output_dir is not None else None
    if target:
        target.mkdir(parents=True, exist_ok=True)
        if any(target.iterdir()):
            raise ValueError("New empty artificial output directory required")
    accounts, artifacts, input_artifacts = {}, {}, {}
    if target:
        input_artifacts["fixture"] = _persist(target/"fixture.json", fixture)
        input_artifacts["signal_states"] = _persist(target/"signal_states.json", dict(
            fixture_canonical_sha256=prepared.fixture_sha256, invented_only=True,
            signal_arithmetic=json.loads(prepared.signal_context_json),
            states=[dict(date=row.day, desired=state) for row, state in zip(prepared.daily, prepared.states)]))
    for case in CASES:
        for role in ROLES:
            key = f"fee{case[0]}_slip{case[1]}/{role}"
            account = _run_prepared(prepared, case, role)
            accounts[key] = account
            if target:
                artifacts[key] = _persist(target/(key.replace("/", "__")+".json"), account)
    bootstrap = paired_bootstrap(accounts) if len(prepared.execution) == 1827 else None
    checks, annual = _conditional_checks(accounts, bootstrap)
    result = serial(dict(artifact_type="invented_spot27_suite_v1", qualified=False,
        historical_returns_computed=False, financial_sources_read=0, method_sha256=METHOD_SHA,
        fixture_sha256=prepared.fixture_sha256, account_count=27, observations=len(prepared.execution),
        full_fixed_statistics_completed=bootstrap is not None, checks=checks,
        conditional_screen_passed=bool(bootstrap) and all(checks.values()),
        original_qualification_not_granted=True, primary_relative_attribution_blocks=annual,
        bootstrap=bootstrap, summaries={k:a["summary"] for k,a in accounts.items()}, artifacts=artifacts,
        input_artifacts=input_artifacts,
        limitations=["Allpricesinvented", "Holdingfixed252cycle_oneattempt_notuninterruptedbuyhold",
            "Dustnotzero", "HistoricalfiltersfeesPITunproved", "Native1000USDT_notCNYconversion",
            "Observedrisknotallpath", "Capacityauditnotactualdepth", "Noactualforwardevidence"]))
    if target:
        for ref in (*artifacts.values(), *input_artifacts.values()):
            if hashlib.sha256(Path(ref["path"]).read_bytes()).hexdigest() != ref["sha256"]:
                raise ValueError("Persisted account drift")
        _persist(target/"summary.json", result)
    return result
