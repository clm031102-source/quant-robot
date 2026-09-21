"""One immutable labor-risk study; exclusive claim precedes actual data decode."""
from datetime import datetime, timezone
import json
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, runtime_environment, sha256, write_exclusive_json
from quant_robot.research.labor_risk_diagnostic import calculate

DIRECTORY='data/reports/positive_ev_20260921/labor_risk_diagnostic'
REGISTRATION=DIRECTORY+'/registration.json'
PROPOSAL='configs/cn_etf_labor_risk_diagnostic_20260921.json'
PROPOSAL_SHA256='c831fb890d50fb861ddaa429b3b1083e0044f3770213f1c8506b2e1ef9993208'
DECISION='labor_risk_diagnostic_decision'
STAGE='single_labor_risk_gross_diagnostic'
MODE='single_labor_risk_diagnostic_only'
ROLES={'proposal','original_proposal','source_scope','source_review','source_rows','history_manifest','extraction_review',
    'method_review','method_paper','price_review','actions','calendar','calendar_manifest',
    *[f'bars_{y}' for y in range(2020,2025)], *[f'release_{i}' for i in range(60)]}
IMPLEMENTATION=('src/quant_robot/research/labor_risk_study.py','src/quant_robot/research/labor_risk_diagnostic.py',
    'src/quant_robot/research/disclosed_flow_diagnostic.py','src/quant_robot/research/disclosed_flow_bounds.py',
    'src/quant_robot/data/etf_reported_holdings.py','src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py','src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/paper/corporate_actions.py','src/quant_robot/data/cn_calendar_snapshot.py',
    'src/quant_robot/data/cn_trading_calendar.py','src/quant_robot/storage/atomic.py',
    'scripts/run_cn_etf_labor_risk_diagnostic.py','scripts/bootstrap.py')


def build_registration(*,inputs,code_files,branch,environment):
    if set(inputs)!=ROLES or set(code_files)!=set(IMPLEMENTATION):raise ValueError('Exact study inputs and implementation required')
    for item in [*inputs.values(),*code_files.values()]:
        if set(item)!={'path','sha256'}:raise ValueError('Path and hash required')
        resolve_path('.',item['path'])
        if len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):raise ValueError('SHA256 required')
    if any(k!=v['path'] for k,v in code_files.items()):raise ValueError('Implementation alias rejected')
    if inputs['proposal']!={'path':PROPOSAL,'sha256':PROPOSAL_SHA256}:raise ValueError('Frozen positive-direction proposal required')
    if not branch.startswith('codex/factor-') or not environment:raise ValueError('Task branch and runtime required')
    body=dict(schema_version=1,stage=STAGE,inputs=inputs,code_files=code_files,branch=branch,environment=environment,max_executions=1,
        conditional_gross_only=True,net_account_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)
    return {**body,'registration_id':sha256(canonical(body))}


def validate_registration(packet):
    expected=build_registration(**{k:packet[k] for k in ('inputs','code_files','branch','environment')})
    if canonical(expected)!=canonical(packet):raise ValueError('Registration mutated')
    return packet


def admission(packet,raw):
    validate_registration(packet)
    return dict(status='authorized_once',registration_id=packet['registration_id'],registration_path=REGISTRATION,
        registration_sha256=sha256(raw),max_executions=1,execution_count=0,allowed_stage=STAGE,ledger_path=DIRECTORY+'/attempt_claim.json',
        conditional_gross_only=True,general_factor_batch_allowed=False,net_account_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root,DIRECTORY+'/'+n).exists() for n in ('attempt_claim.json','result.json','outcome.json')):
        raise ValueError('Labor-risk hypothesis consumed; no rerun')


def scope(task,family_config,family_schedule,*,root,branch):
    if task!='factor_batch' or family_config.get(DECISION,{}).get('status')!='authorized_once':return None
    if (set(family_schedule.get('blockers',[]))!={'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share')!=0 or family_schedule['summary'].get('active_primary_families')!=0):return None
    try:
        raw=resolve_path(root,REGISTRATION).read_bytes(); packet=validate_registration(json.loads(raw)); require_unused(root)
        if packet['branch']!=branch or family_config[DECISION]!=admission(packet,raw):return None
    except (OSError,ValueError,KeyError,TypeError):return None
    return {'mode':MODE,'scope':family_config[DECISION]}


def preflight(root,scheduler,gate_supplier):
    raw=resolve_path(root,REGISTRATION).read_bytes(); packet=validate_registration(json.loads(raw)); require_unused(root)
    if scheduler.get(DECISION)!=admission(packet,raw) or packet['environment']!=runtime_environment():raise ValueError('Exact unused admission/runtime required')
    snapshots={}
    for group in ('code_files','inputs'):
        for role,item in packet[group].items():
            content=resolve_path(root,item['path']).read_bytes()
            if sha256(content)!=item['sha256']:raise ValueError('Pinned file changed: '+role)
            if group=='inputs':snapshots[role]=content
    review=json.loads(snapshots['source_review'])
    if (review.get('status')!='conditional_source_use_reviewed'
            or review.get('inputs')!={k:v for k,v in packet['inputs'].items() if k!='source_review'}
            or any(review.get(k) is not False for k in ('prices_decoded','factor_generated','historical_availability_verified','net_account_allowed'))):
        raise ValueError('Exact source-use self-review required')
    sources=json.loads(snapshots['source_rows'])
    if (sources.get('manifest_sha256')!=sha256(snapshots['history_manifest'])
            or sources.get('extraction_sha256')!=sha256(snapshots['extraction_review'])):raise ValueError('Source corpus scope differs')
    gate=gate_supplier(); safety=gate['safety']; selected=gate['selected']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0<=age<=30 and gate['status']=='ready' and not gate['blockers'] and gate['mode']==MODE
            and gate['primary_market']=='CN_ETF' and safety.get('labor_risk_diagnostic_allowed') is True
            and safety.get('labor_risk_diagnostic_scope')==scheduler[DECISION] and safety.get('factor_batch_scope')=={}
            and selected['machine']=='office_desktop' and selected['task']=='factor_batch'
            and selected['branch']==packet['branch']==selected['current_branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact labor-risk PM gate required')
    return packet,snapshots,gate


def execute(root,scheduler,gate_supplier):
    packet,snapshots,gate=preflight(root,scheduler,gate_supplier)
    receipt=dict(registration_id=packet['registration_id'],claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_factor_and_price_decode')
    write_exclusive_json(resolve_path(root,DIRECTORY+'/attempt_claim.json'),receipt)
    try:
        result={**calculate(snapshots),'registration_id':packet['registration_id'],'pm_gate':gate}
        write_exclusive_json(resolve_path(root,DIRECTORY+'/result.json'),result)
        terminal=dict(status='completed',result_sha256=sha256(canonical(result)))
    except BaseException as exc:
        terminal=dict(status='failed_consumed',error_type=type(exc).__name__);raise
    finally:
        write_exclusive_json(resolve_path(root,DIRECTORY+'/outcome.json'),{**receipt,**terminal,'finished_at':datetime.now(timezone.utc).isoformat()})
    return result
