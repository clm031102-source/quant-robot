from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any


STAGE = "cn_stock_family_rotation_decision"
EXPECTED_STARTUP_NEXT_DIRECTION = "round161_rotate_after_tradeability_limit_event_proxy_prescreen_failure"
NEXT_PREREGISTRATION_DIRECTION = "round161_china_market_regime_temperature_preregistration"
SELECTED_FAMILY_ID = "china_market_regime_temperature_interaction"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
STARTUP_DIRECTION_BLOCKER = "startup_gate_not_pointing_to_round161_rotation"

REQUIRED_SELECTED_CONTROLS = [
    "lagged_market_temperature_state",
    "no_same_day_forward_label_leakage",
    "tradeability_filter_before_signal",
    "industry_style_residual_evaluation",
    "regime_coverage_by_signal_window",
    "multiple_testing_accounting",
    "no_portfolio_grid_before_residual_prescreen",
]

FAMILY_ROW_COLUMNS = [
    "family_id",
    "status",
    "score",
    "data_readiness",
    "novelty_vs_recent_failures",
    "reason",
    "next_action",
]


def default_round161_family_candidates() -> list[dict[str, Any]]:
    return [
        {
            "family_id": SELECTED_FAMILY_ID,
            "status": "eligible",
            "score": 92,
            "data_readiness": "ready_from_bars_amount_and_metadata",
            "novelty_vs_recent_failures": "new_control_axis_not_raw_single_stock_topn",
            "public_reference_tags": [
                "market_breadth",
                "liquidity_temperature",
                "cross_sectional_dispersion",
                "regime_conditioned_alpha",
            ],
            "required_controls": REQUIRED_SELECTED_CONTROLS,
            "reason": (
                "Uses lagged market-wide breadth, liquidity temperature, dispersion, and index-location proxies "
                "as ex-ante conditioning variables for stock cross-sectional signals. This directly addresses the "
                "China-market-regime control gap without reusing the failed moneyflow, RSRS, price-volume shock, "
                "PIT-event, or limit-event families."
            ),
            "next_action": NEXT_PREREGISTRATION_DIRECTION,
        },
        {
            "family_id": "tradeability_limit_events",
            "status": "hibernated",
            "score": 0,
            "data_readiness": "proxy_run_completed",
            "novelty_vs_recent_failures": "failed_round160",
            "reason": "Round160 tested 8 long-cycle limit/tradeability-event proxies and found 0 proxy research leads.",
            "next_action": "do_not_run_true_limit_feed_audit_or_portfolio_grid_after_zero_proxy_leads",
        },
        {
            "family_id": "price_volume_shock_reversal",
            "status": "hibernated",
            "score": 0,
            "data_readiness": "tested",
            "novelty_vs_recent_failures": "failed_round158",
            "reason": "Round158 produced 0 residual research leads after neutral prescreen.",
            "next_action": "no_parameter_tuning_after_zero_residual_leads",
        },
        {
            "family_id": "public_technical_failure_reversal",
            "status": "hibernated",
            "score": 0,
            "data_readiness": "tested",
            "novelty_vs_recent_failures": "failed_round156",
            "reason": "Round156 showed raw and industry-neutral IC survived, but residual alpha failed and RSRS references were redundant.",
            "next_action": "no_rsrs_or_public_technical_failure_reentry_without_new_mechanism",
        },
        {
            "family_id": "pit_profitability_event_revision",
            "status": "hibernated",
            "score": 0,
            "data_readiness": "partial_pit_data_available",
            "novelty_vs_recent_failures": "failed_round153",
            "reason": "Round153 controlled PIT/neutral IC prescreen found 0 research leads.",
            "next_action": "no_portfolio_grid_or_parameter_tuning_after_zero_neutral_leads",
        },
        {
            "family_id": "industry_relative_strength_breadth_bridge",
            "status": "hibernated",
            "score": 0,
            "data_readiness": "tool_exists",
            "novelty_vs_recent_failures": "failed_round69",
            "reason": "Round69 industry-breadth bridge had positive industry RankIC but only 52%-53% positive excess rate and 0 bridge candidates.",
            "next_action": "do_not_reuse_as_standalone_promotion_candidate",
        },
        {
            "family_id": "moneyflow_residual_regime",
            "status": "hibernated",
            "score": 0,
            "data_readiness": "tested_in_validation_profile",
            "novelty_vs_recent_failures": "earlier_validation_not_promotable",
            "reason": "Residual moneyflow/regime variants remained capacity/regime-local and not paper-ready in long-cycle validation.",
            "next_action": "do_not_reopen_as_single_family_lockin",
        },
        {
            "family_id": "external_macro_or_northbound_credit_feed",
            "status": "blocked_by_data_gap",
            "score": 35,
            "data_readiness": "not_verified_locally",
            "novelty_vs_recent_failures": "new_but_feed_dependent",
            "reason": "Potentially useful, but local processed data does not yet prove complete northbound, margin, or credit-cycle history.",
            "next_action": "audit_data_feed_before_factor_preregistration",
        },
    ]


