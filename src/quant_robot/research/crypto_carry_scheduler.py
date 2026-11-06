"""Pure synthetic daily controller; exclusively owns kernel time advancement.

The caller supplies complete prefixes, actual execution openings, exact funding
events and explicit transfer confirmations. No source ingestion, historical
runner or candidate qualification is implemented here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, localcontext

from quant_robot.research.crypto_carry_model import CarryModel, Leg, MINUTE, ZERO, credit, dec, stamp
from quant_robot.research.crypto_carry_policy import CompletedPrices, TRIGGER, VolumeMinute, plan_target, volume_capacity


@dataclass(frozen=True)
class CompletedPrefix:
    prices: CompletedPrices
    spot_minutes: tuple[VolumeMinute, ...]
    futures_minutes: tuple[VolumeMinute, ...]

    def __post_init__(self):
        if not isinstance(self.prices, CompletedPrices):
            raise ValueError("Completed prices are required")
        for name in ("spot_minutes", "futures_minutes"):
            rows = tuple(getattr(self, name))
            if len(rows) != 20 or any(not isinstance(row, VolumeMinute)
                    or row.minute_end != self.prices.minute_end - (19-i)*MINUTE for i, row in enumerate(rows)):
                raise ValueError("Twenty complete consecutive volume minutes per market are required")
            object.__setattr__(self, name, rows)

    @property
    def available_at(self):
        return max(self.prices.received_at,
                   *(row.received_at for row in self.spot_minutes + self.futures_minutes))


@dataclass(frozen=True)
class TransferConfirmation:
    received_at: datetime
    due_at: datetime
    source: str
    amount: Decimal

    def __post_init__(self):
        object.__setattr__(self, "received_at", stamp(self.received_at))
        object.__setattr__(self, "due_at", stamp(self.due_at))
        object.__setattr__(self, "amount", dec(self.amount))
        if self.source not in {"spot", "futures"} or self.amount <= 0:
            raise ValueError("Explicit matching transfer confirmation required")


class SyntheticCarryScheduler:
    """Finite synthetic controller; queue facts then advance through this wrapper.

Direct model.run/register_plan calls after construction violate ownership and
are detected at the next wrapper operation. Hashes are not source provenance.
    """

    def __init__(self, model: CarryModel):
        if model.plan is not None or model.transfer is not None or model._finished:
            raise ValueError("Start the scheduler without a pre-existing pending operation")
        self.model = model
        self.prefixes: dict[datetime, CompletedPrefix] = {}
        self._completed_prices: dict[datetime, tuple[CompletedPrices, datetime]] = {}
        self.openings: set[datetime] = set()
        self.confirmations: dict[datetime, TransferConfirmation] = {}
        self.bindings: dict[int, dict] = {}
        self.journal: list[dict] = []
        self._daily_seen = set()
        self._boundary_seen = set()
        self._waiting_daily = None
        self._day_ends: dict[datetime, datetime] = {}
        self._cursor = self._kernel_cursor()

    def _kernel_cursor(self):
        return (self.model.now, len(self.model.journal), self.model._last_event_time, self.model._last_event_priority)

    def _owned(self):
        if self._kernel_cursor() != self._cursor:
            raise ValueError("External kernel advancement or operation bypassed scheduler ownership")

    def _sync(self):
        self._cursor = self._kernel_cursor()

    def _record(self, event, **fields):
        self.journal.append(dict(time=self.model.now.isoformat(), event=event, **fields))

    def queue_opening(self, at, *, spot, future=None, mark=None):
        self._owned()
        at = stamp(at)
        if at.second or at.microsecond or at in self.openings:
            raise ValueError("One explicit opening per complete-minute boundary required")
        self.model.queue_quote(at, spot=spot, future=future, mark=mark)
        self.openings.add(at)

    def queue_funding(self, at, *, rate, mark, synchronous_spot=None):
        self._owned()
        self.model.queue_funding(at, rate=rate, mark=mark, synchronous_spot=synchronous_spot)

    def queue_day_end(self, at):
        """Settle at the next 00:00 close, before that new day's other events.

