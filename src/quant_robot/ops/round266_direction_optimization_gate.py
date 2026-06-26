from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable


STAGE = "round266_direction_optimization_gate"
ROUND = 266
SELECTED_DIRECTION_ID = "data_source_availability_and_orthogonal_family_gate"
ROUND266_NEXT_DIRECTION = "round267_new_source_or_orthogonal_family_preregistration_after_round266_gate"
EXPECTED_STARTUP_NEXT_DIRECTION = "round266_rotate_after_public_tradeable_indicator_composite_residual_prescreen_failure"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

SOURCE_AUDITS = (
    "docs/research/cn_stock_round265_public_tradeable_indicator_composite_residual_prescreen_2026-06-26.md",
    "docs/research/cn_stock_round263_265_three_round_review_2026-06-26.md",
    "docs/research/cn_stock_round262_data_source_availability_and_direction_audit_2026-06-26.md",
)

DIRECTION_ROW_COLUMNS = (
    "direction_id",
    "status",
    "score",
    "action_type",
    "data_readiness",
    "novelty_vs_recent_failures",
    "reason",
    "next_action",
)

ELIGIBLE_STATUSES = {
    "eligible_control_implementation",
    "eligible_data_readiness",
    "eligible_preregistration",
}

BLOCKED_STATUSES = {
    "hibernated",
    "blocked_by_permission",
    "blocked_by_negative_evidence",
    "blocked_by_data_gap",
}


@dataclass(frozen=True)
class Round266DirectionRow:
    direction_id: str
    status: str
    score: int
    action_type: str
    data_readiness: str
    novelty_vs_recent_failures: str
    reason: str
    next_action: str
    required_controls: tuple[str, ...] = ()
    public_reference_tags: tuple[str, ...] = ()
    forbidden_continuations: tuple[str, ...] = ()


def default_round266_method_areas() -> list[dict[str, Any]]:
    return [
        {
            "area_id": "a_share_real_tradeability",
            "title": "A-share real trading constraints",
            "required_controls": [
                "limit_up_down_filter",
                "suspension_filter",
                "st_flag_filter",
                "new_listing_age_filter",
                "delisting_risk_filter",
                "board_permission_filter",
            ],
            "required_outputs": [
                "tradable_universe_mask",
                "blocked_signal_count",
                "limit_suspend_st_listing_board_breakout",
            ],
        },
        {
            "area_id": "financial_pit_timing",
            "title": "Point-in-time financial availability",
            "required_controls": [
                "announcement_date_or_revision_date_available_lag",
                "same_day_announcement_trading_block",
                "report_period_end_signal_block",
                "financial_stale_lag_gate",
            ],
            "required_outputs": [
                "ann_date",
                "available_date",
                "signal_date",
                "signal_lag_days",
                "revision_or_duplicate_key_audit",
            ],
        },
        {
            "area_id": "industry_style_neutralization",
            "title": "Industry and style neutral combination",
            "required_controls": [
                "industry_exposure_report",
                "size_value_lowvol_momentum_liquidity_decomposition",
                "neutralized_or_residual_factor_matrix",
                "reference_overlap_audit",
            ],
            "required_outputs": [
                "raw_ic",
                "industry_neutral_ic",
                "style_residual_ic",
                "reference_overlap",
                "style_exposure_breakout",
            ],
        },
        {
            "area_id": "cn_etf_rotation_boundary",
            "title": "CN ETF rotation boundary",
            "required_controls": [
                "cn_stock_scope_confirmation",
                "etf_rotation_evidence_separate",
                "cn_etf_signal_pack_not_reused_for_stock_factor",
            ],
            "required_outputs": [
                "stock_scope_confirmation",
                "etf_evidence_rejection_note",
                "separate_cn_etf_signal_pack_status",
            ],
        },
        {
            "area_id": "portfolio_construction",
            "title": "Portfolio construction beyond raw TopN",
            "required_controls": [
                "risk_budget_position_sizing",
                "volatility_budget",
                "industry_weight_constraints",
                "turnover_constraints",
                "drawdown_derisk_rule",
            ],
            "required_outputs": [
                "total_return",
                "annual_return",
                "profit_rate",
                "sharpe",
                "cost_adjusted_sharpe",
                "max_drawdown",
                "win_rate",
                "turnover",
                "capacity_usage",
            ],
        },
        {
            "area_id": "strict_statistics",
            "title": "Strict statistical reality checks",
            "required_controls": [
                "deflated_sharpe",
                "purged_cpcv",
                "white_reality_check_or_fdr",
                "parameter_sensitivity_heatmap",
                "overlap_adjusted_statistics",
                "final_holdout_readiness_gate",
            ],
            "required_outputs": [
                "deflated_sharpe",
                "cpcv_summary",
                "white_reality_check_or_fdr",
                "sensitivity_heatmap",
                "overlap_adjusted_sharpe",
                "final_holdout_status",
            ],
        },
        {
            "area_id": "china_market_regime",
            "title": "China market regime context",
            "required_controls": [
                "policy_liquidity_regime",
                "credit_cycle_proxy",
                "northbound_margin_turnover_temperature",
                "index_location_state",
                "allowed_and_blocked_regime_date_counts",
            ],
            "required_outputs": [
                "policy_liquidity_state",
                "credit_cycle_state",
                "flow_temperature_state",
                "index_location_state",
                "signal_window_regime_coverage",
            ],
        },
        {
            "area_id": "event_factors",
            "title": "Event factors and event contamination",
            "required_controls": [
                "earnings_forecast_or_statement_event_audit",
                "dividend_ex_right_event_audit",
                "buyback_holder_unlock_event_audit",
                "index_rebalance_event_audit",
                "event_contamination_extreme_return_audit",
            ],
            "required_outputs": [
                "event_available_date",
                "event_effective_date",
                "event_type",
                "event_signal_lag_days",
                "event_neutralized_ic",
            ],
        },
    ]


