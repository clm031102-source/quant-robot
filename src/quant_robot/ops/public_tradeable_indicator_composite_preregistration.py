from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.factor_mining_candidate_plan_gate import (
    default_cn_stock_pre_mining_control_plan,
    default_cn_stock_promotion_policy,
)


STAGE = "public_tradeable_indicator_composite_preregistration"
ROUND = 264
SOURCE_AUDIT = "docs/research/cn_stock_round263_historical_lead_recovery_audit_2026-06-26.md"
SOURCE_AUDIT_TITLE = "Round263 Historical Lead Recovery Audit"
NEXT_REQUIRED_GATE = "round265_public_tradeable_indicator_composite_long_cycle_residual_prescreen"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
SOURCE_EVIDENCE_STATUS = "public_indicator_composite_preregistered_not_empirical_alpha"

PUBLIC_REFERENCE_PROJECTS = (
    "alphalens",
    "vectorbt",
    "qlib",
    "pyfolio",
    "worldquant_101_alphas",
)
STATIC_CHECKS = ("qtype", "lookahead_shift_audit", "candidate_plan_gate")
FORBIDDEN_OR_HIBERNATED_FAMILIES = {
    "public_supertrend",
    "public_trend_volume_single_filter",
    "daily_basic_low_turnover_repair_after_round263_recovery_audit_failure",
    "market_residual_public_technical_after_round263_redundancy_or_2015_failure",
    "public_formula_alpha101_after_round263_quantile_shape_failure",
    "qlib_alpha158_public_reference_after_round263_redundancy_failure",
    "smart_money_flow_public_reference_after_round263_low_icir_quantile_failure",
}
DEFAULT_CAPACITY_FILTERS: dict[str, Any] = {
    "exclude_st": True,
    "exclude_suspended": True,
    "exclude_limit_up_down_if_untradable": True,
    "min_listing_days": 120,
    "min_signal_date_amount": 10_000_000,
    "max_position_adv_participation": 0.01,
    "require_calendar_holding_gate": True,
    "require_extreme_trade_diagnostic": True,
}


