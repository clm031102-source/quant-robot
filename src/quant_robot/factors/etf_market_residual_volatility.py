from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.factors.public_formula_price_volume import (
    compute_public_formula_price_volume_factors,
)
from quant_robot.factors.public_technical import compute_public_technical_factors
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES = (
    "etf_idio_vol_low_60",
    "etf_downside_beta_low_120",
    "etf_positive_residual_skew_60",
)

ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES = (
    "low_volatility_20",
    "low_volatility_60",
    "low_downside_volatility_60",
    "drawdown_resilience_60",
    "crash_recovery_60",
    "recovery_quality_60",
    "formula_range_contraction_breakout_20",
    "formula_range_contraction_breakout_lowvol_20",
    "bollinger_reversal_20",
)

_DIRECT_REFERENCE_NAMES = ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES[:6]
_FORMULA_REFERENCE_NAMES = ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES[6:8]
_PUBLIC_TECHNICAL_REFERENCE_NAMES = ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES[8:]


def compute_point_in_time_etf_market_proxy(
    bars: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame,
    min_cross_section: int = 30,
) -> pd.DataFrame:
    if min_cross_section < 1:
        raise ValueError("min_cross_section must be positive")
    frame = _normalise_bars(bars)
    keys = _normalise_eligible_keys(eligible_keys)
    eligible_assets = set(keys["asset_id"])
    frame = frame[frame["asset_id"].isin(eligible_assets)].copy()
    frame["asset_return"] = frame.groupby("asset_id", sort=False)["adj_close"].pct_change(
        fill_method=None
    )
    eligible = keys.merge(
        frame[["date", "asset_id", "market", "asset_return"]],
        on=["date", "asset_id", "market"],
        how="left",
        validate="one_to_one",
    )
    proxy = (
        eligible.groupby(["date", "market"], as_index=False)
        .agg(
            market_return=("asset_return", "median"),
            eligible_asset_count=("asset_return", "count"),
        )
        .sort_values(["market", "date"])
        .reset_index(drop=True)
    )
    proxy.loc[proxy["eligible_asset_count"].lt(min_cross_section), "market_return"] = np.nan
    return proxy


def compute_etf_market_residual_volatility_factors(
    bars: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame,
    market_proxy_min_cross_section: int = 30,
    beta_window: int = 120,
    beta_min_observations: int = 80,
    downside_beta_window: int = 120,
    downside_beta_min_observations: int = 24,
    residual_window: int = 60,
    residual_min_observations: int = 40,
    residual_model_lag: int = 1,
) -> pd.DataFrame:
    _validate_windows(
        beta_window=beta_window,
        beta_min_observations=beta_min_observations,
        downside_beta_window=downside_beta_window,
        downside_beta_min_observations=downside_beta_min_observations,
        residual_window=residual_window,
        residual_min_observations=residual_min_observations,
        residual_model_lag=residual_model_lag,
    )
    frame = _normalise_bars(bars)
    keys = _normalise_eligible_keys(eligible_keys)
    eligible_assets = set(keys["asset_id"])
    frame = frame[frame["asset_id"].isin(eligible_assets)].copy()
    proxy = compute_point_in_time_etf_market_proxy(
        frame,
        eligible_keys=keys,
        min_cross_section=market_proxy_min_cross_section,
    )
    frame = frame.merge(
        proxy[["date", "market", "market_return"]],
        on=["date", "market"],
        how="left",
        validate="many_to_one",
    ).sort_values(["asset_id", "date"])

    pieces: list[pd.DataFrame] = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        returns = item["adj_close"].pct_change(fill_method=None)
        market_returns = pd.to_numeric(item["market_return"], errors="coerce")
        beta = _rolling_beta(
            returns,
            market_returns,
            window=beta_window,
            min_periods=beta_min_observations,
        )
        alpha = (
            returns.rolling(beta_window, min_periods=beta_min_observations).mean()
            - beta
            * market_returns.rolling(beta_window, min_periods=beta_min_observations).mean()
        )
        residual = (
            returns
            - alpha.shift(residual_model_lag)
            - beta.shift(residual_model_lag) * market_returns
        )
        downside_returns = returns.where(market_returns < 0.0)
        downside_market = market_returns.where(market_returns < 0.0)
        downside_beta = _rolling_beta(
            downside_returns,
            downside_market,
            window=downside_beta_window,
            min_periods=downside_beta_min_observations,
        )
        residual_volatility = residual.rolling(
            residual_window,
            min_periods=residual_min_observations,
        ).std(ddof=0)
        residual_skew = residual.rolling(
            residual_window,
            min_periods=residual_min_observations,
        ).skew()
        pieces.extend(
            [
                _factor_frame(
                    item,
                    "etf_idio_vol_low_60",
                    -residual_volatility,
                    beta_window + residual_window,
                ),
                _factor_frame(
                    item,
                    "etf_downside_beta_low_120",
                    -downside_beta,
                    downside_beta_window,
                ),
                _factor_frame(
                    item,
                    "etf_positive_residual_skew_60",
                    residual_skew,
                    beta_window + residual_window,
                ),
            ]
        )
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    factors = pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS]
    return _materialise_requested_keys(
        factors,
        keys,
        expected_names=ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES,
    )


