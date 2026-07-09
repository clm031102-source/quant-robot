from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any


STAGE = "cn_stock_local_source_queue_audit"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

SOURCE_ROW_COLUMNS = (
    "source_id",
    "status",
    "provider_required",
    "evidence_present",
    "local_prescreen_allowed",
    "matched_processed_paths",
    "matched_report_paths",
    "matched_prescreen_paths",
    "latest_source_cache_period",
    "latest_prescreen_period",
    "local_prescreen_current",
    "allowed_next_action",
    "blocked_actions",
    "latest_evidence",
    "rationale",
)

ACTIVE_STATUS = "active_source_accumulation"
CONDITIONAL_ACTIVE_STATUS = "conditional_active_source"
HIBERNATED_OR_CLOSED_STATUSES = {"hibernated", "closed", "source_maintenance_only"}


@dataclass(frozen=True)
class SourceQueueDefinition:
    source_id: str
    status: str
    provider_required: bool
    allowed_next_action: str
    blocked_actions: tuple[str, ...]
    latest_evidence: str
    rationale: str
    processed_globs: tuple[str, ...] = ()
    report_globs: tuple[str, ...] = ()
    prescreen_globs: tuple[str, ...] = ()
    evidence_required: bool = False


def default_source_queue_definitions() -> list[SourceQueueDefinition]:
    return [
        SourceQueueDefinition(
            source_id="analyst_report_revision",
            status=ACTIVE_STATUS,
            provider_required=True,
            allowed_next_action="monthly_report_rc_cache_preflight_then_frozen_prescreen",
            blocked_actions=(
                "portfolio_or_promotion_before_year_coverage",
                "parameter_tuning_from_single_added_month",
                "provider_request_when_quota_preflight_blocks",
            ),
            latest_evidence="round700_round701_analyst_report_revision_jan_to_jun_2024",
            rationale=(
                "Only live accumulation line after local source closeout; June improved IC but still lacks "
                "year coverage and promotion evidence."
            ),
            processed_globs=("round70*_analyst_report_revision_cache_*",),
            report_globs=("round70*_analyst_report_revision_cache_*",),
            prescreen_globs=("round*_analyst_report_revision_*prescreen_*",),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            source_id="external_macro_lpr_regime",
            status="source_maintenance_only",
            provider_required=False,
            allowed_next_action="new_lpr_macro_interaction_source_gate_only_after_round738_rejection",
            blocked_actions=(
                "same_lpr_gap_widening_candidate_retry",
                "cost_or_fold_threshold_relaxation_after_walk_forward_rejection",
                "standalone_market_level_lpr_stock_rank",
                "portfolio_grid_before_residual_prescreen",
                "promotion_from_source_or_join_smoke",
                "hk_hold_lpr_interaction_before_hk_hold_history_ready",
            ),
            latest_evidence="round738_lpr_walk_forward_rejection_rotation_gate",
            rationale=(
                "Repaired LPR macro-rate data remains useful source-maintenance evidence, but the Round737 "
                "walk-forward rejection and Round738 rotation gate closed the old gap-widening residual path "
                "to simple rerun or threshold rescue."
            ),
            processed_globs=("round695_external_feeds_lpr_repaired_*",),
            report_globs=("round695_external_feed_lpr_repaired_coverage_audit_*",),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "financial_statement_adjacent_realized",
            "closed",
            False,
            "do_not_reenter_without_new_external_expectation_source",
            ("direct_formula_mutation", "sign_flip_after_negative_ic", "same_parameter_replay"),
            "round691_694_statement_source_closeout",
            "Adjacent realized-statement rotations produced zero research leads across the closeout set.",
            report_globs=(
                "round691_financial_reporting_timeliness_residual_ic_shape_prescreen_*",
                "round692_pead_gap_reversal_source_repair_residual_prescreen_*",
                "round693_statement_working_capital_pressure_residual_prescreen_*",
                "round694_statement_capital_structure_efficiency_residual_prescreen_*",
            ),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "forecast_express_event",
            "hibernated",
            False,
            "source_readiness_only_if_true_new_expectation_feed_exists",
            ("old_forecast_or_express_formula_grid", "guidance_range_tuning"),
            "forecast_express_prior_zero_research_leads",
            "Old forecast and express event formulas failed strict neutral gates.",
            report_globs=(
                "round255_event_express_profit_surprise_pit_ic_prescreen_*",
                "round256_forecast_guidance_uncertainty_pit_ic_prescreen_*",
                "round268_forecast_express_disagreement_pit_ic_prescreen_*",
            ),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "share_unlock_pledge",
            "hibernated",
            False,
            "do_not_run_direct_supply_rankings",
            ("unlock_direct_rank", "pledge_direct_rank", "sparse_year_retry"),
            "share_unlock_pledge_sparse_year_and_zero_lead_evidence",
            "Supply-event evidence was too sparse and failed size-neutral checks.",
            report_globs=("round251_share_unlock_pledge_full_*",),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "repurchase_contextual_repair",
            "hibernated",
            False,
            "do_not_expand_contextual_repair_without_new_event_source",
            ("context_weight_tuning", "raw_event_reentry"),
            "event_contextual_underreaction_reference_dedup_failures",
            "Contextual event leads were explained by raw event and reference clusters.",
            report_globs=(
                "round248_event_contextual_underreaction_prescreen_*",
                "round249_event_contextual_underreaction_reference_dedup_*",
                "round250_event_contextual_underreaction_residual_audit_*",
                "round303_24h_profit_sprint_repurchase_contextual_repair_pit_ic_prescreen_*",
            ),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "index_rebalance_passive_flow",
            "hibernated",
            False,
            "do_not_flip_direction_after_failed_passive_flow_test",
            ("direction_flip", "window_grid", "portfolio_grid"),
            "index_rebalance_zero_research_leads",
            "Passive-flow tests had no promotable research leads.",
            report_globs=("round231_index_rebalance_passive_flow_*",),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "dragon_tiger_attention",
            "hibernated",
            False,
            "do_not_expand_attention_windows",
            ("window_expansion", "size_residual_repair_retry"),
            "dragon_tiger_direct_and_size_residual_repair_zero_leads",
            "Dragon-tiger attention/reversal repair produced zero size-residual leads.",
            report_globs=(
                "round232_dragon_tiger_pit_ic_prescreen_*",
                "round233_dragon_tiger_size_residual_repair_*",
                "round234_family_rotation_after_dragon_tiger_failure_*",
            ),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "northbound_hk_hold_daily",
            "source_maintenance_only",
            False,
            "quarterly_state_audit_only_not_daily_factor_feed",
            ("daily_northbound_factor_generation", "post_2024_daily_hk_hold_panel"),
            "round697_round698_hk_hold_source_audit",
            "Tushare hk_hold daily northbound holding feed stopped and is now quarterly disclosure state.",
            report_globs=(
                "round697_hk_hold_source_symbol_composition_audit_*",
                "round698_hk_hold_quarterly_policy_audit_*",
            ),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "margin_financing",
            "hibernated",
            False,
            "do_not_reenter_without_new_margin_source_or_control_role",
            ("direct_margin_rank", "credit_temperature_alpha"),
            "external_feed_rotation_closeout",
            "Margin-style external feed rotations are not active alpha sources in the current queue.",
            report_globs=(
                "round192_external_margin_credit_prescreen_*",
                "round193_external_margin_credit_neutral_dedup_*",
                "round528_external_feed_coverage_audit_*",
            ),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "daily_basic_direct",
            "hibernated",
            False,
            "do_not_run_direct_daily_basic_portfolio_grid",
            ("valuation_reversion_weight_tuning", "direct_carry_grid"),
            "daily_basic_direct_and_valuation_shape_failures",
            "Daily-basic direct carry/valuation had IC fragments but failed shape, coverage, or strict gates.",
            report_globs=(
                "round257_daily_basic_non_price_public_carry_full_sample_replay_*",
                "round258_daily_basic_valuation_reversion_dvratio_full_sample_prescreen_*",
                "round258_daily_basic_valuation_shape_exposure_audit_*",
            ),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "calendar_seasonality",
            "hibernated",
            False,
            "do_not_reenter_pre_holiday_or_calendar_windows_after_round165_failure",
            (
                "pre_holiday_window_tuning",
                "calendar_bucket_grid",
                "cost_or_capacity_assumption_rescue",
                "walk_forward_after_round165_failure",
                "portfolio_grid",
            ),
            "round163_165_calendar_seasonality_cost_capacity_failure",
            (
                "The only calendar residual lead failed Round165 cost/capacity, overlap-quality, holding-day, "
                "and larger-capital capacity gates; do not revive it through window or portfolio tuning."
            ),
            report_globs=("cn_calendar_pre_holiday_cost_capacity_preflight_round165_*",),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "listing_age_board_structural",
            "hibernated",
            False,
            "use_listing_age_and_board_as_risk_control_not_alpha_source",
            (
                "listing_age_threshold_tuning",
                "board_permission_direct_rank",
                "fresh_listing_sign_flip",
                "sign_flip_after_residual_collapse",
                "portfolio_grid",
            ),
            "round259_listing_age_board_zero_residual_leads",
            (
                "Listing-age and board-permission variables are useful control/risk context, but the "
                "Round259 full-cycle residual screen produced zero research leads after industry, size, "
                "liquidity, volatility, and yearly-stability controls."
            ),
            report_globs=("round259_listing_age_board_full_core_*",),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "low_turnover_public_technical_alpha101",
            "hibernated",
            False,
            "do_not_reenter_public_price_volume_without_new_orthogonal_mechanism",
            ("mfi_obv_macd_rsi_tuning", "alpha101_rank_replay", "low_turnover_repair_grid"),
            "public_technical_alpha101_low_turnover_closeouts",
            "Public technical, Alpha101, and low-turnover repair lines failed residual or walk-forward gates.",
            report_globs=(
                "alpha101_rank_pv_reversal_residual_prescreen_round130_*",
                "public_alpha101_reference_exposure_dedup_round116_*",
                "round315_24h_profit_sprint_turnover_low_exact_validation_*",
                "round333_24h_profit_sprint_turnover_low_failure_attribution_*",
            ),
            evidence_required=True,
        ),
        SourceQueueDefinition(
            "official_tradeability_state",
            "validation_only",
            False,
            "use_as_control_mask_not_alpha_source",
            ("tradeability_event_alpha", "portfolio_grid_from_state_flags"),
            "official_tradeability_state_zero_residual_leads",
            "Tradeability state remains a control and validation surface, not a standalone alpha source.",
        ),
        SourceQueueDefinition(
            "industry_breadth",
            "validation_only",
            False,
            "use_as_regime_or_control_context_only",
            ("breadth_window_tuning", "direct_stock_alpha_from_breadth"),
            "industry_breadth_residual_collapse",
            "Industry breadth is useful context but not an active direct stock-alpha source here.",
        ),
    ]


