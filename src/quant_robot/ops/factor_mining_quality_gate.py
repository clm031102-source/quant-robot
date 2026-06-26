from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


STAGE = "factor_mining_quality_gate"
ALLOWED_CONTROL_STATUSES = {"implemented", "partial", "planned", "not_applicable"}
PROMOTION_READY_STATUSES = {"implemented", "not_applicable"}
EVIDENCE_REQUIRED_STATUSES = {"implemented", "partial", "not_applicable"}
NEXT_ACTION_REQUIRED_STATUSES = {"partial", "planned"}
DIRECT_MINING_READY_STATUSES = {"implemented", "not_applicable"}
DIRECT_MINING_SCOPE_EXEMPT_CONTROLS = {
    "cn_etf_dedicated_signal_pack_for_etf_rotation",
}

DEFAULT_CN_STOCK_QUALITY_AREAS: list[dict[str, Any]] = [
    {
        "id": "cn_stock_tradeability",
        "title": "A-share real trading constraints",
        "why": "A CN stock factor cannot be promoted if returns come from names that were not tradable in reality.",
        "required_controls": [
            "limit_up_down_filter",
            "suspension_filter",
            "st_flag_filter",
            "new_listing_age_filter",
            "delisting_risk_filter",
            "board_permission_filter",
        ],
    },
    {
        "id": "financial_pit_timing",
        "title": "Point-in-time financial statement availability",
        "why": "Financial factors must use the date the information became tradable, not only the report period.",
        "required_controls": [
            "financial_statement_ann_date_lag",
            "financial_revision_announcement_handling",
            "report_release_lag_not_period_end",
        ],
    },
    {
        "id": "industry_style_neutralization",
        "title": "Industry and style neutralization",
        "why": "Apparent alpha must be separated from industry, size, value, low-vol, momentum, and liquidity exposure.",
        "required_controls": [
            "industry_exposure_report",
            "style_exposure_report",
            "size_value_lowvol_momentum_liquidity_decomposition",
            "neutralized_factor_matrix_or_residual_option",
        ],
    },
    {
        "id": "etf_rotation_scope_boundary",
        "title": "ETF rotation signal boundary",
        "why": "CN stock mining and ETF rotation need separate evidence, universes, and signal packs.",
        "required_controls": [
            "stock_vs_etf_scope_boundary",
            "cn_etf_dedicated_signal_pack_for_etf_rotation",
        ],
    },
    {
        "id": "portfolio_construction",
        "title": "Portfolio construction beyond raw TopN",
        "why": "A factor should survive realistic construction, not only a raw ranking table.",
        "required_controls": [
            "risk_budget_position_sizing",
            "volatility_targeting",
            "industry_weight_constraints",
            "turnover_constraints",
            "stop_loss_or_de_risk_rules",
        ],
    },
    {
        "id": "strict_statistics",
        "title": "Strict statistical reality checks",
        "why": "Single best parameters are not evidence after repeated searches.",
        "required_controls": [
            "deflated_sharpe",
            "cpcv_purged_cross_validation",
            "white_reality_check_or_fdr",
            "parameter_sensitivity_heatmap",
        ],
    },
    {
        "id": "final_holdout_promotion_gate",
        "title": "Final-holdout promotion gate",
        "why": "Aggregate walk-forward acceptance is not enough when the read-once final holdout fails.",
        "required_controls": [
            "final_holdout_readiness_audit",
            "final_holdout_result_audit",
        ],
    },
    {
        "id": "china_market_regime",
        "title": "China market regime context",
        "why": "A-share performance must be audited across policy, credit, flow, liquidity, and index-location regimes.",
        "required_controls": [
            "policy_liquidity_regime",
            "credit_cycle_proxy",
            "northbound_margin_turnover_temperature",
            "index_location_state",
        ],
    },
    {
        "id": "event_factors",
        "title": "Event-factor coverage",
        "why": "Corporate events can be real alpha sources or hidden data/event contamination.",
        "required_controls": [
            "earnings_forecast_events",
            "dividend_ex_right_events",
            "buyback_holder_change_unlock_events",
            "index_rebalance_events",
        ],
    },
]


