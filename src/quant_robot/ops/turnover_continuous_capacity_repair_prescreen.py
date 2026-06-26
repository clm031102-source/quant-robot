from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS as BASE_RESULT_COLUMNS,
    _data_window,
    _is_finite,
    _sanitize,
    _spearman,
    _write_csv,
    load_capacity_safe_bars,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.ops.turnover_continuous_capacity_repair_preregistration import (
    NEXT_REQUIRED_GATE as PREREGISTERED_NEXT_GATE,
    SAFETY,
    SOURCE_AUDIT,
    default_turnover_continuous_capacity_repair_specs,
)
from quant_robot.research.labels import make_forward_returns
from quant_robot.storage.factor_inputs import load_factor_inputs


STAGE = "turnover_continuous_capacity_repair_prescreen"
NEXT_DEDUP_GATE = "turnover_repair_correlation_dedup_and_small_capital_sensitivity"
NEXT_ROTATION_DIRECTION = "round125_low_turnover_family_hibernation_profitability_quality_rotation"
DEFAULT_PORTFOLIO_CAPITAL = 100_000.0
DEFAULT_TOP_N = 100
DEFAULT_MAX_PARTICIPATION = 0.01
DEFAULT_EXTREME_FORWARD_RETURN = 0.50
DEFAULT_MAX_EXTREME_FORWARD_RETURN_RATE = 0.10
DEFAULT_MIN_RAW_FACTOR_CORRELATION = 0.20

RESULT_COLUMNS = BASE_RESULT_COLUMNS + [
    "capacity_limited_top_quantile_trades",
    "max_estimated_participation",
    "median_estimated_participation",
    "extreme_forward_return_count",
    "extreme_forward_return_rate",
    "raw_factor_spearman_corr",
    "capacity_clean",
]


