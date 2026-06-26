from __future__ import annotations

from dataclasses import asdict
from datetime import date
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Sequence

import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS as BASE_RESULT_COLUMNS,
    _apply_multiple_testing,
    _is_research_lead,
    _result_blockers,
    _sanitize,
    _summarize_factor_horizon,
    _write_csv,
)
from quant_robot.ops.public_reference_multi_family_preregistration import (
    ROUND126_SOURCE_AUDIT,
    SAFETY,
    default_public_reference_multi_family_candidate_specs,
)
from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.factor_inputs import load_factor_inputs
from quant_robot.storage.moneyflow_inputs import load_moneyflow_inputs


STAGE = "public_reference_multi_family_prescreen"
ROUND127_PREREGISTRATION = "docs/research/cn_stock_public_reference_multi_family_preregistration_round127_2026-06-22.md"
ROUND129_NEXT_DIRECTION = "round129_round126_128_three_round_review_before_next_action"
NEXT_REQUIRED_GATE = "round129_round126_128_three_round_review_before_next_action"
RESULT_COLUMNS = [
    "factor_name",
    "family",
    *[column for column in BASE_RESULT_COLUMNS if column != "factor_name"],
]


def build_public_reference_multi_family_prescreen(
    *,
    bars_roots: Iterable[str | Path],
    factor_input_root: str | Path,
    moneyflow_input_root: str | Path,
    candidate_specs: Sequence[Any] | None = None,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
    horizons: tuple[int, ...] = (5, 10, 20),
    execution_lag: int = 1,
    min_cross_section: int = 30,
    min_ic_observations: int = 20,
    min_signal_date_amount: float = 10_000_000,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_public_reference_multi_family_candidate_specs())
    bars = load_public_reference_multi_family_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_inputs = load_factor_inputs(factor_input_root, "CN")
    moneyflow_inputs = load_moneyflow_inputs(moneyflow_input_root, "CN")
    features = _feature_frame(bars, factor_inputs=factor_inputs, moneyflow_inputs=moneyflow_inputs)
    features = _add_cross_sectional_features(features)
    features = _add_forward_return_columns(
        features,
        horizons=horizons,
        execution_lag=execution_lag,
    )
    result = summarize_public_reference_multi_family_prescreen_from_features(
        features,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
        min_signal_date_amount=min_signal_date_amount,
    )
    result["stage"] = STAGE
    result["summary"]["next_direction"] = ROUND129_NEXT_DIRECTION
    result["summary"]["promotion_allowed_candidates"] = 0
    result["summary"]["portfolio_backtest_allowed_candidates"] = 0
    result["candidate_specs"] = [_spec_payload(spec) for spec in specs]
    result["data_window"] = _streaming_data_window(
        bars,
        features,
        horizons=horizons,
        min_signal_date_amount=min_signal_date_amount,
    )
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["multiple_testing_policy"]["counts_all_round127_candidates"] = True
    result["multiple_testing_policy"]["round127_candidate_count"] = len(specs)
    result["source_context"] = {
        "source_audit": ROUND126_SOURCE_AUDIT,
        "source_preregistration": ROUND127_PREREGISTRATION,
        "public_reference_projects_are_hypothesis_sources_only": True,
        "portfolio_grid_blocked_before_statistical_lead": True,
        "hibernated_families": ["low_turnover_repair", "turnover_repair_champion"],
    }
    result["capacity_policy"] = {
        "min_signal_date_amount": min_signal_date_amount,
        "adv20_amount_filter_enabled": True,
        "portfolio_backtest_allowed_before_prescreen_lead": False,
    }
    result["promotion_policy"] = {
        "promotion_allowed": False,
        "portfolio_backtest_allowed_before_prescreen": False,
        "requires_next_gate": NEXT_REQUIRED_GATE,
        "next_allowed_action": "round126_128_three_round_review_before_any_portfolio_grid_or_family_lock_in",
        "reason": "Round128 is a long-cycle IC/quantile/turnover prescreen, not a tradable portfolio validation.",
    }
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_public_reference_multi_family_prescreen_markdown(result)
    return result


