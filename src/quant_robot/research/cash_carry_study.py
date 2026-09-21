"""One frozen cash-carry study; claim before income-value decoding, including failures."""
from datetime import datetime, timezone
import json
from pathlib import PurePosixPath
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, runtime_environment, sha256, write_exclusive_json
from quant_robot.research.cash_carry_diagnostic import calculate

DIRECTORY='data/reports/positive_ev_20260921/cash_carry_diagnostic'
SOURCE_DIRECTORY='data/reports/positive_ev_20260921/cash_carry_annual_sources'
REGISTRATION=DIRECTORY+'/registration.json'
PROPOSAL='configs/cn_etf_cash_carry_annual_diagnostic_20260921.json'
PROPOSAL_SHA256='bff664923726a7b5bd909ff6d53607368dad7ffd280fd6b962d55c9b0cb62357'
SOURCE_PREFLIGHT=SOURCE_DIRECTORY+'/source_preflight_v2.json'
SOURCE_PREFLIGHT_SHA256='ecd0f663e76e2ce3f9c0734526fdbe5a8aeeeaf7336fff10585f0432157e5bb4'
DECISION='cash_carry_diagnostic_decision'
STAGE='single_primary_cash_carry_endpoint_cost_diagnostic'
MODE='single_cash_carry_diagnostic_only'
ROLES=({'proposal','source_preflight','source_review','calendar','calendar_manifest','source_ledger_v2','date_coverage'}
       |{f'{kind}_{year}' for kind in ('pcf','income') for year in range(2015,2025)}
       |{f'{kind}_{i}' for kind in ('evidence','claim','receipt') for i in range(54)})
IMPLEMENTATION=('src/quant_robot/research/cash_carry_study.py','src/quant_robot/research/cash_carry_diagnostic.py',
    'src/quant_robot/research/cash_carry_inputs.py','src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py','src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/data/cn_calendar_snapshot.py','src/quant_robot/data/cn_trading_calendar.py',
    'src/quant_robot/storage/atomic.py','scripts/run_cn_etf_cash_carry_diagnostic.py','scripts/bootstrap.py')


def build_registration(*,inputs,code_files,branch,environment):
    if set(inputs)!=ROLES or set(code_files)!=set(IMPLEMENTATION):raise ValueError('Exact study inputs and implementation required')
    for item in [*inputs.values(),*code_files.values()]:
        if set(item)!={'path','sha256'}:raise ValueError('Path and hash required')
        resolve_path('.',item['path'])
        if len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):raise ValueError('SHA256 required')
    if any(k!=v['path'] for k,v in code_files.items()):raise ValueError('Implementation alias rejected')
    for role,path,digest in [('proposal',PROPOSAL,PROPOSAL_SHA256),('source_preflight',SOURCE_PREFLIGHT,SOURCE_PREFLIGHT_SHA256)]:
        if inputs[role]!={'path':path,'sha256':digest}:raise ValueError('Frozen proposal and source preflight required')
    if not branch.startswith('codex/factor-') or not environment:raise ValueError('Task branch and runtime required')
    body=dict(schema_version=1,stage=STAGE,inputs=inputs,code_files=code_files,branch=branch,environment=environment,max_executions=1,
        conditional_endpoint_cost_only=True,net_account_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)
    return {**body,'registration_id':sha256(canonical(body))}


def validate_registration(packet):
    expected=build_registration(**{k:packet[k] for k in ('inputs','code_files','branch','environment')})
    if canonical(expected)!=canonical(packet):raise ValueError('Registration mutated')
    return packet


def admission(packet,raw):
    validate_registration(packet)
    return dict(status='authorized_once',registration_id=packet['registration_id'],registration_path=REGISTRATION,
        registration_sha256=sha256(raw),max_executions=1,execution_count=0,allowed_stage=STAGE,ledger_path=DIRECTORY+'/attempt_claim.json',
        conditional_endpoint_cost_only=True,general_factor_batch_allowed=False,net_account_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root,DIRECTORY+'/'+n).exists() for n in ('attempt_claim.json','result.json','outcome.json')):
        raise ValueError('cash-carry hypothesis consumed; no rerun')


def scope(task,family_config,family_schedule,*,root,branch):
    if task!='factor_batch' or family_config.get(DECISION,{}).get('status')!='authorized_once':return None
    if (set(family_schedule.get('blockers',[]))!={'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share')!=0 or family_schedule['summary'].get('active_primary_families')!=0):return None
    try:
        raw=resolve_path(root,REGISTRATION).read_bytes(); packet=validate_registration(json.loads(raw)); require_unused(root)
        if packet['branch']!=branch or family_config[DECISION]!=admission(packet,raw):return None
    except (OSError,ValueError,KeyError,TypeError):return None
    return {'mode':MODE,'scope':family_config[DECISION]}