def build_turnover_continuous_capacity_repair_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    factor_input_root: str | Path,
    candidate_specs: Sequence[Any] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
    portfolio_capital: float = DEFAULT_PORTFOLIO_CAPITAL,
    top_n: int = DEFAULT_TOP_N,
    max_participation: float = DEFAULT_MAX_PARTICIPATION,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_turnover_continuous_capacity_repair_specs())
    bars = load_capacity_safe_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    daily_basic = load_factor_inputs(factor_input_root, "CN")
    factor_frame = compute_turnover_continuous_capacity_repair_factors(
        bars,
        daily_basic,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
        portfolio_capital=portfolio_capital,
        top_n=top_n,
        max_participation=max_participation,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_turnover_continuous_capacity_repair_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        max_participation=max_participation,
    )
    result["data_window"] = _data_window(bars, factor_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "portfolio_capital": portfolio_capital,
        "top_n": top_n,
        "per_position_notional": portfolio_capital / top_n if top_n else 0.0,
        "max_position_adv_participation": max_participation,
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["source_context"] = {
        "source_audit": SOURCE_AUDIT,
        "source_preregistration": "docs/research/cn_stock_turnover_continuous_capacity_repair_preregistration_round123_2026-06-22.md",
        "preregistered_next_gate": PREREGISTERED_NEXT_GATE,
        "raw_research_leads": ["turnover_rate_low", "turnover_rate_f_low"],
        "binary_large_mv_repair_reused": False,
    }
    result["markdown"] = render_turnover_continuous_capacity_repair_prescreen_markdown(result)
    return result


def compute_turnover_continuous_capacity_repair_factors(
    bars: pd.DataFrame,
    daily_basic: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any] | None = None,
    min_signal_date_amount: float = 10_000_000,
    portfolio_capital: float = DEFAULT_PORTFOLIO_CAPITAL,
    top_n: int = DEFAULT_TOP_N,
    max_participation: float = DEFAULT_MAX_PARTICIPATION,
) -> pd.DataFrame:
    specs = list(candidate_specs or default_turnover_continuous_capacity_repair_specs())
    features = _feature_frame(
        bars,
        daily_basic,
        portfolio_capital=portfolio_capital,
        top_n=top_n,
    )
    if features.empty:
        return _empty_factor_frame()
    features = _add_cross_sectional_features(features)
    candidate_values = {
        "turnover_rate_low_adv_soft_rank_20": (
            features["z_neg_turnover_rate"] * features["adv_rank_clip"]
            + 0.20 * features["z_log_circ_mv"]
        ),
        "turnover_rate_low_adv_mv_soft_blend_20": (
            0.60 * features["z_neg_turnover_rate"]
            + 0.25 * features["z_log_adv20"]
            + 0.15 * features["z_log_circ_mv"]
        ),
        "turnover_rate_low_participation_budget_100k_20": (
            features["z_neg_turnover_rate"] * features["participation_budget_clip"]
        ),
        "turnover_rate_f_low_adv_soft_rank_20": (
            features["z_neg_turnover_rate_f"] * features["adv_rank_clip"]
            + 0.20 * features["z_log_circ_mv"]
        ),
        "turnover_rate_f_low_adv_mv_soft_blend_20": (
            0.60 * features["z_neg_turnover_rate_f"]
            + 0.25 * features["z_log_adv20"]
            + 0.15 * features["z_log_circ_mv"]
        ),
        "turnover_rate_f_low_participation_budget_100k_20": (
            features["z_neg_turnover_rate_f"] * features["participation_budget_clip"]
        ),
    }
    raw_values = {
        "turnover_rate_low": features["z_neg_turnover_rate"],
        "turnover_rate_f_low": features["z_neg_turnover_rate_f"],
    }
    spec_by_name = {spec.factor_name: spec for spec in specs}
    rows: list[pd.DataFrame] = []
    base_columns = [
        "date",
        "asset_id",
        "market",
        "amount",
        "adv20_amount",
        "circ_mv",
        "estimated_participation_100k_top100_adv20",
    ]
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= DEFAULT_EXTREME_FORWARD_RETURN)
        & (features["estimated_participation_100k_top100_adv20"] <= max(1.0, max_participation * 500.0))
    )
    for factor_name, values in candidate_values.items():
        spec = spec_by_name.get(factor_name)
        if spec is None:
            continue
        frame = features.loc[capacity_mask, base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = values.loc[capacity_mask]
        frame["raw_factor_name"] = spec.raw_factor_name
        frame["raw_factor_value"] = raw_values[spec.raw_factor_name].loc[capacity_mask]
        frame = frame.dropna(
            subset=[
                "factor_value",
                "raw_factor_value",
                "amount",
                "adv20_amount",
                "estimated_participation_100k_top100_adv20",
            ]
        )
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def summarize_turnover_continuous_capacity_repair_prescreen(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    expected_candidate_count: int | None = None,
    candidate_specs: Sequence[Any] | None = None,
    horizons: tuple[int, ...] | None = None,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    max_participation: float = DEFAULT_MAX_PARTICIPATION,
    extreme_forward_return: float = DEFAULT_EXTREME_FORWARD_RETURN,
    max_extreme_forward_return_rate: float = DEFAULT_MAX_EXTREME_FORWARD_RETURN_RATE,
    min_raw_factor_correlation: float = DEFAULT_MIN_RAW_FACTOR_CORRELATION,
) -> dict[str, Any]:
    result = summarize_capacity_safe_price_volume_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=expected_candidate_count,
        candidate_specs=candidate_specs or default_turnover_continuous_capacity_repair_specs(),
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    diagnostics = _capacity_repair_diagnostics(
        factor_frame,
        labels,
        horizons=tuple(horizons or result["summary"].get("horizons", [])),
        max_participation=max_participation,
        extreme_forward_return=extreme_forward_return,
    )
    for row in result["results"]:
        key = (row["factor_name"], int(row["horizon"]))
        row.update(diagnostics.get(key, _empty_diagnostics()))
        row["capacity_clean"] = bool(
            row["capacity_limited_top_quantile_trades"] == 0
            and row["max_estimated_participation"] <= max_participation
            and row["extreme_forward_return_rate"] <= max_extreme_forward_return_rate
        )
        base_lead = bool(row["research_lead"])
        row["research_lead"] = bool(
            base_lead
            and row["capacity_clean"]
            and row["raw_factor_spearman_corr"] >= min_raw_factor_correlation
        )
        row["blockers"] = _turnover_repair_blockers(
            row,
            base_blockers=row.get("blockers", []),
            min_raw_factor_correlation=min_raw_factor_correlation,
            max_extreme_forward_return_rate=max_extreme_forward_return_rate,
        )
    lead_count = sum(1 for row in result["results"] if row["research_lead"])
    capacity_clean_tests = sum(1 for row in result["results"] if row.get("capacity_clean"))
    result["stage"] = STAGE
    result["summary"]["research_lead_count"] = int(lead_count)
    result["summary"]["capacity_clean_tests"] = int(capacity_clean_tests)
    result["summary"]["promotion_allowed_candidates"] = 0
    result["summary"]["next_direction"] = NEXT_DEDUP_GATE if lead_count else NEXT_ROTATION_DIRECTION
    result["summary"]["portfolio_backtest_allowed_candidates"] = 0
    result["candidate_specs"] = [_spec_payload(spec) for spec in (candidate_specs or default_turnover_continuous_capacity_repair_specs())]
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": NEXT_DEDUP_GATE if lead_count else NEXT_ROTATION_DIRECTION,
        "next_allowed_action": (
            "run_correlation_dedup_and_small_capital_sensitivity_if_leads_survive"
            if lead_count
            else "hibernate_low_turnover_family_and_rotate_to_profitability_quality_coverage"
        ),
        "reason": (
            "Round124 is an IC/quantile/top-quantile turnover/capacity prescreen. "
            "It cannot promote a factor by itself."
        ),
    }
    result["repair_gate_policy"] = {
        "max_participation": max_participation,
        "extreme_forward_return": extreme_forward_return,
        "max_extreme_forward_return_rate": max_extreme_forward_return_rate,
        "min_raw_factor_correlation": min_raw_factor_correlation,
        "binary_large_mv_repair_allowed": False,
        "raw_low_turnover_promotion_allowed": False,
    }
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_turnover_continuous_capacity_repair_prescreen_markdown(result)
    return result


