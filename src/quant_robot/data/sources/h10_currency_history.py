"""Parse dated Federal Reserve H.10 China rows; never infer currency returns."""
from calendar import monthrange
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
import re

MONTHS = {name: i+1 for i, name in enumerate(
    ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'))}
FULL_MONTHS = ('January', 'February', 'March', 'April', 'May', 'June',
               'July', 'August', 'September', 'October', 'November', 'December')


class _ReleaseTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active = False
        self.tables = 0
        self.rows, self.text = [], []
        self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table' and 'statistics' in dict(attrs).get('class', '').split():
            if self.active:
                raise ValueError('Nested statistics table')
            self.tables += 1
            self.active = True
        elif self.active and tag == 'table':
            raise ValueError('Nested statistics table')
        elif self.active and tag == 'tr':
            if self.row is not None:
                raise ValueError('Nested source row')
            self.row = []
        elif self.active and tag in ('td', 'th'):
            # Published H.10 memo rows omit opening tr tags; browsers create
            # those rows implicitly. Preserve cells without changing quotes.
            if self.row is None:
                self.row = []
            if self.cell is not None:
                raise ValueError('Invalid source cell')
            self.cell = []

    def handle_endtag(self, tag):
        if not self.active:
            return
        if tag in ('td', 'th'):
            if self.cell is None or self.row is None:
                raise ValueError('Unmatched source cell')
            self.row.append(' '.join(''.join(self.cell).split()))
            self.cell = None
        elif tag == 'tr':
            if self.row is None or self.cell is not None:
                raise ValueError('Unfinished source row')
            self.rows.append(self.row)
            self.row = None
        elif tag == 'table':
            if self.row is not None or self.cell is not None:
                raise ValueError('Unfinished statistics table')
            self.active = False

    def handle_data(self, data):
        self.text.append(data)
        if self.cell is not None:
            self.cell.append(data)


def parse_release(raw, *, release_date):
    release = date.fromisoformat(release_date)
    if release.isoformat() != release_date or not isinstance(raw, bytes) or len(raw) > 3_000_000:
        raise ValueError('Bounded source bytes and ISO release date required')
    parser = _ReleaseTable()
    parser.feed(raw.decode('utf-8'))
    parser.close()
    if parser.tables != 1 or parser.active or parser.row is not None or parser.cell is not None:
        raise ValueError('One complete statistics table required')
    text = ' '.join(' '.join(parser.text).split())
    dates = re.findall(r'Release Date:\s*([A-Za-z]+) (\d{1,2}), (\d{4})', text)
    expected = (FULL_MONTHS[release.month-1], str(release.day), str(release.year))
    if dates != [expected] or 'Rates in currency units per U.S. dollar' not in text:
        raise ValueError('Release identity or quote convention differs')
    header = parser.rows[0]
    if len(header) != 7 or header[:2] != ['COUNTRY', 'CURRENCY']:
        raise ValueError('Exact country/currency/five-date header required')
    observations = []
    for label in header[2:]:
        match = re.fullmatch(r'([A-Z][a-z]{2})\.? (\d{1,2})', label)
        if not match or match[1] not in MONTHS:
            raise ValueError('Invalid observation date header')
        day = date(release.year, MONTHS[match[1]], int(match[2]))
        if day >= release:
            day = date(release.year-1, day.month, day.day)
        if not timedelta(0) < release-day <= timedelta(days=14):
            raise ValueError('Observation must precede release within14days')
        observations.append(day)
    if ([d.weekday() for d in observations] != list(range(5))
            or any(b-a != timedelta(days=1) for a,b in zip(observations, observations[1:]))):
        raise ValueError('One consecutive Monday-Friday observation week required')
    china = [row for row in parser.rows[1:] if row and row[0] in ('CHINA, P.R.', '*CHINA, P.R.')]
    if len(china) != 1 or len(china[0]) != 7 or china[0][:2] != ['CHINA, P.R.', 'YUAN']:
        raise ValueError('One unstarred CHINA,YUAN row required')
    out = []
    for day, raw_value in zip(observations, china[0][2:]):
        value = None
        if raw_value != 'ND':
            try:
                number = Decimal(raw_value)
            except InvalidOperation as exc:
                raise ValueError('Positive finite quote orND required') from exc
            if not number.is_finite() or number <= 0:
                raise ValueError('Positive finite quote orND required')
            value = str(number)
        out.append(dict(date=day.isoformat(), cny_per_usd=value))
    return out


def endpoint_snapshot(raw, *, release_date, quarter_end):
    release, end = date.fromisoformat(release_date), date.fromisoformat(quarter_end)
    if release >= end or end.month not in (3, 6, 9, 12) or end.day != monthrange(end.year,end.month)[1]:
        raise ValueError('Release must be strictly before the fixed quarter end')
    rows = parse_release(raw, release_date=release_date)
    valid = [row for row in rows if row['cny_per_usd'] is not None]
    latest = valid[-1] if valid else None
    age = (end-date.fromisoformat(latest['date'])).days if latest else None
    known = latest is not None and age <= 14
    return dict(quarter_end=quarter_end, release_date=release_date,
        status='conditional' if known else 'unknown',
        reason=None if known else ('no_valid_quote' if latest is None else 'quote_older_than14days'),
        observation_date=latest['date'] if latest else None, age_calendar_days=age,
        cny_per_usd=latest['cny_per_usd'] if known else None, source_rows=rows)


def quarter_requests(catalog):
    dates = []
    for year in catalog:
        for month in year['Months']:
            for raw in month['Dates']:
                if not re.fullmatch(r'\d{8}',raw):
                    raise ValueError('Invalid catalogue date')
                day = date(int(raw[:4]),int(raw[4:6]),int(raw[6:]))
                if day.year != int(year['yearValue']):
                    raise ValueError('Catalogue year differs')
                dates.append(day)
    if len(dates) != len(set(dates)):
        raise ValueError('Duplicate catalogue release')
    result = []
    for ordinal in range(2013*12+8, 2023*12+9, 3):
        year, month0 = divmod(ordinal, 12)
        end = date(year, month0+1, monthrange(year,month0+1)[1])
        eligible = [day for day in dates if day < end]
        if not eligible:
            raise ValueError('No pre-quarter-end catalogue release')
        release = max(eligible)
        result.append(dict(id=release.strftime('%Y%m%d'),quarter_end=end.isoformat(),
            release_date=release.isoformat(),url=f'https://www.federalreserve.gov/releases/h10/{release:%Y%m%d}/'))
    if len(result) != 41 or len({r['id'] for r in result}) != 41:
        raise ValueError('Exact41distinct quarterly source endpoints required')
    return result
