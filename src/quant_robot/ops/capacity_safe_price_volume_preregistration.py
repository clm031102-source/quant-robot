from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable


STAGE = "capacity_safe_price_volume_preregistration"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
NEXT_REQUIRED_GATE = "alphalens_style_ic_quantile_turnover_prescreen"
PUBLIC_REFERENCE_PROJECTS = (
    "qlib",
    "alphalens",
    "vectorbt",
    "pyfolio",
    "worldquant_101_alphas",
)
DEFAULT_CAPACITY_FILTERS: dict[str, Any] = {
    "exclude_st": True,
    "exclude_suspended": True,
    "exclude_limit_up_down_if_untradable": True,
    "min_listing_days": 120,
    "min_signal_date_amount": 10_000_000,
    "max_position_adv_participation": 0.05,
    "require_calendar_holding_gate": True,
}


@dataclass(frozen=True)
class CapacitySafePriceVolumeCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    capacity_filters: dict[str, Any] | None = None
    source_evidence_status: str = "public_reference_preregistered_not_empirical"
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_capacity_safe_price_volume_candidate_specs() -> list[CapacitySafePriceVolumeCandidateSpec]:
    return [
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="pv_lowvol_reversal_blend_20",
            family="price_volume_lowvol_reversal",
            formula_template="0.45*cs_z(reversal_5)+0.35*cs_z(-pv_corr_20)+0.20*cs_z(-downside_vol_20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Combines short reversal, price-volume divergence, and low downside volatility to avoid "
                "treating a single noisy public formula as a tradable signal."
            ),
            public_reference_tags=("alphalens", "worldquant_101_alphas", "qlib"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="range_contraction_lowvol_reversal_20",
            family="range_contraction",
            formula_template="0.40*cs_z(reversal_5)+0.35*cs_z(-hl_range_20)+0.25*cs_z(-realized_vol_20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "high", "low"),
            economic_rationale=(
                "Range contraction plus low volatility is a public breakout/reversal screen; preregistration "
                "requires later IC decay and turnover checks before portfolio use."
            ),
            public_reference_tags=("alphalens", "vectorbt", "qlib"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="volume_contraction_reversal_lowvol_20",
            family="volume_contraction",
            formula_template="0.45*cs_z(reversal_5)+0.35*cs_z(-amount_trend_20)+0.20*cs_z(-downside_vol_20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "A pullback with contracting turnover can indicate seller exhaustion, but capacity filters "
                "are mandatory because low turnover can become untradeable."
            ),
            public_reference_tags=("alphalens", "worldquant_101_alphas", "pyfolio"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="price_volume_trend_quality_20_60",
            family="trend_quality",
            formula_template="0.40*cs_z(skip5_momentum_20)+0.35*cs_z(momentum_60)+0.25*cs_z(return_efficiency_20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Momentum is only accepted when recent price path efficiency supports it; skip-5 avoids "
                "chasing the shortest reversal noise."
            ),
            public_reference_tags=("qlib", "alphalens", "vectorbt"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="skip5_momentum_lowvol_20",
            family="momentum_lowvol",
            formula_template="0.60*cs_z(skip5_momentum_20)+0.40*cs_z(-realized_vol_20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "high", "low"),
            economic_rationale=(
                "Skip-window momentum with low volatility is a simple public anomaly family that should be "
                "screened for IC persistence before any top-N construction."
            ),
            public_reference_tags=("qlib", "alphalens", "pyfolio"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="pv_corr_reversal_capacity_safe_20",
            family="price_volume_divergence",
            formula_template="0.70*cs_z(-pv_corr_20)+0.30*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Price-volume correlation reversal is retained only with explicit liquidity quality so the "
                "old pv-corr line cannot become another capacity-blind continuation."
            ),
            public_reference_tags=("worldquant_101_alphas", "alphalens", "pyfolio"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="bollinger_reversal_lowvol_liquid_20",
            family="public_technical_reversal",
            formula_template="0.55*cs_z(bollinger_reversal_20)+0.25*cs_z(-realized_vol_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Bollinger reversal is a known public technical indicator, but low-vol and liquidity terms "
                "are pre-registered to reduce tail and execution failure."
            ),
            public_reference_tags=("vectorbt", "alphalens", "pyfolio"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="rsi_reversal_lowvol_liquid_14_20",
            family="public_technical_reversal",
            formula_template="0.55*cs_z(rsi_reversal_14)+0.25*cs_z(-downside_vol_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(14, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "RSI reversal is a public mean-reversion indicator; this candidate requires later turnover "
                "and decay evidence before it can graduate."
            ),
            public_reference_tags=("vectorbt", "alphalens", "qlib"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="amount_stability_reversal_5_20",
            family="liquidity_capacity",
            formula_template="0.50*cs_z(reversal_5)+0.30*cs_z(-abs(amount_trend_20))+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "A capacity-aware reversal candidate should prefer stable, liquid turnover instead of the "
                "weakest low-turnover tail that failed earlier rounds."
            ),
            public_reference_tags=("alphalens", "pyfolio", "qlib"),
        ),
        CapacitySafePriceVolumeCandidateSpec(
            factor_name="donchian_pullback_lowvol_liquid_20",
            family="public_technical_pullback",
            formula_template="0.45*cs_z(1-donchian_position_20)+0.30*cs_z(-realized_vol_20)+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "Donchian position converts a public channel indicator into a pullback hypothesis with "
                "explicit low-volatility and liquidity constraints."
            ),
            public_reference_tags=("vectorbt", "alphalens", "worldquant_101_alphas"),
        ),
    ]