def required_control_ids(areas: list[dict[str, Any]] | None = None) -> list[str]:
    return _unique_preserving_order(
        control_id
        for area in (areas or DEFAULT_CN_STOCK_QUALITY_AREAS)
        for control_id in _list(area.get("required_controls"))
    )


def build_factor_mining_quality_gate(config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = _dict(config)
    areas = _areas(config)
    configured_status = _dict(config.get("control_status"))
    evidence = _dict(config.get("control_evidence"))
    next_actions = _dict(config.get("control_next_actions"))
    normalized_status: dict[str, str] = {}
    blockers: list[str] = []
    promotion_blockers: list[str] = []
    control_rows: list[dict[str, str]] = []
    missing_evidence_count = 0
    missing_next_action_count = 0

    for area in areas:
        for control_id in _list(area.get("required_controls")):
            status = str(configured_status.get(control_id, "")).strip().lower()
            evidence_text = str(evidence.get(control_id, "")).strip()
            next_action_text = str(next_actions.get(control_id, "")).strip()
            if not status:
                blockers.append(f"missing_quality_control:{control_id}")
                normalized_status[control_id] = "missing"
            elif status not in ALLOWED_CONTROL_STATUSES:
                blockers.append(f"invalid_quality_control_status:{control_id}:{status}")
                normalized_status[control_id] = status
            else:
                normalized_status[control_id] = status
                if status in EVIDENCE_REQUIRED_STATUSES and not evidence_text:
                    blockers.append(f"missing_quality_control_evidence:{control_id}")
                    missing_evidence_count += 1
                if status in NEXT_ACTION_REQUIRED_STATUSES and not next_action_text:
                    blockers.append(f"missing_quality_control_next_action:{control_id}")
                    missing_next_action_count += 1
                if status not in PROMOTION_READY_STATUSES:
                    promotion_blockers.append(f"promotion_control_not_implemented:{control_id}")
            control_rows.append(
                {
                    "area_id": str(area.get("id", "")),
                    "control_id": control_id,
                    "status": normalized_status[control_id],
                    "evidence": evidence_text,
                    "next_action": next_action_text,
                }
            )

    summary = _summary(normalized_status)
    research_execution_policy = _research_execution_policy(
        normalized_status,
        startup_blockers=blockers,
        promotion_blockers=promotion_blockers,
    )
    if blockers:
        status = "blocked"
    elif promotion_blockers:
        status = "classified"
    else:
        status = "promotion_ready"
    return {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": {
            "scope_id": str(config.get("scope_id", "cn_stock_factor_mining_round142")),
            "market": str(config.get("market", "CN")),
            "asset_type": str(config.get("asset_type", "stock")),
            **summary,
            "missing_evidence_controls": missing_evidence_count,
            "missing_next_action_controls": missing_next_action_count,
        },
        "quality_areas": _annotated_areas(areas, normalized_status, evidence, next_actions),
        "control_status": normalized_status,
        "control_evidence": evidence,
        "control_next_actions": next_actions,
        "control_rows": control_rows,
        "research_execution_policy": research_execution_policy,
        "decision": {
            "startup_gate_cleared": not blockers,
            "promotion_gate_cleared": not blockers and not promotion_blockers,
            "blockers": blockers,
            "promotion_blockers": promotion_blockers,
        },
    }


def validate_quality_gate_for_startup(
    packet_path: str | Path | None,
    *,
    expected_market: str = "CN",
    expected_asset_type: str = "stock",
    require_generated_today: bool = True,
    context: str = "CN stock factor mining",
) -> dict[str, Any]:
    if packet_path is None:
        raise ValueError(f"{context} requires a cleared quality gate packet")
    path = Path(packet_path)
    if not path.exists():
        raise ValueError(f"{context} requires a cleared quality gate packet: {path}")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if require_generated_today and packet.get("generated_at") != date.today().isoformat():
        raise ValueError(f"{context} quality gate packet must be generated today: {path}")
    decision = _dict(packet.get("decision"))
    if packet.get("status") == "blocked" or decision.get("startup_gate_cleared") is not True:
        raise ValueError(f"{context} quality gate is not cleared: {path}")
    summary = _dict(packet.get("summary"))
    if str(summary.get("market", "")).upper() != expected_market.upper():
        raise ValueError(f"{context} quality gate market mismatch: {path}")
    if str(summary.get("asset_type", "")).lower() != expected_asset_type.lower():
        raise ValueError(f"{context} quality gate asset type mismatch: {path}")
    return packet