The old final-microsecond label is accepted as a request label only. Its last
minute cannot be complete until the next boundary; no price is backdated.
        """
        self._owned()
        at = stamp(at)
        if (at.hour, at.minute, at.second, at.microsecond) == (23, 59, 59, 999999):
            boundary = at + timedelta(microseconds=1)
        elif (at.hour, at.minute, at.second, at.microsecond) == (0, 0, 0, 0):
            boundary = at
        else:
            raise ValueError("Day end requires a final-microsecond label or next UTC midnight")
        if boundary in self._day_ends:
            raise ValueError("Duplicate day-end request")
        self.model.queue_day_end(boundary, completed_close=True)
        self._day_ends[boundary] = at

    def _store_prefix(self, prefix, until):
        if not isinstance(prefix, CompletedPrefix) or prefix.available_at > until:
            raise ValueError("Only an already received complete prefix may be supplied")
        key = prefix.prices.minute_end
        if key > until:
            raise ValueError("Future completed prefix")
        if key in self.prefixes and self.prefixes[key] != prefix:
            raise ValueError("A previously supplied prefix is immutable")
        if key in self.prefixes:
            return
        self._store_completed_prices(prefix.prices, prefix.available_at, until)
        self.prefixes[key] = prefix

    def _store_completed_prices(self, prices, available_at, until):
        if not isinstance(prices, CompletedPrices) or not prices.received_at <= available_at <= until:
            raise ValueError("Received completed prices required independently of capacity history")
        previous = self._completed_prices.get(prices.minute_end)
        if previous is not None:
            if previous[0] != prices or available_at < previous[1]:
                raise ValueError("Previously supplied completed prices are immutable")
            return
        self.model.queue_completed_close(closed_at=prices.minute_end, available_at=available_at,
            price_received_at=prices.received_at, spot=prices.spot, future=prices.future, mark=prices.mark)
        self._completed_prices[prices.minute_end] = (prices, available_at)

    def _day_end_blocker(self, at):
        if at not in self._day_ends:
            return None
        close = self._completed_prices.get(at)
        if close is None or close[1] != at:
            return 'day_end_requires_received_completed_final_minute_at_midnight'
        return None

    def _prefix_at(self, trigger):
        key = trigger.replace(second=0, microsecond=0)
        prefix = self.prefixes.get(key)
        if prefix is None or prefix.available_at > trigger:
            return None
        volume_capacity(prefix.spot_minutes, decision_at=trigger)
        volume_capacity(prefix.futures_minutes, decision_at=trigger)
        return prefix

    def _bind_new_plan(self):
        plan = self.model.plan
        if plan is None or plan.number in self.bindings:
            return
        trigger = self.model.now
        prefix = self._prefix_at(trigger)
        binding = dict(trigger_at=trigger.isoformat(), kind=plan.kind,
                       sides=tuple(leg.side for leg in plan.legs), blocked_reason=None)
        if any(leg.capacity is None for leg in plan.legs):
            if prefix is None:
                binding['blocked_reason'] = 'missing_received_capacity_prefix_at_plan_trigger'
                self._record('new_plan_execution_blocked', number=plan.number, **binding)
                self.bindings[plan.number] = binding
                return
            spot_capacity = volume_capacity(prefix.spot_minutes, decision_at=trigger)
            futures_capacity = volume_capacity(prefix.futures_minutes, decision_at=trigger)
            plan.legs = tuple(Leg(leg.side, leg.quantity,
                leg.capacity if leg.capacity is not None else
                spot_capacity if leg.side.startswith('spot') else futures_capacity) for leg in plan.legs)
        binding['capacities'] = tuple(str(leg.capacity) for leg in plan.legs)
        binding['prefix_end'] = None if prefix is None else prefix.prices.minute_end.isoformat()
        self.bindings[plan.number] = binding
        self._record('plan_capacity_frozen', number=plan.number, **binding)

    def _due_fill_blocker(self, at):
        plan = self.model.plan
        if plan is None or not any(event[0] == at and event[3] == 'fill'
                and event[4] == (plan.number, plan.index) for event in self.model._events):
            return None
        binding = self.bindings.get(plan.number)
        if binding is None or binding.get('blocked_reason') or plan.legs[plan.index].capacity is None:
            return 'due_fill_has_no_trigger_time_capacity_binding'
        if at not in self.openings:
            return 'due_fill_requires_explicit_execution_opening'
        return None

    def _store_confirmation(self, receipt, until):
        if not isinstance(receipt, TransferConfirmation) or receipt.received_at > until:
            raise ValueError("A received transfer confirmation is required")
        transfer = self.model.transfer
        if (transfer is None or transfer.source != receipt.source or transfer.amount != receipt.amount
                or transfer.due != receipt.due_at):
            raise ValueError("Transfer confirmation does not match the outstanding operation")
        due_still_queued = any(event[3] == 'transfer' and event[4] is transfer for event in self.model._events)
        if receipt.received_at != receipt.due_at or self.model.now > receipt.due_at or not due_still_queued:
            self._record('late_confirmation_requires_reconciliation', received_at=receipt.received_at.isoformat())
            self._cancel_waiting_daily('late_transfer_confirmation')
            return
        previous = self.confirmations.get(receipt.due_at)
        if previous is not None and previous != receipt:
            raise ValueError("Conflicting transfer confirmation")
        self.confirmations[receipt.due_at] = receipt

    def _apply_confirmation_before_group(self, at):
        transfer = self.model.transfer
        if transfer is None or transfer.due != at:
            return
        receipt = self.confirmations.get(at)
        if receipt is not None:
            transfer.confirmed = True
            self._record('transfer_confirmation_applied', due=at.isoformat())

    def _equalize(self, *, purpose):
        if self.model.plan is not None or self.model.transfer is not None or self.model.unresolved:
            return False
        # The existing kernel rounds transfers down to eight decimals. Avoid
        # requesting a strictly positive sub-atom amount that rounds to zero.
        if credit(abs(self.model.spot_cash - self.model.futures_cash) / 2) == ZERO:
            return False
        if not self.model.equalize_cash():
            return False
        # No queue advancement occurs between creation and this conservative
        # confirmation state. Cash remains in transit until explicit evidence.
        self.model.transfer.confirmed = False
        self._record('await_explicit_transfer_confirmation', purpose=purpose,
                     source=self.model.transfer.source, amount=str(self.model.transfer.amount),
                     due=self.model.transfer.due.isoformat())
        return True

    def _after_group(self, journal_start):
        completed = [row['number'] for row in self.model.journal[journal_start:] if row['event'] == 'plan_completed']
        # Promoting an already pending partial reduction must first let its
        # second leg finish, then exit the remaining main position. Do not put
        # an equalizing transfer ahead of that terminal work.
        if (self.model.terminal and self.model.plan is None
                and (self.model.short_btc > 0 or self.model.has_tradable_spot())):
            self.model.request_exit(terminal=True)
        self._bind_new_plan()
        if any(self.bindings.get(number, {}).get('sides') == ('short_close', 'spot_sell') for number in completed):
            if self.model.plan is None and self.model.transfer is None:
                self._equalize(purpose='confirmed_paired_reduction')
        self._sync()

    def _cancel_waiting_daily(self, reason):
        if self._waiting_daily is not None:
            self._record('daily_opportunity_cancelled', day=self._waiting_daily['day'].isoformat(), reason=reason)
            self._waiting_daily = None

    def _planning_copy(self, prefix):
        model = self.model.planning_copy()
        model.spot_price, model.future_price, model.mark_price = (
            prefix.prices.spot, prefix.prices.future, prefix.prices.mark)
        return model

    def _register_policy(self, prefix, *, purpose):
        result = plan_target(self._planning_copy(prefix), decision_at=self.model.now, prices=prefix.prices,
            spot_minutes=prefix.spot_minutes, futures_minutes=prefix.futures_minutes)
        self._record('policy_decision', purpose=purpose, status=result.status, reason=result.reason,
                     ceiling=None if result.equal_quantity_ceiling is None else str(result.equal_quantity_ceiling))
        if result.status != 'planned':
            return
        accepted = self.model.register_plan(result.legs, kind=result.kind,
                                            first_at=self.model.now + MINUTE)
        self._record('policy_plan_registration', accepted=accepted, purpose=purpose)
        self._bind_new_plan()

    def _boundary(self):
        now = self.model.now
        if now.second or now.microsecond or now in self._boundary_seen:
            return
        self._boundary_seen.add(now)
        prefix = self._prefix_at(now)
        if self._waiting_daily is not None and now == self._waiting_daily['due']:
            arrived = any(row['event'] == 'transfer_arrived' and row['time'] == now.isoformat()
                          for row in self.model.journal)
            if (not arrived or self.model.transfer is not None or prefix is None
                    or self.model.plan is not None or self.model.paused or self.model.terminal):
                self._cancel_waiting_daily('due_confirmation_prefix_or_priority_missing')
            else:
                self._waiting_daily = None
                self._register_policy(prefix, purpose='daily_after_five_minute_transfer')
            return
        if now.hour == 0 and now.minute == 2:
            if now.date() in self._daily_seen:
                return
            self._daily_seen.add(now.date())
            if self.model.paused and self.model.cooldown_days >= 5 and self.model.cooldown_eligible():
                self.model.queue_resume(now)
                before = len(self.model.journal)
                self.model.run(now)
                self._after_group(before)
            if (prefix is None or self.model.plan is not None or self.model.transfer is not None
                    or self.model.paused or self.model.terminal or self.model.unresolved):
                self._record('daily_opportunity_cancelled', day=now.date().isoformat(), reason='prefix_or_higher_priority_state')
                return
            if self._equalize(purpose='daily_0002'):
                self._waiting_daily = dict(day=now.date(), due=self.model.transfer.due)
                return
            self._register_policy(prefix, purpose='daily_0002')
        elif prefix is not None and self.model.plan is None and self.model.transfer is None and not self.model.paused and not self.model.terminal:
            completed = self._planning_copy(prefix)
            if completed.nav > 0 and completed.gross > TRIGGER * completed.nav:
                self._register_policy(prefix, purpose='completed_minute_over_90_percent_reduction')

    def advance(self, until, *, prefix: CompletedPrefix | None = None,
                completed_prices: CompletedPrices | None = None,
                confirmation: TransferConfirmation | None = None, terminal_intent=False):
        """Run ordered whole event groups; stop before any unbound or unpriced fill.

