"""Pure synthetic quantity planning; no calendar runner, market reads or qualification.

Prices and volume prefixes are supplied, completed observations. Planning calls
the existing accounting kernel on a private copy at those prices; actual future
fills must still pass the kernel's independent execution checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_CEILING, localcontext

from quant_robot.research.crypto_carry_model import (
    ATOM, MINUTE, ONE, ZERO, CarryModel, Leg, debit, dec, stamp,
)

TARGET = Decimal("0.80")
TRIGGER = Decimal("0.90")
DELTA_LIMIT = Decimal("0.005")
PARTICIPATION = Decimal("0.01")
SCENARIOS = frozenset(
    (spot, future, slip)
    for spot, future in ((Decimal(".001"), Decimal(".0005")),
                         (Decimal(".0015"), Decimal(".00075")),
                         (Decimal(".002"), Decimal(".001")))
    for slip in (Decimal(".0002"), Decimal(".0005"), Decimal(".001"))
)
MAX_SEARCH_STEPS = 1_000_000
REMAINING = (
    "daily_0002_and_transfer_0008_scheduler_not_implemented",
    "historical_runner_and_date_effective_source_rules_not_admitted",
    "actual_execution_prices_unknown_at_planning_time",
)


@dataclass(frozen=True)
class CompletedPrices:
    """Close of [minute_end-1m, minute_end), never that boundary's opening.