def compute_etf_market_residual_volatility_references(
    bars: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame,
) -> pd.DataFrame:
    frame = _normalise_bars(bars, require_ohlc_amount=True)
    keys = _normalise_eligible_keys(eligible_keys)
    eligible_assets = set(keys["asset_id"])
    frame = frame[frame["asset_id"].isin(eligible_assets)].copy()
    references = pd.concat(
        [
            compute_basic_factors(
                frame,
                windows=(20, 60),
                factor_names=_DIRECT_REFERENCE_NAMES,
            ),
            compute_public_formula_price_volume_factors(
                frame,
                factor_names=_FORMULA_REFERENCE_NAMES,
            ),
            compute_public_technical_factors(
                frame,
                factor_names=_PUBLIC_TECHNICAL_REFERENCE_NAMES,
            ),
        ],
        ignore_index=True,
    )[FACTOR_COLUMNS]
    return _materialise_requested_keys(
        references,
        keys,
        expected_names=ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES,
    )


def _rolling_beta(
    left: pd.Series,
    right: pd.Series,
    *,
    window: int,
    min_periods: int,
) -> pd.Series:
    covariance = left.rolling(window, min_periods=min_periods).cov(right)
    variance = right.rolling(window, min_periods=min_periods).var()
    return covariance / variance.where(variance.abs() > 1e-12)


def _factor_frame(
    frame: pd.DataFrame,
    factor_name: str,
    values: pd.Series,
    lookback_window: int,
) -> pd.DataFrame:
    output = frame[["date", "asset_id", "market"]].copy()
    output["factor_name"] = factor_name
    output["factor_value"] = pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)
    output["lookback_window"] = int(lookback_window)
    return output[FACTOR_COLUMNS]


def _materialise_requested_keys(
    factors: pd.DataFrame,
    eligible_keys: pd.DataFrame,
    *,
    expected_names: tuple[str, ...],
) -> pd.DataFrame:
    names = pd.DataFrame({"factor_name": list(expected_names)})
    requested = eligible_keys.assign(_join_key=1).merge(
        names.assign(_join_key=1),
        on="_join_key",
        how="inner",
    ).drop(columns="_join_key")
    values = factors.copy()
    values["date"] = pd.to_datetime(values["date"])
    output = requested.merge(
        values,
        on=["date", "asset_id", "market", "factor_name"],
        how="left",
        validate="one_to_one",
    )
    if output["lookback_window"].isna().any():
        lookbacks = {
            "etf_idio_vol_low_60": 180,
            "etf_downside_beta_low_120": 120,
            "etf_positive_residual_skew_60": 180,
            "low_volatility_20": 20,
            "low_volatility_60": 60,
            "low_downside_volatility_60": 60,
            "drawdown_resilience_60": 60,
            "crash_recovery_60": 60,
            "recovery_quality_60": 60,
            "formula_range_contraction_breakout_20": 20,
            "formula_range_contraction_breakout_lowvol_20": 20,
            "bollinger_reversal_20": 20,
        }
        output["lookback_window"] = output["lookback_window"].fillna(
            output["factor_name"].map(lookbacks)
        )
    output["lookback_window"] = output["lookback_window"].astype(int)
    output["date"] = output["date"].dt.date
    return output[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _normalise_bars(
    bars: pd.DataFrame,
    *,
    require_ohlc_amount: bool = False,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market", "adj_close"]
    if require_ohlc_amount:
        required.extend(["high", "low", "volume", "amount"])
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError("Bars are missing columns: " + ", ".join(missing))
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    if frame.duplicated(["date", "asset_id", "market"]).any():
        raise ValueError("Bars contain duplicate asset-date rows")
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _normalise_eligible_keys(eligible_keys: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "asset_id", "market"]
    missing = [column for column in required if column not in eligible_keys.columns]
    if missing:
        raise ValueError("Eligible keys are missing columns: " + ", ".join(missing))
    keys = eligible_keys[required].copy()
    keys["date"] = pd.to_datetime(keys["date"])
    keys["asset_id"] = keys["asset_id"].astype(str)
    keys["market"] = keys["market"].astype(str)
    if keys.duplicated(required).any():
        raise ValueError("Eligible keys contain duplicate asset-date rows")
    return keys.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _validate_windows(
    *,
    beta_window: int,
    beta_min_observations: int,
    downside_beta_window: int,
    downside_beta_min_observations: int,
    residual_window: int,
    residual_min_observations: int,
    residual_model_lag: int,
) -> None:
    pairs = (
        ("beta", beta_window, beta_min_observations),
        ("downside_beta", downside_beta_window, downside_beta_min_observations),
        ("residual", residual_window, residual_min_observations),
    )
    for label, window, observations in pairs:
        if window < 1 or observations < 1 or observations > window:
            raise ValueError(f"Invalid {label} window/minimum observations")
    if residual_model_lag != 1:
        raise ValueError("residual_model_lag must remain frozen at 1")
