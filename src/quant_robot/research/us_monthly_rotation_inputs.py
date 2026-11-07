"""Pure Yahoo-source normalization, called only AFTER the outer durable decode marker.

No transport, credentials, trading, admission, or automatic source substitution.
The caller binds original bytes and supplies its claim/marker provenance. Current
quote metadata and all values in split-history quote arrays are never converted.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
import json
import re
from zoneinfo import ZoneInfo

ASSETS = ('SPY', 'EFA', 'IEF', 'GLD')
METHOD_SHA256 = 'dbc19912feded581fd55c4a5e0aa992140e3dfa4743586df2cd3a00c83e04a30'
START, TERMINAL = '2004-12-01', '2024-12-31'
FIELDS = ('open', 'high', 'low', 'close', 'adj_close', 'volume')
NY = ZoneInfo('America/New_York')
NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z')


def _require(value, label):
    if not value:
        raise ValueError(label)


def _pairs(items):
    result = {}
    for key, value in items:
        _require(key not in result, 'duplicate_json_key')
        result[key] = value
    return result


def _opaque(raw):
    _require(type(raw) is bytes, 'immutable_source_bytes_required')
    try:
        return json.loads(raw, parse_int=str, parse_float=str, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonstandard_number')))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('source_json') from exc


def _row(raw, symbol, *, split_history=False):
    obj = _opaque(raw)
    _require(type(obj) is dict and type(obj.get('chart')) is dict, 'chart_object')
    chart = obj['chart']
    _require(chart.get('error') is None and type(chart.get('result')) is list
             and len(chart['result']) == 1, 'chart_result')
    row = chart['result'][0]
    _require(type(row) is dict and type(row.get('meta')) is dict, 'row_meta')
    meta = row['meta']
    _require(meta.get('symbol') == symbol and meta.get('currency') == 'USD'
             and meta.get('exchangeTimezoneName') == 'America/New_York'
             and meta.get('instrumentType') == 'ETF', 'source_identity_units')
    events = row.get('events', {})
    _require(type(events) is dict and set(events) <= {'dividends', 'splits', 'capitalGains'}, 'event_schema')
    _require(not events.get('capitalGains'), 'capital_gains_unsupported')
    for values in events.values():
        _require(type(values) is dict, 'event_container')
    return row


def _day(token):
    _require(type(token) is str and re.fullmatch(r'[0-9]+', token) is not None, 'timestamp_integer')
    try:
        return datetime.fromtimestamp(int(token), NY).date().isoformat()
    except (ValueError, OverflowError, OSError) as exc:
        raise ValueError('timestamp_range') from exc


def _number(token, *, volume=False):
    _require(type(token) is str and NUMBER.fullmatch(token) is not None, 'required_numeric_token')
    try:
        value = Decimal(token)
    except InvalidOperation as exc:
        raise ValueError('numeric_syntax') from exc
    _require(value.is_finite() and (value >= 0 if volume else value > 0), 'numeric_domain')
    return str(value)


def _splits(row, symbol, *, split_history=False):
    actual = []
    if split_history:
        _require(row['meta'].get('dataGranularity') == '1mo', 'split_history_interval')
    for key, event in row.get('events', {}).get('splits', {}).items():
        _require(type(event) is dict and {'date', 'numerator', 'denominator', 'splitRatio'} <= set(event), 'split_fields')
        event_day, key_day = _day(event['date']), _day(key)
        if split_history:
            # The retained 1mo response keys events by the NY calendar-month
            # bucket. Preserve that key separately from the actual event time.
            bucket = datetime.fromtimestamp(int(key), NY)
            _require(bucket.day == 1 and (bucket.hour, bucket.minute, bucket.second) == (0,0,0)
                     and key_day[:7] == event_day[:7], 'split_month_bucket')
            timestamps = row.get('timestamp')
            _require(type(timestamps) is list and timestamps.count(key) == 1, 'split_bucket_timestamp')
        else:
            _require(key == event['date'], 'split_key_date')
        actual.append({'source_key':key, 'event_timestamp':event['date'],
                       'key_ny_date':key_day, 'event_ny_date':event_day,
                       'key_semantics':'NY_month_start_bucket' if split_history else 'exact_event_timestamp',
                       'numerator_literal':event['numerator'], 'denominator_literal':event['denominator'],
                       'split_ratio':event['splitRatio']})
    _require(len(actual) == (1 if symbol == 'EFA' else 0), 'unexpected_split_chain')
    if symbol == 'EFA':
        item = actual[0]
        _require(item['event_ny_date'] == '2005-06-09' and item['numerator_literal'] in ('3','3.0')
                 and item['denominator_literal'] in ('1','1.0') and item['split_ratio'] == '3:1', 'unexpected_split_identity')
    return actual


def _hash(value):
    return hashlib.sha256(value).hexdigest()


def _hex(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def normalize_saved_sources(raw_by_symbol, *, split_raw_by_symbol, method_sha256,
                            provenance, before_numeric_decode, test_values=False):
    """Normalize supplied bytes; production caller MUST already hold claim/marker.

    Provenance hashes document the caller's authorization; this pure function does
    not issue or verify a financial release. Artificial tests are permanently
    labelled artificial, even when using the real historical calendar shape.
    """
    _require(method_sha256 == METHOD_SHA256, 'method_identity')
    _require(type(test_values) is bool and type(provenance) is dict and callable(before_numeric_decode), 'context_type')
    _require(set(raw_by_symbol) == set(ASSETS) == set(split_raw_by_symbol), 'exact_four_sources')
    if not test_values:
        _require(_hex(provenance.get('registration_sha256')), 'outer_registration_required')
    rows = {s: _row(raw_by_symbol[s], s) for s in ASSETS}
    split_rows = {s: _row(split_raw_by_symbol[s], s, split_history=True) for s in ASSETS}
    split_evidence = {symbol:{'daily':_splits(rows[symbol], symbol),
                             'monthly_metadata':_splits(split_rows[symbol], symbol, split_history=True)}
                      for symbol in ASSETS}
    dates = {}
    quote = {}
    adjusted = {}
    for symbol, row in rows.items():
        _require(type(row.get('timestamp')) is list, 'timestamps')
        d = [_day(t) for t in row['timestamp']]
        _require(d and d == sorted(set(d)) and d[0] == START and d[-1] == TERMINAL, 'date_bounds_order')
        _require(all(START <= x <= TERMINAL for x in d), 'date_outside_window')
        dates[symbol] = d
        indicators = row.get('indicators', {})
        q, a = indicators.get('quote'), indicators.get('adjclose')
        _require(type(q) is list and len(q) == 1 and type(q[0]) is dict
                 and type(a) is list and len(a) == 1 and type(a[0]) is dict, 'indicator_shape')
        _require(set(q[0]) == {'open','high','low','close','volume'}
                 and set(a[0]) == {'adjclose'}, 'required_indicator_fields')
        for values in (*q[0].values(), a[0]['adjclose']):
            _require(type(values) is list and len(values) == len(d), 'indicator_length')
        quote[symbol], adjusted[symbol] = q[0], a[0]['adjclose']
    _require(all(d == dates['SPY'] for d in dates.values()), 'date_sets_must_match_no_intersection')
    common = dates['SPY']
    month_last = {}
    for d in common:
        month_last[d[:7]] = d
    expected_months = [f'{year:04d}-{month:02d}' for year in range(2004,2025)
                       for month in range(1,13) if '2004-12' <= f'{year:04d}-{month:02d}' <= '2024-12']
    _require(list(month_last) == expected_months, 'missing_calendar_month')
    first = month_last['2005-12']
    _require(len([m for m in month_last if m <= '2005-12']) == 13, 'thirteen_month_warmup')
    _require(common.index(first) >= 20 and common.index(first)+4 < len(common)-1, 'warmup_execution_bounds')
    pending_dividends = []
    for symbol in ASSETS:
        seen = set()
        for key, event in rows[symbol].get('events', {}).get('dividends', {}).items():
            _require(type(event) is dict and {'date','amount'} <= set(event) and key == event['date'], 'dividend_fields')
            ex = _day(event['date'])
            _require(ex in common and ex not in seen, 'dividend_date_or_duplicate')
            seen.add(ex)
            if ex > first:
                pending_dividends.append((symbol,key,ex,event['amount']))
    # First and only numeric-transition callback; it must persist the outer marker.
    # All parsing below uses the same verified immutable byte representations.
    marker = before_numeric_decode()
    days = []
    for i, d in enumerate(common):
        terminal = d == TERMINAL
        prices = {}
        for symbol in ASSETS:
            raw = quote[symbol]
            if terminal:
                prices[symbol] = {f: (_number(raw['open'][i]) if f == 'open' else None) for f in FIELDS}
            else:
                values = {f: _number(adjusted[symbol][i] if f == 'adj_close' else raw[f][i], volume=f == 'volume') for f in FIELDS}
                _require(Decimal(values['low']) <= min(Decimal(values['open']), Decimal(values['close']))
                         <= max(Decimal(values['open']), Decimal(values['close'])) <= Decimal(values['high']), 'ohlc_order')
                prices[symbol] = values
        days.append({'date': d, 'prices': prices, 'terminal_open_only': terminal})
    dividends = [{'id':f'{s}:{key}', 'symbol':s, 'ex_date':ex,
                  'amount_per_share':_number(amount,volume=True)} for s,key,ex,amount in pending_dividends]
    dividends.sort(key=lambda e:(e['ex_date'], ASSETS.index(e['symbol']), e['id']))
    source_refs = {s:{'chart_sha256':_hash(raw_by_symbol[s]),'chart_bytes':len(raw_by_symbol[s]),
                      'split_history_sha256':_hash(split_raw_by_symbol[s]),'split_history_bytes':len(split_raw_by_symbol[s])} for s in ASSETS}
    prov = dict(provenance)
    prov.update(constructed_from_market_data=not test_values, test_injected_values=test_values,
                numeric_decode_marker=marker,
                split_policy_verified=True, capital_gains_present=False,
                split_event_metadata=split_evidence,
                source_identities=source_refs, same_provider_date_sets=True,
                independent_exchange_calendar_certified=False,
                historical_first_publication_verified=False,
                warmup_dividend_amounts_converted=False, terminal_non_open_values_converted=False,
                current_quote_metadata_converted=False,
                month_end_basis='same exact provider session sets; historical PIT/calendar completeness conditional')
    return {'schema':'us_monthly_rotation_fixture_v1',
            'evidence_kind':'artificial_values_true_calendar' if test_values else 'known_history_conditional',
            'assets':list(ASSETS),'days':days,'dividends':dividends,
            'first_decision_date':first,'terminal_date':TERMINAL,
            'method_sha256':METHOD_SHA256,'provenance':prov}


def load_inputs(root, source_manifest, *, method_sha256, registration_sha256, before_numeric_decode):
    """Root-relative bound source entrypoint; no copies and no implicit admission."""
    root = Path(root).resolve()
    _require(_hex(registration_sha256), 'registration_sha256')
    _require(source_manifest.get('schema') == 'us_monthly_rotation_sources_v1', 'manifest_schema')
    _require(set(source_manifest['charts']) == set(ASSETS) == set(source_manifest['split_metadata']), 'manifest_symbols')
    retained = {}
    def bound(ref):
        _require(type(ref) is dict and set(ref) == {'path','sha256','bytes'}, 'source_reference')
        p = Path(ref['path'])
        _require(not p.is_absolute() and '..' not in p.parts, 'root_relative_reference')
        p = (root/p).resolve()
        _require(p.is_relative_to(root) and type(ref['bytes']) is int and _hex(ref['sha256']), 'reference_boundary')
        raw = p.read_bytes()
        _require(len(raw) == ref['bytes'] and _hash(raw) == ref['sha256'], 'source_bytes_mismatch')
        _require(str(p) not in retained, 'source_path_duplicate')
        retained[str(p)] = ref
        return raw
    method = bound(source_manifest['method'])
    _require(_hash(method) == method_sha256 == METHOD_SHA256, 'method_bytes')
    charts, splits = {}, {}
    for symbol in ASSETS:
        entry = source_manifest['charts'][symbol]
        _require(set(entry) == {'raw','receipt','projection'}, 'chart_reference_roles')
        charts[symbol] = bound(entry['raw'])
        receipt = _opaque(bound(entry['receipt'])); bound(entry['projection'])
        _require(receipt.get('status',receipt.get('HTTP_status')) in ('200',200), 'source_HTTP_status')
        expected = receipt.get('raw_sha256') or receipt.get('raw',{}).get('sha256')
        _require(expected == entry['raw']['sha256'] and receipt.get('raw_complete') is True, 'source_receipt')
        entry = source_manifest['split_metadata'][symbol]
        _require(set(entry) == {'raw','receipt'}, 'split_reference_roles')
        splits[symbol] = bound(entry['raw']); receipt = _opaque(bound(entry['receipt']))
        _require(receipt.get('status') == '200' and receipt.get('error') is None
                 and receipt.get('raw_sha256') == entry['raw']['sha256'], 'split_receipt')
    for name in ('split_projection','remaining_source_outcome'):
        bound(source_manifest[name])
    provenance = {'registration_sha256':registration_sha256,
                  'source_manifest_sha256':_hash(json.dumps(source_manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),
                  'bound_sources':list(retained.values())}
    return normalize_saved_sources(charts,split_raw_by_symbol=splits,method_sha256=method_sha256,
        provenance=provenance,before_numeric_decode=before_numeric_decode)
