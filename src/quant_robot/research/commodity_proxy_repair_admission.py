"""One separately reviewed lifecycle-wrapper repair; the failed attempt stays spent.

The envelope retains every original input and numerical implementation. Only the
loader wrapper and the two routing modules may differ from the failed packet.
Preflight hashes opaque source bytes; only the durable new claim permits decoding.
"""
from datetime import datetime, timezone

from quant_robot.research import commodity_proxy_admission as original
from quant_robot.research.monthly_diagnostic_registration import (
    canonical, resolve_path, write_exclusive_json,
)


DIRECTORY = 'data/reports/campaign_72h_20261106/commodity_accounts_lifecycle_repair'
REGISTRATION = DIRECTORY+'/registration.json'
REVIEW = DIRECTORY+'/independent_review.json'
ADMISSION = 'configs/cn_etf_commodity_proxy_lifecycle_repair_20261106.json'
BRANCH = original.BRANCH
MODE = 'single_campaign_commodity_lifecycle_repair_36_account_only'
POLICY = dict(original.POLICY)
PREDECESSOR_REGISTRATION_SHA256 = 'dccef5c23b77a94414bfc1fe8897ebd26a14607df002c497d240dfc233cb6efe'
PREDECESSOR_PATHS = dict(registration=original.REGISTRATION,
    attempt_claim=original.DIRECTORY+'/attempt_claim.json',
    outcome=original.DIRECTORY+'/outcome.json', independent_review=original.REVIEW,
    admission=original.ADMISSION,
    failure_review='data/reports/campaign_72h_20261106/manager/commodity_first_attempt_failure_independent_review.json')
ALLOWED_CHANGED_IMPLEMENTATION = frozenset((
    'scripts/run_commodity_proxy_accounts.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/account_comparison_scope.py',
))
IMPLEMENTATION = (
    'src/quant_robot/research/commodity_proxy_repair_admission.py',
    'scripts/run_commodity_proxy_repair.py',
)
ACCOUNT_IDENTITIES = frozenset(f'{window}/{rule}/min{minimum}_slip{slip}'
    for window in ('development', 'later') for rule in ('curve', 'holding')
    for minimum in (0, 5, 10) for slip in (0, 10, 30))
digest, read_bound, _json = original.digest, original.read_bound, original._json


def _digest_valid(packet):
    return packet.get('registration_sha256') == digest(canonical(
        {key: value for key, value in packet.items() if key != 'registration_sha256'}))


def _zero(value):
    return type(value) is int and value == 0


