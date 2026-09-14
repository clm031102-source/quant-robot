"""Dedicated immutable identity and one-use claim for the fixed fiscal study."""
from datetime import datetime, timezone
import json
import os
import re
from uuid import uuid4

from quant_robot.research.fiscal_execution_gate import HYPOTHESIS
from quant_robot.research.monthly_diagnostic_registration import (
    canonical, relative_path, resolve_path, runtime_environment, sha256, write_exclusive_json,
)

STAGE = 'cn_etf_fiscal_event_account_v1'
DIRECTORY = 'data/reports/cn_etf_fiscal_event_account_20260914'
LEDGER = DIRECTORY + '/attempt_claim.json'
REVIEW_PATH = 'data/reports/etf_monetization_20260911/fiscal_execution_review_20260914/account_contract_review/source_use_review.json'
REVIEW_SHA256 = 'cf4c2fce729646cc3b56aaa8aab9cd0a87985fe4bedf1486c880ab4549c25168'
PROPOSAL_PATH = 'configs/cn_etf_fiscal_execution_proposal_20260914.json'
PROPOSAL_SHA256 = '4447d118b644f327f430aeff79acc7d593071e05cad419e98f5ee2c22f3c07b8'
DENIED = ('general_factor_batch_allowed', 'promotion_allowed', 'holdout_allowed',
    'paper_account_allowed', 'broker_connection_allowed', 'account_read_allowed', 'order_placement_allowed')
IMPLEMENTATION_FILES = (
    'src/quant_robot/research/fiscal_study_registration.py',
    'src/quant_robot/research/fiscal_study_execution.py',
    'src/quant_robot/research/fiscal_study_inputs.py',
    'src/quant_robot/research/fiscal_study_pm_scope.py',
    'src/quant_robot/research/fiscal_execution_gate.py',
    'src/quant_robot/research/fiscal_execution_decision.py',
    'src/quant_robot/research/announced_cash_ledger.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/pm_startup_gate.py', 'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/paper/event_hold.py', 'src/quant_robot/paper/fixed_hold.py',
    'src/quant_robot/paper/corporate_actions.py', 'src/quant_robot/paper/simulator.py',
    'src/quant_robot/paper/account_comparison.py', 'src/quant_robot/paper/economics.py',
    'src/quant_robot/backtest/costs.py', 'src/quant_robot/data/quality.py',
    'src/quant_robot/schema/market_data.py', 'src/quant_robot/data/cn_calendar_snapshot.py',
    'src/quant_robot/data/cn_trading_calendar.py', 'src/quant_robot/storage/input_provenance.py',
    'src/quant_robot/storage/fingerprints.py', 'src/quant_robot/storage/atomic.py',
    'scripts/run_cn_etf_fiscal_study.py', 'scripts/bootstrap.py',
)


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Lowercase SHA256 required')
    return value


def build_registration(*, inputs, code_files, environment, source_origin, branch):
    if not isinstance(inputs, dict) or REVIEW_PATH not in inputs or not isinstance(code_files, dict) or not code_files:
        raise ValueError('Source-use review, inputs and implementation fingerprints required')
    for mapping in (inputs, code_files):
        for path, digest in mapping.items():
            relative_path(path); _digest(digest)
    if any(not path.endswith('.py') for path in code_files):
        raise ValueError('Implementation must be Python source')
    if source_origin not in ('synthetic_fixture', 'retained_research_sources'):
        raise ValueError('Explicit source origin required')
    if source_origin == 'retained_research_sources' and (
            inputs.get(REVIEW_PATH) != REVIEW_SHA256 or inputs.get(PROPOSAL_PATH) != PROPOSAL_SHA256
            or len(inputs) != 165 or set(code_files) != set(IMPLEMENTATION_FILES)):
        raise ValueError('Real sources require exact reviewed proposal, source packet and complete implementation')
    if not isinstance(environment, dict) or not environment or any(not isinstance(v, str) or not v for v in environment.values()):
        raise ValueError('Explicit runtime environment required')
    if not isinstance(branch, str) or not branch.startswith('codex/factor-'):
        raise ValueError('Research task branch required')
    payload = {'schema_version': 1, 'stage': STAGE, 'status': 'prepared_not_authorized',
        'economic_hypothesis_id': HYPOTHESIS, 'source_origin': source_origin, 'branch': branch,
        'inputs': inputs, 'code_files': code_files, 'environment': environment,
        'ledger_path': LEDGER, 'output_directory': DIRECTORY, 'max_executions': 1,
        'conditional_historical_account_only': True, 'fresh_pm_gate_required': True,
        'complete_search_history_verified': False, **{key: False for key in DENIED}}
    payload = json.loads(canonical(payload))
    return {**payload, 'registration_id': sha256(canonical(payload))}


