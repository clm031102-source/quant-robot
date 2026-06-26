from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    DEFAULT_ANALYSIS_END_DATE,
    DEFAULT_ANALYSIS_START_DATE,
    DEFAULT_HORIZONS,
    RESULT_COLUMNS,
    _data_window,
    _sanitize,
    _write_csv,
    summarize_capacity_safe_price_volume_prescreen,
)
from quant_robot.ops.public_alpha101_capacity_safe_preregistration import (
    ROUND113_SOURCE_AUDIT,
    SAFETY,
    default_public_alpha101_candidate_specs,
)
from quant_robot.research.labels import make_forward_returns


STAGE = "public_alpha101_capacity_safe_prescreen"
ROUND115_NEXT_DEDUP_DIRECTION = "round116_public_alpha101_reference_exposure_dedup"
ROUND115_NEXT_ROTATE_DIRECTION = "round116_family_rotation_after_public_alpha101_prescreen_failure"
NEXT_REQUIRED_GATE = "alpha101_reference_redundancy_dedup_before_portfolio_grid"


def build_public_alpha101_capacity_safe_prescreen(
    *,
    bars_roots: Iterable[str | Path],
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
    specs = list(candidate_specs or default_public_alpha101_candidate_specs())
    bars = load_public_alpha101_bars(
        bars_roots,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
    )
    factor_frame = compute_public_alpha101_capacity_safe_factors(
        bars,
        candidate_specs=specs,
        min_signal_date_amount=min_signal_date_amount,
    )
    labels = make_forward_returns(
        bars[["date", "asset_id", "market", "adj_close"]],
        horizons=horizons,
        execution_lag=execution_lag,
    )
    labels = labels[labels["date"] <= pd.Timestamp(analysis_end_date)].reset_index(drop=True)
    result = summarize_capacity_safe_price_volume_prescreen(
        factor_frame,
        labels,
        expected_candidate_count=len(specs),
        candidate_specs=specs,
        horizons=horizons,
        min_cross_section=min_cross_section,
        min_ic_observations=min_ic_observations,
    )
    lead_count = int(result["summary"].get("research_lead_count", 0))
    result["stage"] = STAGE
    result["summary"]["next_direction"] = ROUND115_NEXT_DEDUP_DIRECTION if lead_count else ROUND115_NEXT_ROTATE_DIRECTION
    result["summary"]["promotion_allowed_candidates"] = 0
    result["candidate_specs"] = [_spec_payload(spec) for spec in specs]
    result["data_window"] = _data_window(bars, factor_frame, labels)
    result["holdout_policy"] = {
        "final_holdout_included": include_final_holdout,
        "analysis_start_date": analysis_start_date,
        "analysis_end_date": analysis_end_date,
        "final_holdout_start": "2026-01-01",
        "final_holdout_use": "read_once_after_oos_clearance_only",
    }
    result["public_formula_context"] = {
        "source_audit": ROUND113_SOURCE_AUDIT,
        "source_preregistration": "docs/research/cn_stock_public_alpha101_capacity_safe_preregistration_round114_2026-06-22.md",
        "translation_layer": "fixed_public_alpha101_qlib_daily_ohlcv_amount_vwap_features",
        "no_random_formula_search": True,
        "no_parameter_expansion": True,
        "portfolio_grid_blocked": True,
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
        "next_allowed_action": (
            "alpha101_reference_exposure_dedup_if_research_leads_survive"
            if lead_count
            else "family_rotation_or_round114_116_review_after_zero_public_alpha101_leads"
        ),
        "reason": "Round115 is an IC/quantile/turnover/capacity prescreen, not a tradable portfolio validation.",
    }
    result["live_boundary_allowed"] = False
    result["safety"] = SAFETY
    result["markdown"] = render_public_alpha101_capacity_safe_prescreen_markdown(result)
    return result


def load_public_alpha101_bars(
    bars_roots: Iterable[str | Path],
    *,
    analysis_start_date: str = DEFAULT_ANALYSIS_START_DATE,
    analysis_end_date: str = DEFAULT_ANALYSIS_END_DATE,
    include_final_holdout: bool = False,
) -> pd.DataFrame:
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
    frames = [_read_public_alpha101_bars_file(file) for file in files if "market=CN" in str(file) or not files]
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        raise FileNotFoundError(f"No CN bar files found under: {', '.join(str(root) for root in bars_roots)}")
    bars = pd.concat(frames, ignore_index=True)
    bars = _normalise_public_alpha101_bars(bars)
    start = pd.Timestamp(analysis_start_date)
    end = pd.Timestamp(analysis_end_date)
    if include_final_holdout:
        end = max(end, bars["date"].max())
    bars = bars[(bars["date"] >= start) & (bars["date"] <= end)]
    return (
        bars.drop_duplicates(["asset_id", "market", "date"], keep="last")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def compute_public_alpha101_capacity_safe_factors(
    bars: pd.DataFrame,
    *,
    candidate_specs: Sequence[Any] | None = None,
    min_signal_date_amount: float = 10_000_000,
) -> pd.DataFrame:
    specs = list(candidate_specs or default_public_alpha101_candidate_specs())
    features = _feature_frame(bars)
    if features.empty:
        return _empty_factor_frame()
    features = _add_cross_sectional_features(features)
    features = _add_decay_features(features)
    candidate_values = {
        "alpha101_intraday_close_position_reversal": (
            1.00 * features["z_neg_intraday_close_position"] + 0.20 * features["z_log_adv20"]
        ),
        "alpha101_gap_fade_amount_confirmed_5_20": (
            0.60 * features["z_gap_fade"]
            + 0.25 * features["z_neg_amount_z_20"]
            + 0.15 * features["z_log_adv20"]
        ),
        "alpha101_price_volume_corr_reversal_20": (
            0.70 * features["z_neg_price_amount_return_corr_20"] + 0.30 * features["z_log_adv20"]
        ),
        "alpha101_vwap_proxy_reversion_liquid_20": (
            0.65 * features["z_vwap_reversion_20"] + 0.35 * features["z_log_adv20"]
        ),
        "alpha101_decay_rank_reversal_10": (
            0.75 * features["z_decay_rank_reversal_10"] + 0.25 * features["z_log_adv20"]
        ),
        "alpha101_amount_shock_exhaustion_5_20": (
            0.55 * features["z_reversal_5"]
            + 0.30 * features["z_neg_amount_z_20"]
            + 0.15 * features["z_log_adv20"]
        ),
        "alpha101_open_close_pressure_fade_10": (
            0.70 * features["z_neg_open_close_pressure_10"] + 0.30 * features["z_log_adv20"]
        ),
        "alpha101_range_compression_liquid_20": (
            0.55 * features["z_neg_range_20"]
            + 0.15 * features["z_neg_realized_vol_20"]
            + 0.30 * features["z_log_adv20"]
        ),
        "qlib_alpha158_return_std_position_blend_20": (
            0.45 * features["z_reversal_5"]
            + 0.25 * features["z_neg_realized_vol_20"]
            + 0.20 * features["z_kbar_close_position_20"]
            + 0.10 * features["z_log_adv20"]
        ),
        "alpha101_volume_rank_divergence_20": (
            0.60 * features["z_neg_price_amount_level_corr_20"]
            + 0.25 * features["z_reversal_5"]
            + 0.15 * features["z_log_adv20"]
        ),
    }
    allowed_names = {spec.factor_name for spec in specs}
    base_columns = ["date", "asset_id", "market", "amount", "adv20_amount"]
    capacity_mask = (
        (features["amount"] >= min_signal_date_amount)
        & (features["adv20_amount"] >= min_signal_date_amount)
        & (features["return_1d"].abs() <= 0.50)
    )
    rows: list[pd.DataFrame] = []
    for factor_name, values in candidate_values.items():
        if factor_name not in allowed_names:
            continue
        frame = features.loc[capacity_mask, base_columns].copy()
        frame["factor_name"] = factor_name
        frame["factor_value"] = values.loc[capacity_mask]
        frame = frame.dropna(subset=["factor_value", "amount", "adv20_amount"])
        rows.append(frame)
    if not rows:
        return _empty_factor_frame()
    return pd.concat(rows, ignore_index=True).sort_values(["factor_name", "date", "asset_id"]).reset_index(drop=True)


def write_public_alpha101_capacity_safe_prescreen(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(result)
    (output_path / "public_alpha101_capacity_safe_prescreen.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "public_alpha101_capacity_safe_prescreen.md").write_text(
        render_public_alpha101_capacity_safe_prescreen_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "public_alpha101_capacity_safe_prescreen_results.csv", result.get("results", []), RESULT_COLUMNS)
    _write_csv(
        output_path / "public_alpha101_capacity_safe_prescreen_ic_observations.csv",
        result.get("ic_observations", []),
        ["factor_name", "horizon", "date", "spearman_ic", "cross_section"],
    )


def render_public_alpha101_capacity_safe_prescreen_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    context = result.get("public_formula_context", {})
    lines = [
        "# Public Alpha101 Capacity-Safe Prescreen",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Label rows: {summary.get('label_rows', 0)}",
        f"- Aligned rows: {summary.get('aligned_rows', 0)}",
        f"- Tests: {summary.get('test_count', 0)}",
        f"- Research leads: {summary.get('research_lead_count', 0)}",
        f"- FDR-significant tests: {summary.get('multiple_testing_lead_count', 0)}",
        f"- Promotion allowed candidates: {summary.get('promotion_allowed_candidates', 0)}",
        f"- Next direction: {summary.get('next_direction', '')}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        "",
        "## Public Formula Context",
        "",
        f"- Source audit: {context.get('source_audit', ROUND113_SOURCE_AUDIT)}",
        f"- Source preregistration: {context.get('source_preregistration', '')}",
        f"- Translation layer: {context.get('translation_layer', '')}",
        f"- Random formula search: {not context.get('no_random_formula_search', True)}",
        f"- Parameter expansion: {not context.get('no_parameter_expansion', True)}",
        f"- Portfolio grid blocked: {context.get('portfolio_grid_blocked', True)}",
        "",
        "## Results",
        "",
        "| Factor | Horizon | IC | ICIR | t | IC+ | Q5-Q1 | Mono | Turnover | FDR | Lead |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|",
    ]
    for row in result.get("results", []):
        lines.append(
            "| {factor_name} | {horizon} | {ic:.4f} | {icir:.3f} | {t:.2f} | {pos:.1%} | {spread:.4f} | {mono:.3f} | {turnover:.1%} | {fdr} | {lead} |".format(
                factor_name=row["factor_name"],
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
            "## Promotion Policy",
            "",
            f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
            f"- Requires next gate: {result.get('promotion_policy', {}).get('requires_next_gate', NEXT_REQUIRED_GATE)}",
            f"- Reason: {result.get('promotion_policy', {}).get('reason', '')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _read_public_alpha101_bars_file(file: Path) -> pd.DataFrame:
    columns = [
        "date",
        "asset_id",
        "symbol",
        "market",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "amount",
        "vwap",
    ]
    if file.suffix == ".parquet":
        try:
            return pd.read_parquet(file, columns=columns)
        except Exception:
            frame = pd.read_parquet(file)
            return frame[[column for column in columns if column in frame.columns]]
    frame = pd.read_csv(file)
    return frame[[column for column in columns if column in frame.columns]]


def _normalise_public_alpha101_bars(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    if "asset_id" not in frame.columns and "symbol" in frame.columns:
        frame["asset_id"] = frame["symbol"].astype(str)
    if "market" not in frame.columns:
        frame["market"] = "CN"
    required = ["date", "asset_id", "market", "open", "high", "low", "adj_close", "volume", "amount"]
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Bars are missing required columns: {', '.join(missing)}")
    frame["date"] = pd.to_datetime(frame["date"])
    frame["market"] = frame["market"].fillna("CN").astype(str)
    frame["asset_id"] = frame["asset_id"].astype(str)
    for column in ["open", "high", "low", "close", "adj_close", "volume", "amount", "vwap"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "vwap" not in frame.columns:
        frame["vwap"] = np.nan
    frame["vwap"] = frame["vwap"].where(frame["vwap"] > 0, frame["amount"] / frame["volume"].replace(0, np.nan))
    frame = frame.dropna(subset=required + ["vwap"])
    frame = frame[
        (frame["market"] == "CN")
        & (frame["open"] > 0)
        & (frame["high"] > 0)
        & (frame["low"] > 0)
        & (frame["adj_close"] > 0)
        & (frame["volume"] > 0)
        & (frame["amount"] > 0)
        & (frame["vwap"] > 0)
    ]
    return frame


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    bars = _normalise_public_alpha101_bars(bars).sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces: list[pd.DataFrame] = []
    for _, group in bars.groupby("asset_id", sort=False):
        group = group.copy().reset_index(drop=True)
        close = group["adj_close"]
        open_ = group["open"]
        high = group["high"]
        low = group["low"]
        amount = group["amount"]
        volume = group["volume"]
        vwap = group["vwap"]
        returns = close.pct_change()
        amount_returns = amount.pct_change()
        range_width = (high - low).replace(0, np.nan)
        rolling_high20 = high.rolling(20, min_periods=5).max()
        rolling_low20 = low.rolling(20, min_periods=5).min()
        rolling_range20 = (rolling_high20 - rolling_low20).replace(0, np.nan)
        adv20 = amount.rolling(20, min_periods=5).mean()
        amount_mean20 = amount.rolling(20, min_periods=5).mean()
        amount_std20 = amount.rolling(20, min_periods=5).std(ddof=0).replace(0, np.nan)
        vwap_proxy20 = (amount.rolling(20, min_periods=5).sum() / volume.rolling(20, min_periods=5).sum()).replace(
            0, np.nan
        )
        frame = group[["date", "asset_id", "market", "amount"]].copy()
        frame["return_1d"] = returns
        frame["reversal_5"] = -close.pct_change(5)
        frame["intraday_close_position"] = (close - open_) / (range_width + 1e-6)
        frame["gap_fade"] = -(open_ / close.shift(1) - 1.0)
        frame["amount_z_20"] = (amount - amount_mean20) / amount_std20
        frame["price_amount_return_corr_20"] = returns.rolling(20, min_periods=10).corr(amount_returns)
        frame["vwap_reversion_20"] = -(close / vwap_proxy20 - 1.0)
        frame["open_close_pressure_10"] = ((close - open_) / (open_ + 1e-6)).rolling(10, min_periods=5).mean()
        frame["range_20"] = ((high - low) / (close + 1e-6)).rolling(20, min_periods=5).mean()
        frame["realized_vol_20"] = returns.rolling(20, min_periods=5).std(ddof=0)
        frame["kbar_close_position_20"] = (close - rolling_low20) / rolling_range20
        frame["price_amount_level_corr_20"] = close.rolling(20, min_periods=10).corr(amount)
        frame["adv20_amount"] = adv20
        frame["vwap"] = vwap
        pieces.append(frame)
    if not pieces:
        return pd.DataFrame()
    features = pd.concat(pieces, ignore_index=True).replace([np.inf, -np.inf], np.nan)
    features["log_adv20"] = np.log(features["adv20_amount"].where(features["adv20_amount"] > 0))
    features["cs_rank_neg_return_5"] = features.groupby("date")["reversal_5"].rank(pct=True)
    return features


def _add_cross_sectional_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.copy()
    z_inputs = {
        "z_neg_intraday_close_position": -frame["intraday_close_position"],
        "z_gap_fade": frame["gap_fade"],
        "z_neg_amount_z_20": -frame["amount_z_20"],
        "z_neg_price_amount_return_corr_20": -frame["price_amount_return_corr_20"],
        "z_vwap_reversion_20": frame["vwap_reversion_20"],
        "z_reversal_5": frame["reversal_5"],
        "z_neg_open_close_pressure_10": -frame["open_close_pressure_10"],
        "z_neg_range_20": -frame["range_20"],
        "z_neg_realized_vol_20": -frame["realized_vol_20"],
        "z_kbar_close_position_20": frame["kbar_close_position_20"],
        "z_neg_price_amount_level_corr_20": -frame["price_amount_level_corr_20"],
        "z_log_adv20": frame["log_adv20"],
    }
    for column, series in z_inputs.items():
        frame[column] = _cs_zscore(frame, series)
    return frame


def _add_decay_features(features: pd.DataFrame) -> pd.DataFrame:
    frame = features.sort_values(["asset_id", "date"]).copy()
    weights = np.arange(1, 11, dtype=float)

    def decay(values: np.ndarray) -> float:
        usable = weights[-len(values) :]
        return float(np.dot(values, usable) / usable.sum())

    frame["decay_rank_reversal_10"] = (
        frame.groupby("asset_id", sort=False)["cs_rank_neg_return_5"]
        .rolling(10, min_periods=5)
        .apply(decay, raw=True)
        .reset_index(level=0, drop=True)
    )
    frame["z_decay_rank_reversal_10"] = _cs_zscore(frame, frame["decay_rank_reversal_10"])
    return frame.sort_index()


def _cs_zscore(frame: pd.DataFrame, series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    grouped = values.groupby(frame["date"])
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return (values - mean) / std.replace(0, np.nan)


def _empty_factor_frame() -> pd.DataFrame:
    return pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "amount", "adv20_amount"])


def _spec_payload(spec: Any) -> dict[str, Any]:
    payload = asdict(spec) if hasattr(spec, "__dataclass_fields__") else dict(spec)
    for key in ("windows", "required_fields", "public_reference_tags"):
        if key in payload:
            payload[key] = list(payload[key])
    return payload
