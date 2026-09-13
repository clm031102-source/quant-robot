"""Canonical identity of GUI paper requests, including declared fee scenarios."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PAPER_REQUEST_SIGNATURE_KEYS = (
    "source",
    "market",
    "factor_name",
    "factor_windows",
    "top_n",
    "rebalance_interval",
    "initial_cash",
    "commission_bps",
    "minimum_commission",
    "slippage_bps",
    "max_asset_weight",
    "max_market_weight",
    "max_gross_exposure",
    "min_cash_weight",
    "max_drawdown_guard",
    "guard_cooldown_periods",
    "as_of_date",
    "run_date",
    "same_parameter_lock_id",
    "same_parameter_request_id",
    "case_id",
    "risk_profile_id",
)

def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    return str(value)

def _request_signature(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        return {}
    source: dict[str, Any] = dict(request)
    if not source.get("factor_name") and source.get("factor") not in {None, ""}:
        source["factor_name"] = source.get("factor")
    signature: dict[str, Any] = {}
    for key in PAPER_REQUEST_SIGNATURE_KEYS:
        value = source.get(key)
        if value is None or value == "":
            continue
        signature[key] = _canonical_signature_value(key, value)
    # Omitted legacy GUI fees used zero. Do not turn an unrelated or empty
    # request into paper identity solely by adding this default.
    if signature and "minimum_commission" not in signature:
        signature["minimum_commission"] = 0.0
    return signature

def _signature_mismatch_keys(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    for key, expected_value in expected.items():
        if actual.get(key) != expected_value:
            mismatches.append(key)
    return mismatches

def _canonical_signature_value(key: str, value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 10)
    text = str(value).strip()
    if key == "market":
        return text.upper()
    if key == "factor_windows":
        if isinstance(value, (list, tuple)):
            return ",".join(str(item).strip() for item in value if str(item).strip())
        return text.replace(" ", "")
    if key in {
        "top_n",
        "rebalance_interval",
        "initial_cash",
        "commission_bps",
        "minimum_commission",
        "slippage_bps",
        "max_asset_weight",
        "max_market_weight",
        "max_gross_exposure",
        "min_cash_weight",
        "max_drawdown_guard",
        "guard_cooldown_periods",
    }:
        try:
            return round(float(text), 10)
        except ValueError:
            return text
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(_json_safe(value), sort_keys=True, ensure_ascii=False)
    return text