def _predecessor(packet, root):
    references = packet['predecessor']
    if not isinstance(references, dict) or set(references) != set(PREDECESSOR_PATHS):
        raise ValueError('Exact preserved predecessor evidence required')
    documents = {}
    for name, reference in references.items():
        if reference['path'] != PREDECESSOR_PATHS[name]:
            raise ValueError('Predecessor evidence alias forbidden')
        documents[name] = _json(read_bound(root, reference))
    old = documents['registration']
    # Do not demand obsolete loader/routing hashes still match current code.
    if (not isinstance(old, dict) or set(old) != {'artifact_type', 'branch', 'inputs',
            'implementation', 'environment', 'policy', 'registration_sha256'}
            or old['artifact_type'] != 'commodity_proxy_account_registration_v1'
            or old['branch'] != BRANCH or not _digest_valid(old)
            or old['registration_sha256'] != PREDECESSOR_REGISTRATION_SHA256
            or set(old['inputs']) != original.INPUT_ROLES
            or set(old['implementation']) != set(original.IMPLEMENTATION)
            or canonical(old['policy']) != canonical(POLICY)):
        raise ValueError('Exact failed original registration required')
    claim, outcome, admission = (documents[name] for name in ('attempt_claim', 'outcome', 'admission'))
    if (set(admission) != {'artifact_type', 'status', 'registration', 'review', 'policy'}
            or admission['artifact_type'] != 'commodity_proxy_finite_admission_v1'
            or admission['status'] != 'authorized_once'
            or admission['registration'] != references['registration']
            or admission['review'] != references['independent_review']
            or canonical(admission['policy']) != canonical(POLICY)):
        raise ValueError('Original admission evidence chain changed')
    review = documents['independent_review']
    if (review.get('status') != 'accepted_for_one_conditional_batch'
            or review.get('registration_sha256') != PREDECESSOR_REGISTRATION_SHA256
            or review.get('reviewer') != 'quant_manager_72h'
            or review.get('qualified') is not False or not _zero(review.get('real_forward_days_added'))):
        raise ValueError('Original independent review evidence changed')
    if (claim.get('status') != 'claimed_before_financial_decode'
            or claim.get('registration_sha256') != PREDECESSOR_REGISTRATION_SHA256
            or claim.get('admission_sha256') != digest(canonical(admission))
            or canonical(claim.get('policy')) != canonical(POLICY)
            or claim.get('gate', {}).get('mode') != original.MODE
            or claim.get('gate', {}).get('status') != 'ready'
            or claim.get('gate', {}).get('safety', {}).get('commodity_proxy_36_account_scope',
                {}).get('registration_sha256') != PREDECESSOR_REGISTRATION_SHA256):
        raise ValueError('Original attempt claim does not bind failed registration')
    if (set(outcome) != {'status', 'error_type', 'registration_sha256', 'finished_at'}
            or outcome['status'] != 'failed_consumed' or outcome['error_type'] != 'ValueError'
            or outcome['registration_sha256'] != PREDECESSOR_REGISTRATION_SHA256):
        raise ValueError('Only the preserved pre-signal ValueError failure may be repaired')
    folder = resolve_path(root, original.DIRECTORY)
    if any((folder/name).exists() for name in ('result.json', 'accounts')):
        raise ValueError('Predecessor with any result or account directory cannot be repaired')
    failure = documents['failure_review']
    boundary = failure.get('execution_boundary', {})
    proposal = failure.get('allowed_next_proposal', {})
    inventory = failure.get('lifecycle_original', {})
    reproduction = failure.get('metadata_only_reproduction', {})
    if (failure.get('artifact_type') != 'commodity_first_attempt_engineering_failure_review_v1'
            or failure.get('status') != 'confirmed_pre_signal_interface_failure_consumed'
            or failure.get('reviewer') != 'quant_manager_72h'
            or failure.get('registration_sha256') != PREDECESSOR_REGISTRATION_SHA256
            or failure.get('qualified') is not False or not _zero(failure.get('real_forward_days_added'))
            or any(not _zero(boundary.get(key)) for key in (
                'financial_accounts_computed', 'result_files', 'signal_values_computed'))
            or boundary.get('real_ETF_and_settlement_fields_decoded_by_original_loader') is not True
            or proposal.get('old_attempt_preserved') is not True
            or proposal.get('new_parameter_search') is not False
            or proposal.get('same_originals_method_dates_costs_risk_and_numeric_kernel') is not True
            or proposal.get('new_separate_finite_technical_registration_required') is not True
            or inventory.get('outer_type') != 'dict' or inventory.get('records') != 43
            or set(inventory.get('outer_keys', [])) != {'source_sha256', 'records',
                'delist_date_semantics', 'historical_vintage_verified'}
            or inventory.get('records_inventory_validation_passed') is not True
            or {key: inventory.get(key) for key in ('path', 'sha256')} != old['inputs']['lifecycle']
            or reproduction.get('function') != 'commodity_curve_proxy._inventory'
            or reproduction.get('real_financial_values_read') is not False
            or reproduction.get('same_error') != 'Bounded contract lifecycle inventory required'):
        raise ValueError('Independent lifecycle boundary failure evidence required')
    if failure.get('files') != {name+'.json': references[name] for name in (
            'registration', 'attempt_claim', 'outcome', 'independent_review')}:
        raise ValueError('Failure review predecessor fingerprints changed')
    return old


