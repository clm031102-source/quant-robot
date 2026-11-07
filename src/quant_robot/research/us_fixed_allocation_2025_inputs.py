"""Bound 2025 fixed-allocation input adapter; no network or implicit admission.

Old chart prices outside December2024 and all adjusted/current quote prices stay
opaque. The caller must persist its once claim and numeric marker via callback.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from decimal import Decimal

from . import us_monthly_rotation_inputs as old

ASSETS = old.ASSETS
METHOD_SHA256 = 'c46de5d2ea527be77aea806cb6ab42c331b6e4b29070f4e89f840845ab7f74a1'
FIRST, TERMINAL = '2024-12-31', '2025-12-31'
require = old._require


def _hash(raw): return hashlib.sha256(raw).hexdigest()


def _quotes(row):
    timestamps = row.get('timestamp')
    require(type(timestamps) is list, 'timestamps')
    dates = [old._day(t) for t in timestamps]
    require(dates and dates == sorted(set(dates)), 'dates_order_unique')
    indicators = row.get('indicators', {})
    quote = indicators.get('quote')
    require(type(quote) is list and len(quote) == 1 and type(quote[0]) is dict, 'quote_shape')
    require(set(quote[0]) == {'open','high','low','close','volume'}, 'quote_fields')
    require(all(type(v) is list and len(v) == len(dates) for v in quote[0].values()), 'quote_length')
    require(row['meta'].get('dataGranularity') == '1d', 'daily_interval')
    # Adjustment arrays are not numerical inputs for a fixed-weight allocation.
    return dates, quote[0]


def normalize_saved_sources(raw_by_symbol, *, warmup_raw_by_symbol, split_raw_by_symbol,
                            method_sha256, provenance, before_numeric_decode,
                            session_metadata=None, test_values=False):
    require(method_sha256 == METHOD_SHA256, 'method_identity')
    require(type(provenance) is dict and type(test_values) is bool and callable(before_numeric_decode), 'context')
    require(set(raw_by_symbol) == set(warmup_raw_by_symbol) == set(split_raw_by_symbol) == set(ASSETS), 'four_sources')
    if not test_values: require(old._hex(provenance.get('registration_sha256')), 'registration_required')
    new_rows = {s:old._row(raw_by_symbol[s], s) for s in ASSETS}
    old_rows = {s:old._row(warmup_raw_by_symbol[s], s) for s in ASSETS}
    split_rows = {s:old._row(split_raw_by_symbol[s], s, split_history=True) for s in ASSETS}
    split_evidence = {s:old._splits(split_rows[s], s, split_history=True) for s in ASSETS}
    selection = {};dates_by_symbol = {};warm_by_symbol = {};account_by_symbol = {}
    for symbol in ASSETS:
        new_dates, new_quotes = _quotes(new_rows[symbol])
        old_dates, old_quotes = _quotes(old_rows[symbol])
        require(all('2025-01-01' <= d <= TERMINAL for d in new_dates), 'new_window')
        require(new_dates[-1] == TERMINAL, 'terminal_present')
        require(sorted({d[:7] for d in new_dates}) == [f'2025-{m:02d}' for m in range(1,13)], 'account_months')
        require(not new_rows[symbol].get('events', {}).get('splits'), 'holding_split_unsupported')
        indices = [i for i,d in enumerate(old_dates) if '2024-12-01' <= d <= FIRST]
        warm = [old_dates[i] for i in indices]
        require(len(warm) >= 20 and warm[-1] == FIRST, 'warmup_coverage')
        for event in old_rows[symbol].get('events', {}).get('splits', {}).values():
            require(old._day(event['date']) < warm[0], 'warmup_split_unsupported')
        selection[symbol] = [(old_quotes,i) for i in indices] + [(new_quotes,i) for i in range(len(new_dates))]
        dates_by_symbol[symbol] = warm + new_dates
        warm_by_symbol[symbol],account_by_symbol[symbol] = warm,new_dates
    require(all(d == dates_by_symbol['SPY'] for d in dates_by_symbol.values()), 'exact_date_sets_required')
    dates = dates_by_symbol['SPY']; first_index = dates.index(FIRST)
    require(first_index+4 < len(dates)-1, 'first_execution_bounds')
    observed = {'first_decision':FIRST,'first_sell':dates[first_index+1],'first_buy':dates[first_index+4],
                'terminal':TERMINAL,'warmup_dates':warm_by_symbol['SPY'],'account_dates':account_by_symbol['SPY']}
    if session_metadata is not None:require(observed == session_metadata, 'session_metadata_mismatch')
    pending = []
    for symbol in ASSETS:
        seen = set()
        for key,event in new_rows[symbol].get('events', {}).get('dividends', {}).items():
            require(type(event) is dict and {'date','amount'} <= set(event) and key == event['date'], 'dividend_schema')
            ex = old._day(event['date'])
            require(ex in account_by_symbol[symbol] and ex not in seen, 'dividend_date')
            seen.add(ex);pending.append((symbol,key,ex,event['amount']))
    marker = before_numeric_decode()
    days = []
    for i,when in enumerate(dates):
        terminal = when == TERMINAL;prices = {}
        for symbol in ASSETS:
            quote,slot = selection[symbol][i]
            prices[symbol] = {field:(old._number(quote[field][slot],volume=field=='volume')
                                     if field!='adj_close' and (not terminal or field=='open') else None)
                              for field in old.FIELDS}
            if not terminal:
                p=prices[symbol]
                require(Decimal(p['low']) <= min(Decimal(p['open']),Decimal(p['close']))
                        <= max(Decimal(p['open']),Decimal(p['close'])) <= Decimal(p['high']), 'ohlc_order')
        days.append({'date':when,'prices':prices,'terminal_open_only':terminal})
    dividends = [{'id':f'{s}:{key}','symbol':s,'ex_date':ex,'amount_per_share':old._number(amount,volume=True)}
                 for s,key,ex,amount in pending]
    dividends.sort(key=lambda e:(e['ex_date'],ASSETS.index(e['symbol']),e['id']))
    prov = dict(provenance)
    prov.update(constructed_from_market_data=not test_values,test_injected_values=test_values,numeric_decode_marker=marker,
        split_policy_verified=True,capital_gains_present=False,holding_window_splits_absent=True,
        split_event_metadata=split_evidence,session_metadata=observed,
        source_identities={s:{'new_chart_sha256':_hash(raw_by_symbol[s]),'warmup_chart_sha256':_hash(warmup_raw_by_symbol[s]),
                              'split_metadata_sha256':_hash(split_raw_by_symbol[s])} for s in ASSETS},
        adjusted_close_values_converted=False,current_quote_metadata_converted=False,warmup_dividend_amounts_converted=False,
        old_non_december2024_prices_converted=False,terminal_non_open_values_converted=False,
        historical_first_publication_verified=False,independent_exchange_calendar_certified=False)
    return {'schema':'us_fixed_allocation_2025_fixture_v1','evidence_kind':'artificial_values_true_calendar' if test_values else 'known_history_conditional',
            'assets':list(ASSETS),'days':days,'dividends':dividends,'first_decision_date':FIRST,'terminal_date':TERMINAL,
            'method_sha256':METHOD_SHA256,'provenance':prov}


def load_inputs(root, source_manifest, *, method_sha256, registration_sha256, before_numeric_decode):
    root=Path(root).resolve();require(old._hex(registration_sha256), 'registration_sha256')
    require(source_manifest.get('schema') == 'us_fixed_allocation_2025_sources_v1', 'manifest_schema')
    retained={}
    def bound(ref):
        require(type(ref) is dict and set(ref)=={'path','sha256','bytes'}, 'source_reference')
        path=Path(ref['path']);require(not path.is_absolute() and '..' not in path.parts, 'root_relative_reference')
        path=(root/path).resolve();require(path.is_relative_to(root), 'source_boundary')
        raw=path.read_bytes();require(len(raw)==ref['bytes'] and _hash(raw)==ref['sha256'], 'source_hash')
        if str(path) in retained:require(retained[str(path)]==ref, 'source_alias_conflict')
        retained[str(path)]=ref;return raw
    require(_hash(bound(source_manifest['method'])) == method_sha256 == METHOD_SHA256, 'method_bytes')
    groups={}
    for name in ('charts_2025','warmup_charts','split_metadata'):
        entries=source_manifest[name];require(set(entries)==set(ASSETS), 'manifest_assets');groups[name]={}
        for symbol,entry in entries.items():
            require(set(entry)==({'raw','receipt'} if name=='split_metadata' else {'raw','receipt','projection'}),'source_roles')
            groups[name][symbol]=bound(entry['raw']);receipt=old._opaque(bound(entry['receipt']))
            require(receipt.get('HTTP_status',receipt.get('status'))=='200','source_status')
            expected=receipt.get('raw_sha256') or receipt.get('raw',{}).get('sha256')
            require(expected==entry['raw']['sha256'],'source_receipt_raw')
            if name!='split_metadata':
                require(receipt.get('raw_complete') is True,'source_incomplete');bound(entry['projection'])
            else:require(receipt.get('error') is None,'split_source_error')
    bound(source_manifest['source_outcome']);bound(source_manifest['split_projection'])
    provenance={'registration_sha256':registration_sha256,'source_manifest_sha256':_hash(json.dumps(source_manifest,sort_keys=True,separators=(',',':')).encode()),'bound_sources':list(retained.values())}
    return normalize_saved_sources(groups['charts_2025'],warmup_raw_by_symbol=groups['warmup_charts'],split_raw_by_symbol=groups['split_metadata'],
        method_sha256=method_sha256,provenance=provenance,before_numeric_decode=before_numeric_decode,
        session_metadata=source_manifest['session_metadata'])