def build_cn_stock_local_source_queue_audit(
    *,
    processed_root: str | Path = "data/processed",
    reports_root: str | Path = "data/reports",
    provider_request_allowed: bool = False,
    source_definitions: list[SourceQueueDefinition] | None = None,
) -> dict[str, Any]:
    processed_path = Path(processed_root)
    reports_path = Path(reports_root)
    definitions = source_definitions or default_source_queue_definitions()
    rows = [
        _build_source_row(definition, processed_root=processed_path, reports_root=reports_path)
        for definition in definitions
    ]
    active_rows = [row for row in rows if row["status"] == ACTIVE_STATUS]
    evidence_ready_active_rows = [row for row in active_rows if row["evidence_present"]]
    local_prescreen_ready_rows = [row for row in evidence_ready_active_rows if row["local_prescreen_allowed"]]
    no_provider_ready_rows = [row for row in evidence_ready_active_rows if not row["provider_required"]]
    provider_ready_rows = [row for row in evidence_ready_active_rows if row["provider_required"]]
    blockers = _decision_blockers(
        active_rows=active_rows,
        no_provider_ready_rows=no_provider_ready_rows,
        provider_ready_rows=provider_ready_rows,
        provider_request_allowed=provider_request_allowed,
    )
    warnings = _decision_warnings(
        no_provider_ready_rows=no_provider_ready_rows,
        provider_ready_rows=provider_ready_rows,
        provider_request_allowed=provider_request_allowed,
    )
    if no_provider_ready_rows:
        blockers = [blocker for blocker in blockers if blocker != "report_rc_quota_blocked"]
    no_provider_allowed = bool(no_provider_ready_rows)
    provider_allowed = bool(provider_ready_rows and provider_request_allowed) and not any(
        blocker.startswith("active_source_evidence_missing:") for blocker in blockers
    )
    decision = {
        "status": "cleared" if no_provider_allowed or provider_allowed else "blocked",
        "no_provider_factor_batch_allowed": no_provider_allowed,
        "provider_factor_batch_allowed": provider_allowed,
        "local_prescreen_allowed": bool(local_prescreen_ready_rows),
        "provider_request_allowed": bool(provider_request_allowed),
        "next_action": _next_action(
            blockers=blockers,
            provider_ready_rows=provider_ready_rows,
            provider_request_allowed=provider_request_allowed,
            no_provider_ready_rows=no_provider_ready_rows,
        ),
        "local_prescreen_next_action": _local_prescreen_next_action(
            local_prescreen_ready_rows=local_prescreen_ready_rows,
            provider_ready_rows=provider_ready_rows,
            provider_request_allowed=provider_request_allowed,
        ),
        "blockers": blockers,
        "warnings": warnings,
    }
    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "processed_root": str(processed_path),
        "reports_root": str(reports_path),
        "summary": {
            "source_count": len(rows),
            "active_source_count": len(active_rows),
            "evidence_ready_active_source_count": len(evidence_ready_active_rows),
            "local_prescreen_ready_source_count": len(local_prescreen_ready_rows),
            "no_provider_ready_source_count": len(no_provider_ready_rows),
            "provider_ready_source_count": len(provider_ready_rows),
            "hibernated_or_closed_source_count": sum(
                1 for row in rows if row["status"] in HIBERNATED_OR_CLOSED_STATUSES
            ),
            "missing_required_evidence_count": sum(
                1 for row in rows if row["evidence_required"] and not row["evidence_present"]
            ),
        },
        "decision": decision,
        "source_rows": rows,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_cn_stock_local_source_queue_audit_markdown(result)
    return result


