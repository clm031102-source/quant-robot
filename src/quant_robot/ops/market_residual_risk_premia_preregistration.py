from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    NEXT_REQUIRED_GATE,
    PUBLIC_REFERENCE_PROJECTS,
    SAFETY,
    CapacitySafePriceVolumeCandidateSpec,
    build_capacity_safe_price_volume_preregistration,
)


STAGE = "market_residual_risk_premia_preregistration"
ROUND107_109_SOURCE_AUDIT = "docs/research/cn_stock_round107_109_three_round_review_2026-06-22.md"
ROUND110_NEXT_DIRECTION = "round111_market_residual_risk_premia_prescreen"
SOURCE_EVIDENCE_STATUS = "round107_109_family_rotation_after_redundancy_and_zero_leads"


def default_market_residual_risk_premia_candidate_specs() -> list[CapacitySafePriceVolumeCandidateSpec]:
    return [
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="low_beta_120",
            family="market_beta_low",
            formula_template="-1.00*cs_z(rolling_beta_120)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(120,),
            required_fields=("adj_close", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "Low-beta and betting-against-beta effects are public risk-premia ideas. This candidate "
                "tests low market exposure directly before any portfolio construction."
            ),
            public_reference_tags=("factor_model", "alphalens", "pyfolio"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="downside_beta_low_120",
            family="downside_beta_low",
            formula_template="-0.80*cs_z(downside_beta_120)-0.20*cs_z(downside_residual_vol_60)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(60, 120),
            required_fields=("adj_close", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "Downside beta isolates crash participation instead of rewarding generic low volatility. "
                "The thesis is that lower downside market sensitivity may be rewarded after costs."
            ),
            public_reference_tags=("factor_model", "alphalens", "vectorbt"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="idio_vol_low_60",
            family="idiosyncratic_volatility_low",
            formula_template="-0.75*cs_z(residual_vol_60)-0.15*cs_z(abs(residual_return_20))+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "The low idiosyncratic volatility anomaly is public, but this registration forces the "
                "volatility estimate to be market-residual rather than raw price volatility."
            ),
            public_reference_tags=("factor_model", "alphalens", "qlib"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="residual_reversal_5_60",
            family="market_residual_reversal",
            formula_template="0.70*cs_z(-residual_return_5)+0.20*cs_z(-residual_vol_60)+0.10*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 60),
            required_fields=("adj_close", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "Short reversal has repeatedly mixed with raw price-volume effects. This candidate tests "
                "whether reversal remains after removing market beta."
            ),
            public_reference_tags=("factor_model", "worldquant_101_alphas", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="residual_momentum_quality_20_120",
            family="market_residual_momentum",
            formula_template="0.55*cs_z(residual_momentum_120_skip20)+0.25*cs_z(residual_return_efficiency_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 120),
            required_fields=("adj_close", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "Momentum can be disguised market beta. This candidate keeps only residual momentum with "
                "path quality and liquidity before later IC screening."
            ),
            public_reference_tags=("factor_model", "qlib", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="low_market_corr_60",
            family="market_correlation_low",
            formula_template="-0.70*cs_z(market_corr_60)-0.20*cs_z(residual_vol_60)+0.10*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(60,),
            required_fields=("adj_close", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "Low market correlation may identify stock-specific return streams rather than another "
                "version of broad market exposure."
            ),
            public_reference_tags=("factor_model", "alphalens", "pyfolio"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="crash_resilience_60",
            family="crash_resilience",
            formula_template="-0.50*cs_z(co_crash_days_60)-0.30*cs_z(downside_residual_vol_60)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(60,),
            required_fields=("adj_close", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "Crash-resilience counts co-crash behavior with the equal-weight market proxy, then penalizes "
                "downside residual volatility before any return-claim is made."
            ),
            public_reference_tags=("factor_model", "pyfolio", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="beta_adjusted_range_contraction_60",
            family="beta_adjusted_range_contraction",
            formula_template="-0.45*cs_z(beta_adjusted_hl_range_60)-0.35*cs_z(residual_vol_60)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(60,),
            required_fields=("adj_close", "high", "low", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "Prior range contraction was easy to confound with raw volatility. This version measures "
                "range contraction after accounting for market exposure."
            ),
            public_reference_tags=("factor_model", "vectorbt", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="downside_residual_vol_low_60",
            family="downside_residual_volatility_low",
            formula_template="-0.80*cs_z(downside_residual_vol_60)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(60,),
            required_fields=("adj_close", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "This candidate separates downside stock-specific noise from market selloff participation, "
                "then requires capacity-aware prescreening before use."
            ),
            public_reference_tags=("factor_model", "alphalens", "qlib"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="positive_residual_skew_60",
            family="positive_residual_skew",
            formula_template="0.70*cs_z(residual_skew_60)-0.20*cs_z(residual_vol_60)+0.10*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(60,),
            required_fields=("adj_close", "amount", "market_equal_weight_return"),
            economic_rationale=(
                "Positive residual skew tests whether stocks with more favorable stock-specific upside tails "
                "rank better than symmetric or downside-skewed residual return streams."
            ),
            public_reference_tags=("factor_model", "alphalens", "pyfolio"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
    ]


def build_market_residual_risk_premia_preregistration(
    *,
    min_candidates: int = 8,
    candidate_specs: Iterable[CapacitySafePriceVolumeCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_market_residual_risk_premia_candidate_specs())
    result = build_capacity_safe_price_volume_preregistration(
        min_candidates=min_candidates,
        candidate_specs=specs,
    )
    result["stage"] = STAGE
    result["factor_model_context"] = {
        "source_audit": ROUND107_109_SOURCE_AUDIT,
        "source_rounds": "round107_negative_ic_prescreen_round108_dedup_round109_gap_prescreen",
        "evidence_status": "family_rotation_required_not_promotion_evidence",
        "market_proxy_policy": (
            "Build an equal_weight_market_proxy from same-date eligible CN stock returns, then use only "
            "rolling information available at the signal date for beta, residual, and correlation estimates."
        ),
        "residualization_policy": (
            "Do not claim alpha from raw returns until market beta, downside beta, residual volatility, "
            "and residual return structure have been separately measured."
        ),
        "final_holdout_policy": "Do not touch 2026 final holdout during preregistration or prescreen.",
    }
    result["family_rotation_context"] = {
        "previous_blockers": [
            "round108_hard_redundancy_with_price_volume_cluster",
            "round109_zero_research_leads_after_gap_prescreen",
            "fdr_significant_but_weak_icir_not_promotion_evidence",
        ],
        "rotated_away_from": [
            "negative_ic_trend_accumulation_continuation",
            "overnight_intraday_gap_parameter_tuning",
            "topn_portfolio_grid_before_residual_prescreen",
        ],
        "next_direction": ROUND110_NEXT_DIRECTION,
    }
    result["public_reference_review"] = {
        "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS) + ["factor_model_construction"],
        "method": (
            "Use public factor model, low-beta, downside-beta, residual momentum/reversal, Alphalens/qlib "
            "prescreening, and pyfolio/vectorbt risk attribution ideas as hypotheses only."
        ),
    }
    result["promotion_policy"]["next_allowed_action"] = (
        "Build the market-residual factor matrix and run IC/quantile/turnover/capacity prescreen; "
        "top-N portfolio work remains blocked_before_prescreen."
    )
    result["summary"]["next_direction"] = ROUND110_NEXT_DIRECTION
    result["markdown"] = render_market_residual_risk_premia_preregistration_markdown(result)
    return result


def write_market_residual_risk_premia_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "market_residual_risk_premia_preregistration.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "market_residual_risk_premia_preregistration.md").write_text(
        render_market_residual_risk_premia_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "market_residual_risk_premia_candidates.csv", _candidate_csv_rows(result))


def render_market_residual_risk_premia_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    context = result.get("factor_model_context", {})
    rotation = result.get("family_rotation_context", {})
    lines = [
        "# Market Residual Risk Premia Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Next direction: {rotation.get('next_direction', ROUND110_NEXT_DIRECTION)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Factor Model Context",
        "",
        f"- Source audit: {context.get('source_audit', ROUND107_109_SOURCE_AUDIT)}",
        f"- Evidence status: {context.get('evidence_status', '')}",
        f"- Market proxy policy: {context.get('market_proxy_policy', '')}",
        f"- Residualization policy: {context.get('residualization_policy', '')}",
        f"- Final holdout policy: {context.get('final_holdout_policy', '')}",
        "",
        "## Rotation Context",
        "",
        "- Previous blockers: " + ", ".join(rotation.get("previous_blockers", []) or []),
        "- Rotated away from: " + ", ".join(rotation.get("rotated_away_from", []) or []),
        "",
        "## Candidates",
        "",
        "| Factor | Family | Direction | Windows | Public refs | Required fields |",
        "|---|---|---|---|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(
            "| {name} | {family} | {direction} | {windows} | {refs} | {fields} |".format(
                name=candidate["factor_name"],
                family=candidate["family"],
                direction=candidate["direction"],
                windows=", ".join(str(window) for window in candidate.get("windows", []) or []),
                refs=", ".join(candidate.get("public_reference_tags", []) or []),
                fields=", ".join(candidate.get("required_fields", []) or []),
            )
        )
    return "\n".join(lines) + "\n"


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in result.get("candidates", []) or []:
        rows.append(
            {
                "factor_name": candidate["factor_name"],
                "family": candidate["family"],
                "direction": candidate["direction"],
                "windows": ",".join(str(window) for window in candidate.get("windows", []) or []),
                "required_fields": ",".join(candidate.get("required_fields", []) or []),
                "public_reference_tags": ",".join(candidate.get("public_reference_tags", []) or []),
                "source_evidence_status": candidate["source_evidence_status"],
                "registration_status": candidate["registration_status"],
                "next_required_gate": candidate["next_required_gate"],
                "portfolio_backtest_allowed": candidate["portfolio_backtest_allowed"],
                "promotion_allowed": candidate["promotion_allowed"],
                "min_signal_date_amount": candidate["capacity_filters"]["min_signal_date_amount"],
                "max_position_adv_participation": candidate["capacity_filters"]["max_position_adv_participation"],
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


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