def render_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    lines = [
        "# CN Stock Factor Mining Quality Gate",
        "",
        f"- Stage: {packet.get('stage', STAGE)}",
        f"- Status: {packet.get('status', 'unknown')}",
        f"- Scope: {summary.get('scope_id')}",
        f"- Market: {summary.get('market')}",
        f"- Asset type: {summary.get('asset_type')}",
        f"- Controls: {summary.get('total_controls', 0)}",
        f"- Implemented: {summary.get('implemented_controls', 0)}",
        f"- Partial: {summary.get('partial_controls', 0)}",
        f"- Planned: {summary.get('planned_controls', 0)}",
        f"- Missing: {summary.get('missing_controls', 0)}",
        f"- Missing evidence controls: {summary.get('missing_evidence_controls', 0)}",
        f"- Missing next-action controls: {summary.get('missing_next_action_controls', 0)}",
        f"- Startup cleared: {decision.get('startup_gate_cleared', False)}",
        f"- Promotion cleared: {decision.get('promotion_gate_cleared', False)}",
        "",
        "## Research Execution Policy",
        "",
        f"- Candidate preregistration allowed: {_dict(packet.get('research_execution_policy')).get('candidate_preregistration_allowed', False)}",
        f"- Data coverage audit allowed: {_dict(packet.get('research_execution_policy')).get('data_coverage_audit_allowed', False)}",
        f"- Direct factor generation allowed: {_dict(packet.get('research_execution_policy')).get('direct_factor_generation_allowed', False)}",
        f"- Portfolio grid allowed by quality gate: {_dict(packet.get('research_execution_policy')).get('portfolio_grid_allowed_by_quality_gate', False)}",
        f"- Promotion review allowed by quality gate: {_dict(packet.get('research_execution_policy')).get('promotion_review_allowed_by_quality_gate', False)}",
        f"- Allowed next work modes: {', '.join(_list(_dict(packet.get('research_execution_policy')).get('allowed_next_work_modes')))}",
        f"- Blocked next work modes: {', '.join(_list(_dict(packet.get('research_execution_policy')).get('blocked_next_work_modes')))}",
        f"- Direct mining blockers: {', '.join(_list(_dict(packet.get('research_execution_policy')).get('direct_mining_blockers'))) or 'none'}",
        "",
        "## Areas",
        "",
    ]
    for area in _list_of_dicts(packet.get("quality_areas")):
        lines.extend(
            [
                f"### {area.get('id')}",
                "",
                f"- Title: {area.get('title')}",
                f"- Why: {area.get('why')}",
                f"- Implemented: {area.get('implemented_controls', 0)}",
                f"- Partial: {area.get('partial_controls', 0)}",
                f"- Planned: {area.get('planned_controls', 0)}",
                f"- Missing: {area.get('missing_controls', 0)}",
                "",
                "| Control | Status | Evidence | Next action |",
                "| --- | --- | --- | --- |",
            ]
        )
        for row in _list_of_dicts(area.get("controls")):
            lines.append(
                f"| {row.get('control_id')} | {row.get('status')} | "
                f"{row.get('evidence', '')} | {row.get('next_action', '')} |"
            )
        lines.append("")
    lines.extend(["## Startup Blockers", ""])
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Promotion Blockers", ""])
    promotion_blockers = _list(decision.get("promotion_blockers"))
    lines.extend(f"- {blocker}" for blocker in promotion_blockers) if promotion_blockers else lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _areas(config: dict[str, Any]) -> list[dict[str, Any]]:
    custom_areas = _list_of_dicts(config.get("quality_areas"))
    return custom_areas or DEFAULT_CN_STOCK_QUALITY_AREAS


