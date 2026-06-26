from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

from quant_robot.ops.capacity_safe_price_volume_preregistration import (
    DEFAULT_CAPACITY_FILTERS,
    PUBLIC_REFERENCE_PROJECTS,
    SAFETY,
)
from quant_robot.ops.factor_mining_candidate_plan_gate import default_cn_stock_pre_mining_control_plan


STAGE = "lottery_extreme_upside_reversal_preregistration"
NEXT_REQUIRED_GATE = "round150_lottery_extreme_upside_reversal_ic_neutral_prescreen"
SOURCE_AUDIT = "docs/research/cn_stock_round146_148_three_round_review_2026-06-22.md"


@dataclass(frozen=True)
class LotteryExtremeUpsideCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    capacity_filters: dict[str, Any] | None = None
    source_evidence_status: str = "public_max_effect_preregistered_not_empirical"
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_lottery_extreme_upside_candidate_specs() -> list[LotteryExtremeUpsideCandidateSpec]:
    return [
        LotteryExtremeUpsideCandidateSpec(
            factor_name="lottery_max_return_reversal_20",
            family="max_effect_reversal",
            formula_template="cs_z(-rolling_max(return_1d,20)) + 0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "The public MAX-effect anomaly says stocks with extreme recent upside can become lottery-demand "
                "overcrowded and underperform. Liquidity is included only as a tradability control."
            ),
            public_reference_tags=("max_effect", "lottery_demand", "alphalens"),
            expected_failure_modes=("limit_up_execution_artifact", "microcap_capacity_tail", "short_reversal_duplicate"),
        ),
        LotteryExtremeUpsideCandidateSpec(
            factor_name="lottery_limit_chase_exhaustion_20",
            family="limit_chase_exhaustion",
            formula_template="cs_z(-rolling_sum(return_1d>0.08,20) * amount_spike_5_20) + 0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "A-share limit-chase behavior can create crowded lottery demand; this candidate tests whether "
                "recent high-upside days plus volume spikes reverse after capacity filters."
            ),
            public_reference_tags=("max_effect", "limit_chase", "a_share_microstructure"),
            expected_failure_modes=("limit_up_buy_untradable", "event_path_extreme_return", "momentum_regime_false_positive"),
        ),
        LotteryExtremeUpsideCandidateSpec(
            factor_name="lottery_upside_tail_asymmetry_reversal_60",
            family="upside_tail_asymmetry",
            formula_template="cs_z(-(rolling_max(return_1d,60)-abs(rolling_min(return_1d,60)))) + 0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(60,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "This separates extreme upside-tail demand from symmetric volatility. It should not be promoted "
                "unless it beats low-volatility and residual-skew references."
            ),
            public_reference_tags=("max_effect", "idiosyncratic_skew", "qlib"),
            expected_failure_modes=("residual_skew_redundancy", "low_vol_duplicate", "yearly_regime_instability"),
        ),
        LotteryExtremeUpsideCandidateSpec(
            factor_name="lottery_climax_volume_reversal_20",
            family="climax_volume_reversal",
            formula_template="cs_z(-rolling_max(return_1d * amount_spike_5_20,20)) + 0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "A high-return day with abnormal turnover is a climax-demand proxy. The factor is only a "
                "hypothesis until IC, turnover, capacity, and extreme-trade audits clear."
            ),
            public_reference_tags=("volume_climax", "max_effect", "pyfolio"),
            expected_failure_modes=("volume_spike_news_event", "capacity_stress", "same_day_close_lookahead"),
        ),
        LotteryExtremeUpsideCandidateSpec(
            factor_name="lottery_upper_shadow_reversal_20",
            family="failed_intraday_chase",
            formula_template="cs_z(-rolling_mean((high-close)/(high-low) * positive_return_flag,20)) + 0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "Large upper shadows after positive moves can mark failed chase demand. This is kept separate "
                "from prior smart-money close-location work by focusing on positive-return failure tails."
            ),
            public_reference_tags=("candlestick_upper_shadow", "lottery_demand", "vectorbt"),
            expected_failure_modes=("close_location_redundancy", "limit_up_limit_down_proxy_error", "weak_cross_section"),
        ),
        LotteryExtremeUpsideCandidateSpec(
            factor_name="lottery_gapless_max_reversal_20",
            family="pure_close_to_close_max_effect",
            formula_template="cs_z(-rolling_max(return_1d where amount_spike_5_20<=2,20)) + 0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "This control removes the most obvious volume-climax days to test whether MAX reversal survives "
                "outside pure event/limit-chase paths."
            ),
            public_reference_tags=("max_effect", "robustness_control", "alphalens"),
            expected_failure_modes=("signal_too_sparse", "reversal_duplicate", "low_incremental_ic"),
        ),
    ]


