from __future__ import annotations

import ast
import json
import math
from collections.abc import Mapping
from typing import Any

VALUATION_MODEL = "daily_adjusted_close_v1"

EXECUTION_ECONOMICS_FIELDS = (
    "initial_cash", "commission_bps", "minimum_commission", "slippage_bps",
    "market_impact_bps", "max_participation_rate",
)


def normalize_execution_economics(value: Any) -> dict[str, Any]:
    """Read a complete, versioned cash/cost contract, including CSV representations."""
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            try:
                value = ast.literal_eval(value)
            except (ValueError, SyntaxError) as exc:
                raise ValueError("execution_economics must be a complete object") from exc
    if not isinstance(value, Mapping):
        raise ValueError("execution_economics must be a complete object")
    if (type(value.get("schema_version")) is not int or value.get("schema_version") != 2
            or value.get("commission_model") != "per_order_minimum_v1"
            or value.get("valuation_model") != VALUATION_MODEL):
        raise ValueError("execution_economics has an unsupported model or schema")
    unknown = set(value).difference({"schema_version", "commission_model", "valuation_model", *EXECUTION_ECONOMICS_FIELDS})
    if unknown:
        raise ValueError("execution_economics has unsupported fields: " + ", ".join(sorted(unknown)))
    result: dict[str, Any] = {"schema_version": 2, "commission_model": "per_order_minimum_v1", "valuation_model": VALUATION_MODEL}
    for field in EXECUTION_ECONOMICS_FIELDS:
        if field not in value:
            raise ValueError(f"execution_economics missing {field}")
        raw = value[field]
        if field == "max_participation_rate" and raw is None:
            result[field] = None
            continue
        try:
            number = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"execution_economics invalid {field}") from exc
        if isinstance(raw, bool) or not math.isfinite(number) or number < 0:
            raise ValueError(f"execution_economics invalid {field}")
        if field in {"initial_cash", "max_participation_rate"} and number <= 0:
            raise ValueError(f"execution_economics {field} must be positive")
        result[field] = number
    return result


def execution_economics_from_request(request: Mapping[str, Any]) -> dict[str, Any]:
    return normalize_execution_economics({
        "schema_version": 2, "commission_model": "per_order_minimum_v1",
        "valuation_model": request.get("valuation_model"),
        **{field: request[field] for field in EXECUTION_ECONOMICS_FIELDS if field in request},
    })


def paper_economics_match(row: Mapping[str, Any], request: Mapping[str, Any]) -> bool:
    try:
        expected = normalize_execution_economics(row.get("execution_economics"))
        declared = normalize_execution_economics(request.get("execution_economics"))
        actual = execution_economics_from_request(request)
    except ValueError:
        return False
    return expected == declared == actual