def build_cn_stock_family_rotation_decision(
    startup_gate: dict[str, Any] | None,
    *,
    expected_startup_next_direction: str = EXPECTED_STARTUP_NEXT_DIRECTION,
    selected_family_id: str = SELECTED_FAMILY_ID,
    next_preregistration_direction: str = NEXT_PREREGISTRATION_DIRECTION,
    selected_required_controls: list[str] | None = None,
    family_candidates: list[dict[str, Any]] | None = None,
    candidate_plan_seed: dict[str, Any] | None = None,
    startup_direction_blocker: str | None = None,
) -> dict[str, Any]:
    startup = _dict(startup_gate)
    protocol = _dict(startup.get("repeatable_mining_protocol"))
    required_controls = list(selected_required_controls or REQUIRED_SELECTED_CONTROLS)
    candidate_rows = [dict(row) for row in (family_candidates or default_round161_family_candidates())]
    selected = next((row for row in candidate_rows if row.get("family_id") == selected_family_id), None)

    blockers: list[str] = []
    if startup.get("status") not in {"cleared", "research_ready", "classified"}:
        blockers.append("startup_gate_not_cleared")
    if protocol.get("next_direction") != expected_startup_next_direction:
        blockers.append(_startup_direction_blocker(expected_startup_next_direction, startup_direction_blocker))
    if selected is None:
        blockers.append(f"selected_family_unknown:{selected_family_id}")
    else:
        if selected.get("status") == "hibernated":
            blockers.append(f"selected_family_is_hibernated:{selected_family_id}")
        if selected.get("status") == "blocked_by_data_gap":
            blockers.append(f"selected_family_has_data_gap:{selected_family_id}")
        missing_controls = [
            control
            for control in required_controls
            if control not in _list(selected.get("required_controls"))
        ]
        if missing_controls:
            blockers.append("selected_family_missing_controls:" + ",".join(missing_controls))

    family_rows = []
    for row in candidate_rows:
        clean = {
            "family_id": str(row.get("family_id", "")),
            "status": str(row.get("status", "")),
            "score": int(row.get("score", 0) or 0),
            "data_readiness": str(row.get("data_readiness", "")),
            "novelty_vs_recent_failures": str(row.get("novelty_vs_recent_failures", "")),
            "public_reference_tags": _list(row.get("public_reference_tags")),
            "required_controls": _list(row.get("required_controls")),
            "reason": str(row.get("reason", "")),
            "next_action": str(row.get("next_action", "")),
        }
        if clean["family_id"] == selected_family_id and clean["status"] == "eligible" and not blockers:
            clean["status"] = "selected_for_preregistration"
        family_rows.append(clean)

    cleared = not blockers
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "startup_source_audit": protocol.get("source_audit", ""),
        "startup_next_direction": protocol.get("next_direction", ""),
        "summary": {
            "family_count": len(family_rows),
            "hibernated_family_count": sum(1 for row in family_rows if row["status"] == "hibernated"),
            "blocked_by_data_gap_family_count": sum(1 for row in family_rows if row["status"] == "blocked_by_data_gap"),
            "selected_family_count": sum(1 for row in family_rows if row["status"] == "selected_for_preregistration"),
        },
        "decision": {
            "rotation_decision_cleared": cleared,
            "selected_family": selected_family_id if selected is not None else "",
            "next_direction": next_preregistration_direction if cleared else "blocked_until_rotation_decision_clears",
            "research_preregistration_allowed": cleared,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "blockers": blockers,
        },
        "family_rows": family_rows,
        "candidate_plan_seed": (
            _dict(candidate_plan_seed)
            if cleared and candidate_plan_seed is not None
            else _candidate_plan_seed(
                selected_family_id=selected_family_id,
                next_preregistration_direction=next_preregistration_direction,
                selected_required_controls=required_controls,
            )
            if cleared
            else {}
        ),
        "safety": SAFETY,
        "live_boundary_allowed": False,
    }
    result["markdown"] = render_cn_stock_family_rotation_decision_markdown(result)
    return result


