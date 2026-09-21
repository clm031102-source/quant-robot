"""A separate one-use scope for the fixed household study, with no batch budget."""
import json

from quant_robot.research.household_diagnostic_registration import (
    DIRECTORY, check_scheduler_admission, validate_registration,
)
from quant_robot.research.monthly_diagnostic_registration import resolve_path, sha256


def household_diagnostic_scope(task, family_config, family_schedule, *, root, branch):
    if task != 'factor_batch':
        return None
    decision = family_config.get('household_diagnostic_decision')
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
        if packet['branch'] != branch or any(resolve_path(root, DIRECTORY + '/' + name).exists()
                for name in ('attempt_claim.json', 'result.json', 'outcome.json')):
            return None
        scope = check_scheduler_admission(family_config, packet,
            registration_path=path, registration_sha256=sha256(content))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {'mode': 'single_household_diagnostic_only', 'scope': scope}
