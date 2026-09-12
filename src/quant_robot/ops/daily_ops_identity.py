"""Check declared daily trading recipes; this does not certify research sources."""
from __future__ import annotations

import ast
import hashlib
import json
import math
from decimal import Decimal, InvalidOperation
from typing import Any

RECIPE_FIELDS = ("market", "factor_source", "factor_name", "factor_windows", "top_n", "rebalance_interval")
SHARED_FIELDS = RECIPE_FIELDS[:-1]
WEIGHT_FIELDS = ("max_asset_weight", "max_market_weight", "max_gross_exposure", "min_cash_weight")


def require_daily_candidate_recipe(candidate: dict[str, Any]) -> dict[str, Any]:
    """Require explicit parameters before generating new daily artifacts."""
    issues: list[dict[str, str]] = []
    recipe = _recipe(candidate, RECIPE_FIELDS, "candidate", issues)
    if _text(candidate.get("case_id")) is None:
        _issue(issues, "candidate", "case_id", "missing_or_invalid")
    if issues:
        fields = ", ".join(issue["field"] for issue in issues)
        raise ValueError(f"Daily Ops candidate recipe is incomplete or invalid: {fields}")
    return recipe


def validate_daily_artifact_recipe(
    candidate: dict[str, Any], readiness_candidate: Any, signal: dict[str, Any],
    simulation: dict[str, Any], profile: dict[str, Any],
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    expected = _recipe(candidate, RECIPE_FIELDS, "candidate", issues)
    case_id = _text(candidate.get("case_id"))
    if case_id is None:
        _issue(issues, "candidate", "case_id", "missing_or_invalid")
    requests = {"signal": signal.get("request"), "simulation": simulation.get("request")}
    normalized: dict[str, dict[str, Any]] = {}
    for role, request in requests.items():
        mapping = request if isinstance(request, dict) else {}
        fields = SHARED_FIELDS if role == "signal" else RECIPE_FIELDS
        normalized[role] = _recipe(mapping, fields, role, issues)
        for field in fields:
            if field in expected and field in normalized[role] and expected[field] != normalized[role][field]:
                _issue(issues, role, field, "candidate_mismatch")
        if "case_id" in mapping and _text(mapping["case_id"]) != case_id:
            _issue(issues, role, "case_id", "candidate_mismatch")

    if isinstance(readiness_candidate, dict) and readiness_candidate:
        if _text(readiness_candidate.get("case_id")) != case_id:
            _issue(issues, "readiness", "case_id", "candidate_mismatch")
        supplied = tuple(field for field in RECIPE_FIELDS if field in readiness_candidate)
        observed = _recipe(readiness_candidate, supplied, "readiness", issues)
        for field, value in observed.items():
            if field in expected and value != expected[field]:
                _issue(issues, "readiness", field, "candidate_mismatch")
    if profile and _text(profile.get("case_id")) != case_id:
        _issue(issues, "profile", "case_id", "missing_or_candidate_mismatch")
    for field in WEIGHT_FIELDS:
        values: dict[str, float] = {}
        for role, request in requests.items():
            raw = request.get(field) if isinstance(request, dict) else None
            value = _number(raw)
            if value is None or value < 0:
                _issue(issues, role, field, "missing_or_invalid")
            else:
                values[role] = value
        if len(values) == 2 and values["signal"] != values["simulation"]:
            _issue(issues, "signal", field, "simulation_mismatch")
        for owner, mapping in (("profile", profile), ("candidate", candidate)):
            if field not in mapping:
                continue
            value = _number(mapping[field])
            if value is None or value < 0:
                _issue(issues, owner, field, "invalid")
            elif any(value != actual for actual in values.values()):
                _issue(issues, owner, field, "artifact_mismatch")
            break  # A bound selected profile supplies the active risk overlay.
    paper_request = requests["simulation"] if isinstance(requests["simulation"], dict) else {}
    if "risk_profile_id" in paper_request:
        expected_profile = _text(profile.get("profile_id"))
        actual_profile = _text(paper_request["risk_profile_id"])
        if expected_profile is None or actual_profile != expected_profile:
            _issue(issues, "simulation", "risk_profile_id", "profile_mismatch")
    for field in ("max_drawdown_guard", "guard_cooldown_periods"):
        owner = "profile" if field in profile else "candidate"
        active = profile if field in profile else candidate
        if field not in active:
            continue
        if field not in paper_request:
            _issue(issues, "simulation", field, "missing")
            continue
        expected_guard = _guard_value(field, active[field])
        actual_guard = _guard_value(field, paper_request[field])
        if not expected_guard[0]:
            _issue(issues, owner, field, "invalid")
        if not actual_guard[0] or expected_guard[1] != actual_guard[1]:
            _issue(issues, "simulation", field, "active_profile_mismatch")
    complete = len(expected) == len(RECIPE_FIELDS) and case_id is not None
    recipe_hash = hashlib.sha256(json.dumps(expected, sort_keys=True, separators=(",", ":")).encode()).hexdigest() if complete else None
    return {
        "status": "blocked" if issues else "recipe_matched",
        "candidate_case_id": case_id,
        "candidate_recipe_sha256": recipe_hash,
        "scope": "declared_recipe_consistency_only",
        "source_binding_verified": False,
        "research_admission_verified": False,
        "issues": issues,
        "blocking_reasons": ["daily_artifact_identity_invalid"] if issues else [],
    }


def _recipe(mapping: dict[str, Any], fields: tuple[str, ...], role: str, issues: list[dict[str, str]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in fields:
        value = mapping.get(field)
        if field == "factor_windows":
            parsed = _windows(value)
        elif field in {"top_n", "rebalance_interval"}:
            parsed = _positive_integer(value)
        else:
            parsed = _text(value)
            if parsed is not None and field == "market":
                parsed = parsed.upper()
        if parsed is None:
            _issue(issues, role, field, "missing_or_invalid")
        else:
            result[field] = parsed
    return result


def _windows(value: Any) -> list[int] | None:
    if isinstance(value, str):
        if len(value) > 4096:
            return None
        try:
            value = ast.literal_eval(value)
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            return None
    if not isinstance(value, (list, tuple)) or not value:
        return None
    parsed = [_positive_integer(item) for item in value]
    if any(item is None for item in parsed) or len(set(parsed)) != len(parsed):
        return None
    return parsed


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _positive_integer(value: Any) -> int | None:
    return _integer(value, 1)


def _integer(value: Any, minimum: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not number.is_finite() or number != number.to_integral_value() or not minimum <= number <= 2**63 - 1:
        return None
    return int(number)


def _guard_value(field: str, value: Any) -> tuple[bool, float | int | None]:
    if field == "guard_cooldown_periods":
        number = _integer(value, 0)
        return number is not None, number
    if value is None:
        return True, None
    number = _number(value)
    return number is not None and abs(number) <= 1, number


def _text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _issue(issues: list[dict[str, str]], role: str, field: str, reason: str) -> None:
    issues.append({"artifact": role, "field": field, "reason": reason})
