from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from quant_robot.ops.factor_mining_quality_gate import build_factor_mining_quality_gate


STAGE = "factor_mining_startup_gate"
SAFETY_TEXT = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
REQUIRED_RESEARCH_OBJECTIVE = "cn_stock_cross_sectional_alpha"
DEFAULT_AUDIT_REPORT = "data/reports/cn_stock_factor_mining_20260617_batch_audit.md"
DEFAULT_NEXT_DIRECTION = "factor_validation_required_for_daily_champion_oos_candidates"
REQUIRED_LONG_CYCLE_STAGE = "long_cycle_replay"
REQUIRED_LONG_CYCLE_DESIGN_ITEMS = [
    "long_cycle_same_parameter_replay",
    "same_parameter_full_sample_diagnostic",
    "rolling_walk_forward_train_test_split",
    "walk_forward_progress_audit",
    "market_regime_coverage",
    "market_regime_signal_window_coverage",
    "lookahead_bias_audit",
    "overfit_multiple_testing_audit",
    "source_performance_evidence_required",
    "source_evidence_status_gate",
]
REQUIRED_LONG_CYCLE_CONFIRMATIONS = [
    "same_parameter_full_sample_enabled",
    "promotion_progress_audit_gate_enabled",
    "market_regime_coverage_enabled",
    "market_regime_signal_window_coverage_enabled",
    "lookahead_bias_audit_enabled",
    "overfit_multiple_testing_audit_enabled",
    "source_performance_evidence_gate_enabled",
    "promotion_source_evidence_gate_enabled",
]
REQUIRED_ROUND_GOVERNANCE_DESIGN_ITEMS = [
    "round_number_tracking",
    "three_round_review_audit",
    "ten_round_result_packaging",
    "three_round_review_after_every_three_factor_batches",
    "ten_round_github_sync_after_every_ten_factor_batches",
    "public_reference_method_check",
    "waste_budget_stop_loss",
]
REQUIRED_ROUND_GOVERNANCE_CONFIRMATIONS = [
    "three_round_review_gate_enabled",
    "ten_round_github_sync_gate_enabled",
    "three_round_review_cadence_confirmed",
    "ten_round_github_sync_cadence_confirmed",
    "public_reference_method_cadence_confirmed",
    "budget_stop_loss_cadence_confirmed",
    "public_reference_method_review_enabled",
    "waste_budget_stop_loss_enabled",
]
REQUIRED_TRANSLATION_LAYER_DESIGN_ITEMS = [
    "ic_to_portfolio_gap_audit_before_topn_expansion",
    "industry_neutral_ic_audit_for_stock_factors",
    "translation_layer_required_after_strong_ic_rejection",
    "bottom_exclusion_overlay_audit_for_strong_ic_rejected_topn",
    "bottom_exclusion_costed_walk_forward_before_promotion",
]
REQUIRED_TRANSLATION_LAYER_CONFIRMATIONS = [
    "ic_to_portfolio_gap_audit_read",
    "industry_neutral_ic_audit_enabled",
    "translation_layer_plan_registered",
    "bottom_exclusion_overlay_audit_read",
    "bottom_exclusion_costed_walk_forward_registered",
]
REQUIRED_ROUND142_QUALITY_GATE_DESIGN_ITEMS = [
    "round142_quality_gate_classification_before_factor_mining",
    "quality_gate_evidence_next_action_ledger",
    "cn_stock_tradeability_controls_required",
    "financial_pit_timing_controls_required",
    "industry_style_neutralization_controls_required",
    "etf_rotation_scope_boundary_required",
    "portfolio_construction_controls_required",
    "strict_statistics_controls_required",
    "china_market_regime_controls_required",
    "event_factor_controls_required",
]
REQUIRED_ROUND142_QUALITY_GATE_CONFIRMATIONS = [
    "round142_quality_gate_reviewed_before_each_run",
    "quality_gate_evidence_next_actions_confirmed",
    "quality_gate_startup_classification_cleared",
    "quality_gate_promotion_blockers_acknowledged",
]
REQUIRED_CANDIDATE_PLAN_CONTROL_DESIGN_ITEMS = [
    "candidate_plan_control_gate_before_factor_generation",
    "candidate_plan_gate_packet_required_by_mining_entrypoints",
    "candidate_hypothesis_source_required_before_generation",
    "candidate_strict_promotion_policy_before_screening",
    "real_tradeability_controls_declared_before_mining",
    "pit_availability_lag_controls_declared_before_mining",
    "industry_style_neutralization_controls_declared_before_mining",
    "etf_rotation_scope_boundary_declared_before_mining",
    "portfolio_construction_controls_declared_before_portfolio_grid",
    "strict_statistics_controls_declared_before_result_ranking",
    "china_regime_controls_declared_before_walk_forward",
    "event_or_event_contamination_controls_declared_before_promotion",
]
REQUIRED_CANDIDATE_PLAN_CONTROL_CONFIRMATIONS = [
    "candidate_plan_control_gate_enabled",
    "candidate_plan_gate_packet_validated_before_factor_generation",
    "candidate_hypothesis_source_declared",
    "candidate_strict_promotion_policy_declared",
    "real_tradeability_controls_declared",
    "pit_availability_lag_controls_declared",
    "industry_style_neutralization_controls_declared",
    "etf_rotation_scope_boundary_declared",
    "portfolio_construction_controls_declared",
    "strict_statistics_controls_declared",
    "china_regime_controls_declared",
    "event_or_event_contamination_controls_declared",
]
REQUIRED_RESEARCH_EXECUTION_POLICY_DESIGN_ITEMS = [
    "quality_gate_research_execution_policy_before_mining",
    "direct_factor_generation_blocked_until_pre_mining_controls_ready",
    "candidate_preregistration_without_profit_claims_when_controls_incomplete",
]
REQUIRED_RESEARCH_EXECUTION_POLICY_CONFIRMATIONS = [
    "research_execution_policy_reviewed_before_factor_generation",
    "direct_factor_generation_policy_confirmed",
    "candidate_preregistration_only_when_controls_incomplete_confirmed",
]
REQUIRED_TRADEABILITY_DATA_READINESS_DESIGN_ITEMS = [
    "tradeability_data_readiness_audit_before_direct_factor_generation",
    "official_limit_suspend_st_delist_feeds_required_before_direct_mining",
    "official_tradeability_feed_coverage_manifest_required_before_direct_mining",
    "proxy_tradeability_signals_not_promotable_without_official_feed",
]
REQUIRED_TRADEABILITY_DATA_READINESS_CONFIRMATIONS = [
    "tradeability_data_readiness_audit_read",
    "official_tradeability_feeds_confirmed_before_direct_mining",
    "official_tradeability_feed_coverage_manifest_confirmed",
    "proxy_tradeability_blockers_acknowledged",
]
REQUIRED_TRADEABILITY_MASK_CACHE_DESIGN_ITEMS = [
    "year_sliced_tradeability_mask_cache_before_old_candidate_replay",
    "full_window_tradeability_mask_cache_required_before_new_profit_claims",
    "short_window_mask_cache_smoke_not_promotion_evidence",
    "tradeability_mask_cache_cross_year_namechange_interval_check",
    "tradeability_cache_direct_equivalence_check_before_profit_claims",
    "tradeability_mask_cache_stock_basic_l_d_p_status_required",
    "tradeability_mask_cache_metadata_blocker_counts_required",
]
REQUIRED_TRADEABILITY_MASK_CACHE_CONFIRMATIONS = [
    "tradeability_mask_cache_full_window_confirmed",
    "old_candidate_replay_uses_precomputed_tradeability_mask_cache",
    "short_window_smoke_rejected_as_profitability_evidence",
    "tradeability_mask_cache_cross_year_namechange_confirmed",
    "tradeability_cache_direct_equivalence_confirmed",
    "tradeability_mask_cache_stock_basic_l_d_p_confirmed",
    "tradeability_mask_cache_metadata_blockers_confirmed",
]
REQUIRED_FINANCIAL_PIT_TIMING_AUDIT_DESIGN_ITEMS = [
    "financial_pit_timing_audit_before_financial_factor_generation",
    "financial_signal_lag_stale_threshold_required",
    "financial_exact_duplicate_key_blocker_required",
    "financial_revision_distinct_ann_date_preservation_required",
]
REQUIRED_FINANCIAL_PIT_TIMING_AUDIT_CONFIRMATIONS = [
    "financial_pit_timing_audit_confirmed",
    "financial_stale_or_unmapped_signal_rows_blocked",
    "financial_exact_duplicate_keys_blocked",
    "financial_same_day_announcement_trading_rejected",
]
REQUIRED_PORTFOLIO_POLICY_GATE_DESIGN_ITEMS = [
    "portfolio_construction_policy_gate_before_portfolio_grid",
    "portfolio_required_metric_pack_before_promotion",
    "portfolio_risk_budget_constraints_required",
    "portfolio_drawdown_derisk_policy_required",
]
REQUIRED_PORTFOLIO_POLICY_GATE_CONFIRMATIONS = [
    "portfolio_construction_policy_gate_confirmed",
    "portfolio_grid_without_policy_gate_rejected",
    "portfolio_required_metric_pack_confirmed",
    "portfolio_drawdown_tolerance_not_capacity_waiver_confirmed",
]
REQUIRED_INDUSTRY_STYLE_EXPOSURE_AUDIT_DESIGN_ITEMS = [
    "industry_style_exposure_audit_before_portfolio_grid",
    "industry_r2_and_style_correlation_report_required",
    "residual_factor_matrix_required_before_portfolio_grid",
    "style_decomposition_size_value_lowvol_momentum_liquidity_required",
]
REQUIRED_INDUSTRY_STYLE_EXPOSURE_AUDIT_CONFIRMATIONS = [
    "industry_style_exposure_audit_confirmed",
    "industry_r2_and_style_correlation_report_confirmed",
    "residual_factor_matrix_before_portfolio_grid_confirmed",
    "raw_topn_without_residual_audit_rejected",
]
REQUIRED_PRE_MINING_CONTROL_CONTRACT_DESIGN_ITEMS = [
    "pre_mining_control_contract_before_factor_generation",
]
REQUIRED_PRE_MINING_CONTROL_CONTRACT_CONFIRMATIONS = [
    "pre_mining_control_contract_reviewed_before_generation",
]
REQUIRED_DATA_SOURCE_AVAILABILITY_DESIGN_ITEMS = [
    "data_source_availability_audit_before_family_selection",
    "local_processed_coverage_and_tushare_permission_probe_required",
    "candidate_family_data_source_must_be_accessible_pit_safe_and_long_cycle_ready",
    "short_window_smoke_cannot_be_used_as_profitability_or_family_success_evidence",
]
REQUIRED_DATA_SOURCE_AVAILABILITY_CONFIRMATIONS = [
    "data_source_availability_audit_read",
    "local_processed_coverage_and_tushare_permission_probe_confirmed",
    "candidate_family_accessible_pit_source_confirmed",
    "short_window_smoke_rejected_as_profitability_evidence_confirmed",
]
REQUIRED_METHOD_OPTIMIZATION_DESIGN_ITEMS = [
    "a_share_microstructure_limit_suspend_st_new_delist_board_filters",
    "financial_pit_announcement_revision_available_date_lag",
    "industry_style_neutral_combination_policy",
    "cn_etf_rotation_dedicated_signal_pack_separation",
    "portfolio_metric_pack_profit_rate_sharpe_win_rate_drawdown_turnover",
    "strict_deflated_sharpe_cpcv_white_reality_check_sensitivity",
    "china_regime_policy_credit_flow_liquidity_index_location",
    "event_factor_forecast_dividend_buyback_holder_lockup_index_rebalance",
]
REQUIRED_METHOD_OPTIMIZATION_CONFIRMATIONS = [
    "method_optimization_controls_reviewed_before_mining",
    "a_share_real_trading_filters_confirmed",
    "financial_available_date_controls_confirmed",
    "industry_style_neutral_combination_confirmed",
    "cn_etf_dedicated_signal_pack_separated_confirmed",
    "portfolio_metric_pack_confirmed",
    "strict_statistics_suite_confirmed",
    "china_market_regime_suite_confirmed",
    "event_factor_suite_confirmed",
]
ROUND_STATE_DECISIONS = {
    "continue_family",
    "rotate_family",
    "control_implementation",
    "audit_only",
    "sync_only",
}
PRE_MINING_CONTROL_CONTRACT_AREAS: list[dict[str, Any]] = [
    {
        "area_id": "a_share_real_tradeability",
        "title": "A-share real trading constraints",
        "why": "Block phantom returns from limit-up/down, suspension, ST, fresh listings, delisting, or board-permission gaps.",
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
            "limit_state_mask",
            "suspension_mask",
            "st_or_delisting_mask",
            "board_permission_mask",
            "new_listing_age_days",
            "exchange_board_permission_state",
        ],
    },
    {
        "area_id": "financial_pit_timing",
        "title": "Point-in-time financial availability",
        "why": "Financial values must become usable only after announcement or revision availability, not at report-period end.",
        "required_controls": [
            "financial_statement_ann_date_lag",
            "financial_revision_announcement_handling",
            "report_release_lag_not_period_end",
        ],
        "required_outputs": [
            "report_period",
            "ann_date",
            "available_date",
            "signal_date",
            "revision_flag_or_update_flag",
            "raw_date",
            "signal_lag_calendar_days",
        ],
    },
    {
        "area_id": "industry_style_neutralization",
        "title": "Industry and style exposure separation",
        "why": "Separate alpha from industry, size, value, low-volatility, momentum, and liquidity beta.",
        "required_controls": [
            "industry_exposure_report",
            "style_exposure_report",
            "size_value_lowvol_momentum_liquidity_decomposition",
            "neutralized_factor_matrix_or_residual_option",
        ],
        "required_outputs": [
            "industry_exposure",
            "size_exposure",
            "value_exposure",
            "lowvol_exposure",
            "momentum_exposure",
            "liquidity_exposure",
            "industry_neutral_factor",
            "style_neutral_factor",
            "style_residual_ic",
        ],
    },
    {
        "area_id": "cn_etf_rotation_boundary",
        "title": "CN ETF rotation evidence boundary",
        "why": "CN stock mining and CN ETF rotation need separate universes, signals, and evidence packs.",
        "required_controls": [
            "stock_vs_etf_scope_boundary",
            "cn_etf_dedicated_signal_pack_for_etf_rotation",
        ],
        "required_outputs": [
            "stock_scope_confirmation",
            "etf_evidence_rejection_note",
            "separate_cn_etf_signal_pack_plan",
            "etf_signal_pack_status",
        ],
    },
    {
        "area_id": "portfolio_construction",
        "title": "Portfolio construction beyond raw TopN",
        "why": "Ranking evidence must survive risk budget, volatility, industry, turnover, and de-risk constraints.",
        "required_controls": [
            "risk_budget_position_sizing",
            "volatility_targeting",
            "industry_weight_constraints",
            "turnover_constraints",
            "stop_loss_or_de_risk_rules",
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
        "why": "Single best parameters are not evidence after repeated searches and overlapping folds.",
        "required_controls": [
            "deflated_sharpe",
            "cpcv_purged_cross_validation",
            "white_reality_check_or_fdr",
            "parameter_sensitivity_heatmap",
            "final_holdout_readiness_audit",
            "final_holdout_result_audit",
        ],
        "required_outputs": [
            "deflated_sharpe",
            "cpcv_summary",
            "white_reality_check_or_fdr",
            "parameter_sensitivity_heatmap",
            "overlap_adjusted_statistics",
            "parameter_sensitivity_heatmap_status",
            "final_holdout_status",
        ],
    },
    {
        "area_id": "china_market_regime",
        "title": "China market regime context",
        "why": "A-share factors must be tested across policy, credit, flow, liquidity, and index-location regimes.",
        "required_controls": [
            "policy_liquidity_regime",
            "credit_cycle_proxy",
            "northbound_margin_turnover_temperature",
            "index_location_state",
        ],
        "required_outputs": [
            "policy_liquidity_state",
            "credit_cycle_state",
            "northbound_margin_temperature",
            "index_location_state",
            "signal_window_regime_coverage",
            "allowed_and_blocked_regime_date_counts",
        ],
    },
    {
        "area_id": "event_factors",
        "title": "Event-factor coverage",
        "why": "Corporate events can be real alpha sources or hidden event-contamination artifacts.",
        "required_controls": [
            "earnings_forecast_events",
            "dividend_ex_right_events",
            "buyback_holder_change_unlock_events",
            "index_rebalance_events",
        ],
        "required_outputs": [
            "event_available_date",
            "event_effective_date",
            "event_type",
            "event_contamination_audit",
            "event_neutralized_ic",
            "event_signal_lag_days",
        ],
    },
]


