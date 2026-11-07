"""One-shot public chart transport and opaque four-source evidence assembly.

No release authority, financial conversion, strategy or application credential
lookup lives here. The caller must enforce reviews, durable batch claim and finite
window. Socket timeouts/deadline checks are NOT an independent wall-clock kill;
the reviewed task supervisor owns the five-minute outer deadline. If it kills
this call, request/attempt/partial files remain and no final receipt is invented.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
from http.client import IncompleteRead
import json
import os
from pathlib import Path
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from quant_robot.ops import us_allocation_source_contract as C

CAP = 4 * 1024 * 1024
SAFE_HEADERS = ('Date', 'Content-Type', 'Content-Length', 'Content-Encoding',
                'Transfer-Encoding', 'Last-Modified', 'ETag', 'Cache-Control', 'Retry-After')


def _require(ok, code):
    if not ok:
        raise ValueError(code)


def _now():
    return datetime.now(timezone.utc)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _expected_ref(path, raw):
    return dict(path=str(Path(path).resolve()), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def _bound(ref):
    _require(C._ref(ref), 'invalid_source_reference')
    raw = Path(ref['path']).read_bytes()
    _require(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'], 'source_reference_changed')
    return raw


def _save(path, value):
    raw = value if type(value) is bytes else _canonical(value)
    ref = _expected_ref(path, raw)  # Written bytes, never a later disk baseline.
    with Path(path).open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    _require(Path(path).read_bytes() == raw, 'saved_bytes_changed')
    return ref


def expected_url(symbol, start, end, *, assets=C.ASSETS):
    """The exact known Yahoo route; dates are canonical UTC query boundaries."""
    _require(symbol in C._asset_scope(assets), 'symbol')
    for item in (start, end):
        _require(type(item) is str and date.fromisoformat(item).isoformat() == item, 'canonical_query_date')
    _require(start < end, 'query_interval')
    first = int(datetime.fromisoformat(start + 'T00:00:00+00:00').timestamp())
    last = int(datetime.fromisoformat(end + 'T00:00:00+00:00').timestamp())
    return (f'https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1={first}&period2={last}'
            '&interval=1d&events=div%2Csplits%2CcapitalGains&includeAdjustedClose=true')


def _validate_url(url, *, assets=C.ASSETS):
    parts = urlsplit(url)
    _require(parts.scheme == 'https' and parts.netloc == 'query2.finance.yahoo.com'
             and not parts.fragment, 'exact_public_host')
    symbol = parts.path.removeprefix('/v8/finance/chart/')
    query = parse_qs(parts.query, strict_parsing=True)
    _require(set(query) == {'period1', 'period2', 'interval', 'events', 'includeAdjustedClose'}
             and all(len(v) == 1 for v in query.values()), 'exact_query_keys')
    values = []
    for key in ('period1', 'period2'):
        token = query[key][0]
        _require(token.isascii() and token.isdigit(), 'query_timestamp')
        instant = datetime.fromtimestamp(int(token), timezone.utc)
        _require(instant.time().isoformat() == '00:00:00', 'UTC_query_boundary')
        values.append(instant.date().isoformat())
    _require(url == expected_url(symbol, *values, assets=assets), 'exact_chart_URL')


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_one(url, prefix, *, socket_timeout=20, max_body_bytes=CAP, deadline_at=None, assets=C.ASSETS):
    """Return (immutable bytes, raw ref or None, receipt, receipt ref).

    HTTP_attempts_started counts entered opener.open calls, not reservations or
    proof of packets reaching the provider. Interrupted calls without a receipt
    have unknown dispatch/completion, even when an attempt-intent file exists.
    At most cap+1 bytes are read/retained (one oversize detection byte); EOF and
    length checks are required for raw_complete. Error bodies remain opaque.
    """
    _validate_url(url, assets=assets)
    _require(type(socket_timeout) in (int, float) and 0 < socket_timeout <= 20
             and type(max_body_bytes) is int and 0 < max_body_bytes <= CAP, 'bounded_transport_budget')
    deadline = C._instant(deadline_at) if deadline_at is not None else None
    _require(deadline_at is None or deadline is not None, 'UTC_deadline')
    prefix = Path(prefix).resolve(); prefix.parent.mkdir(parents=True, exist_ok=True)
    paths = {k:prefix.with_name(prefix.name + suffix) for k,suffix in
             [('request', '_request.json'), ('attempt', '_attempt.json'),
              ('raw', '_raw.body'), ('receipt', '_receipt.json')]}
    _require(not any(path.exists() for path in paths.values()), 'already_reserved_no_retry')
    request_ref = _save(paths['request'], dict(schema='us_chart_request_v1', url=url, method='GET',
        reserved_at=_now().isoformat(), socket_timeout_seconds=socket_timeout,
        max_body_bytes=max_body_bytes, oversize_probe_bytes=1, deadline_at=deadline_at,
        redirects=0, retries=0, application_credentials_added=False,
        proxy_configuration='urllib_default_environment_or_system_not_inspected'))
    result = dict(schema='us_chart_capture_receipt_v1', url=url, request=request_ref, attempt=None,
        request_started_at=None, headers_received_at=None, body_completed_at=None, retained_at=None,
        failed_at=None, HTTP_status=None, headers={}, HTTP_attempts_started=0,
        attempt_count_basis='opener_open_invocation_not_remote_receipt',
        raw_complete=False, raw=None, bytes_received=0, bytes_retained=0,
        oversize_detection_bytes=0, content_length=None, error=None,
        independent_worker_used=False, transport_call_returned=False,
        independent_wall_timeout=False, financial_values_decoded=False)
    response = None; retained = bytearray()
    try:
        if deadline is not None:
            _require(_now() < deadline, 'deadline_before_dispatch')
        # Preserve the proven default urllib proxy route without inspecting it.
        # Application code adds no credentials; underlying proxy auth is unknown.
        opener = build_opener(_NoRedirect())
        req = Request(url, headers={'User-Agent':'Mozilla/5.0', 'Accept':'application/json',
                                   'Accept-Encoding':'identity', 'Connection':'close'}, method='GET')
        remaining = socket_timeout if deadline is None else min(socket_timeout, (deadline-_now()).total_seconds())
        _require(remaining > 0, 'deadline_before_dispatch')
        started = _now().isoformat()
        result['attempt'] = _save(paths['attempt'], dict(schema='us_chart_attempt_intent_v1',
            url=url, dispatch_intent_at=started, actual_dispatch_confirmed=False))
        result['request_started_at'] = started
        try:
            response = opener.open(req, timeout=remaining)
        except HTTPError as exc:
            response = exc  # Preserve opaque error/redirect body, never follow.
        finally:
            result['HTTP_attempts_started'] = 1
        result['HTTP_status'] = int(response.code)
        result['headers_received_at'] = _now().isoformat()
        result['headers'] = {key:str(response.headers[key]) for key in SAFE_HEADERS if key in response.headers}
        raw_length = response.headers.get('Content-Length')
        if raw_length is not None:
            _require(raw_length.isascii() and raw_length.isdigit(), 'invalid_content_length')
            result['content_length'] = int(raw_length)
        if result['HTTP_status'] != 200:
            result['error'] = 'redirect_blocked' if 300 <= result['HTTP_status'] < 400 else 'HTTP_error'
        if response.headers.get('Content-Encoding', 'identity').lower() not in ('', 'identity'):
            result['error'] = 'unexpected_content_encoding'
        with paths['raw'].open('xb') as stream:
            while True:
                if deadline is not None:
                    _require(_now() < deadline, 'deadline_during_body')
                room = max_body_bytes + 1 - len(retained)
                chunk = response.read(min(65536, room))
                _require(type(chunk) is bytes and len(chunk) <= min(65536, room), 'invalid_read_contract')
                if not chunk:
                    result['body_completed_at'] = _now().isoformat()
                    if result['content_length'] is not None and len(retained) != result['content_length']:
                        result['error'] = 'content_length_mismatch'
                    else:
                        result['raw_complete'] = True
                    break
                retained.extend(chunk); stream.write(chunk); stream.flush(); os.fsync(stream.fileno())
                if len(retained) > max_body_bytes:
                    result['oversize_detection_bytes'] = 1; result['error'] = 'body_cap_exceeded'
                    break
    except IncompleteRead as exc:
        # http.client exposes bytes already received when framing ends early.
        partial = exc.partial if type(exc.partial) is bytes else b''
        room = max_body_bytes + 1 - len(retained)
        _require(len(partial) <= room, 'invalid_partial_read_contract')
        retained.extend(partial)
        with paths['raw'].open('ab') as stream:
            stream.write(partial); stream.flush(); os.fsync(stream.fileno())
        result['error'] = 'incomplete_HTTP_body'
    except (TimeoutError, socket.timeout):
        result['error'] = 'socket_timeout'
    except URLError:
        result['error'] = 'transport_error'
    except Exception as exc:
        result['error'] = 'deadline' if str(exc) in ('deadline_before_dispatch', 'deadline_during_body') else 'capture_error'
    finally:
        if response is not None:
            try:
                response.close()
            except Exception:
                result['error'] = result['error'] or 'response_close_error'
        result['transport_call_returned'] = True
    raw = bytes(retained); retained_integrity = True
    if paths['raw'].exists():
        # Only this synchronous call writes it. Compare to bytes seen on read.
        result['raw'] = _expected_ref(paths['raw'], raw)
        if paths['raw'].read_bytes() != raw:
            result['error'] = 'retained_bytes_changed'; result['raw_complete'] = False
            retained_integrity = False
        else:
            result['retained_at'] = _now().isoformat()
    result['bytes_received'] = len(raw)
    result['bytes_retained'] = len(raw) if retained_integrity else None
    result['retained_bytes_verified'] = retained_integrity
    if result['error'] is not None:
        result['failed_at'] = _now().isoformat()
    receipt_ref = _save(paths['receipt'], result)
    return raw, result['raw'], result, receipt_ref


def build_source_packet(scope, manifest, key, captured, batch_ref, *, prior_session_date=None,
                        prior_committed_ref=None, prior_committed_at=None, assets=C.ASSETS):
    """Bind saved sources.json and four receipts; describe only opaque identity.

    coverage_complete refers solely to this provider query snapshot. No auction,
    publication, exchange finality, executable status or issuer completeness is
    inferred. This function never imports the model or calls its numeric decoder.
    """
    assets = C._asset_scope(assets)
    _require(type(captured) is dict and set(captured) == set(assets), 'four_captured_sources')
    saved = json.loads(_bound(batch_ref))
    expected = {s:dict(raw=captured[s][1], receipt=captured[s][3]) for s in assets}
    _require(saved == expected, 'batch_source_manifest_binding')
    schedule = manifest['schedule']; authorities = manifest['authorities']
    dates = [row['date'] for row in schedule['sessions']]
    target = scope['operation_dates'][0] if key == 'warmup' else key
    _require(target in dates and (key == 'warmup' or key in scope['operation_dates']), 'operation_session')
    index = dates.index(target)
    wanted = dates[max(0, index-20):index] if key == 'warmup' else [target]
    if key == 'warmup':
        _require(len(wanted) == 20, 'twenty_prior_sessions')
    def authority(kind):
        matches = [(identifier,row) for identifier,row in authorities.items() if row.get('kind') == kind]
        _require(len(matches) == 1 and C._ref(matches[0][1].get('definition_ref')), 'unique_declared_authority')
        return matches[0]
    provider_id, provider = authority('provider_daily_completed')
    action_id, actions = authority('corporate_action_coverage')
    packet = dict(schema='us_allocation_source_evidence_v1', purpose='warmup' if key == 'warmup' else 'daily_model',
        symbols=list(assets), session_date=target, calendar_ref=deepcopy(schedule['source_ref']),
        source_ref=deepcopy(batch_ref), records={})
    received = []
    for symbol in assets:
        raw, raw_ref, receipt, receipt_ref = captured[symbol]
        _require(type(raw) is bytes and _bound(raw_ref) == raw, 'immutable_raw_binding')
        _require(json.loads(_bound(receipt_ref)) == receipt and receipt.get('raw') == raw_ref,
                 'receipt_raw_binding')
        _require(receipt.get('url') == scope['requests'][key]['urls'][symbol]
                 and receipt.get('HTTP_status') == 200 and receipt.get('raw_complete') is True
                 and receipt.get('error') is None and receipt.get('transport_call_returned') is True
                 and receipt.get('HTTP_attempts_started') == 1, 'successful_single_capture_required')
        request = json.loads(_bound(receipt['request']))
        attempt = json.loads(_bound(receipt['attempt']))
        _require(request.get('url') == receipt['url'] == attempt.get('url')
                 and request.get('method') == 'GET'
                 and attempt.get('actual_dispatch_confirmed') is False,
                 'request_attempt_identity')
        reserved = C._instant(request.get('reserved_at'))
        intent = C._instant(attempt.get('dispatch_intent_at'))
        clocks = [C._instant(receipt.get(k)) for k in
                  ('request_started_at', 'headers_received_at', 'body_completed_at', 'retained_at')]
        _require(reserved is not None and intent is not None and all(t is not None for t in clocks)
                 and reserved <= intent == clocks[0] and clocks == sorted(clocks)
                 and clocks[-1] <= _now(), 'capture_clock_order')
        description = C.describe_yahoo_source(raw, raw_ref, symbol=symbol, assets=assets)
        _require(description['dates'] == wanted, 'exact_source_dates_no_intersection')
        _require(description['event_counts']['splits'] == 0 and description['event_counts']['capitalGains'] == 0,
                 'split_or_capital_gain_unsupported')
        row = dict(currency=description['currency'], timezone=description['timezone'], source_ref=deepcopy(raw_ref),
            receipt_ref=deepcopy(receipt_ref), source_authority=provider_id, definition_ref=deepcopy(provider['definition_ref']),
            complete=True, received_at=receipt['body_completed_at'], observation_kind='completed_daily',
            effective_at=None, provider_available_at=None, finality='provider_snapshot_finality_unknown',
            execution=dict(suspended=None, buy_blocked=None, sell_blocked=None),
            units=dict(prices='USD_per_share', volume='shares', dividend='USD_per_share'),
            corporate_actions=dict(authority=action_id, definition_ref=deepcopy(actions['definition_ref']),
                coverage_complete=True, coverage_basis='provider_query_snapshot_only', coverage_dates=list(wanted),
                units='USD_per_share', split_ratio_unit='new_shares_per_old_share', splits_absent=True,
                capital_gains_absent=True, event_counts=description['event_counts']))
        if key == 'warmup':
            row.update(dates=list(wanted), session_complete=[True]*20)
        else:
            row.update(provider_bar_interval='1d', provider_trading_date=target,
                provider_bucket_timestamp=description['provider_bucket_timestamps'][0],
                session_open_at=schedule['sessions'][index]['open_at'],
                session_close_at=schedule['sessions'][index]['close_at'])
        received.append(clocks[2]); packet['records'][symbol] = row
    packet['received_at'] = max(received).isoformat()
    if key == 'warmup':
        packet['warmup_dates'] = list(wanted)
    else:
        packet.update(previous_observed_session_date=prior_session_date,
            previous_committed_decision_at=prior_committed_at,
            previous_committed_decision_ref=deepcopy(prior_committed_ref))
    assessment = C.assess_source_metadata(packet, schedule, authorities=authorities, assets=assets)
    _require(assessment['requirements_met'], 'source_metadata_requirements')
    return packet
