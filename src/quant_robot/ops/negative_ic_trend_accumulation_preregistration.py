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


STAGE = "negative_ic_trend_accumulation_preregistration"
ROUND105_SOURCE_AUDIT = "docs/research/cn_stock_capacity_safe_trend_accumulation_prescreen_round105_2026-06-22.md"
ROUND106_NEXT_DIRECTION = "round107_negative_ic_trend_accumulation_prescreen"
SOURCE_EVIDENCE_STATUS = "round105_negative_ic_hypothesis_not_promotion"


def default_negative_ic_trend_accumulation_candidate_specs() -> list[CapacitySafePriceVolumeCandidateSpec]:
    return [
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="anti_volume_weighted_momentum_quality_20",
            family="anti_overheat_volume_weighted_trend",
            formula_template="-0.50*cs_z(volume_weighted_return_20)-0.30*cs_z(return_efficiency_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Round105 found volume-weighted trend quality had strong negative IC. This candidate tests "
                "whether avoiding late-stage volume-weighted trend while retaining liquidity is useful."
            ),
            public_reference_tags=("alphalens", "qlib", "worldquant_101_alphas"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="anti_money_pressure_efficiency_20",
            family="anti_overheat_money_pressure",
            formula_template="-0.55*cs_z(money_pressure_20)-0.25*cs_z(return_efficiency_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "High directional return per traded amount behaved like crowded pressure in Round105. "
                "The inverse tests overreaction avoidance, not promotion-ready alpha."
            ),
            public_reference_tags=("worldquant_101_alphas", "alphalens", "vectorbt"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="anti_accumulation_distribution_pressure_20",
            family="anti_overheat_accumulation_distribution",
            formula_template="-0.50*cs_z(accumulation_distribution_20)-0.30*cs_z(momentum_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "Accumulation/distribution pressure produced the largest negative IC in Round105. The new "
                "hypothesis is that intense accumulation with momentum marks overheat."
            ),
            public_reference_tags=("vectorbt", "alphalens", "worldquant_101_alphas"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="anti_turnover_expansion_momentum_10_40",
            family="anti_overheat_turnover_expansion",
            formula_template="-0.45*cs_z(momentum_20)-0.35*cs_z(amount_mean_10/amount_mean_40-1)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(10, 20, 40),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Turnover expansion plus momentum was negatively predictive in Round105. This candidate "
                "tests whether non-crowded momentum is safer than active-demand spikes."
            ),
            public_reference_tags=("alphalens", "qlib", "pyfolio"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="anti_amount_accumulation_breakout_20_60",
            family="anti_overheat_breakout",
            formula_template="-0.45*cs_z(price_breakout_20)-0.35*cs_z(amount_trend_20_60)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "Breakout plus rising amount showed negative IC in Round105. The new candidate treats that "
                "shape as potential late-stage demand that must be screened before portfolio use."
            ),
            public_reference_tags=("vectorbt", "alphalens", "qlib"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="anti_obv_late_accumulation_20",
            family="anti_overheat_obv",
            formula_template="-0.50*cs_z(obv_slope_20)-0.30*cs_z(momentum_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "OBV-style accumulation failed in the positive direction. This candidate tests whether "
                "late OBV accumulation should be avoided in a capacity-safe liquid universe."
            ),
            public_reference_tags=("vectorbt", "alphalens", "pyfolio"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="overheat_avoidance_high_volume_breakout_20",
            family="overheat_avoidance_breakout_quality",
            formula_template="-0.45*cs_z(close_to_20d_high)-0.35*cs_z(amount_zscore_20)+0.20*cs_z(return_efficiency_20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "amount"),
            economic_rationale=(
                "High-volume breakouts were weaker and high-turnover in Round105. This candidate isolates "
                "avoidance of unusually hot breakouts while keeping path efficiency visible."
            ),
            public_reference_tags=("vectorbt", "alphalens", "qlib"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="overheat_avoidance_relative_strength_60",
            family="overheat_avoidance_relative_strength",
            formula_template="-0.55*cs_z(momentum_60)-0.25*cs_z(amount_percentile_60)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Long relative strength was negatively predictive in Round105. This tests a non-crowded "
                "relative-strength avoidance score before any portfolio conversion."
            ),
            public_reference_tags=("qlib", "alphalens", "pyfolio"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="amount_exhaustion_pullback_20_60",
            family="amount_exhaustion",
            formula_template="-0.40*cs_z(amount_trend_20_60)-0.35*cs_z(price_breakout_20)+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "This candidate frames the Round105 negative trend-volume evidence as amount exhaustion: "
                "prefer liquid names without recent amount breakout pressure."
            ),
            public_reference_tags=("alphalens", "worldquant_101_alphas", "qlib"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="overheat_avoidance_composite_20_60",
            family="overheat_avoidance_composite",
            formula_template="-0.25*cs_z(money_pressure_20)-0.25*cs_z(accumulation_distribution_20)-0.25*cs_z(momentum_60)-0.15*cs_z(amount_trend_20_60)+0.10*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "A compact composite tests the shared negative-IC cluster from Round105 without adding "
                "extra tuned parameters or treating any single inverse as already validated."
            ),
            public_reference_tags=("alphalens", "qlib", "vectorbt"),
            source_evidence_status=SOURCE_EVIDENCE_STATUS,
        ),
    ]


