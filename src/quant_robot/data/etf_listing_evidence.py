"""Observe dated ETF listing identity fields without certifying tradability."""
from __future__ import annotations

from collections import Counter
from datetime import date
import hashlib
import io
import json
from pathlib import Path
import re
from typing import Any, Mapping
import unicodedata


_NUMBER = r'(?:\(?[一二三四五六七八九十0-9]+[)、.)]\s*)?'
_CODE = (r'(?:本?基金)?(?:二级市场)?交易代码|证券代码\(二级市场交易代码\)|'
         r'(?:本?基金)?(?:二级市场)?交易简称(?:及|和)交易代码:[^:\n]{1,40}[,，]\s*交易代码')
_SCOPE = r'例如|示例|假设|若|如果|其他基金|(?:修订|修改|变更)[前后]'
_RAW_CODE_LABEL = r'(?:证券代码\(二级市场交易代码\)|交易代码\)?|证券代码)\s*:'


def _normal(value: str) -> str:
    return unicodedata.normalize('NFKC', value)


def _compact(value: str) -> str:
    return ''.join(_normal(value).split())


def _publication(value: str) -> date:
    if not isinstance(value, str):
        raise ValueError('invalid publication date')
    result = date.fromisoformat(value)
    if result.isoformat() != value or result >= date(2026, 1, 1):
        raise ValueError('noncanonical publication date or sealed holdout')
    return result


def _dates(text: str, label: str) -> set[date]:
    result = set()
    normalized = _normal(text)
    for match in re.finditer(label + r'\s*:', normalized):
        prefix_lines = [line.strip() for line in normalized[:match.start()].splitlines() if line.strip()]
        if re.search(_SCOPE, ' '.join(prefix_lines[-2:])):
            raise ValueError('example or conditional date requires scope review')
        tail = normalized[match.end():]
        found = re.match(r'\s*([0-9]{4})\s*年\s*([0-9]{1,2})\s*月\s*([0-9]{1,2})\s*日', tail)
        if found is None:
            raise ValueError('unsupported explicit date field')
        result.add(date(*(int(x) for x in found.groups())))
    return result


def _codes(pages: Mapping[int, str]) -> dict[str, set[int]]:
    result: dict[str, set[int]] = {}
    for page, text in pages.items():
        previous = ''
        for line in _normal(text).splitlines():
            line = line.strip()
            if not line:
                continue
            matches = list(re.finditer(r'(?:^|[;,。])\s*' + _NUMBER + '(?:' + _CODE + r')\s*:\s*', line))
            for match in matches:
                if (re.search(_SCOPE, line[:match.end()])
                        or re.search(_SCOPE, previous)):
                    raise ValueError('example or conditional code requires scope review')
                result.setdefault(_code_value(line[match.end():]), set()).add(page)
            for label in re.finditer(_RAW_CODE_LABEL, line):
                if not any(match.start() <= label.start() and label.end() <= match.end() for match in matches):
                    raise ValueError('unscoped or compound explicit trading code')
            previous = line
    return result


def _code_value(text: str) -> str:
    value = re.match(r'([0-9]{6})(?![A-Za-z0-9_])', text)
    if value is None:
        raise ValueError('invalid explicit trading code')
    rest = text[value.end():].strip()
    if rest and not (
        (rest.startswith('。') and not re.match(r'。\s*[0-9]', rest))
        or re.match(r'^[;,]\s*' + _NUMBER + r'[^0-9:;,。\s]{1,24}\s*:', rest)
    ):
        raise ValueError('multiple values or unexplained trading code suffix')
    return value.group(1)