def write_cn_stock_family_rotation_decision(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "cn_stock_family_rotation_decision.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_stock_family_rotation_decision.md").write_text(
        render_cn_stock_family_rotation_decision_markdown(clean),
        encoding="utf-8",
    )
    with (output_path / "cn_stock_family_rotation_family_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FAMILY_ROW_COLUMNS)
        writer.writeheader()
        for row in _list_of_dicts(clean.get("family_rows")):
            writer.writerow({column: row.get(column, "") for column in FAMILY_ROW_COLUMNS})


def render_cn_stock_family_rotation_decision_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    decision = _dict(result.get("decision"))
    lines = [
        "# CN Stock Family Rotation Decision",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Startup source audit: `{result.get('startup_source_audit', '')}`",
        f"- Startup next direction: `{result.get('startup_next_direction', '')}`",
        f"- Selected family: `{decision.get('selected_family', '')}`",
        f"- Next direction: `{decision.get('next_direction', '')}`",
        f"- Rotation decision cleared: {decision.get('rotation_decision_cleared', False)}",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Families reviewed: {summary.get('family_count', 0)}",
        f"- Hibernated families: {summary.get('hibernated_family_count', 0)}",
        f"- Data-gap families: {summary.get('blocked_by_data_gap_family_count', 0)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Family Rows", "", "| Family | Status | Score | Data | Reason | Next Action |", "|---|---|---:|---|---|---|"])
    for row in _list_of_dicts(result.get("family_rows")):
        lines.append(
            "| {family} | {status} | {score} | {data} | {reason} | {next_action} |".format(
                family=row.get("family_id", ""),
                status=row.get("status", ""),
                score=row.get("score", 0),
                data=row.get("data_readiness", ""),
                reason=str(row.get("reason", "")).replace("|", "/"),
                next_action=row.get("next_action", ""),
            )
        )
    seed = _dict(result.get("candidate_plan_seed"))
    if seed:
        lines.extend(["", "## Candidate Plan Seed", ""])
        lines.append(f"- Family: `{seed.get('family', '')}`")
        lines.append(f"- Preregistration direction: `{seed.get('next_direction', '')}`")
        lines.append(f"- Candidate count: {len(_list(seed.get('candidate_ideas')))}")
        for idea in _list(seed.get("candidate_ideas")):
            lines.append(f"- `{idea}`")
    return "\n".join(lines) + "\n"


def _candidate_plan_seed(
    *,
    selected_family_id: str = SELECTED_FAMILY_ID,
    next_preregistration_direction: str = NEXT_PREREGISTRATION_DIRECTION,
    selected_required_controls: list[str] | None = None,
) -> dict[str, Any]:
    required_controls = list(selected_required_controls or REQUIRED_SELECTED_CONTROLS)
    if selected_family_id != SELECTED_FAMILY_ID or next_preregistration_direction != NEXT_PREREGISTRATION_DIRECTION:
        return {
            "family": selected_family_id,
            "next_direction": next_preregistration_direction,
            "mechanism": "Selected factor family must be preregistered before any portfolio grid or promotion claim.",
            "candidate_ideas": [],
            "mandatory_controls": required_controls,
            "promotion_policy": _default_promotion_policy(),
        }
    return {
        "family": SELECTED_FAMILY_ID,
        "next_direction": NEXT_PREREGISTRATION_DIRECTION,
        "mechanism": (
            "Lagged market-wide breadth, turnover/liquidity temperature, cross-sectional dispersion, and "
            "index-location proxies condition stock cross-sectional alpha instead of acting as standalone "
            "same-day return predictors."
        ),
        "candidate_ideas": [
            "regime_cold_liquidity_reversal_quality_20_5",
            "regime_hot_turnover_exhaustion_avoidance_10_5",
            "breadth_recovery_residual_momentum_20_10",
            "dispersion_high_lowvol_residual_reversal_20_5",
            "index_location_low_residual_value_liquidity_60_10",
            "market_temperature_state_interaction_composite_20_5",
        ],
        "mandatory_controls": required_controls,
        "promotion_policy": _default_promotion_policy(),
    }


def _default_promotion_policy() -> dict[str, bool]:
    return {
        "portfolio_grid_allowed_before_residual_prescreen": False,
        "promotion_allowed": False,
        "requires_long_cycle_replay": True,
        "requires_walk_forward": True,
        "requires_cost_capacity_gate": True,
        "requires_regime_coverage": True,
    }


def _startup_direction_blocker(expected_startup_next_direction: str, blocker: str | None) -> str:
    if blocker:
        return blocker
    if expected_startup_next_direction == EXPECTED_STARTUP_NEXT_DIRECTION:
        return STARTUP_DIRECTION_BLOCKER
    return f"startup_gate_not_pointing_to:{expected_startup_next_direction}"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [row for row in _list(value) if isinstance(row, dict)]


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value