def _source_closure(inputs,snapshots):
    """Bind aliases/receipts without decoding any income response."""
    source=json.loads(snapshots['source_preflight']);proposal=json.loads(snapshots['proposal'])
    if (source['proposal']!=inputs['proposal'] or source['responses_total']!=54
            or len(source['all_retained_responses'])!=54):raise ValueError('Frozen source inventory required')
    by_path={}
    for i,row in enumerate(source['all_retained_responses']):
        path=PurePosixPath(row['path']);binding=dict(path=row['path'],sha256=row['sha256'])
        if row['path'] in by_path or inputs[f'evidence_{i}']!=binding:raise ValueError('Source evidence alias differs')
        by_path[row['path']]=binding
        for kind in ('claim','receipt'):
            expected=dict(path=str(path.with_name(path.stem+'_'+kind+'.json')),sha256=row[kind+'_sha256'])
            if inputs[f'{kind}_{i}']!=expected:raise ValueError('Source collection alias differs')
        claim=json.loads(snapshots[f'claim_{i}']);receipt=json.loads(snapshots[f'receipt_{i}'])
        if (len(snapshots[f'evidence_{i}'])!=row['bytes'] or receipt.get('http_status')!=200
                or receipt.get('bytes')!=row['bytes'] or receipt.get('sha256')!=row['sha256']
                or not claim.get('url') or claim['url']!=receipt.get('url')):raise ValueError('Source receipt mismatch')
    for row in source['PCF_anchors']:
        if inputs['pcf_'+row['date'][:4]]!=by_path[row['source']]:raise ValueError('PCF source alias differs')
    for year in range(2015,2025):
        if inputs[f'income_{year}']!=by_path[SOURCE_DIRECTORY+f'/income_{year}.response']:
            raise ValueError('Income source alias differs')
    amendment=proposal['source_semantics_amendment']
    if (proposal['calendar']!=inputs['calendar'] or proposal['source_ledger_v2']!=inputs['source_ledger_v2']
            or amendment['date_review']!=inputs['date_coverage']
            or source['previous_source_ledger_v2_sha256']!=inputs['source_ledger_v2']['sha256']):
        raise ValueError('Source identities differ from frozen proposal')
    refs=[amendment['quota_schema'],amendment['active_quota_notice'],*amendment['income_formula_sources'],
          *proposal['source_scope']['reuse_PCF'].values()]
    if any(by_path.get(r['path'])!=r for r in refs):raise ValueError('Source protocol identity differs')
    review=json.loads(snapshots['source_review'])
    if (review.get('status')!='conditional_source_use_reviewed'
            or review.get('inputs')!={k:v for k,v in inputs.items() if k!='source_review'}
            or any(review.get(k) is not False for k in ('returns_calculated','factor_generated',
                'historical_availability_verified','net_account_allowed','income_values_inspected'))):
        raise ValueError('Exact opaque source-use self-review required')


def preflight(root,scheduler,gate_supplier):
    raw=resolve_path(root,REGISTRATION).read_bytes(); packet=validate_registration(json.loads(raw)); require_unused(root)
    if scheduler.get(DECISION)!=admission(packet,raw) or packet['environment']!=runtime_environment():raise ValueError('Exact unused admission/runtime required')
    snapshots={}
    for group in ('code_files','inputs'):
        for role,item in packet[group].items():
            content=resolve_path(root,item['path']).read_bytes()
            if sha256(content)!=item['sha256']:raise ValueError('Pinned file changed: '+role)
            if group=='inputs':snapshots[role]=content
    _source_closure(packet['inputs'],snapshots)
    gate=gate_supplier(); safety=gate['safety']; selected=gate['selected']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0<=age<=30 and gate['status']=='ready' and not gate['blockers'] and gate['mode']==MODE
            and gate['primary_market']=='CN_ETF' and safety.get('cash_carry_diagnostic_allowed') is True
            and safety.get('cash_carry_diagnostic_scope')==scheduler[DECISION] and safety.get('factor_batch_scope')=={}
            and selected['machine']=='office_desktop' and selected['task']=='factor_batch'
            and selected['branch']==packet['branch']==selected['current_branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact cash-carry PM gate required')
    return packet,snapshots,gate


def execute(root,scheduler,gate_supplier):
    packet,snapshots,gate=preflight(root,scheduler,gate_supplier)
    receipt=dict(registration_id=packet['registration_id'],claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_income_value_decode')
    write_exclusive_json(resolve_path(root,DIRECTORY+'/attempt_claim.json'),receipt)
    try:
        result={**calculate(snapshots),'registration_id':packet['registration_id'],'pm_gate':gate}
        write_exclusive_json(resolve_path(root,DIRECTORY+'/result.json'),result)
        terminal=dict(status='completed',result_sha256=sha256(canonical(result)))
    except BaseException as exc:
        terminal=dict(status='failed_consumed',error_type=type(exc).__name__,error_message=str(exc)[:500]);raise
    finally:
        write_exclusive_json(resolve_path(root,DIRECTORY+'/outcome.json'),{**receipt,**terminal,'finished_at':datetime.now(timezone.utc).isoformat()})
    return result
