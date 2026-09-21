"""Identity-preserving report_rc observations; no historical availability certification."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import hashlib
import json
import re
from typing import Any
import unicodedata


CHINA = timezone(timedelta(hours=8))
UTC = timezone.utc
SCHEMA = 'analyst_forecast_observation_v1'


@dataclass(frozen=True)
class AnalystForecastEvent:
    record_id: str
    version_id: str
    source_sha256: str
    source_rows: tuple[int, ...]
    asset_id: str
    institution: str
    author: str
    forecast_period: str
    report_date: date
    report_title: str
    report_type: str
    classification: str
    provider_updated_at: datetime | None
    observed_at: datetime
    available_at: datetime
    net_profit: Decimal | None
    eps: Decimal | None
    total_profit: Decimal | None
    target_low: Decimal | None
    target_high: Decimal | None
    historical_availability_verified: bool = False

    @property
    def match_key(self) -> tuple[str, str, str, str]:
        return self.asset_id, self.institution, self.author, self.forecast_period

    @property
    def target_price(self) -> Decimal | None:
        low, high = self.target_low, self.target_high
        if low is None or high is None or low <= 0 or high < low:
            return None
        with localcontext(Context(prec=64, rounding=ROUND_HALF_EVEN)):
            return low / 2 + high / 2


@dataclass(frozen=True)
class AnalystForecastBatch:
    source_sha256: str
    observed_at: datetime
    raw_rows: int
    events: tuple[AnalystForecastEvent, ...]
    provider_has_more: bool | None = None
    provider_count: int | None = None
    schema: str = SCHEMA
    source_completeness_verified: bool = False
    historical_availability_verified: bool = False


def normalize_analyst_response(raw: bytes, *, observed_at: datetime) -> AnalystForecastBatch:
    """Read original successful API bytes; a caller's observation clock is not independent proof."""
    if not isinstance(observed_at, datetime) or observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError('observed_at_timezone_required')
    observed = observed_at.astimezone(UTC)
    if not isinstance(raw, bytes) or len(raw) > 8_000_000:
        raise ValueError('invalid_response_bytes')
    try:
        packet = json.loads(raw.decode('utf-8-sig'), parse_float=Decimal,
                            parse_constant=_invalid_constant, object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid_response_json') from exc
    if not isinstance(packet, dict) or type(packet.get('code')) is not int or packet['code'] != 0:
        raise ValueError('successful_original_response_required')
    data = packet.get('data')
    if not isinstance(data, dict):
        raise ValueError('invalid_response_data')
    fields, items = data.get('fields'), data.get('items')
    if (not isinstance(fields, list) or not fields or any(not isinstance(f, str) for f in fields)
            or len(fields) != len(set(fields)) or not isinstance(items, list)):
        raise ValueError('invalid_response_fields_or_items')
    required = {'ts_code', 'report_date', 'quarter', 'org_name', 'author_name', 'report_title'}
    if not required.issubset(fields):
        raise ValueError('missing_identity_fields')
    has_more, count = data.get('has_more'), data.get('count')
    if ((has_more is not None and type(has_more) is not bool)
            or (count is not None and (type(count) is not int or count < 0))):
        raise ValueError('invalid_response_pagination_metadata')
    digest = hashlib.sha256(raw).hexdigest()
    versions: dict[str, AnalystForecastEvent] = {}
    identity_updates: dict[tuple[str, datetime | None], str] = {}
    for index, item in enumerate(items):
        if not isinstance(item, list) or len(item) != len(fields):
            raise ValueError('invalid_response_row_shape')
        event = _event(dict(zip(fields, item)), digest, index, observed)
        update_key = event.record_id, event.provider_updated_at
        if update_key in identity_updates and identity_updates[update_key] != event.version_id:
            raise ValueError('conflicting_forecast_version')
        identity_updates[update_key] = event.version_id
        if event.version_id in versions:
            prior = versions[event.version_id]
            event = replace(prior, source_rows=prior.source_rows + (index,))
        versions[event.version_id] = event
    events = tuple(sorted(versions.values(), key=lambda e: (e.available_at, e.record_id, e.provider_updated_at or datetime.min.replace(tzinfo=UTC), e.version_id)))
    return AnalystForecastBatch(digest, observed, len(items), events, has_more, count)


def _event(row: dict[str, Any], digest: str, index: int, observed: datetime) -> AnalystForecastEvent:
    symbol = _text(row.get('ts_code'), required=True)
    if not re.fullmatch(r'[0-9]{6}\.(SH|SZ|BJ)', symbol):
        raise ValueError('invalid_stock_identity')
    code, market = symbol.split('.')
    asset = f"CN_{ {'SH':'XSHG','SZ':'XSHE','BJ':'XBEI'}[market]}_{code}"
    institution = _text(row.get('org_name'), required=True)
    author = _text(row.get('author_name'), required=True)
    title = _text(row.get('report_title'), required=True)
    period = _text(row.get('quarter'), required=True)
    if not re.fullmatch(r'[0-9]{4}Q[1-4]', period) or period.startswith('0000'):
        raise ValueError('invalid_forecast_period')
    report_day = _report_date(row.get('report_date'))
    start = datetime.combine(report_day, time(), CHINA).astimezone(UTC)
    if start > observed:
        raise ValueError('report_after_observation')
    updated = _provider_time(row.get('create_time'))
    if updated is not None and updated < start:
        raise ValueError('provider_update_before_report')
    if updated is not None and updated > observed:
        raise ValueError('provider_update_after_observation')
    available = max(observed, start + timedelta(days=1))
    report_type, classification = _text(row.get('report_type')), _text(row.get('classify'))
    identity = [SCHEMA, asset, institution, author, period, report_day.isoformat(), title, report_type, classification]
    record_id = _fingerprint(identity)
    metrics = [_number(row.get(name)) for name in ('np', 'eps', 'tp', 'min_price', 'max_price')]
    version_id = _fingerprint([record_id, updated.isoformat() if updated is not None else None, metrics])
    return AnalystForecastEvent(record_id, version_id, digest, (index,), asset, institution, author, period,
                                report_day, title, report_type, classification, updated, observed, available,
                                *metrics)


def _text(value: Any, *, required: bool = False) -> str:
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise ValueError('invalid_identity_text')
    result = unicodedata.normalize('NFC', value.strip())
    if required and not result:
        raise ValueError('missing_identity_text')
    return result


def _report_date(value: Any) -> date:
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{8}|[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError('invalid_report_date')
    try:
        return datetime.strptime(value, '%Y%m%d' if len(value) == 8 else '%Y-%m-%d').date()
    except ValueError as exc:
        raise ValueError('invalid_report_date') from exc


def _provider_time(value: Any) -> datetime | None:
    if value is None or value == '':
        return None
    if not isinstance(value, str) or not re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}', value):
        raise ValueError('invalid_provider_update_time')
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('invalid_provider_update_time') from exc
    if result.tzinfo is None:
        result = result.replace(tzinfo=CHINA)
    return result.astimezone(UTC)


def _number(value: Any) -> Decimal | None:
    if value is None or value == '':
        return None
    if isinstance(value, bool) or not isinstance(value, (str, int, Decimal)):
        raise ValueError('invalid_forecast_number')
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError('invalid_forecast_number') from exc
    if not result.is_finite():
        raise ValueError('nonfinite_forecast_number')
    return result


def _decimal_identity(value: Decimal) -> str:
    if value == 0:
        return '0'
    sign, digits, exponent = value.as_tuple()
    digits = list(digits)
    while digits[-1] == 0:
        digits.pop(); exponent += 1
    return f"{sign}:{''.join(map(str, digits))}:{exponent}"


def _fingerprint(value: Any) -> str:
    content = json.dumps(value, ensure_ascii=False, separators=(',', ':'), default=_decimal_identity)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate_response_key')
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError('nonfinite_json_number')