def build_lottery_extreme_upside_reversal_preregistration(
    *,
    min_candidates: int = 6,
    candidate_specs: Iterable[LotteryExtremeUpsideCandidateSpec | dict[str, Any]] | None = None,
) -> dict[str, Any]:
    specs = [_coerce_spec(spec) for spec in (candidate_specs or default_lottery_extreme_upside_candidate_specs())]
    candidates = [_candidate_payload(spec) for spec in specs]
    blockers = _blockers(candidates, min_candidates=min_candidates)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "source_context": {
            "source_audit": SOURCE_AUDIT,
            "rotation_reason": "Round148 rejected event-dividend continuation after public-yield exposure and weak residual ICIR.",
        },
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
            "academic_anomaly": "MAX effect / lottery demand reversal",
            "method": "Treat public anomalies as hypotheses only; require long-cycle IC, neutral IC, redundancy, cost, and capacity gates before any portfolio grid.",
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
                "industry_neutral_ic",
                "size_liquidity_neutral_ic",
                "reference_correlation_vs_reversal_lowvol_skew",
                "limit_up_down_tradeability_audit",
            ],
            "portfolio_backtest_allowed_after": "statistical_lead_and_reference_dedup_prescreen",
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "research_control_plan": default_cn_stock_pre_mining_control_plan(),
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_prescreen": False,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_tradeability_limit_path_audit": True,
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_lottery_extreme_upside_reversal_preregistration_markdown(result)
    return result


def write_lottery_extreme_upside_reversal_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "lottery_extreme_upside_reversal_preregistration.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "lottery_extreme_upside_reversal_preregistration.md").write_text(
        render_lottery_extreme_upside_reversal_preregistration_markdown(result),
        encoding="utf-8",
    )
    rows = _candidate_csv_rows(result)
    with (output_path / "lottery_extreme_upside_reversal_candidates.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else ["factor_name"])
        writer.writeheader()
        writer.writerows(rows)


def render_lottery_extreme_upside_reversal_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Lottery Extreme Upside Reversal Preregistration Round149",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Portfolio before prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidates",
        "",
        "| Factor | Family | Windows | Fields | Public refs |",
        "|---|---|---|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(
            "| {name} | {family} | {windows} | {fields} | {refs} |".format(
                name=candidate["factor_name"],
                family=candidate["family"],
                windows=", ".join(str(item) for item in candidate.get("windows", [])),
                fields=", ".join(candidate.get("required_fields", [])),
                refs=", ".join(candidate.get("public_reference_tags", [])),
            )
        )
    return "\n".join(lines) + "\n"


def _coerce_spec(value: LotteryExtremeUpsideCandidateSpec | dict[str, Any]) -> LotteryExtremeUpsideCandidateSpec:
    if isinstance(value, LotteryExtremeUpsideCandidateSpec):
        return value
    payload = dict(value)
    payload["windows"] = tuple(payload.get("windows", ()))
    payload["required_fields"] = tuple(payload.get("required_fields", ()))
    payload["public_reference_tags"] = tuple(payload.get("public_reference_tags", ()))
    payload["expected_failure_modes"] = tuple(payload.get("expected_failure_modes", ("unspecified_failure_mode",)))
    return LotteryExtremeUpsideCandidateSpec(**payload)


def _candidate_payload(spec: LotteryExtremeUpsideCandidateSpec) -> dict[str, Any]:
    capacity_filters = dict(DEFAULT_CAPACITY_FILTERS)
    if spec.capacity_filters:
        capacity_filters.update(spec.capacity_filters)
    return {
        **asdict(spec),
        "windows": list(spec.windows),
        "required_fields": list(spec.required_fields),
        "public_reference_tags": list(spec.public_reference_tags),
        "expected_failure_modes": list(spec.expected_failure_modes),
        "capacity_filters": capacity_filters,
        "registration_status": "pre_registered",
        "market": "CN",
        "asset_type": "stock",
        "next_required_gate": NEXT_REQUIRED_GATE,
        "lookahead_policy": "Close-derived signals require next-tradable-bar execution lag; no same-day close-to-close target alignment.",
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
    if any(not candidate.get("expected_failure_modes") for candidate in candidates):
        blockers.append("missing_expected_failure_modes")
    if any(candidate.get("portfolio_backtest_allowed") for candidate in candidates):
        blockers.append("portfolio_backtest_allowed_before_prescreen")
    if any(candidate.get("promotion_allowed") for candidate in candidates):
        blockers.append("promotion_allowed_before_validation")
    return blockers


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in result.get("candidates", []) or []:
        rows.append(
            {
                "factor_name": candidate["factor_name"],
                "family": candidate["family"],
                "direction": candidate["direction"],
                "windows": ",".join(str(item) for item in candidate.get("windows", [])),
                "required_fields": ",".join(candidate.get("required_fields", [])),
                "public_reference_tags": ",".join(candidate.get("public_reference_tags", [])),
                "expected_failure_modes": ",".join(candidate.get("expected_failure_modes", [])),
                "registration_status": candidate["registration_status"],
                "next_required_gate": candidate["next_required_gate"],
                "portfolio_backtest_allowed": candidate["portfolio_backtest_allowed"],
                "promotion_allowed": candidate["promotion_allowed"],
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