def build_factor_mining_startup_gate(
    config: dict[str, Any],
    *,
    request: dict[str, Any],
    current_branch: str,
) -> dict[str, Any]:
    expected_market = str(config.get("market", "CN"))
    expected_asset_type = str(config.get("asset_type", "stock"))
    branch = str(request.get("branch", ""))
    confirmations = _dict(request.get("confirmations"))
    blockers = _blockers(config, request, current_branch=current_branch, confirmations=confirmations)
    status = "cleared" if not blockers else "blocked"
    quality_gate = _quality_gate(config)
    repeatable_protocol = _repeatable_mining_protocol(config)
    round_state = _round_state(config, protocol=repeatable_protocol)
    pre_mining_control_contract = _pre_mining_control_contract(quality_gate)
    packet = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": status,
        "summary": {
            "scope_id": str(config.get("scope_id", "cn_stock_factor_mining")),
            "machine": request.get("machine"),
            "task": request.get("task"),
            "branch": branch,
            "current_branch": current_branch,
            "market": request.get("market", expected_market),
            "asset_type": request.get("asset_type", expected_asset_type),
            "expected_market": expected_market,
            "expected_asset_type": expected_asset_type,
            "excluded_markets": _list(config.get("forbidden_markets")),
            "commits_allowed": bool(request.get("commits_allowed", False)),
            "pushes_allowed": bool(request.get("pushes_allowed", False)),
        },
        "validation_windows": _dict(config.get("validation_windows")),
        "config_required_inputs": _list(config.get("required_inputs")),
        "candidate_budget": _dict(config.get("candidate_budget")),
        "research_direction": _research_direction(config),
        "repeatable_mining_protocol": repeatable_protocol,
        "round_state": round_state,
        "quality_gate": quality_gate,
        "pre_mining_control_contract": pre_mining_control_contract,
        "method_optimization_contract": _method_optimization_contract(config, protocol=repeatable_protocol),
        "round_governance": _round_governance(config),
        "pre_run_checklist": _pre_run_checklist(config, quality_gate=quality_gate),
        "confirmation_questions": _confirmation_questions(config, quality_gate=quality_gate),
        "decision": {
            "startup_gate_cleared": not blockers,
            "blockers": blockers,
        },
        "safety": SAFETY_TEXT,
        "live_boundary_allowed": False,
    }
    return packet


