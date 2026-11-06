"""Offline-tested fund_daily entity-body capture and exact field mapping.

No production transport, credential lookup, source allowance or forward gate is
provided here. Every capture in this version is explicitly synthetic. HTTP Date
is a response clock, not the publication time of a daily market observation.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from email.utils import parsedate_to_datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit


SOURCE_URL = 'https://api.tushare.pro'
API_NAME = 'fund_daily'
FIELDS = ('ts_code', 'trade_date', 'open', 'high', 'low', 'close', 'vol', 'amount')
MAX_BYTES = 65536
HTTP_CLOCK_TOLERANCE_SECONDS = 5
RECEIPT_TYPE = 'tushare_fund_daily_synthetic_receipt_v1'
SAFE_FAILURE_CODES = {
    'explicit_UTC_clock_required', 'invalid_UTC_clock', 'duplicate_JSON_key',
    'nonfinite_JSON_constant', 'response_byte_budget_exceeded',
    'credential_echo_not_archived', 'invalid_JSON_not_archived',
    'provider_response_rejected', 'data_object_missing',
    'fund_daily_field_contract_changed', 'exactly_one_requested_symbol_date_row_required',
    'invalid_fund_daily_row_shape', 'unexpected_pagination',
    'invalid_unverified_count_metadata', 'response_symbol_or_date_mismatch',
    'inconsistent_OHLC', 'invalid_HTTP_Date_header', 'response_endpoint_changed',
    'HTTP_status_rejected', 'credential_or_invalid_HTTP_header_not_archived',
    'response_chunk_must_be_bytes', 'host_clock_regressed',
    *{field+'_'+reason for field in ('open','high','low','close','vol','amount')
      for reason in ('must_be_JSON_number','invalid_range','precision_budget_exceeded')},
}
UNIT_CONTRACT = {
    'official_definition_reference': 'https://tushare.pro/document/2?doc_id=127',
    'frozen_local_review': 'docs/research/cn_etf_turnover_precision_review_2026-09-13.md',
    'vol': {'source_unit': 'hands', 'target_unit': 'fund_units', 'decimal_shift': 2},
    'amount': {'source_unit': 'thousand_CNY', 'target_unit': 'CNY', 'decimal_shift': 3},
    'price': 'provider_raw_OHLC_no_adjustment_applied',
}


class ReceiptError(ValueError):
    """Only constant local error codes are safe to persist after an API failure."""


def _canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def _sha(value):
    return sha256(value).hexdigest()


def _write(path, raw):
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _write_json(path, value):
    _write(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                           allow_nan=False).encode('utf-8') + b'\n')


def _utc(value):
    if isinstance(value, str):
        if not value.endswith('Z'):
            raise ReceiptError('explicit_UTC_clock_required')
        try:
            value = datetime.fromisoformat(value[:-1] + '+00:00')
        except ValueError as exc:
            raise ReceiptError('invalid_UTC_clock') from exc
    if (not isinstance(value, datetime) or value.tzinfo is None
            or value.utcoffset() is None or value.utcoffset().total_seconds() != 0):
        raise ReceiptError('explicit_UTC_clock_required')
    return value


def _stamp(value):
    return _utc(value).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _now():
    return datetime.now(timezone.utc)


def request_identity(ts_code, trade_date):
    if not isinstance(ts_code, str) or not re.fullmatch(r'[0-9]{6}\.(SH|SZ)', ts_code):
        raise ReceiptError('single_SH_SZ_symbol_required')
    if not isinstance(trade_date, str) or not re.fullmatch(r'[0-9]{8}', trade_date):
        raise ReceiptError('single_trade_date_required')
    try:
        datetime.strptime(trade_date, '%Y%m%d')
    except ValueError as exc:
        raise ReceiptError('invalid_trade_date') from exc
    return dict(url=SOURCE_URL, method='POST', api_name=API_NAME,
                params={'ts_code': ts_code, 'trade_date': trade_date}, fields=list(FIELDS),
                credentials_retained=False, verify_TLS=True, allow_redirects=False)


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ReceiptError('duplicate_JSON_key')
        value[key] = item
    return value


def _reject_constant(value):
    raise ReceiptError('nonfinite_JSON_constant')


def _secret_echo(value, token):
    if isinstance(value, str):
        return bool(token and token in value)
    if isinstance(value, list):
        return any(_secret_echo(item, token) for item in value)
    if isinstance(value, dict):
        if any(key.lower() in {'token', 'password', 'api_key', 'authorization', 'secret'} for key in value):
            return True
        return any(_secret_echo(key, token) or _secret_echo(item, token) for key, item in value.items())
    return False


def decode_body(raw, *, token=None):
    if not isinstance(raw, bytes) or len(raw) > MAX_BYTES:
        raise ReceiptError('response_byte_budget_exceeded')
    if token and token.encode('utf-8') in raw:
        raise ReceiptError('credential_echo_not_archived')
    try:
        parsed = json.loads(raw, object_pairs_hook=_object, parse_float=Decimal,
                            parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ReceiptError('invalid_JSON_not_archived') from exc
    if _secret_echo(parsed, token):
        raise ReceiptError('credential_echo_not_archived')
    return parsed


def _number(value, field, *, positive=False):
    if type(value) not in (int, Decimal):
        raise ReceiptError(f'{field}_must_be_JSON_number')
    number = Decimal(value)
    if not number.is_finite() or number < 0 or positive and number == 0:
        raise ReceiptError(f'{field}_invalid_range')
    if len(number.as_tuple().digits) > 128 or abs(number.as_tuple().exponent) > 128:
        raise ReceiptError(f'{field}_precision_budget_exceeded')
    return number


def _decimal_text(number, shift=0):
    parts = number.as_tuple()
    # Decimal exponent shift, without binary float or decimal-context rounding.
    scaled = Decimal((parts.sign, parts.digits, parts.exponent + shift))
    return format(scaled, 'f')


def parse_fund_daily_body(raw, *, ts_code, trade_date):
    request_identity(ts_code, trade_date)
    parsed = decode_body(raw)
    if not isinstance(parsed, dict) or type(parsed.get('code')) is not int or parsed['code'] != 0:
        raise ReceiptError('provider_response_rejected')
    data = parsed.get('data')
    if not isinstance(data, dict):
        raise ReceiptError('data_object_missing')
    fields, rows = data.get('fields'), data.get('items')
    if (not isinstance(fields, list) or len(fields) != len(FIELDS)
            or any(not isinstance(field, str) for field in fields)
            or set(fields) != set(FIELDS)):
        raise ReceiptError('fund_daily_field_contract_changed')
    if not isinstance(rows, list) or len(rows) != 1:
        raise ReceiptError('exactly_one_requested_symbol_date_row_required')
    if not isinstance(rows[0], list) or len(rows[0]) != len(FIELDS):
        raise ReceiptError('invalid_fund_daily_row_shape')
    if 'has_more' in data and (type(data['has_more']) is not bool or data['has_more']):
        raise ReceiptError('unexpected_pagination')
    if 'count' in data and (type(data['count']) is not int or data['count'] < 0):
        raise ReceiptError('invalid_unverified_count_metadata')
    row = dict(zip(fields, rows[0], strict=True))
    if row['ts_code'] != ts_code or row['trade_date'] != trade_date:
        raise ReceiptError('response_symbol_or_date_mismatch')
    values = {key: _number(row[key], key, positive=key in ('open', 'high', 'low', 'close'))
              for key in ('open', 'high', 'low', 'close', 'vol', 'amount')}
    if not (values['low'] <= min(values['open'], values['close'])
            <= max(values['open'], values['close']) <= values['high']):
        raise ReceiptError('inconsistent_OHLC')
    exchange = 'XSHG' if ts_code.endswith('.SH') else 'XSHE'
    bar = dict(asset_id=f'CN_ETF_{exchange}_{ts_code[:6]}',
               date=datetime.strptime(trade_date, '%Y%m%d').date().isoformat(),
               **{key: _decimal_text(values[key]) for key in ('open', 'high', 'low', 'close')},
               volume=_decimal_text(values['vol'], 2), amount=_decimal_text(values['amount'], 3),
               suspended=None, limit_up=None, limit_down=None)
    return dict(bar=bar, field_order=fields, rows=1, unit_contract=UNIT_CONTRACT,
                normalized_bar_sha256=_sha(_canonical(bar)),
                source_adjustment_semantics_verified=False, adjustment_applied=False,
                asset_membership_verified=False,
                fund_daily_row_is_not_ETF_membership_evidence=True,
                daily_bar_finality_verified=False, session_close_verified=False,
                execution_constraints_complete=False,
                corporate_actions=None, corporate_actions_complete=False,
                provider_count=data.get('count'), provider_count_semantics_verified=False,
                provider_generated_at=None, provider_available_at=None,
                first_publication_verified=False, source_quality_verified=False,
                real_forward_eligible=False)


def _http_clock(raw, *, started, received):
    output = dict(http_date=raw, http_date_utc=None, status='missing',
                  role='server_response_clock_not_market_publication_time',
                  local_clock_attested=False, tolerance_seconds=HTTP_CLOCK_TOLERANCE_SECONDS)
    if raw is None:
        return output
    if not isinstance(raw, str) or len(raw) > 128:
        raise ReceiptError('invalid_HTTP_Date_header')
    try:
        parsed = parsedate_to_datetime(raw)
        if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
            raise ValueError('UTC HTTP Date required')
        parsed = parsed.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        output['status'] = 'unparseable'
        # An invalid header may be a credential echo disguised by escaping.
        # Keep its fingerprint, never arbitrary unparsed header text.
        output['http_date'] = None
        output['unparseable_header_sha256'] = _sha(raw.encode('utf-8'))
        return output
    output['http_date_utc'] = _stamp(parsed)
    tolerance = timedelta(seconds=HTTP_CLOCK_TOLERANCE_SECONDS)
    output['status'] = ('consistent_with_local_request_window'
                        if started-tolerance <= parsed <= received+tolerance else 'outside_local_request_window')
    return output


def _availability_bound(received):
    return dict(at=_stamp(received),
        basis='client_finished_receiving_this_response_not_first_publication',
        clock_class='local_UTC_unattested_synthetic_transport')


def _endpoint(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'api.tushare.pro'
            or parsed.port not in (None, 443) or parsed.username or parsed.password
            or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
        raise ReceiptError('response_endpoint_changed')


def _ref(path):
    return {'name': path.name, 'sha256': _sha(path.read_bytes())}


def _read_bound(folder, ref):
    if (not isinstance(ref, dict) or set(ref) != {'name', 'sha256'}
            or ref['name'] not in ('claim.json', 'response.entity.json')):
        raise ReceiptError('invalid_receipt_reference')
    path = folder/ref['name']
    if path.is_symlink() or not path.resolve().is_relative_to(folder.resolve()):
        raise ReceiptError('receipt_path_escapes_archive')
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES+1)
    if len(raw) > MAX_BYTES:
        raise ReceiptError('archive_byte_budget_exceeded')
    if _sha(raw) != ref['sha256']:
        raise ReceiptError('archive_hash_mismatch')
    return raw


def verify_receipt(path):
    path = Path(path)
    with path.open('rb') as stream:
        raw_receipt = stream.read(MAX_BYTES+1)
    if len(raw_receipt) > MAX_BYTES:
        raise ReceiptError('receipt_byte_budget_exceeded')
    receipt = json.loads(raw_receipt)
    if not isinstance(receipt, dict):
        raise ReceiptError('receipt_object_required')
    supplied = receipt.pop('sha256', None)
    if supplied != _sha(_canonical(receipt)) or receipt.get('artifact_type') != RECEIPT_TYPE:
        raise ReceiptError('receipt_hash_mismatch')
    claim = json.loads(_read_bound(path.parent, receipt['claim']))
    if (claim['request'] != receipt['request'] or claim['evidence_class'] != 'synthetic_only'
            or claim['request_started_at'] != receipt['request_started_at']):
        raise ReceiptError('claim_identity_mismatch')
    if (receipt.get('evidence_class') != 'synthetic_only'
            or any(receipt.get(key) is not False for key in (
                'real_forward_eligible', 'first_publication_verified', 'source_quality_verified',
                'daily_bar_finality_verified', 'session_close_verified',
                'live_capture_enabled', 'source_allowance_issued'))
            or receipt.get('provider_generated_at') is not None
            or receipt.get('provider_available_at') is not None):
        raise ReceiptError('synthetic_receipt_cannot_be_promoted')
    if request_identity(**receipt['request']['params']) != receipt['request']:
        raise ReceiptError('fixed_request_identity_changed')
    if receipt['status'] not in ('captured_synthetic', 'captured_synthetic_clock_review_required', 'capture_rejected'):
        raise ReceiptError('invalid_receipt_status')
    captured = receipt['status'].startswith('captured_')
    if captured and (not isinstance(receipt.get('parsed'), dict)
            or receipt.get('response_body') is None or receipt.get('received_at') is None
            or not isinstance(receipt.get('http_clock'), dict)):
        raise ReceiptError('successful_capture_requires_raw_mapping_and_clocks')
    if receipt.get('received_at') is not None and _utc(receipt['received_at']) < _utc(receipt['request_started_at']):
        raise ReceiptError('host_clock_regressed')
    raw_ref = receipt.get('response_body')
    if raw_ref is not None:
        raw = _read_bound(path.parent, raw_ref)
        if type(receipt.get('response_bytes')) is not int or receipt['response_bytes'] != len(raw):
            raise ReceiptError('receipt_response_byte_count_mismatch')
        if receipt.get('parsed') is not None:
            parsed = parse_fund_daily_body(raw, **receipt['request']['params'])
            if parsed != receipt['parsed']:
                raise ReceiptError('raw_to_normalized_mapping_mismatch')
    elif (path.parent/'response.entity.json').exists():
        raise ReceiptError('unbound_response_body')
    if captured:
        started, received = _utc(receipt['request_started_at']), _utc(receipt['received_at'])
        if receipt.get('availability_upper_bound') != _availability_bound(received):
            raise ReceiptError('receipt_availability_bound_mismatch')
        clock = _http_clock(receipt['http_clock'].get('http_date'), started=started, received=received)
        if clock != receipt['http_clock'] or clock['status'] == 'unparseable':
            raise ReceiptError('receipt_HTTP_clock_mismatch')
        expected_status = ('captured_synthetic' if clock['status']=='consistent_with_local_request_window'
                           else 'captured_synthetic_clock_review_required')
        if receipt['status'] != expected_status:
            raise ReceiptError('receipt_clock_status_mismatch')
    receipt['sha256'] = supplied
    return receipt


def capture_synthetic_receipt(archive, *, ts_code, trade_date, token, transport,
                              clock=_now, synthetic_only=True):
    """Exercise one injected transport. This API never issues eligible live evidence.

    Production HTTP creation is deliberately absent. Tests pass an in-memory
    transport; even an accidentally supplied real transport remains unqualified.
    """
    if synthetic_only is not True:
        raise ReceiptError('capture_scope_synthetic_only')
    if transport is None:
        raise ReceiptError('live_transport_not_implemented_or_reviewed')
    request = request_identity(ts_code, trade_date)
    if not isinstance(token, str) or not 16 <= len(token) <= 256:
        raise ReceiptError('explicit_test_credential_required')
    folder = Path(archive)/(trade_date+'_'+ts_code.replace('.', '_'))
    claim_path, receipt_path = folder/'claim.json', folder/'receipt.json'
    if claim_path.exists():
        if receipt_path.exists():
            receipt = verify_receipt(receipt_path)
            return dict(status='already_captured', receipt_path=str(receipt_path.resolve()),
                        receipt_sha256=receipt['sha256'], real_forward_eligible=False)
        return dict(status='attempt_incomplete', real_forward_eligible=False)
    started = _utc(clock())
    claim = dict(artifact_type='tushare_fund_daily_synthetic_claim_v1', request=request,
                 request_started_at=_stamp(started), evidence_class='synthetic_only',
                 source_allowance_issued=False, live_capture_enabled=False)
    folder.mkdir(parents=True, exist_ok=True)
    _write_json(claim_path, claim)
    receipt = dict(artifact_type=RECEIPT_TYPE, evidence_class='synthetic_only', request=request,
                   claim=_ref(claim_path), request_started_at=_stamp(started), received_at=None,
                   status='capture_rejected', response_body=None, parsed=None,
                   http_clock=None, availability_upper_bound=None,
                   provider_generated_at=None, provider_available_at=None,
                   first_publication_verified=False, source_quality_verified=False,
                   daily_bar_finality_verified=False, session_close_verified=False,
                   live_capture_enabled=False, real_forward_eligible=False,
                   source_allowance_issued=False,
                   representation='response_entity_bytes_after_HTTP_content_decoding_not_wire_bytes',
                   implementation_sha256=_sha(Path(__file__).read_bytes()))
    try:
        transport.trust_env = False
        with transport.post(SOURCE_URL, json=dict(api_name=API_NAME, token=token,
                params=request['params'], fields=','.join(FIELDS)),
                timeout=(10, 20), stream=True, allow_redirects=False, verify=True) as response:
            _endpoint(response.url)
            if response.status_code != 200:
                raise ReceiptError('HTTP_status_rejected')
            headers = {str(key).lower(): value for key, value in response.headers.items()}
            http_date = headers.get('date')
            if http_date is not None and (not isinstance(http_date, str) or token in http_date):
                raise ReceiptError('credential_or_invalid_HTTP_header_not_archived')
            body = bytearray()
            for chunk in response.iter_content(8192):
                if not isinstance(chunk, bytes):
                    raise ReceiptError('response_chunk_must_be_bytes')
                body.extend(chunk)
                if len(body) > MAX_BYTES:
                    raise ReceiptError('response_byte_budget_exceeded')
        received = _utc(clock())
        if received < started:
            raise ReceiptError('host_clock_regressed')
        receipt['received_at'] = _stamp(received)
        receipt['http_clock'] = _http_clock(http_date, started=started, received=received)
        receipt['availability_upper_bound'] = _availability_bound(received)
        if receipt['http_clock']['status'] == 'unparseable':
            raise ReceiptError('invalid_HTTP_Date_header')
        decode_body(bytes(body), token=token)  # Reject credential echoes before persistence.
        raw_path = folder/'response.entity.json'
        _write(raw_path, bytes(body))
        receipt['response_body'] = _ref(raw_path)
        receipt['response_bytes'] = len(body)
        receipt['parsed'] = parse_fund_daily_body(bytes(body), ts_code=ts_code, trade_date=trade_date)
        receipt['status'] = ('captured_synthetic' if receipt['http_clock']['status']=='consistent_with_local_request_window'
                             else 'captured_synthetic_clock_review_required')
    except ReceiptError as exc:
        receipt['failure_code'] = (str(exc) if str(exc) in SAFE_FAILURE_CODES
                                   else 'transport_or_unclassified_failure_redacted')
    except Exception:
        # Transport exceptions can contain authorization payloads or tokens.
        receipt['failure_code'] = 'transport_or_unclassified_failure_redacted'
    receipt['sha256'] = _sha(_canonical(receipt))
    _write_json(receipt_path, receipt)
    return dict(status=receipt['status'], receipt_path=str(receipt_path.resolve()),
                receipt_sha256=receipt['sha256'], real_forward_eligible=False)