def write_turnover_continuous_capacity_repair_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "turnover_continuous_capacity_repair_prescreen.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "turnover_continuous_capacity_repair_prescreen.md").write_text(
        render_turnover_continuous_capacity_repair_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(
        output_path / "turnover_continuous_capacity_repair_prescreen_results.csv",
        result.get("results", []),
        RESULT_COLUMNS,
    )
    _write_csv(
        output_path / "turnover_continuous_capacity_repair_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_turnover_continuous_capacity_repair_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Turnover Continuous Capacity Repair Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- Capacity-clean tests: {summary.get('capacity_clean_tests', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Portfolio backtest allowed candidates: {summary.get('portfolio_backtest_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', '')}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Source Context",
        "",
        f"- Source audit: {result.get('source_context', {}).get('source_audit', SOURCE_AUDIT)}",
        f"- Source preregistration: {result.get('source_context', {}).get('source_preregistration', '')}",
        f"- Binary large-mv repair reused: {result.get('source_context', {}).get('binary_large_mv_repair_reused', False)}",
        "",
        "## Results",
        "",
        "| Factor | H | IC | ICIR | t | IC+ | Q5-Q1 | Mono | Turnover | MaxPart | CapTrades | ExtremeRate | RawCorr | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {max_part:.4f} | {cap_trades} | {extreme_rate:.2%} | {raw_corr:.3f} | {fdr} | {lead} |".format(
                factor_name=row["factor_name"],
                horizon=row["horizon"],
                ic=row["mean_spearman_ic"],
                icir=row["icir"],
                t=row["ic_t_stat"],
                pos=row["ic_positive_rate"],
                spread=row["quantile_spread"],
                mono=row["quantile_monotonicity"],
                turnover=row["avg_top_quantile_turnover"],
                max_part=row.get("max_estimated_participation", 0.0),
                cap_trades=row.get("capacity_limited_top_quantile_trades", 0),
                extreme_rate=row.get("extreme_forward_return_rate", 0.0),
                raw_corr=row.get("raw_factor_spearman_corr", 0.0),
                fdr="yes" if row["fdr_significant"] else "no",
                lead="yes" if row["research_lead"] else "no",
            )
        )
    lines.extend(
        [
            "",
            "## Gate Interpretation",
            "",
            "- This prescreen can only create research leads; it cannot promote a paper-ready or live factor.",
            "- A lead must next pass correlation de-duplication, small-capital sensitivity, long-cycle walk-forward, cost/capacity, and regime checks.",
            "- If no repair keeps IC, quantile spread, and capacity cleanliness, the low-turnover family should be hibernated.",
        ]
    )
    return "\n".join(lines) + "\n"