received_at is the actual availability clock of these prices. The scheduler
admits them to the live valuation before newer boundary events; planning alone
does not replace that ledger/risk stage.
    """
    minute_end: datetime
    received_at: datetime
    spot: Decimal
    future: Decimal
    mark: Decimal

    def __post_init__(self):
        for name in ("minute_end", "received_at"):
            object.__setattr__(self, name, stamp(getattr(self, name)))
        for name in ("spot", "future", "mark"):
            value = dec(getattr(self, name))
            if value <= 0:
                raise ValueError("Positive completed prices required")
            object.__setattr__(self, name, value)
        if self.minute_end.second or self.minute_end.microsecond or self.received_at < self.minute_end:
            raise ValueError("Completed minute and causal receive clock required")


@dataclass(frozen=True)
class VolumeMinute:
    minute_end: datetime
    received_at: datetime
    volume_btc: Decimal

    def __post_init__(self):
        for name in ("minute_end", "received_at"):
            object.__setattr__(self, name, stamp(getattr(self, name)))
        object.__setattr__(self, "volume_btc", dec(self.volume_btc))
        if (self.volume_btc < 0 or self.minute_end.second or self.minute_end.microsecond
                or self.received_at < self.minute_end):
            raise ValueError("Completed nonnegative volume and causal clock required")


@dataclass(frozen=True)
class PolicyPlan:
    status: str
    reason: str
    kind: str | None = None
    legs: tuple[Leg, ...] = ()
    final_short_btc: Decimal | None = None
    projected_nav: Decimal | None = None
    projected_gross: Decimal | None = None
    projected_delta_btc: Decimal | None = None
    candidates_checked: int = 0
    qualified: bool = False
    synthetic_only: bool = True
    real_forward: int = 0
    remaining: tuple[str, ...] = REMAINING
    equal_quantity_ceiling: Decimal | None = None


def volume_capacity(rows: tuple[VolumeMinute, ...] | list[VolumeMinute], *, decision_at: datetime) -> Decimal:
    """Exactly the prior twenty complete consecutive minutes, separately per market."""
    decision_at = stamp(decision_at)
    last = decision_at.replace(second=0, microsecond=0)
    if len(rows) != 20:
        raise ValueError("Exactly twenty completed volume minutes required")
    for index, row in enumerate(rows):
        if (not isinstance(row, VolumeMinute)
                or row.minute_end != last - (19 - index) * MINUTE
                or row.received_at > decision_at):
            raise ValueError("Missing, unordered, stale or unreceived volume minute")
    with localcontext() as context:
        context.prec = 40
        return sum((row.volume_btc for row in rows), ZERO) / 20 * PARTICIPATION


def _prepare(model, decision_at, prices, spot_minutes, futures_minutes):
    decision_at = stamp(decision_at)
    if model.now != decision_at or prices.minute_end != decision_at.replace(second=0, microsecond=0):
        raise ValueError("State and quotes must belong to this completed decision prefix")
    if prices.received_at > decision_at:
        raise ValueError("Unreceived quote cannot be used by planning")
    if (model.spot_price, model.future_price, model.mark_price) != (prices.spot, prices.future, prices.mark):
        raise ValueError("Kernel state and completed quotes disagree")
    if (model.fees.spot, model.fees.futures, model.fees.slippage) not in SCENARIOS:
        raise ValueError("Only the nine frozen fee/slippage scenarios are supported")
    # Eight-decimal base fee rounding requires an explicitly supported quantity
    # grid. Finer unknown precision is a source-contract gap, never rounded away.
    for rule in (model.spot_rule, model.futures_rule):
        if rule.quantity_step % ATOM or rule.min_quantity % ATOM:
            raise ValueError("Quantity grids finer than the eight-decimal contract are unsupported")
    return (volume_capacity(spot_minutes, decision_at=decision_at),
            volume_capacity(futures_minutes, decision_at=decision_at))


def _ceil_quantity(quantity, step):
    return (quantity / step).to_integral_value(rounding=ROUND_CEILING) * step


def _cover_net(required, *, step, fee):
    if required <= 0:
        return ZERO
    quantity = _ceil_quantity(required / (ONE - fee), step)
    # With the supported >=1e-8 grid, one extra grid unit covers the rounding
    # gap; keep the exact check, rather than assuming ideal proportional fees.
    while quantity - debit(quantity * fee) < required:
        quantity += step
    return quantity


def _project(model, legs, *, final_checks=True):
    """Use the frozen kernel itself, never a second wallet-accounting formula."""
    projected = model.planning_copy()
    for leg in legs:
        price = projected._fill_price(leg)
        reason = projected._rule_rejection(leg, price)
        if reason:
            return None, reason
        reason, _ = projected._apply_fill(leg, price)
        if reason:
            return None, reason
        # Both legs and their temporarily unhedged state remain subject to 1x.
        if projected.nav <= 0 or projected.gross > projected.nav:
            return None, "projected_interleg_gross_over_100_percent"
        if projected.short_btc and projected.futures_equity < projected.short_btc * projected.mark_price:
            return None, "projected_interleg_futures_wallet_below_1x"
    if final_checks and projected.gross > TARGET * projected.nav:
        return None, "projected_gross_above_target"
    if final_checks and abs(projected.delta_btc) * projected.spot_price > DELTA_LIMIT * projected.nav:
        return None, "projected_residual_delta_over_half_percent"
    return projected, None


def _minimum_quantity(rule, price):
    quantity = max(rule.quantity_step, _ceil_quantity(rule.min_quantity, rule.quantity_step),
                   _ceil_quantity(rule.min_notional / price, rule.quantity_step))
    # Decimal division cannot silently round a threshold into illegality.
    while rule.rejection(quantity, price):
        quantity += rule.quantity_step
    return quantity


def _reduction_legs(model, quantity, spot_capacity, future_capacity):
    first = Leg("short_close", model.short_btc - quantity, future_capacity)
    reduced, reason = _project(model, (first,), final_checks=False)
    if reduced is None:
        return (), reason
    rule = model.spot_rule
    sale_price = model.spot_price * (ONE - model.fees.slippage)
    minimum = _minimum_quantity(rule, sale_price)
    maximum = rule.floor_quantity(min(model.spot_btc, spot_capacity))
    if maximum < minimum:
        return (), "spot_minimum_quantity_notional_or_capacity"
    # Selling more reduces gross monotonically relative to the 80% NAV bound;
    # find the first legal sale on the quantity grid that covers trading costs.
    lo, hi = int(minimum / rule.quantity_step), int(maximum / rule.quantity_step)
    threshold = None
    while lo <= hi:
        middle = (lo + hi) // 2
        leg = Leg("spot_sell", middle * rule.quantity_step, spot_capacity)
        final, failure = _project(reduced, (leg,), final_checks=False)
        if final is not None and final.gross <= TARGET * final.nav:
            threshold, hi = middle, middle - 1
        else:
            lo = middle + 1
    if threshold is None:
        return (), "spot_capacity_cannot_reach_target"
    nearest_below = rule.floor_quantity(model.spot_btc - quantity)
    sale = max(threshold * rule.quantity_step, nearest_below)
    # The adjacent quantity can be needed when mismatched lot grids make the
    # positive residual illegal but the negative residual remains <=0.5% NAV.
    return tuple((first, Leg("spot_sell", q, spot_capacity)) for q in (sale, sale + rule.quantity_step)
                 if minimum <= q <= maximum), None


def plan_target(model: CarryModel, *, decision_at: datetime, prices: CompletedPrices,
                spot_minutes: tuple[VolumeMinute, ...] | list[VolumeMinute],
                futures_minutes: tuple[VolumeMinute, ...] | list[VolumeMinute]) -> PolicyPlan:
    """Largest feasible short below the conservative equal-quantity ceiling.

