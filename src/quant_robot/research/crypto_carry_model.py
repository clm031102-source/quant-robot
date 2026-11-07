"""Pure synthetic BTC spot/USDT perpetual event-accounting kernel.

No network, filesystem, account connector, historical runner or promotion path.
Rules/prices supplied here are synthetic fixtures, not historical exchange facts.
This intentionally incomplete diagnostic always reports qualified=False.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, localcontext
import heapq
from typing import Any

ZERO = Decimal("0")
ONE = Decimal("1")
ATOM = Decimal("0.00000001")
MINUTE = timedelta(minutes=1)
PRIORITY = {"entry": 1, "rebalance": 1, "repair": 3, "risk_exit": 4, "terminal_exit": 5}
LEGACY_FUNDING = "event_mark_legacy"
CHARGE_BASIS_FUNDING = "charge_basis_last_known_market_v1"
INCOMPLETE = (
    "historical_inputs_and_date_effective_rules_not_admitted",
    "automatic_80_percent_target_search_not_implemented",
    "automatic_90_to_80_percent_rebalance_not_implemented",
    "twenty_minute_volume_capacity_estimation_not_implemented",
    "full_intraminute_OHLC_event_envelope_not_implemented",
    "exchange_liquidation_ADL_and_outage_execution_not_implemented",
    "daily_strategy_calendar_and_bootstrap_not_implemented",
)


def dec(value: Decimal | str | int) -> Decimal:
    if isinstance(value, (bool, float)) or not isinstance(value, (Decimal, str, int)):
        raise ValueError("Use finite Decimal, string or integer; binary floats are forbidden")
    result = Decimal(value)
    if not result.is_finite():
        raise ValueError("Nonfinite decimal")
    return result


def stamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("An explicit timezone is required")
    return value.astimezone(timezone.utc)


def debit(value: Decimal) -> Decimal:
    return value.quantize(ATOM, rounding=ROUND_CEILING)


def credit(value: Decimal) -> Decimal:
    # Positive receipts round down; negative receipts round away from zero.
    return value.quantize(ATOM, rounding=ROUND_FLOOR)


@dataclass(frozen=True)
class TradingRule:
    min_quantity: Decimal
    quantity_step: Decimal
    min_notional: Decimal

    def __post_init__(self):
        for name in ("min_quantity", "quantity_step", "min_notional"):
            object.__setattr__(self, name, dec(getattr(self, name)))
        if self.quantity_step <= 0 or self.min_quantity < 0 or self.min_notional < 0:
            raise ValueError("Invalid synthetic trading rule")

    def floor_quantity(self, quantity: Decimal) -> Decimal:
        return (quantity / self.quantity_step).to_integral_value(rounding=ROUND_FLOOR) * self.quantity_step

    def rejection(self, quantity: Decimal, price: Decimal) -> str | None:
        if quantity <= 0 or quantity < self.min_quantity:
            return "minimum_quantity"
        if quantity % self.quantity_step:
            return "quantity_step"
        if quantity * price < self.min_notional:
            return "minimum_notional"
        return None


@dataclass(frozen=True)
class FeeScenario:
    spot: Decimal = Decimal("0.0015")
    futures: Decimal = Decimal("0.00075")
    slippage: Decimal = Decimal("0.0005")

    def __post_init__(self):
        for name in ("spot", "futures", "slippage"):
            value = dec(getattr(self, name))
            if not ZERO <= value < ONE:
                raise ValueError("Invalid synthetic fee or slippage")
            object.__setattr__(self, name, value)


@dataclass(frozen=True)
class Leg:
    side: str
    quantity: Decimal
    capacity: Decimal | None = None

    def __post_init__(self):
        if self.side not in {"spot_buy", "spot_sell", "short_open", "short_close"}:
            raise ValueError("Unsupported leg")
        quantity = dec(self.quantity)
        if quantity <= 0:
            raise ValueError("Positive quantity required")
        object.__setattr__(self, "quantity", quantity)
        if self.capacity is not None:
            capacity = dec(self.capacity)
            if capacity < 0:
                raise ValueError("Negative capacity")
            object.__setattr__(self, "capacity", capacity)


@dataclass
class Plan:
    number: int
    kind: str
    legs: tuple[Leg, ...]
    index: int = 0
    fills: list[dict[str, Any]] = field(default_factory=list)
    repair_of: int | None = None


@dataclass
class Transfer:
    source: str
    amount: Decimal
    due: datetime
    confirmed: bool = True


@dataclass(frozen=True)
class EventWalletState:
    """Immutable diagnostic observation; contains no external model reference."""
    at: datetime
    event: str
    stage: str
    spot_cash: Decimal
    futures_cash: Decimal
    spot_btc: Decimal
    short_btc: Decimal
    entry_vwap: Decimal
    in_transit: Decimal
    global_peak: Decimal
    daily_reference: Decimal
    spot_price: Decimal | None
    future_price: Decimal | None
    mark_price: Decimal | None


@dataclass(frozen=True)
class FundingChargeEvent:
    """Charge basis only; contains no market valuation or execution quote."""
    at: datetime
    rate: Decimal
    charge_basis: Decimal

    def __post_init__(self):
        object.__setattr__(self, "at", stamp(self.at))
        object.__setattr__(self, "rate", dec(self.rate))
        object.__setattr__(self, "charge_basis", dec(self.charge_basis))
        if self.charge_basis <= 0:
            raise ValueError("Positive funding charge basis required")


@dataclass(frozen=True)
class MarketObservation:
    market: str
    source: str
    kind: str
    value: Decimal
    observed_at: datetime
    model_available_at: datetime


class CarryModel:
    """Single-threaded exact-time synthetic event queue, never a broker adapter."""

    def __init__(self, *, start: datetime, spot_rule: TradingRule, futures_rule: TradingRule,
                 fees: FeeScenario | None = None, spot_cash="500", futures_cash="500",
                 audit_event_states=False, funding_mode=LEGACY_FUNDING):
        if type(audit_event_states) is not bool:
            raise ValueError("Explicit boolean audit switch required")
        if funding_mode not in {LEGACY_FUNDING, CHARGE_BASIS_FUNDING}:
            raise ValueError("Explicit supported funding mode required")
        self.funding_mode = funding_mode
        self._market_observations: dict[str, MarketObservation] = {}
        self._market_sources: dict[tuple[str, datetime], dict[str, str]] = {}
        self.audit_event_states = audit_event_states
        self._event_state_trace: list[EventWalletState] = []
        self.now = stamp(start)
        self.spot_rule, self.futures_rule = spot_rule, futures_rule
        self.fees = fees or FeeScenario()
        self.spot_cash, self.futures_cash = dec(spot_cash), dec(futures_cash)
        if min(self.spot_cash, self.futures_cash) < 0:
            raise ValueError("Negative initial cash")
        self.spot_btc = self.short_btc = self.entry_vwap = ZERO
        self.spot_cost = self.realized_spot = self.realized_futures = ZERO
        self.funding_cash = self.fees_quote = self.base_fee_btc = ZERO
        self.spot_price = self.future_price = self.mark_price = None
        self.transfer: Transfer | None = None
        self.plan: Plan | None = None
        self.peak = self.spot_cash + self.futures_cash
        if self.peak <= 0:
            raise ValueError("Positive initial capital required")
        self.daily_reference = self.peak
        self.max_drawdown = ZERO
        self.dd_armed = True
        self.dd_events = 0
        self.paused = self.terminal = False
        self.cooldown_days = 0
        self.eligible_since: datetime | None = None
        self.last_counted_day = None
        self.failures: set[str] = set()
        self.unresolved: set[str] = set()
        self.journal: list[dict[str, Any]] = []
        self._events: list[tuple[datetime, int, int, str, Any]] = []
        self._sequence = self._plan_number = 0
        self._last_event_time = None
        self._last_event_priority = -1
        self._funding_times: set[datetime] = set()
        self._last_market_or_wallet_event_at = None
        self._last_completed_close = None
        self._finished = False

    def audit_states_since(self, cursor=0):
        if type(cursor) is not int or not 0 <= cursor <= len(self._event_state_trace):
            raise ValueError("Invalid audit cursor")
        return len(self._event_state_trace), tuple(self._event_state_trace[cursor:])

    def _audit_state(self, event, stage):
        if self.audit_event_states:
            self._event_state_trace.append(EventWalletState(self.now, event, stage,
                self.spot_cash, self.futures_cash, self.spot_btc, self.short_btc, self.entry_vwap,
                self.transfer.amount if self.transfer else ZERO, self.peak, self.daily_reference,
                self.spot_price, self.future_price, self.mark_price))

    def planning_copy(self):
        """Independent economic state; omit diagnostics during deepcopy itself."""
        clone = deepcopy(self, {id(self.journal): [], id(self._event_state_trace): []})
        clone.audit_event_states = False
        return clone

    def _record(self, event: str, **values):
        self.journal.append({"time": self.now.isoformat(), "event": event, **values})

    def _enqueue(self, at, priority, kind, payload, *, strictly_future=False):
        at = stamp(at)
        if self._finished:
            raise ValueError("Finished synthetic account cannot receive more events")
        if at < self.now or strictly_future and at <= self.now:
            raise ValueError("Cannot queue a past or same-time new operation")
        if at == self._last_event_time and priority < self._last_event_priority:
            raise ValueError("Cannot insert an earlier-priority event after processing that time")
        self._sequence += 1
        heapq.heappush(self._events, (at, priority, self._sequence, kind, payload))

    def _checked_market_sources(self, sources):
        if self.funding_mode == LEGACY_FUNDING:
            if sources is not None:
                raise ValueError("Market-source clocks require the explicit charge-basis mode")
            return None
        if (not isinstance(sources, dict) or set(sources) != {"spot", "mark"}
                or any(not isinstance(v, str) or not v.strip() for v in sources.values())):
            raise ValueError("Independent spot and mark source identities required")
        return dict(sources)

    def _observe_market(self, kind, observed_at, available_at):
        if self.funding_mode == CHARGE_BASIS_FUNDING:
            sources = self._market_sources.pop((kind, available_at))
            self._market_observations = {
                market: MarketObservation(market, sources[market], kind, value, observed_at, available_at)
                for market, value in (("spot", self.spot_price), ("mark", self.mark_price))}

    def _charge_valuation(self, at):
        """A carried boundary observation is a proxy, not a new synchronous fact."""
        boundary = at.replace(second=0, microsecond=0)
        result = {}
        for market, value in (("spot", self.spot_price), ("mark", self.mark_price)):
            row = self._market_observations.get(market)
            if (row is None or row.kind != "quote" or row.observed_at != boundary
                    or row.model_available_at > at or row.value != value):
                raise ValueError("Funding requires the current minute's independent market opening")
            age = at - row.observed_at
            result[market] = dict(value=str(value), source=row.source,
                market_observed_at=row.observed_at.isoformat(),
                model_available_at=row.model_available_at.isoformat(), used_at=at.isoformat(),
                age_model_ms=(age.days*86400+age.seconds)*1000+age.microseconds//1000,
                carried_forward=at != row.observed_at,
                instantaneous_at_event_certified=False)
        return result

    def queue_quote(self, at, *, spot, future=None, mark=None, market_sources=None):
        at = stamp(at)
        sources = self._checked_market_sources(market_sources)
        if self.funding_mode == CHARGE_BASIS_FUNDING and (mark is None or future is None
                or at.second or at.microsecond or ("quote", at) in self._market_sources):
            raise ValueError("Explicit independent prices at a unique minute opening required")
        values = tuple(dec(v) for v in (spot, future if future is not None else spot,
                                        mark if mark is not None else spot))
        if min(values) <= 0:
            raise ValueError("Positive synthetic prices required")
        self._enqueue(at, 0, "quote", values)
        self._enqueue(at, 4, "risk", None)
        if sources is not None:
            self._market_sources[("quote", at)] = sources

    def queue_funding(self, at, *, rate, mark, synchronous_spot=None):
        if self.funding_mode != LEGACY_FUNDING:
            raise ValueError("Use queue_funding_charge in the explicit charge-basis mode")
        at = stamp(at)
        rate, mark = dec(rate), dec(mark)
        if mark <= 0:
            raise ValueError("Positive event mark required")
        synchronous_spot = None if synchronous_spot is None else dec(synchronous_spot)
        if synchronous_spot is not None and synchronous_spot <= 0:
            raise ValueError("Positive explicitly synchronous event spot required")
        if at in self._funding_times:
            raise ValueError("Duplicate funding event time")
        self._enqueue(at, 1, "funding", (rate, mark, synchronous_spot))
        self._funding_times.add(at)

    def queue_funding_charge(self, at, *, rate, charge_basis):
        if self.funding_mode != CHARGE_BASIS_FUNDING:
            raise ValueError("Charge funding requires its explicit model mode")
        event = FundingChargeEvent(at, rate, charge_basis)
        if event.at in self._funding_times:
            raise ValueError("Duplicate funding event time")
        self._enqueue(event.at, 1, "funding_charge", event)
        self._funding_times.add(event.at)

    def queue_completed_close(self, *, closed_at, available_at, spot, future, mark,
                              price_received_at=None, market_sources=None):
        """Value a completed [t-1m,t) bar when available, before boundary events.