def _feature_frame(
    bars: pd.DataFrame,
    daily_basic: pd.DataFrame,
    *,
    portfolio_capital: float,
    top_n: int,
) -> pd.DataFrame:
    bar_features = _bar_liquidity_features(bars)
    inputs = _normalise_daily_basic(daily_basic)
    if bar_features.empty or inputs.empty:
        return pd.DataFrame()
    frame = inputs.merge(
        bar_features,
        on=["date", "asset_id", "market"],
        how="inner",
        validate="one_to_one",
    )
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    frame["log_adv20"] = np.log(frame["adv20_amount"].where(frame["adv20_amount"] > 0))
    frame["log_circ_mv"] = np.log(frame["circ_mv"].where(frame["circ_mv"] > 0))
    per_position = portfolio_capital / top_n if top_n else np.nan
    frame["estimated_participation_100k_top100_adv20"] = per_position / frame["adv20_amount"].replace(0, np.nan)
    return frame.replace([np.inf, -np.inf], np.nan)


def _bar_liquidity_features(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required turnover-repair columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["adj_close", "amount"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame[(frame["market"] == "CN") & (frame["adj_close"] > 0) & (frame["amount"] > 0)]
    pieces = []
    for _, group in frame.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        group = group.copy()
        group["return_1d"] = group["adj_close"].pct_change()
        group["adv20_amount"] = group["amount"].rolling(20, min_periods=5).mean()
        pieces.append(group[["date", "asset_id", "market", "amount", "adv20_amount", "return_1d"]])
    if not pieces:
        return pd.DataFrame(columns=["date", "asset_id", "market", "amount", "adv20_amount", "return_1d"])
    return pd.concat(pieces, ignore_index=True)


def _normalise_daily_basic(daily_basic: pd.DataFrame) -> pd.DataFrame:
    frame = daily_basic.copy()
    if "asset_id" not in frame.columns and "symbol" in frame.columns:
        frame["asset_id"] = frame["symbol"].astype(str)
    if "market" not in frame.columns:
        frame["market"] = "CN"
    required = ["date", "asset_id", "market", "turnover_rate", "turnover_rate_f", "circ_mv"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Daily-basic inputs are missing required turnover-repair columns: {', '.join(missing)}")
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    for column in ["turnover_rate", "turnover_rate_f", "circ_mv"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame[(frame["market"] == "CN") & (frame["circ_mv"] > 0)]
    return (
        frame.dropna(subset=required)
        .drop_duplicates(["date", "asset_id", "market"], keep="last")
        [["date", "asset_id", "market", "turnover_rate", "turnover_rate_f", "circ_mv"]]
        .reset_index(drop=True)
    )


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    frame["z_neg_turnover_rate"] = _cs_zscore(frame, -frame["turnover_rate"])
    frame["z_neg_turnover_rate_f"] = _cs_zscore(frame, -frame["turnover_rate_f"])
    frame["z_log_adv20"] = _cs_zscore(frame, frame["log_adv20"])
    frame["z_log_circ_mv"] = _cs_zscore(frame, frame["log_circ_mv"])
    frame["adv_rank_clip"] = frame.groupby("date")["log_adv20"].rank(method="average", pct=True).clip(0.35, 1.00)
    budget = DEFAULT_MAX_PARTICIPATION / frame["estimated_participation_100k_top100_adv20"].replace(0, np.nan)
    frame["participation_budget_clip"] = budget.clip(0.0, 1.0)
    return frame.replace([np.inf, -np.inf], np.nan)


def _capacity_repair_diagnostics(
    factor_frame: pd.DataFrame,
    labels: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    max_participation: float,
    extreme_forward_return: float,
) -> dict[tuple[str, int], dict[str, Any]]:
    if factor_frame.empty or labels.empty:
        return {}
    frame = factor_frame.copy()
    label_frame = labels.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    label_frame["date"] = pd.to_datetime(label_frame["date"])
    requested_horizons = horizons or tuple(sorted(label_frame["horizon"].dropna().astype(int).unique()))
    diagnostics: dict[tuple[str, int], dict[str, Any]] = {}
    labels_by_horizon = {
        int(horizon): horizon_frame.drop(columns=["horizon"]).copy()
        for horizon, horizon_frame in label_frame[label_frame["horizon"].isin(requested_horizons)].groupby("horizon", sort=False)
    }
    for factor_name, factor_group in frame.groupby("factor_name", sort=False):
        for horizon in requested_horizons:
            label_group = labels_by_horizon.get(int(horizon))
            if label_group is None:
                diagnostics[(str(factor_name), int(horizon))] = _empty_diagnostics()
                continue
            merged = factor_group.merge(
                label_group,
                on=["date", "asset_id", "market"],
                how="inner",
                validate="many_to_one",
            )
            diagnostics[(str(factor_name), int(horizon))] = _summarize_capacity_repair_diagnostic(
                merged,
                max_participation=max_participation,
                extreme_forward_return=extreme_forward_return,
            )
    return diagnostics


def _summarize_capacity_repair_diagnostic(
    merged: pd.DataFrame,
    *,
    max_participation: float,
    extreme_forward_return: float,
) -> dict[str, Any]:
    top_participation: list[float] = []
    capacity_limited = 0
    extreme_count = 0
    top_observations = 0
    raw_corrs: list[float] = []
    for _, date_frame in merged.dropna(
        subset=[
            "factor_value",
            "raw_factor_value",
            "forward_return",
            "estimated_participation_100k_top100_adv20",
        ]
    ).groupby("date", sort=True):
        if len(date_frame) < 5:
            continue
        quantiles = _quantile_labels(date_frame["factor_value"])
        if quantiles is None:
            continue
        top = date_frame.loc[quantiles == 4]
        top_observations += int(len(top))
        participation = pd.to_numeric(top["estimated_participation_100k_top100_adv20"], errors="coerce").dropna()
        top_participation.extend(float(value) for value in participation)
        capacity_limited += int((participation > max_participation).sum())
        extreme_count += int((pd.to_numeric(top["forward_return"], errors="coerce").abs() > extreme_forward_return).sum())
        corr = _spearman(date_frame["factor_value"], date_frame["raw_factor_value"])
        if _is_finite(corr):
            raw_corrs.append(float(corr))
    participation_series = pd.Series(top_participation, dtype=float)
    raw_corr = float(pd.Series(raw_corrs, dtype=float).mean()) if raw_corrs else 0.0
    return {
        "capacity_limited_top_quantile_trades": int(capacity_limited),
        "max_estimated_participation": float(participation_series.max()) if not participation_series.empty else 0.0,
        "median_estimated_participation": float(participation_series.median()) if not participation_series.empty else 0.0,
        "extreme_forward_return_count": int(extreme_count),
        "extreme_forward_return_rate": float(extreme_count / top_observations) if top_observations else 0.0,
        "raw_factor_spearman_corr": raw_corr,
    }


def _turnover_repair_blockers(
    row: dict[str, Any],
    *,
    base_blockers: list[str],
    min_raw_factor_correlation: float,
    max_extreme_forward_return_rate: float,
) -> list[str]:
    blockers = list(base_blockers or [])
    if row["capacity_limited_top_quantile_trades"] > 0:
        blockers.append("capacity_limited_top_quantile_trades_present")
    if row["max_estimated_participation"] > DEFAULT_MAX_PARTICIPATION:
        blockers.append("max_participation_above_limit")
    if row["extreme_forward_return_rate"] > max_extreme_forward_return_rate:
        blockers.append("extreme_forward_return_rate_above_limit")
    if row["raw_factor_spearman_corr"] < min_raw_factor_correlation:
        blockers.append("raw_factor_correlation_below_repair_threshold")
    return _dedupe(blockers)


def _empty_diagnostics() -> dict[str, Any]:
    return {
        "capacity_limited_top_quantile_trades": 0,
        "max_estimated_participation": 0.0,
        "median_estimated_participation": 0.0,
        "extreme_forward_return_count": 0,
        "extreme_forward_return_rate": 0.0,
        "raw_factor_spearman_corr": 0.0,
        "capacity_clean": False,
    }


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "date",
            "asset_id",
            "market",
            "factor_name",
            "factor_value",
            "raw_factor_name",
            "raw_factor_value",
            "amount",
            "adv20_amount",
            "circ_mv",
            "estimated_participation_100k_top100_adv20",
        ]
    )


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / std.replace(0, np.nan)


def _quantile_labels(values: pd.Series) -> pd.Series | None:
    try:
        return pd.qcut(values.rank(method="first"), 5, labels=False)
    except ValueError:
        return None


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _spec_payload(spec: Any) -> dict[str, Any]:
    payload = asdict(spec) if hasattr(spec, "__dataclass_fields__") else dict(spec)
    for key in ("windows", "required_fields", "public_reference_tags"):
        if key in payload:
            payload[key] = list(payload[key])
    return payload
