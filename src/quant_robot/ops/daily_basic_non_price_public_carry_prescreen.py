from __future__ import annotations

from dataclasses import asdict
from datetime import date
import csv
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    load_capacity_safe_bars,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (
    KNOWN_DAILY_BASIC_FIELDS,
    SAFETY,
    DailyBasicNonPricePublicCarryCandidateSpec,
    default_daily_basic_non_price_public_carry_specs,
)
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.factor_inputs import load_factor_inputs


STAGE = "daily_basic_non_price_public_carry_prescreen"
NEXT_DIRECTION_WITH_LEADS = "round133_daily_basic_non_price_carry_dedup_before_portfolio_conversion"
NEXT_DIRECTION_WITHOUT_LEADS = "round133_rotate_after_daily_basic_non_price_carry_prescreen_failure"
RESULT_COLUMNS = [
    "factor_name",
    "horizon",
    "ic_observations",
    "mean_spearman_ic",
    "ic_std",
    "icir",
    "ic_t_stat",
    "ic_p_value",
    "bonferroni_significant",
    "fdr_significant",
    "ic_positive_rate",
    "quantile_spread",
    "quantile_monotonicity",
    "avg_top_quantile_turnover",
    "median_cross_section",
    "unique_dates",
    "unique_assets",
    "median_field_coverage_ratio",
    "min_field_coverage_ratio",
    "field_coverage_clean_ratio",
    "capacity_clean_ratio",
    "capacity_limited_rows",
    "median_amount",
    "median_adv20_amount",
    "research_lead",
    "promotion_allowed",
    "blockers",
]
FIELD_COVERAGE_COLUMNS = [
    "factor_name",
    "required_fields",
    "unique_dates",
    "median_cross_section",
    "min_field_coverage_ratio",
    "median_field_coverage_ratio",
    "field_coverage_clean_ratio",
    "capacity_clean_ratio",
    "capacity_limited_rows",
    "coverage_pass",
]


