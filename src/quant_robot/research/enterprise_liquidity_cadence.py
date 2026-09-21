"""Fixed release/expiration cadence; source values and calendars only, no outcomes."""
from bisect import bisect_left
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import json
import re

FRESHNESS_DAYS = 124


def _day(value):
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('ISO calendar date required')
    return parsed


def _quarter(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}Q[1-4]', value):
        raise ValueError('YYYYQ1..4 survey quarter required')
    return int(value[:4])*4 + int(value[-1])-1


def _sources(reports, cutoff):
    seen, result = set(), []
    for original in reports:
        q = original['quarter']
        ordinal = _quarter(q)
        if q in seen:
            raise ValueError('One frozen original per survey quarter required')
        seen.add(q)
        day = _day(original['available_date'])
        try:
            value = None if original['index_percent'] is None else Decimal(str(original['index_percent']))
        except InvalidOperation as exc:
            raise ValueError('Numeric or unavailable survey level required') from exc
        if value is not None and (not value.is_finite() or not 0 <= value <= 100):
            raise ValueError('Finite survey level within0..100 required')
        if day <= cutoff:
            result.append(dict(quarter=q, ordinal=ordinal, available_date=day,
                               expires=day+timedelta(days=FRESHNESS_DAYS), value=value))
    return sorted(result, key=lambda row: (row['available_date'], row['ordinal']))


def _decision(latest, history, day):
    if latest is None:
        return dict(state=None, quarter=None, available_date=None, reason='no_report')
    base = dict(quarter=latest['quarter'], available_date=latest['available_date'].isoformat())
    if day > latest['expires']:
        return dict(base, state=None, reason='expired')
    prior = history.get(latest['ordinal']-4)
    if latest['value'] is None:
        return dict(base, state=None, reason='report_unavailable')
    if prior is None or prior['value'] is None:
        return dict(base, state=None, reason='comparison_missing')
    selected = int(latest['value'] > prior['value'])
    return dict(base, state=selected, reason='improved' if selected else 'not_improved')


def event_intervals(reports, sessions, *, start='2013-01-01', terminal='2024-01-02',
                    publication_cutoff='2023-12-31'):
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError('Unique chronological exchange sessions required')
    days = [_day(day) for day in sessions]
    start_day, terminal_day = _day(start), _day(terminal)
    if terminal not in sessions or start_day >= terminal_day:
        raise ValueError('Terminal exchange open after start required')
    active = [(i, day) for i, day in enumerate(days) if start_day <= day < terminal_day]
    if not active:
        raise ValueError('Nonempty exchange window required')
    sources = _sources(reports, _day(publication_cutoff))
    pointer, history, latest, expired = 0, {}, None, False
    events = []
    for index, day in active:
        previous_latest = latest
        # All announcements visible before this open are installed as one batch.
        while pointer < len(sources) and sources[pointer]['available_date'] < day:
            row = sources[pointer]
            history[row['ordinal']] = row
            if latest is None or row['ordinal'] > latest['ordinal']:
                latest = row
            pointer += 1
        new_latest = latest is not previous_latest
        expiry_event = latest is not None and day > latest['expires'] and not expired
        if not events or new_latest or expiry_event:
            decision = _decision(latest, history, day)
            events.append(dict(entry_date=day.isoformat(), entry_index=index, **decision,
                               event='initial' if not events else
                               ('latest_release' if new_latest else 'expiration')))
            expired = decision['reason'] == 'expired'
    out, episode, episode_start = [], 0, None
    terminal_index = sessions.index(terminal)
    for index, event in enumerate(events):
        end_index = events[index+1]['entry_index'] if index+1 < len(events) else terminal_index
        duration = end_index-event['entry_index']
        if duration <= 0:
            raise ValueError('Zero/negative event interval rejected')
        if event['state'] == 1:
            if not out or out[-1]['state'] != 1:
                episode += 1
                episode_start = event['entry_date']
            episode_id = episode
        else:
            episode_id, episode_start = None, None
        out.append(dict(event, exit_date=sessions[end_index], sessions=duration,
                        episode_id=episode_id, episode_start=episode_start, carry_in=False))
    if sum(row['sessions'] for row in out) != terminal_index-active[0][0]:
        raise ValueError('Intervals must cover every session without gaps or overlaps')
    return out


def later_intervals(rows, sessions, *, boundary='2020-01-01'):
    if sessions != sorted(set(sessions)):
        raise ValueError('Unique chronological exchange sessions required')
    position = bisect_left(sessions, boundary)
    if position >= len(sessions):
        return []
    cutoff = sessions[position]
    locations = {day: i for i, day in enumerate(sessions)}
    out = []
    for row in rows:
        entry = max(row['entry_date'], cutoff)
        if entry >= row['exit_date']:
            continue
        out.append(dict(row, original_entry_date=row['entry_date'], entry_date=entry,
                        entry_index=locations[entry],
                        sessions=locations[row['exit_date']]-locations[entry],
                        carry_in=row['state'] == 1 and row['episode_start'] < cutoff))
    return out


def describe(rows):
    selected = [row for row in rows if row['state'] == 1]
    known_cash = [row for row in rows if row['state'] == 0]
    unknown = [row for row in rows if row['state'] is None]
    episodes = {row['episode_id'] for row in selected}
    carry = {row['episode_id'] for row in selected if row['carry_in']}
    return dict(intervals=len(rows), selected_intervals=len(selected),
                known_cash_intervals=len(known_cash), unknown_intervals=len(unknown),
                selected_episodes=len(episodes), new_selected_episodes=len(episodes-carry),
                carry_in_episodes=len(carry), total_sessions=sum(r['sessions'] for r in rows),
                selected_sessions=sum(r['sessions'] for r in selected),
                known_cash_sessions=sum(r['sessions'] for r in known_cash),
                unknown_sessions=sum(r['sessions'] for r in unknown),
                interval_session_min=min((r['sessions'] for r in rows), default=None),
                interval_session_max=max((r['sessions'] for r in rows), default=None))


def screen_counts(full_rows, later_rows):
    full, later = describe(full_rows), describe(later_rows)
    checks = dict(full_selected_intervals=full['selected_intervals'] >= 16,
                  full_selected_episodes=full['selected_episodes'] >= 6,
                  later_selected_intervals=later['selected_intervals'] >= 6,
                  later_new_selected_episodes=later['new_selected_episodes'] >= 3,
                  full_known_cash=full['known_cash_intervals'] > 0,
                  later_known_cash=later['known_cash_intervals'] > 0)
    return dict(full=full, later=later, checks=checks, passed=all(checks.values()))


def calculate(snapshots):
    from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
    sessions = []
    for role, first, last in [('old_calendar', date(2013, 1, 1), date(2014, 12, 31)),
                              ('calendar', date(2015, 1, 1), date(2024, 6, 28))]:
        days = calendar_rows_from_snapshot(snapshots[role], snapshots[role+'_manifest'],
                                          start=first, end=last)
        sessions.extend(str(day) for day, opened in days if opened)
    reports = json.loads(snapshots['source_inventory'])['rows']
    rows = event_intervals(reports, sessions)
    later = later_intervals(rows, sessions)
    counts = screen_counts(rows, later)
    return dict(intervals=rows, later_intervals=later, screen=counts,
                status='cadence_minima_passed_return_admission_pending' if counts['passed']
                else 'closed_insufficient_selected_observations',
                states_generated=True, ETF_outcomes_read=False, returns_computed=False,
                net_positive_EV_verified=False, new_return_studies=0,
                financial_execution_allowed=False, general_factor_batch_allowed=False,
                final_holdout_allowed=False, live_boundary_allowed=False)

