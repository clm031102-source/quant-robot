from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.public_reference_multi_family_preregistration import DEFAULT_CAPACITY_FILTERS


STAGE = "cn_market_regime_temperature_preregistration"
SOURCE_AUDIT = "docs/research/cn_stock_family_rotation_decision_round161_2026-06-23.md"
NEGATIVE_EVIDENCE_AUDIT = "docs/research/cn_stock_cn_tradeability_limit_event_proxy_prescreen_round160_2026-06-23.md"
NEXT_REQUIRED_GATE = "round162_china_market_regime_temperature_residual_prescreen"
SOURCE_EVIDENCE_STATUS = "china_market_regime_temperature_after_round161_rotation"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

DEFAULT_REQUIRED_CONTROLS = (
    "lagged_market_temperature_state",
    "no_same_day_forward_label_leakage",
    "tradeability_filter_before_signal",
    "industry_style_residual_evaluation",
    "regime_coverage_by_signal_window",
    "multiple_testing_accounting",
    "no_portfolio_grid_before_residual_prescreen",
)
FAILED_RECENT_FAMILIES = (
    "tradeability_limit_events",
    "price_volume_shock_reversal",
    "public_technical_failure_reversal",
    "pit_profitability_event_revision",
    "industry_relative_strength_breadth_bridge",
    "moneyflow_residual_regime",
)
PUBLIC_REFERENCE_PROJECTS = (
    "alphalens",
    "mlfinlab_purged_cv",
    "vectorbt",
    "market_breadth",
    "cross_sectional_dispersion",
    "regime_conditioned_alpha",
)


@dataclass(frozen=True)
class CNMarketRegimeTemperatureCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    required_controls: tuple[str, ...] = DEFAULT_REQUIRED_CONTROLS
    lagged_regime_state_required: bool = True
    residual_prescreen_required: bool = True
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_cn_market_regime_temperature_specs() -> list[CNMarketRegimeTemperatureCandidateSpec]:
    return [
        CNMarketRegimeTemperatureCandidateSpec(
            factor_name="regime_cold_liquidity_reversal_quality_20_5",
            family="cold_liquidity_reversal",
            formula_template="I(lag_mkt_liquidity_temp_z<-1)*cs_z(-ret_20)+0.30*cs_z(log_adv20_amount)-0.20*cs_z(realized_vol_20)",
            direction="higher_is_better",
            windows=(5, 20, 60),
            required_fields=("close", "amount", "volume", "industry", "list_date"),
            economic_rationale=(
                "Tests whether broad liquidity-cold regimes reward liquid, lower-volatility reversal candidates after forced de-risking."
            ),
            public_reference_tags=("market_breadth", "liquidity_temperature", "reversal"),
            expected_failure_modes=("bear_regime_continuation", "liquidity_proxy_same_day_leakage", "size_exposure"),
        ),
        CNMarketRegimeTemperatureCandidateSpec(
            factor_name="regime_hot_turnover_exhaustion_avoidance_10_5",
            family="hot_turnover_exhaustion",
            formula_template="I(lag_mkt_turnover_temp_z>1)*cs_z(turnover_spike_10+ret_10-realized_vol_20)",
            direction="lower_is_better",
            windows=(5, 10, 20),
            required_fields=("close", "amount", "volume", "industry", "list_date"),
            economic_rationale=(
                "Flags overheated, high-turnover strength only when the whole market is already hot; treated as an avoidance candidate."
            ),
            public_reference_tags=("turnover_temperature", "overheat", "avoidance"),
            expected_failure_modes=("strong_bull_trend_false_negative", "small_cap_chase_bias", "turnover_definition_instability"),
        ),
        CNMarketRegimeTemperatureCandidateSpec(
            factor_name="breadth_recovery_residual_momentum_20_10",
            family="breadth_recovery_momentum",
            formula_template="I(lag_breadth_recovery_20>0)*cs_z(ret_20_skip_5)-0.25*cs_z(beta_to_market_60)",
            direction="higher_is_better",
            windows=(10, 20, 60),
            required_fields=("close", "amount", "volume", "industry", "list_date"),
            economic_rationale=(
                "Separates residual momentum in names that lead a broad recovery from pure beta when market breadth turns up."
            ),
            public_reference_tags=("breadth_recovery", "residual_momentum", "cross_sectional_momentum"),
            expected_failure_modes=("beta_redundancy", "industry_rotation_only", "breadth_proxy_undercoverage"),
        ),
        CNMarketRegimeTemperatureCandidateSpec(
            factor_name="dispersion_high_lowvol_residual_reversal_20_5",
            family="dispersion_reversal",
            formula_template="I(lag_cross_sectional_dispersion_z>1)*cs_z(-ret_20-realized_vol_20)+0.20*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(5, 20, 60),
            required_fields=("close", "amount", "volume", "industry", "list_date"),
            economic_rationale=(
                "Tests whether broad cross-sectional dispersion creates a better reversal setting for liquid, low-volatility stocks."
            ),
            public_reference_tags=("cross_sectional_dispersion", "low_volatility", "reversal"),
            expected_failure_modes=("lottery_tail_contamination", "industry_crash_exposure", "volatility_as_only_driver"),
        ),
        CNMarketRegimeTemperatureCandidateSpec(
            factor_name="index_location_low_residual_value_liquidity_60_10",
            family="low_index_location_value_liquidity",
            formula_template="I(lag_index_location_252<0.35)*(0.35*cs_z(-pb)+0.35*cs_z(log_adv20_amount)+0.30*cs_z(-ret_60))",
            direction="higher_is_better",
            windows=(10, 60, 252),
            required_fields=("close", "amount", "volume", "pb", "industry", "list_date"),
            economic_rationale=(
                "Tests whether low index-location regimes make liquid value/reversal combinations more effective than in hot markets."
            ),
            public_reference_tags=("index_location", "value", "liquidity", "reversal"),
            expected_failure_modes=("daily_basic_value_redundancy", "pb_coverage_gap", "value_trap_in_bear_market"),
        ),
        CNMarketRegimeTemperatureCandidateSpec(
            factor_name="market_temperature_state_interaction_composite_20_5",
            family="regime_temperature_composite",
            formula_template="state_weight(lag_temp_state)*[cs_z(-ret_20), cs_z(ret_20_skip_5), cs_z(-vol_20), cs_z(log_adv20_amount)]",
            direction="higher_is_better",
            windows=(5, 20, 60, 252),
            required_fields=("close", "amount", "volume", "industry", "list_date"),
            economic_rationale=(
                "Pre-registers a state-conditional composite where each market-temperature state chooses a fixed, lagged interaction form before screening."
            ),
            public_reference_tags=("regime_conditioned_alpha", "state_interaction", "multiple_testing_control"),
            expected_failure_modes=("state_overfit", "parameter_sensitivity", "regime_sample_imbalance"),
        ),
    ]