Late facts may only value an unchanged wallet/quote history. Otherwise reject
them instead of rewriting already processed openings, funding or inventory.
        """
        closed_at, available_at = stamp(closed_at), stamp(available_at)
        sources = self._checked_market_sources(market_sources)
        price_received_at = stamp(price_received_at or available_at)
        if (closed_at.second or closed_at.microsecond or not closed_at <= price_received_at <= available_at):
            raise ValueError("Completed-close clocks must be causal minute boundaries")
        values = tuple(dec(v) for v in (spot, future, mark))
        if min(values) <= 0:
            raise ValueError("Positive completed prices required")
        self._check_close_history(closed_at)
        if any(closed_at <= event[0] < available_at and event[3] in
               {"quote", "funding", "funding_charge", "transfer", "fill", "day_end"} for event in self._events):
            raise ValueError("Late completed close crosses a queued market or wallet event")
        if sources is not None and ("completed_close", available_at) in self._market_sources:
            raise ValueError("Duplicate completed market source clock")
        self._enqueue(available_at, -2, "completed_close",
                      (closed_at, available_at, price_received_at, values))
        if sources is not None:
            self._market_sources[("completed_close", available_at)] = sources

    def _check_close_history(self, closed_at):
        if (self._last_market_or_wallet_event_at is not None
                and self._last_market_or_wallet_event_at >= closed_at):
            raise ValueError("Late completed close cannot overwrite newer market or wallet events")
        if self._last_completed_close is not None and closed_at <= self._last_completed_close:
            raise ValueError("Completed-close time cannot repeat or move backwards")

    def queue_day_end(self, at, *, completed_close=False):
        """Strict mode settles the prior day at its next 00:00 completed close.