def build_daily_basic_non_price_public_carry_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    daily_basic_roots: Iterable[str | Path],
    candidate_specs: Sequence[DailyBasicNonPricePublicCarryCandidateSpec] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_field_coverage_ratio: float = 0.80,
    min_field_coverage_clean_ratio: float = 0.80,
    min_capacity_clean_ratio: float = 0.80,
    min_signal_date_amount: float = 10_000_000,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_daily_basic_non_price_public_carry_specs())
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    daily_basic = load_daily_basic_non_price_public_carry_inputs(
        daily_basic_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_daily_basic_non_price_public_carry_factors(
        daily_basic,
        candidate_specs=specs,
    )
    factor_frame = attach_daily_basic_capacity_fields(factor_frame, bars)
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_daily_basic_non_price_public_carry_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_field_coverage_ratio=min_field_coverage_ratio,
        min_field_coverage_clean_ratio=min_field_coverage_clean_ratio,
        min_capacity_clean_ratio=min_capacity_clean_ratio,
        min_signal_date_amount=min_signal_date_amount,
    )
    result["data_window"] = _data_window(bars, daily_basic, factor_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "min_capacity_clean_ratio": min_capacity_clean_ratio,
        "capacity_is_diagnostic_not_signal_formula": True,
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["markdown"] = render_daily_basic_non_price_public_carry_prescreen_markdown(result)
    return result


def load_daily_basic_non_price_public_carry_inputs(
    daily_basic_roots: Iterable[str | Path],
    *,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
) -> pd.DataFrame:
    frames = []
    for root in daily_basic_roots:
        frames.append(load_factor_inputs(root, "CN"))
    if not frames:
        raise FileNotFoundError("No daily-basic factor-input roots were provided")
    frame = pd.concat(frames, ignore_index=True)
    frame = _normalise_daily_basic(frame)
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if include_final_holdout and not frame.empty:
        end = max(end, frame["date"].max())
    frame = frame[(frame["date"] >= start) & (frame["date"] <= end)]
    return (
        frame.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def compute_daily_basic_non_price_public_carry_factors(
    daily_basic: pd.DataFrame,
    *,
    candidate_specs: Sequence[DailyBasicNonPricePublicCarryCandidateSpec] | None = None,
) -> pd.DataFrame:
    specs = list(candidate_specs or default_daily_basic_non_price_public_carry_specs())
    features = _feature_frame(daily_basic)
    if features.empty:
        return _empty_factor_frame()
    values = _candidate_values(features, requested_factor_names={spec.factor_name for spec in specs})
    rows: list[pd.DataFrame] = []
    base_columns = ["date", "asset_id", "market"]
    for spec in specs:
        if spec.factor_name not in values:
            continue
        required_fields = list(spec.required_fields)
        available_field_count = features[required_fields].notna().sum(axis=1)
        frame = features[base_columns].copy()
        frame["factor_name"] = spec.factor_name
        frame["factor_value"] = values[spec.factor_name]
        frame["required_field_count"] = len(required_fields)
        frame["available_field_count"] = available_field_count.astype(int)
        frame["field_coverage_ratio"] = available_field_count / max(len(required_fields), 1)
        frame = frame.dropna(subset=["factor_value"])
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def attach_daily_basic_capacity_fields(factor_frame: pd.DataFrame, bars: pd.DataFrame) -> pd.DataFrame:
    if factor_frame.empty:
        return factor_frame.copy()
    capacity = _capacity_frame(bars)
    frame = factor_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.merge(capacity, on=["date", "asset_id", "market"], how="left", validate="many_to_one")


def summarize_daily_basic_non_price_public_carry_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    expected_candidate_count: int | None = None,
    candidate_specs: Sequence[DailyBasicNonPricePublicCarryCandidateSpec] | None = None,
    horizons: tuple[int, ...] | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_field_coverage_ratio: float = 0.80,
    min_field_coverage_clean_ratio: float = 0.80,
    min_capacity_clean_ratio: float = 0.80,
    min_signal_date_amount: float = 10_000_000,
    alpha: float = 0.05,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_daily_basic_non_price_public_carry_specs())
    base_result = summarize_capacity_safe_price_volume_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=expected_candidate_count,
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        alpha=alpha,
    )
    coverage_rows = _field_coverage_rows(
        factor_frame,
        min_field_coverage_ratio=min_field_coverage_ratio,
        min_field_coverage_clean_ratio=min_field_coverage_clean_ratio,
        min_capacity_clean_ratio=min_capacity_clean_ratio,
        min_signal_date_amount=min_signal_date_amount,
        required_fields_by_factor={spec.factor_name: "|".join(spec.required_fields) for spec in specs},
    )
    coverage_by_factor = {row["factor_name"]: row for row in coverage_rows}
    for row in base_result.get("results", []):
        coverage = coverage_by_factor.get(row["factor_name"], {})
        row["median_field_coverage_ratio"] = float(coverage.get("median_field_coverage_ratio", 0.0))
        row["min_field_coverage_ratio"] = float(coverage.get("min_field_coverage_ratio", 0.0))
        row["field_coverage_clean_ratio"] = float(coverage.get("field_coverage_clean_ratio", 0.0))
        row["capacity_clean_ratio"] = float(coverage.get("capacity_clean_ratio", 0.0))
        row["capacity_limited_rows"] = int(coverage.get("capacity_limited_rows", 0))
        row["blockers"] = _daily_basic_result_blockers(
            row,
            base_blockers=row.get("blockers", []),
            min_field_coverage_ratio=min_field_coverage_ratio,
            min_field_coverage_clean_ratio=min_field_coverage_clean_ratio,
            min_capacity_clean_ratio=min_capacity_clean_ratio,
        )
        row["research_lead"] = bool(row.get("research_lead", False) and not _hard_daily_basic_blockers(row))
        row["promotion_allowed"] = False
    summary = base_result["summary"]
    summary["research_lead_count"] = sum(1 for row in base_result.get("results", []) if row["research_lead"])
    summary["promotion_allowed_candidates"] = 0
    summary["coverage_pass_candidate_count"] = sum(1 for row in coverage_rows if row["coverage_pass"])
    summary["field_coverage_row_count"] = len(coverage_rows)
    summary["next_direction"] = NEXT_DIRECTION_WITH_LEADS if summary["research_lead_count"] else NEXT_DIRECTION_WITHOUT_LEADS
    base_result.update(
        {
            "stage": STAGE,
            "candidate_specs": [_spec_payload(spec) for spec in specs],
            "coverage_preflight": {
                "min_field_coverage_ratio": min_field_coverage_ratio,
                "min_field_coverage_clean_ratio": min_field_coverage_clean_ratio,
                "min_capacity_clean_ratio": min_capacity_clean_ratio,
                "min_signal_date_amount": min_signal_date_amount,
                "factor_coverage_rows": len(coverage_rows),
                "coverage_pass_candidate_count": summary["coverage_pass_candidate_count"],
                "field_coverage": coverage_rows,
            },
            "multiple_testing_policy": {
                "alpha": alpha,
                "method": "Bonferroni and Benjamini-Hochberg FDR across daily-basic factor x horizon tests",
            },
            "promotion_policy": {
                "promotion_allowed": False,
                "portfolio_backtest_allowed_before_prescreen": False,
                "requires_next_gate": "daily_basic_lead_dedup_before_portfolio_conversion",
                "reason": "This is a daily-basic coverage/IC/quantile/capacity prescreen, not a tradable portfolio validation.",
            },
            "live_boundary_allowed": False,
            "safety": SAFETY,
        }
    )
    base_result["markdown"] = render_daily_basic_non_price_public_carry_prescreen_markdown(base_result)
    return base_result


