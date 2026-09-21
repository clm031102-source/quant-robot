"""One-year AAA note source projection and same-date pairing; no credit signal."""
from calendar import monthrange
from datetime import date

from .chinabond_history import CURVE as GOVERNMENT, HEADERS, _iso_day, _yield
from .chinabond_observation import _CurveTable

CORPORATE = 'ChinaBond CP&Note Yield Curve (AAA)'


def parse_credit_history(raw: bytes, *, start: str, end: str) -> list[dict]:
    first, last = _iso_day(start), _iso_day(end)
    if first > last or (last - first).days > 365:
        raise ValueError('one-year request bounds required')
    if not isinstance(raw, bytes) or len(raw) > 1_000_000:
        raise ValueError('response size or type invalid')
    table = _CurveTable()
    table.feed(raw.decode('utf-8'))
    table.close()
    if (table.regions != 1 or table.tables != 1 or table.depth
            or table.row is not None or table.cell is not None
            or not 2 <= len(table.rows) <= 367):
        raise ValueError('source table shape invalid')
    if [''.join(x.split()) for x in table.rows[0]] != HEADERS:
        raise ValueError('source headers changed')
    seen, rows = set(), []
    for row in table.rows[1:]:
        if len(row) != 10 or row[0] != CORPORATE:
            raise ValueError('corporate curve identity or width changed')
        if any(row[i] for i in [2, 3, 5, 6, 7, 8, 9]):
            raise ValueError('exact one-year projection required')
        day = _iso_day(row[1])
        if not first <= day <= last or day in seen:
            raise ValueError('date outside bounds or duplicate')
        seen.add(day)
        rows.append(dict(date=str(day), curve=CORPORATE, yield_1y_percent=_yield(row[4])))
    return sorted(rows, key=lambda row: row['date'])


def pair_months(government: list[dict], corporate: list[dict], *, first: str, last: str) -> list[dict]:
    """Fix the government month-end date before pairing; never calculate a spread."""
    start, finish = _iso_day(first + '-01'), _iso_day(last + '-01')
    if start > finish:
        raise ValueError('reversed month range')
    final = date(finish.year, finish.month, monthrange(finish.year, finish.month)[1])
    indexed = []
    for source, identity in [(government, GOVERNMENT), (corporate, CORPORATE)]:
        by = {}
        for row in source:
            day = _iso_day(row['date'])
            if row['curve'] != identity or not start <= day <= final or row['date'] in by:
                raise ValueError('wrong identity, out-of-range or duplicate date')
            value = row['yield_1y_percent']
            if value is not None:
                if _yield(value) is None:
                    raise ValueError('normalized missing yield must be None')
            by[row['date']] = row
        indexed.append(by)
    gov, corp = indexed
    result, current = [], start
    while current <= finish:
        month = current.strftime('%Y-%m')
        dates = [day for day in gov if day.startswith(month)]
        row = dict(month=month, status='unknown', reason='government_month_missing',
                   observation_date=None, age_calendar_days=None,
                   government_1y_percent=None, corporate_1y_percent=None)
        if dates:
            key = max(dates)
            last_day = date(current.year, current.month, monthrange(current.year, current.month)[1])
            age = (last_day - _iso_day(key)).days
            one = gov[key]['yield_1y_percent']
            other = corp[key]['yield_1y_percent'] if key in corp else None
            row.update(observation_date=key, age_calendar_days=age,
                       government_1y_percent=one, corporate_1y_percent=other)
            if age > 7:
                row['reason'] = 'government_observation_more_than_seven_days_old'
            elif one is None:
                row['reason'] = 'government_one_year_missing'
            elif key not in corp:
                row['reason'] = 'same_date_corporate_observation_missing'
            elif other is None:
                row['reason'] = 'corporate_one_year_missing'
            else:
                row.update(status='conditional', reason=None)
        result.append(row)
        current = date(current.year + 1, 1, 1) if current.month == 12 else date(current.year, current.month + 1, 1)
    return result