def validate_registration(packet):
    try:
        expected = build_registration(**{key: packet[key] for key in (
            'inputs', 'code_files', 'environment', 'source_origin', 'branch')})
    except (KeyError, TypeError) as exc:
        raise ValueError('Malformed fiscal registration') from exc
    if canonical(packet) != canonical(expected):
        raise ValueError('Frozen fiscal scope or identity differs')
    return expected


def verified_input_bytes(root, registration, *, environment):
    packet = validate_registration(registration)
    if environment != packet['environment'] or (packet['source_origin'] == 'retained_research_sources' and environment != runtime_environment()):
        raise ValueError('Registered runtime differs')
    for path, digest in packet['code_files'].items():
        if sha256(resolve_path(root, path).read_bytes()) != digest:
            raise ValueError('Implementation changed: ' + path)
    snapshots = {}
    for path, digest in packet['inputs'].items():
        content = resolve_path(root, path).read_bytes()
        if sha256(content) != digest:
            raise ValueError('Source changed: ' + path)
        snapshots[path] = content
    review = json.loads(snapshots[REVIEW_PATH])
    if (review.get('status') != 'conditional_source_use_reviewed_not_admitted'
            or review.get('economic_hypothesis_id') != HYPOTHESIS
            or review.get('source_fingerprints') != {p: d for p, d in packet['inputs'].items() if p != REVIEW_PATH}):
        raise ValueError('Dedicated source-use review does not bind exactly these inputs')
    for field in ('source_audit_verified', 'historical_availability_verified', 'research_admission_granted',
                  'local_ETF_price_columns_decoded', 'real_fiscal_ratios_computed', 'net_account_cash_verified'):
        if review.get(field) is not False:
            raise ValueError('Source review cannot grant outcome or account certification')
    return snapshots


def expected_admission(registration, registration_sha256):
    packet = validate_registration(registration)
    return {'status': 'authorized_once', 'registration_id': packet['registration_id'],
        'registration_path': DIRECTORY+'/registration.json', 'registration_sha256': _digest(registration_sha256),
        'execution_count': 0, 'max_executions': 1, 'allowed_stage': STAGE, 'ledger_path': LEDGER,
        'source_origin': packet['source_origin'], 'conditional_historical_account_only': True,
        **{key: False for key in DENIED}}


def check_scheduler_admission(scheduler, registration, *, registration_path, registration_sha256):
    expected = expected_admission(registration, registration_sha256)
    if registration_path != expected['registration_path'] or canonical(scheduler.get('fiscal_event_account_decision')) != canonical(expected):
        raise ValueError('Dedicated fiscal admission absent, consumed or mismatched')
    return expected


def require_unused(root):
    if any(resolve_path(root, DIRECTORY+'/'+name).exists() for name in ('attempt_claim.json', 'result.json', 'outcome.json')):
        raise ValueError('Fiscal attempt already claimed or recorded; no rerun')


def claim_attempt(root, registration):
    packet = validate_registration(registration)
    require_unused(root)
    path = resolve_path(root, LEDGER); path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'registration_id': packet['registration_id'], 'attempt_id': uuid4().hex,
        'claimed_at': datetime.now(timezone.utc).isoformat(), 'source_origin': packet['source_origin'],
        'status': 'claimed_before_real_fiscal_ratio_or_price_read'}
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('Fiscal attempt already claimed') from exc
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(canonical(receipt)); handle.flush(); os.fsync(handle.fileno())
    return receipt


def finish_attempt(root, registration, receipt, *, status, **details):
    packet = validate_registration(registration)
    if status not in ('completed', 'failed', 'interrupted') or set(details) - {'failure_kind', 'result_sha256'}:
        raise ValueError('Invalid terminal fiscal attempt state')
    if json.loads(resolve_path(root, LEDGER).read_bytes()) != receipt or receipt['registration_id'] != packet['registration_id']:
        raise ValueError('Cannot finish a different claim')
    if status == 'completed' and sha256(resolve_path(root, DIRECTORY+'/result.json').read_bytes()) != _digest(details.get('result_sha256')):
        raise ValueError('Completion requires the exact result')
    outcome = {**receipt, **details, 'status': status, 'finished_at': datetime.now(timezone.utc).isoformat()}
    write_exclusive_json(resolve_path(root, DIRECTORY+'/outcome.json'), outcome)
    return outcome
