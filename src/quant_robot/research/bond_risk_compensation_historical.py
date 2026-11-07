"""Fixed511220 known-history loader and serial conditional accounts.

No live data retrieval. Only a durable admission capability may cross the first
financial parser. Shared Parquet rowgroups may be decoded internally; only the
fixed asset/date/column projection is passed to the account or persisted.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, localcontext
import io
import math
from pathlib import Path

from quant_robot.paper import bond_risk_compensation as kernel
from quant_robot.research import bond_risk_compensation_admission as admission

ASSET='CN_ETF_XSHG_511220'
SOURCE_CLASS='retained_known_historical_sources'
START='2020-01-02'
END='2024-06-28'
IDENTITY={'asset_id':ASSET,'symbol':'511220.SH','market':'CN_ETF','exchange':'XSHG','asset_type':'etf',
          'currency':'CNY','source':'tushare','frequency':'1d','timezone':'Asia/Shanghai','calendar':'XSHG','adjusted':False}
NUMERIC=('open','high','low','close','volume')
COLUMNS=tuple(IDENTITY)+('date','timestamp','ingested_at')+NUMERIC


@dataclass(frozen=True)
class LoadedBond:
    fixture: dict
    provenance: dict


def _require(ok,message):
    if not ok: raise ValueError(message)


def _require_claim(claim):
    _require(isinstance(claim,admission._Claim) and claim.active
             and admission.canonical(claim.packet['policy'])==admission.canonical(admission.POLICY),
             'Active exact bond claim required')


def _clock(value):
    _require(isinstance(value,datetime) and value.tzinfo is not None,'Retained timezone-aware ingest timestamp required')
    return value.astimezone(timezone.utc).isoformat()


def _number(value):
    _require(type(value) in (int,float) and math.isfinite(value),'Finite original numeric field required')
    # Stored source doubles cannot recover precision discarded by upstream;
    # preserve their shortest roundtrip decimal, without price or share rounding.
    return Decimal(str(value))


def _calendar(raw):
    rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    _require(rows and set(rows[0])=={'market','date','is_open','source'},'Exact retained calendar schema required')
    selected=[]
    for row in rows:
        if START<=row['date']<=END:
            _require(row['market']=='CN' and row['source']=='tushare' and row['is_open'] in ('0','1'),'Calendar identity invalid')
            _require(date.fromisoformat(row['date']).isoformat()==row['date'],'Calendar date invalid')
            if row['is_open']=='1': selected.append(row['date'])
    _require(len(selected)==1087 and selected==sorted(set(selected)) and selected[0]==START
             and selected[-1]==END and selected[19]=='2020-02-06' and selected[20]=='2020-02-07',
             'Exact1087session window and20session capacity prefix required')
    return selected


def _source_ref_in_packet(claim,source):
    path=Path(source['path'])
    relative=path.resolve().relative_to(claim.root).as_posix() if path.is_absolute() else source['path']
    ref={'path':relative,'sha256':source['sha256']}
    _require(ref in claim.packet['inputs'].values(),'Action/report original not bound in manifest')
    _require(admission.resolve_path(claim.root,relative).stat().st_size==source['bytes'],'Action source size changed')
    return ref


def _notice_acquisition(claim,order,source):
    receipt=admission._json(claim.read(f'PDF_receipt_{order:02}'))
    _require(receipt.get('body_complete') is True and receipt['entity']['sha256']==source['sha256'],
             'Original notice acquisition not linked')
    received=datetime.fromisoformat(receipt['body_received_at'].replace('Z','+00:00'))
    _require(received.tzinfo is not None,'Actual source receipt needs timezone')
    return received.astimezone(timezone.utc).isoformat()


def _decode_actions(claim,raw):
    facts=admission._json(raw['cash_action_facts']); closure=admission._json(raw['cash_action_closure'])
    projection=admission._json(raw['split_projection']); proposal=admission._json(raw['report_proposal'])
    _require(facts.get('artifact_type')=='511220_fifteen_dividend_notice_action_facts_v1'
             and len(facts.get('events',[]))==15,'Exact15retained cash events required')
    _require(closure.get('artifact_type')=='511220_annual_dividend_and_share_closure_v1'
             and closure.get('research_subinterval')==[START,END]
             and closure.get('all_15_notice_events_matched_once') is True
             and closure.get('cross_report_share_balance_links_exact') is True
             and closure.get('total_notice_events_matched')==15,'Reviewed complete cash-action closure required')
    requests=proposal['requests']; indexed={r['order']:r for r in requests}
    _require(len(indexed)==len(requests)==22,'Fixed22notice/report provenance required')
    event=projection['event']
    _require(event['asset_id']==ASSET and event['share_multiplier']=='10'
             and event['rights_record_date']=='2023-01-13' and event['ex_date']=='2023-01-16',
             'Exact single split10 event required')
    _require(indexed[1]['catalog_date']=='2023-01-10','Split condition-known catalog date required')
    split={'event_id':'511220_share_split_20230113_20230116_1_to_10','asset_id':ASSET,
        'record_date':'2023-01-13','ex_date':'2023-01-16','known_date':'2023-01-10',
        'registry_phase':'record_day_end','share_multiplier':'10'}
    actions=[]; evidence=[]; seen=set()
    for source in facts['events']:
        identity=source['event_id']; record=source['record_date']; ex=source['ex_date']; pay=source['pay_date']
        _require(identity not in seen and source['asset_id']==ASSET and START<=record<ex<=pay<=END,
                 'Distinct exact-window cash action dates required')
        seen.add(identity)
        _require(all(date.fromisoformat(x).isoformat()==x for x in (record,ex,pay)),'Invalid cash action date')
        denominator=source['declared_denominator_shares']
        _require(type(denominator) is int and denominator==10,'Original per10denominator required')
        _require(all(isinstance(source[k],str) for k in ('declared_amount_cny',
            'cash_per_event_date_share_cny','conditional_receipt_per_share_cny')),'Exact string cash amounts required')
        declared=Decimal(source['declared_amount_cny'])
        per=Decimal(source['cash_per_event_date_share_cny']); received=Decimal(source['conditional_receipt_per_share_cny'])
        _require(declared.is_finite() and per.is_finite() and received.is_finite()
                 and declared>=0 and per==declared/10 and received==per,
                 'Conditional per-share cash mapping inconsistent')
        era='pre_20230113_1_to_10_split' if record<split['ex_date'] else 'post_20230113_1_to_10_split'
        _require(source['share_unit_era']==era,'Cash record share-unit era inconsistent')
        notice=indexed[source['document']]
        _require(notice['role']=='cash_distribution_notice' and notice['symbol']=='511220'
                 and notice['catalog_date']<=record and notice['url']==source['notice_url'],
                 'Cash announcement metadata not mapped to original notice')
        unit='pre_split' if record<split['ex_date'] else 'post_split'
        actions.append({'event_id':identity,'asset_id':ASSET,'record_date':record,'ex_date':ex,'pay_date':pay,
            'cash_per_unit':str(received),'share_multiplier':'1','record_quantity_unit':unit,'cash_per_unit_basis':unit})
        evidence.append({'event_id':identity,'original':_source_ref_in_packet(claim,source['source']),
            'catalog_marked_date':notice['catalog_date'],'historical_first_available_at':None,
            'actual_body_received_at':_notice_acquisition(claim,source['document'],source['source']),
            'conditional_known_before_record':True,'gross_net_status':source['gross_net_status'],
            'investor_cash_availability':source['investor_cash_availability'],
            'declared_denominator_shares':10,'record_unit':unit})
    # Raw report and split bodies remain linked too; projection is no substitute.
    for report in closure['reports']: _source_ref_in_packet(claim,report['source'])
    for source in projection['raw_sources'].values(): _source_ref_in_packet(claim,source)
    return actions,[split],evidence


def load_claimed_inputs(claim):
    _require_claim(claim)
    _require(not claim.decoding_started,'Bond inputs may be decoded once')
    claim.guard('before','source_bytes')
    roles=('calendar','cash_action_facts','cash_action_closure','split_projection','report_proposal','input_authority')
    raw={role:claim.read(role) for role in roles}
    raw.update({'bars_'+str(year):claim.read('bars_'+str(year)) for year in range(2020,2025)})
    # Bytes are prepared and rehashed under the claim. This marker precedes
    # action amount arithmetic as well as the first numeric Parquet projection.
    claim.begin_financial_decode()
    with localcontext(kernel.CONTEXT):
        sessions=_calendar(raw['calendar'])
        actions,splits,action_evidence=_decode_actions(claim,raw)
        authority=admission._json(raw['input_authority'])
        _require(authority['asset_id']==ASSET and authority['metadata_expected']==IDENTITY
                 and authority['date_coverage']['rows']==1087,'Exact511220metadata authority required')
        import pyarrow as pa
        import pyarrow.parquet as pq
        bars=[]; clocks=[]
        for year in range(2020,2025):
            # Fixed files only; no dataset-directory discovery (in particular2026).
            dates=pq.read_table(pa.BufferReader(raw['bars_'+str(year)]),columns=['date'],
                                filters=[('asset_id','=',ASSET)]).column('date').to_pylist()
            _require(all(isinstance(day,date) and day.year==year and START<=day.isoformat()<=END for day in dates),
                     'Out-of-window target date in fixed partition')
            table=pq.read_table(pa.BufferReader(raw['bars_'+str(year)]),columns=list(COLUMNS),
                filters=[('asset_id','=',ASSET),('date','>=',date.fromisoformat(START)),('date','<=',date.fromisoformat(END))])
            for source in table.to_pylist():
                _require(all(source.get(k)==v and type(source.get(k))==type(v) for k,v in IDENTITY.items()),
                         'Target source identity/type invalid')
                day=source['date'].isoformat()
                _require(day[:4]==str(year) and day in sessions,'Partition date mismatch')
                timestamp=source['timestamp']; acquired=source['ingested_at']
                _require(isinstance(timestamp,datetime) and timestamp.tzinfo is not None
                         and timestamp.astimezone(timezone(timedelta(hours=8))).date().isoformat()==day,'Original bar timestamp/date mapping invalid')
                clocks.append(_clock(acquired))
                values={key:_number(source[key]) for key in NUMERIC}
                bars.append({'date':day,'asset_id':ASSET,**{k:str(v) for k,v in values.items()},
                    'suspended':None,'limit_up':None,'limit_down':None,
                    'share_unit':'pre_split' if day<splits[0]['ex_date'] else 'post_split'})
        bars.sort(key=lambda x:x['date'])
        _require([x['date'] for x in bars]==sessions,'Missing/duplicate/unexpected target bar date')
        fixture={'evidence_class':SOURCE_CLASS,'asset_id':ASSET,'invented_values':False,
            'price_unit':'CNY_per_share','volume_unit':'shares','price_basis':'raw_unadjusted',
            'corporate_actions_complete':True,'sessions':sessions,'bars':bars,'actions':actions,'split_events':splits}
        # Complete validation happens once before any economic account.
        prepared=kernel._prepare(fixture,kernel.SPLIT_MODE,context=kernel.HISTORICAL_CONTEXT)
        kernel._prepare_split(fixture,prepared,kernel.SPLIT_MODE,context=kernel.HISTORICAL_CONTEXT)
        provenance={'evidence_class':SOURCE_CLASS,'original_asset_and_dates_preserved':True,
            'registration_sha256':claim.packet['registration_sha256'],'financial_decode_claim_sha256':claim.claim_hash,
            'source_acquisition':{'retained_row_ingested_at_min':min(clocks),'retained_row_ingested_at_max':max(clocks),
                'semantics':'stored pipeline ingested_at; not provider publication or historical availability'},
            'historical_first_available_at':None,'actual_source_request_clocks_bound_by_manifest':True,
            'numeric_mapping':'source stored double shortest-roundtrip decimal; stored shares/CNY not rescaled',
            'split_raw_quote_units':'declared unadjusted event-date unit mapping; no independent exchange numeric certification',
            'conditional_assumptions':['previous complete daily bar available before next open',
                'catalog-marked announcement rules known before modeled action',
                'open-print fills conditional; all secondary suspension/limit flags unknown',
                'cash on stated payment date after fills; no account-specific tax/receipt certification'],
            'shared_partition_decode_boundary':'PyArrow may decode shared rowgroups internally; only exact511220/date/column projection reaches model/output; only5fixed partitions read',
            'action_evidence':action_evidence,'corporate_actions_complete_scope':'accepted source interval and conditional account mapping; not actual account receipt verification',
            'qualified':False,'real_forward':0}
    claim.guard('after','source_decode')
    return LoadedBond(fixture,provenance)


def loaded_digest(data):
    return admission.digest(admission.canonical({'fixture':data.fixture,'provenance':data.provenance}))


def _persist_account(folder,result):
    admission.write_exclusive_json(folder/'complete.json',result)
    # Each durable file is closed by the exclusive writer before index publish;
    # Windows sync must use writable handles if any later sync is added.
    return {'path':str(folder/'complete.json'),'sha256':admission.file_digest(folder/'complete.json')}


def _annual_attribution(result):
    """Continuous-CNY attribution, never credit/duration/coupon decomposition."""
    rows=result['rows']; years=sorted({r['date'][:4] for r in rows}); output=[]
    opening=Decimal('10000')
    with localcontext(kernel.CONTEXT):
        for year in years:
            selected=[r for r in rows if r['date'].startswith(year)]
            closing=Decimal(selected[-1]['equity'])
            fills=[f for f in result['fills'] if f['date'].startswith(year)]
            fees=sum((Decimal(f['fee']) for f in fills),Decimal(0))
            impact=sum((Decimal(f['slippage_and_tick_cost_CNY']) for f in fills),Decimal(0))
            payments=sum((Decimal(x['amount']) for x in result['actions']
                          if x['date'].startswith(year) and x['kind']=='paid_after_fills'),Decimal(0))
            output.append({'year':year,'opening_carried_NAV':opening,'ending_book_NAV':closing,
                'net_book_change':closing-opening,'commission_paid':fees,'slippage_tick_cost_already_in_fills':impact,
                'cash_distributions_received':payments,
                'attribution_limit':'net change includes share marks, receivable changes, timing and all costs; no isolated credit/duration/coupon estimate'})
            opening=closing
        return kernel._exact(output)


def run_claimed_diagnostic(claim):
    _require_claim(claim)
    data=load_claimed_inputs(claim); frozen=loaded_digest(data)
    folder=admission.resolve_path(claim.root,admission.DIRECTORY)
    admission.write_exclusive_json(folder/'decoded_input.json',{'fixture':data.fixture,'provenance':data.provenance})
    decoded_artifact={'path':admission.DIRECTORY+'/decoded_input.json',
        'sha256':admission.file_digest(folder/'decoded_input.json'),'canonical_sha256':frozen}
    accounts={}
    def guard(phase,identity):
        claim.guard(phase,identity)
        _require(loaded_digest(data)==frozen,'Decoded inputs changed between accounts')
    def prepared():
        value=kernel._prepare(data.fixture,kernel.SPLIT_MODE,context=kernel.HISTORICAL_CONTEXT)
        split=kernel._prepare_split(data.fixture,value,kernel.SPLIT_MODE,context=kernel.HISTORICAL_CONTEXT)
        return value,split
    for minimum,slip in kernel.COST_CASES:
        identity=f'M{minimum}_S{slip}'; guard('before',identity)
        target=folder/'accounts'/identity
        admission.write_exclusive_json(target/'started.json',dict(at=datetime.now(timezone.utc).isoformat(),scenario=identity))
        try:
            with localcontext(kernel.CONTEXT):
                value,split=prepared()
                result=kernel._exact(kernel._account(value,minimum,slip,split,context=kernel.HISTORICAL_CONTEXT))
            result.update(scenario=identity,source_provenance=data.provenance,study_number=21,
                          account_complete=True,execution_class='conditional_known_historical_bond')
            result['annual_attribution']=_annual_attribution(result)
            artifact=_persist_account(target,result)
        except BaseException as exc:
            admission.write_exclusive_json(target/'failed.json',dict(error_type=type(exc).__name__,account_complete=False,qualified=False))
            raise
        guard('after',identity)
        _require(result['historical_returns_computed'] is True and result['evidence_class']==SOURCE_CLASS
                 and result['qualified'] is False,'Historical account identity invalid')
        artifact['path']=Path(artifact['path']).relative_to(claim.root).as_posix()
        summary=result['summary']
        accounts[identity]={**artifact,'account_complete':True,'terminal_unsettled':summary['terminal_unsettled'],
            'conditional_net_book_PnL':summary['net_book_PnL'],'daily_close_model_max_drawdown':summary['daily_close_model_max_drawdown'],
            'execution_uncertainty_count':summary['execution_uncertainty_count'],'qualified':False}
        admission.write_exclusive_json(folder/'account_index'/f'{len(accounts):02}.json',accounts[identity])
    guard('before','CASH')
    cash={'artifact_type':'conditional_historical_zero_interest_cash_control_v1','evidence_class':SOURCE_CLASS,
        'scenario':'CASH','initial_cash_CNY':'10000','rows':[{'date':d,'cash':'10000','equity':'10000'} for d in data.fixture['sessions']],
        'interest':'0','qualified':False,'account_complete':True,'historical_returns_computed':True,
        'not_riskfree_return_or_income_target':True}
    artifact=_persist_account(folder/'accounts/CASH',cash); guard('after','CASH')
    accounts['CASH']={**artifact,'path':Path(artifact['path']).relative_to(claim.root).as_posix(),'account_complete':True}
    guard('before','NONTRADING_REFERENCE')
    with localcontext(kernel.CONTEXT):
        value,split=prepared()
        reference=kernel._exact(kernel._reference(value,split,context=kernel.HISTORICAL_CONTEXT))
    reference.update(source_provenance=data.provenance,study_number=21)
    artifact=_persist_account(folder/'reference',reference); guard('after','NONTRADING_REFERENCE')
    return {'artifact_type':'conditional_bond_risk_compensation_result_v1','registration_sha256':claim.packet['registration_sha256'],
        'evidence_class':SOURCE_CLASS,'historical_returns_computed':True,'qualified':False,'real_forward':0,'study_number':21,
        'strategy_accounts':9,'cash_controls':1,'additional_nontrading_references':1,'primary':'M5_S10','accounts':accounts,
        'reference':{**artifact,'path':Path(artifact['path']).relative_to(claim.root).as_posix(),'not_an_executable_account':True,
                     'terminal_unsettled':reference['summary']['terminal_unsettled']},
        'decoded_input_sha256':frozen,'decoded_input_artifact':decoded_artifact,'source_provenance':data.provenance,
        'comparison_purpose':'conditional_bond_risk_compensation_only','holding_control_tested':False,
        'alpha_or_promotion_eligible':False,'source_quality_or_execution_certified':False}