def build_negative_ic_trend_accumulation_preregistration(
    *,
    min_candidates: int = 8,
    candidate_specs: Iterable[CapacitySafePriceVolumeCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_negative_ic_trend_accumulation_candidate_specs())
    result = build_capacity_safe_price_volume_preregistration(
        min_candidates=min_candidates,
        candidate_specs=specs,
    )
    result["stage"] = STAGE
    result["negative_ic_context"] = {
        "source_audit": ROUND105_SOURCE_AUDIT,
        "source_round": "round105_capacity_safe_trend_accumulation_prescreen",
        "evidence_status": "round105_negative_ic_is_hypothesis_evidence_not_promotion_evidence",
        "observed_shape": "20/20 tests were FDR-significant with negative mean IC and zero research leads.",
        "policy": "Inverse candidates must be pre-registered and prescreened before any portfolio grid.",
    }
    result["family_rotation_context"] = {
        "previous_blocker": "positive_trend_amount_direction_failed_with_strong_negative_ic",
        "rotated_away_from": [
            "positive_trend_accumulation_direct_long",
            "same_family_parameter_tuning_after_negative_ic",
            "post_hoc_inverse_promotion",
        ],
        "next_direction": ROUND106_NEXT_DIRECTION,
    }
    result["public_reference_review"] = {
        "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
        "method": (
            "Use public overreaction, price-volume reversal, and Alphalens/qlib prescreening ideas as "
            "hypotheses only. Round105 negative IC provides direction-audit evidence, not profitability evidence."
        ),
    }
    result["promotion_policy"]["next_allowed_action"] = (
        "Build the negative-IC trend/amount factor matrix and run Alphalens-style IC/quantile/turnover prescreen."
    )
    result["summary"]["next_direction"] = ROUND106_NEXT_DIRECTION
    result["markdown"] = render_negative_ic_trend_accumulation_preregistration_markdown(result)
    return result


def write_negative_ic_trend_accumulation_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "negative_ic_trend_accumulation_preregistration.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "negative_ic_trend_accumulation_preregistration.md").write_text(
        render_negative_ic_trend_accumulation_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "negative_ic_trend_accumulation_candidates.csv", _candidate_csv_rows(result))


def render_negative_ic_trend_accumulation_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    context = result.get("negative_ic_context", {})
    rotation = result.get("family_rotation_context", {})
    lines = [
        "# Negative-IC Trend Accumulation Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Next direction: {rotation.get('next_direction', ROUND106_NEXT_DIRECTION)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Negative-IC Context",
        "",
        f"- Source audit: {context.get('source_audit', ROUND105_SOURCE_AUDIT)}",
        f"- Evidence status: {context.get('evidence_status', '')}",
        f"- Observed shape: {context.get('observed_shape', '')}",
        f"- Policy: {context.get('policy', '')}",
        "",
        "## Rotation Context",
        "",
        f"- Previous blocker: {rotation.get('previous_blocker', '')}",
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