def validate_registration(packet, root):
    if (not isinstance(packet, dict) or set(packet) != {'artifact_type', 'branch', 'predecessor',
            'base_registration', 'implementation', 'policy', 'registration_sha256'}
            or packet['artifact_type'] != 'commodity_proxy_lifecycle_repair_registration_v1'
            or packet['branch'] != BRANCH or canonical(packet['policy']) != canonical(POLICY)
            or set(packet['implementation']) != set(IMPLEMENTATION) or not _digest_valid(packet)):
        raise ValueError('Exact finite lifecycle repair registration required')
    old = _predecessor(packet, root)
    base = packet['base_registration']
    if not isinstance(base, dict) or set(base) != set(old):
        raise ValueError('Original-shaped current base registration required')
    for key in set(old)-{'implementation', 'registration_sha256'}:
        if canonical(base[key]) != canonical(old[key]):
            raise ValueError('Repair must retain all original inputs, method, environment and policy')
    if not isinstance(base['implementation'], dict) or set(base['implementation']) != set(old['implementation']):
        raise ValueError('Repair must retain all16 implementation paths')
    for name, reference in base['implementation'].items():
        if (name not in ALLOWED_CHANGED_IMPLEMENTATION
                and canonical(reference) != canonical(old['implementation'][name])):
            raise ValueError('Numerical implementation or unrelated code may not change')
    original.validate_registration(base, root)
    for name, reference in packet['implementation'].items():
        if name != reference['path']:
            raise ValueError('Repair implementation alias forbidden')
        read_bound(root, reference, return_bytes=False)
    return packet


def require_unused(root):
    folder = resolve_path(root, DIRECTORY)
    if any((folder/name).exists() for name in ('attempt_claim.json', 'result.json', 'outcome.json', 'accounts')):
        raise ValueError('Lifecycle repair already reserved or consumed; no resume')


def admitted_packet(root, *, unused=True):
    admission = _json(resolve_path(root, ADMISSION).read_bytes())
    if (set(admission) != {'artifact_type', 'status', 'registration', 'review', 'policy'}
            or admission['artifact_type'] != 'commodity_proxy_lifecycle_repair_admission_v1'
            or admission['status'] != 'authorized_once' or canonical(admission['policy']) != canonical(POLICY)
            or admission['registration']['path'] != REGISTRATION or admission['review']['path'] != REVIEW):
        raise ValueError('Separately reviewed one-use lifecycle repair admission required')
    packet = validate_registration(_json(read_bound(root, admission['registration'])), root)
    review = _json(read_bound(root, admission['review']))
    if (set(review) != {'status', 'registration_sha256', 'predecessor_registration_sha256',
            'reviewer', 'qualified', 'real_forward_days_added'}
            or review['status'] != 'accepted_for_one_conditional_lifecycle_repair'
            or review['registration_sha256'] != packet['registration_sha256']
            or review['predecessor_registration_sha256'] != PREDECESSOR_REGISTRATION_SHA256
            or review['reviewer'] != 'quant_manager_72h' or review['qualified'] is not False
            or not _zero(review['real_forward_days_added'])):
        raise ValueError('Independent review of exact lifecycle repair required')
    if unused:
        require_unused(root)
    return packet, admission


def _scope(packet, root):
    return dict(registration_sha256=packet['registration_sha256'],
        admission_file_sha256=digest(resolve_path(root, ADMISSION).read_bytes()), policy=POLICY)


def scope(task, family_config, family_schedule, *, root, branch):
    if task != 'factor_review' or branch != BRANCH or not resolve_path(root, ADMISSION).exists():
        return None
    if (set(family_schedule.get('blockers', [])) != {'insufficient_active_research_families'}
            or family_schedule['summary'].get('primary_budget_share') != 0
            or family_schedule['summary'].get('active_primary_families') != 0):
        return None
    try:
        packet, _ = admitted_packet(root)
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return dict(mode=MODE, scope=_scope(packet, root))