def validate_cleared_startup_gate_packet(
    packet_path: str | Path | None,
    *,
    expected_market: str = "CN",
    expected_asset_type: str = "stock",
    context: str = "CN stock factor mining",
    require_generated_today: bool = True,
) -> dict[str, Any]:
    if packet_path is None:
        raise ValueError(f"{context} requires a cleared startup gate packet")
    path = Path(packet_path)
    if not path.exists():
        raise ValueError(f"{context} requires a cleared startup gate packet: {path}")
    packet = json.loads(path.read_text(encoding="utf-8"))
    if require_generated_today and packet.get("generated_at") != date.today().isoformat():
        raise ValueError(f"{context} startup gate packet must be generated today: {path}")
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    if packet.get("status") != "cleared" or decision.get("startup_gate_cleared") is not True:
        raise ValueError(f"{context} startup gate is not cleared: {path}")
    if str(summary.get("market")).upper() != expected_market.upper() or str(summary.get("asset_type")).lower() != expected_asset_type.lower():
        raise ValueError(f"{context} startup gate scope mismatch: {path}")
    _validate_research_direction(packet, context=context, path=path)
    _validate_repeatable_mining_protocol(packet, context=context, path=path)
    _validate_round_state(packet, context=context, path=path)
    _validate_round_governance(packet, context=context, path=path)
    _validate_translation_layer_protocol(packet, context=context, path=path)
    _validate_candidate_plan_control_protocol(packet, context=context, path=path)
    _validate_research_execution_policy_protocol(packet, context=context, path=path)
    _validate_tradeability_data_readiness_protocol(packet, context=context, path=path)
    _validate_tradeability_mask_cache_protocol(packet, context=context, path=path)
    _validate_financial_pit_timing_audit_protocol(packet, context=context, path=path)
    _validate_portfolio_policy_gate_protocol(packet, context=context, path=path)
    _validate_industry_style_exposure_audit_protocol(packet, context=context, path=path)
    _validate_pre_mining_control_contract_protocol(packet, context=context, path=path)
    _validate_data_source_availability_protocol(packet, context=context, path=path)
    _validate_method_optimization_protocol(packet, context=context, path=path)
    _validate_method_optimization_contract(packet, context=context, path=path)
    _validate_pre_mining_control_contract(packet, context=context, path=path)
    return packet


def _validate_research_direction(packet: dict[str, Any], *, context: str, path: Path) -> None:
    research_direction = _dict(packet.get("research_direction"))
    if not research_direction:
        raise ValueError(f"{context} startup gate research direction is missing: {path}")
    objective = str(research_direction.get("objective", ""))
    if objective != REQUIRED_RESEARCH_OBJECTIVE:
        raise ValueError(f"{context} startup gate research direction mismatch: {path}")
    if not _list(research_direction.get("allowed_factor_families")):
        raise ValueError(f"{context} startup gate research direction lacks factor families: {path}")
    stage_policy = _dict(research_direction.get("stage_policy"))
    missing_stages = [stage for stage in ("discovery", "validation", "final_holdout") if stage not in stage_policy]
    if missing_stages:
        raise ValueError(f"{context} startup gate research direction lacks stage policy: {path}")
    if REQUIRED_LONG_CYCLE_STAGE not in stage_policy:
        raise ValueError(f"{context} startup gate lacks long-cycle replay stage policy: {path}")
    rotation = _dict(research_direction.get("factor_family_rotation"))
    if rotation.get("max_failed_batches_before_rotation") is None:
        raise ValueError(f"{context} startup gate research direction lacks rotation policy: {path}")


