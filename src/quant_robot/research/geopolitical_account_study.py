"""One-use admission for the predeclared GPRT gold full-account test."""
from datetime import datetime, timezone
import json

from quant_robot.data.sources.geopolitical_account_sources import IMPLEMENTATION as SOURCE_CODE
from quant_robot.research.geopolitical_account import STUDY, calculate
from quant_robot.research.monthly_diagnostic_registration import (
    canonical, resolve_path, runtime_environment, sha256, write_exclusive_json,
)

DIRECTORY = 'data/reports/geopolitical_account_20261104/account'
REGISTRATION = DIRECTORY+'/registration.json'
DECISION = 'geopolitical_account_decision'
STAGE = 'single_geopolitical_conditional_full_account'
MODE = 'single_geopolitical_account_only'
BRANCH = 'codex/factor-batch-geopolitical-account-20261104'
PREPARED = 'data/reports/geopolitical_account_20261104'
EXTRA = {'input_review','independent_source_review','execution_proposal','executed_source_pm_gate',
         'comparison_policy','sessions','strategy_cycles'}
IMPLEMENTATION = (*SOURCE_CODE,
    'src/quant_robot/research/account_comparison_scope.py',
    'src/quant_robot/research/geopolitical_account_study.py',
    'scripts/prepare_cn_etf_geopolitical_account.py',
    'scripts/run_cn_etf_geopolitical_account.py')
FROZEN = {
    'execution_proposal': dict(path='configs/cn_etf_geopolitical_account_execution_20261104.json',sha256='3710e794ccbb33bb4ccf0efe3d04f0199d86e47aeaf804d293c9095a092c6d43'),
    'input_review': dict(path=PREPARED+'/input_review.json',sha256='78d0f3278018e09bf4c4a4bc9e00c3ad8aed07f787505a5557e51232035ced64'),
    'review_proposal': dict(path='configs/cn_etf_geopolitical_gold_proposal_20260922.json',sha256='58a5f1e9ca392eadf6f2e90468d6100257a9e994e7b278eef5065d8f1d66dae4'),
    'review_method': dict(path='configs/cn_etf_geopolitical_account_method_20261104.json',sha256='1717534363a6f1c3406b001b2e829e7cf6eb98bb625d3f345321f22ea10924a6'),
    'review_account_plan': dict(path=PREPARED+'/account_plan.json',sha256='0db22cce014a8b0d95c1655246738bcc69fb4d8344113b344fcf023469d04e42'),
    'review_cadence_result': dict(path='data/reports/geopolitical_cadence_20261104/result.json',sha256='94ea9f95a5522b9d40d1d51aa57dd24f2e9101fb51bad4b1b9c428088a2a081b'),
}
EXTRA_PATHS = dict(input_review=PREPARED+'/input_review.json',
    independent_source_review=PREPARED+'/source_result_independent_review.md',
    execution_proposal='configs/cn_etf_geopolitical_account_execution_20261104.json',
    executed_source_pm_gate=PREPARED+'/source/executed_code/pm_startup_gate.py',
    comparison_policy=PREPARED+'/inputs/comparison_policy.json',
    sessions=PREPARED+'/inputs/sessions.json',strategy_cycles=PREPARED+'/inputs/strategy_cycles.json')


def build_registration(*, inputs, code_files, branch, environment):
    if (len(inputs) != 67 or not EXTRA <= set(inputs)
            or any(not k.startswith('review_') for k in set(inputs)-EXTRA)
            or set(code_files) != set(IMPLEMENTATION)):
        raise ValueError('Exact 67 input and 16 implementation roles required')
    for pin in [*inputs.values(),*code_files.values()]:
        if set(pin) != {'path','sha256'}:
            raise ValueError('Exact path and digest required')
        resolve_path('.',pin['path']); digest=pin['sha256']
        if not isinstance(digest,str) or len(digest)!=64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('Lowercase SHA256 required')
    if (any(inputs.get(role)!=pin for role,pin in FROZEN.items())
            or any(inputs[k]['path']!=v for k,v in EXTRA_PATHS.items())
            or any(k!=v['path'] for k,v in code_files.items())):
        raise ValueError('Original fixed method, inputs and implementation paths required')
    if branch != BRANCH or not environment:
        raise ValueError('Exact account branch and environment required')
    body=dict(schema_version=1,stage=STAGE,study_id=STUDY,inputs=inputs,code_files=code_files,branch=branch,
        environment=environment,max_executions=1,conditional_historical_account_allowed=True,
        general_factor_batch_allowed=False,general_account_runs_allowed=False,
        promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)
    return dict(body,registration_id=sha256(canonical(body)))


def validate_registration(packet):
    expected=build_registration(**{k:packet[k] for k in ('inputs','code_files','branch','environment')})
    if canonical(expected)!=canonical(packet):
        raise ValueError('Account registration changed')
    return packet


def admission(packet,raw):
    validate_registration(packet)
    return dict(status='authorized_once',registration_id=packet['registration_id'],
        registration_path=REGISTRATION,registration_sha256=sha256(raw),max_executions=1,
        execution_count=0,allowed_stage=STAGE,ledger_path=DIRECTORY+'/attempt_claim.json',
        conditional_historical_account_allowed=True,general_factor_batch_allowed=False,
        general_account_runs_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root,DIRECTORY+'/'+name).exists() for name in ('attempt_claim.json','result.json','outcome.json')):
        raise ValueError('Geopolitical account consumed; no rerun')


