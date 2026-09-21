"""Frozen credit-premium quarterly cadence. Source values and calendars only."""
from bisect import bisect_left
from datetime import date
from decimal import Decimal, InvalidOperation
import json

from quant_robot.research.enterprise_liquidity_cadence import later_intervals, screen_counts


def month_name(ordinal):
    year, month = divmod(ordinal, 12)
    return f'{year:04d}-{month+1:02d}'


def monthly_premiums(rows):
    expected = [month_name(i) for i in range(2011*12+11, 2023*12+9)]
    if [row['month'] for row in rows] != expected:
        raise ValueError('Exact142chronological calendar months required, including unknowns')
    result = {}
    for row in rows:
        if row['status'] == 'unknown':
            result[row['month']] = None
            continue
        if row['status'] != 'conditional':
            raise ValueError('Reviewed conditional or unknown month required')
        try:
            government = Decimal(str(row['government_1y_percent']))
            corporate = Decimal(str(row['corporate_1y_percent']))
        except InvalidOperation as exc:
            raise ValueError('Finite numeric yields required') from exc
        if not government.is_finite() or not corporate.is_finite():
            raise ValueError('Finite numeric yields required')
        result[row['month']] = corporate-government
    return result


def decision(premiums, ordinal):
    names = [month_name(i) for i in range(ordinal-12, ordinal+1)]
    values = [premiums.get(name) for name in names]
    if any(value is None for value in values):
        return dict(state=None, reason='required_month_unknown',
                    missing_months=[name for name, value in zip(names, values) if value is None],
                    premium_percent=None if values[-1] is None else str(values[-1]),
                    prior12_median_percent=None)
    history = sorted(values[:-1])
    median = (history[5]+history[6])/2
    selected = int(values[-1] > median)
    return dict(state=selected, reason='above_prior12_median' if selected else 'not_above_prior12_median',
                missing_months=[], premium_percent=str(values[-1]), prior12_median_percent=str(median))


def quarterly_intervals(months, sessions):
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError('Unique chronological exchange sessions required')
    if any(date.fromisoformat(day).isoformat() != day for day in sessions):
        raise ValueError('ISO exchange sessions required')
    premiums = monthly_premiums(months)
    anchors = []
    for i in range(45):
        ordinal = 2013*12 + 3*i
        month = month_name(ordinal)
        index = bisect_left(sessions, month+'-01')
        if index == len(sessions) or not sessions[index].startswith(month+'-'):
            raise ValueError('Every fixed quarter needs an exchange opening anchor')
        anchors.append((index, ordinal))
    out, episode, episode_start = [], 0, None
    for (index, ordinal), (end, _) in zip(anchors, anchors[1:]):
        signal = decision(premiums, ordinal-1)
        if signal['state'] == 1:
            if not out or out[-1]['state'] != 1:
                episode += 1
                episode_start = sessions[index]
            episode_id = episode
        else:
            episode_id, episode_start = None, None
        out.append(dict(signal, source_month=month_name(ordinal-1), entry_date=sessions[index],
                        exit_date=sessions[end], entry_index=index, sessions=end-index,
                        episode_id=episode_id, episode_start=episode_start, carry_in=False))
    if len(out) != 44 or sum(row['sessions'] for row in out) != anchors[-1][0]-anchors[0][0]:
        raise ValueError('All44quarters must partition the full exchange window')
    return out


def calculate(snapshots):
    from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
    sessions = []
    for role, first, last in [('old_calendar', date(2013, 1, 1), date(2014, 12, 31)),
                              ('calendar', date(2015, 1, 1), date(2024, 6, 28))]:
        days = calendar_rows_from_snapshot(snapshots[role], snapshots[role+'_manifest'],
                                          start=first, end=last)
        sessions.extend(str(day) for day, opened in days if opened)
    rows = quarterly_intervals(json.loads(snapshots['source_inventory'])['months'], sessions)
    later = later_intervals(rows, sessions)
    if len(later) != 16:
        raise ValueError('Exact16later quarters required')
    counts = screen_counts(rows, later)
    return dict(intervals=rows, later_intervals=later, screen=counts,
                status='cadence_minima_passed_return_admission_pending' if counts['passed']
                else 'closed_insufficient_selected_observations',
                states_generated=True, ETF_outcomes_read=False, returns_computed=False,
                net_positive_EV_verified=False, new_return_studies=0,
                financial_execution_allowed=False, general_factor_batch_allowed=False,
                final_holdout_allowed=False, live_boundary_allowed=False)
