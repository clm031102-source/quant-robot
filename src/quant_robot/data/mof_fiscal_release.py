"""Decode retained monthly fiscal releases, without source or trading authority.

Publication labels support a conservative assumed day; neither those labels nor
successful parsing prove the bytes were available historically. Annual budgets
and image-based budget annexes require their own source review.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from decimal import Context, Decimal, localcontext
import hashlib
from html.parser import HTMLParser
import re


class _Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.visible, self.publication, self.charsets = [], [], [], []
        self.suppressed = []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'template', 'noscript'}:
            self.suppressed.append(tag)
        if self.suppressed:
            return
        if tag == 'title':
            self.in_title = True
            self.title.append([])
        elif tag == 'meta':
            values = dict(attrs)
            if 'charset' in values:
                self.charsets.append(values['charset'] or '')
            if (values.get('http-equiv') or '').strip().lower() == 'content-type':
                content = values.get('content') or ''
                if 'charset' in content.lower():
                    declared = re.search(r'''charset\s*=\s*["']?([A-Za-z0-9_-]+)''', content, re.I)
                    self.charsets.append(declared[1] if declared else '')
            if (values.get('name') or '').lower() == 'pubdate' and values.get('content'):
                self.publication.append(values['content'])
        elif tag in {'p', 'div', 'br', 'li', 'h1', 'h2', 'h3'}:
            self.visible.append('\n')

    def handle_endtag(self, tag):
        if self.suppressed:
            if self.suppressed[-1] == tag:
                self.suppressed.pop()
            return
        if tag == 'title':
            self.in_title = False
        elif tag in {'p', 'div', 'li', 'h1', 'h2', 'h3'}:
            self.visible.append('\n')

    def handle_data(self, value):
        if not self.suppressed:
            (self.title[-1] if self.in_title else self.visible).append(value)


_DAY = r'(?:[0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日|[0-9]{4}-[0-9]{2}-[0-9]{2})'
_NUMBER = r'(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,6})?'


def _decode(raw):
    # Read ASCII-compatible HTML declarations without guessing a legacy codec.
    probe = _Document()
    probe.feed(raw.decode('latin-1'))
    probe.close()
    encodings = {name.strip().lower().replace('_', '-') for name in probe.charsets}
    encodings = {'utf-8' if name == 'utf8' else name for name in encodings}
    if not encodings:
        encodings = {'utf-8'}
    if len(encodings) != 1 or not encodings <= {'utf-8', 'gb2312'}:
        raise ValueError('unreviewed or conflicting source encoding declarations')
    encoding = encodings.pop()
    if encoding != 'utf-8' and raw.startswith(b'\xef\xbb\xbf'):
        raise ValueError('UTF8 byte marker conflicts with declared legacy encoding')
    decoded = raw.decode('utf-8-sig' if encoding == 'utf-8' else encoding)
    return decoded, encoding, probe.charsets


def _day(token):
    if re.fullmatch(_DAY, token) is None:
        raise ValueError('unrecognized publication date label')
    return date(*map(int, re.split(r'[-年月日]', token.rstrip('日'))))


def _publication_day(doc, text):
    visible = re.findall(r'发布日期[:：]?\s*(' + _DAY + ')', text)
    visible += re.findall('(' + _DAY + r')\s*来源[:：]', text)
    if not visible:
        raise ValueError('visible publication date evidence is required')
    days = {_day(token) for token in visible}
    for token in doc.publication:
        if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?: [0-9]{2}:[0-9]{2}:[0-9]{2})?', token) is None:
            raise ValueError('unrecognized publication metadata precision')
        days.add(datetime.fromisoformat(token).date())
    if len(days) != 1:
        raise ValueError('visible and metadata publication dates disagree')
    return days.pop()


def _amount(paragraph, label):
    matches = re.findall(re.escape(label) + '(' + _NUMBER + ')亿元', paragraph)
    if paragraph.count(label) != 1 or len(matches) != 1:
        raise ValueError('one explicit CNY100million amount required for ' + label)
    return Decimal(matches[0])


def parse_mof_monthly_expenditure(raw: bytes, *, expected_year: int, expected_month: int) -> dict:
    """Return reported cumulative expenditure and dates, never a fiscal factor.

    The caller binds URL/origin and review scope. Only the declared monthly
    formats below are understood; unknown variants require source review.
    """
    if type(raw) is not bytes or len(raw) > 3_000_000:
        raise ValueError('retained source must be bytes within the 3MB limit')
    if type(expected_year) is not int or type(expected_month) is not int:
        raise ValueError('year and month must be explicit integers')
    try:
        first = date(expected_year, 1, 1)
        last = date(expected_year, expected_month, calendar.monthrange(expected_year, expected_month)[1])
        doc = _Document()
        decoded, encoding, declarations = _decode(raw)
        doc.feed(decoded)
        doc.close()
        titles = [re.sub(r'\s+', '', ''.join(parts)) for parts in doc.title]
        if not titles or any(t != '无标题文档' for t in titles[1:]):
            raise ValueError('ambiguous or unreviewed secondary document titles')
        title = titles[0]
        titles = [rf'{expected_month}月', rf'1[-—－–]{expected_month}月']
        if expected_month in {3, 6, 9, 12}:
            titles.append({3: '一季度', 6: '上半年', 9: '前三季度', 12: ''}[expected_month])
        period = '(?:' + '|'.join(titles) + ')'
        if re.fullmatch(rf'{expected_year}年{period}财政收支情况', title) is None:
            raise ValueError('monthly title differs from the declared year and period')
        lines = [re.sub(r'\s+', '', line) for line in ''.join(doc.visible).splitlines()]
        paragraphs = [line for line in lines if '全国一般公共预算支出' in line]
        if len(paragraphs) != 1:
            raise ValueError('one unambiguous nationwide expenditure paragraph required')
        paragraph = paragraphs[0]
        prefix = rf'(?:{expected_year}年)?1[-—－–至]{expected_month}月(?:累计)?'
        if expected_month == 6:
            prefix = '(?:' + prefix + '|上半年(?:累计)?)'
        elif expected_month == 12:
            prefix = '(?:' + prefix + rf'|{expected_year}年(?:累计)?)'
        if re.match(prefix + r'[,，]全国一般公共预算支出', paragraph) is None:
            raise ValueError('reported cumulative period differs from expected January-to-month period')
        nationwide = _amount(paragraph, '全国一般公共预算支出')
        central = _amount(paragraph, '中央一般公共预算本级支出')
        local = _amount(paragraph, '地方一般公共预算支出')
        with localcontext(Context(prec=40)):
            if nationwide <= 0 or central < 0 or local < 0 or central + local != nationwide:
                raise ValueError('national expenditure must reconcile to central own plus local expenditure')
        published = _publication_day(doc, '\n'.join(lines))
        if published <= last:
            raise ValueError('publication day must follow the completed reporting period')
        available = published + timedelta(days=1)
    except (UnicodeError, OverflowError) as exc:
        raise ValueError('malformed source encoding or date') from exc
    return {'title': title, 'period_start': first.isoformat(), 'period_end': last.isoformat(),
        'scope': 'national_general_public_budget', 'source_value_semantics': 'cumulative_from_january',
        'amount_cny_100m': str(nationwide), 'central_own_amount_cny_100m': str(central),
        'local_amount_cny_100m': str(local), 'published_date_label': published.isoformat(),
        'publication_metadata': list(doc.publication), 'assumed_available_civil_day': available.isoformat(),
        'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_encoding': encoding,
        'source_encoding_declarations': declarations, 'matched_paragraph': paragraph,
        'historical_availability_verified': False, 'source_audit_verified': False,
        'research_admission_granted': False, 'factor_or_return_computed': False}