def review_comparison(root, scope):
    packet, _ = admitted_packet(root)
    if canonical(scope) != canonical(_scope(packet, root)):
        raise ValueError('Comparison must bind exact lifecycle repair scope')
    base = packet['base_registration']
    return dict(status='passed_specification_only', blockers=[],
        method=base['inputs']['method'], implementation={**base['implementation'], **packet['implementation']},
        predecessor=packet['predecessor'], strategy_and_matched_holding_accounts=36, cash_controls=2,
        no_price_decoding_performed=True, predecessor_financial_fields_decoded=True,
        net_positive_EV_verified=False, source_quality_verified=False)


def execute(root, *, expected_registration_sha256, gate_supplier, load_inputs, calculate):
    packet, admission = admitted_packet(root)
    if expected_registration_sha256 != packet['registration_sha256']:
        raise ValueError('Exact repair registration digest required')
    gate = gate_supplier()
    selected, safety = gate['selected'], gate['safety']
    age = (datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'].replace('Z', '+00:00'))).total_seconds()
    if (not 0 <= age <= 120 or gate['status'] != 'ready' or gate['blockers']
            or gate['mode'] != MODE or gate['primary_market'] != 'CN_ETF'
            or selected != dict(machine='office_desktop', task='factor_review', branch=BRANCH, current_branch=BRANCH)
            or safety.get('commodity_proxy_lifecycle_repair_allowed') is not True
            or canonical(safety.get('commodity_proxy_lifecycle_repair_scope')) != canonical(_scope(packet, root))
            or any(safety.get(key) is not False for key in ('commodity_proxy_36_account_allowed',
                'factor_batch_allowed', 'final_holdout_allowed', 'live_boundary_allowed'))):
        raise ValueError('Fresh dedicated lifecycle repair financial gate required')
    again, admission_again = admitted_packet(root)
    if canonical(again) != canonical(packet) or canonical(admission_again) != canonical(admission):
        raise ValueError('Repair admission changed during gate')
    folder = resolve_path(root, DIRECTORY)
    write_exclusive_json(folder/'attempt_claim.json', dict(
        registration_sha256=expected_registration_sha256,
        predecessor_registration_sha256=PREDECESSOR_REGISTRATION_SHA256,
        claimed_at=datetime.now(timezone.utc).isoformat(), status='claimed_before_financial_decode',
        admission_sha256=digest(canonical(admission)), gate=gate, policy=POLICY))
    outcome = dict(status='failed_consumed')
    try:
        def guard(phase, identity):
            current, current_admission = admitted_packet(root, unused=False)
            if canonical(current) != canonical(packet) or canonical(current_admission) != canonical(admission):
                raise ValueError('Frozen repair changed during execution')
        guard('before', 'source_decode')
        snapshots = {role: read_bound(root, reference)
            for role, reference in packet['base_registration']['inputs'].items()}
        inputs = load_inputs(snapshots)
        guard('after', 'source_decode')
        saved = set()
        def sink(identity, account):
            if identity not in ACCOUNT_IDENTITIES or identity in saved:
                raise ValueError('Only the fixed36 unique account identities may be saved')
            guard('before', 'account_save')
            write_exclusive_json(folder/'accounts'/(identity.replace('/', '__')+'.json'), account)
            saved.add(identity)
        result = calculate(**inputs, guard=guard, account_sink=sink)
        guard('final', 'all_accounts')
        if (saved != ACCOUNT_IDENTITIES or result.get('account_count') != 36
                or result.get('cash_benchmark_count') != 2 or result.get('qualified') is not False
                or not _zero(result.get('real_forward_days_added'))):
            raise ValueError('Exact36 conditional accounts and two cash benchmarks required')
        write_exclusive_json(folder/'result.json', result)
        outcome = dict(status='completed', result_sha256=digest(canonical(result)),
            strategy_and_control_accounts=36, cash_benchmarks=2, qualified=False, real_forward_days_added=0)
    except BaseException as exc:
        outcome['error_type'] = type(exc).__name__
        raise
    finally:
        write_exclusive_json(folder/'outcome.json', dict(**outcome,
            registration_sha256=expected_registration_sha256,
            predecessor_registration_sha256=PREDECESSOR_REGISTRATION_SHA256,
            finished_at=datetime.now(timezone.utc).isoformat()))
    return outcome
