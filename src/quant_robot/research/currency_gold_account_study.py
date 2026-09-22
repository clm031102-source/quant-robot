"""One immutable Currency-gold-account study; exclusive claim precedes real signal/outcome computation."""
from datetime import datetime, timezone
import json
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, runtime_environment, sha256, write_exclusive_json
from quant_robot.research.currency_gold_account import calculate

DIRECTORY='data/reports/positive_ev_20260922/currency_gold_account'
REGISTRATION=DIRECTORY+'/registration.json'
REVIEW='configs/cn_etf_currency_gold_account_review_20260922.json'
REVIEW_SHA256='649ee471ace52823fc5e3a043f3e458288e52b4b978168c523d03554c8f3519f'
DECISION='currency_gold_account_decision'
STAGE='single_currency_gold_net_account'
MODE='single_currency_gold_account_only'
ROLES = {'actions', 'bars', 'cadence_result', 'gold_annual_audit', 'gold_terminal_review', 'gross_claim', 'gross_outcome', 'gross_registration', 'gross_result', 'gross_verification', 'proposal', 'sessions', 'source_review', *[f'gross_authority_{i}' for i in range(348)]}
IMPLEMENTATION = (
    'src/quant_robot/research/currency_gold_account_study.py',
    'src/quant_robot/research/currency_gold_account.py',
    'src/quant_robot/paper/annual_allocation.py',
    'src/quant_robot/research/equity_gold_diagnostic.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/storage/atomic.py',
    'scripts/run_cn_etf_currency_gold_account.py',
    'scripts/bootstrap.py',
)


def build_registration(*,inputs,code_files,branch,environment):
    if set(inputs)!=ROLES or set(code_files)!=set(IMPLEMENTATION):raise ValueError('Exact study inputs and implementation required')
    for item in [*inputs.values(),*code_files.values()]:
        if set(item)!={'path','sha256'}:raise ValueError('Path and hash required')
        resolve_path('.',item['path'])
        if len(item['sha256'])!=64 or any(c not in '0123456789abcdef' for c in item['sha256']):raise ValueError('SHA256 required')
    if any(k!=v['path'] for k,v in code_files.items()):raise ValueError('Implementation alias rejected')
    if inputs['source_review']!={'path':REVIEW,'sha256':REVIEW_SHA256}:raise ValueError('Frozen currency-gold source-use review required')
    if not branch.startswith('codex/factor-') or not environment:raise ValueError('Task branch and runtime required')
    body=dict(schema_version=1,stage=STAGE,inputs=inputs,code_files=code_files,branch=branch,environment=environment,max_executions=1,
        conditional_account_only=True,net_account_allowed=True,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)
    return {**body,'registration_id':sha256(canonical(body))}


def validate_registration(packet):
    expected=build_registration(**{k:packet[k] for k in ('inputs','code_files','branch','environment')})
    if canonical(expected)!=canonical(packet):raise ValueError('Registration mutated')
    return packet


def admission(packet,raw):
    validate_registration(packet)
    return dict(status='authorized_once',registration_id=packet['registration_id'],registration_path=REGISTRATION,
        registration_sha256=sha256(raw),max_executions=1,execution_count=0,allowed_stage=STAGE,ledger_path=DIRECTORY+'/attempt_claim.json',
        conditional_account_only=True,general_factor_batch_allowed=False,net_account_allowed=True,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root,DIRECTORY+'/'+n).exists() for n in ('attempt_claim.json','result.json','outcome.json')):
        raise ValueError('Currency-gold-account hypothesis consumed; no rerun')


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
    if (review['fixed']!={k:v for k,v in packet['inputs'].items() if k!='source_review'}
            or review['account_returns_calculated'] is not False):
        raise ValueError('Exact pre-account source review required')
    proof=json.loads(snapshots['gross_verification'])
    gross=json.loads(snapshots['gross_result'])
    outcome=json.loads(snapshots['gross_outcome'])
    if (proof['status']!='passed' or proof['result_sha256']!=sha256(snapshots['gross_result'])
            or proof['registration_sha256']!=sha256(snapshots['gross_registration'])
            or outcome['status']!='completed' or outcome['result_sha256']!=proof['result_sha256']
            or gross['diagnostic']['gross_screen_passed'] is not True or gross['net_account_run'] is not False
            or len(proof['pins'])!=348):
        raise ValueError('Completed and reconciled gross pass required')
    for i,original in enumerate(proof['pins']):
        if packet['inputs'][f'gross_authority_{i}']['sha256']!=original['sha256']:
            raise ValueError('Gross authority changed')
    old=json.loads(snapshots['gross_registration'])
    for role in ('bars','sessions','actions','gold_annual_audit','gold_terminal_review'):
        if packet['inputs'][role]!=old['inputs']['market_'+role]:
            raise ValueError('Retained financial input identity changed')
    if packet['inputs']['cadence_result']!=old['inputs']['cadence_result']:
        raise ValueError('Frozen source states changed')
    gate=gate_supplier(); safety=gate['safety']; selected=gate['selected']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0<=age<=30 and gate['status']=='ready' and not gate['blockers'] and gate['mode']==MODE
            and gate['primary_market']=='CN_ETF' and safety.get('currency_gold_account_allowed') is True
            and safety.get('currency_gold_account_scope')==scheduler[DECISION] and safety.get('factor_batch_scope')=={}
            and selected['machine']=='office_desktop' and selected['task']=='factor_batch'
            and selected['branch']==packet['branch']==selected['current_branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact Currency-gold-account PM gate required')
    return packet,snapshots,gate


def execute(root,scheduler,gate_supplier):
    packet,snapshots,gate=preflight(root,scheduler,gate_supplier)
    receipt=dict(registration_id=packet['registration_id'],claimed_at=datetime.now(timezone.utc).isoformat(),status='claimed_before_candidate_net_account_calculation')
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
