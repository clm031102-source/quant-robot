"""Strict source parsing for PBC enterprise surveys; no signals or returns."""
from datetime import date, datetime
from decimal import Decimal
import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


def _compact(value):
    return re.sub(r'\s+', '', value)


def _quarter(title):
    match = re.fullmatch(r'(\d{4})年(?:第)?([一二三四1234])季度(?:全国)?企业家问卷调查(?:报告|综述)',
                         _compact(title))
    if not match:
        return None
    year, quarter = match.groups()
    quarter = str('一二三四'.index(quarter) + 1) if quarter in '一二三四' else quarter
    return year + 'Q' + quarter


def _source_url(base, href):
    url = urljoin(base, href)
    parsed = urlsplit(url)
    if (parsed.scheme not in ('http', 'https') or parsed.username or parsed.password
            or not parsed.hostname or not
            (parsed.hostname == 'gov.cn' or parsed.hostname.endswith('.gov.cn'))):
        raise ValueError('source link is not an ordinary government URL')
    return url


def catalogue_rows(raw, url):
    soup = BeautifulSoup(raw, 'html.parser')
    result = []
    for anchor in soup.find_all('a', href=True):
        title = anchor.get_text(' ', strip=True)
        quarter = _quarter(title)
        if quarter is None:
            continue
        row = anchor.find_parent(['td', 'li'])
        if row is None:
            raise ValueError('quarter link has no dated row')
        days = set(re.findall(r'\d{4}-\d{2}-\d{2}', row.get_text(' ', strip=True)))
        if len(days) != 1:
            raise ValueError('quarter row has missing or ambiguous dates')
        day = days.pop()
        date.fromisoformat(day)
        result.append({'quarter': quarter, 'title': title, 'catalogue_date': day,
                       'url': _source_url(url, anchor['href'])})
    return result


def landing_details(raw, url, expected_quarter):
    soup = BeautifulSoup(raw, 'html.parser')
    titles = [tag.get('content', '') for tag in soup.find_all('meta')
              if tag.get('name', '').lower() == 'articletitle']
    if not titles or {_quarter(title) for title in titles} != {expected_quarter}:
        raise ValueError('article title does not identify the expected survey quarter')
    stamps = set(re.findall(r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',
                            soup.get_text(' ', strip=True)))
    if len(stamps) != 1:
        raise ValueError('article has no unique explicit body publication timestamp')
    stamp = next(iter(stamps))
    published = datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S')
    metadata_days = {tag.get('content', '') for tag in soup.find_all('meta')
                     if tag.get('name', '').lower() == 'pubdate'}
    if metadata_days and metadata_days != {published.date().isoformat()}:
        raise ValueError('article body and PubDate conflict')
    links = {_source_url(url, a['href']) for a in soup.find_all('a', href=True)
             if urlsplit(a['href']).path.lower().endswith('.pdf')}
    if len(links) != 1:
        raise ValueError('article has no unique PDF attachment')
    return {'quarter': expected_quarter, 'published_at': published.isoformat(sep=' '),
            'pdf_url': links.pop()}


def report_fields(pages, expected_quarter):
    if not pages or not all(isinstance(page, str) for page in pages):
        raise ValueError('decoded PDF pages are required')
    normalized = [_compact(page) for page in pages]
    title_pattern = r'\d{4}年(?:第)?[一二三四1234]季度(?:全国)?企业家问卷调查(?:报告|综述)'
    quarters = {_quarter(title) for title in re.findall(title_pattern, normalized[0])}
    if quarters != {expected_quarter}:
        raise ValueError('PDF title does not identify the expected quarter')
    body = ''.join(normalized[:3])
    numbers = re.findall(r'(?<!预期)资金周转指数为([+-]?\d+(?:\.\d+)?)%', body)
    location = 'report_body'
    if not numbers:
        numbers = [_original_table_level(pages, expected_quarter)]
        location = 'original_quarter_appendix'
    if len(numbers) != 1:
        raise ValueError('PDF body has no unique explicit funds-turnover level')
    value = Decimal(numbers[0])
    if not value.is_finite() or not 0 <= value <= 100:
        raise ValueError('diffusion index outside0..100')
    dates = set(re.findall(r'(\d{4})年(\d{1,2})月(\d{1,2})日', normalized[0]))
    if len(dates) > 1:
        raise ValueError('multiple declared PDF dates need review')
    declared = date(*map(int, next(iter(dates)))).isoformat() if dates else None
    full = re.sub(r'WWW\.PBC\.GOV\.CN\d+', '', ''.join(normalized))
    method = _method(full)
    return {'quarter': expected_quarter, 'index_percent': str(value),
            'document_date': declared, 'method': method, 'value_location': location}


def _original_table_level(pages, quarter):
    """Read only the current quarter in the reviewed11-column legacy layout."""
    header = ('时间企业家信心指数企业景气指数设备能力利用指数原材料供应情况'
              '产品销售情况产成品库存水平国内订单水平出口产品订单资金周转状况'
              '企业盈利指数设备投资指数')
    year, number = quarter.split('Q')
    values = []
    for page in pages:
        before_rows = re.split(r'\d{4}\.Q[1-4]', page, maxsplit=1)[0]
        if header not in _compact(before_rows):
            continue
        for tail in re.findall(r'^\s*' + year + r'\.Q' + number + r'\s+([^\r\n]+)',
                               page, flags=re.MULTILINE):
            cells = tail.split()
            if len(cells) != 11 or not all(re.fullmatch(r'\d+(?:\.\d+)?', c) for c in cells):
                raise ValueError('original-quarter table row has an unexpected layout')
            values.append(cells[8])
    if len(values) != 1:
        raise ValueError('PDF has neither an explicit level nor a unique original-quarter table cell')
    return values[0]


def _method(full):
    legacy = ('表明企业家对本企业资金周转情况判断的扩散指数。一般指全部接受调查的企业家中，'
              '认为本企业资金周转状况“良好”的占比减去认为“困难”的占比。')
    transform = '前述差额加上100%除以2'
    if legacy in full:
        if transform not in full:
            raise ValueError('legacy difference definition has no reviewed scale transformation')
        return legacy + '；' + transform
    marker = '反映企业家对本企业本季资金周转情况判断的扩散指数'
    start = full.find(marker)
    end = full.find('后求和得出。', start)
    if start < 0 or end < 0:
        raise ValueError('funds-turnover method paragraph not identified')
    method = full[start:end + len('后求和得出。')]
    if len(method) > 200 or not all(text in method for text in
                                    ('全部调查的企业', '良好', '一般', '权重1和0.5后求和得出。')):
        raise ValueError('funds-turnover definition or response weights need review')
    return method