def write_daily_basic_non_price_public_carry_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "daily_basic_non_price_public_carry_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "daily_basic_non_price_public_carry_prescreen.md").write_text(
        render_daily_basic_non_price_public_carry_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "daily_basic_non_price_public_carry_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "daily_basic_non_price_public_carry_prescreen_field_coverage.csv",
        result.get("coverage_preflight", {}).get("field_coverage", []),
        FIELD_COVERAGE_COLUMNS,
    )
    _write_csv(
        output_path / "daily_basic_non_price_public_carry_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_daily_basic_non_price_public_carry_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    coverage = result.get("coverage_preflight", {})
    lines = [
        "# Daily-Basic Non-Price Public Carry Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Coverage pass candidates: {summary.get('coverage_pass_candidate_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Next direction: {summary.get('next_direction', NEXT_DIRECTION_WITHOUT_LEADS)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Coverage Preflight",
        "",
        f"- Min field coverage ratio: {coverage.get('min_field_coverage_ratio', 0):.2f}",
        f"- Min capacity clean ratio: {coverage.get('min_capacity_clean_ratio', 0):.2f}",
        f"- Min field coverage clean ratio: {coverage.get('min_field_coverage_clean_ratio', 0):.2f}",
        f"- Factor coverage rows: {coverage.get('factor_coverage_rows', 0)}",
        "",
        "| Factor | Dates | Median XS | Min Field Cov | Median Field Cov | Field Clean | Capacity Clean | Pass |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in coverage.get("field_coverage", [])[:20]:
        lines.append(
            "| {factor_name} | {dates} | {xs:.1f} | {min_cov:.1%} | {median_cov:.1%} | {field_clean:.1%} | {cap:.1%} | {passed} |".format(
                factor_name=row["factor_name"],
                dates=row["unique_dates"],
                xs=row["median_cross_section"],
                min_cov=row["min_field_coverage_ratio"],
                median_cov=row["median_field_coverage_ratio"],
                field_clean=row["field_coverage_clean_ratio"],
                cap=row["capacity_clean_ratio"],
                passed="yes" if row["coverage_pass"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Top Results",
            "",
            "| Factor | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | Field Cov | Cap Clean | FDR | Lead |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
        ]
    )
    for row in result.get("results", [])[:20]:
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {field_cov:.1%} | {cap:.1%} | {fdr} | {lead} |".format(
                factor_name=row["factor_name"],
                horizon=row["horizon"],
                ic=row["mean_spearman_ic"],
                icir=row["icir"],
                t=row["ic_t_stat"],
                pos=row["ic_positive_rate"],
                spread=row["quantile_spread"],
                mono=row["quantile_monotonicity"],
                turnover=row["avg_top_quantile_turnover"],
                field_cov=row.get("median_field_coverage_ratio", 0.0),
                cap=row.get("capacity_clean_ratio", 0.0),
                fdr="yes" if row["fdr_significant"] else "no",
                lead="yes" if row["research_lead"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This stage can create research leads only; it cannot promote a factor to paper-ready or live use.",
            "- Signal formulas use daily-basic non-price fields only. Price bars are used for labels and capacity diagnostics.",
            "- Any lead must next pass factor correlation de-duplication, long-cycle walk-forward, cost/capacity, and regime checks.",
        ]
    )
    return "\n".join(lines) + "\n"


def _normalise_daily_basic(daily_basic: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market"]
    missing = [column for column in required if column not in daily_basic.columns]
    if missing:
        raise ValueError(f"Daily-basic inputs are missing required columns: {', '.join(missing)}")
    frame = daily_basic.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["market"] = frame["market"].fillna("CN").astype(str)
    frame["asset_id"] = frame["asset_id"].astype(str)
    for column in KNOWN_DAILY_BASIC_FIELDS:
        if column not in frame.columns:
            frame[column] = pd.NA
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["date", "asset_id", "market"])
    return frame[frame["market"] == "CN"].reset_index(drop=True)


def _feature_frame(daily_basic: pd.DataFrame) -> pd.DataFrame:
    frame = _normalise_daily_basic(daily_basic)
    if frame.empty:
        return frame
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    frame["inv_pb"] = _positive_inverse(frame["pb"])
    frame["inv_pe_ttm"] = _positive_inverse(frame["pe_ttm"])
    frame["inv_ps_ttm"] = _positive_inverse(frame["ps_ttm"])
    frame["log_circ_mv"] = _positive_log(frame["circ_mv"])
    frame["log_total_mv"] = _positive_log(frame["total_mv"])
    frame["free_share_to_total_share"] = _safe_divide(frame["free_share"], frame["total_share"])
    frame["float_share_to_total_share"] = _safe_divide(frame["float_share"], frame["total_share"])
    frame["free_share_to_float_share"] = _safe_divide(frame["free_share"], frame["float_share"])
    frame["pb_z_60"] = _rolling_z(frame, "pb", 60)
    frame["pe_ttm_z_60"] = _rolling_z(frame, "pe_ttm", 60)
    frame["ps_ttm_z_60"] = _rolling_z(frame, "ps_ttm", 60)
    frame["volume_ratio_z_20"] = _rolling_z(frame, "volume_ratio", 20)
    frame["abs_volume_ratio_z_20"] = frame["volume_ratio_z_20"].abs()
    frame["abs_pb_z_60"] = frame["pb_z_60"].abs()
    frame["abs_pe_ttm_z_60"] = frame["pe_ttm_z_60"].abs()
    pe_stability = frame.groupby("asset_id", sort=False)["pe_ttm"].transform(
        lambda item: item.rolling(20, min_periods=5).std(ddof=0)
    )
    frame["inv_pe_ttm_stable_20"] = frame["inv_pe_ttm"] / (1.0 + pe_stability)
    frame["mid_circ_mv_score"] = -_cs_zscore(frame, frame["log_circ_mv"]).abs()
    frame["mid_total_mv_score"] = -_cs_zscore(frame, frame["log_total_mv"]).abs()
    inv_pb_instability = frame.groupby("asset_id", sort=False)["inv_pb"].transform(
        lambda item: item.rolling(60, min_periods=10).std(ddof=0)
    )
    inv_pe_instability = frame.groupby("asset_id", sort=False)["inv_pe_ttm"].transform(
        lambda item: item.rolling(60, min_periods=10).std(ddof=0)
    )
    frame["valuation_instability_60"] = (inv_pb_instability + inv_pe_instability) / 2.0
    value_yield = _cs_zscore(frame, frame["inv_pb"]) + _cs_zscore(frame, frame["inv_pe_ttm"]) + _cs_zscore(frame, frame["dv_ttm"])
    frame["resid_value_yield_vs_log_circ_mv_20"] = _daily_residual(value_yield, frame["log_circ_mv"], frame["date"])
    return frame.replace([float("inf"), float("-inf")], pd.NA)


def _candidate_values(features: pd.DataFrame, requested_factor_names: set[str] | None = None) -> dict[str, pd.Series]:
    z = lambda series: _cs_zscore(features, series).fillna(0.0)
    requested = set(requested_factor_names or ())
    if not requested:
        requested = {
            "daily_basic_dividend_value_stability_carry_20",
            "daily_basic_value_yield_size_neutral_20",
            "daily_basic_valuation_reversion_quality_60",
            "daily_basic_valuation_reversion_dvratio_quality_60",
            "daily_basic_valuation_dispersion_compression_60",
            "daily_basic_free_float_supply_quality_20",
            "daily_basic_float_structure_value_blend_20",
            "daily_basic_volume_ratio_crowding_reversal_20",
            "daily_basic_crowding_value_yield_balance_20",
            "daily_basic_midcap_value_yield_capacity_20",
            "daily_basic_size_quality_value_stability_60",
        }
    values: dict[str, pd.Series] = {}
    if "daily_basic_dividend_value_stability_carry_20" in requested:
        values["daily_basic_dividend_value_stability_carry_20"] = (
            0.35 * z(features["dv_ttm"])
            + 0.25 * z(features["dv_ratio"])
            + 0.20 * z(features["inv_pb"])
            + 0.20 * z(features["inv_pe_ttm_stable_20"])
        )
    if "daily_basic_value_yield_size_neutral_20" in requested:
        values["daily_basic_value_yield_size_neutral_20"] = (
            0.45 * z(features["resid_value_yield_vs_log_circ_mv_20"])
            + 0.30 * z(features["dv_ttm"])
            + 0.25 * z(features["inv_ps_ttm"])
        )
    if "daily_basic_valuation_reversion_quality_60" in requested:
        values["daily_basic_valuation_reversion_quality_60"] = (
            0.45 * z(-features["pb_z_60"])
            + 0.30 * z(-features["ps_ttm_z_60"])
            + 0.25 * z(features["dv_ttm"])
        )
    if "daily_basic_valuation_reversion_dvratio_quality_60" in requested:
        values["daily_basic_valuation_reversion_dvratio_quality_60"] = (
            0.45 * z(-features["pb_z_60"])
            + 0.30 * z(-features["ps_ttm_z_60"])
            + 0.25 * z(features["dv_ratio"])
        )
    if "daily_basic_valuation_dispersion_compression_60" in requested:
        values["daily_basic_valuation_dispersion_compression_60"] = (
            0.40 * z(-features["abs_pb_z_60"])
            + 0.35 * z(-features["abs_pe_ttm_z_60"])
            + 0.25 * z(features["dv_ratio"])
        )
    if "daily_basic_free_float_supply_quality_20" in requested:
        values["daily_basic_free_float_supply_quality_20"] = (
            0.45 * z(features["free_share_to_total_share"])
            + 0.30 * z(features["float_share_to_total_share"])
            + 0.25 * z(features["inv_pb"])
        )
    if "daily_basic_float_structure_value_blend_20" in requested:
        values["daily_basic_float_structure_value_blend_20"] = (
            0.35 * z(features["free_share_to_float_share"])
            + 0.35 * z(features["inv_pb"])
            + 0.30 * z(features["dv_ttm"])
        )
    if "daily_basic_volume_ratio_crowding_reversal_20" in requested:
        values["daily_basic_volume_ratio_crowding_reversal_20"] = (
            0.45 * z(-features["volume_ratio_z_20"])
            + 0.30 * z(features["inv_pb"])
            + 0.25 * z(features["dv_ttm"])
        )
    if "daily_basic_crowding_value_yield_balance_20" in requested:
        values["daily_basic_crowding_value_yield_balance_20"] = (
            0.35 * z(-features["abs_volume_ratio_z_20"])
            + 0.35 * z(features["inv_ps_ttm"])
            + 0.30 * z(features["dv_ratio"])
        )
    if "daily_basic_midcap_value_yield_capacity_20" in requested:
        values["daily_basic_midcap_value_yield_capacity_20"] = (
            0.30 * z(features["dv_ttm"])
            + 0.30 * z(features["inv_pb"])
            + 0.20 * z(features["inv_ps_ttm"])
            + 0.20 * z(features["mid_circ_mv_score"])
        )
    if "daily_basic_size_quality_value_stability_60" in requested:
        values["daily_basic_size_quality_value_stability_60"] = (
            0.35 * z(features["inv_pb"])
            + 0.25 * z(features["dv_ttm"])
            + 0.20 * z(features["mid_total_mv_score"])
            + 0.20 * z(-features["valuation_instability_60"])
        )
    return values


def _field_coverage_rows(
    factor_frame: pd.DataFrame,
    *,
    min_field_coverage_ratio: float,
    min_field_coverage_clean_ratio: float,
    min_capacity_clean_ratio: float,
    min_signal_date_amount: float,
    required_fields_by_factor: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    rows = []
    if factor_frame.empty:
        return rows
    frame = factor_frame.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    for factor_name, group in frame.groupby("factor_name", sort=False):
        date_cross_sections = group.groupby("date")["asset_id"].nunique()
        field_coverage = pd.to_numeric(group.get("field_coverage_ratio", pd.Series(dtype=float)), errors="coerce")
        amount = pd.to_numeric(group.get("amount", pd.Series(index=group.index, dtype=float)), errors="coerce")
        adv20 = pd.to_numeric(group.get("adv20_amount", pd.Series(index=group.index, dtype=float)), errors="coerce")
        capacity_clean = (amount >= min_signal_date_amount) & (adv20 >= min_signal_date_amount)
        field_clean = field_coverage >= min_field_coverage_ratio
        required_fields = ""
        if required_fields_by_factor and str(factor_name) in required_fields_by_factor:
            required_fields = required_fields_by_factor[str(factor_name)]
        elif "required_fields" in group and not group.empty:
            required_fields = str(group["required_fields"].iloc[0])
        min_cov = float(field_coverage.min()) if not field_coverage.dropna().empty else 0.0
        median_cov = float(field_coverage.median()) if not field_coverage.dropna().empty else 0.0
        cap_ratio = float(capacity_clean.mean()) if len(capacity_clean) else 0.0
        field_clean_ratio = float(field_clean.mean()) if len(field_clean) else 0.0
        row = {
            "factor_name": str(factor_name),
            "required_fields": required_fields,
            "unique_dates": int(group["date"].nunique()),
            "median_cross_section": float(date_cross_sections.median()) if not date_cross_sections.empty else 0.0,
            "min_field_coverage_ratio": min_cov,
            "median_field_coverage_ratio": median_cov,
            "field_coverage_clean_ratio": field_clean_ratio,
            "capacity_clean_ratio": cap_ratio,
            "capacity_limited_rows": int((~capacity_clean).sum()) if len(capacity_clean) else int(len(group)),
            "coverage_pass": bool(
                median_cov >= min_field_coverage_ratio
                and field_clean_ratio >= min_field_coverage_clean_ratio
                and cap_ratio >= min_capacity_clean_ratio
            ),
        }
        rows.append(row)
    return rows


def _daily_basic_result_blockers(
    row: dict[str, Any],
    *,
    base_blockers: list[str],
    min_field_coverage_ratio: float,
    min_field_coverage_clean_ratio: float,
    min_capacity_clean_ratio: float,
) -> list[str]:
    blockers = list(base_blockers)
    if row.get("median_field_coverage_ratio", 0.0) < min_field_coverage_ratio:
        blockers.append("daily_basic_field_coverage_below_minimum")
    if row.get("field_coverage_clean_ratio", 0.0) < min_field_coverage_clean_ratio:
        blockers.append("daily_basic_field_coverage_clean_ratio_below_minimum")
    if row.get("capacity_clean_ratio", 0.0) < min_capacity_clean_ratio:
        blockers.append("daily_basic_capacity_clean_ratio_below_minimum")
    return _dedupe(blockers)


def _hard_daily_basic_blockers(row: dict[str, Any]) -> list[str]:
    return [
        blocker
        for blocker in row.get("blockers", [])
        if blocker
        in {
            "daily_basic_field_coverage_below_minimum",
            "daily_basic_field_coverage_clean_ratio_below_minimum",
            "daily_basic_capacity_clean_ratio_below_minimum",
        }
    ]


def _capacity_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    pieces = []
    for _, group in frame.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        group = group.copy()
        group["adv20_amount"] = group["amount"].rolling(20, min_periods=5).mean()
        pieces.append(group[["date", "asset_id", "market", "amount", "adv20_amount"]])
    if not pieces:
        return pd.DataFrame(columns=["date", "asset_id", "market", "amount", "adv20_amount"])
    return pd.concat(pieces, ignore_index=True)


def _positive_inverse(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return 1.0 / values.where(values > 0)


def _positive_log(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values > 0).apply(lambda value: math.log(value) if _is_finite(value) else pd.NA)


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    left = pd.to_numeric(numerator, errors="coerce")
    right = pd.to_numeric(denominator, errors="coerce")
    return left / right.where(right > 0)


def _rolling_z(frame: pd.DataFrame, column: str, window: int) -> pd.Series:
    values = pd.to_numeric(frame[column], errors="coerce")
    grouped = values.groupby(frame["asset_id"], sort=False)
    mean = grouped.transform(lambda item: item.rolling(window, min_periods=max(5, window // 4)).mean())
    std = grouped.transform(lambda item: item.rolling(window, min_periods=max(5, window // 4)).std(ddof=0))
    return (values - mean) / std.replace(0, pd.NA)


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / std.replace(0, pd.NA)


def _daily_residual(y: pd.Series, x: pd.Series, dates: pd.Series) -> pd.Series:
    frame = pd.DataFrame({"y": pd.to_numeric(y, errors="coerce"), "x": pd.to_numeric(x, errors="coerce"), "date": dates})
    residual = pd.Series(index=frame.index, dtype=float)
    for _, group in frame.groupby("date", sort=False):
        clean = group.dropna(subset=["y", "x"])
        if len(clean) < 3:
            residual.loc[group.index] = group["y"] - group["y"].mean()
            continue
        x_centered = clean["x"] - clean["x"].mean()
        denominator = float((x_centered * x_centered).sum())
        if denominator == 0.0:
            residual.loc[group.index] = group["y"] - clean["y"].mean()
            continue
        beta = float(((clean["y"] - clean["y"].mean()) * x_centered).sum() / denominator)
        alpha = float(clean["y"].mean() - beta * clean["x"].mean())
        residual.loc[clean.index] = clean["y"] - (alpha + beta * clean["x"])
    return residual


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "required_field_count",
            "available_field_count",
            "field_coverage_ratio",
        ]
    )


def _data_window(bars: pd.DataFrame, daily_basic: pd.DataFrame, factor_frame: pd.DataFrame, labels: pd.DataFrame) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_daily_basic_date": _min_date(daily_basic, "date"),
        "max_daily_basic_date": _max_date(daily_basic, "date"),
        "min_signal_date": _min_date(factor_frame, "date"),
        "max_signal_date": _max_date(factor_frame, "date"),
        "min_label_date": _min_date(labels, "date"),
        "max_label_date": _max_date(labels, "date"),
        "bar_rows": int(len(bars)),
        "daily_basic_rows": int(len(daily_basic)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
        "daily_basic_assets": int(daily_basic["asset_id"].nunique()) if not daily_basic.empty else 0,
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _spec_payload(spec: Any) -> dict[str, Any]:
    if hasattr(spec, "__dataclass_fields__"):
        payload = asdict(spec)
        for key in ["windows", "required_fields", "public_reference_tags", "expected_failure_modes"]:
            payload[key] = list(payload[key])
        return payload
    return dict(spec)


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _csv_value(row.get(field)) for field in fieldnames})


def _csv_value(value: Any) -> Any:
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if isinstance(value, float) and not math.isfinite(value):
        return ""
    return value


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _is_finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False
