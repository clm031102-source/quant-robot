"""Registration and exclusive attempt evidence for one conditional monthly study.

Registration does not authorize reading outcomes. The executor must additionally
check the exact scheduler admission and a fresh matching Quant PM gate.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
from uuid import uuid4

STAGE = 'cn_etf_policy_uncertainty_historical_diagnostic_v1'
HYPOTHESIS = 'policy_uncertainty_monthly_median_v1'
DIRECTORY = 'data/reports/cn_etf_policy_uncertainty_historical_diagnostic_20260914'
LEDGER = DIRECTORY + '/attempt_claim.json'
INPUT_ROLES = frozenset(['proposal', 'source_review', 'source_join', 'policy_audit', 'policy_scope',
    'calendar', 'actions', 'policy_1', 'policy_2', *['bars_' + str(year) for year in range(2020, 2025)]])
DENIED = ('general_factor_batch_allowed', 'promotion_allowed', 'holdout_allowed',
    'paper_account_allowed', 'broker_connection_allowed', 'account_read_allowed', 'order_placement_allowed')
IMPLEMENTATION_FILES = (
    'src/quant_robot/research/monthly_diagnostic_registration.py',
    'src/quant_robot/research/monthly_diagnostic_execution.py',
    'src/quant_robot/research/monthly_diagnostic_inputs.py',
    'src/quant_robot/research/monthly_diagnostic_pm_scope.py',
    'src/quant_robot/research/policy_uncertainty_diagnostic.py',
    'src/quant_robot/research/price_basis.py',
    'src/quant_robot/research/pm_startup_gate.py',
    'src/quant_robot/research/family_scheduler.py',
    'src/quant_robot/data/alfred_monthly_vintages.py',
    'src/quant_robot/paper/corporate_actions.py',
    'src/quant_robot/storage/fingerprints.py',
    'scripts/prepare_cn_etf_policy_uncertainty_diagnostic.py',
    'scripts/run_cn_etf_policy_uncertainty_diagnostic.py',
    'scripts/bootstrap.py',
)


def runtime_environment():
    from importlib.metadata import version
    return {'python': platform.python_version(), 'implementation': platform.python_implementation(),
        'platform': platform.platform(), **{name: version(name) for name in ('pandas', 'pyarrow', 'numpy')}}


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('fingerprint must be a lowercase SHA256')
    return value


def relative_path(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('paths must be relative POSIX paths')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != value or value == '.':
        raise ValueError('paths must remain inside the workspace')
    return value


def resolve_path(root, value):
    root = Path(root).resolve()
    path = (root / relative_path(value)).resolve()
    if not _comparison_path(path).is_relative_to(_comparison_path(root)):
        raise ValueError(f'resolved path leaves the workspace: root={root!s}; path={path!s}')
    return path


def _comparison_path(path):
    # ntpath.realpath can retain the extended prefix when an absent parent is
    # created between its two existence probes (WinError3 becomes WinError2).
    # Compare equivalent drive/UNC spellings, retaining the actual resolved path
    # for I/O. Other device namespaces and resolved outside targets stay rejected.
    text = str(path)
    if os.name == 'nt':
        if text.startswith('\\\\?\\UNC\\'):
            text = '\\\\' + text[8:]
        elif text.startswith('\\\\?\\') and re.match(r'[A-Za-z]:\\', text[4:]):
            text = text[4:]
    return Path(text)


def build_registration(*, inputs, code_files, environment, source_origin, branch):
    if not isinstance(inputs, dict) or set(inputs) != INPUT_ROLES:
        raise ValueError('input roles must exactly match the fixed study')
    for role, record in inputs.items():
        if not isinstance(record, dict) or set(record) != {'path', 'sha256'}:
            raise ValueError('each input needs exactly a path and fingerprint')
        path = relative_path(record['path'])
        if not path.startswith(('data/', 'configs/')) or PurePosixPath(path).suffix not in {'.json', '.csv', '.parquet'}:
            raise ValueError('input must be a scoped research artifact')
        _digest(record['sha256'])
        partitions = re.findall(r'(?:^|/)year=(\d{4})(?:/|$)', path)
        if partitions and (not role.startswith('bars_') or partitions != [role[-4:]]):
            raise ValueError('bar partition does not match its fixed year')
    if len({item['path'] for item in inputs.values()}) != len(inputs):
        raise ValueError('input roles must identify distinct files')
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
        raise ValueError('real inputs require the complete frozen implementation file set')
    if not isinstance(branch, str) or not branch.startswith('codex/factor-'):
        raise ValueError('task branch required')
    payload = {'schema_version': 1, 'stage': STAGE, 'status': 'prepared_not_authorized',
        'economic_hypothesis_id': HYPOTHESIS, 'symbol': '510300.SH', 'asset_id': 'CN_ETF_XSHG_510300',
        'window': {'first_anchor_month': '2020-01', 'last_anchor_month': '2024-06', 'anchors': 54, 'intervals': 53},
        'source_origin': source_origin, 'branch': branch, 'inputs': inputs, 'code_files': code_files,
        'environment': environment, 'ledger_path': LEDGER, 'output_directory': DIRECTORY,
        'max_executions': 1, 'conditional_gross_diagnostic_only': True,
        'scheduler_admission_required': True, 'fresh_pm_gate_required': True,
        'net_account_result': False, 'complete_search_history_verified': False,
        **{field: False for field in DENIED}}
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
    decision = scheduler.get('monthly_diagnostic_decision', {})
    expected = {'status': 'authorized_once', 'registration_id': packet['registration_id'],
        'registration_sha256': _digest(registration_sha256),
        'registration_path': relative_path(registration_path), 'execution_count': 0,
        'max_executions': 1, 'allowed_stage': STAGE, 'ledger_path': LEDGER,
        'conditional_gross_diagnostic_only': True, 'source_origin': packet['source_origin'],
        **{field: False for field in DENIED}}
    if not isinstance(decision, dict) or canonical(decision) != canonical(expected):
        raise ValueError('dedicated scheduler admission absent, consumed or mismatched')
    return expected


def claim_attempt(root, registration):
    packet = validate_registration(registration)
    path = resolve_path(root, packet['ledger_path'])
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
    path = resolve_path(root, DIRECTORY + '/outcome.json')
    write_exclusive_json(path, outcome)
    return outcome


def write_exclusive_json(path, value):
    """Never replace prior or partial evidence, including across racing writers."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(canonical(value)); handle.flush(); os.fsync(handle.fileno())
