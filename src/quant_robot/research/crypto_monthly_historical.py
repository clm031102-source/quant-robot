"""Exact original-format historical adapter, accessible only under a live claim.

This file never relabels retained observations as synthetic or changes their date.
The shared parser/controller are numerical primitives; the public API requires
the admission module's process-local, durable, fully fingerprinted capability.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from quant_robot.research import crypto_monthly_admission as admission
from quant_robot.research.crypto_monthly_diagnostic import (
    DAY, MARKETS, PRIMARY, SCENARIOS, RawArchive, RawMonthlyBundle,
    _base, _decode_month_core, _json, _run_account_core,
)

START=datetime(2025,1,1,tzinfo=timezone.utc)
END=datetime(2025,2,1,tzinfo=timezone.utc)
ARCHIVES={'spot':('spot_1m_zip','spot_1m_checksum'),
          'um':('futures_1m_zip','futures_1m_checksum'),
          'mark':('mark_1m_zip','mark_1m_checksum'),
          'funding':('funding_zip','funding_checksum')}


def _require_claim(claim):
    if (not isinstance(claim,admission._Claim) or not claim.active or not claim.decoding_started
            or claim.packet['policy']!=admission.POLICY):
        raise ValueError('Live reviewed claim required before historical decode')


def _clock(text):
    if not isinstance(text,str): raise ValueError('Original acquisition clock required')
    if text.endswith(' UTC'):
        return datetime.strptime(text,'%Y-%m-%d %H:%M:%S UTC').replace(tzinfo=timezone.utc).isoformat()
    value=datetime.fromisoformat(text.replace('Z','+00:00'))
    if value.tzinfo is None: raise ValueError('UTC-aware acquisition clock required')
    return value.astimezone(timezone.utc).isoformat()


def load_claimed_month(claim):
    _require_claim(claim)
    claim.guard('before','source_decode')
    projection=admission._json(claim.read('time_projection_result'))
    rows=projection.get('rows',[])
    if (projection.get('status')!='complete_timestamp_projection' or len(rows)!=4
            or {row['market'] for row in rows}!={'spot_1m','futures_1m','mark_1m','funding'}):
        raise ValueError('Frozen timestamp projection schema changed')
    indexed={row['market']:row for row in rows}
    for market in ('spot_1m','futures_1m','mark_1m'):
        if (indexed[market].get('exact_minute_grid') is not True or indexed[market].get('row_count')!=44640
                or indexed[market].get('financial_values_decoded') is not False):
            raise ValueError('Exact prechecked minute structure required')
    times=tuple(indexed['funding']['event_times_ms'])
    if len(times)!=93 or any(type(t) is not int for t in times) or sum(bool(t%60000) for t in times)!=12:
        raise ValueError('Exact93 millisecond clocks with12 offsets required')
    capture=admission._json(claim.read('funding_source_capture'))
    if (capture.get('row_count')!=93 or capture.get('isError') is not False
            or capture.get('raw_artifact_kind')!='serialized_MCP_response_not_native_HTTP_entity'):
        raise ValueError('Original MCP acquisition receipt required')
    source_received=_clock(capture['clocks']['received']['current_time'])
    source_requested=_clock(capture['clocks']['started']['current_time'])
    if source_received<source_requested: raise ValueError('Original request/receive clock reversed')
    original_batch=admission._json(claim.read('archive_original_source_result'))
    checksum_repair=admission._json(claim.read('spot_checksum_repair_result'))
    batch_upper=_clock(original_batch['completed_at'])
    checksum_upper=_clock(checksum_repair['completed_at'])
    archives={}
    for market,(zip_role,checksum_role) in ARCHIVES.items():
        filename=Path(claim.packet['inputs'][zip_role]['path']).name
        expected='BTCUSDT-fundingRate-2025-01.zip' if market=='funding' else 'BTCUSDT-1m-2025-01.zip'
        if filename!=expected: raise ValueError('Only exact202501 original member names permitted')
        archives[market]=RawArchive(filename,filename[:-4]+'.csv',claim.read(zip_role),claim.read(checksum_role))
    raw=RawMonthlyBundle(START,END,archives,claim.read('funding_raw_MCP'),times,
        'retained_historical_sources',None,None,None)
    provenance={
        'evidence_class':'retained_historical_sources','fixture_created_at':None,
        'actual_market_values_decoded':True,'financial_source_files_decoded':5,
        'actual_market_acquired_at':None,'historical_first_publication_at':None,
        'acquisition_clock_semantics':'actual_retained_receipts_not_offline_model_event_clocks',
        'source_acquisition':{'funding_mcp':{'requested_at':source_requested,'received_at':source_received,
            'receipt_sha256':claim.packet['inputs']['funding_source_capture']['sha256'],
            'native_http_entity':False},
            'archive_zip':{'acquired_at_exact':None,'batch_completed_upper_bound':batch_upper,
                'receipt_sha256':claim.packet['inputs']['archive_original_source_result']['sha256']},
            'spot_checksum':{'acquired_at_exact':None,'repair_completed_upper_bound':checksum_upper,
                'receipt_sha256':claim.packet['inputs']['spot_checksum_repair_result']['sha256']}},
        'registration_sha256':claim.packet['registration_sha256'],
        'financial_decode_claim_sha256':claim.claim_hash,
        'original_dates_preserved':True,'historical_rule_and_execution_certification':False,
        'raw_kernel_journal_label_semantics':
            'Legacy not_evaluated_synthetic_only event labels identify the reused kernel, not source identity or qualification; historical summary/provenance govern evidence class. Failures and unresolved states remain unchanged.',
    }
    data=_decode_month_core(raw,source_provenance=provenance)
    if data.coverage['days']!=31 or data.coverage['minutes_per_market']!=44640 or data.coverage['funding_events']!=93:
        raise ValueError('Historical decode scope changed')
    claim.guard('after','source_decode')
    return data


def loaded_digest(data):
    """Post-claim value fingerprint: detects mutable dict changes between accounts."""
    h=hashlib.sha256()
    for value in (data.start,data.end,data.provenance,data.coverage): h.update((_json(value)+'\n').encode())
    for market in MARKETS:
        h.update((market+'\n').encode())
        # These frozen typed fields have delimiter-free ISO/Decimal encodings;
        # avoid dataclasses.asdict deep-copying every datetime 20 times/month.
        for bar in data.bars[market]:
            c=bar.candle
            h.update(('|'.join((c.start.isoformat(),c.end.isoformat(),c.received_at.isoformat(),
                str(c.open),str(c.high),str(c.low),str(c.close),str(bar.volume_btc)))+'\n').encode())
    for event in data.funding: h.update((_json(asdict(event))+'\n').encode())
    return h.hexdigest()


def _durable_account(folder):
    """Flush the already-closed account files before publishing its batch index."""
    for path in sorted(folder.iterdir()):
        if not path.is_file(): raise ValueError('Unexpected account subdirectory')
        with path.open('r+b') as stream:
            stream.flush()
            os.fsync(stream.fileno())


def run_claimed_month(claim):
    _require_claim(claim)
    data=load_claimed_month(claim)
    frozen_loaded=loaded_digest(data)
    folder=admission.resolve_path(claim.root,admission.DIRECTORY)
    accounts={}; completed=[]
    def guard(phase,identity):
        claim.guard(phase,identity)
        if loaded_digest(data)!=frozen_loaded: raise ValueError('Decoded input changed between accounts')
    for scenario in SCENARIOS:
        guard('before',scenario)
        account_dir=folder/'accounts'/scenario
        # Account-level execution/risk failures are returned with their full
        # trajectory. An unexpected software exception stops this consumed batch.
        result=_run_account_core(data,scenario=scenario,output_dir=account_dir)
        guard('after',scenario)
        if (result.get('scenario')!=scenario or result.get('qualified') is not False
                or result.get('real_forward')!=0 or result.get('historical_returns_computed') is not True
                or result.get('final_drawdown_metric')!='conditional_drawdown_including_terminal_haircut'):
            raise ValueError('Historical account identity/label contract changed')
        _durable_account(account_dir)
        accounts[scenario]={'path':str((account_dir/'summary.json').relative_to(claim.root)).replace('\\','/'),
            'sha256':admission.file_digest(account_dir/'summary.json'),'status':result['status'],
            'account_complete':result['account_complete'],
            'terminal_unsettled':None if result['terminal'] is None else result['terminal']['terminal_unsettled'],
            'sampled_book_drawdown_before_terminal_haircut':result['sampled_book_drawdown_before_terminal_haircut'],
            'conditional_drawdown_including_terminal_haircut':result['conditional_drawdown_including_terminal_haircut'],
            'final_drawdown_metric':result['final_drawdown_metric'],'qualified':False}
        completed.append(scenario)
        admission.write_exclusive_json(folder/'account_index'/f'{len(completed):02}.json',accounts[scenario])
    guard('before','CASH')
    cash={**_base(data),'scenario':'CASH','nav':'1000','interest':'0','fees':'0','account_complete':True,
        'historical_returns_computed':True,'economic_exercise_complete':False,
        'daily_nav':[{'day':(START+i*DAY).date().isoformat(),'nav':'1000'} for i in range(31)],
        'reason':'non_trading_cash_reference_not_holding_comparison'}
    admission.write_exclusive_json(folder/'accounts/CASH/summary.json',cash)
    guard('after','CASH')
    accounts['CASH']={'path':admission.DIRECTORY+'/accounts/CASH/summary.json',
                     'sha256':admission.file_digest(folder/'accounts/CASH/summary.json'),'account_complete':True}
    return {'artifact_type':'conditional_crypto_monthly_historical_result_v1','registration_sha256':claim.packet['registration_sha256'],
        'evidence_class':'retained_historical_sources','historical_returns_computed':True,
        'qualified':False,'real_forward':0,'study_number':19,'strategy_accounts':9,'cash_controls':1,
        'primary':PRIMARY,'accounts':accounts,'all_accounts_complete':all(row['account_complete'] for row in accounts.values()),
        'decoded_input_sha256':frozen_loaded,'source_provenance':data.provenance,'coverage':data.coverage,
        'comparison_purpose':'conditional_one_month_mechanism_only','holding_control_tested':False,
        'alpha_or_promotion_eligible':False,'final_drawdown_metric':'conditional_drawdown_including_terminal_haircut'}
