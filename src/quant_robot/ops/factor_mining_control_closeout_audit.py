from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


STAGE = "factor_mining_control_closeout_audit"
SCOPE_EXEMPT_DIRECT_MINING_CONTROLS = {
    "cn_etf_dedicated_signal_pack_for_etf_rotation",
}

AREA_PRIORITY = {
    "cn_stock_tradeability": 120,
    "financial_pit_timing": 95,
    "portfolio_construction": 90,
    "industry_style_neutralization": 85,
    "china_market_regime": 80,
    "event_factors": 75,
    "strict_statistics": 70,
    "final_holdout_promotion_gate": 65,
    "etf_rotation_scope_boundary": 30,
}

STATUS_PENALTY = {
    "planned": 15,
    "partial": 5,
    "missing": 25,
}

DATA_READINESS_HINTS = (
    "official",
    "backfill",
    "point-in-time",
    "pit",
    "feed",
    "coverage",
    "available",
    "effective",
)


def build_factor_mining_control_closeout_audit(quality_gate: dict[str, Any] | None) -> dict[str, Any]:
    packet = _dict(quality_gate)
    policy = _dict(packet.get("research_execution_policy"))
    direct_blocker_ids = _direct_blocker_ids(policy)
    control_rows = _list_of_dicts(packet.get("control_rows"))
    priority_rows = _priority_rows(control_rows, direct_blocker_ids=direct_blocker_ids)
    direct_allowed = bool(policy.get("direct_factor_generation_allowed")) and not priority_rows
    status = "direct_mining_ready" if direct_allowed else "direct_mining_blocked"
    next_round_direction = _next_round_direction(priority_rows, direct_allowed=direct_allowed)
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": {
            "quality_gate_status": str(packet.get("status", "not_provided")),
            "direct_mining_blocker_count": len(direct_blocker_ids),
            "priority_count": len(priority_rows),
            "top_priority_area": priority_rows[0]["area_id"] if priority_rows else "",
            "top_priority_control": priority_rows[0]["control_id"] if priority_rows else "",
        },
        "priority_rows": priority_rows,
        "scope_exempt_controls": sorted(SCOPE_EXEMPT_DIRECT_MINING_CONTROLS),
        "decision": {
            "direct_factor_generation_allowed": direct_allowed,
            "next_round_direction": next_round_direction,
            "allowed_next_work_modes": _allowed_next_work_modes(priority_rows, direct_allowed=direct_allowed),
            "blockers": [row["blocker"] for row in priority_rows],
        },
    }


def write_factor_mining_control_closeout_audit(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean_packet = _sanitize(packet)
    (output_path / "factor_mining_control_closeout_audit.json").write_text(
        json.dumps(clean_packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "factor_mining_control_closeout_audit.md").write_text(
        render_markdown(clean_packet),
        encoding="utf-8",
    )


def render_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    lines = [
        "# Factor Mining Control Closeout Audit",
        "",
        f"- Stage: {packet.get('stage', STAGE)}",
        f"- Status: {packet.get('status', '')}",
        f"- Quality gate status: {summary.get('quality_gate_status', '')}",
        f"- Direct mining blocker count: {summary.get('direct_mining_blocker_count', 0)}",
        f"- Priority count: {summary.get('priority_count', 0)}",
        f"- Top priority area: {summary.get('top_priority_area', '')}",
        f"- Top priority control: {summary.get('top_priority_control', '')}",
        f"- Direct factor generation allowed: {decision.get('direct_factor_generation_allowed', False)}",
        f"- Next round direction: {decision.get('next_round_direction', '')}",
        "",
        "## Priority Rows",
        "",
        "| Rank | Area | Control | Status | Action type | Score | Next action |",
        "|---:|---|---|---|---|---:|---|",
    ]
    for row in _list_of_dicts(packet.get("priority_rows")):
        lines.append(
            "| {rank} | {area} | {control} | {status} | {action} | {score} | {next_action} |".format(
                rank=row.get("rank", ""),
                area=row.get("area_id", ""),
                control=row.get("control_id", ""),
                status=row.get("status", ""),
                action=row.get("action_type", ""),
                score=row.get("score", ""),
                next_action=row.get("next_action", ""),
            )
        )
    return "\n".join(lines) + "\n"


def _direct_blocker_ids(policy: dict[str, Any]) -> set[str]:
    blocker_ids: set[str] = set()
    for blocker in _list(policy.get("direct_mining_blockers")):
        prefix = "direct_mining_control_not_implemented:"
        if not blocker.startswith(prefix):
            continue
        control_id = blocker.removeprefix(prefix)
        if control_id in SCOPE_EXEMPT_DIRECT_MINING_CONTROLS:
            continue
        blocker_ids.add(control_id)
    return blocker_ids


def _priority_rows(control_rows: list[dict[str, Any]], *, direct_blocker_ids: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in control_rows:
        control_id = str(row.get("control_id", ""))
        if control_id not in direct_blocker_ids:
            continue
        area_id = str(row.get("area_id", ""))
        status = str(row.get("status", ""))
        score = AREA_PRIORITY.get(area_id, 50) + STATUS_PENALTY.get(status, 0)
        next_action = str(row.get("next_action", ""))
        rows.append(
            {
                "area_id": area_id,
                "control_id": control_id,
                "status": status,
                "evidence": str(row.get("evidence", "")),
                "next_action": next_action,
                "action_type": _action_type(next_action),
                "score": score,
                "blocker": f"direct_mining_control_not_implemented:{control_id}",
            }
        )
    rows.sort(key=lambda item: (-int(item["score"]), item["area_id"], item["control_id"]))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _action_type(next_action: str) -> str:
    lowered = next_action.lower()
    if any(hint in lowered for hint in DATA_READINESS_HINTS):
        return "data_readiness_audit"
    return "implementation_closeout"


def _next_round_direction(priority_rows: list[dict[str, Any]], *, direct_allowed: bool) -> str:
    if direct_allowed:
        return "direct_factor_generation_allowed_after_control_closeout"
    if not priority_rows:
        return "quality_gate_packet_missing_or_not_actionable"
    top_area = str(priority_rows[0].get("area_id", ""))
    if top_area == "cn_stock_tradeability":
        return "round198_continue_long_cycle_tradeability_backfill_until_manifest_coverage_then_mask_integration"
    if top_area == "financial_pit_timing":
        return "round195_close_financial_pit_timing_controls_before_direct_factor_generation"
    if top_area == "portfolio_construction":
        return "round195_close_portfolio_construction_controls_before_direct_factor_generation"
    return f"round195_close_{top_area}_controls_before_direct_factor_generation"


def _allowed_next_work_modes(priority_rows: list[dict[str, Any]], *, direct_allowed: bool) -> list[str]:
    if direct_allowed:
        return ["direct_factor_generation_with_candidate_plan_gate"]
    action_types = {str(row.get("action_type", "")) for row in priority_rows[:5]}
    modes = []
    if "data_readiness_audit" in action_types:
        modes.append("data_readiness_audit")
    if "implementation_closeout" in action_types:
        modes.append("quality_control_implementation")
    modes.append("candidate_preregistration_without_profit_claims")
    return _unique_preserving_order(modes)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, set):
        return sorted(str(item) for item in value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
