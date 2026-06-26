from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.public_reference_multi_family_preregistration import DEFAULT_CAPACITY_FILTERS


STAGE = "cn_calendar_seasonality_preregistration"
SOURCE_AUDIT = "docs/research/cn_stock_round160_162_three_round_review_2026-06-23.md"
NEGATIVE_EVIDENCE_AUDIT = "docs/research/cn_stock_cn_market_regime_temperature_residual_prescreen_round162_2026-06-23.md"
NEXT_REQUIRED_GATE = "round164_cn_calendar_seasonality_residual_prescreen"
SOURCE_EVIDENCE_STATUS = "calendar_seasonality_after_round160_162_zero_residual_leads"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."

DEFAULT_REQUIRED_CONTROLS = (
    "ex_ante_calendar_state",
    "cn_trading_calendar_alignment",
    "no_future_holiday_gap_lookup",
    "tradeability_filter_before_signal",
    "industry_style_residual_evaluation",
    "calendar_bucket_coverage",
    "yearly_and_2015_stress_breakout",
    "multiple_testing_accounting",
    "no_portfolio_grid_before_residual_prescreen",
)
FAILED_RECENT_FAMILIES = (
    "moneyflow_residual_regime",
    "industry_relative_strength_breadth_bridge",
    "public_technical_failure_reversal",
    "price_volume_shock_reversal",
    "pit_profitability_event_revision",
    "tradeability_limit_events",
    "china_market_regime_temperature",
    "lottery_extreme_upside_reversal",
    "daily_basic_free_float_supply_quality",
    "turnover_continuous_capacity_repair",
    "low_turnover_repair",
)
PUBLIC_REFERENCE_PROJECTS = (
    "alphalens",
    "mlfinlab_purged_cv",
    "vectorbt",
    "calendar_anomaly_literature",
    "turn_of_month_effect",
    "holiday_effect",
    "day_of_week_effect",
)