Only the endpoint gets a scheduled boundary decision. Skipping 00:02 or 00:07
therefore cannot silently execute a late ordinary opportunity.
        """
        self._owned()
        until = stamp(until)
        if type(terminal_intent) is not bool or terminal_intent and (until.second or until.microsecond):
            raise ValueError("Terminal intent requires a complete-minute endpoint")
        if until < self.model.now or self.model._finished:
            raise ValueError("Cannot rewind or advance a finished synthetic account")
        if prefix is not None:
            self._store_prefix(prefix, until)
        if completed_prices is not None:
            self._store_completed_prices(completed_prices, completed_prices.received_at, until)
        if confirmation is not None:
            self._store_confirmation(confirmation, until)
        if self._waiting_daily is not None and until > self._waiting_daily['due']:
            self._cancel_waiting_daily('missed_0007_reassessment')
        with localcontext() as context:
            context.prec = 40
            while self.model._events and self.model._events[0][0] <= until:
                at = self.model._events[0][0]
                blocker = self._day_end_blocker(at) or self._due_fill_blocker(at)
                if blocker:
                    self._record('event_group_blocked', at=at.isoformat(), reason=blocker)
                    self._sync()
                    return self.snapshot(status='blocked', reason=blocker, blocked_at=at.isoformat())
                self._apply_confirmation_before_group(at)
                before = len(self.model.journal)
                self.model.run(at)
                if terminal_intent and at == until:
                    self._apply_terminal_intent()
                    terminal_intent = False
                self._after_group(before)
            if any(requested <= until < boundary for boundary, requested in self._day_ends.items()):
                reason = 'final_minute_not_complete_before_next_utc_boundary'
                self._record('event_group_blocked', at=until.isoformat(), reason=reason)
                self._sync()
                return self.snapshot(status='blocked', reason=reason, blocked_at=until.isoformat())
            before = len(self.model.journal)
            self.model.run(until)
            if terminal_intent:
                self._apply_terminal_intent()
            self._after_group(before)
            self._boundary()
            self._sync()
        return self.snapshot()

    def on_completed_prefix(self, prefix: CompletedPrefix):
        return self.advance(prefix.available_at, prefix=prefix)

    def request_terminal_exit(self):
        """Promote immediately at an already processed boundary.

