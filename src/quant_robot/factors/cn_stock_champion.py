from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


CN_STOCK_CHAMPION_FACTOR_NAMES = ("rankic_neg1_downside_range_blend",)


def compute_cn_stock_champion_factors(
    bars: pd.DataFrame,
    daily_basic_inputs: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    requested = _resolve_requested_factor_names(factor_names)
    _require_columns(
        bars,
        ["date", "asset_id", "market", "amount", "adj_close", "high", "low", "volume"],
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
            "dv_ttm",
            "total_mv",
            "circ_mv",
        ],
        "daily-basic inputs",
    )
    frame = _build_research_frame(bars, daily_basic_inputs)
    values_by_name = {
        "rankic_neg1_downside_range_blend": _rankic_neg1_downside_range_blend(frame),
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return CN_STOCK_CHAMPION_FACTOR_NAMES
    supported = set(CN_STOCK_CHAMPION_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported CN stock champion factor_names: {', '.join(unknown)}")
    return factor_names


def _build_research_frame(bars: pd.DataFrame, daily_basic_inputs: pd.DataFrame) -> pd.DataFrame:
    bar_cols = ["date", "asset_id", "market", "amount", "adj_close", "high", "low", "volume"]
    input_cols = [
        "date",
        "asset_id",
        "market",
        "turnover_rate",
        "turnover_rate_f",
        "volume_ratio",
        "pe_ttm",
        "pb",
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
    frame["amount"] = _numeric(frame, "amount")
    frame["amount_rank"] = _cs_rank(frame, frame["amount"])
    _add_price_volume_features(frame)
    _add_tradeable_gates(frame)
    return frame


def _add_price_volume_features(frame: pd.DataFrame) -> None:
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        close = _numeric(item, "adj_close")
        high = _numeric(item, "high")
        low = _numeric(item, "low")
        volume = _numeric(item, "volume")
        returns = close.pct_change()
        low20 = close.rolling(20).min()
        high20 = close.rolling(20).max()
        ma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std(ddof=0)
        item["momentum_20"] = close / close.shift(20) - 1.0
        item["bollinger_reversal_20"] = -((close - ma20) / std20.replace(0, np.nan))
        item["range_position_low_20"] = -((close - low20) / (high20 - low20).replace(0, np.nan))
        item["pv_corr_reversal_20"] = -returns.rolling(20).corr(volume.pct_change())
        item["low_vol_20"] = -returns.rolling(20).std(ddof=0)
        item["downside_vol_low_20"] = -returns.clip(upper=0).rolling(20).std(ddof=0)
        item["hl_range_low_20"] = -((high / low.replace(0, np.nan) - 1.0).rolling(20).mean())
        pieces.append(
            item[
                [
                    "momentum_20",
                    "bollinger_reversal_20",
                    "range_position_low_20",
                    "pv_corr_reversal_20",
                    "low_vol_20",
                    "downside_vol_low_20",
                    "hl_range_low_20",
                ]
            ]
        )
    features = pd.concat(pieces).sort_index()
    for column in features.columns:
        frame[column] = pd.to_numeric(features[column], errors="coerce").replace([np.inf, -np.inf], np.nan)

    for column in [
        "momentum_20",
        "turnover_rate",
        "volume_ratio",
    ]:
        frame[f"{column}_rank"] = _cs_rank(frame, _numeric(frame, column))


def _add_tradeable_gates(frame: pd.DataFrame) -> None:
    frame["base_tradeable"] = (
        frame["amount_rank"].between(0.30, 0.90, inclusive="both")
        & frame["momentum_20_rank"].between(0.10, 0.80, inclusive="both")
        & (frame["turnover_rate_rank"] <= 0.80)
    )
    frame["tailrankic_base_tradeable"] = frame["base_tradeable"].fillna(False)


def _rankic_neg1_downside_range_blend(frame: pd.DataFrame) -> pd.Series:
    pb_inv = _safe_inverse(frame, "pb")
    pe_inv = _safe_inverse(frame, "pe_ttm")
    turnover_band30 = _cs_rank_band(frame, "turnover_rate", 0.30)
    amount_mid60 = -(_numeric(frame, "amount_rank") - 0.60).abs()
    downside = _cs_z(frame, _numeric(frame, "downside_vol_low_20"))
    range_component = _cs_z(frame, _numeric(frame, "range_position_low_20"))
    value = _cs_z(frame, pb_inv) + _cs_z(frame, pe_inv)
    liquidity = _cs_z(frame, turnover_band30) + _cs_z(frame, amount_mid60)
    return _gate(frame, value + liquidity + downside + 0.50 * range_component, "tailrankic_base_tradeable")


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame[column], errors="coerce")


def _safe_inverse(frame: pd.DataFrame, column: str) -> pd.Series:
    values = _numeric(frame, column)
    return (1.0 / values.where(values > 0)).replace([np.inf, -np.inf], np.nan)


def _cs_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    return pd.to_numeric(values, errors="coerce").groupby([frame["date"], frame["market"]], sort=False).rank(pct=True)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric_values = pd.to_numeric(values, errors="coerce")
    grouped = numeric_values.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric_values - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


def _cs_rank_band(frame: pd.DataFrame, column: str, target: float) -> pd.Series:
    rank = _cs_rank(frame, _numeric(frame, column))
    return -(rank - target).abs()


def _gate(frame: pd.DataFrame, values: pd.Series, flag_column: str) -> pd.Series:
    out = pd.to_numeric(values, errors="coerce").copy()
    return out.where(frame[flag_column].fillna(False))


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