@dataclass(frozen=True)
class PublicTradeableIndicatorCompositeCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    hypothesis_source: str
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    capacity_filters: dict[str, Any] | None = None
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_public_tradeable_indicator_composite_candidate_specs() -> list[PublicTradeableIndicatorCompositeCandidateSpec]:
    return [
        PublicTradeableIndicatorCompositeCandidateSpec(
            factor_name="mfi_cmf_exhaustion_reversal_liquid_14_20",
            family="trend_exhaustion_reversal_composite",
            formula_template="0.35*cs_z(mfi_reversal_14)+0.30*cs_z(-cmf_20)+0.20*cs_z(-return_5)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 14, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            hypothesis_source="public_indicator_composite:mfi_cmf_exhaustion_reversal",
            economic_rationale=(
                "MFI and Chaikin money flow are public volume-price indicators; the candidate tests exhaustion "
                "reversal only when liquidity is adequate, not a blind low-turnover or moneyflow selection rule."
            ),
            public_reference_tags=("alphalens", "vectorbt", "pyfolio"),
            expected_failure_modes=("volume_indicator_lag", "quantile_shape_failure", "capacity_tail"),
        ),
        PublicTradeableIndicatorCompositeCandidateSpec(
            factor_name="supertrend_pullback_absorption_quality_10_3_20",
            family="trend_exhaustion_reversal_composite",
            formula_template="0.35*cs_z(supertrend_distance_reversal_10_3)+0.30*cs_z(obv_absorption_20)+0.20*cs_z(-atr_ratio_20)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(10, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            hypothesis_source="public_indicator_composite:supertrend_pullback_with_absorption",
            economic_rationale=(
                "Supertrend is only a state component here. It must agree with volume absorption, ATR risk, and "
                "liquidity, avoiding re-entry into the old single SuperTrend grid."
            ),
            public_reference_tags=("vectorbt", "alphalens", "qlib"),
            expected_failure_modes=("single_indicator_reentry", "trend_chop_instability", "same_cluster_redundancy"),
        ),
        PublicTradeableIndicatorCompositeCandidateSpec(
            factor_name="obv_cmf_absorption_reversal_quality_20",
            family="volume_price_absorption_composite",
            formula_template="0.40*cs_z(obv_absorption_20)+0.30*cs_z(-cmf_20)+0.20*cs_z(-downside_vol_20)+0.10*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            hypothesis_source="public_indicator_composite:obv_cmf_absorption_reversal",
            economic_rationale=(
                "OBV and CMF are public accumulation indicators; this tests whether absorption plus lower downside "
                "risk predicts recovery after strict residual and reference overlap checks."
            ),
            public_reference_tags=("vectorbt", "alphalens", "worldquant_101_alphas"),
            expected_failure_modes=("obv_redundancy", "weak_icir", "turnover_cost"),
        ),
        PublicTradeableIndicatorCompositeCandidateSpec(
            factor_name="volume_dryup_pullback_liquid_reversal_5_20",
            family="volume_price_absorption_composite",
            formula_template="0.40*cs_z(-return_5)+0.30*cs_z(-amount_trend_5_20)+0.20*cs_z(-realized_vol_20)+0.10*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            hypothesis_source="public_indicator_composite:volume_dryup_pullback_reversal",
            economic_rationale=(
                "A pullback with volume dry-up can indicate seller exhaustion, but the liquidity term is fixed "
                "up front to avoid reviving the failed low-turnover tail."
            ),
            public_reference_tags=("alphalens", "pyfolio", "qlib"),
            expected_failure_modes=("low_turnover_tail", "capacity_tail", "yearly_instability"),
        ),
        PublicTradeableIndicatorCompositeCandidateSpec(
            factor_name="atr_bandwidth_compression_breakout_quality_20",
            family="volatility_compression_breakout_quality",
            formula_template="0.35*cs_z(-atr_ratio_20)+0.30*cs_z(-bollinger_bandwidth_20)+0.20*cs_z(return_efficiency_20)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount"),
            hypothesis_source="public_indicator_composite:atr_bandwidth_compression_quality",
            economic_rationale=(
                "ATR and Bollinger bandwidth compression are public volatility-state indicators. The thesis is "
                "clean compression with efficient price path, not raw range-contraction reuse."
            ),
            public_reference_tags=("vectorbt", "alphalens", "qlib"),
            expected_failure_modes=("range_contraction_redundancy", "twenty_fifteen_regime_dependency", "false_breakout"),
        ),
        PublicTradeableIndicatorCompositeCandidateSpec(
            factor_name="donchian_atr_compression_breakout_efficiency_20",
            family="volatility_compression_breakout_quality",
            formula_template="0.35*cs_z(donchian_position_20)+0.30*cs_z(-atr_ratio_20)+0.20*cs_z(return_efficiency_20)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount"),
            hypothesis_source="public_indicator_composite:donchian_atr_breakout_efficiency",
            economic_rationale=(
                "Donchian location is paired with ATR compression and path efficiency to test tradeable breakout "
                "quality, with 2015 contribution and reference overlap required before portfolio use."
            ),
            public_reference_tags=("vectorbt", "alphalens", "pyfolio"),
            expected_failure_modes=("breakout_false_positive", "market_beta_disguise", "drawdown_tail"),
        ),
        PublicTradeableIndicatorCompositeCandidateSpec(
            factor_name="adx_efficiency_momentum_quality_14_20",
            family="risk_adjusted_momentum_quality",
            formula_template="0.35*cs_z(adx_trend_strength_14)+0.30*cs_z(return_efficiency_20)+0.20*cs_z(skip5_momentum_20)+0.15*cs_z(-realized_vol_20)",
            direction="higher_is_better",
            windows=(5, 14, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            hypothesis_source="public_indicator_composite:adx_efficiency_momentum_quality",
            economic_rationale=(
                "ADX trend strength is accepted only with path efficiency and volatility control, reducing the "
                "risk that the signal is just broad market beta."
            ),
            public_reference_tags=("vectorbt", "qlib", "alphalens"),
            expected_failure_modes=("momentum_crash", "market_beta_disguise", "regime_dependency"),
        ),
        PublicTradeableIndicatorCompositeCandidateSpec(
            factor_name="macd_rsi_momentum_exhaustion_quality_14_26",
            family="risk_adjusted_momentum_quality",
            formula_template="0.30*cs_z(macd_hist_z_26)+0.30*cs_z(rsi_midline_reclaim_14)+0.25*cs_z(return_efficiency_20)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(14, 20, 26),
            required_fields=("adj_close", "amount"),
            hypothesis_source="public_indicator_composite:macd_rsi_exhaustion_quality",
            economic_rationale=(
                "MACD and RSI are common public indicators; the pre-registered version tests reclaim quality "
                "rather than tuning indicator thresholds after seeing returns."
            ),
            public_reference_tags=("vectorbt", "alphalens", "pyfolio"),
            expected_failure_modes=("indicator_lag", "parameter_fragility", "weak_quantile_monotonicity"),
        ),
    ]


