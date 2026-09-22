"""Frozen currency-pressure/gold quarterly cadence; no ETF outcome input."""
from bisect import bisect_left
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import json

from quant_robot.research.enterprise_liquidity_cadence import later_intervals, screen_counts


def quarter_ends():
    result = []
    for ordinal in range(2013*12+8, 2023*12+9, 3):
        year, month0 = divmod(ordinal, 12)
        result.append(date(year, month0+1, monthrange(year, month0+1)[1]).isoformat())
    return result


def source_endpoints(rows):
    if [row['quarter_end'] for row in rows] != quarter_ends():
        raise ValueError('Exact41chronological quarter endpoints,including unknowns,required')
    result = []
    for row in rows:
        end = date.fromisoformat(row['quarter_end'])
        release = date.fromisoformat(row['release_date'])
        if release >= end:
            raise ValueError('Publication day must be strictly before quarter end')
        # End of the named New York day, using UTC-5 as the conservative bound
        # for either standard or daylight time in this fixed2013..2023window.
        bound = datetime.combine(release+timedelta(days=1),datetime.min.time(),timezone.utc)+timedelta(hours=5)
        value = None
        if row['status'] == 'conditional':
            observation = date.fromisoformat(row['observation_date'])
            if not observation < release or not 0 <= (end-observation).days <= 14:
                raise ValueError('Known endpoint violates publication or14day age')
            if row['age_calendar_days'] != (end-observation).days:
                raise ValueError('Source age differs')
            try:
                value = Decimal(str(row['cny_per_usd']))
            except InvalidOperation as exc:
                raise ValueError('Positive finite CNYperUSD quote required') from exc
            if not value.is_finite() or value <= 0:
                raise ValueError('Positive finite CNYperUSD quote required')
        elif row['status'] != 'unknown':
            raise ValueError('Conditional or unknown endpoint required')
        result.append(dict(row, value=value, publication_bound=bound))
    return result


def quarterly_intervals(endpoints, sessions):
    if not sessions or sessions != sorted(set(sessions)):
        raise ValueError('Unique chronological exchange sessions required')
    if any(date.fromisoformat(day).isoformat() != day for day in sessions):
        raise ValueError('ISO exchange sessions required')
    sources = source_endpoints(endpoints)
    anchors = []
    for i in range(41):
        year, month0 = divmod(2014*12+3*i,12)
        month = f'{year:04d}-{month0+1:02d}'
        index = bisect_left(sessions,month+'-01')
        if index == len(sessions) or not sessions[index].startswith(month+'-'):
            raise ValueError('Every fixed quarter needs an exchange opening anchor')
        anchors.append(index)
    out, episode, episode_start = [], 0, None
    for i,(index,end) in enumerate(zip(anchors,anchors[1:])):
        prior,current = sources[i:i+2]
        opened = datetime.fromisoformat(sessions[index]+'T09:30:00+08:00')
        bound = max(prior['publication_bound'],current['publication_bound'])
        if not bound < opened:
            raise ValueError('Publication bound must precede China opening')
        missing = [row['quarter_end'] for row in (prior,current) if row['value'] is None]
        state = None if missing else int(current['value'] > prior['value'])
        if state == 1:
            if not out or out[-1]['state'] != 1:
                episode += 1
                episode_start = sessions[index]
            episode_id = episode
        else:
            episode_id, episode_start = None,None
        out.append(dict(state=state,reason='endpoint_unknown' if missing else
            ('CNY_depreciated' if state else 'CNY_not_depreciated'),
            source_quarter_end=current['quarter_end'],prior_quarter_end=prior['quarter_end'],
            source_quote=None if current['value'] is None else str(current['value']),
            prior_quote=None if prior['value'] is None else str(prior['value']),
            missing_endpoints=missing,publication_upper_bound_UTC=bound.isoformat(),
            entry_date=sessions[index],exit_date=sessions[end],entry_index=index,sessions=end-index,
            episode_id=episode_id,episode_start=episode_start,carry_in=False))
    if len(out)!=40 or sum(row['sessions'] for row in out)!=anchors[-1]-anchors[0]:
        raise ValueError('All40quarters must partition the exchange window')
    return out


def calculate(snapshots):
    from quant_robot.data.cn_calendar_snapshot import calendar_rows_from_snapshot
    sessions = []
    for role,first,last in [('old_calendar',date(2014,1,1),date(2014,12,31)),
                             ('calendar',date(2015,1,1),date(2024,6,28))]:
        days = calendar_rows_from_snapshot(snapshots[role],snapshots[role+'_manifest'],start=first,end=last)
        sessions.extend(str(day) for day,opened in days if opened)
    rows = quarterly_intervals(json.loads(snapshots['source_inventory'])['endpoints'],sessions)
    later = later_intervals(rows,sessions)
    if len(later)!=16:
        raise ValueError('Exact16later quarters required')
    counts = screen_counts(rows,later)
    return dict(intervals=rows,later_intervals=later,screen=counts,
        status='cadence_minima_passed_return_admission_pending' if counts['passed']
        else 'closed_insufficient_selected_observations',
        states_generated=True,ETF_outcomes_read=False,returns_computed=False,
        net_positive_EV_verified=False,new_return_studies=0,
        financial_execution_allowed=False,general_factor_batch_allowed=False,
        final_holdout_allowed=False,live_boundary_allowed=False)