def load_public_reference_multi_family_bars(
    bars_roots: Iterable[str | Path],
    *,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
) -> pd.DataFrame:
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    files: list[Path] = []
    for root in bars_roots:
        root_path = Path(root)
        if (root_path / "processed" / "bars").exists():
            bars_root = root_path / "processed" / "bars"
        elif (root_path / "bars").exists():
            bars_root = root_path / "bars"
        else:
            bars_root = root_path
        files.extend(sorted(bars_root.rglob("*.parquet")))
        files.extend(sorted(bars_root.rglob("*.csv")))
    files = _filter_bar_files_by_date_window(
        [file for file in files if "market=CN" in str(file) or "bars" in str(file)],
        start=start,
        end=None if include_final_holdout else end,
    )
    frames = [_filter_bar_frame_to_date_window(_read_bars_file(file), start=start, end=None if include_final_holdout else end) for file in files]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise FileNotFoundError(f"No CN bar files found under: {', '.join(str(root) for root in bars_roots)}")
    bars = pd.concat(frames, ignore_index=True)
    bars = _normalise_bars(bars)
    if include_final_holdout:
        end = max(end, bars["date"].max())
    bars = bars[(bars["date"] >= start) & (bars["date"] <= end)]
    return (
        bars.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _filter_bar_files_by_date_window(files: list[Path], *, start: pd.Timestamp, end: pd.Timestamp | None) -> list[Path]:
    output: list[Path] = []
    start_year = int(start.year)
    end_year = int(end.year) if end is not None else None
    for file in files:
        year = _year_from_partition_path(file)
        if year is None:
            output.append(file)
            continue
        if year < start_year:
            continue
        if end_year is not None and year > end_year:
            continue
        output.append(file)
    return output


def _year_from_partition_path(file: Path) -> int | None:
    match = re.search(r"(?:^|[\\/])year=(\d{4})(?:[\\/]|$)", str(file))
    return int(match.group(1)) if match else None


def _filter_bar_frame_to_date_window(
    frame: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp | None,
) -> pd.DataFrame:
    if frame.empty or "date" not in frame:
        return frame
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    mask = output["date"] >= start
    if end is not None:
        mask &= output["date"] <= end
    return output.loc[mask].reset_index(drop=True)


def compute_public_reference_multi_family_factors(
    bars: pd.DataFrame,
    *,
    factor_inputs: pd.DataFrame,
    moneyflow_inputs: pd.DataFrame,
    candidate_specs: Sequence[Any] | None = None,
    min_signal_date_amount: float = 10_000_000,
) -> pd.DataFrame:
    specs = list(candidate_specs or default_public_reference_multi_family_candidate_specs())
    features = _feature_frame(bars, factor_inputs=factor_inputs, moneyflow_inputs=moneyflow_inputs)
    if features.empty:
        return _empty_factor_frame()
    features = _add_cross_sectional_features(features)
    candidate_values = _candidate_value_series(features)
    spec_by_name = {spec.factor_name: spec for spec in specs}
    base_columns = [
        "date",
        "asset_id",
        "market",
        "amount",
        "adv20_amount",
        "family",
    ]
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    rows: list[pd.DataFrame] = []
    for factor_name, values in candidate_values.items():
        spec = spec_by_name.get(factor_name)
        if spec is None:
            continue
        frame = features.loc[capacity_mask, ["date", "asset_id", "market", "amount", "adv20_amount"]].copy()
        frame["family"] = spec.family
        frame["factor_name"] = factor_name
        frame["factor_value"] = values.loc[capacity_mask]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        rows.append(frame[base_columns + ["factor_name", "factor_value"]])
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def summarize_public_reference_multi_family_prescreen_from_features(
    features: pd.DataFrame,
    *,
    expected_candidate_count: int,
    candidate_specs: Sequence[Any],
    horizons: tuple[int, ...],
    min_cross_section: int,
    min_ic_observations: int,
    min_signal_date_amount: float,
    alpha: float = 0.05,
    min_abs_ic: float = 0.02,
    min_abs_icir: float = 0.30,
    min_positive_ic_rate: float = 0.55,
    max_top_quantile_turnover: float = 0.90,
) -> dict[str, Any]:
    requested_horizons = tuple(int(horizon) for horizon in horizons)
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    candidate_values = _candidate_value_series(features)
    results: list[dict[str, Any]] = []
    ic_rows: list[dict[str, Any]] = []
    aligned_rows = 0
    factor_rows = 0
    families_with_rows: set[str] = set()
    factor_names_with_rows: set[str] = set()
    unique_assets: set[str] = set()

    for spec in candidate_specs:
        values = candidate_values.get(spec.factor_name)
        if values is None:
            factor_frame = _empty_factor_frame()
        else:
            factor_frame = features.loc[
                capacity_mask,
                ["date", "asset_id", "market", "amount", "adv20_amount"],
            ].copy()
            factor_frame["family"] = spec.family
            factor_frame["factor_name"] = spec.factor_name
            factor_frame["factor_value"] = values.loc[capacity_mask]
            factor_frame = factor_frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        factor_rows += len(factor_frame)
        if not factor_frame.empty:
            families_with_rows.add(spec.family)
            factor_names_with_rows.add(spec.factor_name)
            unique_assets.update(factor_frame["asset_id"].astype(str).unique().tolist())
        for horizon in requested_horizons:
            forward_column = f"forward_return_{horizon}"
            if factor_frame.empty or forward_column not in features:
                group = pd.DataFrame(columns=list(factor_frame.columns) + ["forward_return"])
            else:
                group = factor_frame.copy()
                group["forward_return"] = features.loc[group.index, forward_column]
                group = group.dropna(subset=["forward_return"])
            aligned_rows += len(group)
            summary, observations = _summarize_factor_horizon(
                factor_name=spec.factor_name,
                horizon=int(horizon),
                group=group,
                min_cross_section=min_cross_section,
                min_ic_observations=min_ic_observations,
            )
            summary["family"] = spec.family
            summary["source_evidence_status"] = spec.source_evidence_status
            results.append(summary)
            ic_rows.extend(observations)

    _apply_multiple_testing(results, alpha=alpha)
    for row in results:
        row["research_lead"] = _is_research_lead(
            row,
            min_abs_ic=min_abs_ic,
            min_abs_icir=min_abs_icir,
            min_positive_ic_rate=min_positive_ic_rate,
            max_top_quantile_turnover=max_top_quantile_turnover,
        )
        row["promotion_allowed"] = False
        row["blockers"] = _result_blockers(row)

    result = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": True,
            "candidate_count": int(expected_candidate_count),
            "family_count": len({spec.family for spec in candidate_specs}),
            "factor_names_with_rows": len(factor_names_with_rows),
            "families_with_rows": len(families_with_rows),
            "test_count": len(results),
            "research_lead_count": sum(1 for row in results if row["research_lead"]),
            "multiple_testing_lead_count": sum(1 for row in results if row["fdr_significant"]),
            "promotion_allowed_candidates": 0,
            "portfolio_backtest_allowed_candidates": 0,
            "factor_rows": int(factor_rows),
            "label_rows": int(
                sum(
                    features[f"forward_return_{horizon}"].notna().sum()
                    for horizon in requested_horizons
                    if f"forward_return_{horizon}" in features
                )
            ),
            "aligned_rows": int(aligned_rows),
            "horizons": sorted(requested_horizons),
            "min_cross_section": min_cross_section,
            "min_ic_observations": min_ic_observations,
            "streaming_factor_evaluation": True,
            "unique_assets": len(unique_assets),
        },
        "candidate_specs": [_spec_payload(spec) for spec in candidate_specs],
        "multiple_testing_policy": {
            "alpha": alpha,
            "method": "Bonferroni and Benjamini-Hochberg FDR across all Round127 factor x horizon tests",
            "counts_all_round127_candidates": True,
            "round127_candidate_count": int(expected_candidate_count),
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_prescreen": False,
            "requires_next_gate": NEXT_REQUIRED_GATE,
            "reason": "This is an Alphalens-style statistical prescreen, not a tradable portfolio validation.",
        },
        "results": sorted(results, key=lambda row: (not row["research_lead"], row["family"], -abs(row["mean_spearman_ic"]))),
        "ic_observations": ic_rows,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_public_reference_multi_family_prescreen_markdown(result)
    return result


