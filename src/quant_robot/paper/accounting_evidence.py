"""Promotion checks for source-qualified execution accounting evidence."""
from __future__ import annotations

import re
from typing import Any

from quant_robot.paper.economics import VALUATION_MODEL


def paper_accounting_blockers(manifest: dict[str, Any]) -> list[str]:
    accounting = manifest.get("accounting")
    request = manifest.get("request", {})
    if not isinstance(accounting, dict) or not isinstance(request, dict):
        return ["paper_execution_accounting_missing"]
    blockers = []
    if accounting.get("source_audit_verified") is not True:
        blockers.append("paper_execution_accounting_source_unverified")
    if accounting.get("declared_coverage_validated") is not True:
        blockers.append("paper_corporate_action_coverage_missing")
    fingerprint = accounting.get("corporate_actions_fingerprint")
    if (not isinstance(fingerprint, str) or re.fullmatch(r"[0-9a-f]{64}", fingerprint) is None
            or fingerprint != request.get("corporate_actions_fingerprint")):
        blockers.append("paper_corporate_action_fingerprint_mismatch")
    if request.get("valuation_model") != VALUATION_MODEL:
        blockers.append("paper_execution_valuation_model_mismatch")
    return blockers
