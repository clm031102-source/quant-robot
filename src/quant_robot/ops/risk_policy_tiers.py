from __future__ import annotations

import math
from typing import Any


PHASE_5_4_STAGE = "phase_5_4_risk_tier_policy"
DEFAULT_PRIMARY_RISK_TIER = "capital_preservation"


DEFAULT_GROWTH_RISK_TIERS: tuple[dict[str, Any], ...] = (
    {
        "tier_id": "capital_preservation",
        "label": "Capital Preservation",
        "max_drawdown_limit": 0.20,
        "min_walk_forward_sharpe": 0.3,
        "min_relative_return": 0.0,
        "min_paper_sharpe": 0.5,
        "min_paper_calmar": 1.0,
        "min_total_return": 0.0,
        "min_trades": 20,
        "priority": 1,
    },
    {
        "tier_id": "balanced_growth",
        "label": "Balanced Growth",
        "max_drawdown_limit": 0.25,
        "min_walk_forward_sharpe": 0.3,
        "min_relative_return": 0.0,
        "min_paper_sharpe": 0.5,
        "min_paper_calmar": 1.0,
        "min_total_return": 0.0,
        "min_trades": 20,
        "priority": 2,
    },
    {
        "tier_id": "aggressive_growth",
        "label": "Aggressive Growth",
        "max_drawdown_limit": 0.30,
        "min_walk_forward_sharpe": 0.3,
        "min_relative_return": 0.0,
        "min_paper_sharpe": 0.5,
        "min_paper_calmar": 1.0,
        "min_total_return": 0.0,
        "min_trades": 20,
        "priority": 3,
    },
)


def normalize_risk_tiers(
    raw_tiers: Any,
    fallback_policy: dict[str, Any],
    primary_risk_tier: str | None = None,
) -> tuple[list[dict[str, Any]], str]:
    rows = raw_tiers if isinstance(raw_tiers, list | tuple) else []
    tiers = [_normalize_tier(row, index, fallback_policy) for index, row in enumerate(rows, start=1) if isinstance(row, dict)]
    tiers = sorted(tiers, key=lambda row: (_int(row.get("priority"), 999), str(row.get("tier_id"))))
    primary = primary_risk_tier or (tiers[0]["tier_id"] if tiers else DEFAULT_PRIMARY_RISK_TIER)
    return tiers, primary


def paper_calmar(total_return: Any, max_drawdown: Any) -> float:
    total = _float(total_return)
    drawdown = abs(min(_float(max_drawdown), 0.0))
    if drawdown == 0.0:
        return math.inf if total > 0.0 else 0.0
    return total / drawdown


def assign_risk_tier(
    tier_rejections: dict[str, list[str]],
    tiers: list[dict[str, Any]],
) -> tuple[list[str], str | None]:
    eligible = [tier["tier_id"] for tier in tiers if not tier_rejections.get(str(tier.get("tier_id")), [])]
    assigned = eligible[0] if eligible else None
    return eligible, assigned


def risk_tier_counts(rows: list[dict[str, Any]], tiers: list[dict[str, Any]]) -> dict[str, int]:
    counts = {str(tier["tier_id"]): 0 for tier in tiers}
    for row in rows:
        tier = row.get("risk_tier")
        if tier in counts:
            counts[str(tier)] += 1
    return counts


def tier_label(tiers: list[dict[str, Any]], tier_id: str | None) -> str | None:
    for tier in tiers:
        if tier.get("tier_id") == tier_id:
            return str(tier.get("label", tier_id))
    return tier_id


def _normalize_tier(raw: dict[str, Any], index: int, fallback: dict[str, Any]) -> dict[str, Any]:
    tier_id = str(raw.get("tier_id") or raw.get("id") or f"risk_tier_{index}")
    return {
        "tier_id": tier_id,
        "label": str(raw.get("label") or tier_id.replace("_", " ").title()),
        "max_drawdown_limit": -abs(_float(raw.get("max_drawdown_limit"), fallback.get("max_drawdown_limit", -0.2))),
        "min_walk_forward_sharpe": _float(
            raw.get("min_walk_forward_sharpe"),
            fallback.get("min_walk_forward_sharpe", 0.0),
        ),
        "min_relative_return": _float(raw.get("min_relative_return"), fallback.get("min_relative_return", 0.0)),
        "min_paper_sharpe": _float(raw.get("min_paper_sharpe"), fallback.get("min_paper_sharpe", 0.0)),
        "min_paper_calmar": _float(raw.get("min_paper_calmar", raw.get("min_calmar")), fallback.get("min_paper_calmar", 0.0)),
        "min_total_return": _float(raw.get("min_total_return"), fallback.get("min_total_return", 0.0)),
        "min_trades": _int(raw.get("min_trades"), fallback.get("min_trades", 0)),
        "priority": _int(raw.get("priority"), index),
    }


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default