This is not a scheduler: the caller must separately establish a valid ordinary
decision time/priority. No real source, candidate or historical claim is made.
The ceiling is floor(0.80 * decision NAV / (spot + mark)) on the futures grid.
No residual-delta allowance or favorable execution basis expands that ceiling.
    """
    with localcontext() as context:
        context.prec = 40
        spot_capacity, future_capacity = _prepare(model, decision_at, prices, spot_minutes, futures_minutes)
        if model._finished or model.paused or model.terminal or model.transfer is not None or model.plan is not None:
            return PolicyPlan("blocked", "active_operation_pause_terminal_or_transfer")
        if model.unresolved:
            return PolicyPlan("blocked", "unresolved_state_requires_higher_priority_repair")
        if model.nav <= 0 or model.gross > model.nav or (model.short_btc and model.futures_equity < model.short_btc * model.mark_price):
            return PolicyPlan("blocked", "known_risk_breach_requires_exit")
        if abs(model.delta_btc) * model.spot_price > DELTA_LIMIT * model.nav:
            return PolicyPlan("blocked", "existing_delta_requires_repair")
        reducing = model.gross > TRIGGER * model.nav
        if not reducing and model.gross >= TARGET * model.nav:
            return PolicyPlan("no_action", "within_80_to_90_percent_band")
        if spot_capacity <= 0 or future_capacity <= 0:
            return PolicyPlan("blocked", "zero_completed_volume_capacity")
        ideal = TARGET * model.nav / (model.spot_price + model.mark_price)
        ceiling = model.futures_rule.floor_quantity(ideal)
        maximum = ceiling
        step = model.futures_rule.quantity_step
        if reducing:
            maximum = min(maximum, model.short_btc - step)
            lower = max(ZERO, model.short_btc - model.futures_rule.floor_quantity(future_capacity))
        else:
            maximum = min(maximum, model.short_btc + model.futures_rule.floor_quantity(future_capacity))
            lower = model.short_btc + step
        quantity, checked, last_reason = maximum, 0, "no_legal_pair_at_target"
        while quantity >= lower:
            if checked >= MAX_SEARCH_STEPS:
                return PolicyPlan("blocked", "search_budget_exhausted_no_maximum_certified", candidates_checked=checked,
                    equal_quantity_ceiling=ceiling)
            checked += 1
            if reducing:
                alternatives, reason = _reduction_legs(model, quantity, spot_capacity, future_capacity)
                if not alternatives:
                    last_reason = reason
            else:
                buy = _cover_net(quantity - model.spot_btc, step=model.spot_rule.quantity_step, fee=model.fees.spot)
                if buy <= 0:
                    # No synthetic redundant spot purchase: reuse sufficient
                    # inventory by opening only the required matching short.
                    legs = (Leg("short_open", quantity - model.short_btc, future_capacity),)
                else:
                    buy = max(buy, _minimum_quantity(model.spot_rule,
                        model.spot_price * (ONE + model.fees.slippage)))
                    legs = (Leg("spot_buy", buy, spot_capacity),
                            Leg("short_open", quantity - model.short_btc, future_capacity))
                alternatives = (legs,)
            for legs in alternatives:
                projected, reason = _project(model, legs)
                if projected is not None:
                    return PolicyPlan("planned", "largest_feasible_below_equal_quantity_ceiling", "rebalance" if reducing or model.short_btc else "entry",
                        legs, projected.short_btc, projected.nav, projected.gross, projected.delta_btc, checked,
                        equal_quantity_ceiling=ceiling)
                last_reason = reason
            quantity -= step
        return PolicyPlan("blocked", "no_legal_pair_at_target:" + last_reason, candidates_checked=checked,
            equal_quantity_ceiling=ceiling)


@dataclass(frozen=True)
class WalletState:
    """An explicitly supplied event-before/event-after state, not inferred fills."""
    at: datetime
    label: str
    spot_cash: Decimal
    futures_cash: Decimal
    spot_btc: Decimal
    short_btc: Decimal
    entry_vwap: Decimal
    in_transit: Decimal
    global_peak: Decimal
    daily_reference: Decimal

    def __post_init__(self):
        object.__setattr__(self, "at", stamp(self.at))
        if not isinstance(self.label, str) or not self.label:
            raise ValueError("Explicit state identity required")
        for name in ("spot_cash", "futures_cash", "spot_btc", "short_btc", "entry_vwap",
                     "in_transit", "global_peak", "daily_reference"):
            value = dec(getattr(self, name))
            # A funding shock may make futures cash negative; retain it so the
            # risk result can confirm insolvency instead of hiding the state.
            if (name != "futures_cash" and value < 0
                    or name in {"global_peak", "daily_reference"} and value == 0):
                raise ValueError("Invalid supplied wallet state")
            object.__setattr__(self, name, value)
        if self.short_btc > 0 and self.entry_vwap <= 0:
            raise ValueError("An existing short requires its entry VWAP")

    @classmethod
    def from_model(cls, model: CarryModel, *, label: str) -> WalletState:
        return cls(model.now, label, model.spot_cash, model.futures_cash,
            model.spot_btc, model.short_btc, model.entry_vwap,
            model.transfer.amount if model.transfer else ZERO, model.peak, model.daily_reference)


@dataclass(frozen=True)
class OHLCMinute:
    start: datetime
    end: datetime
    received_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self):
        for name in ("start", "end", "received_at"):
            object.__setattr__(self, name, stamp(getattr(self, name)))
        for name in ("open", "high", "low", "close"):
            object.__setattr__(self, name, dec(getattr(self, name)))
        if (self.start.second or self.start.microsecond or self.end != self.start + MINUTE
                or self.received_at < self.end
                or not ZERO < self.low <= min(self.open, self.close) <= max(self.open, self.close) <= self.high):
            raise ValueError("Complete valid OHLC minute required")


@dataclass(frozen=True)
class KnownPoint:
    at: datetime
    state_index: int
    spot: Decimal
    mark: Decimal

    def __post_init__(self):
        object.__setattr__(self, "at", stamp(self.at))
        for name in ("spot", "mark"):
            object.__setattr__(self, name, dec(getattr(self, name)))
        if type(self.state_index) is not int or self.state_index < 0 or min(self.spot, self.mark) <= 0:
            raise ValueError("Invalid discrete observation")


@dataclass(frozen=True)
class EnvelopeResult:
    status: str
    confirmed_breaches: tuple[str, ...]
    possible_breaches: tuple[str, ...]
    known_pause_triggers: tuple[str, ...]
    possible_pause_triggers: tuple[str, ...]
    known_touches: tuple[str, ...]
    coverage_complete: bool
    nav_min: Decimal
    nav_max: Decimal
    gross_max: Decimal
    margin_buffer_min: Decimal
    peak_upper_bound: Decimal
    drawdown_upper_bound: Decimal
    qualified: bool = False
    synthetic_only: bool = True
    real_forward: int = 0
    conclusion_scope: str = "conditional_on_supplied_complete_states_and_price_ranges_not_actual_path"


def _valuation(state, spot, mark):
    equity = state.futures_cash + state.short_btc * (state.entry_vwap - mark)
    return (state.spot_cash + state.spot_btc * spot + equity + state.in_transit,
            state.spot_btc * spot + state.short_btc * mark,
            equity - state.short_btc * mark)


def _risk_labels(state, nav, gross, margin_buffer, peak):
    breaches, pauses, touches = set(), set(), set()
    if nav <= 0:
        breaches.add("nonpositive_nav")
    if gross > nav:
        breaches.add("gross_over_100_percent")
    elif nav > 0 and gross == nav:
        touches.add("gross_at_100_percent")
    if state.short_btc > 0 and margin_buffer < 0:
        breaches.add("futures_wallet_below_1x")
    drawdown = ONE - nav / peak
    if drawdown > Decimal(".4"):
        breaches.add("global_drawdown_over_40_percent")
    if drawdown >= Decimal(".4"):
        pauses.add("drawdown_40_percent_trigger_requires_latch_processing")
    if nav <= Decimal(".98") * state.daily_reference:
        pauses.add("daily_loss_2_percent_trigger")
    return breaches, pauses, touches


def minute_risk_envelope(*, states: tuple[WalletState, ...] | list[WalletState],
                         spot: OHLCMinute, mark: OHLCMinute, evaluated_at: datetime,
                         known_points: tuple[KnownPoint, ...] | list[KnownPoint] = (),
                         coverage_complete: bool = False) -> EnvelopeResult:
    """Conservative rectangular extrema; never invent an intraminute chronology.

