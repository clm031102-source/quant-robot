"""Exact, one-use admission for the fixed conditional equity/gold account."""
from datetime import datetime, timezone
import json
from pathlib import Path

from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, runtime_environment, sha256, write_exclusive_json
from quant_robot.research.equity_gold_diagnostic import calculate

DIRECTORY = 'data/reports/positive_ev_20260921/equity_gold_account'
REGISTRATION = DIRECTORY+'/registration.json'
PROPOSAL = 'configs/cn_etf_equity_gold_account_execution_20260922.json'
PROPOSAL_SHA256 = 'fdf258a398e7d9ef9f067fab101bcd8fe180ab940da8f2d5914d3767994ba634'
DECISION = 'equity_gold_account_decision'
STAGE = 'single_equity_gold_conditional_historical_account'
MODE = 'single_equity_gold_account_only'
IMPLEMENTATION = (
    'src/quant_robot/research/equity_gold_study.py',
    'src/quant_robot/research/equity_gold_diagnostic.py',
    'src/quant_robot/paper/annual_allocation.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/storage/atomic.py',
    'scripts/run_cn_etf_equity_gold_account.py',
    'scripts/bootstrap.py',
)


def build_registration(*, inputs, code_files, branch, environment):
    required = {'proposal','input_review','input_binding','bars','sessions','actions','cycles',
                'config_account_method','config_execution_clarification','current_research_account'}
    if len(inputs)!=143 or not required<=set(inputs) or set(code_files)!=set(IMPLEMENTATION):
        raise ValueError('Exact143input roles and implementation required')
    for item in [*inputs.values(),*code_files.values()]:
        if set(item)!={'path','sha256'}:
            raise ValueError('Exact path and SHA256 required')
        resolve_path('.',item['path'])
        if len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):
            raise ValueError('SHA256 required')
    if any(key!=item['path'] for key,item in code_files.items()):
        raise ValueError('Implementation alias rejected')
    if len({item['path'] for item in inputs.values()})!=143:
        raise ValueError('Input paths must be distinct')
    if inputs['proposal']!={'path':PROPOSAL,'sha256':PROPOSAL_SHA256}:
        raise ValueError('Frozen execution proposal required')
    if not branch.startswith('codex/factor-') or not environment:
        raise ValueError('Task branch and runtime required')
    body = dict(schema_version=1,stage=STAGE,inputs=inputs,code_files=code_files,branch=branch,environment=environment,
        max_executions=1,conditional_historical_account_allowed=True,general_factor_batch_allowed=False,
        general_account_runs_allowed=False,forward_paper_allowed=False,promotion_allowed=False,
        final_holdout_allowed=False,live_boundary_allowed=False)
    return {**body,'registration_id':sha256(canonical(body))}


def validate_registration(packet):
    expected=build_registration(**{key:packet[key] for key in ('inputs','code_files','branch','environment')})
    if canonical(expected)!=canonical(packet):
        raise ValueError('Registration mutated')
    return packet


def admission(packet, raw):
    validate_registration(packet)
    return dict(status='authorized_once',registration_id=packet['registration_id'],registration_path=REGISTRATION,
        registration_sha256=sha256(raw),max_executions=1,execution_count=0,allowed_stage=STAGE,
        ledger_path=DIRECTORY+'/attempt_claim.json',conditional_historical_account_allowed=True,
        general_factor_batch_allowed=False,general_account_runs_allowed=False,forward_paper_allowed=False,
        promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root,DIRECTORY+'/'+name).exists() for name in ('attempt_claim.json','result.json','outcome.json')):
        raise ValueError('Equity/gold study consumed; no rerun')


def scope(task, family_config, family_schedule, *, root, branch):
    if task!='factor_batch' or family_config.get(DECISION,{}).get('status')!='authorized_once':
        return None
    summary=family_schedule['summary']
    if (set(family_schedule.get('blockers',[]))!={'insufficient_active_research_families'}
            or summary.get('primary_budget_share')!=0 or summary.get('active_primary_families')!=0):
        return None
    try:
        raw=resolve_path(root,REGISTRATION).read_bytes(); packet=validate_registration(json.loads(raw)); require_unused(root)
        if packet['branch']!=branch or family_config[DECISION]!=admission(packet,raw):
            return None
    except (OSError,ValueError,KeyError,TypeError):
        return None
    return {'mode':MODE,'scope':family_config[DECISION]}


def preflight(root, scheduler, gate_supplier):
    raw=resolve_path(root,REGISTRATION).read_bytes(); packet=validate_registration(json.loads(raw));require_unused(root)
    if scheduler.get(DECISION)!=admission(packet,raw) or packet['environment']!=runtime_environment():
        raise ValueError('Exact unused admission/runtime required')
    snapshots={}
    for group in ('code_files','inputs'):
        for role,item in packet[group].items():
            content=resolve_path(root,item['path']).read_bytes()
            if sha256(content)!=item['sha256']:
                raise ValueError('Pinned file changed: '+role)
            if group=='inputs':
                snapshots[role]=content
    proposal=json.loads(snapshots['proposal'])
    for key,role in [('source_review','input_review'),('input_binding','input_binding'),
                     ('financial_method','config_account_method'),('execution_clarification','config_execution_clarification')]:
        if proposal[key]!=packet['inputs'][role]:
            raise ValueError('Frozen source identity differs: '+role)
    review=json.loads(snapshots['input_review']); binding=json.loads(snapshots['input_binding'])
    original={}
    for role,item in review['inputs'].items():
        path=Path(item['path'])
        if path.is_absolute():
            path=path.relative_to(Path(binding['original_root']))
        original[role]={'path':path.as_posix(),'sha256':item['sha256']}
    actual={k:v for k,v in packet['inputs'].items() if k not in {'proposal','input_binding','input_review'}}
    if (review.get('status')!='conditional_account_inputs_prepared_no_outcomes'
            or review.get('market_outcomes_computed') is not False or review.get('account_executed') is not False
            or binding.get('source_review')!=packet['inputs']['input_review'] or original!=binding['inputs'] or actual!=original):
        raise ValueError('Exact source review and content-preserving relative binding required')
    gate=gate_supplier(); safety=gate['safety']; selected=gate['selected']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0<=age<=30 and gate['status']=='ready' and not gate['blockers'] and gate['mode']==MODE
            and gate['primary_market']=='CN_ETF' and safety.get('equity_gold_account_allowed') is True
            and safety.get('equity_gold_account_scope')==scheduler[DECISION] and safety.get('factor_batch_scope')=={}
            and selected['machine']=='office_desktop' and selected['task']=='factor_batch'
            and selected['branch']==packet['branch']==selected['current_branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact equity/gold PM gate required')
    return packet,snapshots,gate


def execute(root, scheduler, gate_supplier):
    packet,snapshots,gate=preflight(root,scheduler,gate_supplier)
    receipt=dict(registration_id=packet['registration_id'],claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_account_outcomes')
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
