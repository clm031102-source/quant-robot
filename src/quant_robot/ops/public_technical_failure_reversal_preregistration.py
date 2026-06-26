from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
import csv
import json
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.public_reference_multi_family_preregistration import DEFAULT_CAPACITY_FILTERS


STAGE = "public_technical_failure_reversal_preregistration"
SOURCE_AUDIT = "docs/research/cn_stock_round151_153_three_round_review_2026-06-23.md"
NEGATIVE_EVIDENCE_AUDIT = "docs/research/cn_stock_public_reference_multi_family_prescreen_round128_2026-06-22.md"
NEXT_REQUIRED_GATE = "round155_public_technical_failure_reversal_prescreen"
SOURCE_EVIDENCE_STATUS = "negative_public_reference_evidence_reframed_as_new_preregistered_hypothesis"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
PUBLIC_REFERENCE_PROJECTS = (
    "qlib_alpha158",
    "alphalens",
    "vectorbt",
    "public_supertrend",
    "public_rsrs",
    "donchian_breakout",
)


@dataclass(frozen=True)
class PublicTechnicalFailureReversalCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    source_failed_positive_factor: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_public_technical_failure_reversal_specs() -> list[PublicTechnicalFailureReversalCandidateSpec]:
    return [
        PublicTechnicalFailureReversalCandidateSpec(
            factor_name="inverse_donchian_breakout_failure_liquid_20",
            family="public_breakout_failure_reversal",
            formula_template="-0.45*cs_z(donchian_position_20)-0.30*cs_z(return_efficiency_20)+0.25*cs_z(log_adv20)",
            source_failed_positive_factor="donchian_breakout_efficiency_liquid_20",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale="Round128 showed Donchian breakout/efficiency was strongly negative in CN stocks; this preregisters the opposite as a crowding-failure reversal with liquidity kept positive.",
            public_reference_tags=("donchian_breakout", "alphalens", "vectorbt"),
            expected_failure_modes=("post_hoc_inversion_overfit", "range_data_quality", "capacity_tail"),
        ),
        PublicTechnicalFailureReversalCandidateSpec(
            factor_name="inverse_price_efficiency_failure_liquid_20",
            family="qlib_efficiency_failure_reversal",
            formula_template="-0.50*cs_z(return_efficiency_20)-0.25*cs_z(return_20)+0.25*cs_z(log_adv20)",
            source_failed_positive_factor="qlib_alpha158_price_efficiency_liquid_20",
            direction="higher_is_better",
            windows=(20,),
            required_fields=("adj_close", "amount"),
            economic_rationale="Public Qlib-style path efficiency had negative IC; this tests whether efficient trend paths mean crowding/exhaustion rather than continuation in A-shares.",
            public_reference_tags=("qlib_alpha158", "alphalens"),
            expected_failure_modes=("same_price_volume_cluster", "market_regime_dependency", "weak_portfolio_translation"),
        ),
        PublicTechnicalFailureReversalCandidateSpec(
            factor_name="inverse_volume_price_resonance_failure_20_60",
            family="qlib_efficiency_failure_reversal",
            formula_template="-0.40*cs_z(return_20)-0.30*cs_z(amount_trend_20_60)-0.20*cs_z(return_efficiency_20)+0.10*cs_z(log_adv20)",
            source_failed_positive_factor="qlib_alpha158_volume_price_resonance_20_60",
            direction="higher_is_better",
            windows=(20, 60),
            required_fields=("adj_close", "amount"),
            economic_rationale="Volume-confirmed momentum failed in Round128; the inverse hypothesis is that volume-resonant trends are crowded and mean revert.",
            public_reference_tags=("qlib_alpha158", "vectorbt", "alphalens"),
            expected_failure_modes=("momentum_crash_timing", "turnover_cost", "same_cluster_redundancy"),
        ),
        PublicTechnicalFailureReversalCandidateSpec(
            factor_name="inverse_supertrend_breakout_failure_10_20",
            family="supertrend_failure_reversal",
            formula_template="-0.35*cs_z(supertrend_state_10_3)-0.35*cs_z(price_breakout_20)-0.20*cs_z(return_efficiency_20)+0.10*cs_z(log_adv20)",
            source_failed_positive_factor="supertrend_consensus_breakout_efficiency_10_20",
            direction="higher_is_better",
            windows=(10, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale="Naive Supertrend/breakout consensus is treated as an exhaustion/crowding signal, not a standalone trend-following entry.",
            public_reference_tags=("public_supertrend", "vectorbt", "alphalens"),
            expected_failure_modes=("indicator_lag", "choppy_market_false_reversal", "drawdown_tail"),
        ),
        PublicTechnicalFailureReversalCandidateSpec(
            factor_name="supertrend_extension_continuation_repair_10_3",
            family="supertrend_failure_reversal",
            formula_template="-0.45*cs_z(supertrend_distance_reversal_10_3)+0.30*cs_z(-atr_ratio_10)+0.25*cs_z(log_adv20)",
            source_failed_positive_factor="supertrend_pullback_lowvol_liquid_10_3",
            direction="higher_is_better",
            windows=(10, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale="Round128's Supertrend pullback version failed; this repair tests whether CN stocks reward controlled extension rather than pullback.",
            public_reference_tags=("public_supertrend", "vectorbt"),
            expected_failure_modes=("post_hoc_repair", "trend_chop_instability", "cost_drag"),
        ),
        PublicTechnicalFailureReversalCandidateSpec(
            factor_name="inverse_rsrs_slope_failure_liquid_18_60",
            family="rsrs_failure_reversal",
            formula_template="-0.45*cs_z(rsrs_slope_18)-0.30*cs_z(rsrs_slope_delta_60)+0.15*cs_z(-realized_vol_20)+0.10*cs_z(log_adv20)",
            source_failed_positive_factor="rsrs_slope_acceleration_quality_18_60",
            direction="higher_is_better",
            windows=(18, 20, 60),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale="RSRS slope acceleration was negative in Round128; the inverse checks channel-overextension reversal while retaining low-vol and liquidity controls.",
            public_reference_tags=("public_rsrs", "alphalens", "vectorbt"),
            expected_failure_modes=("range_data_quality", "same_rsrs_cluster", "parameter_fragility"),
        ),
        PublicTechnicalFailureReversalCandidateSpec(
            factor_name="rsrs_residual_extreme_reversal_repair_18",
            family="rsrs_failure_reversal",
            formula_template="-0.55*cs_z(rsrs_residual_z_18)+0.25*cs_z(-realized_vol_20)+0.20*cs_z(log_adv20)",
            source_failed_positive_factor="rsrs_residual_reversal_liquid_18",
            direction="higher_is_better",
            windows=(18, 20),
            required_fields=("adj_close", "high", "low", "amount"),
            economic_rationale="Keeps the public RSRS residual mean-reversion idea but isolates it in the post-Round153 rotation batch for fresh accounting.",
            public_reference_tags=("public_rsrs", "alphalens"),
            expected_failure_modes=("tail_event_dependency", "range_data_quality", "redundant_with_bollinger_reversal"),
        ),
        PublicTechnicalFailureReversalCandidateSpec(
            factor_name="inverse_kbar_momentum_failure_lowvol_20",
            family="qlib_candlestick_failure_reversal",
            formula_template="-0.40*cs_z(kbar_close_position_20)-0.35*cs_z(skip5_momentum_20)+0.25*cs_z(-realized_vol_20)",
            source_failed_positive_factor="qlib_alpha158_kbar_momentum_lowvol_20",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("adj_close", "high", "low"),
            economic_rationale="Candlestick close-position plus momentum is tested as reversal/exhaustion because public trend continuation repeatedly failed.",
            public_reference_tags=("qlib_alpha158", "alphalens"),
            expected_failure_modes=("candlestick_noise", "hidden_reversal_cluster", "weak_oos"),
        ),
    ]


def build_public_technical_failure_reversal_preregistration(
    *,
    min_candidates: int = 8,
    min_families: int = 4,
    candidate_specs: Iterable[PublicTechnicalFailureReversalCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_public_technical_failure_reversal_specs())
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
            "portfolio_backtest_allowed_candidates": sum(1 for candidate in candidates if candidate["portfolio_backtest_allowed"]),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": NEXT_REQUIRED_GATE,
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "rotation_context": {
            "source_audit": SOURCE_AUDIT,
            "negative_evidence_audit": NEGATIVE_EVIDENCE_AUDIT,
            "source_round": "round153_profitability_event_revision_failure",
            "rotation_reason": "Round153 produced zero FDR/neutral research leads; rotate away from PIT profitability and test public technical failure-reversal hypotheses.",
            "hibernated_families": ["pit_profitability_event_revision", "alpha101_pv_reversal_residual", "daily_basic_free_float_supply_quality_after_final_holdout_failure"],
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "public_reference_review": {
            "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
            "method": "Public indicators are hypothesis sources only. Inversion after negative evidence is treated as a new preregistered hypothesis and counted in fresh multiple-testing accounting.",
        },
        "capacity_policy": {
            "filters": DEFAULT_CAPACITY_FILTERS,
            "liquidity_kept_positive_when_inverting": True,
            "reason": "Inverting public trend signals must not become an illiquid tail bet.",
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
                "fdr_multiple_testing",
                "industry_size_liquidity_neutral_ic_later_gate",
                "cost_capacity_walk_forward_later_gate",
            ],
            "portfolio_backtest_allowed_after": "statistical_lead_and_dedup_preflight_only",
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
            "requires_reference_dedup": True,
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_public_technical_failure_reversal_preregistration_markdown(result)
    return result


def write_public_technical_failure_reversal_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "public_technical_failure_reversal_preregistration.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_technical_failure_reversal_preregistration.md").write_text(
        render_public_technical_failure_reversal_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "public_technical_failure_reversal_candidates.csv", _candidate_csv_rows(result))


def render_public_technical_failure_reversal_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    rotation = result.get("rotation_context", {})
    lines = [
        "# Public Technical Failure-Reversal Preregistration Round154",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Source audit: {rotation.get('source_audit', SOURCE_AUDIT)}",
        f"- Negative evidence audit: {rotation.get('negative_evidence_audit', NEGATIVE_EVIDENCE_AUDIT)}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio before prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_prescreen', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Candidates",
        "",
        "| Factor | Family | Source failed factor | Windows | Public refs | Failure modes |",
        "|---|---|---|---|---|---|",
    ]
    for candidate in result.get("candidates", []) or []:
        lines.append(
            "| {factor} | {family} | {source} | {windows} | {refs} | {failure_modes} |".format(
                factor=candidate["factor_name"],
                family=candidate["family"],
                source=candidate["source_failed_positive_factor"],
                windows="/".join(str(item) for item in candidate["windows"]),
                refs=", ".join(candidate["public_reference_tags"]),
                failure_modes=", ".join(candidate["expected_failure_modes"]),
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This is preregistration only; it creates no IC, return, Sharpe, win-rate, or promotion claim.",
            "- The source negative evidence is allowed only as motivation for a new fixed hypothesis.",
            "- Round155 must count all candidates in multiple-testing accounting and keep final holdout blocked.",
        ]
    )
    return "\n".join(lines) + "\n"


def _candidate_payload(spec: PublicTechnicalFailureReversalCandidateSpec) -> dict[str, Any]:
    payload = asdict(spec)
    for key in ["windows", "required_fields", "public_reference_tags", "expected_failure_modes"]:
        payload[key] = list(payload[key])
    payload.update(
        {
            "capacity_filters": dict(DEFAULT_CAPACITY_FILTERS),
            "market": "CN",
            "asset_type": "stock",
            "next_required_gate": NEXT_REQUIRED_GATE,
        }
    )
    return payload


def _blockers(candidates: list[dict[str, Any]], *, min_candidates: int, min_families: int) -> list[str]:
    blockers = []
    if len(candidates) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len({candidate["family"] for candidate in candidates}) < min_families:
        blockers.append("family_breadth_below_minimum")
    if len({candidate["factor_name"] for candidate in candidates}) != len(candidates):
        blockers.append("duplicate_candidate_names")
    if any(candidate["portfolio_backtest_allowed"] for candidate in candidates):
        blockers.append("portfolio_backtest_permission_not_allowed_at_preregistration")
    if any(candidate["promotion_allowed"] for candidate in candidates):
        blockers.append("promotion_permission_not_allowed_at_preregistration")
    if any("low_turnover" in candidate["factor_name"] for candidate in candidates):
        blockers.append("low_turnover_repair_family_reused")
    return blockers


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "factor_name": candidate.get("factor_name"),
            "family": candidate.get("family"),
            "source_failed_positive_factor": candidate.get("source_failed_positive_factor"),
            "windows": "|".join(str(item) for item in candidate.get("windows", [])),
            "required_fields": "|".join(candidate.get("required_fields", [])),
            "portfolio_backtest_allowed": candidate.get("portfolio_backtest_allowed"),
            "promotion_allowed": candidate.get("promotion_allowed"),
            "next_required_gate": candidate.get("next_required_gate"),
        }
        for candidate in result.get("candidates", []) or []
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = list(rows[0].keys()) if rows else ["factor_name"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
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