def write_cn_stock_local_source_queue_audit(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    clean = _sanitize(packet)
    (output_path / "cn_stock_local_source_queue_audit.json").write_text(
        json.dumps(clean, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_stock_local_source_queue_audit.md").write_text(
        render_cn_stock_local_source_queue_audit_markdown(clean),
        encoding="utf-8",
    )
    with (output_path / "cn_stock_local_source_queue_rows.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(SOURCE_ROW_COLUMNS))
        writer.writeheader()
        for row in _list_of_dicts(clean.get("source_rows")):
            writer.writerow({column: _csv_value(row.get(column, "")) for column in SOURCE_ROW_COLUMNS})


def render_cn_stock_local_source_queue_audit_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    lines = [
        "# CN Stock Local Source Queue Audit",
        "",
        f"- Stage: {packet.get('stage', STAGE)}",
        f"- Generated at: {packet.get('generated_at', '')}",
        f"- Processed root: `{packet.get('processed_root', '')}`",
        f"- Reports root: `{packet.get('reports_root', '')}`",
        f"- Decision status: {decision.get('status', 'blocked')}",
        f"- No-provider factor batch allowed: {decision.get('no_provider_factor_batch_allowed', False)}",
        f"- Provider factor batch allowed: {decision.get('provider_factor_batch_allowed', False)}",
        f"- Local cached prescreen allowed: {decision.get('local_prescreen_allowed', False)}",
        f"- Provider request allowed: {decision.get('provider_request_allowed', False)}",
        f"- Next action: `{decision.get('next_action', '')}`",
        f"- Local prescreen next action: `{decision.get('local_prescreen_next_action', '')}`",
        f"- Active sources: {summary.get('active_source_count', 0)}",
        f"- Evidence-ready active sources: {summary.get('evidence_ready_active_source_count', 0)}",
        f"- Local-prescreen-ready active sources: {summary.get('local_prescreen_ready_source_count', 0)}",
        f"- Hibernated or closed sources: {summary.get('hibernated_or_closed_source_count', 0)}",
        f"- Safety: {packet.get('safety', SAFETY)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    warnings = _list(decision.get("warnings"))
    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    lines.extend(f"- {warning}" for warning in warnings) if warnings else lines.append("- none")
    lines.extend(
        [
            "",
            "## Source Rows",
            "",
            "| Source | Status | Provider Required | Evidence Present | Local Prescreen Allowed | Latest Cache | Latest Prescreen | Prescreen Current | Allowed Next Action | Blocked Actions |",
            "|---|---|---:|---:|---:|---|---|---:|---|---|",
        ]
    )
    for row in _list_of_dicts(packet.get("source_rows")):
        lines.append(
            "| {source_id} | {status} | {provider_required} | {evidence_present} | {local_prescreen_allowed} | {cache_period} | {prescreen_period} | {prescreen_current} | {allowed_next_action} | {blocked_actions} |".format(
                source_id=row.get("source_id", ""),
                status=row.get("status", ""),
                provider_required=row.get("provider_required", False),
                evidence_present=row.get("evidence_present", False),
                local_prescreen_allowed=row.get("local_prescreen_allowed", False),
                cache_period=row.get("latest_source_cache_period", ""),
                prescreen_period=row.get("latest_prescreen_period", ""),
                prescreen_current=row.get("local_prescreen_current", False),
                allowed_next_action=str(row.get("allowed_next_action", "")).replace("|", "/"),
                blocked_actions=", ".join(_list(row.get("blocked_actions"))),
            )
        )
    return "\n".join(lines) + "\n"


def _build_source_row(
    definition: SourceQueueDefinition,
    *,
    processed_root: Path,
    reports_root: Path,
) -> dict[str, Any]:
    processed_matches = _match_globs(processed_root, definition.processed_globs)
    report_matches = _match_globs(reports_root, definition.report_globs)
    prescreen_matches = _match_globs(reports_root, definition.prescreen_globs)
    period_state = _source_period_state(
        definition=definition,
        processed_matches=processed_matches,
        report_matches=report_matches,
        prescreen_matches=prescreen_matches,
    )
    evidence_present = True
    if definition.evidence_required:
        required_evidence = []
        if definition.processed_globs:
            required_evidence.append(bool(processed_matches))
        if definition.report_globs:
            required_evidence.append(bool(report_matches))
        evidence_present = all(required_evidence) if required_evidence else False
    status = definition.status
    if status == CONDITIONAL_ACTIVE_STATUS:
        status = ACTIVE_STATUS if evidence_present else "source_pending_evidence"
    local_prescreen_allowed = definition.status == ACTIVE_STATUS and evidence_present
    if definition.status == CONDITIONAL_ACTIVE_STATUS:
        local_prescreen_allowed = evidence_present
    return {
        **asdict(definition),
        "status": status,
        "matched_processed_paths": [str(path) for path in processed_matches],
        "matched_report_paths": [str(path) for path in report_matches],
        "matched_prescreen_paths": [str(path) for path in prescreen_matches],
        **period_state,
        "evidence_present": evidence_present,
        "local_prescreen_allowed": local_prescreen_allowed,
    }


def _match_globs(root: Path, patterns: tuple[str, ...]) -> list[Path]:
    if not patterns or not root.exists():
        return []
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(path for path in root.glob(pattern) if path.exists())
    return sorted(set(matches), key=lambda value: str(value))


def _decision_blockers(
    *,
    active_rows: list[dict[str, Any]],
    no_provider_ready_rows: list[dict[str, Any]],
    provider_ready_rows: list[dict[str, Any]],
    provider_request_allowed: bool,
) -> list[str]:
    blockers: list[str] = []
    provider_path_ready = bool(provider_ready_rows and provider_request_allowed)
    if not no_provider_ready_rows and not provider_path_ready:
        blockers.append("no_local_no_provider_source_ready")
    if provider_ready_rows and not provider_request_allowed:
        blockers.append("report_rc_quota_blocked")
    for row in active_rows:
        if row.get("evidence_required") and not row.get("evidence_present"):
            blockers.append(f"active_source_evidence_missing:{row.get('source_id', '')}")
    if not active_rows:
        blockers.append("no_active_source_in_local_queue")
    return _unique_preserving_order(blockers)


def _decision_warnings(
    *,
    no_provider_ready_rows: list[dict[str, Any]],
    provider_ready_rows: list[dict[str, Any]],
    provider_request_allowed: bool,
) -> list[str]:
    warnings: list[str] = []
    if no_provider_ready_rows and provider_ready_rows and not provider_request_allowed:
        warnings.append("report_rc_quota_blocked")
    return warnings


def _next_action(
    *,
    blockers: list[str],
    provider_ready_rows: list[dict[str, Any]],
    provider_request_allowed: bool,
    no_provider_ready_rows: list[dict[str, Any]],
) -> str:
    if any(blocker.startswith("active_source_evidence_missing:") for blocker in blockers):
        return "restore_active_source_evidence_before_factor_batch"
    if no_provider_ready_rows:
        return "run_no_provider_factor_batch_from_ready_local_source"
    if provider_ready_rows and provider_request_allowed:
        return "analyst_monthly_cache_preflight_then_frozen_prescreen"
    if provider_ready_rows:
        return "wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight"
    return "review_local_source_catalog_before_factor_batch"


def _local_prescreen_next_action(
    *,
    local_prescreen_ready_rows: list[dict[str, Any]],
    provider_ready_rows: list[dict[str, Any]],
    provider_request_allowed: bool,
) -> str:
    if not local_prescreen_ready_rows:
        return "restore_active_source_evidence_before_cached_prescreen"
    if any(row.get("local_prescreen_current") is not True for row in local_prescreen_ready_rows):
        if provider_ready_rows and not provider_request_allowed:
            return "run_cached_local_prescreen_then_wait_for_report_rc_quota_reset"
        return "run_cached_local_prescreen"
    if provider_ready_rows and provider_request_allowed:
        return "analyst_monthly_cache_preflight_then_frozen_prescreen"
    if provider_ready_rows and not provider_request_allowed:
        return "local_prescreen_current_wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight"
    return "local_prescreen_current_review_next_source_extension"


def _source_period_state(
    *,
    definition: SourceQueueDefinition,
    processed_matches: list[Path],
    report_matches: list[Path],
    prescreen_matches: list[Path],
) -> dict[str, Any]:
    if definition.source_id != "analyst_report_revision":
        return {
            "latest_source_cache_period": "",
            "latest_prescreen_period": "",
            "local_prescreen_current": False,
        }
    cache_period = _latest_cache_period([*processed_matches, *report_matches])
    prescreen_period = _latest_analyst_prescreen_period(prescreen_matches)
    return {
        "latest_source_cache_period": cache_period,
        "latest_prescreen_period": prescreen_period,
        "local_prescreen_current": bool(cache_period and prescreen_period and prescreen_period >= cache_period),
    }


def _latest_cache_period(paths: list[Path]) -> str:
    periods: list[str] = []
    for path in paths:
        match = re.search(r"analyst_report_revision_cache_(20\d{4})", path.name)
        if match:
            periods.append(match.group(1))
    return max(periods) if periods else ""


def _latest_analyst_prescreen_period(paths: list[Path]) -> str:
    periods: list[str] = []
    for path in paths:
        periods.extend(_prescreen_periods_from_report_json(path))
        periods.extend(_prescreen_periods_from_path_name(path.name))
    return max(periods) if periods else ""


def _prescreen_periods_from_report_json(path: Path) -> list[str]:
    report_path = path / "analyst_report_revision_prescreen.json" if path.is_dir() else path
    if not report_path.exists():
        return []
    try:
        packet = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    max_report_date = str(_dict(packet.get("data_window")).get("max_report_date", ""))
    period = _yyyymm_from_date(max_report_date)
    return [period] if period else []


def _prescreen_periods_from_path_name(name: str) -> list[str]:
    periods: list[str] = []
    for match in re.finditer(r"_(20\d{4})_(20\d{4})_", name):
        periods.append(match.group(2))
    return periods


def _yyyymm_from_date(value: str) -> str:
    match = re.search(r"(20\d{2})[-_/]?([01]\d)", value)
    if not match:
        return ""
    return f"{match.group(1)}{match.group(2)}"


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


def _csv_value(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return "; ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value)


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
