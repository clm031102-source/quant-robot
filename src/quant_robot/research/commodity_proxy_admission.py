"""Separate one-use campaign admission; legacy research budgets stay closed."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path

from quant_robot.research.monthly_diagnostic_registration import (
    canonical, resolve_path, runtime_environment, write_exclusive_json,
)


DIRECTORY = 'data/reports/campaign_72h_20261106/commodity_accounts'
REGISTRATION = DIRECTORY+'/registration.json'
REVIEW = DIRECTORY+'/independent_review.json'
ADMISSION = 'configs/cn_etf_commodity_proxy_admission_20261106.json'
CAMPAIGN = 'configs/research_campaign_72h_20261106.json'
BRANCH = 'codex/factor-review-72h-campaign-20261106'
MODE = 'single_campaign_commodity_proxy_36_account_only'
IMPLEMENTATION = (
    'src/quant_robot/research/commodity_proxy_admission.py',
    'src/quant_robot/research/commodity_proxy_accounts.py',
    'src/quant_robot/research/commodity_curve_proxy.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/research/account_comparison_scope.py',
    'src/quant_robot/paper/comparative_allocation.py',
    'src/quant_robot/paper/annual_allocation.py',
    'src/quant_robot/paper/daily_entry_policy.py',
    'src/quant_robot/paper/daily_recovery.py',
    'src/quant_robot/paper/position_buffer.py',
    'scripts/run_commodity_proxy_accounts.py', 'scripts/bootstrap.py',
    'scripts/run_quant_pm_startup_gate.py', 'scripts/start_task_context.py',
)
INPUT_ROLES = {'calendar', 'lifecycle', 'settlement_structure', 'settlement_scope',
    'etf_authority', 'actions', 'actions_review', 'method', 'campaign', 'authorization',
    'pm_policy', 'workstations', 'family_scheduler',
    'action_source_scope', 'action_source_batch',
    *('action_report_'+str(year) for year in range(2020, 2025)),
    *('bars_'+str(year) for year in range(2020, 2025)),
    *('settlement_'+str(number).zfill(2) for number in range(1, 39))}
POLICY = dict(hypotheses=1, strategy_and_control_accounts=36, cash_benchmarks=2,
    max_executions=1, ordinary_factor_budget_changed=False, conditional_only=True,
    qualification_granted=False, final_holdout_allowed=False, live_boundary_allowed=False)


def _json(raw, *, decimal_numbers=False):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate registration/evidence JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Nonfinite JSON token')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid,
                      parse_float=Decimal if decimal_numbers else float)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bound(root, reference, *, return_bytes=True):
    if (not isinstance(reference, dict) or set(reference) != {'path', 'sha256'}
            or not isinstance(reference['sha256'], str) or len(reference['sha256']) != 64
            or any(ch not in '0123456789abcdef' for ch in reference['sha256'])):
        raise ValueError('Exact relative path and SHA256 reference required')
    path = resolve_path(root, reference['path'])
    if path.is_symlink():
        raise ValueError('Symlink evidence forbidden')
    raw = path.read_bytes()
    if digest(raw) != reference['sha256']:
        raise ValueError('Frozen file changed: '+reference['path'])
    return raw if return_bytes else None


def validate_registration(packet, root):
    if (not isinstance(packet, dict) or set(packet) != {'artifact_type', 'branch', 'inputs',
            'implementation', 'environment', 'policy', 'registration_sha256'}
            or packet['artifact_type'] != 'commodity_proxy_account_registration_v1'
            or packet['branch'] != BRANCH or canonical(packet['policy']) != canonical(POLICY)
            or set(packet['inputs']) != INPUT_ROLES or set(packet['implementation']) != set(IMPLEMENTATION)):
        raise ValueError('Exact finite commodity registration required')
    body = {key: value for key, value in packet.items() if key != 'registration_sha256'}
    if packet['registration_sha256'] != digest(canonical(body)):
        raise ValueError('Registration mutated')
    if packet['environment'] != runtime_environment():
        raise ValueError('Frozen runtime environment changed')
    for role, reference in packet['inputs'].items():
        fixed = {'campaign': CAMPAIGN, 'pm_policy': 'configs/quant_pm_startup_gate_cn_etf.json',
                 'workstations': 'configs/workstations.json',
                 'family_scheduler': 'configs/research_family_scheduler_cn_etf.json'}
        if role in fixed and reference['path'] != fixed[role]:
            raise ValueError('Exact campaign and PM protocol files required')
        if role.startswith('bars_') and '/year='+role[-4:]+'/' not in reference['path']:
            raise ValueError('Only exact 2020-2024 ETF partitions allowed')
        read_bound(root, reference, return_bytes=False)
    for name, reference in packet['implementation'].items():
        if name != reference['path']:
            raise ValueError('Implementation alias forbidden')
        read_bound(root, reference, return_bytes=False)
    campaign = _json(read_bound(root, packet['inputs']['campaign']))
    now = datetime.now(timezone.utc)
    if (campaign.get('campaign_id') != 'quant_manager_72h_20261106'
            or campaign.get('status') != 'active' or campaign.get('task_branch') != BRANCH
            or campaign.get('started_at') != '2026-11-06T16:21:39Z'
            or campaign.get('delivery_deadline') != '2026-11-09T16:21:39Z'
            or not datetime.fromisoformat(campaign['started_at'].replace('Z', '+00:00')) <= now
                < datetime.fromisoformat(campaign['delivery_deadline'].replace('Z', '+00:00'))
            or campaign.get('finite_preregistered_studies_required') is not True
            or campaign.get('old_consumed_scopes_remain_closed') is not True
            or campaign.get('holdout_unsealing_authorized') is not False
            or campaign.get('live_boundary_allowed') is not False):
        raise ValueError('Active exact campaign with retained closed boundaries required')
    return packet


def require_unused(root):
    folder = resolve_path(root, DIRECTORY)
    if any((folder/name).exists() for name in ('attempt_claim.json', 'result.json', 'outcome.json', 'accounts')):
        raise ValueError('Financial batch already reserved or consumed; no resume')


def admitted_packet(root, *, unused=True):
    admission = _json(resolve_path(root, ADMISSION).read_bytes())
    if (set(admission) != {'artifact_type', 'status', 'registration', 'review', 'policy'}
            or admission['artifact_type'] != 'commodity_proxy_finite_admission_v1'
            or admission['status'] != 'authorized_once' or canonical(admission['policy']) != canonical(POLICY)
            or admission['registration']['path'] != REGISTRATION or admission['review']['path'] != REVIEW):
        raise ValueError('Exact separately reviewed finite admission required')
    packet = validate_registration(_json(read_bound(root, admission['registration'])), root)
    review = _json(read_bound(root, admission['review']))
    if (review.get('status') != 'accepted_for_one_conditional_batch'
            or review.get('registration_sha256') != packet['registration_sha256']
            or review.get('reviewer') != 'quant_manager_72h'
            or review.get('qualified') is not False or review.get('real_forward_days_added') != 0):
        raise ValueError('Independent review of this exact registration required')
    if unused:
        require_unused(root)
    return packet, admission


def scope(task, family_config, family_schedule, *, root, branch):
    if task != 'factor_review' or branch != BRANCH or not resolve_path(root, ADMISSION).exists():
        return None
    if (set(family_schedule.get('blockers', [])) != {'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share') != 0
            or family_schedule['summary'].get('active_primary_families') != 0):
        return None
    try:
        packet, admission = admitted_packet(root)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return dict(mode=MODE, scope=dict(registration_sha256=packet['registration_sha256'],
        admission_file_sha256=digest(resolve_path(root, ADMISSION).read_bytes()), policy=POLICY))


def review_comparison(root, scope):
    packet, _ = admitted_packet(root)
    if (scope.get('registration_sha256') != packet['registration_sha256']
            or scope.get('admission_file_sha256') != digest(resolve_path(root, ADMISSION).read_bytes())
            or canonical(scope.get('policy')) != canonical(POLICY)):
        raise ValueError('Comparison must belong to exact admitted account batch')
    return dict(status='passed_specification_only', blockers=[],
        method=packet['inputs']['method'], implementation=packet['implementation'],
        strategy_and_matched_holding_accounts=36, cash_controls=2,
        no_price_decoding_performed=True, net_positive_EV_verified=False, source_quality_verified=False)


def execute(root, *, expected_registration_sha256, gate_supplier, load_inputs, calculate):
    packet, admission = admitted_packet(root)
    if expected_registration_sha256 != packet['registration_sha256']:
        raise ValueError('Exact registration digest required')
    gate = gate_supplier()
    selected, safety = gate['selected'], gate['safety']
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'].replace('Z', '+00:00'))).total_seconds()
    if (not 0 <= age <= 120 or gate['status'] != 'ready' or gate['blockers']
            or gate['mode'] != MODE or gate['primary_market'] != 'CN_ETF'
            or selected != dict(machine='office_desktop', task='factor_review', branch=BRANCH, current_branch=BRANCH)
            or safety.get('commodity_proxy_36_account_allowed') is not True
            or safety.get('commodity_proxy_36_account_scope', {}).get('registration_sha256') != expected_registration_sha256
            or any(safety.get(key) is not False for key in ('factor_batch_allowed', 'final_holdout_allowed', 'live_boundary_allowed'))):
        raise ValueError('Fresh dedicated finite financial gate required')
    again, admission_again = admitted_packet(root)
    if canonical(again) != canonical(packet) or canonical(admission_again) != canonical(admission):
        raise ValueError('Admission changed during gate')
    folder = resolve_path(root, DIRECTORY)
    claim = dict(registration_sha256=expected_registration_sha256,
        claimed_at=datetime.now(timezone.utc).isoformat(), status='claimed_before_financial_decode',
        admission_sha256=digest(canonical(admission)), gate=gate, policy=POLICY)
    write_exclusive_json(folder/'attempt_claim.json', claim)
    outcome = dict(status='failed_consumed')
    try:
        snapshots = {role: read_bound(root, reference) for role, reference in packet['inputs'].items()}
        inputs = load_inputs(snapshots)
        def guard(phase, identity):
            current, current_admission = admitted_packet(root, unused=False)
            if canonical(current) != canonical(packet) or canonical(current_admission) != canonical(admission):
                raise ValueError('Frozen batch changed during account execution')
        def sink(identity, account):
            write_exclusive_json(folder/'accounts'/(identity.replace('/', '__')+'.json'), account)
        result = calculate(**inputs, guard=guard, account_sink=sink)
        guard('final', 'all_accounts')
        write_exclusive_json(folder/'result.json', result)
        outcome = dict(status='completed', result_sha256=digest(canonical(result)),
            strategy_and_control_accounts=36, cash_benchmarks=2, qualified=False, real_forward_days_added=0)
    except BaseException as exc:
        outcome['error_type'] = type(exc).__name__
        raise
    finally:
        write_exclusive_json(folder/'outcome.json', dict(**outcome,
            registration_sha256=expected_registration_sha256, finished_at=datetime.now(timezone.utc).isoformat()))
    return outcome
