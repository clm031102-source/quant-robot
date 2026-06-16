from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "research_family_scheduler"
PRIMARY_STATUSES = {"active", "exploratory"}
NON_PRIMARY_STATUSES = {"auxiliary_only", "deprecated", "paused", "retired", "rejected_as_primary"}


def load_research_family_config(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def build_research_family_schedule(config: dict[str, Any]) -> dict[str, Any]:
    policy = _dict(config.get("stop_loss_policy"))
    max_failure_rounds = _int(policy.get("max_repeated_failure_rounds"), 2)
    max_rescue_iterations = _int(policy.get("max_rescue_iterations"), 3)
    min_active = _int(config.get("min_active_primary_families"), 3)
    max_share = _float(config.get("max_budget_share_per_family"), 0.45)
    families = [_family_row(row, max_failure_rounds, max_rescue_iterations, max_share) for row in _list(config.get("families"))]
    active_primary = [row for row in families if row["primary_allocation_allowed"]]
    blockers = _blockers(families, active_primary, min_active)
    warnings = _warnings(families, active_primary)
    pack = {
        "stage": config.get("stage", STAGE),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "primary_market": config.get("primary_market", "CN_ETF"),
        "research_only": bool(config.get("research_only", True)),
        "policy": {
            "min_active_primary_families": min_active,
            "max_budget_share_per_family": max_share,
            "max_repeated_failure_rounds": max_failure_rounds,
            "max_rescue_iterations": max_rescue_iterations,
        },
        "summary": _summary(families, active_primary, blockers, warnings),
        "families": families,
        "allocation": _allocation(active_primary),
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": _next_actions(families, active_primary, blockers),
        "safety": {
            "research_only": True,
            "paper_only_next_step": True,
            "live_boundary_allowed": False,
        },
    }
    pack["markdown"] = render_research_family_schedule_markdown(pack)
    return _sanitize(pack)


def write_research_family_schedule(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "research_family_schedule_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "research_family_schedule_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("families", [])).to_csv(output_path / "research_family_schedule_families.csv", index=False)
    pd.DataFrame(pack.get("allocation", [])).to_csv(output_path / "research_family_schedule_allocation.csv", index=False)


def render_research_family_schedule_markdown(pack: dict[str, Any]) -> str:
    summary = _dict(pack.get("summary"))
    lines = [
        "# Research Family Scheduler",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Primary market: {pack.get('primary_market', 'CN_ETF')}",
        f"- Scheduler status: {summary.get('scheduler_status', 'unknown')}",
        f"- Active primary families: {summary.get('active_primary_families', 0)}",
        f"- Primary budget share: {_round(summary.get('primary_budget_share', 0.0))}",
        f"- Stop-lossed families: {summary.get('stop_lossed_families', 0)}",
        f"- Research only: {pack.get('research_only', True)}",
        f"- Live boundary allowed: {pack.get('safety', {}).get('live_boundary_allowed', False)}",
        "",
        "## Active Allocation",
        "",
    ]
    allocation = _list(pack.get("allocation"))
    if allocation:
        lines.extend(
            f"- {row.get('family_id')}: budget={_round(row.get('budget_share'))}, next={row.get('next_action')}"
            for row in allocation
            if isinstance(row, dict)
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Stop-Loss And Auxiliary Families", ""])
    stop_rows = [
        row
        for row in _list(pack.get("families"))
        if isinstance(row, dict) and (row.get("stop_loss_triggered") or row.get("status") in NON_PRIMARY_STATUSES)
    ]
    if stop_rows:
        lines.extend(
            f"- {row.get('family_id')}: status={row.get('status')}, primary_allowed={row.get('primary_allocation_allowed')}, "
            f"reasons={', '.join(_list(row.get('stop_loss_reasons')))}"
            for row in stop_rows
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = _list(pack.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    actions = _list(pack.get("next_actions"))
    lines.extend(f"- {row.get('action')}: {row.get('reason')}" for row in actions if isinstance(row, dict)) if actions else lines.append("- none")
    return "\n".join(lines) + "\n"


def _family_row(
    row: dict[str, Any],
    max_failure_rounds: int,
    max_rescue_iterations: int,
    max_share: float,
) -> dict[str, Any]:
    status = str(row.get("status", "active"))
    family_id = str(row.get("family_id", "unknown"))
    budget_share = _float(row.get("budget_share"), 0.0)
    failed_rounds = _int(row.get("failed_rounds"), 0)
    rescue_iterations = _int(row.get("rescue_iterations"), 0)
    failure_reasons = [str(reason) for reason in _list(row.get("failure_reasons"))]
    repeated_failure_reasons = [str(reason) for reason in _list(row.get("repeated_failure_reasons"))]
    stop_loss_reasons: list[str] = []
    if status in NON_PRIMARY_STATUSES:
        stop_loss_reasons.append(f"status_{status}")
    if failed_rounds >= max_failure_rounds and (failure_reasons or repeated_failure_reasons):
        stop_loss_reasons.append("research_family_stop_loss")
    if rescue_iterations >= max_rescue_iterations:
        stop_loss_reasons.append("rescue_iteration_limit_reached")
    if len(set(failure_reasons)) >= 3 and failed_rounds >= max_failure_rounds:
        stop_loss_reasons.append("repeated_failure_modes")
    if budget_share > max_share:
        stop_loss_reasons.append("budget_share_above_family_cap")
    primary_allowed = status in PRIMARY_STATUSES and not stop_loss_reasons and budget_share > 0.0
    allocation_status = "primary" if primary_allowed else "no_primary_allocation"
    if status == "auxiliary_only":
        allocation_status = "auxiliary_only"
    return {
        **row,
        "family_id": family_id,
        "status": status,
        "budget_share": budget_share,
        "failed_rounds": failed_rounds,
        "rescue_iterations": rescue_iterations,
        "failure_reasons": failure_reasons,
        "repeated_failure_reasons": repeated_failure_reasons,
        "stop_loss_triggered": bool(stop_loss_reasons),
        "stop_loss_reasons": _unique(stop_loss_reasons),
        "primary_allocation_allowed": primary_allowed,
        "allocation_status": allocation_status,
    }


def _blockers(families: list[dict[str, Any]], active_primary: list[dict[str, Any]], min_active: int) -> list[str]:
    blockers: list[str] = []
    if len(active_primary) < min_active:
        blockers.append("insufficient_active_research_families")
    for row in families:
        if row["status"] in NON_PRIMARY_STATUSES and _float(row.get("budget_share"), 0.0) > 0.0:
            blockers.append(f"{row['family_id']}_has_budget_after_downgrade")
        if row.get("stop_loss_triggered") and _float(row.get("budget_share"), 0.0) > 0.0:
            blockers.append(f"{row['family_id']}_stop_lossed_but_still_budgeted")
        if "budget_share_above_family_cap" in row.get("stop_loss_reasons", []):
            blockers.append(f"{row['family_id']}_budget_share_above_family_cap")
    return _unique(blockers)


def _warnings(families: list[dict[str, Any]], active_primary: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    budget_sum = sum(_float(row.get("budget_share"), 0.0) for row in active_primary)
    if budget_sum < 0.95:
        warnings.append("primary_budget_below_full_allocation")
    if budget_sum > 1.01:
        warnings.append("primary_budget_above_full_allocation")
    for row in families:
        if row.get("family_id") == "cn_stock_moneyflow_selection" and row.get("primary_allocation_allowed"):
            warnings.append("cn_stock_moneyflow_selection_should_not_be_primary")
    return _unique(warnings)


def _summary(
    families: list[dict[str, Any]],
    active_primary: list[dict[str, Any]],
    blockers: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    return {
        "scheduler_status": "blocked" if blockers else "ready",
        "family_count": len(families),
        "active_primary_families": len(active_primary),
        "primary_budget_share": sum(_float(row.get("budget_share"), 0.0) for row in active_primary),
        "stop_lossed_families": sum(1 for row in families if row.get("stop_loss_triggered")),
        "auxiliary_only_families": sum(1 for row in families if row.get("status") == "auxiliary_only"),
        "blocker_count": len(blockers),
        "warning_count": len(warnings),
    }


def _allocation(active_primary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "family_id": row.get("family_id"),
            "market": row.get("market"),
            "budget_share": row.get("budget_share"),
            "hypothesis_family": row.get("hypothesis_family"),
            "next_action": row.get("next_action"),
        }
        for row in sorted(active_primary, key=lambda item: (-_float(item.get("budget_share")), str(item.get("family_id"))))
    ]


def _next_actions(
    families: list[dict[str, Any]],
    active_primary: list[dict[str, Any]],
    blockers: list[str],
) -> list[dict[str, Any]]:
    if blockers:
        return [
            {
                "action": "fix_research_family_allocation",
                "reason": "Research family scheduling is blocked; do not start another factor batch until budget and stop-loss issues are resolved.",
            }
        ]
    actions = [
        {
            "action": "run_active_family_batch",
            "family_id": row.get("family_id"),
            "budget_share": row.get("budget_share"),
            "reason": str(row.get("next_action", "Run the next pre-registered hypothesis batch for this family.")),
        }
        for row in active_primary
    ]
    auxiliary = [row for row in families if row.get("status") == "auxiliary_only"]
    for row in auxiliary:
        actions.append(
            {
                "action": "keep_family_auxiliary_only",
                "family_id": row.get("family_id"),
                "budget_share": 0.0,
                "reason": str(row.get("next_action", "Use only as an auxiliary feature source, not as a primary research line.")),
            }
        )
    return actions


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _round(value: Any) -> float:
    return round(_float(value), 4)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Path):
        return str(value)
    return value