def default_round266_direction_rows() -> list[Round266DirectionRow]:
    controls = (
        "startup_gate_round266_state",
        "data_source_availability_proof",
        "blocked_family_reentry_audit",
        "candidate_plan_gate_before_prescreen",
        "full_sample_2015_2025_required",
        "2015_regime_and_reference_redundancy_diagnostic",
    )
    return [
        Round266DirectionRow(
            direction_id=SELECTED_DIRECTION_ID,
            status="eligible_control_implementation",
            score=96,
            action_type="pre_mining_control",
            data_readiness="uses_existing_reports_and_local_processed_catalog",
            novelty_vs_recent_failures="meta_gate_prevents_same_family_parameter_search",
            reason=(
                "After Round263-265 produced zero recoverable or residual leads, the next useful work is a hard "
                "direction gate. It allows only new PIT-safe source proof or a genuinely orthogonal hypothesis "
                "before factor generation."
            ),
            next_action=ROUND266_NEXT_DIRECTION,
            required_controls=controls,
            public_reference_tags=("alphalens", "mlfinlab_purged_cv", "white_reality_check", "deflated_sharpe"),
            forbidden_continuations=(
                "same_family_parameter_tuning_after_zero_residual_leads",
                "portfolio_grid_before_candidate_plan_gate",
                "single_metric_total_return_promotion",
            ),
        ),
        Round266DirectionRow(
            direction_id="financial_statement_full_coverage_pit_readiness",
            status="eligible_data_readiness",
            score=86,
            action_type="data_readiness_before_factor_generation",
            data_readiness="partial_statement_backfill_exists_but_direct_formula_mutations_failed",
            novelty_vs_recent_failures="data_engineering_only_not_realized_statement_formula_reentry",
            reason=(
                "Statement data can still be valuable, but direct realized statement formulas already failed. "
                "Only full-coverage PIT readiness or new external-expectation linkage may re-open this source."
            ),
            next_action="audit_statement_coverage_before_any_new_statement_factor",
            required_controls=controls,
            public_reference_tags=("accruals_anomaly", "earnings_quality", "asset_growth"),
        ),
        Round266DirectionRow(
            direction_id="external_expectation_event_feed_readiness",
            status="eligible_data_readiness",
            score=80,
            action_type="data_readiness_before_factor_generation",
            data_readiness="requires endpoint permission and cached event snapshot proof",
            novelty_vs_recent_failures="true_expectation_data_not_old_forecast_or_express_formula_grid",
            reason=(
                "Old forecast and express formulas were weak. A future expectation line needs a true source "
                "availability audit, not sign flips or guidance-range tuning."
            ),
            next_action="probe_true_expectation_or_event_snapshot_coverage_before_preregistration",
            required_controls=controls,
            public_reference_tags=("analyst_revision", "earnings_guidance", "event_study"),
        ),
        Round266DirectionRow(
            "public_tradeable_indicator_composite",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round265_full_sample",
            "failed_zero_residual_leads",
            "Round265 produced zero residual research leads after full 2015-2025 residual prescreen.",
            "do_not_tune_mfi_obv_supertrend_macd_rsi_parameters",
        ),
        Round266DirectionRow(
            "single_indicator_mfi_obv_supertrend_macd_rsi",
            "hibernated",
            0,
            "blocked_reentry",
            "covered_by_round264_265_composite_failure",
            "single_indicator_reentry_after_composite_failure",
            "Single public indicators are weaker reentries into the same failed public-indicator direction.",
            "do_not_run_single_indicator_grids",
        ),
        Round266DirectionRow(
            "low_turnover_repair",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round126_and_round263_recovery",
            "failed_walk_forward_and_recovery_audit",
            "High total return was blocked by overlap Sharpe, drawdown, extreme-trade, and walk-forward gates.",
            "do_not_reenter_low_turnover_without_new_capacity_mechanism",
        ),
        Round266DirectionRow(
            "daily_basic_direct_carry_value",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round257_full_sample",
            "fdr_ic_but_zero_strict_research_leads",
            "Daily-basic replay had IC evidence but failed shape, coverage, or strict research-lead gates.",
            "do_not_run_daily_basic_direct_portfolio_grid",
        ),
        Round266DirectionRow(
            "daily_basic_valuation_reversion_repair",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round258",
            "style_exposure_and_shape_failure",
            "Coverage repair did not fix residual retention and quantile-shape blockers.",
            "do_not_tune_valuation_reversion_weights",
        ),
        Round266DirectionRow(
            "listing_age_board_structural",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round259_full_sample",
            "zero_residual_leads",
            "Short-window diagnostics vanished in the 2015-2025 residual prescreen.",
            "do_not_tune_listing_age_or_board_thresholds",
        ),
        Round266DirectionRow(
            "official_tradeability_event_state",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round260_full_sample",
            "zero_residual_leads",
            "Official tradeability state remains a control, not a standalone alpha source.",
            "do_not_run_tradeability_event_portfolios",
        ),
        Round266DirectionRow(
            "industry_breadth_regime_translation",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round261_full_sample",
            "neutral_ic_residual_collapse",
            "Industry breadth is useful as regime/control context but not as direct stock alpha here.",
            "do_not_tune_breadth_windows",
        ),
        Round266DirectionRow(
            "event_contextual_underreaction",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round248_250",
            "raw_leads_removed_by_reference_residual_audit",
            "Apparent leads were explained by raw event and context-reference clusters.",
            "do_not_walk_forward_non_deduped_event_context_leads",
        ),
        Round266DirectionRow(
            "share_unlock_pledge_supply",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round251",
            "sparse_year_coverage_and_zero_leads",
            "Evidence was concentrated in too few years and failed size-neutral gates.",
            "do_not_run_unlock_or_pledge_direct_ranking",
        ),
        Round266DirectionRow(
            "forecast_guidance_uncertainty",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round256",
            "zero_research_leads",
            "Guidance confidence, uncertainty compression, and floor skew did not clear the PIT prescreen.",
            "do_not_expand_forecast_guidance_formulas",
        ),
        Round266DirectionRow(
            "public_reference_alpha101_main_force",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round252_and_round263",
            "quantile_shape_and_redundancy_failure",
            "Public Alpha101/main-force style leads failed quantile shape or redundancy checks.",
            "do_not_run_direct_public_reference_grids",
        ),
        Round266DirectionRow(
            "financial_statement_formula_mutations",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round244_247",
            "zero_neutral_gate_leads",
            "Realized statement formula mutations, including stress relief and profitability revision, failed.",
            "do_not_mutate_realized_statement_formulas_without_new_source",
        ),
        Round266DirectionRow(
            "index_rebalance_passive_flow",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round231",
            "zero_research_leads",
            "Opposite-sign diagnostics are not promotable after the zero-lead passive-flow test.",
            "do_not_flip_index_rebalance_direction",
        ),
        Round266DirectionRow(
            "dragon_tiger_attention_reversal",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round232_233",
            "zero_size_residual_repair_leads",
            "Direct and size-residual repair tests produced zero research leads.",
            "do_not_expand_dragon_tiger_windows",
        ),
        Round266DirectionRow(
            "liquidity_shock_recovery",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round230",
            "zero_residual_leads",
            "Liquidity shock recovery failed residual gates and should not receive window tuning.",
            "do_not_run_liquidity_shock_portfolios",
        ),
        Round266DirectionRow(
            "public_anomaly_residual_ensemble",
            "hibernated",
            0,
            "blocked_reentry",
            "tested_round229",
            "zero_residual_leads_and_high_exposure",
            "Fixed public anomaly ensemble had raw IC but no residual alpha.",
            "do_not_tune_public_anomaly_weights",
        ),
        Round266DirectionRow(
            "chip_distribution_stk_factor_ths_sw_daily",
            "blocked_by_permission",
            0,
            "blocked_data_source",
            "permission_blocked_round262",
            "endpoint_inaccessible",
            "Round262 found local Tushare permission blockers for chip/STK/THS/SW daily-style endpoints.",
            "do_not_generate_factors_from_permission_blocked_endpoints",
        ),
    ]