``coverage_complete`` is the caller's explicit event-state coverage assertion,
not independent source verification. Only supplied, causal discrete points can
confirm a breach. Rectangular worst cases can only make the path unresolved.
    """
    evaluated_at = stamp(evaluated_at)
    if (type(coverage_complete) is not bool or not states
            or spot.start != mark.start or spot.end != mark.end
            or max(spot.received_at, mark.received_at) > evaluated_at
            or states[0].at != spot.start):
        raise ValueError("A received aligned minute and its starting wallet state are required")
    for index, state in enumerate(states):
        if (not spot.start <= state.at < spot.end
                or index and (state.at < states[index-1].at or state.global_peak < states[index-1].global_peak)):
            raise ValueError("Event states must be a completed chronological prefix")
    for index, point in enumerate(known_points):
        if (point.state_index >= len(states)
                or not spot.low <= point.spot <= spot.high or not mark.low <= point.mark <= mark.high
                or point.at < states[point.state_index].at
                or point.at > (states[point.state_index+1].at if point.state_index+1 < len(states) else spot.end)
                or index and (point.at, point.state_index) < (known_points[index-1].at, known_points[index-1].state_index)):
            raise ValueError("Known points must belong to the supplied state/time/range")
    with localcontext() as context:
        context.prec = 40
        corners = [(state, *_valuation(state, s, m)) for state in states
                   for s in (spot.low, spot.high) for m in (mark.low, mark.high)]
        nav_min, nav_max = min(row[1] for row in corners), max(row[1] for row in corners)
        # Unknown ordering permits a high NAV before a low NAV, including across
        # event states. This deliberately overbounds; it is not an observed peak.
        peak_upper = max(nav_max, *(state.global_peak for state in states))
        possible, possible_pauses, confirmed, known_pauses, touches = set(), set(), set(), set(), set()
        for state, nav, gross, margin in corners:
            risks, pauses, _ = _risk_labels(state, nav, gross, margin, peak_upper)
            possible.update(risks)
            possible_pauses.update(pauses)
        known_peak = states[0].global_peak
        for point in known_points:
            state = states[point.state_index]
            nav, gross, margin = _valuation(state, point.spot, point.mark)
            known_peak = max(known_peak, state.global_peak, nav)
            risks, pauses, touch = _risk_labels(state, nav, gross, margin, known_peak)
            confirmed.update(risks)
            known_pauses.update(pauses)
            touches.update(touch)
        # Even a possible daily-stop event changes the subsequent operation
        # path. Do not call a financially bounded but operationally ambiguous
        # minute verified merely because the 40% financial gate stayed intact.
        status = ("confirmed_breach" if confirmed else "unresolved_path"
                  if possible or possible_pauses or not coverage_complete else "verified_within_envelope")
        return EnvelopeResult(status, tuple(sorted(confirmed)), tuple(sorted(possible)),
            tuple(sorted(known_pauses)), tuple(sorted(possible_pauses)), tuple(sorted(touches)),
            coverage_complete, nav_min, nav_max, max(row[2] for row in corners),
            min(row[3] for row in corners), peak_upper, max(ZERO, ONE - nav_min / peak_upper))