For a cutoff that must precede that boundary's ordinary decisions, pass
terminal_intent=True to advance rather than calling this afterwards.
        """
        self._owned()
        if self.model.now.second or self.model.now.microsecond:
            raise ValueError("Terminal trigger requires an explicit current minute boundary")
        accepted = self._apply_terminal_intent()
        self._bind_new_plan()
        self._sync()
        return accepted

    def _apply_terminal_intent(self):
        """After existing events, before cash equalization or ordinary decisions."""
        self._cancel_waiting_daily('terminal_priority')
        accepted = self.model.request_exit(terminal=True)
        self._record('terminal_intent_applied_before_boundary', accepted=accepted)
        return accepted

    def snapshot(self, *, status='advanced', reason=None, blocked_at=None):
        return dict(status=status, reason=reason, blocked_at=blocked_at, qualified=False,
            synthetic_only=True, real_forward=0, historical_returns_computed=False,
            time=self.model.now.isoformat(), pending_daily_transfer=None if self._waiting_daily is None else
                dict(day=self._waiting_daily['day'].isoformat(), due=self._waiting_daily['due'].isoformat()),
            active_plan=None if self.model.plan is None else dict(number=self.model.plan.number,
                kind=self.model.plan.kind, next_leg_index=self.model.plan.index),
            capacity_bindings=deepcopy(self.bindings), kernel=self.model.snapshot(),
            remaining=['historical_runner_and_effective_source_contracts', 'statistical_bootstrap',
                       'caller_supplied_complete_funding_OHLC_event_coverage',
                       'caller_supplied_each_minute_close_and_day_end_calendar',
                       'outer_interval_2200_terminal_trigger_and_terminal_window',
                       'late_unconfirmed_transfer_reconciliation'])
