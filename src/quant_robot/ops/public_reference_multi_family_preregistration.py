from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable


STAGE = "public_reference_multi_family_preregistration"
ROUND126_SOURCE_AUDIT = "docs/research/cn_stock_turnover_repair_champion_portfolio_conversion_round126_2026-06-22.md"
ROUND128_NEXT_DIRECTION = "round128_public_reference_multi_family_prescreen"
SOURCE_EVIDENCE_STATUS = "public_reference_preregistered_not_empirical_alpha"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
PUBLIC_REFERENCE_PROJECTS = (
    "qlib",
    "alphalens",
    "vectorbt",
    "pyfolio",
    "worldquant_101_alphas",
    "public_supertrend",
    "public_rsrs",
)
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
class PublicReferenceMultiFamilyCandidateSpec:
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
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_public_reference_multi_family_candidate_specs() -> list[PublicReferenceMultiFamilyCandidateSpec]:
    return [
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="alpha101_rank_pv_reversal_liquid_20",
            family="public_formula_alpha101",
            formula_template="-0.55*cs_z(ts_corr(cs_rank(return_1),cs_rank(amount_return_1),20))+0.30*cs_z(-return_5)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "WorldQuant-style rank price-volume correlation is treated as a reversal hypothesis, with "
                "liquidity included before any portfolio work."
            ),
            public_reference_tags=("worldquant_101_alphas", "alphalens", "qlib"),
            expected_failure_modes=("formula_redundancy", "ic_decay", "capacity_tail"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="alpha101_decay_reversal_amount_stability_10",
            family="public_formula_alpha101",
            formula_template="0.60*cs_z(decay_linear(cs_rank(-return_5),10))+0.25*cs_z(-abs(amount_z_20))+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 10, 20),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "A decayed rank operator can reduce one-day noise, while amount stability avoids another "
                "illiquid-tail illusion."
            ),
            public_reference_tags=("worldquant_101_alphas", "alphalens"),
            expected_failure_modes=("multiple_testing", "weak_quantile_monotonicity", "turnover_decay"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="alpha101_intraday_range_position_fade_20",
            family="public_formula_alpha101",
            formula_template="-0.50*cs_z(ts_mean((adj_close-open)/(high-low+1e-6),20))+0.30*cs_z(-realized_vol_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "open", "high", "low", "amount"),
            economic_rationale=(
                "Close-location pressure is a common public formula input; this candidate tests fade behavior "
                "only after volatility and liquidity controls."
            ),
            public_reference_tags=("worldquant_101_alphas", "qlib", "alphalens"),
            expected_failure_modes=("close_price_alignment", "range_data_quality", "weak_oos"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="qlib_alpha158_kbar_momentum_lowvol_20",
            family="qlib_alpha158_feature_blend",
            formula_template="0.40*cs_z(kbar_close_position_20)+0.35*cs_z(skip5_momentum_20)+0.25*cs_z(-realized_vol_20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "high", "low"),
            economic_rationale=(
                "Qlib-style candlestick position is paired with skip-window momentum and low volatility instead "
                "of being used as a raw TopN signal."
            ),
            public_reference_tags=("qlib", "alphalens", "pyfolio"),
            expected_failure_modes=("hidden_beta_exposure", "regime_dependency", "trend_chop_instability"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="qlib_alpha158_price_efficiency_liquid_20",
            family="qlib_alpha158_feature_blend",
            formula_template="0.50*cs_z(return_efficiency_20)+0.25*cs_z(momentum_20)+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Efficient price paths can proxy institutional accumulation, but the liquidity term keeps it "
                "away from small-cap path artifacts."
            ),
            public_reference_tags=("qlib", "alphalens"),
            expected_failure_modes=("market_beta_disguise", "yearly_instability", "capacity_tail"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="qlib_alpha158_volume_price_resonance_20_60",
            family="qlib_alpha158_feature_blend",
            formula_template="0.45*cs_z(momentum_20)+0.35*cs_z(amount_trend_20_60)+0.20*cs_z(return_efficiency_20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Momentum with medium-term amount confirmation is a public, interpretable demand hypothesis."
            ),
            public_reference_tags=("qlib", "vectorbt", "alphalens"),
            expected_failure_modes=("momentum_crash", "turnover_cost", "regime_dependency"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="supertrend_pullback_lowvol_liquid_10_3",
            family="public_technical_supertrend",
            formula_template="0.45*cs_z(supertrend_distance_reversal_10_3)+0.30*cs_z(-atr_ratio_10)+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(10, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "Supertrend distance is tested as a pullback entry, not as a naive trend-following buy signal "
                "that previously failed public-indicator gates."
            ),
            public_reference_tags=("public_supertrend", "vectorbt", "pyfolio"),
            expected_failure_modes=("trend_indicator_lag", "same_family_redundancy", "cost_drag"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="supertrend_consensus_breakout_efficiency_10_20",
            family="public_technical_supertrend",
            formula_template="0.35*cs_z(supertrend_state_10_3)+0.35*cs_z(price_breakout_20)+0.30*cs_z(return_efficiency_20)",
            direction="higher_is_better",
            windows=(10, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "Trend state is accepted only when breakout and path efficiency agree, reducing a one-filter "
                "public-indicator trap."
            ),
            public_reference_tags=("public_supertrend", "vectorbt", "alphalens"),
            expected_failure_modes=("trend_chop_instability", "market_beta_disguise", "turnover_cost"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="donchian_breakout_efficiency_liquid_20",
            family="public_technical_breakout",
            formula_template="0.45*cs_z(donchian_position_20)+0.30*cs_z(return_efficiency_20)+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "A Donchian breakout hypothesis is kept liquid and path-efficient before later IC and turnover "
                "proof."
            ),
            public_reference_tags=("vectorbt", "alphalens", "pyfolio"),
            expected_failure_modes=("breakout_false_positive", "drawdown_tail", "regime_dependency"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="rsrs_residual_reversal_liquid_18",
            family="public_rsrs_channel",
            formula_template="-0.55*cs_z(rsrs_residual_z_18)+0.25*cs_z(-realized_vol_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(18, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale=(
                "RSRS residual extremes are tested as a mean-reversion channel signal with liquidity and "
                "volatility controls."
            ),
            public_reference_tags=("public_rsrs", "alphalens", "vectorbt"),
            expected_failure_modes=("rsrs_redundancy", "tail_event_dependency", "range_data_quality"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="rsrs_slope_acceleration_quality_18_60",
            family="public_rsrs_channel",
            formula_template="0.45*cs_z(rsrs_slope_18)+0.30*cs_z(rsrs_slope_delta_60)+0.25*cs_z(return_efficiency_20)",
            direction="higher_is_better",
            windows=(18, 20, 60),
            required_fields=("adj_close", "high", "low"),
            economic_rationale=(
                "RSRS slope is treated as a channel-strength hypothesis and must prove it is not just market "
                "beta in prescreen."
            ),
            public_reference_tags=("public_rsrs", "alphalens"),
            expected_failure_modes=("hidden_beta_exposure", "regime_dependency", "parameter_fragility"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="smart_money_efficiency_reversal_20",
            family="smart_money_flow",
            formula_template="0.45*cs_z(smart_money_net_ratio_20)+0.30*cs_z(-return_5)+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount", "moneyflow_net_amount"),
            economic_rationale=(
                "Smart-money pressure is combined with short reversal and liquidity to avoid pure moneyflow "
                "lock-in."
            ),
            public_reference_tags=("alphalens", "pyfolio", "moneyflow_research"),
            expected_failure_modes=("moneyflow_lockin", "data_lag", "capacity_tail"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="smart_money_accumulation_quality_20",
            family="smart_money_flow",
            formula_template="0.50*cs_z(smart_money_persistent_net_ratio_20)+0.30*cs_z(return_efficiency_20)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount", "moneyflow_net_amount"),
            economic_rationale=(
                "Persistent moneyflow is tested only when price path quality confirms it, so the factor is not "
                "a blind CN moneyflow continuation."
            ),
            public_reference_tags=("alphalens", "qlib", "moneyflow_research"),
            expected_failure_modes=("moneyflow_lockin", "weak_oos", "source_data_gap"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="main_force_divergence_reversal_5_20",
            family="smart_money_flow",
            formula_template="0.45*cs_z(main_force_flow_divergence_20)+0.35*cs_z(-return_5)+0.20*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "amount", "moneyflow_main_net_amount"),
            economic_rationale=(
                "Main-force divergence is a behavioral exhaustion hypothesis, not a standalone moneyflow "
                "selection rule."
            ),
            public_reference_tags=("alphalens", "pyfolio", "moneyflow_research"),
            expected_failure_modes=("data_lag", "extreme_trade_dependency", "family_redundancy"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="qvm_quality_value_momentum_blend_20_60",
            family="qvm_quality_value_momentum",
            formula_template="0.35*cs_z(quality_proxy)+0.30*cs_z(value_proxy)+0.25*cs_z(skip5_momentum_60)+0.10*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount", "pe_ttm", "pb", "roe_proxy"),
            economic_rationale=(
                "Quality-value-momentum is a public multi-factor template; the preregistered version is compact "
                "and capacity-aware."
            ),
            public_reference_tags=("qlib", "alphalens", "pyfolio"),
            expected_failure_modes=("daily_basic_proxy_weakness", "factor_crowding", "rebalance_cost"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="qvm_lowvol_value_momentum_liquid_20_60",
            family="qvm_quality_value_momentum",
            formula_template="0.30*cs_z(value_proxy)+0.30*cs_z(skip5_momentum_60)+0.25*cs_z(-realized_vol_20)+0.15*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount", "pe_ttm", "pb"),
            economic_rationale=(
                "This checks whether public QVM improves only when volatility and liquidity are explicit "
                "rather than afterthought filters."
            ),
            public_reference_tags=("qlib", "alphalens", "pyfolio"),
            expected_failure_modes=("value_trap", "momentum_reversal", "proxy_quality_gap"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="bollinger_bandwidth_reversal_liquid_20",
            family="volatility_reversal",
            formula_template="0.45*cs_z(bollinger_reversal_20)+0.30*cs_z(-bollinger_bandwidth_20)+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "Bollinger reversal is retested only as one member of a wider public-reference batch, with "
                "liquidity and bandwidth compression fixed in advance."
            ),
            public_reference_tags=("vectorbt", "alphalens", "pyfolio"),
            expected_failure_modes=("same_cluster_redundancy", "weak_portfolio_translation", "tail_event_dependency"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="rsi_macd_exhaustion_reversal_14_26",
            family="volatility_reversal",
            formula_template="0.40*cs_z(rsi_reversal_14)+0.35*cs_z(-macd_hist_z_26)+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(14, 26),
            required_fields=("adj_close", "amount"),
            economic_rationale=(
                "RSI and MACD are common public indicators; using them together tests exhaustion rather than "
                "a single indicator story."
            ),
            public_reference_tags=("vectorbt", "alphalens"),
            expected_failure_modes=("indicator_lag", "overlap_noise", "false_reversal"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="beta_neutral_momentum_residual_quality_60",
            family="market_residual_quality",
            formula_template="0.45*cs_z(residual_momentum_60)+0.30*cs_z(return_efficiency_20)+0.25*cs_z(-residual_vol_20)",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount", "market_return"),
            economic_rationale=(
                "Momentum must prove it is not market beta; this candidate starts from residual momentum and "
                "risk quality."
            ),
            public_reference_tags=("qlib", "alphalens", "pyfolio"),
            expected_failure_modes=("beta_model_error", "residualization_instability", "regime_dependency"),
        ),
        PublicReferenceMultiFamilyCandidateSpec(
            factor_name="residual_range_contraction_reversal_20",
            family="market_residual_quality",
            formula_template="0.45*cs_z(-residual_return_5)+0.30*cs_z(-hl_range_20)+0.25*cs_z(log_adv20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "high", "low", "amount", "market_return"),
            economic_rationale=(
                "Residual reversal with range contraction is a fresh testable bridge from prior residual work, "
                "but it remains blocked from portfolio use until prescreen."
            ),
            public_reference_tags=("alphalens", "qlib", "vectorbt"),
            expected_failure_modes=("market_residual_redundancy", "range_data_quality", "weak_oos"),
        ),
    ]


def build_public_reference_multi_family_preregistration(
    *,
    min_candidates: int = 18,
    min_families: int = 6,
    candidate_specs: Iterable[PublicReferenceMultiFamilyCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_public_reference_multi_family_candidate_specs())
    candidates = [_candidate_payload(spec) for spec in specs]
    blockers = _blockers(candidates, min_candidates=min_candidates, min_families=min_families)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "candidate_count": len(candidates),
            "min_candidates": int(min_candidates),
            "family_count": len({candidate["family"] for candidate in candidates}),
            "min_families": int(min_families),
            "unique_candidate_names": len({candidate["factor_name"] for candidate in candidates}),
            "portfolio_backtest_allowed_candidates": sum(
                1 for candidate in candidates if candidate["portfolio_backtest_allowed"]
            ),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": ROUND128_NEXT_DIRECTION,
            "next_direction": ROUND128_NEXT_DIRECTION,
        },
        "family_rotation_context": {
            "source_audit": ROUND126_SOURCE_AUDIT,
            "source_round": "round126_turnover_repair_champion_portfolio_conversion",
            "hibernated_families": ["low_turnover_repair", "turnover_repair_champion"],
            "rotation_reason": (
                "Round126 had high total return but zero walk-forward candidates after overlap, drawdown, "
                "calendar, extreme-trade, and capacity gates."
            ),
            "next_direction": ROUND128_NEXT_DIRECTION,
        },
        "public_reference_review": {
            "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
            "method": (
                "Use public projects as hypothesis sources only. Candidates are fixed before measurement, "
                "counted in multiple-testing accounting, and blocked from promotion until long-cycle IC, "
                "quantile, turnover, cost, capacity, regime, and walk-forward evidence exists."
            ),
        },
        "capacity_policy": {
            "filters": DEFAULT_CAPACITY_FILTERS,
            "reason": (
                "After Round126, high headline return is not enough. Every candidate must remain capacity, "
                "calendar, and extreme-trade clean before portfolio conversion."
            ),
        },
        "evaluation_gate": {
            "next_required_gate": ROUND128_NEXT_DIRECTION,
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
                "extreme_forward_return_rate",
                "source_evidence_status",
                "family_redundancy_correlation",
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
            "requires_extreme_trade_diagnostic": True,
            "next_allowed_action": (
                "Build the Round128 factor matrix and run public-reference multi-family IC, quantile, turnover, "
                "capacity, redundancy, and extreme-trade prescreen. No portfolio grid before prescreen leads."
            ),
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_public_reference_multi_family_preregistration_markdown(result)
    return result


def write_public_reference_multi_family_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "public_reference_multi_family_preregistration.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_reference_multi_family_preregistration.md").write_text(
        render_public_reference_multi_family_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "public_reference_multi_family_candidates.csv", _candidate_csv_rows(result))


def render_public_reference_multi_family_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    rotation = result.get("family_rotation_context", {})
    lines = [
        "# Public Reference Multi-Family Preregistration",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Source audit: {rotation.get('source_audit', ROUND126_SOURCE_AUDIT)}",
        f"- Next required gate: {summary.get('next_required_gate', ROUND128_NEXT_DIRECTION)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio backtest allowed before prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Rotation Context",
        "",
        f"- Hibernated families: {', '.join(rotation.get('hibernated_families', []))}",
        f"- Rotation reason: {rotation.get('rotation_reason', '')}",
        "",
        "## Candidates",
        "",
        "| Factor | Family | Windows | Public refs | Required fields | Failure modes |",
        "|---|---|---|---|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(
            "| {factor} | {family} | {windows} | {refs} | {fields} | {failure_modes} |".format(
                factor=candidate["factor_name"],
                family=candidate["family"],
                windows="/".join(str(item) for item in candidate["windows"]),
                refs=", ".join(candidate["public_reference_tags"]),
                fields=", ".join(candidate["required_fields"]),
                failure_modes=", ".join(candidate["expected_failure_modes"]),
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is preregistration only. It creates no profitability claim.",
            "- Every candidate is blocked from portfolio backtest and promotion until Round128 prescreen evidence exists.",
            "- Round128 must count all candidates in multiple-testing accounting and must not read final holdout data.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_payload(spec: PublicReferenceMultiFamilyCandidateSpec) -> dict[str, Any]:
    return {
        "factor_name": spec.factor_name,
        "family": spec.family,
        "formula_template": spec.formula_template,
        "direction": spec.direction,
        "windows": list(spec.windows),
        "required_fields": list(spec.required_fields),
        "economic_rationale": spec.economic_rationale,
        "public_reference_tags": list(spec.public_reference_tags),
        "expected_failure_modes": list(spec.expected_failure_modes),
        "capacity_filters": dict(spec.capacity_filters or DEFAULT_CAPACITY_FILTERS),
        "source_evidence_status": spec.source_evidence_status,
        "portfolio_backtest_allowed": spec.portfolio_backtest_allowed,
        "promotion_allowed": spec.promotion_allowed,
        "market": "CN",
        "asset_type": "stock",
        "next_required_gate": ROUND128_NEXT_DIRECTION,
    }


def _blockers(candidates: list[dict[str, Any]], *, min_candidates: int, min_families: int) -> list[str]:
    blockers: list[str] = []
    if len(candidates) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len({candidate["factor_name"] for candidate in candidates}) != len(candidates):
        blockers.append("duplicate_candidate_names")
    if len({candidate["family"] for candidate in candidates}) < min_families:
        blockers.append("family_breadth_below_minimum")
    if any(candidate["portfolio_backtest_allowed"] for candidate in candidates):
        blockers.append("portfolio_backtest_allowed_before_prescreen")
    if any(candidate["promotion_allowed"] for candidate in candidates):
        blockers.append("promotion_allowed_before_validation")
    if any("low_turnover" in candidate["factor_name"] for candidate in candidates):
        blockers.append("low_turnover_repair_not_hibernated")
    if any(not candidate["public_reference_tags"] for candidate in candidates):
        blockers.append("missing_public_reference_tags")
    if any(not candidate["expected_failure_modes"] for candidate in candidates):
        blockers.append("missing_expected_failure_modes")
    return blockers


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in result.get("candidates", []) or []:
        rows.append(
            {
                "factor_name": candidate["factor_name"],
                "family": candidate["family"],
                "direction": candidate["direction"],
                "windows": "|".join(str(item) for item in candidate["windows"]),
                "required_fields": "|".join(candidate["required_fields"]),
                "public_reference_tags": "|".join(candidate["public_reference_tags"]),
                "expected_failure_modes": "|".join(candidate["expected_failure_modes"]),
                "source_evidence_status": candidate["source_evidence_status"],
                "portfolio_backtest_allowed": candidate["portfolio_backtest_allowed"],
                "promotion_allowed": candidate["promotion_allowed"],
                "next_required_gate": candidate["next_required_gate"],
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    columns = [
        "factor_name",
        "family",
        "direction",
        "windows",
        "required_fields",
        "public_reference_tags",
        "expected_failure_modes",
        "source_evidence_status",
        "portfolio_backtest_allowed",
        "promotion_allowed",
        "next_required_gate",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in columns})


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass
    return value
