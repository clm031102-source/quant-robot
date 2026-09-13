"""A dedicated, consumed-once scope; never enables general factor batches."""
from __future__ import annotations

import json

from quant_robot.research.monthly_diagnostic_registration import (
    check_scheduler_admission, resolve_path, sha256, validate_registration,
)


def monthly_diagnostic_scope(task, family_config, family_schedule, *, root, branch):
    if task != 'factor_batch':
        return None
    decision = family_config.get('monthly_diagnostic_decision')
    if not isinstance(decision, dict) or decision.get('status') != 'authorized_once':
        return None
    summary = family_schedule.get('summary', {})
    if (set(family_schedule.get('blockers', [])) != {'insufficient_active_research_families'}
            or summary.get('primary_budget_share') != 0 or summary.get('active_primary_families') != 0):
        return None
    try:
        path = decision['registration_path']
        content = resolve_path(root, path).read_bytes()
        packet = validate_registration(json.loads(content))
        if packet['branch'] != branch or resolve_path(root, packet['ledger_path']).exists():
            return None
        scope = check_scheduler_admission(family_config, packet, registration_path=path,
            registration_sha256=sha256(content))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {'mode': 'single_monthly_diagnostic_only', 'scope': scope}