def _validate_repeatable_mining_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    if not protocol:
        raise ValueError(f"{context} startup gate repeatable mining protocol is missing: {path}")
    if not str(protocol.get("source_audit", "")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks source audit: {path}")
    if not str(protocol.get("next_direction", "")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks next direction: {path}")
    if not _list(protocol.get("recently_rejected_directions")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks rejected directions: {path}")
    if not _list(protocol.get("required_experiment_design")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks experiment design: {path}")
    if not _list(protocol.get("confirm_before_each_run")):
        raise ValueError(f"{context} startup gate repeatable mining protocol lacks per-run confirmations: {path}")
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [item for item in REQUIRED_LONG_CYCLE_DESIGN_ITEMS if item not in design_items]
    if missing_design_items:
        if any("source" in item for item in missing_design_items):
            raise ValueError(f"{context} startup gate lacks source-evidence experiment design: {path}")
        if any("progress_audit" in item for item in missing_design_items):
            raise ValueError(f"{context} startup gate lacks progress-audit experiment design: {path}")
        if any("signal_window" in item for item in missing_design_items):
            raise ValueError(f"{context} startup gate lacks signal-window regime experiment design: {path}")
        raise ValueError(f"{context} startup gate lacks long-cycle experiment design: {path}")
    missing_confirmations = [item for item in REQUIRED_LONG_CYCLE_CONFIRMATIONS if item not in confirmations]
    if missing_confirmations:
        if any("source" in item for item in missing_confirmations):
            raise ValueError(f"{context} startup gate lacks source-evidence per-run confirmations: {path}")
        if any("progress_audit" in item for item in missing_confirmations):
            raise ValueError(f"{context} startup gate lacks progress-audit per-run confirmations: {path}")
        if any("signal_window" in item for item in missing_confirmations):
            raise ValueError(f"{context} startup gate lacks signal-window regime per-run confirmations: {path}")
        raise ValueError(f"{context} startup gate lacks long-cycle per-run confirmations: {path}")
    missing_governance_items = [item for item in REQUIRED_ROUND_GOVERNANCE_DESIGN_ITEMS if item not in design_items]
    missing_governance_confirmations = [
        item for item in REQUIRED_ROUND_GOVERNANCE_CONFIRMATIONS if item not in confirmations
    ]
    if missing_governance_items or missing_governance_confirmations:
        raise ValueError(f"{context} startup gate lacks round governance protocol: {path}")


def _validate_round_state(packet: dict[str, Any], *, context: str, path: Path) -> None:
    state = _dict(packet.get("round_state"))
    if not state:
        raise ValueError(f"{context} startup gate round state is missing: {path}")
    last_round = _int(state.get("last_completed_round"), -1)
    next_round = _int(state.get("next_round"), -1)
    if last_round < 0 or next_round < 1:
        raise ValueError(f"{context} startup gate round state has invalid round numbers: {path}")
    if next_round != last_round + 1:
        raise ValueError(f"{context} startup gate round state next round is stale: {path}")
    decision = str(state.get("last_three_round_decision", "")).strip()
    if decision not in ROUND_STATE_DECISIONS:
        raise ValueError(f"{context} startup gate round state decision is unsupported: {path}")
    next_direction = str(state.get("next_direction", "")).strip()
    protocol_direction = str(_dict(packet.get("repeatable_mining_protocol")).get("next_direction", "")).strip()
    if not next_direction:
        raise ValueError(f"{context} startup gate round state lacks next direction: {path}")
    if protocol_direction and next_direction != protocol_direction:
        raise ValueError(f"{context} startup gate round state next direction differs from repeatable protocol: {path}")
    if last_round >= 3 and not str(state.get("last_three_round_review", "")).strip():
        raise ValueError(f"{context} startup gate round state lacks three-round review: {path}")
    if state.get("family_rotation_required") is True and "rotate" not in next_direction:
        raise ValueError(f"{context} startup gate round state rotation does not match next direction: {path}")
    if not _list(state.get("required_before_next_round")):
        raise ValueError(f"{context} startup gate round state lacks next-round requirements: {path}")


def _validate_round_governance(packet: dict[str, Any], *, context: str, path: Path) -> None:
    governance = _dict(packet.get("round_governance"))
    if not governance:
        raise ValueError(f"{context} startup gate round governance is missing: {path}")
    if governance.get("round_unit") != "factor_family_batch":
        raise ValueError(f"{context} startup gate round governance uses an unsupported round unit: {path}")
    if governance.get("review_every_n_rounds") != 3:
        raise ValueError(f"{context} startup gate round governance must review every 3 rounds: {path}")
    if governance.get("sync_every_n_rounds") != 10:
        raise ValueError(f"{context} startup gate round governance must sync every 10 rounds: {path}")
    if not _list(governance.get("three_round_review_required_actions")):
        raise ValueError(f"{context} startup gate round governance lacks review actions: {path}")
    if not _list(governance.get("ten_round_sync_required_actions")):
        raise ValueError(f"{context} startup gate round governance lacks sync actions: {path}")
    public_reference_projects = set(_list(governance.get("public_reference_projects")))
    for project in ("qlib", "alphalens", "vectorbt", "pyfolio"):
        if project not in public_reference_projects:
            raise ValueError(f"{context} startup gate round governance lacks public reference project {project}: {path}")


def _validate_translation_layer_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [item for item in REQUIRED_TRANSLATION_LAYER_DESIGN_ITEMS if item not in design_items]
    missing_confirmations = [item for item in REQUIRED_TRANSLATION_LAYER_CONFIRMATIONS if item not in confirmations]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks translation-layer audit protocol: {path}")


def _validate_candidate_plan_control_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_CANDIDATE_PLAN_CONTROL_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_CANDIDATE_PLAN_CONTROL_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks candidate-plan control protocol: {path}")


def _validate_research_execution_policy_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_RESEARCH_EXECUTION_POLICY_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_RESEARCH_EXECUTION_POLICY_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks research execution policy protocol: {path}")


def _validate_tradeability_data_readiness_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_TRADEABILITY_DATA_READINESS_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_TRADEABILITY_DATA_READINESS_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks tradeability data readiness protocol: {path}")


def _validate_tradeability_mask_cache_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_TRADEABILITY_MASK_CACHE_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_TRADEABILITY_MASK_CACHE_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks tradeability mask cache protocol: {path}")


def _validate_financial_pit_timing_audit_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_FINANCIAL_PIT_TIMING_AUDIT_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_FINANCIAL_PIT_TIMING_AUDIT_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks financial PIT timing audit protocol: {path}")


def _validate_portfolio_policy_gate_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_PORTFOLIO_POLICY_GATE_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_PORTFOLIO_POLICY_GATE_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks portfolio construction policy gate protocol: {path}")


def _validate_industry_style_exposure_audit_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_INDUSTRY_STYLE_EXPOSURE_AUDIT_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_INDUSTRY_STYLE_EXPOSURE_AUDIT_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks industry/style exposure audit protocol: {path}")


def _validate_pre_mining_control_contract_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_PRE_MINING_CONTROL_CONTRACT_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_PRE_MINING_CONTROL_CONTRACT_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks pre-mining control contract protocol: {path}")


def _validate_data_source_availability_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_DATA_SOURCE_AVAILABILITY_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_DATA_SOURCE_AVAILABILITY_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks data-source availability protocol: {path}")


def _validate_method_optimization_protocol(packet: dict[str, Any], *, context: str, path: Path) -> None:
    protocol = _dict(packet.get("repeatable_mining_protocol"))
    design_items = set(_list(protocol.get("required_experiment_design")))
    confirmations = set(_list(protocol.get("confirm_before_each_run")))
    missing_design_items = [
        item for item in REQUIRED_METHOD_OPTIMIZATION_DESIGN_ITEMS if item not in design_items
    ]
    missing_confirmations = [
        item for item in REQUIRED_METHOD_OPTIMIZATION_CONFIRMATIONS if item not in confirmations
    ]
    if missing_design_items or missing_confirmations:
        raise ValueError(f"{context} startup gate lacks method optimization controls: {path}")


def _validate_method_optimization_contract(packet: dict[str, Any], *, context: str, path: Path) -> None:
    contract = _dict(packet.get("method_optimization_contract"))
    if not contract:
        raise ValueError(f"{context} startup gate lacks method optimization contract: {path}")
    if not str(contract.get("source_audit", "")).strip():
        raise ValueError(f"{context} startup gate method optimization contract lacks source audit: {path}")
    if not str(contract.get("next_allowed_direction", "")).strip():
        raise ValueError(f"{context} startup gate method optimization contract lacks next direction: {path}")
    protocol_direction = str(_dict(packet.get("repeatable_mining_protocol")).get("next_direction", "")).strip()
    if protocol_direction and str(contract.get("next_allowed_direction", "")).strip() != protocol_direction:
        raise ValueError(f"{context} startup gate method optimization contract next direction is stale: {path}")
    if contract.get("promotion_allowed_without_contract") is not False:
        raise ValueError(f"{context} startup gate method optimization contract must block promotion bypass: {path}")
    if contract.get("direct_topn_expansion_allowed_without_contract") is not False:
        raise ValueError(f"{context} startup gate method optimization contract must block raw TopN bypass: {path}")

    expected_areas = {str(area["area_id"]): area for area in PRE_MINING_CONTROL_CONTRACT_AREAS}
    areas = _list_of_dicts(contract.get("optimization_areas"))
    expected_area_ids = set(expected_areas)
    actual_area_ids = {str(area.get("area_id", "")) for area in areas}
    if expected_area_ids - actual_area_ids:
        raise ValueError(f"{context} startup gate method optimization contract is incomplete: {path}")
    for area in areas:
        area_id = str(area.get("area_id", ""))
        controls = set(_list(area.get("required_controls")))
        outputs = set(_list(area.get("required_outputs")))
        expected_area = _dict(expected_areas.get(area_id))
        missing_controls = [item for item in _list(expected_area.get("required_controls")) if item not in controls]
        missing_outputs = [item for item in _list(expected_area.get("required_outputs")) if item not in outputs]
        if not controls or not outputs:
            raise ValueError(f"{context} startup gate method optimization contract lacks area controls: {path}")
        if missing_controls:
            raise ValueError(f"{context} startup gate method optimization contract lacks required controls: {path}")
        if missing_outputs:
            raise ValueError(f"{context} startup gate method optimization contract lacks required outputs: {path}")
        if area.get("blocking_for_profit_claim") is not True:
            raise ValueError(f"{context} startup gate method optimization contract has nonblocking area: {path}")

    stop_loss = _dict(contract.get("family_stop_loss"))
    if stop_loss.get("hibernate_after_zero_accepted_walk_forward") is not True:
        raise ValueError(f"{context} startup gate method optimization contract lacks zero-accepted hibernation: {path}")
    if stop_loss.get("reentry_requires_new_orthogonal_hypothesis") is not True:
        raise ValueError(f"{context} startup gate method optimization contract lacks reentry rule: {path}")


def _validate_pre_mining_control_contract(packet: dict[str, Any], *, context: str, path: Path) -> None:
    contract = _dict(packet.get("pre_mining_control_contract"))
    if not contract:
        raise ValueError(f"{context} startup gate lacks pre-mining control contract: {path}")
    expected_areas = {str(area["area_id"]): area for area in PRE_MINING_CONTROL_CONTRACT_AREAS}
    areas = _list_of_dicts(contract.get("areas"))
    expected_area_ids = set(expected_areas)
    actual_area_ids = {str(area.get("area_id", "")) for area in areas}
    if expected_area_ids - actual_area_ids:
        raise ValueError(f"{context} startup gate pre-mining control contract is incomplete: {path}")
    for area in areas:
        area_id = str(area.get("area_id", ""))
        controls = set(_list(area.get("required_controls")))
        outputs = set(_list(area.get("required_outputs")))
        expected_area = _dict(expected_areas.get(area_id))
        missing_controls = [item for item in _list(expected_area.get("required_controls")) if item not in controls]
        missing_outputs = [item for item in _list(expected_area.get("required_outputs")) if item not in outputs]
        if not controls:
            raise ValueError(f"{context} startup gate pre-mining control contract lacks controls: {path}")
        if not outputs:
            raise ValueError(f"{context} startup gate pre-mining control contract lacks required outputs: {path}")
        if missing_controls:
            raise ValueError(f"{context} startup gate pre-mining control contract lacks required controls: {path}")
        if missing_outputs:
            raise ValueError(f"{context} startup gate pre-mining control contract lacks required outputs: {path}")
        if not isinstance(area.get("direct_mining_ready"), bool):
            raise ValueError(f"{context} startup gate pre-mining control contract lacks readiness flags: {path}")


def _blockers(
    config: dict[str, Any],
    request: dict[str, Any],
    *,
    current_branch: str,
    confirmations: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    machine = str(request.get("machine", ""))
    task = str(request.get("task", ""))
    branch = str(request.get("branch", ""))
    market = str(request.get("market", ""))
    asset_type = str(request.get("asset_type", ""))
    expected_market = str(config.get("market", "CN"))
    expected_asset_type = str(config.get("asset_type", "stock"))
    branch_prefixes = _branch_prefixes(config)

    if machine not in set(_list(config.get("allowed_machines"))):
        blockers.append("machine_not_allowed")
    if task not in set(_list(config.get("allowed_tasks"))):
        blockers.append("task_not_allowed")
    if branch_prefixes and not any(branch.startswith(prefix) for prefix in branch_prefixes):
        blockers.append("branch_prefix_mismatch")
    if current_branch and branch and current_branch != branch:
        blockers.append("current_branch_mismatch")
    if market != expected_market:
        blockers.append("market_scope_mismatch")
    if asset_type != expected_asset_type:
        blockers.append("asset_type_scope_mismatch")

    for name in _list(config.get("required_confirmations")):
        if confirmations.get(name) is not True:
            blockers.append(f"missing_confirmation:{name}")
    return blockers


def _pre_run_checklist(config: dict[str, Any], *, quality_gate: dict[str, Any] | None = None) -> list[str]:
    direction = _research_direction(config)
    protocol = _repeatable_mining_protocol(config)
    round_state = _round_state(config, protocol=protocol)
    governance = _round_governance(config)
    quality_summary = _dict(_dict(quality_gate).get("summary"))
    quality_decision = _dict(_dict(quality_gate).get("decision"))
    research_execution_policy = _dict(_dict(quality_gate).get("research_execution_policy"))
    quality_gate_line = (
        "Review Round142 quality gate before candidate generation: "
        f"status={_dict(quality_gate).get('status', 'not_configured')}, "
        f"implemented={quality_summary.get('implemented_controls', 0)}, "
        f"partial={quality_summary.get('partial_controls', 0)}, "
        f"planned={quality_summary.get('planned_controls', 0)}, "
        f"missing={quality_summary.get('missing_controls', 0)}, "
        f"missing_evidence={quality_summary.get('missing_evidence_controls', 0)}, "
        f"missing_next_actions={quality_summary.get('missing_next_action_controls', 0)}, "
        f"promotion_cleared={quality_decision.get('promotion_gate_cleared', False)}."
    )
    research_execution_line = (
        "Research execution policy before mining: "
        f"direct_factor_generation_allowed={research_execution_policy.get('direct_factor_generation_allowed', False)}, "
        f"candidate_preregistration_allowed={research_execution_policy.get('candidate_preregistration_allowed', False)}, "
        f"allowed={', '.join(_list(research_execution_policy.get('allowed_next_work_modes')))}, "
        f"blocked={', '.join(_list(research_execution_policy.get('blocked_next_work_modes')))}, "
        f"direct_mining_blockers="
        f"{', '.join(_list(research_execution_policy.get('direct_mining_blockers'))) or 'none'}."
    )
    return [
        "Confirm CN stock scope before mining; do not mix ETF rotation evidence into this run.",
        "Confirm machine, task type, branch, and commit/push policy before starting.",
        f"Read the source audit before mining again: {protocol.get('source_audit')}.",
        f"Confirm the next mining direction: {protocol.get('next_direction')}.",
        (
            "Current round state: "
            f"last_completed_round=Round{round_state.get('last_completed_round')}; "
            f"next_round=Round{round_state.get('next_round')}; "
            f"last_three_round_review={round_state.get('last_three_round_review')}; "
            f"decision={round_state.get('last_three_round_decision')}; "
            f"next_direction={round_state.get('next_direction')}."
        ),
        (
            "Blocked family reentry before next round: "
            f"{', '.join(_list(round_state.get('blocked_reentry_families'))) or 'none'}."
        ),
        quality_gate_line,
        research_execution_line,
        (
            "Confirm the pre-mining control contract before mining: "
            "A-share tradeability, PIT financial timing, industry/style neutralization, stock/ETF boundary, "
            "portfolio construction metrics, strict statistics, China regime, and event-factor controls."
        ),
        (
            "Review method optimization controls before mining: A-share microstructure filters "
            "(limit-up/down, suspension, ST, new listings, delisting, BSE/STAR/ChiNext permissions), "
            "financial announcement dates and revisions, industry/style neutral combinations, ETF-dedicated "
            "fund-flow/discount/volume/macro signal separation, portfolio profit rate/Sharpe/win-rate/drawdown "
            "metrics, Deflated Sharpe/CPCV/White Reality Check/sensitivity, China regime states, and event factors."
        ),
        "Resolve every quality gate evidence gap and carry every partial/planned control's next action before new factor mining.",
        f"Do not repeat rejected directions without a new thesis: {', '.join(_list(protocol.get('recently_rejected_directions')))}.",
        f"Confirm required experiment design items: {', '.join(_list(protocol.get('required_experiment_design')))}.",
        "Run the candidate plan gate before factor generation; every candidate family must declare tradeability, PIT, neutralization, ETF-scope, portfolio, strict-statistics, China-regime, and event controls.",
        "Require every active candidate to declare a hypothesis source: public method, literature, market mechanism, endpoint feature, or prior failure-review thesis.",
        "Require every active candidate plan to declare a strict promotion policy covering full-sample replay, walk-forward, costs, capacity, regime, no-lookahead, overfit, sensitivity, holdout, tradeability, neutralization, and source evidence.",
        "Run data coverage and universe checks before candidate generation.",
        "Run the tradeability data readiness audit before direct factor generation; proxy-only limit, suspension, ST, or delisting evidence keeps direct mining blocked.",
        "Build and confirm the full-window year-sliced tradeability mask cache with stock_basic L/D/P metadata before old-candidate replay or any new profitability claim; verify new-listing, delist, board, cross-year namechange/ST intervals, metadata blocker counts, and direct-vs-cache equivalence; short-window cache smokes are path checks only.",
        "Run the Financial PIT timing audit before financial factor generation; block exact duplicate financial keys, same-day announcement trading, stale signal lags over 30 calendar days, and unmapped signal dates before IC or portfolio work.",
        "Run the portfolio construction policy gate before any portfolio grid; require risk budget, volatility target, industry constraints, turnover/cost degradation, drawdown de-risk rules, and the full metric pack before promotion review.",
        "Run the industry/style exposure audit before any portfolio grid; require industry R2, size/value/lowvol/momentum/liquidity correlations, residual factor matrix, and residual IC before raw TopN expansion.",
        "Pre-register candidate names, expressions, directions, windows, fields, and economic rationale.",
        f"Confirm the pre-registered batch spans allowed factor families: {', '.join(_list(direction.get('allowed_factor_families')))}.",
        "Do not keep mining one failed family; rotate direction after the configured failed-batch limit.",
        "Do not treat positive IC alone as tradable; require top-N return, cost, capacity, drawdown, and tail-IC review.",
        "After strong IC but rejected long-only results, run IC-to-portfolio gap and industry-neutral IC audits before more TopN sweeps.",
        "Confirm whether the next step is an industry-neutral IC portfolio, a bottom-quantile exclusion overlay, or a stock-to-industry/ETF bridge.",
        "Use same-parameter long-cycle replay before treating any short-window result as evidence.",
        "Require walk-forward progress audit in promotion review; no-trade and regime-all-blocked cases stay rejected.",
        "Require source-performance evidence and source_evidence_status=pass before promotion review.",
        "Require signal-window regime coverage; do not let a hard regime filter clear every tradable signal date.",
        "Use walk-forward validation, regime coverage, realistic costs, capacity controls, overlap-aware statistics, and final holdout review.",
        "Do not tune parameters after reading final_holdout.",
        "Record rejected candidates and failed directions, not only winners.",
        f"After every {governance.get('review_every_n_rounds')} rounds, stop mining to review evidence, reject reasons, family ROI, and direction changes.",
        f"After every {governance.get('sync_every_n_rounds')} rounds, package lightweight results and run GitHub safe-sync only after validation and secret/data-path checks.",
        f"Before extending a weak direction, compare the method against public references: {', '.join(_list(governance.get('public_reference_projects')))}.",
        f"Keep excluded markets out of the run: {', '.join(_list(config.get('forbidden_markets')))}.",
    ]


def _confirmation_questions(config: dict[str, Any], *, quality_gate: dict[str, Any] | None = None) -> list[str]:
    market = str(config.get("market", "CN"))
    asset_type = str(config.get("asset_type", "stock"))
    branch_prefixes = _branch_prefixes(config) or ["codex/factor-batch-cn-stock-"]
    protocol = _repeatable_mining_protocol(config)
    round_state = _round_state(config, protocol=protocol)
    governance = _round_governance(config)
    quality_summary = _dict(_dict(quality_gate).get("summary"))
    return [
        f"Confirm {market} {asset_type} scope and reject ETF rotation scope for this run.",
        "Confirm the machine is allowed for factor_batch or factor_validation.",
        f"Confirm the current branch starts with one of: {', '.join(branch_prefixes)}.",
        "Confirm whether commits are allowed and pushes are disabled unless manually approved.",
        f"Confirm the audit optimization plan was reviewed: {protocol.get('source_audit')}.",
        f"Confirm this run follows the next direction: {protocol.get('next_direction')}.",
        (
            "Confirm the current round state was read: "
            f"Round{round_state.get('last_completed_round')} completed, "
            f"Round{round_state.get('next_round')} next, "
            f"decision={round_state.get('last_three_round_decision')}."
        ),
        (
            "Confirm blocked reentry families are not reused without a new orthogonal hypothesis: "
            f"{', '.join(_list(round_state.get('blocked_reentry_families'))) or 'none'}."
        ),
        "Confirm the Round142 quality gate is reviewed and all missing controls are zero before candidate generation.",
        (
            "Confirm planned or partial Round142 controls block promotion until implemented evidence exists: "
            f"partial={quality_summary.get('partial_controls', 0)}, planned={quality_summary.get('planned_controls', 0)}."
        ),
        "Confirm historical candidates and parameters are replayed unchanged across the long cycle before new profitability claims.",
        "Confirm the full-window tradeability mask cache is used for old-candidate replay, includes stock_basic L/D/P metadata, reports metadata blocker counts, cross-year namechange/ST intervals match the direct official path, and short-window mask smokes are not promotion evidence.",
        "Confirm regime coverage, look-ahead audit, overfit/multiple-testing audit, overlap-aware return statistics, and cost/capacity stress are enabled.",
        "Confirm candidate plan gate is enabled and tradeability, PIT, neutralization, ETF-scope, portfolio, statistics, China-regime, and event controls are declared before mining.",
        "Confirm every active candidate declares a hypothesis source before factor generation; do not mine anonymous parameter formulas.",
        "Confirm the screenshot optimization control suite is reviewed before mining: A-share trading rules, PIT financial timing, neutral combinations, ETF signal boundary, portfolio metrics, strict statistics, China regime, and events.",
        "Confirm the selected family has an accessible, PIT-safe, long-cycle data source before factor generation.",
        "Confirm every active candidate declares a strict promotion policy before screening; do not rank short-sample or single-parameter evidence as usable alpha.",
        "Confirm promotion consumes the walk-forward progress audit and blocks no-trade or regime-all-blocked cases.",
        "Confirm signal-window regime coverage is enabled so regime filters cannot silently empty the trading window.",
        "Confirm source-performance evidence exists and promotion blocks missing source_evidence_status.",
        "Confirm 2026 data, when available, is treated as final holdout rather than a tuning set.",
        "Confirm a pre-registered candidate plan exists before generating candidates.",
        "Confirm cost and capacity gates are required before any candidate can advance.",
        "Confirm the industry/style exposure audit is enabled; raw TopN without a residual factor matrix is rejected.",
        "Confirm IC-to-portfolio gap and industry-neutral IC audits are read before extending a strong-IC failed-long-only family.",
        "Confirm a translation-layer plan is registered before more raw TopN parameter sweeps.",
        "Confirm failed single-family directions will be recorded and rotated away from.",
        f"Confirm every {governance.get('review_every_n_rounds')} factor-mining rounds trigger review, audit, and direction adjustment before new runs.",
        f"Confirm every {governance.get('sync_every_n_rounds')} factor-mining rounds trigger lightweight result packaging and GitHub safe-sync review.",
        f"Confirm public-method references are reviewed before burning more budget: {', '.join(_list(governance.get('public_reference_projects')))}.",
    ]


def _research_direction(config: dict[str, Any]) -> dict[str, Any]:
    raw = _dict(config.get("research_direction"))
    allowed_families = _list(raw.get("allowed_factor_families")) or [
        "price_volume",
        "daily_basic",
        "moneyflow",
        "composite",
    ]
    return {
        "objective": str(raw.get("objective", REQUIRED_RESEARCH_OBJECTIVE)),
        "mandate": str(raw.get("mandate", "Mine tradable CN stock alpha factors, not ETF rotation signals.")),
        "target_market": str(config.get("market", "CN")),
        "target_asset_type": str(config.get("asset_type", "stock")),
        "allowed_factor_families": allowed_families,
        "forbidden_directions": _list(raw.get("forbidden_directions"))
        or ["cn_etf_rotation", "single_family_lockin", "oos_tuning"],
        "stage_policy": _dict(raw.get("stage_policy"))
        or {
            "discovery": "Design and filter candidates only.",
            "long_cycle_replay": "Replay historical candidates and parameters unchanged across the available long cycle before new mining claims.",
            "validation": "Run OOS only after discovery evidence clears.",
            "final_holdout": "Read once; never tune after reading.",
        },
        "factor_family_rotation": _dict(raw.get("factor_family_rotation"))
        or {
            "max_failed_batches_before_rotation": 1,
            "max_single_family_share": 0.5,
            "record_rejected_families": True,
        },
    }


def _repeatable_mining_protocol(config: dict[str, Any]) -> dict[str, Any]:
    direction = _dict(config.get("research_direction"))
    raw = _dict(direction.get("repeatable_mining_protocol")) or _dict(config.get("repeatable_mining_protocol"))
    default_required_experiment_design = [
        "long_cycle_same_parameter_replay",
        "same_parameter_full_sample_diagnostic",
        "rolling_walk_forward_train_test_split",
        "walk_forward_progress_audit",
        "market_regime_coverage",
        "market_regime_signal_window_coverage",
        "lookahead_bias_audit",
        "overfit_multiple_testing_audit",
        "source_performance_evidence_required",
        "source_evidence_status_gate",
        "daily_champion_10bps_20bps_validation",
        "twenty_twenty_five_oos_only",
        "overlap_aware_return_statistics",
        "daily_vs_every2_every3_controls",
        "cost_capacity_turnover_stress",
        "cumulative_multiple_testing_accounting",
        "no_parameter_tuning_during_oos",
        "final_holdout_only_after_oos_clearance",
    ]
    default_confirm_before_each_run = [
        "long_cycle_replay_plan_read",
        "same_parameter_full_sample_enabled",
        "promotion_progress_audit_gate_enabled",
        "market_regime_coverage_enabled",
        "market_regime_signal_window_coverage_enabled",
        "lookahead_bias_audit_enabled",
        "overfit_multiple_testing_audit_enabled",
        "source_performance_evidence_gate_enabled",
        "promotion_source_evidence_gate_enabled",
        "previous_audit_read",
        "latest_bootstrap_diagnostic_read",
        "latest_tailrankic_batch_read",
        "latest_monthly_persistence_batch_read",
        "latest_monthly_loss_control_batch_read",
        "latest_threshold_robustness_batch_read",
        "latest_rankic_enhancement_batch_read",
        "latest_champion_staggered_schedule_batch_read",
        "batch12_validation_handoff_read",
        "prev_month_neg1_gate_pre_registered",
        "downside_range_champion_pre_registered",
        "daily_champion_oos_candidates_pre_registered",
        "factor_validation_branch_confirmed",
        "oos_2025_only_validation_plan_registered",
        "overlap_adjusted_statistics_plan_enabled",
        "cumulative_multiple_testing_gate_enabled",
        "cost_capacity_turnover_stress_enabled",
        "daily_vs_every2_every3_controls_enabled",
        "cost_capacity_gate_enabled",
        "final_holdout_not_touched",
    ]
    required_experiment_design = _unique_preserving_order(
        (_list(raw.get("required_experiment_design")) or default_required_experiment_design)
        + REQUIRED_ROUND_GOVERNANCE_DESIGN_ITEMS
        + REQUIRED_TRANSLATION_LAYER_DESIGN_ITEMS
        + REQUIRED_ROUND142_QUALITY_GATE_DESIGN_ITEMS
        + REQUIRED_CANDIDATE_PLAN_CONTROL_DESIGN_ITEMS
        + REQUIRED_RESEARCH_EXECUTION_POLICY_DESIGN_ITEMS
        + REQUIRED_TRADEABILITY_DATA_READINESS_DESIGN_ITEMS
        + REQUIRED_TRADEABILITY_MASK_CACHE_DESIGN_ITEMS
        + REQUIRED_FINANCIAL_PIT_TIMING_AUDIT_DESIGN_ITEMS
        + REQUIRED_PORTFOLIO_POLICY_GATE_DESIGN_ITEMS
        + REQUIRED_INDUSTRY_STYLE_EXPOSURE_AUDIT_DESIGN_ITEMS
        + REQUIRED_PRE_MINING_CONTROL_CONTRACT_DESIGN_ITEMS
        + REQUIRED_DATA_SOURCE_AVAILABILITY_DESIGN_ITEMS
        + REQUIRED_METHOD_OPTIMIZATION_DESIGN_ITEMS
    )
    confirm_before_each_run = _unique_preserving_order(
        (_list(raw.get("confirm_before_each_run")) or default_confirm_before_each_run)
        + REQUIRED_ROUND_GOVERNANCE_CONFIRMATIONS
        + REQUIRED_TRANSLATION_LAYER_CONFIRMATIONS
        + REQUIRED_ROUND142_QUALITY_GATE_CONFIRMATIONS
        + REQUIRED_CANDIDATE_PLAN_CONTROL_CONFIRMATIONS
        + REQUIRED_RESEARCH_EXECUTION_POLICY_CONFIRMATIONS
        + REQUIRED_TRADEABILITY_DATA_READINESS_CONFIRMATIONS
        + REQUIRED_TRADEABILITY_MASK_CACHE_CONFIRMATIONS
        + REQUIRED_FINANCIAL_PIT_TIMING_AUDIT_CONFIRMATIONS
        + REQUIRED_PORTFOLIO_POLICY_GATE_CONFIRMATIONS
        + REQUIRED_INDUSTRY_STYLE_EXPOSURE_AUDIT_CONFIRMATIONS
        + REQUIRED_PRE_MINING_CONTROL_CONTRACT_CONFIRMATIONS
        + REQUIRED_DATA_SOURCE_AVAILABILITY_CONFIRMATIONS
        + REQUIRED_METHOD_OPTIMIZATION_CONFIRMATIONS
    )
    return {
        "source_audit": str(raw.get("source_audit", DEFAULT_AUDIT_REPORT)),
        "next_direction": str(raw.get("next_direction", DEFAULT_NEXT_DIRECTION)),
        "recently_rejected_directions": _list(raw.get("recently_rejected_directions"))
        or [
            "single_factor_top50_daily_long_only",
            "liquid_trend_direct_long",
            "capacity_blind_microcap_tail",
            "moneyflow_only_lockin",
        ],
        "required_experiment_design": required_experiment_design,
        "confirm_before_each_run": confirm_before_each_run,
    }


def _round_governance(config: dict[str, Any]) -> dict[str, Any]:
    raw = _dict(config.get("round_governance"))
    return {
        "round_unit": str(raw.get("round_unit", "factor_family_batch")),
        "review_every_n_rounds": int(raw.get("review_every_n_rounds", 3)),
        "sync_every_n_rounds": int(raw.get("sync_every_n_rounds", 10)),
        "three_round_review_required_actions": _list(raw.get("three_round_review_required_actions"))
        or [
            "factor_family_result_audit",
            "reject_reason_histogram",
            "direction_adjustment_decision",
            "public_reference_method_review",
            "budget_waste_stop_loss_review",
        ],
        "ten_round_sync_required_actions": _list(raw.get("ten_round_sync_required_actions"))
        or [
            "lightweight_stage_report",
            "factor_registry_or_research_ledger_update",
            "validation_command_rerun",
            "github_safe_sync_after_validation",
            "forbidden_data_and_secret_path_audit",
        ],
        "public_reference_projects": _list(raw.get("public_reference_projects"))
        or [
            "qlib",
            "alphalens",
            "vectorbt",
            "pyfolio",
            "worldquant_101_alphas",
        ],
        "profitability_guardrails": _list(raw.get("profitability_guardrails"))
        or [
            "promotable_requires_cost_capacity_walk_forward_and_long_cycle_replay",
            "research_lead_requires_cross_period_ic_or_portfolio_evidence",
            "discard_single_family_after_repeated_same_blocker_failures",
            "do_not_optimize_for_raw_sharpe_before_hard_gates",
        ],
    }


def _round_state(config: dict[str, Any], *, protocol: dict[str, Any]) -> dict[str, Any]:
    raw = _dict(config.get("round_state"))
    last_round = _int(raw.get("last_completed_round"), 0)
    next_round = _int(raw.get("next_round"), last_round + 1)
    next_direction = str(raw.get("next_direction", protocol.get("next_direction", ""))).strip()
    return {
        "last_completed_round": last_round,
        "next_round": next_round,
        "last_three_round_review": str(raw.get("last_three_round_review", protocol.get("source_audit", ""))).strip(),
        "last_three_round_decision": str(raw.get("last_three_round_decision", "continue_family")).strip(),
        "family_rotation_required": bool(raw.get("family_rotation_required", False)),
        "next_direction": next_direction,
        "blocked_reentry_families": _list(raw.get("blocked_reentry_families")),
        "required_before_next_round": _list(raw.get("required_before_next_round"))
        or [
            "run_startup_gate_before_factor_generation",
            "run_candidate_plan_gate_before_factor_generation",
            "declare_hypothesis_source_before_generation",
            "keep_final_holdout_unread_until_validation_clears",
        ],
    }


def _method_optimization_contract(
    config: dict[str, Any],
    *,
    protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw = _dict(config.get("method_optimization_contract"))
    direction = _research_direction(config)
    protocol = _dict(protocol) or _repeatable_mining_protocol(config)
    rotation = _dict(direction.get("factor_family_rotation"))
    default_stop_loss = {
        "max_failed_batches_before_rotation": int(rotation.get("max_failed_batches_before_rotation", 1)),
        "three_round_review_required": True,
        "review_after_n_rounds": 3,
        "hibernate_after_zero_accepted_walk_forward": True,
        "hibernate_after_repeated_same_blocker_rounds": 3,
        "reentry_requires_new_orthogonal_hypothesis": True,
        "public_reference_review_required": True,
        "no_same_family_parameter_expansion_after_zero_accepted": True,
    }
    stop_loss = default_stop_loss.copy()
    stop_loss.update(_dict(raw.get("family_stop_loss")))
    areas = []
    for area in PRE_MINING_CONTROL_CONTRACT_AREAS:
        areas.append(
            {
                "area_id": str(area.get("area_id", "")),
                "title": str(area.get("title", "")),
                "why": str(area.get("why", "")),
                "required_controls": _list(area.get("required_controls")),
                "required_outputs": _list(area.get("required_outputs")),
                "blocking_for_profit_claim": True,
            }
        )
    return {
        "scope": "CN stock factor mining method optimization",
        "source_audit": str(raw.get("source_audit", protocol.get("source_audit", ""))),
        "next_allowed_direction": str(raw.get("next_allowed_direction", protocol.get("next_direction", ""))),
        "optimization_areas": areas,
        "family_stop_loss": stop_loss,
        "hibernated_families": _unique_preserving_order(
            _list(raw.get("hibernated_families"))
            + _list(raw.get("temporarily_hibernated_families"))
        ),
        "active_constraints": _list(raw.get("active_constraints"))
        or [
            "no_profit_claim_without_all_eight_method_areas",
            "no_raw_topn_expansion_before_tradeability_pit_neutralization_portfolio_statistics_regime_event_controls",
            "no_failed_family_reentry_without_new_orthogonal_hypothesis",
            "no_single_parameter_or_short_sample_promotion",
        ],
        "promotion_allowed_without_contract": False,
        "direct_topn_expansion_allowed_without_contract": False,
    }


def _quality_gate(config: dict[str, Any]) -> dict[str, Any]:
    raw = _dict(config.get("quality_gate"))
    config_path = str(config.get("quality_gate_config_path", "")).strip()
    if not raw and config_path:
        path = Path(config_path)
        if path.exists():
            raw = json.loads(path.read_text(encoding="utf-8"))
        else:
            raw = {
                "scope_id": "missing_quality_gate_config",
                "market": str(config.get("market", "CN")),
                "asset_type": str(config.get("asset_type", "stock")),
                "control_status": {},
            }
    if not raw:
        return {}
    return build_factor_mining_quality_gate(raw)


def _pre_mining_control_contract(quality_gate: dict[str, Any] | None) -> dict[str, Any]:
    quality = _dict(quality_gate)
    status_by_control = _dict(quality.get("control_status"))
    evidence_by_control = _dict(quality.get("control_evidence"))
    next_action_by_control = _dict(quality.get("control_next_actions"))
    policy = _dict(quality.get("research_execution_policy"))
    areas: list[dict[str, Any]] = []
    for area in PRE_MINING_CONTROL_CONTRACT_AREAS:
        control_rows = []
        direct_mining_blockers = []
        for control_id in _list(area.get("required_controls")):
            status = str(status_by_control.get(control_id, "missing"))
            row = {
                "control_id": control_id,
                "status": status,
                "evidence": str(evidence_by_control.get(control_id, "")).strip(),
                "next_action": str(next_action_by_control.get(control_id, "")).strip(),
            }
            control_rows.append(row)
            if status not in {"implemented", "not_applicable"}:
                direct_mining_blockers.append(control_id)
        areas.append(
            {
                "area_id": str(area.get("area_id", "")),
                "title": str(area.get("title", "")),
                "why": str(area.get("why", "")),
                "required_controls": _list(area.get("required_controls")),
                "required_outputs": _list(area.get("required_outputs")),
                "controls": control_rows,
                "direct_mining_ready": not direct_mining_blockers,
                "direct_mining_blockers": direct_mining_blockers,
            }
        )
    return {
        "scope": "CN stock alpha pre-mining controls",
        "policy": (
            "Direct factor generation is allowed only when quality-gate controls are implemented or not applicable. "
            "While any required control is partial, planned, or missing, continue only with control implementation, "
            "data coverage audits, and candidate preregistration without profit claims."
        ),
        "direct_factor_generation_allowed": bool(policy.get("direct_factor_generation_allowed", False)),
        "allowed_next_work_modes": _list(policy.get("allowed_next_work_modes")),
        "blocked_next_work_modes": _list(policy.get("blocked_next_work_modes")),
        "areas": areas,
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
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _unique_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    unique = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _branch_prefixes(config: dict[str, Any]) -> list[str]:
    prefixes = _list(config.get("recommended_branch_prefixes"))
    if prefixes:
        return prefixes
    return _list(config.get("recommended_branch_prefix"))
