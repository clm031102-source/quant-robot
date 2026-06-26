from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES = (
    "resid_value_quality_low_vol_20",
    "resid_value_low_turnover_quality_20",
    "resid_value_reversal_low_tail_20",
)

_EPSILON = 1e-12


def compute_daily_basic_residual_composite_factors(
    bars: pd.DataFrame,
    daily_basic_inputs: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    _require_columns(
        bars,
        ["date", "asset_id", "market", "amount", "adj_close", "high", "low"],
        "bars",
    )
    _require_columns(
        daily_basic_inputs,
        [
            "date",
            "asset_id",
            "market",
            "turnover_rate",
            "turnover_rate_f",
            "volume_ratio",
            "pe_ttm",
            "pb",
            "ps_ttm",
            "dv_ttm",
            "total_mv",
            "circ_mv",
        ],
        "daily-basic inputs",
    )
    requested = _resolve_requested_factor_names(factor_names)
    frame = _build_research_frame(bars, daily_basic_inputs)
    builders = {
        "resid_value_quality_low_vol_20": lambda: _value_quality_low_vol(frame),
        "resid_value_low_turnover_quality_20": lambda: _value_low_turnover_quality(frame),
        "resid_value_reversal_low_tail_20": lambda: _value_reversal_low_tail(frame),
    }
    pieces = [_factor_frame(frame, name, builders[name]()) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES
    supported = set(DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported daily-basic residual composite factor_names: {', '.join(unknown)}")
    return factor_names


def _build_research_frame(bars: pd.DataFrame, daily_basic_inputs: pd.DataFrame) -> pd.DataFrame:
    bar_cols = ["date", "asset_id", "market", "amount", "adj_close", "high", "low"]
    input_cols = [
        "date",
        "asset_id",
        "market",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "pe_ttm",
        "pb",
        "ps_ttm",
        "dv_ttm",
        "total_mv",
        "circ_mv",
    ]
    bar_frame = bars.loc[:, bar_cols].copy()
    input_frame = daily_basic_inputs.loc[:, input_cols].copy()
    bar_frame["date"] = pd.to_datetime(bar_frame["date"]).dt.date
    input_frame["date"] = pd.to_datetime(input_frame["date"]).dt.date
    frame = bar_frame.merge(input_frame, on=["date", "asset_id", "market"], how="left")
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    _add_price_liquidity_features(frame)
    _add_cross_sectional_features(frame)
    _add_tradeable_gate(frame)
    return frame


def _add_price_liquidity_features(frame: pd.DataFrame) -> None:
    frame["amount"] = _numeric(frame, "amount")
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        close = _numeric(item, "adj_close")
        high = _numeric(item, "high")
        low = _numeric(item, "low")
        amount = _numeric(item, "amount")
        returns = close.pct_change()
        low20 = close.rolling(20, min_periods=5).min()
        high20 = close.rolling(20, min_periods=5).max()
        item["return_1"] = returns
        item["momentum_20"] = close.pct_change(20)
        item["reversal_5"] = -close.pct_change(5)
        item["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        item["amount_trend_20"] = (amount.rolling(5, min_periods=3).mean() / amount.rolling(20, min_periods=5).mean().replace(0.0, np.nan)) - 1.0
        item["range_position_20"] = (close - low20) / (high20 - low20).replace(0.0, np.nan)
        item["downside_vol_20"] = returns.clip(upper=0).rolling(20, min_periods=5).std(ddof=0)
        item["hl_range_20"] = ((high / low.replace(0, np.nan)) - 1.0).rolling(20, min_periods=5).mean()
        pieces.append(
            item[
                [
                    "return_1",
                    "momentum_20",
                    "reversal_5",
                    "adv20_amount",
                    "amount_trend_20",
                    "range_position_20",
                    "downside_vol_20",
                    "hl_range_20",
                ]
            ]
        )
    features = pd.concat(pieces).sort_index()
    for column in features.columns:
        frame[column] = pd.to_numeric(features[column], errors="coerce").replace([np.inf, -np.inf], np.nan)


def _add_cross_sectional_features(frame: pd.DataFrame) -> None:
    frame["amount_rank"] = _cs_rank(frame, _numeric(frame, "amount"))
    frame["adv20_rank"] = _cs_rank(frame, _numeric(frame, "adv20_amount"))
    frame["turnover_rank"] = _cs_rank(frame, _numeric(frame, "turnover_rate"))
    frame["downside_vol_rank"] = _cs_rank(frame, _numeric(frame, "downside_vol_20"))
    frame["log_circ_mv"] = _safe_log(_numeric(frame, "circ_mv"))
    frame["log_adv20"] = _safe_log(_numeric(frame, "adv20_amount"))


def _add_tradeable_gate(frame: pd.DataFrame) -> None:
    frame["residual_composite_tradeable"] = (
        (frame["adv20_rank"] > 0.20)
        & (frame["amount_rank"] > 0.20)
        & (frame["downside_vol_rank"] <= 0.85)
        & (frame["range_position_20"] >= 0.10)
        & (frame["return_1"].abs() <= 0.35)
    )


def _value_quality_low_vol(frame: pd.DataFrame) -> pd.Series:
    score = (
        _value_score(frame)
        + 0.30 * _cs_z(frame, _numeric(frame, "dv_ttm"))
        + 0.70 * _low_tail_score(frame)
        + 0.20 * _mid_liquidity_score(frame)
    )
    return _cross_sectional_residual(
        frame,
        score,
        exposure_columns=("log_circ_mv", "log_adv20", "momentum_20"),
    )


def _value_low_turnover_quality(frame: pd.DataFrame) -> pd.Series:
    low_turnover = _cs_z(frame, -_numeric(frame, "turnover_rank")).fillna(0.0)
    anti_crowding = (
        low_turnover
        + 0.50 * _cs_z(frame, -_numeric(frame, "volume_ratio")).fillna(0.0)
        + 0.30 * _cs_z(frame, -_numeric(frame, "amount_trend_20")).fillna(0.0)
    )
    score = _value_score(frame) + 0.60 * anti_crowding + 0.40 * _low_tail_score(frame)
    return _cross_sectional_residual(
        frame,
        score,
        exposure_columns=("log_circ_mv", "log_adv20", "momentum_20"),
    )


def _value_reversal_low_tail(frame: pd.DataFrame) -> pd.Series:
    reversal = (
        0.70 * _cs_z(frame, _numeric(frame, "reversal_5")).fillna(0.0)
        + 0.30 * _cs_z(frame, -_numeric(frame, "momentum_20")).fillna(0.0)
    )
    score = 0.80 * _value_score(frame) + 0.60 * reversal + 0.50 * _low_tail_score(frame)
    return _cross_sectional_residual(
        frame,
        score,
        exposure_columns=("log_circ_mv", "log_adv20", "turnover_rank"),
    )


def _value_score(frame: pd.DataFrame) -> pd.Series:
    return (
        _cs_z(frame, _safe_inverse(frame, "pb")).fillna(0.0)
        + _cs_z(frame, _safe_inverse(frame, "pe_ttm")).fillna(0.0)
        + 0.50 * _cs_z(frame, _safe_inverse(frame, "ps_ttm")).fillna(0.0)
    )


def _low_tail_score(frame: pd.DataFrame) -> pd.Series:
    return (
        _cs_z(frame, -_numeric(frame, "downside_vol_20")).fillna(0.0)
        + 0.50 * _cs_z(frame, -_numeric(frame, "hl_range_20")).fillna(0.0)
        + 0.25 * _cs_z(frame, _numeric(frame, "range_position_20")).fillna(0.0)
    )


def _mid_liquidity_score(frame: pd.DataFrame) -> pd.Series:
    mid_liquidity = -(_numeric(frame, "adv20_rank") - 0.65).abs()
    return _cs_z(frame, mid_liquidity).fillna(0.0)


def _cross_sectional_residual(
    frame: pd.DataFrame,
    score: pd.Series,
    *,
    exposure_columns: tuple[str, ...],
) -> pd.Series:
    work = pd.DataFrame(
        {
            "score": pd.to_numeric(score, errors="coerce"),
            "date": frame["date"],
            "market": frame["market"],
            "tradeable": frame["residual_composite_tradeable"].fillna(False),
        },
        index=frame.index,
    )
    for column in exposure_columns:
        work[column] = pd.to_numeric(frame[column], errors="coerce")

    result = pd.Series(np.nan, index=frame.index, dtype=float)
    required = ["score", *exposure_columns]
    valid = work[work["tradeable"]].dropna(subset=required)
    for _, group in valid.groupby(["date", "market"], sort=False):
        y = _standardized_array(group["score"].to_numpy(dtype=float))
        if y is None:
            continue
        exposure_arrays = []
        for column in exposure_columns:
            exposure = _standardized_array(group[column].to_numpy(dtype=float))
            if exposure is not None:
                exposure_arrays.append(exposure)
        if len(group) <= len(exposure_arrays) + 2:
            continue
        if exposure_arrays:
            x = np.column_stack([np.ones(len(group)), *exposure_arrays])
            coefficients = np.linalg.lstsq(x, y, rcond=None)[0]
            residual = y - x @ coefficients
        else:
            residual = y
        if np.nanstd(residual) <= _EPSILON:
            continue
        result.loc[group.index] = residual
    return result.replace([np.inf, -np.inf], np.nan)


def _standardized_array(values: np.ndarray) -> np.ndarray | None:
    clean = values.astype(float)
    mean = float(np.nanmean(clean))
    std = float(np.nanstd(clean))
    if not np.isfinite(mean) or not np.isfinite(std) or std <= _EPSILON:
        return None
    return (clean - mean) / std


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def _safe_inverse(frame: pd.DataFrame, column: str) -> pd.Series:
    values = _numeric(frame, column)
    return (1.0 / values.where(values > 0)).replace([np.inf, -np.inf], np.nan)


def _safe_log(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return np.log(numeric.where(numeric > 0)).replace([np.inf, -np.inf], np.nan)


def _cs_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").groupby([frame["date"], frame["market"]], sort=False).rank(pct=True)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric_values = pd.to_numeric(values, errors="coerce")
    grouped = numeric_values.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric_values - mean) / std.where(std > _EPSILON)).replace([np.inf, -np.inf], np.nan)


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": frame["date"].to_numpy(),
            "asset_id": frame["asset_id"].to_numpy(),
            "market": frame["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": 20,
        }
    )


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing columns: {', '.join(missing)}")
