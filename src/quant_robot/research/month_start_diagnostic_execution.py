"""Run one separately admitted month_start study using its retained byte snapshots."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os

from quant_robot.research.month_start_diagnostic_registration import (
    DIRECTORY, validate_registration, check_scheduler_admission, verified_input_bytes,
    claim_attempt, finish_attempt,
)
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, sha256
from quant_robot.research.month_start_diagnostic_inputs import check_source_links, calculate_from_snapshots


@dataclass
class PreparedDiagnostic:
    registration: dict
    registration_sha256: str
    snapshots: dict = field(repr=False)
    gate: dict = field(repr=False)


def _check_gate(gate, packet, decision):
    try:
        generated = datetime.fromisoformat(gate['generated_at'])
        age = (datetime.now(timezone.utc)-generated).total_seconds()
        selected, safety = gate['selected'], gate['safety']
        valid = (0 <= age <= 30 and gate.get('status') == 'ready' and gate.get('blockers') == []
            and gate.get('mode') == 'single_month_start_diagnostic_only' and gate.get('primary_market') == 'CN_ETF'
            and selected.get('machine') == 'office_desktop' and selected.get('task') == 'factor_batch'
            and selected.get('branch') == packet['branch'] and selected.get('current_branch') == packet['branch']
            and safety.get('factor_batch_allowed') is False and safety.get('factor_batch_scope') == {}
            and safety.get('monthly_diagnostic_allowed') is False and safety.get('household_diagnostic_allowed') is False
            and safety.get('month_start_diagnostic_allowed') is True
            and canonical(safety.get('month_start_diagnostic_scope')) == canonical(decision)
            and safety.get('final_holdout_allowed') is False and safety.get('live_boundary_allowed') is False)
    except (KeyError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('fresh dedicated month_start Quant PM admission is required')


def preflight_registration(*, root, registration_path, scheduler, gate_supplier, environment):
    content = resolve_path(root, registration_path).read_bytes()
    packet = validate_registration(json.loads(content))
    decision = check_scheduler_admission(scheduler, packet, registration_path=registration_path,
        registration_sha256=sha256(content))
    if any(resolve_path(root, DIRECTORY+'/'+name).exists()
            for name in ('attempt_claim.json', 'result.json', 'outcome.json')):
        raise ValueError('study attempt already claimed or recorded; no automatic rerun')
    snapshots = verified_input_bytes(root, packet, environment=environment)
    check_source_links(packet, snapshots)
    gate = gate_supplier()
    _check_gate(gate, packet, decision)
    return PreparedDiagnostic(packet, sha256(content), snapshots, gate)


def execute_registration(*, root, registration_path, scheduler, gate_supplier, environment, on_claim=None):
    prepared = preflight_registration(root=root, registration_path=registration_path,
        scheduler=scheduler, gate_supplier=gate_supplier, environment=environment)
    packet = prepared.registration
    receipt = claim_attempt(root, packet)
    try:
        if on_claim is not None:
            on_claim(receipt)
        result = calculate_from_snapshots(packet, prepared.snapshots)
        result.update(attempt_id=receipt['attempt_id'], registration_sha256=prepared.registration_sha256,
            input_files=packet['inputs'], code_files=packet['code_files'], environment=packet['environment'],
            pm_gate=prepared.gate, claimed_at=receipt['claimed_at'])
        encoded = json.dumps(result, indent=2, sort_keys=True, allow_nan=False).encode('utf-8')
        with resolve_path(root, DIRECTORY+'/result.json').open('xb') as handle:
            handle.write(encoded); handle.flush(); os.fsync(handle.fileno())
        finish_attempt(root, packet, receipt, status='completed', result_sha256=sha256(encoded))
        return result
    except BaseException as exc:
        finish_attempt(root, packet, receipt, status='failed' if isinstance(exc, Exception) else 'interrupted',
            failure_kind=type(exc).__name__)
        raise
