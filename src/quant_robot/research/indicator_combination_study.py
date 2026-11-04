"""Hash-bound admission for the user's finite indicator-comparison experiment."""
from datetime import datetime, timezone
import json
from pathlib import Path

from quant_robot.research.indicator_combinations import calculate
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, runtime_environment, sha256, write_exclusive_json

DIRECTORY = 'data/reports/indicator_combinations_20261010'
REGISTRATION = DIRECTORY + '/registration.json'
PROPOSAL = 'configs/cn_etf_indicator_combinations_20261010.json'
DECISION = 'indicator_combination_account_decision'
MODE = 'single_indicator_combination_account_only'
STUDY = 'cn_etf_amount_pressure_macd_combinations_v1'
SOURCE_HASHES = {
    'bars':'69133a793dee21f6d9d2c354f577228b70abe37611f2703651b7b95c582ca839',
    'sessions':'38c510fbb2ec2bd0e0e90f4e849107ce25b5dd8cbd648122dfd564dd8ade2f0d',
    'actions':'5832902fef5ca52ac60cbbe534ef0b424cfedc945651868c8eebff0f041062be',
    'gold_annual_audit':'fe8a39a57433c6e7f2cf112520df810dff7d1eef06d6edb0e8127b6d9108f9f6',
    'gold_terminal_review':'59eb3a33fc5bdda2d26ef65f200cfac2dcc0e9799bed132b41c83a770d242663',
}
ROLES = {*SOURCE_HASHES, 'proposal', 'source_review', 'comparison_policy', 'strategy_cycles'}
IMPLEMENTATION = (
    'src/quant_robot/research/indicator_combination_study.py',
    'src/quant_robot/research/indicator_combinations.py',
    'src/quant_robot/paper/comparative_allocation.py',
    'src/quant_robot/paper/annual_allocation.py',
    'src/quant_robot/research/account_comparison_scope.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'scripts/run_cn_etf_indicator_combinations.py',
    'scripts/bootstrap.py',
)


def build_registration(*, inputs, code_files, branch, workspace, environment):
    if set(inputs) != ROLES or set(code_files) != set(IMPLEMENTATION):
        raise ValueError('Exact prospective inputs and implementation required')
    for pin in [*inputs.values(), *code_files.values()]:
        if set(pin) != {'path', 'sha256'}:
            raise ValueError('Exact path and hash pins required')
        resolve_path(workspace, pin['path'])
        if len(pin['sha256']) != 64 or any(c not in '0123456789abcdef' for c in pin['sha256']):
            raise ValueError('SHA256 required')
    if any(k != v['path'] for k,v in code_files.items()) or inputs['proposal']['path'] != PROPOSAL:
        raise ValueError('Implementation or proposal alias rejected')
    if any(inputs[role]['sha256'] != expected for role,expected in SOURCE_HASHES.items()):
        raise ValueError('Only the exact retained pre-2026 source snapshot is admitted')
    if branch != 'codex/factor-batch-indicator-combinations-20261010' or not environment:
        raise ValueError('Exact task branch and runtime required')
    body = dict(schema_version=1,study_id=STUDY,stage=MODE,inputs=inputs,code_files=code_files,
        branch=branch,workspace=str(Path(workspace).resolve()),environment=environment,
        max_executions=1,hypothesis_count=16,conditional_account_only=True,net_account_allowed=True,
        general_factor_batch_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)
    return {**body,'registration_id':sha256(canonical(body))}


def validate_registration(packet):
    expected = build_registration(**{k:packet[k] for k in ('inputs','code_files','branch','workspace','environment')})
    if canonical(expected) != canonical(packet):
        raise ValueError('Registration mutated')
    return packet


def admission(packet, raw):
    validate_registration(packet)
    return dict(status='authorized_once',registration_id=packet['registration_id'],registration_path=REGISTRATION,
        registration_sha256=sha256(raw),max_executions=1,execution_count=0,allowed_stage=MODE,
        ledger_path=DIRECTORY+'/attempt_claim.json',conditional_account_only=True,net_account_allowed=True,
        general_factor_batch_allowed=False,promotion_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False)


