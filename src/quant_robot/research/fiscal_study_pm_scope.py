"""Only one separately registered conditional fiscal account, without batch budget."""
import json

from quant_robot.research.fiscal_study_registration import (
    DIRECTORY, check_scheduler_admission, require_unused, validate_registration,
)
from quant_robot.research.monthly_diagnostic_registration import resolve_path, sha256


def fiscal_study_scope(task, family_config, family_schedule, *, root, branch):
    if task != 'factor_batch':
        return None
    decision = family_config.get('fiscal_event_account_decision')
    if not isinstance(decision, dict) or decision.get('status') != 'authorized_once':
        return None
    summary = family_schedule.get('summary', {})
    if (set(family_schedule.get('blockers', [])) != {'insufficient_active_research_families'}
            or summary.get('primary_budget_share') != 0 or summary.get('active_primary_families') != 0):
        return None
    try:
        content = resolve_path(root, DIRECTORY+'/registration.json').read_bytes()
        packet = validate_registration(json.loads(content))
        if packet['branch'] != branch:
            return None
        require_unused(root)
        scope = check_scheduler_admission(family_config, packet,
            registration_path=decision['registration_path'], registration_sha256=sha256(content))
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return {'mode': 'single_fiscal_event_account_only', 'scope': scope}