def _annotated_areas(
    areas: list[dict[str, Any]],
    status_by_control: dict[str, str],
    evidence_by_control: dict[str, Any],
    next_action_by_control: dict[str, Any],
) -> list[dict[str, Any]]:
    annotated = []
    for area in areas:
        controls = [
            {
                "control_id": control_id,
                "status": status_by_control.get(control_id, "missing"),
                "evidence": str(evidence_by_control.get(control_id, "")).strip(),
                "next_action": str(next_action_by_control.get(control_id, "")).strip(),
            }
            for control_id in _list(area.get("required_controls"))
        ]
        annotated.append(
            {
                "id": str(area.get("id", "")),
                "title": str(area.get("title", "")),
                "why": str(area.get("why", "")),
                "required_controls": _list(area.get("required_controls")),
                "controls": controls,
                **_summary({row["control_id"]: row["status"] for row in controls}),
            }
        )
    return annotated


def _summary(status_by_control: dict[str, str]) -> dict[str, int]:
    return {
        "total_controls": len(status_by_control),
        "implemented_controls": sum(1 for status in status_by_control.values() if status == "implemented"),
        "partial_controls": sum(1 for status in status_by_control.values() if status == "partial"),
        "planned_controls": sum(1 for status in status_by_control.values() if status == "planned"),
        "not_applicable_controls": sum(1 for status in status_by_control.values() if status == "not_applicable"),
        "missing_controls": sum(1 for status in status_by_control.values() if status == "missing"),
    }


def _research_execution_policy(
    status_by_control: dict[str, str],
    *,
    startup_blockers: list[str],
    promotion_blockers: list[str],
) -> dict[str, Any]:
    direct_mining_blockers = [
        f"direct_mining_control_not_implemented:{control_id}"
        for control_id, status in status_by_control.items()
        if status not in DIRECT_MINING_READY_STATUSES and control_id not in DIRECT_MINING_SCOPE_EXEMPT_CONTROLS
    ]
    startup_cleared = not startup_blockers
    direct_factor_generation_allowed = startup_cleared and not direct_mining_blockers
    promotion_ready = startup_cleared and not promotion_blockers
    allowed_next_work_modes: list[str] = []
    blocked_next_work_modes: list[str] = []
    if startup_cleared:
        allowed_next_work_modes.extend(
            [
                "quality_control_implementation",
                "data_coverage_audit",
                "candidate_preregistration_without_profit_claims",
            ]
        )
    if direct_factor_generation_allowed:
        allowed_next_work_modes.append("factor_generation_with_full_pre_mining_controls")
    else:
        blocked_next_work_modes.extend(
            [
                "direct_parameter_grid_mining",
                "fresh_factor_screen_without_control_closeout",
            ]
        )
    if promotion_ready:
        allowed_next_work_modes.append("promotion_review_after_candidate_gate_and_walk_forward")
    else:
        blocked_next_work_modes.extend(["portfolio_grid", "promotion_claim"])
    return {
        "candidate_preregistration_allowed": startup_cleared,
        "data_coverage_audit_allowed": startup_cleared,
        "direct_factor_generation_allowed": direct_factor_generation_allowed,
        "portfolio_grid_allowed_by_quality_gate": direct_factor_generation_allowed and promotion_ready,
        "promotion_review_allowed_by_quality_gate": promotion_ready,
        "allowed_next_work_modes": _unique_preserving_order(allowed_next_work_modes),
        "blocked_next_work_modes": _unique_preserving_order(blocked_next_work_modes),
        "direct_mining_blockers": direct_mining_blockers,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _unique_preserving_order(items: Any) -> list[str]:
    seen: set[str] = set()
    unique = []
    for item in items:
        text = str(item)
        if text in seen:
            continue
        seen.add(text)
        unique.append(text)
    return unique