def require_unused(root):
    if any(resolve_path(root,DIRECTORY+'/'+n).exists() for n in ('attempt_claim.json','result.json','outcome.json')):
        raise ValueError('Indicator comparison already consumed; preserve its result')


def scope(task, family_config, family_schedule, *, root, branch):
    if task != 'factor_batch' or family_config.get(DECISION,{}).get('status') != 'authorized_once':
        return None
    if (set(family_schedule.get('blockers',[])) != {'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share') != 0
            or family_schedule['summary'].get('active_primary_families') != 0):
        return None
    try:
        raw = resolve_path(root,REGISTRATION).read_bytes()
        packet = validate_registration(json.loads(raw)); require_unused(root)
        if packet['workspace'] != str(Path(root).resolve()) or packet['branch'] != branch or family_config[DECISION] != admission(packet,raw):
            return None
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return dict(mode=MODE,scope=family_config[DECISION])


def preflight(root, scheduler, gate_supplier):
    raw = resolve_path(root,REGISTRATION).read_bytes()
    packet = validate_registration(json.loads(raw)); require_unused(root)
    if (packet['workspace'] != str(Path(root).resolve()) or packet['environment'] != runtime_environment()
            or scheduler.get(DECISION) != admission(packet,raw)):
        raise ValueError('Exact workspace, runtime and unused admission required')
    snapshots = {}
    for group in ('inputs','code_files'):
        for role,pin in packet[group].items():
            content = resolve_path(root,pin['path']).read_bytes()
            if sha256(content) != pin['sha256']:
                raise ValueError('Pinned file changed: '+role)
            if group == 'inputs': snapshots[role] = content
    proposal = json.loads(snapshots['proposal'])
    plan = json.loads(snapshots['strategy_cycles'])
    if (proposal['study_id'] != STUDY or proposal['max_executions'] != 1 or proposal['hypothesis_count'] != 16
            or proposal['new_data_requests'] != 0 or proposal['final_holdout_allowed'] is not False
            or plan['kind'] != 'prospective_decision_calendar_and_frozen_rules'
            or plan['proposal'] != packet['inputs']['proposal'] or plan['sessions'] != packet['inputs']['sessions']):
        raise ValueError('Exact prospective finite decision plan required')
    gate = gate_supplier(); selected = gate['selected']; safety = gate['safety']
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
    if not (0 <= age <= 30 and gate['status'] == 'ready' and not gate['blockers'] and gate['mode'] == MODE
            and gate['primary_market'] == 'CN_ETF' and safety.get('indicator_combination_account_allowed') is True
            and safety.get('indicator_combination_account_scope') == scheduler[DECISION]
            and gate['account_comparison']['status'] == 'passed_specification_only'
            and selected['machine'] == 'office_desktop' and selected['task'] == 'factor_batch'
            and selected['branch'] == packet['branch'] == selected['current_branch']
            and all(safety.get(k) is False for k in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed','portfolio_grid_allowed','walk_forward_allowed'))
            and safety['factor_batch_scope'] == {}):
        raise ValueError('Fresh restricted indicator-comparison PM gate required')
    return packet, snapshots, gate


def execute(root, scheduler, gate_supplier, *, progress=None):
    packet, snapshots, gate = preflight(root,scheduler,gate_supplier)
    receipt = dict(registration_id=packet['registration_id'],claimed_at=datetime.now(timezone.utc).isoformat(),
        status='claimed_before_indicator_or_new_account_calculation')
    write_exclusive_json(resolve_path(root,DIRECTORY+'/attempt_claim.json'),receipt)
    terminal = dict(status='failed_consumed')
    try:
        result = {**calculate(snapshots,progress=progress),'registration_id':packet['registration_id'],'pm_gate':gate}
        write_exclusive_json(resolve_path(root,DIRECTORY+'/result.json'),result)
        terminal = dict(status='completed',result_sha256=sha256(canonical(result)))
    except BaseException as exc:
        terminal['error_type'] = type(exc).__name__
        raise
    finally:
        write_exclusive_json(resolve_path(root,DIRECTORY+'/outcome.json'),{**receipt,**terminal,'finished_at':datetime.now(timezone.utc).isoformat()})
    return result