def build_round266_direction_optimization_gate(
    startup_gate: dict[str, Any] | None = None,
    *,
    selected_direction_id: str = SELECTED_DIRECTION_ID,
    direction_rows: Iterable[Round266DirectionRow | dict[str, Any]] | None = None,
    min_blocked_or_hibernated_directions: int = 10,
) -> dict[str, Any]:
    startup = _dict(startup_gate)
    rows = [_coerce_direction_row(row) for row in (direction_rows or default_round266_direction_rows())]
    method_areas = default_round266_method_areas()
    selected = next((row for row in rows if row.direction_id == selected_direction_id), None)
    blockers = _startup_blockers(startup)

    if selected is None:
        blockers.append(f"selected_direction_unknown:{selected_direction_id}")
    elif selected.status not in ELIGIBLE_STATUSES:
        blockers.append(f"selected_direction_not_eligible:{selected_direction_id}")

    blocked_count = sum(1 for row in rows if row.status in BLOCKED_STATUSES)
    if blocked_count < min_blocked_or_hibernated_directions:
        blockers.append("insufficient_negative_evidence_for_round266_rotation")

    if len(method_areas) < 8:
        blockers.append("method_optimization_area_count_below_required")

    cleared = not blockers
    result: dict[str, Any] = {
        "stage": STAGE,
        "round": ROUND,
        "generated_at": date.today().isoformat(),
        "source_audits": list(SOURCE_AUDITS),
        "summary": {
            "passes": cleared,
            "direction_count": len(rows),
            "method_area_count": len(method_areas),
            "blocked_or_hibernated_direction_count": blocked_count,
            "eligible_direction_count": sum(1 for row in rows if row.status in ELIGIBLE_STATUSES),
            "selected_direction": selected_direction_id,
            "selected_action_type": selected.action_type if selected else "",
        },
        "decision": {
            "direction_gate_cleared": cleared,
            "selected_direction": selected_direction_id if selected else "",
            "next_direction": ROUND266_NEXT_DIRECTION if cleared else "blocked_until_round266_direction_gate_clears",
            "direct_factor_generation_allowed": False,
            "candidate_plan_required_before_prescreen": True,
            "candidate_preregistration_allowed_after_new_source_proof": cleared,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "blockers": _unique_preserving_order(blockers),
        },
        "startup_context": {
            "status": startup.get("status", ""),
            "startup_next_direction": _dict(startup.get("repeatable_mining_protocol")).get("next_direction", ""),
            "round_state": _dict(startup.get("round_state")),
        },
        "method_area_rows": method_areas,
        "direction_rows": [_direction_payload(row, selected_direction_id=selected_direction_id, cleared=cleared) for row in rows],
        "next_candidate_plan_requirements": {
            "candidate_plan_gate_required": True,
            "minimum_requirements": [
                "new_or_repaired_pit_safe_data_source_proof",
                "not_in_hibernated_or_blocked_direction_rows",
                "full_sample_2015_2025_same_parameter_design",
                "2015_regime_and_reference_redundancy_diagnostic",
                "industry_style_residual_evaluation",
                "portfolio_and_promotion_blocked_until_later_gates",
            ],
            "forbidden_shortcuts": [
                "same_family_parameter_tuning_after_zero_leads",
                "direction_flip_after_failed_family",
                "raw_total_return_or_raw_sharpe_promotion",
                "short_window_only_screen",
                "portfolio_grid_before_candidate_plan_gate",
            ],
        },
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_round266_direction_optimization_gate_markdown(result)
    return result


def write_round266_direction_optimization_gate(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(result)
    (output_path / "round266_direction_optimization_gate.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "round266_direction_optimization_gate.md").write_text(
        render_round266_direction_optimization_gate_markdown(clean),
        encoding="utf-8",
    )
    with (output_path / "round266_direction_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(DIRECTION_ROW_COLUMNS))
        writer.writeheader()
        for row in _list_of_dicts(clean.get("direction_rows")):
            writer.writerow({column: row.get(column, "") for column in DIRECTION_ROW_COLUMNS})


def render_round266_direction_optimization_gate_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    decision = _dict(result.get("decision"))
    lines = [
        "# Round266 Direction Optimization Gate",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Round: {result.get('round', ROUND)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Selected direction: `{decision.get('selected_direction', '')}`",
        f"- Next direction: `{decision.get('next_direction', '')}`",
        f"- Direct factor generation allowed: {decision.get('direct_factor_generation_allowed', False)}",
        f"- Candidate plan required before prescreen: {decision.get('candidate_plan_required_before_prescreen', True)}",
        f"- Portfolio grid allowed: {decision.get('portfolio_grid_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Blocked or hibernated directions: {summary.get('blocked_or_hibernated_direction_count', 0)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Method Areas", "", "| Area | Controls | Outputs |", "|---|---|---|"])
    for row in _list_of_dicts(result.get("method_area_rows")):
        lines.append(
            "| {area} | {controls} | {outputs} |".format(
                area=row.get("area_id", ""),
                controls=", ".join(_list(row.get("required_controls"))),
                outputs=", ".join(_list(row.get("required_outputs"))),
            )
        )
    lines.extend(["", "## Direction Rows", "", "| Direction | Status | Score | Action | Reason | Next Action |", "|---|---|---:|---|---|---|"])
    for row in _list_of_dicts(result.get("direction_rows")):
        lines.append(
            "| {direction} | {status} | {score} | {action} | {reason} | {next} |".format(
                direction=row.get("direction_id", ""),
                status=row.get("status", ""),
                score=row.get("score", 0),
                action=row.get("action_type", ""),
                reason=str(row.get("reason", "")).replace("|", "/"),
                next=row.get("next_action", ""),
            )
        )
    requirements = _dict(result.get("next_candidate_plan_requirements"))
    lines.extend(["", "## Next Candidate Plan Requirements", ""])
    for item in _list(requirements.get("minimum_requirements")):
        lines.append(f"- {item}")
    lines.extend(["", "## Forbidden Shortcuts", ""])
    for item in _list(requirements.get("forbidden_shortcuts")):
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def _startup_blockers(startup: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not startup:
        return ["startup_gate_packet_missing"]
    if startup.get("status") not in {"cleared", "research_ready", "classified"}:
        blockers.append("startup_gate_not_cleared")
    protocol = _dict(startup.get("repeatable_mining_protocol"))
    if protocol.get("next_direction") != EXPECTED_STARTUP_NEXT_DIRECTION:
        blockers.append("startup_next_direction_not_round266")
    state = _dict(startup.get("round_state"))
    if int(state.get("next_round", -1) or -1) != ROUND:
        blockers.append("startup_round_state_not_round266")
    if int(state.get("last_completed_round", -1) or -1) != ROUND - 1:
        blockers.append("startup_last_completed_round_not_round265")
    if state.get("family_rotation_required") is not True:
        blockers.append("startup_family_rotation_not_required")
    required = set(_list(state.get("required_before_next_round")))
    for item in (
        "round266_rotate_to_new_orthogonal_family_required",
        "round266_candidate_plan_gate_required_before_any_prescreen",
    ):
        if item not in required:
            blockers.append(f"startup_missing_round266_requirement:{item}")
    return blockers


def _direction_payload(row: Round266DirectionRow, *, selected_direction_id: str, cleared: bool) -> dict[str, Any]:
    payload = asdict(row)
    payload["selected"] = bool(cleared and row.direction_id == selected_direction_id and row.status in ELIGIBLE_STATUSES)
    if payload["selected"]:
        payload["status"] = "selected_control_implementation"
    return payload


def _coerce_direction_row(value: Round266DirectionRow | dict[str, Any]) -> Round266DirectionRow:
    if isinstance(value, Round266DirectionRow):
        return value
    payload = dict(value)
    for key in ("required_controls", "public_reference_tags", "forbidden_continuations"):
        payload[key] = tuple(payload.get(key, ()))
    return Round266DirectionRow(**payload)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, tuple):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value