def build_capacity_safe_price_volume_preregistration(
    *,
    min_candidates: int = 8,
    candidate_specs: Iterable[CapacitySafePriceVolumeCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_capacity_safe_price_volume_candidate_specs())
    candidates = [_candidate_payload(spec) for spec in specs]
    blockers = _blockers(candidates, min_candidates=min_candidates)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "candidate_count": len(candidates),
            "min_candidates": min_candidates,
            "unique_candidate_names": len({candidate["factor_name"] for candidate in candidates}),
            "portfolio_backtest_allowed_candidates": sum(
                1 for candidate in candidates if candidate["portfolio_backtest_allowed"]
            ),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": NEXT_REQUIRED_GATE,
        },
        "public_reference_review": {
            "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
            "method": (
                "Use public indicator families as hypotheses, not as promotion evidence. "
                "Every candidate must survive IC, quantile monotonicity, turnover, cost, capacity, "
                "long-cycle, and walk-forward checks before portfolio use."
            ),
        },
        "capacity_policy": {
            "filters": DEFAULT_CAPACITY_FILTERS,
            "reason": "A-share stock factors must be tradable after costs and cannot rely on illiquid low-turnover tails.",
        },
        "evaluation_gate": {
            "next_required_gate": NEXT_REQUIRED_GATE,
            "required_metrics": [
                "mean_spearman_ic",
                "icir",
                "ic_t_stat",
                "ic_positive_rate",
                "quantile_spread",
                "quantile_monotonicity",
                "factor_turnover",
                "coverage_by_date",
                "capacity_participation",
            ],
            "portfolio_backtest_allowed_after": "statistical_lead_and_turnover_capacity_prescreen",
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_prescreen": False,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_multiple_testing_accounting": True,
            "next_allowed_action": "Build factor matrix and run Alphalens-style IC/quantile/turnover prescreen.",
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_capacity_safe_price_volume_preregistration_markdown(result)
    return result


def write_capacity_safe_price_volume_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "capacity_safe_price_volume_preregistration.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "capacity_safe_price_volume_preregistration.md").write_text(
        render_capacity_safe_price_volume_preregistration_markdown(result),
        encoding="utf-8",
    )
    with (output_path / "capacity_safe_price_volume_candidates.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(_candidate_csv_rows(result)[0].keys()))
        writer.writeheader()
        writer.writerows(_candidate_csv_rows(result))


def render_capacity_safe_price_volume_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Capacity-Safe Price-Volume Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Portfolio backtest allowed before prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Public Reference Review",
        "",
        "- Projects reviewed: "
        + ", ".join(result.get("public_reference_review", {}).get("projects_reviewed", []) or []),
        f"- Method: {result.get('public_reference_review', {}).get('method', '')}",
        "",
        "## Capacity Policy",
        "",
        f"- Filters: `{json.dumps(result.get('capacity_policy', {}).get('filters', {}), sort_keys=True)}`",
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


def _candidate_payload(spec: CapacitySafePriceVolumeCandidateSpec) -> dict[str, Any]:
    capacity_filters = dict(DEFAULT_CAPACITY_FILTERS)
    if spec.capacity_filters:
        capacity_filters.update(spec.capacity_filters)
    return {
        "factor_name": spec.factor_name,
        "family": spec.family,
        "market": "CN",
        "asset_type": "stock",
        "formula_template": spec.formula_template,
        "direction": spec.direction,
        "windows": list(spec.windows),
        "required_fields": list(spec.required_fields),
        "economic_rationale": spec.economic_rationale,
        "public_reference_tags": list(spec.public_reference_tags),
        "capacity_filters": capacity_filters,
        "source_evidence_status": spec.source_evidence_status,
        "registration_status": "pre_registered",
        "portfolio_backtest_allowed": spec.portfolio_backtest_allowed,
        "promotion_allowed": spec.promotion_allowed,
        "next_required_gate": NEXT_REQUIRED_GATE,
        "lookahead_policy": "Signal uses only same-day or prior bars; if close-derived, execution must lag to next tradable bar.",
    }


def _blockers(candidates: list[dict[str, Any]], *, min_candidates: int) -> list[str]:
    blockers: list[str] = []
    names = [candidate["factor_name"] for candidate in candidates]
    if len(candidates) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len(names) != len(set(names)):
        blockers.append("duplicate_candidate_names")
    if any(not candidate.get("economic_rationale") for candidate in candidates):
        blockers.append("missing_economic_rationale")
    if any(not candidate.get("public_reference_tags") for candidate in candidates):
        blockers.append("missing_public_reference_tags")
    if any(not _has_capacity_filters(candidate.get("capacity_filters", {})) for candidate in candidates):
        blockers.append("missing_capacity_filters")
    if any(candidate.get("portfolio_backtest_allowed") for candidate in candidates):
        blockers.append("portfolio_backtest_allowed_before_prescreen")
    if any(candidate.get("promotion_allowed") for candidate in candidates):
        blockers.append("promotion_allowed_before_validation")
    return blockers


def _has_capacity_filters(filters: dict[str, Any]) -> bool:
    return "min_signal_date_amount" in filters and "max_position_adv_participation" in filters


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