@dataclass(frozen=True)
class CNCalendarSeasonalityCandidateSpec:
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
    ex_ante_calendar_state_required: bool = True
    residual_prescreen_required: bool = True
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_cn_calendar_seasonality_specs() -> list[CNCalendarSeasonalityCandidateSpec]:
    return [
        CNCalendarSeasonalityCandidateSpec(
            factor_name="turn_of_month_reversal_liquid_5_5",
            family="turn_of_month_reversal",
            formula_template="I(ex_ante_turn_of_month_window)*cs_z(-ret_5)+0.25*cs_z(log_adv20_amount)-0.20*cs_z(realized_vol_20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("close", "amount", "volume", "industry", "list_date", "trade_calendar"),
            economic_rationale=(
                "Tests whether month-turn liquidity and rebalance flows improve short-term reversal in liquid CN stocks."
            ),
            public_reference_tags=("turn_of_month_effect", "reversal", "liquidity"),
            expected_failure_modes=("small_calendar_bucket_sample", "size_liquidity_redundancy", "2015_crash_calendar_concentration"),
        ),
        CNCalendarSeasonalityCandidateSpec(
            factor_name="turn_of_month_residual_momentum_20_5",
            family="turn_of_month_momentum",
            formula_template="I(ex_ante_turn_of_month_window)*cs_z(ret_20_skip_5)-0.25*cs_z(beta_to_market_60)",
            direction="higher_is_better",
            windows=(5, 20, 60),
            required_fields=("close", "amount", "volume", "industry", "list_date", "trade_calendar"),
            economic_rationale=(
                "Checks whether residual momentum is only paid near the month turn after removing market-beta redundancy."
            ),
            public_reference_tags=("turn_of_month_effect", "residual_momentum", "cross_sectional_momentum"),
            expected_failure_modes=("momentum_beta_redundancy", "month_turn_sample_instability", "industry_rotation_only"),
        ),
        CNCalendarSeasonalityCandidateSpec(
            factor_name="month_end_crowding_exhaustion_10_5",
            family="month_end_exhaustion",
            formula_template="I(ex_ante_last_3_trading_days_of_month)*cs_z(ret_10+turnover_spike_10+realized_vol_20)",
            direction="lower_is_better",
            windows=(5, 10, 20),
            required_fields=("close", "amount", "volume", "industry", "list_date", "trade_calendar"),
            economic_rationale=(
                "Pre-registers a public month-end crowding exhaustion hypothesis before testing whether hot winners fade after month-end pressure."
            ),
            public_reference_tags=("month_end_effect", "crowding", "turnover_exhaustion"),
            expected_failure_modes=("bull_market_momentum_continuation", "turnover_exposure_only", "rebalance_window_overfit"),
        ),
        CNCalendarSeasonalityCandidateSpec(
            factor_name="month_start_liquidity_recovery_5_5",
            family="month_start_liquidity_recovery",
            formula_template="I(ex_ante_first_3_trading_days_of_month)*[0.45*cs_z(log_adv20_amount)+0.35*cs_z(-ret_5)-0.20*cs_z(realized_vol_20)]",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("close", "amount", "volume", "industry", "list_date", "trade_calendar"),
            economic_rationale=(
                "Tests whether beginning-of-month liquidity normalization rewards liquid low-volatility rebound candidates."
            ),
            public_reference_tags=("month_start_effect", "liquidity_recovery", "low_volatility"),
            expected_failure_modes=("liquidity_factor_redundancy", "calendar_bucket_undercoverage", "capacity_reversal_tail"),
        ),
        CNCalendarSeasonalityCandidateSpec(
            factor_name="pre_holiday_liquidity_avoidance_5_3",
            family="pre_holiday_liquidity_avoidance",
            formula_template="I(ex_ante_pre_holiday_1_to_3_trading_days)*cs_z(turnover_spike_5+ret_5-realized_vol_20)",
            direction="lower_is_better",
            windows=(3, 5, 20),
            required_fields=("close", "amount", "volume", "industry", "list_date", "trade_calendar"),
            economic_rationale=(
                "Tests whether crowded short-term strength before known holidays is an avoid signal because liquidity will thin out."
            ),
            public_reference_tags=("holiday_effect", "liquidity_avoidance", "crowding"),
            expected_failure_modes=("future_holiday_lookup_leakage", "thin_sample_by_holiday_type", "pre_holiday_risk_premium_not_alpha"),
        ),
        CNCalendarSeasonalityCandidateSpec(
            factor_name="post_holiday_gap_reversal_quality_3_5",
            family="post_holiday_reversal",
            formula_template="I(ex_ante_first_3_sessions_after_holiday)*[0.50*cs_z(-gap_ret_1)+0.30*cs_z(-ret_3)+0.20*cs_z(-realized_vol_20)]",
            direction="higher_is_better",
            windows=(3, 5, 20),
            required_fields=("open", "close", "amount", "volume", "industry", "list_date", "trade_calendar"),
            economic_rationale=(
                "Tests whether post-holiday gap overreaction reverses in cleaner, lower-volatility names after public calendar closures."
            ),
            public_reference_tags=("holiday_effect", "gap_reversal", "quality_low_volatility"),
            expected_failure_modes=("open_price_quality_gap", "holiday_length_mixed_effect", "gap_reversal_overlap_with_round109"),
        ),
        CNCalendarSeasonalityCandidateSpec(
            factor_name="weekday_monday_reversal_quality_5_5",
            family="weekday_reversal",
            formula_template="I(ex_ante_weekday_monday)*[0.45*cs_z(-ret_5)+0.35*cs_z(-realized_vol_20)+0.20*cs_z(log_adv20_amount)]",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("close", "amount", "volume", "industry", "list_date", "trade_calendar"),
            economic_rationale=(
                "Pre-registers a day-of-week behavioral reversal check while requiring residual tests to avoid generic low-vol/liquidity exposure."
            ),
            public_reference_tags=("day_of_week_effect", "monday_reversal", "low_volatility"),
            expected_failure_modes=("weekday_microstructure_artifact", "low_volatility_redundancy", "sample_size_after_controls"),
        ),
        CNCalendarSeasonalityCandidateSpec(
            factor_name="quarter_end_liquidity_window_reversal_20_5",
            family="quarter_end_liquidity_window",
            formula_template="I(ex_ante_quarter_end_window)*[0.40*cs_z(-ret_20)+0.35*cs_z(log_adv20_amount)-0.25*cs_z(realized_vol_20)]",
            direction="higher_is_better",
            windows=(5, 20, 60),
            required_fields=("close", "amount", "volume", "industry", "list_date", "trade_calendar"),
            economic_rationale=(
                "Checks whether quarter-end liquidity and reporting-window pressure create a tradable reversal setting after controls."
            ),
            public_reference_tags=("quarter_end_effect", "liquidity_window", "reversal"),
            expected_failure_modes=("quarter_end_window_overfit", "institutional_rebalance_not_observable", "2015_and_2020_regime_concentration"),
        ),
    ]