def build_public_tradeable_indicator_composite_preregistration(
    *,
    min_candidates: int = 8,
    min_families: int = 4,
    candidate_specs: Iterable[PublicTradeableIndicatorCompositeCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_public_tradeable_indicator_composite_candidate_specs())
    candidates = [_candidate_payload(spec) for spec in specs]
    blockers = _blockers(candidates, min_candidates=min_candidates, min_families=min_families)
    research_control_plan = default_cn_stock_pre_mining_control_plan()
    research_control_plan["policy"] = (
        "Round264 may only generate CN stock public-indicator composite candidates after data-source availability, "
        "Round263 recovery-audit failure review, PIT/long-cycle coverage, 2015 diagnostics, and candidate plan gate clearance."
    )
    promotion_policy = default_cn_stock_promotion_policy()
    promotion_policy["next_allowed_action"] = NEXT_REQUIRED_GATE
    result: dict[str, Any] = {
        "stage": STAGE,
        "round": ROUND,
        "generated_at": date.today().isoformat(),
        "source_audit": SOURCE_AUDIT,
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "round": ROUND,
            "candidate_count": len(candidates),
            "min_candidates": min_candidates,
            "family_count": len({candidate["family"] for candidate in candidates}),
            "min_families": min_families,
            "unique_candidate_names": len({candidate["factor_name"] for candidate in candidates}),
            "portfolio_backtest_allowed_candidates": sum(
                1 for candidate in candidates if candidate["portfolio_backtest_allowed"]
            ),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": NEXT_REQUIRED_GATE,
        },
        "public_reference_review": {
            "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
            "static_checks": list(STATIC_CHECKS),
            "method": (
                "Use public indicators as economic hypotheses only. Composite construction is fixed before "
                "screening; no single-indicator SuperTrend/OBV/Alpha101 re-entry is allowed."
            ),
        },
        "research_control_plan": research_control_plan,
        "family_rotation_policy": {
            "current_family_id": "public_tradeable_indicator_composite",
            "current_family_round_count": 1,
            "max_rounds_before_review": 3,
            "three_round_review_completed": False,
            "hibernated_families": sorted(FORBIDDEN_OR_HIBERNATED_FAMILIES),
            "blocked_families": [],
        },
        "audit_policy": {
            "analysis_start_date": "2015-01-01",
            "analysis_end_date": "2025-12-31",
            "final_holdout_start": "2026-01-01",
            "final_holdout_use": "excluded_from_tuning_and_prescreen",
            "parameter_expansion_allowed": False,
            "direction_flip_allowed": False,
            "portfolio_grid_allowed": False,
            "twenty_fifteen_risk_diagnostic_required": True,
            "reference_overlap_audit_required": True,
        },
        "capacity_policy": {
            "filters": DEFAULT_CAPACITY_FILTERS,
            "reason": "Every candidate must be liquid enough for later cost/capacity preflight before any portfolio grid.",
        },
        "evaluation_gate": {
            "next_required_gate": NEXT_REQUIRED_GATE,
            "required_metrics": [
                "long_cycle_raw_ic",
                "industry_neutral_ic",
                "size_liquidity_vol_residual_ic",
                "quantile_spread",
                "quantile_monotonicity",
                "factor_turnover",
                "reference_overlap",
                "twenty_fifteen_regime_contribution",
                "capacity_participation",
                "final_holdout_excluded",
            ],
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "promotion_policy": promotion_policy,
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_public_tradeable_indicator_composite_preregistration_markdown(result)
    return result


def write_public_tradeable_indicator_composite_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "public_tradeable_indicator_composite_preregistration.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_tradeable_indicator_composite_preregistration.md").write_text(
        render_public_tradeable_indicator_composite_preregistration_markdown(result),
        encoding="utf-8",
    )
    rows = _candidate_csv_rows(result)
    with (output_path / "public_tradeable_indicator_composite_candidates.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def render_public_tradeable_indicator_composite_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = _dict(result.get("summary"))
    lines = [
        "# Public Tradeable Indicator Composite Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Round: {result.get('round', ROUND)}",
        f"- Source audit: {SOURCE_AUDIT_TITLE} (`{result.get('source_audit', SOURCE_AUDIT)}`)",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- Blockers: {', '.join(_list(summary.get('blockers'))) or 'none'}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Portfolio backtest allowed before prescreen: {_dict(result.get('promotion_policy')).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Promotion allowed: {_dict(result.get('promotion_policy')).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Method",
        "",
        f"- Public projects reviewed: {', '.join(_list(_dict(result.get('public_reference_review')).get('projects_reviewed')))}",
        f"- Static checks: {', '.join(_list(_dict(result.get('public_reference_review')).get('static_checks')))}",
        f"- Method: {_dict(result.get('public_reference_review')).get('method', '')}",
        "",
        "## Candidates",
        "",
        "| Factor | Family | Direction | Windows | Public refs | Expected failure modes |",
        "|---|---|---|---|---|---|",
    ]
    for candidate in _list_of_dicts(result.get("candidates")):
        lines.append(
            "| {name} | {family} | {direction} | {windows} | {refs} | {failures} |".format(
                name=candidate.get("factor_name", ""),
                family=candidate.get("family", ""),
                direction=candidate.get("direction", ""),
                windows=", ".join(_list(candidate.get("windows"))),
                refs=", ".join(_list(candidate.get("public_reference_tags"))),
                failures=", ".join(_list(candidate.get("expected_failure_modes"))),
            )
        )
    return "\n".join(lines) + "\n"


def _candidate_payload(spec: PublicTradeableIndicatorCompositeCandidateSpec) -> dict[str, Any]:
    capacity_filters = dict(DEFAULT_CAPACITY_FILTERS)
    if spec.capacity_filters:
        capacity_filters.update(spec.capacity_filters)
    return {
        "factor_name": spec.factor_name,
        "family": spec.family,
        "market": "CN",
        "asset_type": "stock",
        "registration_status": "pre_registered",
        "formula_template": spec.formula_template,
        "direction": spec.direction,
        "windows": list(spec.windows),
        "required_fields": list(spec.required_fields),
        "hypothesis_source": spec.hypothesis_source,
        "economic_rationale": spec.economic_rationale,
        "public_reference_tags": list(spec.public_reference_tags),
        "expected_failure_modes": list(spec.expected_failure_modes),
        "capacity_filters": capacity_filters,
        "source_evidence_status": spec.source_evidence_status,
        "next_required_gate": NEXT_REQUIRED_GATE,
        "regime_diagnostics_required": True,
        "twenty_fifteen_risk_diagnostic_required": True,
        "reference_overlap_audit_required": True,
        "portfolio_backtest_allowed": spec.portfolio_backtest_allowed,
        "promotion_allowed": spec.promotion_allowed,
    }


def _blockers(candidates: list[dict[str, Any]], *, min_candidates: int, min_families: int) -> list[str]:
    blockers: list[str] = []
    names = [str(candidate.get("factor_name", "")) for candidate in candidates]
    families = [str(candidate.get("family", "")) for candidate in candidates]
    if len(candidates) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len(set(names)) != len(names):
        blockers.append("duplicate_candidate_names")
    if len(set(families)) < min_families:
        blockers.append("family_breadth_below_minimum")
    for family in sorted(set(families) & FORBIDDEN_OR_HIBERNATED_FAMILIES):
        blockers.append(f"forbidden_or_hibernated_family_present:{family}")
    for candidate in candidates:
        if not str(candidate.get("hypothesis_source", "")).startswith("public_indicator_composite:"):
            blockers.append("candidate_hypothesis_source_not_public_indicator_composite")
        if bool(candidate.get("portfolio_backtest_allowed")):
            blockers.append("candidate_portfolio_backtest_allowed_before_prescreen")
        if bool(candidate.get("promotion_allowed")):
            blockers.append("candidate_promotion_allowed_before_validation")
    return _unique_preserving_order(blockers)


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "factor_name": candidate.get("factor_name", ""),
            "family": candidate.get("family", ""),
            "direction": candidate.get("direction", ""),
            "windows": ";".join(_list(candidate.get("windows"))),
            "required_fields": ";".join(_list(candidate.get("required_fields"))),
            "hypothesis_source": candidate.get("hypothesis_source", ""),
            "portfolio_backtest_allowed": candidate.get("portfolio_backtest_allowed", False),
            "promotion_allowed": candidate.get("promotion_allowed", False),
            "expected_failure_modes": ";".join(_list(candidate.get("expected_failure_modes"))),
        }
        for candidate in _list_of_dicts(result.get("candidates"))
    ]


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
