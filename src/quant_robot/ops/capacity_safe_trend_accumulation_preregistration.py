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


STAGE = "capacity_safe_trend_accumulation_preregistration"
ROUND104_NEXT_DIRECTION = "round105_capacity_safe_trend_accumulation_prescreen"


def default_capacity_safe_trend_accumulation_candidate_specs() -> list[CapacitySafePriceVolumeCandidateSpec]:
    return [
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="volume_weighted_momentum_quality_20",
            family="volume_confirmed_trend",
            formula_template="0.50*cs_z(volume_weighted_return_20)+0.30*cs_z(return_efficiency_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Momentum backed by traded amount and smooth path quality is a different return engine from "
                "the rejected low-volatility reversal cluster."
            ),
            public_reference_tags=("qlib", "alphalens", "vectorbt"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="amount_accumulation_breakout_20_60",
            family="amount_accumulation",
            formula_template="0.45*cs_z(price_breakout_20)+0.35*cs_z(amount_trend_20_60)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "A price breakout with rising amount is a public trend-confirmation hypothesis; liquidity is "
                "part of the signal rather than a post-hoc rescue."
            ),
            public_reference_tags=("vectorbt", "alphalens", "pyfolio"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="money_pressure_efficiency_20",
            family="money_pressure",
            formula_template="0.55*cs_z(sum(return_1d*amount,20)/sum(amount,20))+0.25*cs_z(return_efficiency_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Return per traded amount approximates directional money pressure without using the already "
                "rejected raw moneyflow-only line."
            ),
            public_reference_tags=("worldquant_101_alphas", "alphalens", "qlib"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="relative_amount_trend_confirmed_momentum_20_60",
            family="amount_confirmed_momentum",
            formula_template="0.45*cs_z(skip5_momentum_20)+0.35*cs_z(amount_trend_20_60)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Skip-window momentum is retained only when medium-term amount expansion confirms demand, "
                "reducing pure price-chasing risk."
            ),
            public_reference_tags=("qlib", "alphalens", "worldquant_101_alphas"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="obv_proxy_trend_quality_20",
            family="obv_proxy",
            formula_template="0.50*cs_z(obv_slope_20)+0.30*cs_z(price_trend_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "OBV-style accumulation is a public technical idea, but this registration keeps it in a "
                "capacity-safe prescreen before any portfolio use."
            ),
            public_reference_tags=("vectorbt", "alphalens", "pyfolio"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="high_volume_breakout_quality_20",
            family="breakout_quality",
            formula_template="0.45*cs_z(close_to_20d_high)+0.35*cs_z(amount_zscore_20)+0.20*cs_z(return_efficiency_20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "amount"),
            economic_rationale=(
                "Breakouts should be more informative when volume is unusually high and the price path is "
                "efficient rather than jumpy."
            ),
            public_reference_tags=("vectorbt", "alphalens", "qlib"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="liquidity_qualified_relative_strength_60",
            family="liquid_relative_strength",
            formula_template="0.55*cs_z(momentum_60)+0.25*cs_z(amount_percentile_60)+0.20*cs_z(return_efficiency_20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Relative strength is only tested when liquidity breadth supports execution, avoiding "
                "capacity-blind momentum tails."
            ),
            public_reference_tags=("qlib", "alphalens", "pyfolio"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="price_path_efficiency_amount_confirmed_20",
            family="trend_efficiency",
            formula_template="0.50*cs_z(return_efficiency_20)+0.30*cs_z(amount_trend_20_60)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Efficient trends with amount confirmation are structurally different from mean-reversion "
                "pullbacks and should be screened as a separate family."
            ),
            public_reference_tags=("alphalens", "qlib", "vectorbt"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="accumulation_distribution_proxy_20",
            family="accumulation_distribution",
            formula_template="0.50*cs_z(((close-low)-(high-close))/(high-low)*amount).rolling(20).sum()+0.30*cs_z(momentum_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "Accumulation/distribution is a known price-volume indicator; this candidate requires "
                "long-cycle IC and quantile proof before any top-N strategy."
            ),
            public_reference_tags=("vectorbt", "alphalens", "worldquant_101_alphas"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="turnover_expansion_momentum_10_40",
            family="turnover_expansion",
            formula_template="0.45*cs_z(momentum_20)+0.35*cs_z(amount_mean_10/amount_mean_40-1)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(10, 20, 40),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Turnover expansion paired with momentum tests active demand, not the old low-turnover "
                "capacity-constrained anomaly."
            ),
            public_reference_tags=("alphalens", "qlib", "pyfolio"),
        ),
    ]


def build_capacity_safe_trend_accumulation_preregistration(
    *,
    min_candidates: int = 8,
    candidate_specs: Iterable[CapacitySafePriceVolumeCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_capacity_safe_trend_accumulation_candidate_specs())
    result = build_capacity_safe_price_volume_preregistration(
        min_candidates=min_candidates,
        candidate_specs=specs,
    )
    result["stage"] = STAGE
    result["family_rotation_context"] = {
        "previous_blocker": "lead_highly_redundant_with_existing_candidate",
        "rotated_away_from": [
            "bollinger_reversal",
            "rsi_reversal",
            "donchian_pullback",
            "range_contraction_lowvol_reversal",
            "lowvol_reversal_blend",
        ],
        "next_direction": ROUND104_NEXT_DIRECTION,
    }
    result["public_reference_review"] = {
        "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
        "method": (
            "Use public trend, amount accumulation, OBV-style, and Alphalens/qlib screening ideas as "
            "hypotheses only. No candidate can advance before long-cycle IC, quantile, turnover, cost, "
            "capacity, and redundancy checks."
        ),
    }
    result["promotion_policy"]["next_allowed_action"] = (
        "Build the trend/accumulation factor matrix and run Alphalens-style IC/quantile/turnover prescreen."
    )
    result["summary"]["next_direction"] = ROUND104_NEXT_DIRECTION
    result["markdown"] = render_capacity_safe_trend_accumulation_preregistration_markdown(result)
    return result


def write_capacity_safe_trend_accumulation_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "capacity_safe_trend_accumulation_preregistration.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "capacity_safe_trend_accumulation_preregistration.md").write_text(
        render_capacity_safe_trend_accumulation_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "capacity_safe_trend_accumulation_candidates.csv", _candidate_csv_rows(result))


def render_capacity_safe_trend_accumulation_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    context = result.get("family_rotation_context", {})
    lines = [
        "# Capacity-Safe Trend Accumulation Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Next direction: {context.get('next_direction', ROUND104_NEXT_DIRECTION)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Rotation Context",
        "",
        f"- Previous blocker: {context.get('previous_blocker', '')}",
        "- Rotated away from: " + ", ".join(context.get("rotated_away_from", []) or []),
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