def build_cn_calendar_seasonality_preregistration(
    *,
    min_candidates: int = 8,
    min_families: int = 6,
    candidate_specs: Iterable[CNCalendarSeasonalityCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_cn_calendar_seasonality_specs())
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
            "ex_ante_calendar_required_candidates": sum(
                1 for candidate in candidates if candidate["ex_ante_calendar_state_required"]
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
            "source_round": "round160_162_three_round_review",
            "rotation_reason": (
                "Round160-162 produced zero residual research leads across tradeability events and China market-regime "
                "temperature. Round163 rotates to a public, ex-ante calendar-seasonality family before any new mining."
            ),
            "hibernated_families": list(FAILED_RECENT_FAMILIES),
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "public_reference_review": {
            "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
            "method": (
                "Use public turn-of-month, holiday, day-of-week, and quarter-end anomaly ideas as pre-registered "
                "hypotheses. Calendar states must be known before signal generation, and all candidates must pass "
                "industry/style residual IC and calendar-bucket coverage before any portfolio grid."
            ),
        },
        "capacity_policy": {
            "filters": DEFAULT_CAPACITY_FILTERS,
            "liquidity_kept_positive": True,
            "reason": "Calendar windows can crowd around lower-liquidity dates, so liquidity and blocked-signal controls stay mandatory.",
        },
        "evaluation_gate": {
            "next_required_gate": NEXT_REQUIRED_GATE,
            "required_metrics": [
                "calendar_bucket_coverage",
                "yearly_calendar_bucket_coverage",
                "mean_spearman_ic",
                "icir",
                "ic_t_stat",
                "industry_neutral_ic",
                "style_residual_ic",
                "yearly_residual_stability",
                "stress_2015_residual_breakout",
                "reference_correlation_dedup",
                "factor_turnover",
                "fdr_multiple_testing",
                "tradeability_blocked_signal_rate",
                "cost_capacity_walk_forward_later_gate",
            ],
            "portfolio_backtest_allowed_after": "residual_prescreen_and_calendar_bucket_coverage_only",
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_residual_prescreen": False,
            "requires_ex_ante_calendar_state": True,
            "requires_cn_stock_tradeability_gate": True,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_calendar_bucket_coverage": True,
            "requires_multiple_testing_accounting": True,
            "requires_reference_dedup": True,
            "requires_2015_stress_audit": True,
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_cn_calendar_seasonality_preregistration_markdown(result)
    return result


def write_cn_calendar_seasonality_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "cn_calendar_seasonality_preregistration.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_calendar_seasonality_preregistration.md").write_text(
        render_cn_calendar_seasonality_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "cn_calendar_seasonality_candidates.csv", _candidate_csv_rows(result))


def render_cn_calendar_seasonality_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    rotation = result.get("rotation_context", {})
    lines = [
        "# CN Calendar Seasonality Preregistration Round163",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- Failed recent family candidates: {summary.get('failed_recent_family_candidate_count', 0)}",
        f"- Ex-ante calendar required candidates: {summary.get('ex_ante_calendar_required_candidates', 0)}",
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


def _candidate_payload(spec: CNCalendarSeasonalityCandidateSpec) -> dict[str, Any]:
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
    if any(not candidate.get("ex_ante_calendar_state_required") for candidate in candidates):
        blockers.append("ex_ante_calendar_state_not_required_for_all_candidates")
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
            "ex_ante_calendar_state_required": candidate.get("ex_ante_calendar_state_required", False),
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