The legacy microsecond interface is a kernel-only synthetic convenience; it
does not certify minute coverage or a strict daily driver.
        """
        at = stamp(at)
        if completed_close:
            if (at.hour, at.minute, at.second, at.microsecond) != (0, 0, 0, 0):
                raise ValueError("Strict day end requires the next UTC midnight boundary")
            self._enqueue(at, -1, "day_end", at.date() - timedelta(days=1))
            return
        if (at.hour, at.minute, at.second, at.microsecond) != (23, 59, 59, 999999):
            raise ValueError("Day end must be the final microsecond of a UTC day")
        self._enqueue(at, 5, "day_end", None)

    def queue_resume(self, at):
        at = stamp(at)
        if (at.hour, at.minute, at.second, at.microsecond) != (0, 2, 0, 0):
            raise ValueError("Recovery is only considered at 00:02 UTC")
        self._enqueue(at, 6, "resume", None)

    def run(self, until: datetime):
        until = stamp(until)
        if self._finished:
            raise ValueError("Finished synthetic account cannot resume execution")
        if until < self.now:
            raise ValueError("Clock cannot move backwards")
        with localcontext() as context:
            context.prec = 40
            while self._events and self._events[0][0] <= until:
                next_at, _, _, next_kind, next_payload = self._events[0]
                if next_kind == "completed_close":
                    self._check_close_history(next_payload[0])
                if next_kind == "day_end" and next_payload is not None and self._last_completed_close != next_at:
                    raise ValueError("Strict day end requires its completed final minute")
                if next_kind == "funding_charge":
                    self._charge_valuation(next_at)
                self.now, priority, _, kind, payload = heapq.heappop(self._events)
                self._last_event_time, self._last_event_priority = self.now, priority
                self._audit_state(kind, "before")
                if kind == "completed_close":
                    closed_at, available_at, price_received_at, values = payload
                    self._check_close_history(closed_at)
                    self.spot_price, self.future_price, self.mark_price = values
                    self._observe_market(kind, closed_at, available_at)
                    self._last_completed_close = closed_at
                    self._record("completed_close", closed_at=closed_at.isoformat(),
                                 available_at=available_at.isoformat(), price_received_at=price_received_at.isoformat(),
                                 processed_at=self.now.isoformat(), nav=str(self.nav))
                    self._risk(observation="completed_minute_close")
                elif kind == "quote":
                    self.spot_price, self.future_price, self.mark_price = payload
                    self._observe_market(kind, self.now, self.now)
                    self._last_market_or_wallet_event_at = self.now
                    self._risk(observation="execution_opening_before_events")
                elif kind == "funding":
                    rate, event_mark, event_spot = payload
                    quantity_before = self.short_btc
                    if event_spot is not None:
                        self.spot_price = event_spot
                    self.mark_price = event_mark
                    self._audit_state(kind, "mark_before_cash")
                    self._risk(observation="funding_event_mark_before_cash")
                    amount = credit(quantity_before * event_mark * rate)
                    self.futures_cash += amount
                    self.funding_cash += amount
                    self.mark_price = event_mark
                    self._last_market_or_wallet_event_at = self.now
                    self._record("funding", quantity_before=str(quantity_before), cash_delta=str(amount),
                                 spot_observation="explicit_synchronous" if event_spot is not None else "unobserved_last_known_valuation")
                    self._risk()
                elif kind == "funding_charge":
                    quantity_before = self.short_btc
                    valuation = self._charge_valuation(self.now)
                    self._risk(observation="conditional_market_proxy_before_funding_cash")
                    self._audit_state(kind, "valuation_before_cash")
                    amount = credit(quantity_before * payload.charge_basis * payload.rate)
                    self.futures_cash += amount
                    self.funding_cash += amount
                    self._last_market_or_wallet_event_at = self.now
                    self._record("funding", funding_mode=self.funding_mode,
                        quantity_before=str(quantity_before), cash_delta=str(amount),
                        charge_basis=str(payload.charge_basis), rate=str(payload.rate), valuation=valuation,
                        spot_observation="last_known_market_proxy_not_new_synchronous_point",
                        cash_formula_and_availability="conditional_model_assumptions")
                    self._risk(observation="conditional_market_proxy_after_funding_cash")
                elif kind == "transfer":
                    self._last_market_or_wallet_event_at = self.now
                    self._settle_transfer(payload)
                elif kind == "fill":
                    self._last_market_or_wallet_event_at = self.now
                    self._execute_leg(payload)
                elif kind == "risk":
                    self._risk()
                elif kind == "day_end":
                    if payload is not None and self._last_completed_close != self.now:
                        raise ValueError("Strict day end requires its completed final minute")
                    self._day_end(day=payload)
                elif kind == "resume":
                    if self.paused and self.cooldown_days >= 5 and self.cooldown_eligible() and not self.terminal:
                        self.paused = False
                        self.cooldown_days = 0
                        self.eligible_since = None
                        self._record("diagnostic_resumed", financial_verdict=self.financial_verdict)
                self._refresh_cooldown()
                self._audit_state(kind, "after")
            self.now = until

    @property
    def unrealized_futures(self):
        return ZERO if self.mark_price is None else self.short_btc * (self.entry_vwap - self.mark_price)

    @property
    def futures_equity(self):
        return self.futures_cash + self.unrealized_futures

    @property
    def nav(self):
        spot_value = ZERO if self.spot_price is None else self.spot_btc * self.spot_price
        return self.spot_cash + spot_value + self.futures_equity + (self.transfer.amount if self.transfer else ZERO)

    @property
    def gross(self):
        if self.spot_price is None:
            return ZERO
        return self.spot_btc * self.spot_price + self.short_btc * self.mark_price

    @property
    def delta_btc(self):
        return self.spot_btc - self.short_btc

    @property
    def actually_flat(self):
        return self.spot_btc == 0 and self.short_btc == 0

    @property
    def financial_verdict(self):
        return "failed" if self.failures else "not_evaluated_synthetic_only"

    def _quoted(self):
        if self._finished:
            raise ValueError("Finished synthetic account is sealed")
        if self.spot_price is None:
            raise ValueError("A received synthetic quote is required")

    def _fill_price(self, leg):
        price = self.spot_price if leg.side.startswith("spot") else self.future_price
        buying = leg.side in {"spot_buy", "short_close"}
        return price * (ONE + self.fees.slippage if buying else ONE - self.fees.slippage)

    def _rule_rejection(self, leg, price):
        rule = self.spot_rule if leg.side.startswith("spot") else self.futures_rule
        return rule.rejection(leg.quantity, price) or (
            "capacity" if leg.capacity is not None and leg.quantity > leg.capacity else None)

    def register_plan(self, legs: tuple[Leg, ...], *, kind="entry", first_at=None) -> bool:
        self._quoted()
        if kind not in PRIORITY or not legs:
            raise ValueError("A supported nonempty plan is required")
        if self.plan is not None:
            raise ValueError("Only one active operation plan is allowed")
        if (self.paused or self.terminal or self.transfer is not None) and kind in {"entry", "rebalance"}:
            self._record("plan_rejected", reason="paused_terminal_or_transfer")
            return False
        next_boundary = self.now.replace(second=0, microsecond=0) + MINUTE
        first_at = stamp(first_at or next_boundary)
        if first_at < next_boundary or first_at.second or first_at.microsecond:
            raise ValueError("First leg must use a future complete-minute boundary")
        for leg in legs:
            reason = self._rule_rejection(leg, self._fill_price(leg))
            if (leg.side == "spot_sell" and leg.quantity > self.spot_btc
                    or leg.side == "short_close" and leg.quantity > self.short_btc):
                reason = "planned_inventory"
            if reason:
                self._record("plan_rejected", side=leg.side, reason=reason)
                if kind in {"risk_exit", "terminal_exit", "repair"}:
                    self.unresolved.add("exit_constraints")
                return False
        self._plan_number += 1
        self.plan = Plan(self._plan_number, kind, tuple(legs))
        self._enqueue(first_at, 3, "fill", (self.plan.number, 0), strictly_future=True)
        self._record("plan_registered", number=self.plan.number, kind=kind, first_at=first_at.isoformat())
        self._refresh_cooldown()
        return True

    def request_exit(self, *, terminal=False) -> bool:
        self._quoted()
        kind = "terminal_exit" if terminal else "risk_exit"
        if terminal:
            self.terminal = True
        if self.plan:
            if all(leg.side in {"short_close", "spot_sell"} for leg in self.plan.legs[self.plan.index:]):
                if PRIORITY[kind] > PRIORITY[self.plan.kind]:
                    self.plan.kind = kind
                    self._record("plan_promoted", number=self.plan.number, kind=kind)
                return True  # Keep its due second leg; never restart it every minute.
            self._record("entry_cancelled_for_exit", number=self.plan.number,
                         completed_legs=len(self.plan.fills))
            self.plan = None  # Already filled assets remain; stale queued legs are ignored.
        legs = []
        if self.short_btc > 0:
            legs.append(Leg("short_close", self.short_btc))
        sellable = self.spot_rule.floor_quantity(self.spot_btc)
        # Inventory below minimum notional/quantity is retained, not an order.
        # The separate dust/NAV limit still blocks cooldown for excessive dust;
        # an unclosed future still has its own mandatory exit leg and checks.
        if self.has_tradable_spot():
            legs.append(Leg("spot_sell", sellable))
        if not legs:
            return True
        return self.register_plan(tuple(legs), kind=kind)

    def _apply_fill(self, leg, price):
        q = leg.quantity
        if leg.side == "spot_buy":
            paid, base_fee = debit(q * price), debit(q * self.fees.spot)
            net = q - base_fee
            if paid > self.spot_cash or net <= 0:
                return "spot_cash_or_fee", None
            if self.gross + net * self.spot_price > self.nav - paid + net * self.spot_price:
                return "gross_entry_limit", None
            self.spot_cash -= paid
            self.spot_btc += net
            self.spot_cost += paid
            self.base_fee_btc += base_fee
            self.fees_quote += debit(base_fee * price)
            return None, {"side": leg.side, "quantity": q, "net_btc": net}
        if leg.side == "spot_sell":
            if q > self.spot_btc:
                return "spot_inventory", None
            received = credit(q * price)
            fee = debit(received * self.fees.spot)
            removed_cost = self.spot_cost * q / self.spot_btc
            self.spot_cost -= removed_cost
            self.spot_cash += received - fee
            self.spot_btc -= q
            self.realized_spot += received - fee - removed_cost
            self.fees_quote += fee
            return None, {"side": leg.side, "quantity": q, "net_btc": -q}
        fee = debit(q * price * self.fees.futures)
        if leg.side == "short_open":
            total = self.short_btc + q
            new_entry = (self.short_btc * self.entry_vwap + q * price) / total
            post_equity = self.futures_cash - fee + total * (new_entry - self.mark_price)
            if post_equity < Decimal("1.25") * total * self.mark_price:
                return "futures_125_percent_buffer", None
            post_nav = self.nav - fee + q * (price - self.mark_price)
            if self.gross + q * self.mark_price > post_nav:
                return "gross_entry_limit", None
            self.short_btc, self.entry_vwap = total, new_entry
            self.futures_cash -= fee
        else:
            if q > self.short_btc:
                return "short_inventory", None
            pnl = credit(q * (self.entry_vwap - price))
            if self.futures_cash + pnl - fee < 0:
                return "futures_cash_on_close", None
            self.futures_cash += pnl - fee
            self.realized_futures += pnl
            self.short_btc -= q
            if self.short_btc == 0:
                self.entry_vwap = ZERO
        self.fees_quote += fee
        return None, {"side": leg.side, "quantity": q, "net_btc": ZERO}

    def _execute_leg(self, identity):
        if self.plan is None or identity != (self.plan.number, self.plan.index):
            return
        plan, leg = self.plan, self.plan.legs[self.plan.index]
        price = self._fill_price(leg)
        reason = self._rule_rejection(leg, price)
        fill = None
        if reason is None:
            reason, fill = self._apply_fill(leg, price)
        if reason:
            self._record("leg_rejected", number=plan.number, side=leg.side, reason=reason)
            self.plan = None
            if plan.kind == "repair":
                self.unresolved.add("failed_repair")
            elif plan.fills:
                self.unresolved.add("pair_repair")
                previous = plan.fills[-1]
                if previous["side"] == "spot_buy":
                    quantity = self.spot_rule.floor_quantity(previous["net_btc"])
                    inverse = "spot_sell"
                elif previous["side"] == "short_close":
                    quantity, inverse = previous["quantity"], "short_open"
                else:
                    quantity, inverse = ZERO, "spot_sell"
                if quantity > 0 and self.register_plan((Leg(inverse, quantity),), kind="repair"):
                    self.plan.repair_of = plan.number
                else:
                    self.unresolved.add("failed_repair")
            elif plan.kind in {"risk_exit", "terminal_exit"}:
                self.unresolved.add("exit_constraints")
            self._risk()
            return
        plan.fills.append(fill)
        self._record("leg_filled", number=plan.number, side=leg.side,
                     quantity=str(leg.quantity), price=str(price))
        plan.index += 1
        if plan.index < len(plan.legs):
            self._enqueue(self.now + MINUTE, 3, "fill", (plan.number, plan.index), strictly_future=True)
        else:
            self.plan = None
            if plan.kind == "repair":
                self.unresolved.discard("pair_repair")
            if self.nav <= 0 or abs(self.delta_btc) * self.spot_price > Decimal("0.005") * self.nav:
                self.unresolved.add("delta_residual")
                if plan.kind != "repair" and self.nav > 0:
                    side = "spot_sell" if self.delta_btc > 0 else "short_close"
                    rule = self.spot_rule if side == "spot_sell" else self.futures_rule
                    amount = rule.floor_quantity(abs(self.delta_btc))
                    if amount > 0 and self.register_plan((Leg(side, amount),), kind="repair"):
                        self.plan.repair_of = plan.number
                    else:
                        self.unresolved.add("failed_repair")
                else:
                    self.unresolved.add("failed_repair")
            else:
                self.unresolved.discard("delta_residual")
            if self.short_btc == 0 and not self.has_tradable_spot():
                self.unresolved.discard("exit_constraints")
            self._record("plan_completed", number=plan.number, kind=plan.kind)
        self._risk()

    def request_transfer(self, source: str, amount, *, confirmed=True) -> bool:
        self._quoted()
        amount = credit(dec(amount))
        if source not in {"spot", "futures"} or amount <= 0:
            raise ValueError("Positive transfer and valid source required")
        if self.transfer or self.plan:
            self._record("transfer_rejected", reason="pending_operation")
            return False
        available = self.spot_cash if source == "spot" else self.futures_cash
        if amount > available or source == "futures" and self.futures_equity - amount < Decimal("1.25") * self.short_btc * self.mark_price:
            self._record("transfer_rejected", reason="cash_or_125_percent_buffer")
            return False
        self._audit_state("transfer_request", "before")
        if source == "spot":
            self.spot_cash -= amount
        else:
            self.futures_cash -= amount
        self.transfer = Transfer(source, amount, self.now + 5 * MINUTE, confirmed)
        self._last_market_or_wallet_event_at = self.now
        self._enqueue(self.transfer.due, 2, "transfer", self.transfer, strictly_future=True)
        self._record("transfer_pending", source=source, amount=str(amount), due=self.transfer.due.isoformat())
        self._refresh_cooldown()
        self._audit_state("transfer_request", "after")
        return True

    def equalize_cash(self) -> bool:
        self._quoted()
        if self.transfer or self.plan:
            return False
        half = (self.spot_cash + self.futures_cash) / 2
        if self.spot_cash > half:
            return self.request_transfer("spot", self.spot_cash - half)
        capacity = min(self.futures_cash, self.futures_equity - Decimal("1.25") * self.short_btc * self.mark_price)
        amount = credit(min(self.futures_cash - half, max(ZERO, capacity)))
        return self.request_transfer("futures", amount) if amount > 0 else False

    def _settle_transfer(self, transfer):
        if self.transfer is not transfer:
            return
        if not transfer.confirmed:
            self.unresolved.add("unconfirmed_transfer")
            self._record("transfer_unconfirmed", amount=str(transfer.amount))
            return
        if transfer.source == "spot":
            self.futures_cash += transfer.amount
        else:
            self.spot_cash += transfer.amount
        self.transfer = None
        self._record("transfer_arrived", amount=str(transfer.amount))
        self._risk()

    def has_tradable_spot(self):
        if self.spot_price is None:
            return False
        q = self.spot_rule.floor_quantity(self.spot_btc)
        return q > 0 and self.spot_rule.rejection(q, self.spot_price * (ONE - self.fees.slippage)) is None

    def cooldown_eligible(self):
        return (self.spot_price is not None and self.short_btc == 0 and self.plan is None
                and self.transfer is None and not self.unresolved and not self.has_tradable_spot()
                and self.nav > 0 and self.spot_btc * self.spot_price <= Decimal("0.001") * self.nav)

    def _refresh_cooldown(self):
        if self.paused and self.cooldown_eligible():
            if self.eligible_since is None:
                self.eligible_since = self.now
        elif self.paused:
            self.eligible_since, self.last_counted_day, self.cooldown_days = None, None, 0

    def _risk(self, *, observation="state_after_event"):
        if self.spot_price is None:
            return
        nav = self.nav
        self.peak = max(self.peak, nav)
        drawdown = ONE - nav / self.peak
        self.max_drawdown = max(self.max_drawdown, drawdown)
        stop = False
        reasons = []
        if drawdown < Decimal("0.4"):
            self.dd_armed = True
        elif self.dd_armed:
            self.dd_armed = False
            self.dd_events += 1
            stop = True
            reasons.append("drawdown_40_event")
            self._record("drawdown_40_event", number=self.dd_events)
        if drawdown > Decimal("0.4"):
            self.failures.add("global_drawdown_over_40_percent")
            reasons.append("global_drawdown_over_40_percent")
        if nav < 0 or self.gross > nav:
            self.failures.add("gross_over_100_percent")
            stop = True
            reasons.append("gross_over_100_percent")
        if self.short_btc > 0 and self.futures_equity < self.short_btc * self.mark_price:
            self.failures.add("futures_wallet_below_1x")
            stop = True
            reasons.append("futures_wallet_below_1x")
        if nav <= self.daily_reference * Decimal("0.98"):
            stop = True
            reasons.append("daily_loss_2_percent")
        if stop:
            self._record("risk_observation", observation=observation, reasons=reasons,
                         nav=str(nav), gross=str(self.gross), futures_equity=str(self.futures_equity),
                         short_mark_notional=str(self.short_btc * self.mark_price),
                         daily_reference=str(self.daily_reference), drawdown=str(drawdown))
            self.paused = True
        if self.paused and not self.actually_flat:
            # A partial reduction may restore the instantaneous limits; it
            # does not cancel the already latched pause/exit obligation.
            self.request_exit()
        self._refresh_cooldown()

    def _day_end(self, *, day=None):
        self._risk()
        day = day or self.now.date()
        start = datetime.combine(day, datetime.min.time(), timezone.utc)
        if (self.paused and self.cooldown_eligible() and self.eligible_since is not None
                and self.eligible_since <= start and self.last_counted_day != day):
            if self.last_counted_day is not None and day != self.last_counted_day + timedelta(days=1):
                self.cooldown_days = 0
            self.cooldown_days += 1
            self.last_counted_day = day
        self.daily_reference = self.nav
        self._record("day_end", day=day.isoformat(), reference_nav=str(self.daily_reference),
                     cooldown_days=self.cooldown_days)

    def finish(self) -> dict[str, Any]:
        self._quoted()
        self.terminal = True
        book_nav = self.nav
        unresolved_terminal = (self.short_btc > 0 or self.has_tradable_spot()
                               or self.plan is not None or self.transfer is not None or bool(self.unresolved))
        if unresolved_terminal:
            self.failures.add("terminal_unsettled")
            conservative = None
        else:
            conservative = book_nav - self.spot_btc * self.spot_price
            terminal_dd = ONE - conservative / self.peak
            self.max_drawdown = max(self.max_drawdown, terminal_dd)
            if terminal_dd > Decimal("0.4"):
                self.failures.add("global_drawdown_over_40_percent")
        self._finished = True
        return {**self.snapshot(), "book_nav": str(book_nav),
                "conservative_terminal_nav": None if conservative is None else str(conservative),
                "terminal_unsettled": unresolved_terminal, "inventory_deleted": False}

    def snapshot(self) -> dict[str, Any]:
        return {
            "synthetic_only": True, "qualified": False, "real_forward": 0,
            "diagnostic_engine_incomplete": list(INCOMPLETE), "historical_returns_computed": False,
            "time": self.now.isoformat(), "spot_cash": str(self.spot_cash),
            "futures_cash": str(self.futures_cash), "spot_btc": str(self.spot_btc),
            "short_btc": str(self.short_btc), "entry_vwap": str(self.entry_vwap),
            "realized_spot": str(self.realized_spot), "realized_futures": str(self.realized_futures),
            "unrealized_futures": str(self.unrealized_futures), "funding_cash": str(self.funding_cash),
            "base_fee_btc": str(self.base_fee_btc), "fees_quote": str(self.fees_quote),
            "in_transit": str(self.transfer.amount if self.transfer else ZERO),
            "nav": str(self.nav), "gross": str(self.gross), "delta_btc": str(self.delta_btc),
            "gross_above_90_percent": self.nav > 0 and self.gross > Decimal("0.9") * self.nav,
            "actually_flat": self.actually_flat, "cooldown_eligible": self.cooldown_eligible(),
            "untradable_spot_value": str(
                self.spot_btc * self.spot_price if self.spot_price is not None and not self.has_tradable_spot() else ZERO),
            "cooldown_days": self.cooldown_days, "paused": self.paused,
            "global_peak": str(self.peak), "max_drawdown": str(self.max_drawdown),
            "dd_armed": self.dd_armed, "dd_events": self.dd_events,
            "financial_verdict": self.financial_verdict, "failures": sorted(self.failures),
            "unresolved": sorted(self.unresolved), "active_plan": None if not self.plan else {
                "number": self.plan.number, "kind": self.plan.kind, "next_leg_index": self.plan.index},
        }
