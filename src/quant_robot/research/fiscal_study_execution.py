"""Verify snapshots and exact admission, then durably claim before real arithmetic."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json

from quant_robot.research.fiscal_study_registration import (
    DIRECTORY, validate_registration, check_scheduler_admission, verified_input_bytes,
    require_unused, claim_attempt, finish_attempt,
)
from quant_robot.research.monthly_diagnostic_registration import canonical, resolve_path, sha256, write_exclusive_json


@dataclass
class PreparedFiscalStudy:
    registration: dict
    registration_sha256: str
    snapshots: dict = field(repr=False)
    gate: dict = field(repr=False)


def _check_gate(gate, packet, decision):
    try:
        age = (datetime.now(timezone.utc)-datetime.fromisoformat(gate['generated_at'])).total_seconds()
        selected, safety = gate['selected'], gate['safety']
        valid = (0 <= age <= 30 and gate.get('status') == 'ready' and gate.get('blockers') == []
            and gate.get('mode') == 'single_fiscal_event_account_only' and gate.get('primary_market') == 'CN_ETF'
            and selected.get('machine') == 'office_desktop' and selected.get('task') == 'factor_batch'
            and selected.get('branch') == packet['branch'] and selected.get('current_branch') == packet['branch']
            and safety.get('factor_batch_scope') == {} and safety.get('fiscal_event_account_allowed') is True
            and canonical(safety.get('fiscal_event_account_scope')) == canonical(decision)
            and all(safety.get(key) is False for key in ('factor_batch_allowed', 'monthly_diagnostic_allowed',
                'household_diagnostic_allowed', 'month_start_diagnostic_allowed', 'final_holdout_allowed', 'live_boundary_allowed')))
    except (KeyError, ValueError, TypeError):
        valid = False
    if not valid:
        raise ValueError('Fresh exact fiscal Quant PM admission required')


def preflight_registration(*, root, scheduler, gate_supplier, environment):
    content = resolve_path(root, DIRECTORY+'/registration.json').read_bytes()
    packet = validate_registration(json.loads(content))
    decision = check_scheduler_admission(scheduler, packet,
        registration_path=DIRECTORY+'/registration.json', registration_sha256=sha256(content))
    require_unused(root)
    snapshots = verified_input_bytes(root, packet, environment=environment)
    gate = gate_supplier()
    _check_gate(gate, packet, decision)
    return PreparedFiscalStudy(packet, sha256(content), snapshots, gate)


def execute_registration(*, root, scheduler, gate_supplier, environment, on_claim=None):
    from quant_robot.research.fiscal_study_inputs import calculate_from_snapshots
    prepared = preflight_registration(root=root, scheduler=scheduler,
        gate_supplier=gate_supplier, environment=environment)
    packet = prepared.registration
    receipt = claim_attempt(root, packet)
    try:
        if on_claim is not None:
            on_claim(receipt)
        result = calculate_from_snapshots(packet, prepared.snapshots)
        result.update(attempt_id=receipt['attempt_id'], registration_sha256=prepared.registration_sha256,
            input_files=packet['inputs'], code_files=packet['code_files'], environment=packet['environment'],
            pm_gate=prepared.gate, claimed_at=receipt['claimed_at'])
        write_exclusive_json(resolve_path(root, DIRECTORY+'/result.json'), result)
        finish_attempt(root, packet, receipt, status='completed', result_sha256=sha256(canonical(result)))
        return result
    except BaseException as exc:
        finish_attempt(root, packet, receipt, status='failed' if isinstance(exc, Exception) else 'interrupted',
            failure_kind=type(exc).__name__)
        raise
