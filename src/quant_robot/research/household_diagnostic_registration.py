"""Identity and one-use evidence for the fixed household event diagnostic.

Only artifact helpers are shared with the prior monthly study. Its registration,
scheduler decision, attempt path, and execution authority are never reused.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import re
from uuid import uuid4

from quant_robot.research.monthly_diagnostic_registration import (
    canonical, relative_path, resolve_path, runtime_environment, sha256,
    write_exclusive_json,
)

STAGE = 'cn_etf_household_preference_event_diagnostic_v1'
HYPOTHESIS = 'household_equity_preference_annual_contrast_v1'
DIRECTORY = 'data/reports/cn_etf_household_preference_event_diagnostic_20260914'
LEDGER = DIRECTORY + '/attempt_claim.json'
SOURCE_ROOT = 'data/reports/etf_monetization_20260911/household_equity_preference_review_20260914'
QUARTERS = tuple(f'{number // 4}Q{number % 4 + 1}' for number in range(2018 * 4 + 3, 2024 * 4 + 1))
DENIED = ('general_factor_batch_allowed', 'promotion_allowed', 'holdout_allowed',
    'paper_account_allowed', 'broker_connection_allowed', 'account_read_allowed', 'order_placement_allowed')
IMPLEMENTATION_FILES = (
    'src/quant_robot/research/household_diagnostic_registration.py',
    'src/quant_robot/research/household_diagnostic_inputs.py',
    'src/quant_robot/research/household_diagnostic_execution.py',
    'src/quant_robot/research/household_diagnostic_pm_scope.py',
    'src/quant_robot/research/household_preference_diagnostic.py',
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/price_basis.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/paper/corporate_actions.py',
    'src/quant_robot/storage/fingerprints.py',
    'scripts/prepare_cn_etf_household_diagnostic.py',
    'scripts/run_cn_etf_household_diagnostic.py',
    'scripts/bootstrap.py',
)


def expected_input_paths():
    paths = {
        'proposal': 'configs/cn_etf_household_equity_preference_proposal_20260914.json',
        'source_review': SOURCE_ROOT + '/source_use_review.json',
        'source_join': 'data/reports/etf_monetization_20260911/joint_source_review_20260914/result.json',
        'survey_inventory': SOURCE_ROOT + '/report_sources/report_source_inventory.json',
        'visual_review': SOURCE_ROOT + '/visual_verification/verified_stock_shares.json',
        'timing_review': SOURCE_ROOT + '/source_timing_review.json',
        'calendar': 'data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar.csv',
        'actions': 'data/reports/etf_monetization_20260911/research_price_basis_20260913/notice_source_contract/510300_notice_gross_observations_v3.json',
    }
    for year in range(2020, 2025):
        paths['bars_' + str(year)] = 'data/processed/tushare_etf_wide_history_2023_2026/processed/bars/frequency=1d/market=CN_ETF/year=' + str(year) + '/part-00000.parquet'
    for quarter in QUARTERS:
        pdf = '/survey_' + quarter.lower() + '.pdf' if quarter in ('2019Q4', '2020Q1') else '/report_sources/' + quarter + '.pdf'
        paths['survey_pdf_' + quarter] = SOURCE_ROOT + pdf
        paths['survey_article_' + quarter] = SOURCE_ROOT + '/detail_inventory/' + quarter + '.html'
    for page in (2, 3, 4, 5):
        paths['survey_catalog_' + str(page)] = SOURCE_ROOT + (
            '/publication_catalog.html' if page == 4 else '/catalog_inventory/catalog' + str(page) + '.html')
    return paths


def _digest(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('fingerprint must be a lowercase SHA256')
    return value


def build_registration(*, inputs, code_files, environment, source_origin, branch):
    paths = expected_input_paths()
    if not isinstance(inputs, dict) or set(inputs) != set(paths):
        raise ValueError('input roles must exactly match the 61 fixed study inputs')
    for role, record in inputs.items():
        if not isinstance(record, dict) or set(record) != {'path', 'sha256'}:
            raise ValueError('each input needs exactly a path and fingerprint')
        if relative_path(record['path']) != paths[role]:
            raise ValueError('input path differs from the fixed source scope: ' + role)
        _digest(record['sha256'])
    if not isinstance(code_files, dict) or not code_files:
        raise ValueError('implementation fingerprints required')
    for path, digest in code_files.items():
        if not relative_path(path).endswith('.py'):
            raise ValueError('implementation must be Python source')
        _digest(digest)
    if not isinstance(environment, dict) or not environment or any(not isinstance(v, str) or not v for v in environment.values()):
        raise ValueError('explicit runtime environment required')
    if source_origin not in {'synthetic_fixture', 'retained_research_sources'}:
        raise ValueError('input origin must be explicit')
    if source_origin == 'retained_research_sources' and set(code_files) != set(IMPLEMENTATION_FILES):
        raise ValueError('real inputs require the complete selected implementation file set')
    if not isinstance(branch, str) or not branch.startswith('codex/factor-'):
        raise ValueError('task branch required')
    payload = {
        'schema_version': 1, 'stage': STAGE, 'status': 'prepared_not_authorized',
        'economic_hypothesis_id': HYPOTHESIS, 'symbol': '510300.SH', 'asset_id': 'CN_ETF_XSHG_510300',
        'window': {'first_anchor': '2020-01-02', 'terminal_anchor': '2024-06-03',
            'anchors': 18, 'intervals': 17, 'close_to_close_transitions': 1068},
        'source_origin': source_origin, 'branch': branch, 'inputs': inputs,
        'code_files': code_files, 'environment': environment, 'ledger_path': LEDGER,
        'output_directory': DIRECTORY, 'max_executions': 1,
        'conditional_gross_diagnostic_only': True, 'scheduler_admission_required': True,
        'fresh_pm_gate_required': True, 'net_account_result': False,
        'complete_search_history_verified': False, **{field: False for field in DENIED},
    }
    payload = json.loads(canonical(payload))
    return {**payload, 'registration_id': sha256(canonical(payload))}


def validate_registration(packet):
    if not isinstance(packet, dict):
        raise ValueError('registration must be an object')
    try:
        expected = build_registration(**{key: packet[key] for key in (
            'inputs', 'code_files', 'environment', 'source_origin', 'branch')})
    except (KeyError, TypeError) as exc:
        raise ValueError('registration fields missing or malformed') from exc
    if canonical(packet) != canonical(expected):
        raise ValueError('registration identity or frozen scope mismatch')
    return expected


def verified_input_bytes(root, registration, *, environment):
    packet = validate_registration(registration)
    if environment != packet['environment']:
        raise ValueError('execution environment differs from registration')
    if packet['source_origin'] == 'retained_research_sources' and environment != runtime_environment():
        raise ValueError('real input environment must match the executing runtime')
    for path, digest in packet['code_files'].items():
        if sha256(resolve_path(root, path).read_bytes()) != digest:
            raise ValueError('implementation fingerprint mismatch: ' + path)
    snapshots = {}
    for role, record in packet['inputs'].items():
        content = resolve_path(root, record['path']).read_bytes()
        if sha256(content) != record['sha256']:
            raise ValueError('input fingerprint mismatch: ' + role)
        snapshots[role] = content
    return snapshots


def check_scheduler_admission(scheduler, registration, *, registration_path, registration_sha256):
    packet = validate_registration(registration)
    if registration_path != DIRECTORY + '/registration.json':
        raise ValueError('registration must use its fixed study path')
    expected = {'status': 'authorized_once', 'registration_id': packet['registration_id'],
        'registration_sha256': _digest(registration_sha256), 'registration_path': registration_path,
        'execution_count': 0, 'max_executions': 1, 'allowed_stage': STAGE,
        'ledger_path': LEDGER, 'conditional_gross_diagnostic_only': True,
        'source_origin': packet['source_origin'], **{field: False for field in DENIED}}
    decision = scheduler.get('household_diagnostic_decision', {})
    if not isinstance(decision, dict) or canonical(decision) != canonical(expected):
        raise ValueError('dedicated household admission absent, consumed or mismatched')
    return expected


def claim_attempt(root, registration):
    packet = validate_registration(registration)
    path = resolve_path(root, packet['ledger_path'])
    if any(resolve_path(root, DIRECTORY + '/' + name).exists() for name in ('result.json', 'outcome.json')):
        raise ValueError('study attempt already claimed or recorded; no rerun')
    path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {'schema_version': 1, 'economic_hypothesis_id': HYPOTHESIS,
        'registration_id': packet['registration_id'], 'attempt_id': uuid4().hex,
        'claimed_at': datetime.now(timezone.utc).isoformat(), 'status': 'claimed_before_signal_or_label_read',
        'source_origin': packet['source_origin']}
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ValueError('study attempt already claimed; partial claims are not unused') from exc
    with os.fdopen(descriptor, 'wb') as handle:
        handle.write(canonical(receipt)); handle.flush(); os.fsync(handle.fileno())
    return receipt


def finish_attempt(root, registration, receipt, *, status, **details):
    packet = validate_registration(registration)
    if status not in {'failed', 'interrupted', 'completed'}:
        raise ValueError('invalid terminal attempt status')
    saved = json.loads(resolve_path(root, packet['ledger_path']).read_bytes())
    if saved != receipt or receipt['registration_id'] != packet['registration_id']:
        raise ValueError('cannot finish a different attempt')
    if set(details) - {'failure_kind', 'result_sha256'}:
        raise ValueError('unsupported attempt detail')
    if status == 'completed':
        result_path = resolve_path(root, DIRECTORY + '/result.json')
        if not result_path.is_file() or sha256(result_path.read_bytes()) != _digest(details.get('result_sha256')):
            raise ValueError('completion requires the fingerprinted result')
    outcome = {**receipt, **details, 'status': status, 'finished_at': datetime.now(timezone.utc).isoformat()}
    write_exclusive_json(resolve_path(root, DIRECTORY + '/outcome.json'), outcome)
    return outcome