def write_public_reference_multi_family_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "public_reference_multi_family_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_reference_multi_family_prescreen.md").write_text(
        render_public_reference_multi_family_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "public_reference_multi_family_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "public_reference_multi_family_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_public_reference_multi_family_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    lines = [
        "# Public Reference Multi-Family Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Portfolio backtest allowed candidates: {summary.get('portfolio_backtest_allowed_candidates', 0)}",
        f"- Final holdout included: {result.get('holdout_policy', {}).get('final_holdout_included', False)}",
        f"- Next direction: {summary.get('next_direction', ROUND129_NEXT_DIRECTION)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Top Results",
        "",
        "| Factor | Family | Horizon | IC | ICIR | t-stat | IC>0 | Q5-Q1 | Mono | Turnover | FDR | Lead |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", [])[:30]:
        lines.append(
            "| {factor_name} | {family} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {fdr} | {lead} |".format(
                factor_name=row["factor_name"],
                family=row.get("family", ""),
                horizon=row["horizon"],
                ic=row["mean_spearman_ic"],
                icir=row["icir"],
                t=row["ic_t_stat"],
                pos=row["ic_positive_rate"],
                spread=row["quantile_spread"],
                mono=row["quantile_monotonicity"],
                turnover=row["avg_top_quantile_turnover"],
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
            "- All 20 Round127 candidates are counted in factor x horizon multiple-testing accounting.",
            "- Round129 must review Rounds 126-128 before any portfolio grid, de-dup bridge, or new family lock-in.",
            "- Final holdout data remains blocked for tuning.",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_bars_file(file: Path) -> pd.DataFrame:
    columns = ["date", "asset_id", "symbol", "market", "open", "high", "low", "close", "adj_close", "volume", "amount", "vwap"]
    if file.suffix == ".parquet":
        try:
            return pd.read_parquet(file, columns=columns)
        except Exception:
            frame = pd.read_parquet(file)
    else:
        frame = pd.read_csv(file)
    return frame[[column for column in columns if column in frame.columns]]


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "high", "low", "adj_close", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["market"] = frame["market"].fillna("CN").astype(str)
    frame["asset_id"] = frame["asset_id"].astype(str)
    if "open" not in frame:
        frame["open"] = frame["adj_close"]
    if "close" not in frame:
        frame["close"] = frame["adj_close"]
    if "volume" not in frame:
        frame["volume"] = 0.0
    if "vwap" not in frame:
        frame["vwap"] = frame["amount"] / _nonzero(pd.to_numeric(frame["volume"], errors="coerce"))
    for column in ["open", "high", "low", "close", "adj_close", "volume", "amount", "vwap"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=required)
    return frame[
        (frame["market"] == "CN")
        & (frame["adj_close"] > 0)
        & (frame["high"] > 0)
        & (frame["low"] > 0)
        & (frame["amount"] > 0)
    ].reset_index(drop=True)


def _feature_frame(
    bars: pd.DataFrame,
    *,
    factor_inputs: pd.DataFrame,
    moneyflow_inputs: pd.DataFrame,
) -> pd.DataFrame:
    bars = _normalise_bars(bars)
    pieces: list[pd.DataFrame] = []
    market_return = _market_return_by_date(bars)
    market_return.name = "market_return_1d"
    for _, group in bars.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        close = group["adj_close"]
        open_ = group["open"]
        high = group["high"]
        low = group["low"]
        amount = group["amount"]
        returns = close.pct_change()
        amount_returns = amount.pct_change()
        adv20 = amount.rolling(20, min_periods=5).mean()
        rolling_high20 = high.rolling(20, min_periods=5).max()
        rolling_low20 = low.rolling(20, min_periods=5).min()
        range_width = _nonzero(rolling_high20 - rolling_low20)
        ma20 = close.rolling(20, min_periods=10).mean()
        std20 = _nonzero(close.rolling(20, min_periods=10).std(ddof=0))
        ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
        ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
        macd_hist = ema12 - ema26 - (ema12 - ema26).ewm(span=9, adjust=False, min_periods=9).mean()
        atr10 = _average_true_range(high, low, close, 10)
        rsrs_slope = high.rolling(18, min_periods=10).cov(low) / _nonzero(low.rolling(18, min_periods=10).var())
        rsrs_residual = high - rsrs_slope * low
        frame = group[["date", "asset_id", "market", "adj_close", "amount"]].copy()
        frame["return_1d"] = returns
        frame["return_5"] = close.pct_change(5)
        frame["return_20"] = close.pct_change(20)
        frame["return_60"] = close.pct_change(60)
        frame["reversal_5"] = -frame["return_5"]
        frame["skip5_momentum_20"] = close.shift(5).pct_change(20)
        frame["skip5_momentum_60"] = close.shift(5).pct_change(60)
        frame["amount_trend_20_60"] = amount.rolling(20, min_periods=5).mean() / amount.rolling(60, min_periods=20).mean() - 1.0
        frame["amount_z_20"] = (amount - amount.rolling(20, min_periods=5).mean()) / _nonzero(
            amount.rolling(20, min_periods=5).std(ddof=0)
        )
        frame["pv_corr_20"] = returns.rolling(20, min_periods=10).corr(amount_returns)
        frame["price_amount_level_corr_20"] = close.rolling(20, min_periods=10).corr(amount)
        frame["adv20_amount"] = adv20
        frame["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        frame["hl_range_20"] = ((high / low) - 1.0).rolling(20, min_periods=5).mean()
        frame["donchian_position_20"] = (close - rolling_low20) / range_width
        frame["price_breakout_20"] = close / _nonzero(rolling_high20) - 1.0
        frame["return_efficiency_20"] = frame["return_20"] / _nonzero(returns.abs().rolling(20, min_periods=5).sum())
        frame["bollinger_reversal_20"] = -((close - ma20) / std20)
        frame["bollinger_bandwidth_20"] = (4.0 * std20) / _nonzero(ma20)
        frame["rsi_reversal_14"] = 100.0 - _rsi(close, 14)
        frame["macd_hist_z_26"] = (macd_hist - macd_hist.rolling(26, min_periods=10).mean()) / _nonzero(
            macd_hist.rolling(26, min_periods=10).std(ddof=0)
        )
        intraday_range = _nonzero(high - low)
        frame["intraday_close_position"] = (close - open_) / intraday_range
        frame["kbar_close_position_20"] = ((close - low) / intraday_range).rolling(20, min_periods=5).mean()
        frame["open_close_pressure_10"] = ((close - open_) / _nonzero(open_)).rolling(10, min_periods=5).mean()
        frame["atr_ratio_10"] = atr10 / _nonzero(close)
        frame["supertrend_distance_reversal_10_3"] = -(
            (close - close.rolling(10, min_periods=5).mean()) / _nonzero(3.0 * atr10)
        )
        frame["supertrend_state_10_3"] = (close > close.rolling(10, min_periods=5).mean()).astype(float) * 2.0 - 1.0
        frame["rsrs_slope_18"] = rsrs_slope
        frame["rsrs_slope_delta_60"] = rsrs_slope - rsrs_slope.rolling(60, min_periods=20).mean()
        frame["rsrs_residual_z_18"] = (
            rsrs_residual - rsrs_residual.rolling(18, min_periods=10).mean()
        ) / _nonzero(rsrs_residual.rolling(18, min_periods=10).std(ddof=0))
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True).sort_values(["asset_id", "date"])
    features = features.merge(market_return.reset_index(), on="date", how="left", validate="many_to_one")
    features = _merge_factor_inputs(features, factor_inputs)
    features = _merge_moneyflow_inputs(features, moneyflow_inputs)
    features = _add_market_residual_features(features)
    features["log_adv20"] = features["adv20_amount"].where(features["adv20_amount"] > 0).apply(math.log)
    return _replace_infinite_numeric(features)


def _merge_factor_inputs(features: pd.DataFrame, factor_inputs: pd.DataFrame) -> pd.DataFrame:
    aux = _normalise_auxiliary_frame(factor_inputs)
    columns = ["date", "asset_id", "market", "pe_ttm", "pb", "dv_ttm", "turnover_rate_f", "circ_mv"]
    for column in columns:
        if column not in aux:
            aux[column] = pd.NA
    merged = features.merge(aux[columns], on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    merged["value_proxy"] = -_positive_numeric(merged["pe_ttm"]).rank(pct=True) - _positive_numeric(merged["pb"]).rank(pct=True)
    merged["quality_proxy"] = (
        _positive_numeric(merged["dv_ttm"]).fillna(0.0)
        - _positive_numeric(merged["turnover_rate_f"]).fillna(merged["turnover_rate_f"].median())
        - _positive_numeric(merged["pb"]).fillna(merged["pb"].median())
    )
    return merged


def _market_return_by_date(bars: pd.DataFrame) -> pd.Series:
    frame = bars[["date", "asset_id", "adj_close"]].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame = frame.dropna(subset=["date", "asset_id", "adj_close"]).sort_values(["asset_id", "date"])
    frame["asset_return_1d"] = frame.groupby("asset_id", sort=False)["adj_close"].pct_change()
    return frame.groupby("date")["asset_return_1d"].mean()


def _merge_moneyflow_inputs(features: pd.DataFrame, moneyflow_inputs: pd.DataFrame) -> pd.DataFrame:
    aux = _normalise_auxiliary_frame(moneyflow_inputs)
    columns = [
        "date",
        "asset_id",
        "market",
        "buy_lg_amount",
        "sell_lg_amount",
        "buy_elg_amount",
        "sell_elg_amount",
        "net_mf_amount",
    ]
    for column in columns:
        if column not in aux:
            aux[column] = 0.0
    merged = features.merge(aux[columns], on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    for column in ["buy_lg_amount", "sell_lg_amount", "buy_elg_amount", "sell_elg_amount", "net_mf_amount"]:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0.0)
    main_force = (
        merged["buy_lg_amount"]
        + merged["buy_elg_amount"]
        - merged["sell_lg_amount"]
        - merged["sell_elg_amount"]
    )
    amount_scale = _nonzero(merged["amount"])
    merged["smart_money_net_ratio"] = merged["net_mf_amount"] / amount_scale
    merged["main_force_net_ratio"] = main_force / amount_scale
    merged["smart_money_net_ratio_20"] = merged.groupby("asset_id")["smart_money_net_ratio"].transform(
        lambda item: item.rolling(20, min_periods=5).mean()
    )
    merged["smart_money_persistent_net_ratio_20"] = merged.groupby("asset_id")["smart_money_net_ratio"].transform(
        lambda item: item.rolling(20, min_periods=10).sum()
    )
    merged["main_force_flow_divergence_20"] = merged.groupby("asset_id")["main_force_net_ratio"].transform(
        lambda item: item.rolling(20, min_periods=5).mean()
    ) - merged["return_20"]
    return merged


def _add_market_residual_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features[["asset_id", "date", "return_1d", "market_return_1d"]].sort_values(["asset_id", "date"]).copy()
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        market = group["market_return_1d"]
        returns = group["return_1d"]
        beta = returns.rolling(60, min_periods=20).cov(market) / _nonzero(
            market.rolling(60, min_periods=20).var()
        )
        residual = returns - beta * market
        pieces.append(
            pd.DataFrame(
                {
                    "residual_return_5": residual.rolling(5, min_periods=3).sum(),
                    "residual_momentum_60": residual.rolling(60, min_periods=20).sum(),
                    "residual_vol_20": residual.rolling(20, min_periods=5).std(ddof=0),
                },
                index=group.index,
            )
        )
    if not pieces:
        features["residual_return_5"] = pd.NA
        features["residual_momentum_60"] = pd.NA
        features["residual_vol_20"] = pd.NA
        return features
    residual_features = pd.concat(pieces).sort_index()
    features["residual_return_5"] = residual_features["residual_return_5"]
    features["residual_momentum_60"] = residual_features["residual_momentum_60"]
    features["residual_vol_20"] = residual_features["residual_vol_20"]
    return features


def _add_forward_return_columns(
    features: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    execution_lag: int,
) -> pd.DataFrame:
    frame = features[["asset_id", "date", "adj_close"]].sort_values(["asset_id", "date"]).copy()
    forward_columns = {f"forward_return_{int(horizon)}": pd.Series(index=features.index, dtype=float) for horizon in horizons}
    for _, group in frame.groupby("asset_id", sort=False):
        for horizon in horizons:
            entry = group["adj_close"].shift(-execution_lag)
            exit_ = group["adj_close"].shift(-(execution_lag + int(horizon)))
            forward_columns[f"forward_return_{int(horizon)}"].loc[group.index] = exit_ / entry - 1.0
    for column, values in forward_columns.items():
        features[column] = values
    return features


def _streaming_data_window(
    bars: pd.DataFrame,
    features: pd.DataFrame,
    *,
    horizons: tuple[int, ...],
    min_signal_date_amount: float,
) -> dict[str, Any]:
    signal_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    label_mask = pd.Series(False, index=features.index)
    for horizon in horizons:
        column = f"forward_return_{int(horizon)}"
        if column in features:
            label_mask = label_mask | features[column].notna()
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "min_signal_date": _min_date(features.loc[signal_mask], "date"),
        "max_signal_date": _max_date(features.loc[signal_mask], "date"),
        "min_label_date": _min_date(features.loc[label_mask], "date"),
        "max_label_date": _max_date(features.loc[label_mask], "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if not bars.empty else 0,
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _normalise_auxiliary_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market"])
    aux = frame.copy()
    aux["date"] = pd.to_datetime(aux["date"])
    aux["asset_id"] = aux["asset_id"].astype(str)
    aux["market"] = aux["market"].fillna("CN").astype(str) if "market" in aux else "CN"
    return aux.drop_duplicates(["date", "asset_id", "market"], keep="last")


def _candidate_value_series(features: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        "alpha101_rank_pv_reversal_liquid_20": (
            -0.55 * features["z_pv_corr_20"] + 0.30 * features["z_reversal_5"] + 0.15 * features["z_log_adv20"]
        ),
        "alpha101_decay_reversal_amount_stability_10": (
            0.60 * features["z_decay_reversal_10"] + 0.25 * features["z_neg_abs_amount_z_20"] + 0.15 * features["z_log_adv20"]
        ),
        "alpha101_intraday_range_position_fade_20": (
            -0.50 * features["z_intraday_close_position"] + 0.30 * features["z_neg_realized_vol_20"] + 0.20 * features["z_log_adv20"]
        ),
        "qlib_alpha158_kbar_momentum_lowvol_20": (
            0.40 * features["z_kbar_close_position_20"] + 0.35 * features["z_skip5_momentum_20"] + 0.25 * features["z_neg_realized_vol_20"]
        ),
        "qlib_alpha158_price_efficiency_liquid_20": (
            0.50 * features["z_return_efficiency_20"] + 0.25 * features["z_return_20"] + 0.25 * features["z_log_adv20"]
        ),
        "qlib_alpha158_volume_price_resonance_20_60": (
            0.45 * features["z_return_20"] + 0.35 * features["z_amount_trend_20_60"] + 0.20 * features["z_return_efficiency_20"]
        ),
        "supertrend_pullback_lowvol_liquid_10_3": (
            0.45 * features["z_supertrend_distance_reversal_10_3"] + 0.30 * features["z_neg_atr_ratio_10"] + 0.25 * features["z_log_adv20"]
        ),
        "supertrend_consensus_breakout_efficiency_10_20": (
            0.35 * features["z_supertrend_state_10_3"] + 0.35 * features["z_price_breakout_20"] + 0.30 * features["z_return_efficiency_20"]
        ),
        "donchian_breakout_efficiency_liquid_20": (
            0.45 * features["z_donchian_position_20"] + 0.30 * features["z_return_efficiency_20"] + 0.25 * features["z_log_adv20"]
        ),
        "rsrs_residual_reversal_liquid_18": (
            -0.55 * features["z_rsrs_residual_z_18"] + 0.25 * features["z_neg_realized_vol_20"] + 0.20 * features["z_log_adv20"]
        ),
        "rsrs_slope_acceleration_quality_18_60": (
            0.45 * features["z_rsrs_slope_18"] + 0.30 * features["z_rsrs_slope_delta_60"] + 0.25 * features["z_return_efficiency_20"]
        ),
        "smart_money_efficiency_reversal_20": (
            0.45 * features["z_smart_money_net_ratio_20"] + 0.30 * features["z_reversal_5"] + 0.25 * features["z_log_adv20"]
        ),
        "smart_money_accumulation_quality_20": (
            0.50 * features["z_smart_money_persistent_net_ratio_20"] + 0.30 * features["z_return_efficiency_20"] + 0.20 * features["z_log_adv20"]
        ),
        "main_force_divergence_reversal_5_20": (
            0.45 * features["z_main_force_flow_divergence_20"] + 0.35 * features["z_reversal_5"] + 0.20 * features["z_log_adv20"]
        ),
        "qvm_quality_value_momentum_blend_20_60": (
            0.35 * features["z_quality_proxy"] + 0.30 * features["z_value_proxy"] + 0.25 * features["z_skip5_momentum_60"] + 0.10 * features["z_log_adv20"]
        ),
        "qvm_lowvol_value_momentum_liquid_20_60": (
            0.30 * features["z_value_proxy"] + 0.30 * features["z_skip5_momentum_60"] + 0.25 * features["z_neg_realized_vol_20"] + 0.15 * features["z_log_adv20"]
        ),
        "bollinger_bandwidth_reversal_liquid_20": (
            0.45 * features["z_bollinger_reversal_20"] + 0.30 * features["z_neg_bollinger_bandwidth_20"] + 0.25 * features["z_log_adv20"]
        ),
        "rsi_macd_exhaustion_reversal_14_26": (
            0.40 * features["z_rsi_reversal_14"] - 0.35 * features["z_macd_hist_z_26"] + 0.25 * features["z_log_adv20"]
        ),
        "beta_neutral_momentum_residual_quality_60": (
            0.45 * features["z_residual_momentum_60"] + 0.30 * features["z_return_efficiency_20"] + 0.25 * features["z_neg_residual_vol_20"]
        ),
        "residual_range_contraction_reversal_20": (
            -0.45 * features["z_residual_return_5"] + 0.30 * features["z_neg_hl_range_20"] + 0.25 * features["z_log_adv20"]
        ),
    }


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features
    frame["decay_reversal_10"] = frame.groupby("asset_id")["reversal_5"].transform(_decay_linear_10)
    z_inputs = {
        "z_pv_corr_20": frame["pv_corr_20"],
        "z_reversal_5": frame["reversal_5"],
        "z_log_adv20": frame["log_adv20"] if "log_adv20" in frame else _safe_log(frame["adv20_amount"]),
        "z_decay_reversal_10": frame["decay_reversal_10"],
        "z_neg_abs_amount_z_20": -frame["amount_z_20"].abs(),
        "z_intraday_close_position": frame["intraday_close_position"],
        "z_neg_realized_vol_20": -frame["realized_vol_20"],
        "z_kbar_close_position_20": frame["kbar_close_position_20"],
        "z_skip5_momentum_20": frame["skip5_momentum_20"],
        "z_return_efficiency_20": frame["return_efficiency_20"],
        "z_return_20": frame["return_20"],
        "z_amount_trend_20_60": frame["amount_trend_20_60"],
        "z_supertrend_distance_reversal_10_3": frame["supertrend_distance_reversal_10_3"],
        "z_neg_atr_ratio_10": -frame["atr_ratio_10"],
        "z_supertrend_state_10_3": frame["supertrend_state_10_3"],
        "z_price_breakout_20": frame["price_breakout_20"],
        "z_donchian_position_20": frame["donchian_position_20"],
        "z_rsrs_residual_z_18": frame["rsrs_residual_z_18"],
        "z_rsrs_slope_18": frame["rsrs_slope_18"],
        "z_rsrs_slope_delta_60": frame["rsrs_slope_delta_60"],
        "z_smart_money_net_ratio_20": frame["smart_money_net_ratio_20"],
        "z_smart_money_persistent_net_ratio_20": frame["smart_money_persistent_net_ratio_20"],
        "z_main_force_flow_divergence_20": frame["main_force_flow_divergence_20"],
        "z_quality_proxy": frame["quality_proxy"],
        "z_value_proxy": frame["value_proxy"],
        "z_skip5_momentum_60": frame["skip5_momentum_60"],
        "z_bollinger_reversal_20": frame["bollinger_reversal_20"],
        "z_neg_bollinger_bandwidth_20": -frame["bollinger_bandwidth_20"],
        "z_rsi_reversal_14": frame["rsi_reversal_14"],
        "z_macd_hist_z_26": frame["macd_hist_z_26"],
        "z_residual_momentum_60": frame["residual_momentum_60"],
        "z_neg_residual_vol_20": -frame["residual_vol_20"],
        "z_residual_return_5": frame["residual_return_5"],
        "z_neg_hl_range_20": -frame["hl_range_20"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


def _decay_linear_10(series: pd.Series) -> pd.Series:
    weights = pd.Series(range(1, 11), dtype=float)

    def apply(values: pd.Series) -> float:
        local_weights = weights.tail(len(values)).to_numpy()
        return float((values.to_numpy() * local_weights).sum() / local_weights.sum())

    return series.rolling(10, min_periods=5).apply(apply, raw=False)


def _average_true_range(high: pd.Series, low: pd.Series, close: pd.Series, window: int) -> pd.Series:
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return true_range.rolling(window, min_periods=max(5, window // 2)).mean()


def _rsi(close: pd.Series, window: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window, min_periods=max(5, window // 2)).mean()
    loss = (-delta.clip(upper=0)).rolling(window, min_periods=max(5, window // 2)).mean()
    rs = gain / _nonzero(loss)
    return 100.0 - 100.0 / (1.0 + rs)


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / _nonzero(std)


def _positive_numeric(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values > 0)


def _replace_infinite_numeric(frame: pd.DataFrame) -> pd.DataFrame:
    clean = frame
    for column in clean.select_dtypes(include=["number"]).columns:
        values = clean[column]
        clean[column] = values.mask(values.isin([float("inf"), float("-inf")]))
    return clean


def _nonzero(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.mask(values == 0)


def _safe_log(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    return values.where(values > 0).apply(math.log)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["date", "asset_id", "market", "amount", "adv20_amount", "family", "factor_name", "factor_value"]
    )


def _spec_payload(spec: Any) -> dict[str, Any]:
    if hasattr(spec, "__dataclass_fields__"):
        payload = asdict(spec)
        for key in ["windows", "required_fields", "public_reference_tags", "expected_failure_modes"]:
            if key in payload:
                payload[key] = list(payload[key])
        return payload
    return dict(spec)