def review_listing_text(*, symbol: str, title: str, published_date: str,
                        pages: Mapping[int, str], expected_manager_name: str | None = None) -> dict[str, Any]:
    published = _publication(published_date)
    if not isinstance(symbol, str) or not re.fullmatch(r'[0-9]{6}\.SH', symbol):
        raise ValueError('explicit SSE symbol required')
    if (not isinstance(pages, Mapping) or 1 not in pages or not pages[1]
            or any(type(n) is not int or not 1 <= n <= 6 or not isinstance(t, str)
                   for n, t in pages.items())):
        raise ValueError('listing review requires physical cover and pages within first six')
    if not isinstance(title, str):
        raise ValueError('invalid listing title identity')
    heading = _compact(title)
    role = r'([A-Za-z0-9\u4e00-\u9fff-]{1,90}交易型开放式(?:指数)?(?:发起式)?证券投资基金)上市交易公告书'
    match = re.fullmatch(role, heading)
    if match is None or heading.startswith('关于'):
        raise ValueError('title does not identify an ETF listing book')
    fund = match.group(1)
    for text in pages.values():
        if re.search(r'(?m)^\s*(?:示例|例如|假设|其他基金|以[^\n]{1,80}为例|(?:修订|修改|变更)[前后])', _normal(text)):
            raise ValueError('example or amendment section requires scope review')
    first = re.sub(r'^\s*[0-9]{1,3}\s+', '', pages[1])
    cover_heading = _compact(first)
    if expected_manager_name is not None:
        if not isinstance(expected_manager_name, str) or not expected_manager_name.strip():
            raise ValueError('invalid explicit manager identity')
        cover_heading = cover_heading.removeprefix(_compact(expected_manager_name) + '上市交易公告书')
    if not cover_heading.startswith(heading):
        raise ValueError('cover and title fund identity disagree')
    for text in pages.values():
        for name in re.findall(r'基金名称:([^:]{1,180}?证券投资基金(?:联接基金)?)', _compact(text)):
            if name != fund:
                raise ValueError('body fund identity disagrees with cover')
    announced = _dates(first, r'公告(?:日期|时间)')
    if announced != {published}:
        raise ValueError('cover publication date missing or disagrees with index')
    listed = set().union(*(_dates(t, r'上市(?:交易)?(?:日期|时间)') for t in pages.values()))
    if len(listed) != 1:
        raise ValueError('missing or conflicting listing dates')
    listing = next(iter(listed))
    if listing < published or listing >= date(2026, 1, 1):
        raise ValueError('listing date outside publication or historical scope')
    codes = _codes(pages)
    if set(codes) != {symbol[:6]}:
        raise ValueError('missing, conflicting or mismatched explicit trading code')
    return {'symbol': symbol, 'status': 'identity_fields_observed',
            'legal_fund_name_observed': fund, 'trading_code': symbol[:6],
            'trading_code_pages': sorted(codes[symbol[:6]]),
            'publication_date_observed': published.isoformat(),
            'listing_date_observed': listing.isoformat(),
            'historical_membership_verified': False, 'mapping_eligible': False,
            'known_from': None, 'scope': 'selected listing pages; no suspension or continuous lifecycle certification'}


def review_listing_bundle(config: Mapping[str, Any]) -> dict[str, Any]:
    source = Path(config['source_manifest_path'])
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != config['source_manifest_sha256']:
        raise ValueError('source manifest fingerprint changed')
    packet = json.loads(raw)
    records = packet.get('records', [])
    if packet.get('complete') is not True or not isinstance(records, list) or not 1 <= len(records) <= 40:
        raise ValueError('listing packet incomplete or outside bounded scope')
    paths = set()
    for record in records:
        _publication(record['date'])
        path = Path(record['path']).resolve()
        if path in paths or path == source.resolve():
            raise ValueError('duplicate listing source path')
        paths.add(path)
    fingerprints = {str(source): config['source_manifest_sha256']}
    output = []; total_bytes = 0
    for record in records:
        path = Path(record['path']); pdf = path.read_bytes(); total_bytes += len(pdf)
        if (not pdf.startswith(b'%PDF-') or len(pdf) > 10_000_000 or total_bytes > 30_000_000
                or hashlib.sha256(pdf).hexdigest() != record['sha256']):
            raise ValueError('listing PDF fingerprint or byte scope invalid')
        fingerprints[str(path)] = record['sha256']
        pages = _listing_pages(pdf)
        try:
            item = review_listing_text(symbol=record['symbol'], title=record['title'],
                published_date=record['date'], pages=pages,
                expected_manager_name=config.get('fund_managers', {}).get(record['symbol']))
        except ValueError as exc:
            item = {'symbol': record['symbol'], 'status': 'rejected_listing_fields', 'reason': str(exc),
                    'mapping_eligible': False, 'historical_membership_verified': False, 'known_from': None}
        output.append({**item, 'source_path': str(path), 'source_sha256': record['sha256'],
                       'source_url': record['url'], 'source_publication_date': record['date']})
    for path, expected in fingerprints.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError('source changed during listing review')
    return {'stage': 'offline_listing_identity_observations', 'documents': output,
            'counts': dict(Counter(r['status'] for r in output)), 'input_fingerprints': fingerprints,
            'source_gate_passed': False, 'historical_mapping_written': False,
            'factor_generation_allowed': False, 'continuous_tradability_verified': False}


def _listing_pages(raw: bytes) -> dict[int, str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError('Install the pdf-sources optional dependency for PDF source review') from exc
    reader = PdfReader(io.BytesIO(raw))
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 250:
        raise ValueError('unsupported listing PDF page scope')
    return {n + 1: reader.pages[n].extract_text() or '' for n in range(min(6, len(reader.pages)))}
