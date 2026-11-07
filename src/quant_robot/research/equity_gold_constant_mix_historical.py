"""Fixed dual-ETF source adapter and serial controller. No network or live path.

Public load/run entrypoints require the durable production claim. Tests may call
private cores with explicit artificial values; production rejects that identity.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
from quant_robot.research.monthly_diagnostic_registration import canonical as _persisted_json_bytes
from quant_robot.research import equity_gold_constant_mix_admission as admission
from quant_robot.research import equity_gold_constant_mix as kernel
from quant_robot.ops import tushare_fund_daily_wire as wire

ASSETS=('CN_ETF_XSHG_510300','CN_ETF_XSHG_518880')
TEST_SOURCE='test_artificial_values_true_calendar'


@dataclass(frozen=True)
class LoadedInputs:
    fixture: dict
    provenance: dict
    context: kernel._ExecutionContext


def _require(ok,message):
    if not ok:raise ValueError(message)


def _production_claim(claim):
    _require(type(claim) is admission._Claim and claim.active,'Exact active production claim required')
    _require(claim.packet['policy']['source_nature']==admission.SOURCE,'Production source identity required')


def _digest(value):return admission.digest(admission.canonical(value))


def loaded_digest(data):return _digest({'fixture':data.fixture,'provenance':data.provenance})


def _bound_source(claim,source,relocations):
    """Resolve an exact original triple, never a permissive outside-root path."""
    _require(type(source) is dict and set(source)=={'path','sha256','bytes'},'Exact original reference triple required')
    _require(type(source['bytes']) is int and source['bytes']>=0,'Reference size required')
    path=Path(source['path'])
    original=path.resolve() if path.is_absolute() else admission.resolve_path(claim.root,source['path'])
    selected=None
    for role,pin in claim.packet['inputs'].items():
        candidate=admission.resolve_path(claim.root,pin['path'])
        if original==candidate and source['sha256']==pin['sha256'] and candidate.stat().st_size==source['bytes']:
            selected=role;break
    if selected is None:
        matches=[m for m in relocations['mappings'] if
            str(Path(m['original']['path']).resolve()).casefold()==str(original).casefold()
            and m['original']['sha256']==source['sha256'] and m['original']['bytes']==source['bytes']]
        _require(len(matches)==1,'Unmapped original path/hash/bytes identity')
        m=matches[0];selected=m['target_role'];pin=claim.packet['inputs'][selected]
        candidate=admission.resolve_path(claim.root,pin['path'])
        _require(candidate==Path(m['restored']['path']).resolve() and pin['sha256']==source['sha256']
                 and candidate.stat().st_size==source['bytes'] and m['restored']['sha256']==source['sha256']
                 and m['restored']['bytes']==source['bytes'],'Restored original identity mismatch')
    admission.read_bound(claim.root,claim.packet['inputs'][selected])
    return selected


def _time(value):
    _require(type(value) is str,'Documented current acquisition clock required')
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    _require(result.tzinfo is not None,'Timezone-aware acquisition clock required')
    return result.astimezone(timezone.utc)


def _metadata(claim,*,test_values=False):
    roles=('method','source_manifest','source_index','source_outcome','source_final_review',
           'sessions','action_bridge','action_review','tax_evidence','tax_review','relocations')
    raw={r:claim.read(r) for r in roles}
    values={r:admission._json(x) for r,x in raw.items()}
    dates=values['sessions'];manifest=values['source_manifest'];index=values['source_index']
    wire.validate_manifest(manifest,dates)
    _require(values['relocations'].get('artifact_type')=='constant_mix_exact_source_relocations_v1','Relocation schema')
    source_class='synthetic_only_not_source_evidence' if test_values else 'provider_wire_structure_only'
    # Current writer assigns this class; no arbitrary user flag upgrades artificial captures.
    _require(index.get('evidence_class')==source_class and index.get('request_count')==24
             and index.get('identity_rows')==4908 and len(index.get('roles',[]))==24,'Complete exact source index')
    outcome=values['source_outcome']
    _require(outcome.get('status')=='completed_structure_only' and outcome.get('evidence_class')==source_class
             and outcome.get('request_receipts')==index['roles'],'Source outcome/index mismatch')
    _require(_bound_source(claim,outcome['source_index'],values['relocations'])=='source_index','Outcome index reference mismatch')
    _bound_source(claim,outcome['batch_claim'],values['relocations'])
    review=values['source_final_review']
    _require(review.get('status')=='accepted_complete_source_structure_for_conditional_input'
             and review.get('source_index_sha256')==claim.packet['inputs']['source_index']['sha256']
             and review.get('qualified') is False,'Final source metadata review required')
    _require(values['action_review'].get('status')=='accepted_existing_metadata_bridge_for_future_conditional_input_only'
             and values['action_review']['bridge']['sha256']==claim.packet['inputs']['action_bridge']['sha256'],
             'Reviewed date/action bridge required')
    tax=values['tax_evidence'];tax_review=values['tax_review']
    _require(tax.get('artifact_type')=='constant_mix_event_tax_evidence_v1'
             and tax_review.get('status')=='accepted_documented_event_tax_mapping'
             and tax_review.get('tax_evidence_sha256')==claim.packet['inputs']['tax_evidence']['sha256']
             and tax_review.get('qualified') is False,'Independent event tax review required')
    _require(len(tax.get('events',[]))==10 and len({e['event_id'] for e in tax['events']})==10,'Exact10 tax event mappings')
    for e in tax['events']:
        _require(e.get('status')=='documented_exemption'
                 and e.get('cash_mapping')=='announced_per_share_no_income_tax_withholding'
                 and e.get('investor_net_credit_verified') is False
                 and e.get('tax_scope')=='documented_notice_conditional_holder'
                 and e.get('source_role') in claim.packet['inputs']
                 and type(e.get('source_field_or_page')) is str and e['source_field_or_page'],
                 'Unknown tax stops data acceptance; no default zero/gross-to-net')
    expected=values['method']['window']['quarter_sell_sessions']
    _require(len(expected)==40 and expected==sorted(set(expected)) and expected[0]=='2014-01-03'
             and dates.index(expected[0])==20 and dates[21]=='2014-01-06'
             and dates[-1]=='2024-01-02' and all(d in dates for d in expected),'Exact frozen quarter/calendar boundary')
    return values


def _receipt(claim,request,entry,relocations,*,test_values=False,batch_claim=None):
    _require(entry['request_id']==request['id'] and entry['role']==request['role'],'Source request order/role mismatch')
    raw_role=_bound_source(claim,entry['raw'],relocations)
    _require(raw_role==request['role'],'Original wire role identity mismatch')
    receipt_role=_bound_source(claim,entry['receipt'],relocations)
    receipt=admission._json(claim.read(receipt_role))
    expected_class='synthetic_only_not_source_evidence' if test_values else 'provider_wire_structure_only'
    _require(receipt.get('artifact_type')=='fund_daily_batch_request_receipt_v1'
             and receipt.get('evidence_class')==expected_class and receipt.get('request_id')==request['id']
             and receipt.get('error') is None and receipt.get('body_complete') is True
             and receipt.get('worker_exit_confirmed') is True and receipt.get('http_status')==200
             and type(receipt.get('received_bytes')) is int and receipt['received_bytes']==entry['raw']['bytes']
             and receipt.get('raw')==entry['raw'] and receipt.get('structure')==entry['structure']
             and receipt.get('request_claim')==entry['request_claim'],'Successful original source receipt required')
    claim_role=_bound_source(claim,entry['request_claim'],relocations)
    source_claim=admission._json(claim.read(claim_role))
    _require(source_claim.get('request')==request and source_claim.get('batch_claim')==batch_claim,'Original request/batch claim mismatch')
    clocks=[source_claim['at'],receipt['request_started_at'],receipt['headers_received_at'],
            receipt['body_completed_at'],receipt['retained_at']]
    ordered=[_time(x) for x in clocks]
    _require(ordered==sorted(ordered),'Claim/request/header/body/retention clock order invalid')
    if not test_values:_require(ordered[-1]<=datetime.now(timezone.utc),'Future acquisition clock rejected')
    return raw_role,dict(raw=entry['raw'],receipt=entry['receipt'],request_claim=entry['request_claim'],
        request_id=request['id'],role=request['role'],actual_claim_at=clocks[0],
        actual_request_started_at=clocks[1],actual_headers_received_at=clocks[2],
        actual_body_completed_at=clocks[3],actual_retained_at=clocks[4],historical_first_published_at=None,
        current_clock_not_historical_PIT=True)


def _wire_rows(raw,request):
    structure=wire.inspect_structure(raw,request)
    parsed=wire.decode_opaque(raw);output=[]
    for row_index,row in enumerate(parsed['data']['items']):
        day=wire._iso_date(row[1],compact=True)
        open_=kernel._number(row[2]);vol=kernel._number(row[6])
        _require(open_>0 and vol>=0,'Positive open and nonnegative volume required')
        terminal=day=='2024-01-02'
        if terminal:close=None
        else:
            high,low,close=(kernel._number(row[i]) for i in (3,4,5))
            _require(0<low<=min(open_,close)<=max(open_,close)<=high,'Finite positive coherent raw OHLC required')
        bar=dict(open=str(open_),close=None if terminal else str(close),volume=str(vol*100),
                 suspended=None,buy_blocked=None,sell_blocked=None)
        if terminal:bar['terminal_close_not_observed']=True
        output.append((day,bar,dict(original_row_index=row_index,trade_date=row[1],
                                   raw_volume_unit='hands',normalized_volume_unit='fund_units',scale='100')))
    return output,structure


def _actions(claim,metadata,raw):
    # Numeric amount tokens are parsed as lexical strings only after the marker.
    facts=wire.decode_opaque(raw)
    _require(facts.get('cash_amount_basis')=='announced_not_investor_verified'
             and len(facts.get('events',[]))==10,'Exact10 announced cash events required')
    dates=metadata['sessions'];bridge=metadata['action_bridge']['date_only_event_bridge']
    joins={e['event_id']:e for e in bridge};tax={e['event_id']:e for e in metadata['tax_evidence']['events']}
    _require(len(joins)==10,'Unique10 announcement joins required')
    actions=[];proof=[];seen=set()
    for source in facts['events']:
        identity=source['event_id'];asset=source['asset_id'];join=joins[identity]
        _require(identity not in seen and identity in tax and asset==ASSETS[0],'Cash action identity invalid')
        seen.add(identity)
        known=join['known_date_bridge']['date_label']
        record,ex,pay=(source[k] for k in ('record_date','ex_date','pay_date'))
        _require(all(d in dates for d in (known,record,ex,pay)) and known<=record<ex<=pay,'Explicit action dates/tax/unit required')
        _require(join['asset_id']==asset and all(join[k]==source[k] for k in ('record_date','ex_date','pay_date')),'Action bridge changed')
        _require(source['share_multiplier']=='1','Cash-only source rejects share conversion')
        cash=kernel._number(source['cash_per_unit']);_require(cash>=0,'Negative announced distribution')
        roles=join['retained_notice_roles_by_same_sha']
        _require(roles and all(r in claim.packet['inputs'] and claim.packet['inputs'][r]['sha256']==join['notice_sha256'] for r in roles),
                 'Exact original notice evidence required')
        known_role=join['known_date_bridge']['role'];_require(known_role in claim.packet['inputs'],'Known-date source role missing')
        actions.append(dict(event_id=identity,asset=asset,known_index=dates.index(known),record_index=dates.index(record),
                            ex_index=dates.index(ex),pay_index=dates.index(pay),share_multiplier='1',cash_per_share=str(cash)))
        proof.append(dict(event_id=identity,canonical_field='cash_per_unit',per_unit_conversion='none_already_per_share',
            known_date_label=known,known_date_source=claim.packet['inputs'][known_role],
            notice_refs=[claim.packet['inputs'][r] for r in roles],tax_mapping=tax[identity],
            historical_first_available_at=None,historical_PIT_verified=False,investor_net_credit_verified=False))
    _require(seen==set(joins)==set(tax),'Exact cash event/tax/known-date coverage required')
    return actions,proof


def _load_core(claim,*,test_values=False):
    _require(not claim.decoding_started,'Inputs parsed once only')
    claim.guard('before','source_metadata');metadata=_metadata(claim,test_values=test_values)
    bars={a:{} for a in ASSETS};wire_proof=[]
    for request,entry in zip(metadata['source_manifest']['requests'],metadata['source_index']['roles']):
        role,proof=_receipt(claim,request,entry,metadata['relocations'],test_values=test_values,batch_claim=metadata['source_outcome']['batch_claim'])
        raw=claim.read(role)  # failure here does not falsely consume a numeric parse
        if not claim.decoding_started:claim.begin_financial_decode()
        with localcontext(kernel.CONTEXT):rows,structure=_wire_rows(raw,request)
        _require(structure==entry['structure'],'Original structure changed')
        asset=ASSETS[0] if request['params']['ts_code']=='510300.SH' else ASSETS[1]
        for day,bar,rowproof in rows:
            _require(day not in bars[asset],'Duplicate asset date')
            bars[asset][day]=bar
        proof['row_mapping']=[dict(date=d,**p) for d,_,p in rows];wire_proof.append(proof)
    with localcontext(kernel.CONTEXT):actions,action_proof=_actions(claim,metadata,claim.read('actions'))
    dates=metadata['sessions']
    _require(all(set(bars[a])==set(dates) for a in ASSETS),'Complete two-asset calendar required')
    source=TEST_SOURCE if test_values else admission.SOURCE
    fixture=dict(artifact_type='admitted_constant_mix_fixture_v1',source_nature=source,
        constructed_from_market_data=not test_values,assets=list(ASSETS),dates=dates,
        bars={a:[bars[a][d] for d in dates] for a in ASSETS},
        event_indices=[dates.index(d) for d in metadata['method']['window']['quarter_sell_sessions']],
        terminal_index=len(dates)-1,actions=actions)
    provenance=dict(source_nature=source,test_injected_values=test_values,
        registration_sha256=claim.packet['registration_sha256'],source_wire_roles=wire_proof,actions=action_proof,
        input_refs=claim.packet['inputs'],source_index=claim.packet['inputs']['source_index'],
        actual_current_receipt_clocks_not_historical_availability=True,amount_tokens_not_converted=True,
        historical_PIT_verified=False,execution_constraints_verified=False,
        daily_bar_prior_open_availability='conditional_model_assumption',
        terminal_close_high_low_not_decoded=True,terminal_volume='after_session_capacity_audit_only',
        qualified=False,real_forward=0)
    context=kernel._ExecutionContext(ASSETS,source,True,test_values,claim.packet['registration_sha256'],
        kernel.digest(fixture),kernel.digest(provenance))
    data=LoadedInputs(fixture,provenance,context)
    claim.guard('after','source_numerical_validation')
    return data


def load_claimed_inputs(claim):
    _production_claim(claim)
    return _load_core(claim)


def _persist(root,path,value):
    # The shared writer uses its own canonical format (ASCII escaped, no final
    # newline). Anchor those exact intended bytes before any file is created.
    expected = _persisted_json_bytes(value)
    expected_sha = admission.digest(expected)
    admission.write_exclusive_json(path,value)
    _require(path.read_bytes() == expected, 'Persisted bytes differ from pre-write intent')
    return dict(path=path.resolve().relative_to(Path(root).resolve()).as_posix(),
                sha256=expected_sha, bytes=len(expected))


def _run_loaded(claim,data):
    frozen=loaded_digest(data);folder=admission.resolve_path(claim.root,admission.DIRECTORY)
    claim.guard('before','decoded_input_persist')
    _require(kernel.digest(data.fixture)==data.context.normalized_input_sha256
             and kernel.digest(data.provenance)==data.context.provenance_sha256,'Loaded financial snapshot changed')
    decoded=_persist(claim.root,folder/'decoded_input.json',dict(fixture=data.fixture,provenance=data.provenance))
    accounts,annual,summaries,events,matches,differences={},{},{},{},{},{}
    def guard(phase,identity):
        claim.guard(phase,identity)
        _require(loaded_digest(data)==frozen and kernel.digest(data.fixture)==data.context.normalized_input_sha256
                 and kernel.digest(data.provenance)==data.context.provenance_sha256,'Loaded financial snapshot changed')
    for minimum,slip in kernel.COSTS:
        cost=f'min{minimum}_slip{slip}';annual[cost]={};pair={}
        for policy in ('constant_mix','drift','cash'):
            identity=cost+'/'+policy;guard('before',identity);target=folder/'accounts'/identity
            admission.write_exclusive_json(target/'started.json',dict(identity=identity,at=datetime.now(timezone.utc).isoformat()))
            try:
                with localcontext(kernel.CONTEXT):prepared=kernel._prepare(data.fixture,context=data.context)
                result=kernel._run_prepared(prepared,policy,minimum,slip,context=data.context)
                artifact=_persist(claim.root,target/'complete.json',result)
            except BaseException as exc:
                admission.write_exclusive_json(target/'failed.json',dict(error_type=type(exc).__name__,account_complete=False,qualified=False));raise
            guard('after',identity)
            summaries[identity]=result['summary'];events[identity]=result['event_attempts']
            annual[cost][policy]=result['annual_contributions']
            accounts[identity]=dict(artifact=artifact,summary=result['summary'])
            if policy!='cash':pair[policy]={k:result[k] for k in ('initial_snapshot','attribution','summary')}
            admission.write_exclusive_json(folder/'account_index'/f'{len(accounts):02}.json',dict(identity=identity,**accounts[identity]))
        matches[cost]=pair['constant_mix']['initial_snapshot']==pair['drift']['initial_snapshot']
        _require(matches[cost],'Same actual initial basket required')
        with localcontext(kernel.CONTEXT):
            delta={k:Decimal(pair['constant_mix']['attribution'][k])-Decimal(pair['drift']['attribution'][k]) for k in pair['drift']['attribution']}
            diff=Decimal(pair['constant_mix']['summary']['terminal_book_NAV'])-Decimal(pair['drift']['summary']['terminal_book_NAV'])
            _require(sum(delta.values(),Decimal(0))==diff,'Policy attribution identity')
            differences[cost]=kernel._json(dict(components=delta,book_NAV_difference=diff,
                meaning='whole_policy_includes_dividend_reinvestment_and_risk_exposure'))
    guard('before','statistics')
    stats=kernel.paired_annual_bootstrap(annual,context=data.context)
    _require(stats.get('N')==10 and stats.get('replications')==5000 and len(stats['endpoint_keys'])==18,'Fixed complete statistics required')
    statistics=_persist(claim.root,folder/'statistics.json',stats)
    checks=kernel._matrix_checks(summaries,annual,events,stats,context=data.context)
    guard('after','statistics')
    result=dict(artifact_type=data.context.artifact('matrix'),source_nature=data.context.source_nature,
        evidence_class=data.context.source_nature,registration_sha256=claim.packet['registration_sha256'],
        test_injected_values=data.context.test_values,historical_returns_computed=data.context.returns_computed,
        qualified=False,real_forward=0,account_count=27,accounts=accounts,statistics=statistics,
        decoded_input_artifact=decoded,decoded_input_sha256=frozen,fixture_sha256=data.context.normalized_input_sha256,
        provenance_sha256=data.context.provenance_sha256,same_actual_initial_baskets=matches,
        policy_difference_attribution=differences,conditional_method_checks=checks,
        independently_verified=False,financial_verdict=data.context.verdict)
    guard('final','persisted_artifacts');admission._final_artifacts(claim.root,result)
    return result


def run_claimed_diagnostic(claim):
    _production_claim(claim)
    return _run_loaded(claim,load_claimed_inputs(claim))
