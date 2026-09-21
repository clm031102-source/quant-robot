"""One accountable engineering repair of a consumed pre-PnL format failure."""
from datetime import datetime, timezone
import json
from quant_robot.research import cash_carry_study as original
from quant_robot.research.cash_carry_income_repair import calculate
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, runtime_environment, sha256, write_exclusive_json

DIRECTORY='data/reports/positive_ev_20260921/cash_carry_format_repair'
REGISTRATION=DIRECTORY+'/registration.json'
PROPOSAL='configs/cn_etf_cash_carry_format_repair_20260921.json'
PROPOSAL_SHA256='8cdd08708611ab4762bc7b1bbf7b1be039e44a87920befbe63d5f4d85e1ef2e8'
DECISION='cash_carry_format_repair_decision'
STAGE='single_primary_cash_carry_literal_format_repair'
MODE=original.MODE
ROLES=original.ROLES|{'prior_registration','prior_outcome','repair_proposal','failure_review'}
IMPLEMENTATION=(*original.IMPLEMENTATION,'src/quant_robot/research/cash_carry_repair_study.py',
    'src/quant_robot/research/cash_carry_income_repair.py','scripts/run_cn_etf_cash_carry_format_repair.py')


def build_registration(*,inputs,code_files,branch,environment):
    if set(inputs)!=ROLES or set(code_files)!=set(IMPLEMENTATION):raise ValueError('Exact repair inputs and code required')
    for item in [*inputs.values(),*code_files.values()]:
        if set(item)!={'path','sha256'}:raise ValueError('Path and hash required')
        resolve_path('.',item['path'])
        if len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):raise ValueError('SHA256 required')
    if any(k!=v['path'] for k,v in code_files.items()):raise ValueError('Implementation alias rejected')
    if inputs['repair_proposal']!={'path':PROPOSAL,'sha256':PROPOSAL_SHA256}:raise ValueError('Frozen format-only repair required')
    if not branch.startswith('codex/factor-') or not environment:raise ValueError('Task branch and runtime required')
    body=dict(schema_version=1,stage=STAGE,inputs=inputs,code_files=code_files,branch=branch,environment=environment,
        max_executions=1,same_economic_hypothesis=True,net_account_allowed=False,promotion_allowed=False,
        final_holdout_allowed=False,live_boundary_allowed=False)
    return {**body,'registration_id':sha256(canonical(body))}


def validate_registration(packet):
    expected=build_registration(**{k:packet[k] for k in ('inputs','code_files','branch','environment')})
    if canonical(expected)!=canonical(packet):raise ValueError('Repair registration mutated')
    return packet


def admission(packet,raw):
    validate_registration(packet)
    return dict(status='authorized_once',registration_id=packet['registration_id'],registration_path=REGISTRATION,
        registration_sha256=sha256(raw),max_executions=1,execution_count=0,allowed_stage=STAGE,
        ledger_path=DIRECTORY+'/attempt_claim.json',same_economic_hypothesis=True,conditional_endpoint_cost_only=True,
        general_factor_batch_allowed=False,net_account_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root,DIRECTORY+'/'+n).exists() for n in ('attempt_claim.json','result.json','outcome.json')):
        raise ValueError('cash-carry format repair consumed; no rerun')


def scope(task,family_config,family_schedule,*,root,branch):
    if task!='factor_batch' or family_config.get(DECISION,{}).get('status')!='authorized_once':return None
    if (set(family_schedule.get('blockers',[]))!={'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share')!=0 or family_schedule['summary'].get('active_primary_families')!=0):return None
    try:
        raw=resolve_path(root,REGISTRATION).read_bytes();packet=validate_registration(json.loads(raw));require_unused(root)
        if packet['branch']!=branch or family_config[DECISION]!=admission(packet,raw):return None
    except (OSError,ValueError,KeyError,TypeError):return None
    return {'mode':MODE,'scope':family_config[DECISION]}


def _repair_closure(root,packet,snapshots):
    proposal=json.loads(snapshots['repair_proposal']);prior=original.validate_registration(json.loads(snapshots['prior_registration']))
    for key,role in [('repair_of_registration','prior_registration'),('prior_outcome','prior_outcome'),
                     ('original_proposal','proposal'),('format_failure_review','failure_review')]:
        if proposal[key]!=packet['inputs'][role]:raise ValueError('Frozen repair evidence differs')
    if ({k:packet['inputs'][k] for k in original.ROLES}!=prior['inputs']
            or prior['branch']!=packet['branch']):raise ValueError('Original source bindings changed')
    if any(packet['code_files'][k]!=v for k,v in prior['code_files'].items()
           if k!='src/quant_robot/research/pm_startup_gate.py'):raise ValueError('Original financial implementation changed')
    outcome=json.loads(snapshots['prior_outcome'])
    if (outcome.get('status')!='failed_consumed' or outcome.get('error_type')!='ValueError'
            or outcome.get('error_message')!='Finite decimal required' or outcome.get('registration_id')!=prior['registration_id']
            or resolve_path(root,original.DIRECTORY+'/result.json').exists()
            or not resolve_path(root,original.DIRECTORY+'/attempt_claim.json').exists()):
        raise ValueError('Original failed format-only attempt required')
    original._source_closure(prior['inputs'],snapshots)


def preflight(root,scheduler,gate_supplier):
    raw=resolve_path(root,REGISTRATION).read_bytes();packet=validate_registration(json.loads(raw));require_unused(root)
    if scheduler.get(DECISION)!=admission(packet,raw) or packet['environment']!=runtime_environment():raise ValueError('Exact repair admission/runtime required')
    snapshots={}
    for group in ('inputs','code_files'):
        for role,item in packet[group].items():
            content=resolve_path(root,item['path']).read_bytes()
            if sha256(content)!=item['sha256']:raise ValueError('Pinned file changed: '+role)
            if group=='inputs':snapshots[role]=content
    _repair_closure(root,packet,snapshots)
    gate=gate_supplier();safety=gate['safety'];selected=gate['selected']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0<=age<=30 and gate['status']=='ready' and not gate['blockers'] and gate['mode']==MODE
            and gate['primary_market']=='CN_ETF' and safety.get('cash_carry_diagnostic_allowed') is True
            and safety.get('cash_carry_diagnostic_scope')==scheduler[DECISION] and safety.get('factor_batch_scope')=={}
            and selected['machine']=='office_desktop' and selected['task']=='factor_batch'
            and selected['branch']==packet['branch']==selected['current_branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact cash-carry repair PM gate required')
    return packet,snapshots,gate


def execute(root,scheduler,gate_supplier):
    packet,snapshots,gate=preflight(root,scheduler,gate_supplier)
    receipt=dict(registration_id=packet['registration_id'],claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_income_normalization')
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
