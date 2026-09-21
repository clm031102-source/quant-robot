"""Parse public government YTM history, without signals or publication claims.

This historical page shares its table region with the existing current-page
collector. Curve dates can include weekends and are never filtered by an ETF
calendar. A source date does not certify when that version became public.
"""
from calendar import monthrange
from datetime import date
from decimal import Decimal
import re

from .chinabond_observation import _CurveTable


HEADERS = ['YieldCurveName', 'Date', '3M', '6M', '1Y', '3Y', '5Y', '7Y', '10Y', '30Y']
CURVE = 'ChinaBond Government Bond Yield Curve'


def _iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('source date is not ISO')
    return date.fromisoformat(value)


def _yield(value):
    if value in {'', '--', '-'}:
        return None
    if not re.fullmatch(r'-?[0-9]+(?:\.[0-9]+)?', value) or not Decimal(value).is_finite():
        raise ValueError('invalid required yield')
    return value


def parse_history(raw: bytes, *, start: str, end: str, max_rows: int = 366) -> list[dict]:
    """Require the exact all-tenor English government table and request bounds."""
    first, last = _iso_day(start), _iso_day(end)
    if first > last or (last - first).days > 365 or not 1 <= max_rows <= 366:
        raise ValueError('invalid one-year request range or row limit')
    if not isinstance(raw, bytes) or len(raw) > 1_000_000:
        raise ValueError('invalid response size')
    table = _CurveTable()
    table.feed(raw.decode('utf-8'))
    table.close()
    if (table.regions != 1 or table.tables != 1 or table.depth
            or table.row is not None or table.cell is not None
            or not 2 <= len(table.rows) <= max_rows + 1):
        raise ValueError('source table shape or row limit changed')
    if [''.join(x.split()) for x in table.rows[0]] != HEADERS:
        raise ValueError('source tenor headers changed')
    seen, result = set(), []
    for row in table.rows[1:]:
        if len(row) != 10 or row[0] != CURVE:
            raise ValueError('source curve identity or width changed')
        day = _iso_day(row[1])
        if not first <= day <= last:
            raise ValueError('source date outside requested range')
        if day in seen:
            raise ValueError('duplicate source date')
        seen.add(day)
        result.append({'date': day.isoformat(), 'curve': CURVE,
                       'yield_1y_percent': _yield(row[4]),
                       'yield_10y_percent': _yield(row[8]),
                       'tenor_metadata': dict(zip(HEADERS[2:], row[2:]))})
    return sorted(result, key=lambda row: row['date'])


def monthly_inputs(rows: list[dict], *, first: str, last: str) -> list[dict]:
    """Last same-date observation per calendar month, including unknown months.

Conditional means the source values satisfy the fixed mechanical selection. It
does not imply certified historical release timing, a signal or positive EV.
"""
    start, finish = _iso_day(first + '-01'), _iso_day(last + '-01')
    if start > finish:
        raise ValueError('reversed month range')
    final_day = date(finish.year, finish.month, monthrange(finish.year, finish.month)[1])
    seen, groups = set(), {}
    for row in rows:
        day = _iso_day(row['date'])
        if not start <= day <= final_day or row['curve'] != CURVE:
            raise ValueError('source outside month range or wrong curve')
        if day in seen:
            raise ValueError('duplicate source date across responses')
        seen.add(day)
        groups.setdefault(day.strftime('%Y-%m'), []).append(row)
    result, current = [], start
    while current <= finish:
        month = current.strftime('%Y-%m')
        candidates = groups.get(month, [])
        item = {'month': month, 'status': 'unknown', 'reason': 'no_observation',
                'observation_date': None, 'age_calendar_days': None,
                'yield_1y_percent': None, 'yield_10y_percent': None}
        if candidates:
            latest = max(candidates, key=lambda row: row['date'])
            end = date(current.year, current.month, monthrange(current.year, current.month)[1])
            age = (end - _iso_day(latest['date'])).days
            item.update(observation_date=latest['date'], age_calendar_days=age,
                        yield_1y_percent=latest['yield_1y_percent'],
                        yield_10y_percent=latest['yield_10y_percent'])
            if age > 7:
                item['reason'] = 'observation_more_than_seven_days_old'
            elif latest['yield_1y_percent'] is None or latest['yield_10y_percent'] is None:
                item['reason'] = 'required_tenor_missing'
            else:
                item.update(status='conditional', reason=None)
        result.append(item)
        current = date(current.year + 1, 1, 1) if current.month == 12 else date(current.year, current.month + 1, 1)
    return result