def scope(task,family_config,family_schedule,*,root,branch):
    if task!='factor_batch' or family_config.get(DECISION,{}).get('status')!='authorized_once':
        return None
    if (set(family_schedule.get('blockers',[]))!={'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share')!=0
            or family_schedule['summary'].get('active_primary_families')!=0):
        return None
    try:
        raw=resolve_path(root,REGISTRATION).read_bytes();packet=validate_registration(json.loads(raw));require_unused(root)
        if packet['branch']!=branch or family_config[DECISION]!=admission(packet,raw):
            return None
    except (OSError,ValueError,KeyError,TypeError):
        return None
    return dict(mode=MODE,scope=family_config[DECISION])


def source_chain(packet,snapshots):
    review=json.loads(snapshots['input_review'])
    original={k[7:]:v for k,v in packet['inputs'].items() if k.startswith('review_')}
    if (original!=review['inputs'] or review.get('status')!='conditional_account_inputs_prepared_no_outcomes'
            or review.get('market_outcomes_computed') is not False or review.get('account_executed') is not False
            or review.get('bar_rows')!=944 or review.get('calendar_sessions')!=944):
        raise ValueError('Exact complete reviewed source input set required')
    proposal=json.loads(snapshots['execution_proposal'])
    for key,role in [('input_review','input_review'),('method','review_method'),
                     ('independent_source_review','independent_source_review')]:
        if proposal[key]!=packet['inputs'][role]:
            raise ValueError('Execution proposal source binding differs')
    if (proposal.get('stage')!=STAGE or proposal.get('max_executions')!=1
            or proposal.get('account_count')!=27 or proposal.get('method_changes_allowed') is not False
            or any(proposal.get(k) is not False for k in ('paper_promotion_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fixed single historical execution proposal required')
    source_scope=json.loads(snapshots['review_scope.json'])
    for path,pin in source_scope['code_files'].items():
        actual=packet['inputs']['executed_source_pm_gate'] if path=='src/quant_robot/research/pm_startup_gate.py' else packet['code_files'][path]
        if actual['sha256']!=pin['sha256']:
            raise ValueError('Prepared economic/source implementation changed: '+path)
    result=json.loads(snapshots['review_source_outcome.json'])
    if (result.get('status')!='raw_sources_retained_review_pending' or result.get('requests')!=6
            or result.get('market_outcomes_computed') is not False
            or result['scope_sha256']!=packet['inputs']['review_scope.json']['sha256']):
        raise ValueError('Original consumed six-request source result required')
    method=json.loads(snapshots['review_method'])
    if method['account_plan']!=packet['inputs']['review_account_plan']:
        raise ValueError('Original pre-price account plan required')
    plan=json.loads(snapshots['review_account_plan'])
    if (json.loads(snapshots['sessions'])!=plan['sessions']
            or json.loads(snapshots['strategy_cycles'])!=plan['strategy_cycles']
            or json.loads(snapshots['comparison_policy'])!=dict(plan['comparison_policy'],strategy_cycles=packet['inputs']['strategy_cycles'])):
        raise ValueError('Extracted controls, sessions and cycles changed the pre-price plan')


def preflight(root,scheduler,gate_supplier):
    raw=resolve_path(root,REGISTRATION).read_bytes();packet=validate_registration(json.loads(raw));require_unused(root)
    if scheduler.get(DECISION)!=admission(packet,raw) or packet['environment']!=runtime_environment():
        raise ValueError('Exact unused admission and runtime required')
    snapshots={}
    for group in ('code_files','inputs'):
        for role,pin in packet[group].items():
            content=resolve_path(root,pin['path']).read_bytes()
            if sha256(content)!=pin['sha256']:
                raise ValueError('Pinned file changed: '+role)
            if group=='inputs':snapshots[role]=content
    source_chain(packet,snapshots)
    gate=gate_supplier();safety=gate['safety'];selected=gate['selected']
    age=(datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0<=age<=30 and gate['status']=='ready' and not gate['blockers'] and gate['mode']==MODE
            and gate['primary_market']=='CN_ETF' and safety.get('geopolitical_account_allowed') is True
            and safety.get('geopolitical_account_scope')==scheduler[DECISION] and safety.get('factor_batch_scope')=={}
            and selected['machine']=='office_desktop' and selected['task']=='factor_batch'
            and selected['branch']==selected['current_branch']==packet['branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'))):
        raise ValueError('Fresh exact geopolitical-account PM gate required')
    return packet,snapshots,gate


def execute(root,scheduler,gate_supplier):
    packet,snapshots,gate=preflight(root,scheduler,gate_supplier)
    receipt=dict(registration_id=packet['registration_id'],claimed_at=datetime.now(timezone.utc).isoformat(),
                 status='claimed_before_account_outcomes')
    write_exclusive_json(resolve_path(root,DIRECTORY+'/attempt_claim.json'),receipt)
    terminal=dict(status='failed_consumed')
    try:
        result=calculate(bars=json.loads(snapshots['review_bars']),actions=json.loads(snapshots['review_actions'])['events'],
            plan=json.loads(snapshots['review_account_plan']),cadence_rows=json.loads(snapshots['review_cadence_result'])['rows'])
        result.update(registration_id=packet['registration_id'],pm_gate=gate,
            source_limitations=json.loads(snapshots['input_review']).get('limitations',[]),
            source_input_review=packet['inputs']['input_review'],
            actual_broker_fees_certified=False)
        write_exclusive_json(resolve_path(root,DIRECTORY+'/result.json'),result)
        terminal=dict(status='completed',result_sha256=sha256(canonical(result)))
    except BaseException as exc:
        terminal['error_type']=type(exc).__name__
        raise
    finally:
        write_exclusive_json(resolve_path(root,DIRECTORY+'/outcome.json'),dict(receipt,**terminal,
            finished_at=datetime.now(timezone.utc).isoformat()))
    return result
