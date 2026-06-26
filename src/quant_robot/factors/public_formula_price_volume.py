from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


PUBLIC_FORMULA_PRICE_VOLUME_FACTOR_NAMES = (
    "formula_pv_corr_reversal_20",
    "formula_volume_contraction_reversal_20",
    "formula_range_contraction_breakout_20",
    "formula_range_contraction_breakout_liquid_20",
    "formula_range_contraction_breakout_lowvol_20",
    "formula_range_contraction_breakout_liquid_lowvol_20",
    "formula_pv_corr_momentum_confirmed_20_60",
    "formula_volume_contraction_momentum_confirmed_20_60",
)


def compute_public_formula_price_volume_factors(
    bars: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close", "high", "low", "amount"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(f"Bars are missing columns for public formula price-volume factor calculation: {', '.join(missing)}")
    requested = _resolve_requested_factor_names(factor_names)
    frame = _feature_frame(bars)
    values_by_name = {
        "formula_pv_corr_reversal_20": _pv_corr_reversal_score(frame),
        "formula_volume_contraction_reversal_20": _volume_contraction_reversal_score(frame),
        "formula_range_contraction_breakout_20": _range_contraction_breakout_score(frame),
        "formula_range_contraction_breakout_liquid_20": _range_contraction_breakout_liquid_score(frame),
        "formula_range_contraction_breakout_lowvol_20": _range_contraction_breakout_lowvol_score(frame),
        "formula_range_contraction_breakout_liquid_lowvol_20": _range_contraction_breakout_liquid_lowvol_score(frame),
        "formula_pv_corr_momentum_confirmed_20_60": _pv_corr_momentum_confirmed_score(frame),
        "formula_volume_contraction_momentum_confirmed_20_60": _volume_contraction_momentum_confirmed_score(frame),
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return PUBLIC_FORMULA_PRICE_VOLUME_FACTOR_NAMES
    supported = set(PUBLIC_FORMULA_PRICE_VOLUME_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported public formula price-volume factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame.sort_values(["asset_id", "date"]).reset_index(drop=True)
    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        price = pd.to_numeric(item["adj_close"], errors="coerce")
        high = pd.to_numeric(item["high"], errors="coerce")
        low = pd.to_numeric(item["low"], errors="coerce")
        amount = pd.to_numeric(item["amount"], errors="coerce")
        returns = price.pct_change()
        amount_change = amount.pct_change()
        rolling_high_20 = high.rolling(20, min_periods=5).max()
        rolling_low_20 = low.rolling(20, min_periods=5).min()
        item["return_1d"] = returns
        item["momentum_20"] = price.pct_change(20)
        item["momentum_60"] = price.pct_change(60)
        item["reversal_5"] = -price.pct_change(5)
        item["amount_trend_20"] = (amount.rolling(5, min_periods=3).mean() / amount.rolling(20, min_periods=5).mean().replace(0.0, np.nan)) - 1.0
        item["pv_corr_20"] = returns.rolling(20, min_periods=10).corr(amount_change)
        item["pv_divergence_20"] = -item["momentum_20"] * item["amount_trend_20"]
        item["adv20_amount"] = amount.rolling(20, min_periods=5).mean()
        item["downside_vol_20"] = returns.clip(upper=0.0).rolling(20, min_periods=5).std(ddof=0)
        item["hl_range_20"] = ((high / low.replace(0.0, np.nan)) - 1.0).rolling(20, min_periods=5).mean()
        item["range_position_20"] = (price - rolling_low_20) / (rolling_high_20 - rolling_low_20).replace(0.0, np.nan)
        pieces.append(item)
    out = pd.concat(pieces, ignore_index=True)
    out["adv20_rank"] = _cs_rank(out, out["adv20_amount"])
    out["downside_vol_rank"] = _cs_rank(out, out["downside_vol_20"])
    out["hl_range_rank"] = _cs_rank(out, out["hl_range_20"])
    hl_range = pd.to_numeric(out["hl_range_20"], errors="coerce")
    out["formula_price_volume_tradeable"] = (
        (out["adv20_rank"] >= 0.30)
        & (out["downside_vol_rank"] <= 0.90)
        & ((out["hl_range_rank"] <= 0.85) | (hl_range <= 0.08))
        & (pd.to_numeric(out["return_1d"], errors="coerce").abs() <= 0.50)
    )
    return out


def _pv_corr_reversal_score(frame: pd.DataFrame) -> pd.Series:
    value = _pv_corr_reversal_raw_score(frame)
    return value.where(frame["formula_price_volume_tradeable"].fillna(False))


def _volume_contraction_reversal_score(frame: pd.DataFrame) -> pd.Series:
    value = _volume_contraction_reversal_raw_score(frame)
    return value.where(frame["formula_price_volume_tradeable"].fillna(False))


def _range_contraction_breakout_score(frame: pd.DataFrame) -> pd.Series:
    value = _range_contraction_breakout_raw_score(frame)
    return value.where(frame["formula_price_volume_tradeable"].fillna(False))


def _range_contraction_breakout_liquid_score(frame: pd.DataFrame) -> pd.Series:
    value = _range_contraction_breakout_raw_score(frame) + 0.10 * _liquidity_score(frame)
    return value.where(frame["formula_price_volume_tradeable"].fillna(False))


def _range_contraction_breakout_lowvol_score(frame: pd.DataFrame) -> pd.Series:
    value = _range_contraction_breakout_raw_score(frame) + 0.10 * _low_tail_score(frame)
    return value.where(frame["formula_price_volume_tradeable"].fillna(False))


def _range_contraction_breakout_liquid_lowvol_score(frame: pd.DataFrame) -> pd.Series:
    value = (
        _range_contraction_breakout_raw_score(frame)
        + 0.07 * _liquidity_score(frame)
        + 0.07 * _low_tail_score(frame)
    )
    return value.where(frame["formula_price_volume_tradeable"].fillna(False))


def _range_contraction_breakout_raw_score(frame: pd.DataFrame) -> pd.Series:
    return (
        0.45 * _cs_z(frame, pd.to_numeric(frame["range_position_20"], errors="coerce")).fillna(0.0)
        + 0.35 * _cs_z(frame, -pd.to_numeric(frame["hl_range_20"], errors="coerce")).fillna(0.0)
        + 0.20 * _cs_z(frame, -pd.to_numeric(frame["downside_vol_20"], errors="coerce")).fillna(0.0)
    )


def _pv_corr_momentum_confirmed_score(frame: pd.DataFrame) -> pd.Series:
    value = (
        0.50 * _pv_corr_reversal_raw_score(frame)
        + 0.35 * _cs_z(frame, pd.to_numeric(frame["momentum_60"], errors="coerce")).fillna(0.0)
        + 0.15 * _cs_z(frame, pd.to_numeric(frame["range_position_20"], errors="coerce")).fillna(0.0)
    )
    mask = _momentum_confirmation_mask(frame)
    return value.where(mask)


def _volume_contraction_momentum_confirmed_score(frame: pd.DataFrame) -> pd.Series:
    value = (
        0.45 * _volume_contraction_reversal_raw_score(frame)
        + 0.40 * _cs_z(frame, pd.to_numeric(frame["momentum_60"], errors="coerce")).fillna(0.0)
        + 0.15 * _cs_z(frame, pd.to_numeric(frame["range_position_20"], errors="coerce")).fillna(0.0)
    )
    mask = _momentum_confirmation_mask(frame)
    return value.where(mask)


def _pv_corr_reversal_raw_score(frame: pd.DataFrame) -> pd.Series:
    return (
        0.70 * _cs_z(frame, frame["pv_divergence_20"]).fillna(0.0)
        + 0.30 * _cs_z(frame, -pd.to_numeric(frame["pv_corr_20"], errors="coerce")).fillna(0.0)
        + 0.15 * _low_tail_score(frame)
    )


def _volume_contraction_reversal_raw_score(frame: pd.DataFrame) -> pd.Series:
    return (
        0.45 * _cs_z(frame, -pd.to_numeric(frame["momentum_20"], errors="coerce")).fillna(0.0)
        + 0.35 * _cs_z(frame, -pd.to_numeric(frame["amount_trend_20"], errors="coerce")).fillna(0.0)
        + 0.20 * _low_tail_score(frame)
    )


def _momentum_confirmation_mask(frame: pd.DataFrame) -> pd.Series:
    momentum_60 = pd.to_numeric(frame["momentum_60"], errors="coerce")
    range_position = pd.to_numeric(frame["range_position_20"], errors="coerce")
    return (
        frame["formula_price_volume_tradeable"].fillna(False)
        & (momentum_60 > 0.0)
        & (range_position >= 0.45)
    )


def _low_tail_score(frame: pd.DataFrame) -> pd.Series:
    return (
        _cs_z(frame, -pd.to_numeric(frame["downside_vol_20"], errors="coerce")).fillna(0.0)
        + 0.50 * _cs_z(frame, -pd.to_numeric(frame["hl_range_20"], errors="coerce")).fillna(0.0)
    )


def _liquidity_score(frame: pd.DataFrame) -> pd.Series:
    adv20 = pd.to_numeric(frame["adv20_amount"], errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        log_adv20 = np.log(adv20.where(adv20 > 0.0))
    return _cs_z(frame, log_adv20).fillna(0.0)


def _cs_rank(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.groupby([frame["date"], frame["market"]], sort=False).rank(pct=True)


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


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
