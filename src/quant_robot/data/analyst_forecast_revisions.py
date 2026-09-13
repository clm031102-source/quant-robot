"""Conservative as-observed forecast transitions, independent of trading or factor admission."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from itertools import groupby

from quant_robot.data.analyst_forecast_events import AnalystForecastEvent


@dataclass(frozen=True)
class ForecastTransition:
    match_key: tuple[str, str, str, str]
    available_at: datetime
    kind: str
    current_version_id: str | None
    previous_version_id: str | None
    observed_version_ids: tuple[str, ...]
    source_sha256: tuple[str, ...]
    net_profit_change: Decimal | None = None
    net_profit_relative_change: Decimal | None = None
    net_profit_status: str = 'not_a_new_report_comparison'
    eps_relative_change: Decimal | None = None
    eps_status: str = 'not_a_new_report_comparison'
    eps_basis_identity: str | None = None
    historical_availability_verified: bool = False


@dataclass(frozen=True)
class _State:
    report_date: date
    event: AnalystForecastEvent | None


def build_revision_trace(
    events: Iterable[AnalystForecastEvent], *, as_of: datetime,
    eps_basis_ids: Mapping[str, str] | None = None,
) -> tuple[ForecastTransition, ...]:
    """Only eligible observations are inspected; supplied basis IDs do not certify their evidence."""
    if not isinstance(as_of, datetime) or as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError('as_of_timezone_required')
    cutoff = as_of.astimezone(timezone.utc)
    eligible = sorted((e for e in events if e.available_at <= cutoff),
                      key=lambda e: (e.available_at, e.match_key, e.record_id, e.version_id,
                                     e.observed_at, e.source_sha256, e.source_rows))
    unique: list[AnalystForecastEvent] = []
    versions: set[str] = set()
    updates: dict[tuple[str, datetime | None], str] = {}
    for event in eligible:
        key = event.record_id, event.provider_updated_at
        if key in updates and updates[key] != event.version_id:
            raise ValueError('conflicting_forecast_version')
        updates[key] = event.version_id
        if event.version_id not in versions:
            unique.append(event)
            versions.add(event.version_id)
    states: dict[tuple[str, str, str, str], _State] = {}
    output: list[ForecastTransition] = []
    for available, batch in groupby(unique, key=lambda e: e.available_at):
        groups: dict[tuple[str, str, str, str], list[AnalystForecastEvent]] = defaultdict(list)
        for event in batch:
            groups[event.match_key].append(event)
        for key in sorted(groups):
            row, state = _transition(groups[key], states.get(key), available, eps_basis_ids or {})
            states[key] = state
            output.append(row)
    return tuple(output)


def _transition(
    events: list[AnalystForecastEvent], state: _State | None, available: datetime,
    basis_ids: Mapping[str, str],
) -> tuple[ForecastTransition, _State]:
    latest_day = max(e.report_date for e in events)
    latest = [e for e in events if e.report_date == latest_day]
    prior = state.event if state else None

    def row(kind: str, current: AnalystForecastEvent | None = None, **metrics) -> ForecastTransition:
        sources = {e.source_sha256 for e in events}
        if prior:
            sources.add(prior.source_sha256)
        return ForecastTransition(events[0].match_key, available, kind,
                                  current.version_id if current else None,
                                  prior.version_id if prior else None,
                                  tuple(sorted(e.version_id for e in events)), tuple(sorted(sources)), **metrics)

    if state and latest_day < state.report_date:
        return row('late_report_ignored'), state
    if len({e.record_id for e in latest}) > 1:
        return row('ambiguous_report_order'), _State(latest_day, None)
    if len(latest) > 1 and any(e.provider_updated_at is None for e in latest):
        return row('ambiguous_provider_version'), _State(latest_day, None)
    current = max(latest, key=lambda e: e.provider_updated_at or datetime.min.replace(tzinfo=timezone.utc))
    new_state = _State(latest_day, current)
    if state is None:
        return row('baseline', current), new_state
    if prior is None:
        if latest_day <= state.report_date:
            return row('unresolved_ambiguity', current), state
        return row('baseline_after_ambiguity', current), new_state
    if latest_day == state.report_date:
        if current.record_id != prior.record_id:
            return row('ambiguous_report_order'), _State(latest_day, None)
        if current.provider_updated_at is None or prior.provider_updated_at is None:
            return row('ambiguous_provider_version'), _State(latest_day, None)
        if current.provider_updated_at <= prior.provider_updated_at:
            return row('stale_provider_version_ignored', current), state
        return row('provider_correction', current), new_state

    baseline_changed = any(
        e.record_id == prior.record_id and (
            e.provider_updated_at is None or prior.provider_updated_at is None
            or e.provider_updated_at > prior.provider_updated_at
        ) for e in events
    )
    if baseline_changed:
        return row('new_report_with_baseline_change', current,
                   net_profit_status='simultaneous_baseline_change',
                   eps_status='simultaneous_baseline_change'), new_state

    change, ratio, status = _changes(current.net_profit, prior.net_profit)
    current_basis = basis_ids.get(current.version_id)
    previous_basis = basis_ids.get(prior.version_id)
    if (isinstance(current_basis, str) and current_basis.strip() and current_basis == previous_basis):
        _, eps_ratio, eps_status = _changes(current.eps, prior.eps)
        basis = current_basis
    else:
        eps_ratio, eps_status, basis = None, 'share_basis_unverified', None
    return row('new_report_revision', current, net_profit_change=change,
               net_profit_relative_change=ratio, net_profit_status=status,
               eps_relative_change=eps_ratio, eps_status=eps_status,
               eps_basis_identity=basis), new_state


def _changes(current: Decimal | None, previous: Decimal | None) -> tuple[Decimal | None, Decimal | None, str]:
    if current is None:
        return None, None, 'missing_current_value'
    if previous is None:
        return None, None, 'missing_previous_value'
    with localcontext(Context(prec=64, rounding=ROUND_HALF_EVEN)):
        change = current - previous
        if previous == 0:
            return change, None, 'zero_previous_value'
        return change, change / abs(previous), 'matched_values'
