from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    DEFAULT_CAPACITY_FILTERS,
    SAFETY,
    CapacitySafePriceVolumeCandidateSpec,
    build_capacity_safe_price_volume_preregistration,
)


STAGE = "public_alpha101_capacity_safe_preregistration"
ROUND113_SOURCE_AUDIT = "docs/research/cn_stock_round110_112_three_round_review_2026-06-22.md"
ROUND115_NEXT_DIRECTION = "round115_public_alpha101_ic_quantile_turnover_prescreen"
SOURCE_EVIDENCE_STATUS = "public_formula_preregistered_not_empirical_alpha"
PUBLIC_ALPHA101_REFERENCES = (
    "worldquant_101_alphas",
    "qlib_alpha158_alpha360",
    "alphalens",
    "vectorbt",
    "pyfolio",
)


def default_public_alpha101_candidate_specs() -> list[CapacitySafePriceVolumeCandidateSpec]:
    return [
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="alpha101_intraday_close_position_reversal",
            family="public_formula_intraday_reversal",
            formula_template="-1.00*cs_z((adj_close-open)/(high-low+1e-6))+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(1, 20),
            required_fields=("adj_close", "open", "high", "low", "amount"),
            economic_rationale=(
                "Formulaic-alpha families often use the close location within the intraday range. This "
                "candidate tests whether same-day close-strength is better treated as a next-period fade "
                "after liquidity control."
            ),
            public_reference_tags=("worldquant_101_alphas", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="alpha101_gap_fade_amount_confirmed_5_20",
            family="public_formula_gap_reversal",
            formula_template="0.60*cs_z(-(open/prev_adj_close-1))+0.25*cs_z(-amount_z_20)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "open", "amount"),
            economic_rationale=(
                "Gap-fade signals are public technical hypotheses. Amount confirmation is pre-registered so "
                "the later prescreen can reject gap moves that only work in untradeable tails."
            ),
            public_reference_tags=("worldquant_101_alphas", "qlib_alpha158_alpha360", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="alpha101_price_volume_corr_reversal_20",
            family="public_formula_price_volume_corr",
            formula_template="-0.70*cs_z(ts_corr(cs_rank(return_1),cs_rank(amount_return_1),20))+0.30*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Many public formulaic alphas combine cross-sectional ranks with price-volume correlations. "
                "This registers the negative correlation side as a hypothesis, not promotion evidence."
            ),
            public_reference_tags=("worldquant_101_alphas", "alphalens", "qlib_alpha158_alpha360"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="alpha101_vwap_proxy_reversion_liquid_20",
            family="public_formula_vwap_reversion",
            formula_template="0.65*cs_z(-(adj_close/vwap_proxy_20-1))+0.35*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount", "volume"),
            economic_rationale=(
                "VWAP-relative reversion is common in public formula libraries. This version uses a daily "
                "amount/volume proxy and demands liquidity before any portfolio test."
            ),
            public_reference_tags=("worldquant_101_alphas", "vectorbt", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="alpha101_decay_rank_reversal_10",
            family="public_formula_decay_rank",
            formula_template="0.75*cs_z(decay_linear(cs_rank(-return_5),10))+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 10),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Formulaic-alpha designs often smooth ranked inputs with a decay operator. This tests whether "
                "a short reversal signal remains after decayed ranking and capacity control."
            ),
            public_reference_tags=("worldquant_101_alphas", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="alpha101_amount_shock_exhaustion_5_20",
            family="public_formula_amount_exhaustion",
            formula_template="0.55*cs_z(-return_5)+0.30*cs_z(-amount_z_20)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "High amount after short price pressure can mark exhaustion, but the liquidity term keeps the "
                "test away from the old capacity-blind low-turnover failure mode."
            ),
            public_reference_tags=("worldquant_101_alphas", "qlib_alpha158_alpha360", "pyfolio"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="alpha101_open_close_pressure_fade_10",
            family="public_formula_open_close_pressure",
            formula_template="-0.70*cs_z(ts_mean((adj_close-open)/(open+1e-6),10))+0.30*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(10,),
            required_fields=("adj_close", "open", "amount"),
            economic_rationale=(
                "Open-to-close pressure is a public intraday-bar feature. This candidate asks whether repeated "
                "positive pressure is overextended and later mean-reverts."
            ),
            public_reference_tags=("worldquant_101_alphas", "qlib_alpha158_alpha360", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="alpha101_range_compression_liquid_20",
            family="public_formula_range_compression",
            formula_template="-0.55*cs_z(ts_mean((high-low)/(adj_close+1e-6),20))-0.15*cs_z(realized_vol_20)+0.30*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "Range compression is a public volatility/range idea. This registration keeps it distinct from "
                "the blocked market-residual lead and requires later redundancy checks."
            ),
            public_reference_tags=("worldquant_101_alphas", "qlib_alpha158_alpha360", "vectorbt"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="qlib_alpha158_return_std_position_blend_20",
            family="qlib_alpha158_feature_blend",
            formula_template="0.45*cs_z(-return_5)+0.25*cs_z(-realized_vol_20)+0.20*cs_z(kbar_close_position_20)+0.10*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "Qlib-style Alpha158 features combine return, volatility, and candlestick-position features. "
                "This blend is preregistered as a compact candidate rather than a broad feature sweep."
            ),
            public_reference_tags=("qlib_alpha158_alpha360", "alphalens", "pyfolio"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="alpha101_volume_rank_divergence_20",
            family="public_formula_volume_rank_divergence",
            formula_template="-0.60*cs_z(ts_corr(cs_rank(adj_close),cs_rank(amount),20))+0.25*cs_z(-return_5)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Ranked price-volume divergence appears frequently in formulaic alpha libraries. This version "
                "adds reversal and liquidity gates before any long-only portfolio conversion."
            ),
            public_reference_tags=("worldquant_101_alphas", "qlib_alpha158_alpha360", "alphalens"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
    ]


def build_public_alpha101_capacity_safe_preregistration(
    *,
    min_candidates: int = 10,
    candidate_specs: Iterable[CapacitySafePriceVolumeCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_public_alpha101_candidate_specs())
    result = build_capacity_safe_price_volume_preregistration(
        min_candidates=min_candidates,
        candidate_specs=specs,
    )
    result["stage"] = STAGE
    result["summary"]["next_required_gate"] = ROUND115_NEXT_DIRECTION
    for candidate in result.get("candidates", []) or []:
        candidate["next_required_gate"] = ROUND115_NEXT_DIRECTION
        candidate["source_evidence_status"] = SOURCE_EVIDENCE_STATUS
    result["public_formula_context"] = {
        "source_audit": ROUND113_SOURCE_AUDIT,
        "source_rounds": "round110_market_residual_prereg_round111_prescreen_round112_dedup_round113_review",
        "evidence_status": "family_rotation_after_market_residual_blockers",
        "translation_policy": (
            "Translate public Alpha101/Qlib-style operators into CN stock daily OHLCV/amount features; "
            "do not eval arbitrary formulas and do not tune parameters after seeing prescreen results."
        ),
        "anti_overfit_policy": (
            "Curate a fixed 10-candidate set before measurement, count all candidates in multiple-testing "
            "accounting, and block portfolio grids until Round115 IC/quantile/turnover/capacity evidence exists."
        ),
        "final_holdout_policy": "Do not touch 2026 final holdout during preregistration or Round115 prescreen.",
    }
    result["family_rotation_context"] = {
        "previous_blockers": [
            "round112_reference_redundancy",
            "round112_high_market_or_liquidity_exposure",
            "round112_2015_regime_failure",
            "round112_yearly_ic_instability",
        ],
        "rotated_away_from": [
            "market_residual_risk_premia_same_family_continuation",
            "beta_adjusted_range_contraction_portfolio_grid",
            "random_alpha101_formula_search",
        ],
        "next_direction": ROUND115_NEXT_DIRECTION,
    }
    result["public_reference_review"] = {
        "projects_reviewed": list(PUBLIC_ALPHA101_REFERENCES),
        "method": (
            "Use public formulaic-alpha and Qlib feature families as hypothesis sources only. The project "
            "translation layer keeps candidates small, named, capacity-aware, and blocked from promotion "
            "until long-cycle prescreen evidence exists."
        ),
        "source_urls": [
            "https://arxiv.org/abs/1601.00991",
            "https://github.com/microsoft/qlib",
        ],
    }
    result["capacity_policy"] = {
        "filters": DEFAULT_CAPACITY_FILTERS,
        "reason": (
            "A-share stock formula factors must not repeat the prior low-turnover/capacity illusion; every "
            "candidate carries minimum signal-date amount and participation limits before portfolio work."
        ),
    }
    result["evaluation_gate"]["next_required_gate"] = ROUND115_NEXT_DIRECTION
    result["promotion_policy"]["next_allowed_action"] = (
        "Run Round115 public Alpha101 IC/quantile/turnover/capacity prescreen with long-cycle data; "
        "portfolio grid and promotion remain blocked."
    )
    result["summary"]["next_direction"] = ROUND115_NEXT_DIRECTION
    result["markdown"] = render_public_alpha101_capacity_safe_preregistration_markdown(result)
    return result


def write_public_alpha101_capacity_safe_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "public_alpha101_capacity_safe_preregistration.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_alpha101_capacity_safe_preregistration.md").write_text(
        render_public_alpha101_capacity_safe_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "public_alpha101_capacity_safe_candidates.csv", _candidate_csv_rows(result))


def render_public_alpha101_capacity_safe_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    context = result.get("public_formula_context", {})
    rotation = result.get("family_rotation_context", {})
    reference = result.get("public_reference_review", {})
    lines = [
        "# Public Alpha101 Capacity-Safe Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next required gate: {summary.get('next_required_gate', ROUND115_NEXT_DIRECTION)}",
        f"- Next direction: {rotation.get('next_direction', ROUND115_NEXT_DIRECTION)}",
        f"- Portfolio backtest allowed before prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Public Formula Context",
        "",
        f"- Source audit: {context.get('source_audit', ROUND113_SOURCE_AUDIT)}",
        f"- Evidence status: {context.get('evidence_status', '')}",
        f"- Translation policy: {context.get('translation_policy', '')}",
        f"- Anti-overfit policy: {context.get('anti_overfit_policy', '')}",
        f"- Final holdout policy: {context.get('final_holdout_policy', '')}",
        "",
        "## Public Reference Review",
        "",
        "- Projects reviewed: " + ", ".join(reference.get("projects_reviewed", []) or []),
        f"- Method: {reference.get('method', '')}",
        "- Source URLs: " + ", ".join(reference.get("source_urls", []) or []),
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