def build_cn_market_regime_temperature_preregistration(
    *,
    min_candidates: int = 6,
    min_families: int = 4,
    candidate_specs: Iterable[CNMarketRegimeTemperatureCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_cn_market_regime_temperature_specs())
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
            "failed_recent_family_candidate_count": _failed_recent_family_count(candidates),
            "lagged_regime_required_candidates": sum(
                1 for candidate in candidates if candidate["lagged_regime_state_required"]
            ),
            "residual_prescreen_required_candidates": sum(
                1 for candidate in candidates if candidate["residual_prescreen_required"]
            ),
            "portfolio_backtest_allowed_candidates": sum(
                1 for candidate in candidates if candidate["portfolio_backtest_allowed"]
            ),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": NEXT_REQUIRED_GATE,
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "rotation_context": {
            "source_audit": SOURCE_AUDIT,
            "negative_evidence_audit": NEGATIVE_EVIDENCE_AUDIT,
            "source_round": "round161_family_rotation_decision",
            "rotation_reason": (
                "Round160 produced zero proxy leads. Round161 selected a different China-market regime-temperature "
                "interaction mechanism and hibernated the recent failed families before any new mining."
            ),
            "hibernated_families": list(FAILED_RECENT_FAMILIES),
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "public_reference_review": {
            "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
            "method": (
                "Use public market breadth, liquidity-temperature, cross-sectional dispersion, and regime-conditioned "
                "alpha ideas as hypotheses. All state variables must be lagged before labels and must pass residual IC "
                "prescreen before any portfolio grid."
            ),
        },
        "capacity_policy": {
            "filters": DEFAULT_CAPACITY_FILTERS,
            "liquidity_kept_positive": True,
            "reason": "Regime interactions can otherwise select untradable panic or mania tails.",
        },
        "evaluation_gate": {
            "next_required_gate": NEXT_REQUIRED_GATE,
            "required_metrics": [
                "market_temperature_state_coverage",
                "signal_window_regime_coverage",
                "mean_spearman_ic",
                "icir",
                "ic_t_stat",
                "industry_neutral_ic",
                "style_residual_ic",
                "yearly_residual_stability",
                "state_bucket_ic_stability",
                "reference_correlation_dedup",
                "factor_turnover",
                "fdr_multiple_testing",
                "tradeability_blocked_signal_rate",
                "cost_capacity_walk_forward_later_gate",
            ],
            "portfolio_backtest_allowed_after": "residual_prescreen_and_state_coverage_only",
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_residual_prescreen": False,
            "requires_lagged_regime_state": True,
            "requires_cn_stock_tradeability_gate": True,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_multiple_testing_accounting": True,
            "requires_reference_dedup": True,
            "requires_state_bucket_stability": True,
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_cn_market_regime_temperature_preregistration_markdown(result)
    return result


def write_cn_market_regime_temperature_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "cn_market_regime_temperature_preregistration.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_market_regime_temperature_preregistration.md").write_text(
        render_cn_market_regime_temperature_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "cn_market_regime_temperature_candidates.csv", _candidate_csv_rows(result))


def render_cn_market_regime_temperature_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    rotation = result.get("rotation_context", {})
    lines = [
        "# CN Market Regime Temperature Preregistration Round161",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- Failed recent family candidates: {summary.get('failed_recent_family_candidate_count', 0)}",
        f"- Lagged regime required candidates: {summary.get('lagged_regime_required_candidates', 0)}",
        f"- Residual prescreen required candidates: {summary.get('residual_prescreen_required_candidates', 0)}",
        f"- Portfolio candidates: {summary.get('portfolio_backtest_allowed_candidates', 0)}",
        f"- Promotion candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Source audit: {rotation.get('source_audit', SOURCE_AUDIT)}",
        f"- Negative evidence audit: {rotation.get('negative_evidence_audit', NEGATIVE_EVIDENCE_AUDIT)}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio before residual prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_residual_prescreen', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Rotation Context",
        "",
        f"- Reason: {rotation.get('rotation_reason', '')}",
        f"- Hibernated families: {', '.join(rotation.get('hibernated_families', []) or [])}",
        "",
        "## Candidates",
        "",
    ]
    for candidate in result.get("candidates", []):
        lines.extend(
            [
                f"### {candidate.get('factor_name')}",
                "",
                f"- Family: {candidate.get('family')}",
                f"- Direction: {candidate.get('direction')}",
                f"- Windows: {', '.join(str(item) for item in candidate.get('windows', []))}",
                f"- Formula template: `{candidate.get('formula_template')}`",
                f"- Required fields: {', '.join(candidate.get('required_fields', []))}",
                f"- Required controls: {', '.join(candidate.get('required_controls', []))}",
                f"- Rationale: {candidate.get('economic_rationale')}",
                f"- Public references: {', '.join(candidate.get('public_reference_tags', []))}",
                f"- Expected failure modes: {', '.join(candidate.get('expected_failure_modes', []))}",
                "",
            ]
        )
    return "\n".join(lines)


def _candidate_payload(spec: CNMarketRegimeTemperatureCandidateSpec) -> dict[str, Any]:
    payload = asdict(spec)
    payload.update(
        {
            "market": "CN",
            "asset_type": "stock",
            "source_audit": SOURCE_AUDIT,
            "next_required_gate": NEXT_REQUIRED_GATE,
        }
    )
    return payload


def _blockers(candidates: list[dict[str, Any]], *, min_candidates: int, min_families: int) -> list[str]:
    blockers: list[str] = []
    if len(candidates) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len({candidate["family"] for candidate in candidates}) < min_families:
        blockers.append("family_breadth_below_minimum")
    if len({candidate["factor_name"] for candidate in candidates}) != len(candidates):
        blockers.append("duplicate_candidate_names")
    if _failed_recent_family_count(candidates):
        blockers.append("failed_recent_family_reentry_blocked")
    if any(not candidate.get("lagged_regime_state_required") for candidate in candidates):
        blockers.append("lagged_regime_state_not_required_for_all_candidates")
    if any(not candidate.get("residual_prescreen_required") for candidate in candidates):
        blockers.append("residual_prescreen_not_required_for_all_candidates")
    if any(candidate.get("portfolio_backtest_allowed") for candidate in candidates):
        blockers.append("portfolio_backtest_allowed_before_residual_prescreen")
    if any(candidate.get("promotion_allowed") for candidate in candidates):
        blockers.append("promotion_allowed_before_validation")
    for candidate in candidates:
        missing = [control for control in DEFAULT_REQUIRED_CONTROLS if control not in candidate.get("required_controls", [])]
        if missing:
            blockers.append(f"candidate_missing_required_controls:{candidate.get('factor_name')}")
    return blockers


def _failed_recent_family_count(candidates: list[dict[str, Any]]) -> int:
    return sum(1 for candidate in candidates if _candidate_in_failed_family(candidate))


def _candidate_in_failed_family(candidate: dict[str, Any]) -> bool:
    family = str(candidate.get("family", "")).lower()
    tags = " ".join(str(tag).lower() for tag in candidate.get("public_reference_tags", []))
    name = str(candidate.get("factor_name", "")).lower()
    searchable = f"{family} {tags} {name}"
    return any(failed.lower() in searchable for failed in FAILED_RECENT_FAMILIES)


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "factor_name": candidate.get("factor_name", ""),
            "family": candidate.get("family", ""),
            "direction": candidate.get("direction", ""),
            "windows": "|".join(str(item) for item in candidate.get("windows", [])),
            "required_fields": "|".join(candidate.get("required_fields", [])),
            "required_controls": "|".join(candidate.get("required_controls", [])),
            "lagged_regime_state_required": candidate.get("lagged_regime_state_required", False),
            "residual_prescreen_required": candidate.get("residual_prescreen_required", False),
            "portfolio_backtest_allowed": candidate.get("portfolio_backtest_allowed", False),
            "promotion_allowed": candidate.get("promotion_allowed", False),
        }
        for candidate in result.get("candidates", [])
    ]


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
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
    return value
