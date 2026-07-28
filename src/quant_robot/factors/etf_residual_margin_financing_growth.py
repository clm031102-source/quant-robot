from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_robot.factors.etf_residual_share_creation_crowding import (
    _build_bar_features,
    _normalise_bars,
    _normalise_eligible_keys,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


FACTOR_NAME = "etf_residual_margin_financing_growth_reversal_20"
DIRECT_EXPOSURE_NAMES = (
    "margin_financing_growth_20",
    "return_20",
    "return_60",
    "realized_volatility_20",
    "log_adv20",
)


@dataclass(frozen=True)
class ResidualMarginFinancingGrowthResult:
    factors: pd.DataFrame
    diagnostics: pd.DataFrame
    direct_exposures: pd.DataFrame
    adv20: pd.DataFrame


def compute_etf_residual_margin_financing_growth(
    bars: pd.DataFrame,
    margin_positioning: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame,
    margin_lookback: int = 20,
    short_return_window: int = 20,
    long_return_window: int = 60,
    volatility_window: int = 20,
    adv_window: int = 20,
    min_cross_section: int = 30,
    winsor_lower: float = 0.01,
    winsor_upper: float = 0.99,
    scale_epsilon: float = 1e-12,
    invalid_signal_dates: set[pd.Timestamp] | None = None,
) -> ResidualMarginFinancingGrowthResult:
    _validate_parameters(
        margin_lookback=margin_lookback,
        short_return_window=short_return_window,
        long_return_window=long_return_window,
        volatility_window=volatility_window,
        adv_window=adv_window,
        min_cross_section=min_cross_section,
        winsor_lower=winsor_lower,
        winsor_upper=winsor_upper,
        scale_epsilon=scale_epsilon,
    )
    bar_frame = _normalise_bars(bars)
    keys = _normalise_eligible_keys(eligible_keys, bar_frame)
    features = _build_bar_features(
        bar_frame,
        short_return_window=short_return_window,
        long_return_window=long_return_window,
        volatility_window=volatility_window,
        adv_window=adv_window,
    )
    margin_features = _build_margin_features(
        margin_positioning,
        sessions=bar_frame[["date", "market", "session_index"]].drop_duplicates(),
        margin_lookback=margin_lookback,
    )
    diagnostics = features.merge(
        margin_features,
        on=["date", "asset_id", "market"],
        how="inner",
        validate="one_to_one",
    )
    diagnostics = keys.merge(
        diagnostics,
        on=["date", "asset_id", "market"],
        how="inner",
        validate="one_to_one",
    ).sort_values(["asset_id", "date"]).reset_index(drop=True)
    diagnostics["factor_value"] = np.nan
    diagnostics["margin_growth_residual"] = np.nan
    invalid = {
        pd.Timestamp(value).normalize()
        for value in (invalid_signal_dates or set())
    }
    for (date, _), indices in diagnostics.groupby(["date", "market"], sort=True).groups.items():
        if pd.Timestamp(date).normalize() in invalid:
            continue
        positions = list(indices)
        daily = diagnostics.loc[positions].copy()
        residuals = _daily_residuals(
            daily,
            min_cross_section=min_cross_section,
            winsor_lower=winsor_lower,
            winsor_upper=winsor_upper,
            scale_epsilon=scale_epsilon,
        )
        if residuals is None:
            continue
        diagnostics.loc[residuals.index, "margin_growth_residual"] = residuals
        diagnostics.loc[residuals.index, "factor_value"] = -residuals

    factors = _materialise_factor(diagnostics, lookback_window=long_return_window)
    direct_exposures = _materialise_direct_exposures(
        diagnostics,
        margin_lookback=margin_lookback,
        short_return_window=short_return_window,
        long_return_window=long_return_window,
        volatility_window=volatility_window,
        adv_window=adv_window,
    )
    adv20 = diagnostics[["date", "asset_id", "market", "adv20"]].copy()
    adv20["date"] = adv20["date"].dt.date
    return ResidualMarginFinancingGrowthResult(
        factors=factors,
        diagnostics=diagnostics,
        direct_exposures=direct_exposures,
        adv20=adv20.sort_values(["asset_id", "date"]).reset_index(drop=True),
    )


def _build_margin_features(
    source: pd.DataFrame,
    *,
    sessions: pd.DataFrame,
    margin_lookback: int,
) -> pd.DataFrame:
    required = {
        "date",
        "available_date",
        "asset_id",
        "market",
        "symbol",
        "rzye",
    }
    missing = sorted(required - set(source.columns))
    if missing:
        raise ValueError("margin positioning is missing columns: " + ", ".join(missing))
    frame = source[list(required)].copy()
    frame["source_date"] = pd.to_datetime(frame.pop("date"), errors="raise").dt.normalize()
    frame["available_date"] = pd.to_datetime(
        frame["available_date"],
        errors="raise",
    ).dt.normalize()
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    frame["symbol"] = frame["symbol"].astype(str).str.upper()
    frame["rzye"] = pd.to_numeric(frame["rzye"], errors="coerce")
    if frame.duplicated(["source_date", "asset_id", "market"]).any():
        raise ValueError("margin positioning contains duplicate asset-source-date rows")
    if frame.duplicated(["available_date", "asset_id", "market"]).any():
        raise ValueError("margin positioning contains duplicate asset-available-date rows")
    if frame["available_date"].le(frame["source_date"]).any():
        raise ValueError("margin positioning available_date must be later than source date")

    session_map = sessions.rename(columns={"date": "source_date"})
    frame = frame.merge(
        session_map,
        on=["source_date", "market"],
        how="left",
        validate="many_to_one",
    )
    frame["lag_session_index"] = frame["session_index"] - margin_lookback
    lag_calendar = sessions.rename(
        columns={"date": "margin_lag_date", "session_index": "lag_session_index"}
    )
    frame = frame.merge(
        lag_calendar,
        on=["market", "lag_session_index"],
        how="left",
        validate="many_to_one",
    )
    lagged = frame[["source_date", "asset_id", "market", "rzye"]].rename(
        columns={"source_date": "margin_lag_date", "rzye": "lagged_rzye"}
    )
    frame = frame.merge(
        lagged,
        on=["margin_lag_date", "asset_id", "market"],
        how="left",
        validate="many_to_one",
    )
    current = frame["rzye"].where(frame["rzye"] > 0.0)
    lag = frame["lagged_rzye"].where(frame["lagged_rzye"] > 0.0)
    frame["raw_margin_growth_20"] = np.log(current / lag)
    frame["exchange_sse"] = frame["symbol"].str.endswith(".SH").astype(float)
    frame["date"] = frame["available_date"]
    return frame[
        [
            "date",
            "asset_id",
            "market",
            "source_date",
            "available_date",
            "raw_margin_growth_20",
            "exchange_sse",
        ]
    ]


def _daily_residuals(
    daily: pd.DataFrame,
    *,
    min_cross_section: int,
    winsor_lower: float,
    winsor_upper: float,
    scale_epsilon: float,
) -> pd.Series | None:
    columns = [
        "raw_margin_growth_20",
        "return_20",
        "return_60",
        "realized_volatility_20",
        "log_adv20",
    ]
    numeric = daily[columns].apply(pd.to_numeric, errors="coerce").replace(
        [np.inf, -np.inf],
        np.nan,
    )
    valid = numeric.notna().all(axis=1) & daily["exchange_sse"].notna()
    if int(valid.sum()) < min_cross_section:
        return None
    usable = numeric.loc[valid]
    standardized = pd.DataFrame(index=usable.index)
    for column in columns:
        values = usable[column]
        clipped = values.clip(
            lower=float(values.quantile(winsor_lower)),
            upper=float(values.quantile(winsor_upper)),
        )
        scale = float(clipped.std(ddof=0))
        if not np.isfinite(scale) or scale <= scale_epsilon:
            return None
        standardized[column] = (clipped - float(clipped.mean())) / scale
    controls = standardized[
        ["return_20", "return_60", "realized_volatility_20", "log_adv20"]
    ].to_numpy(dtype=float)
    x = np.column_stack([np.ones(len(standardized)), controls])
    exchange = daily.loc[standardized.index, "exchange_sse"].to_numpy(dtype=float)
    if np.unique(exchange).size > 1:
        x = np.column_stack([x, exchange])
    y = standardized["raw_margin_growth_20"].to_numpy(dtype=float)
    coefficients, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    if int(rank) != int(x.shape[1]):
        return None
    return pd.Series(y - x @ coefficients, index=standardized.index, dtype=float)


def _materialise_factor(
    diagnostics: pd.DataFrame,
    *,
    lookback_window: int,
) -> pd.DataFrame:
    output = diagnostics[["date", "asset_id", "market", "factor_value"]].copy()
    output["factor_name"] = FACTOR_NAME
    output["lookback_window"] = int(lookback_window)
    output["date"] = output["date"].dt.date
    return output[FACTOR_COLUMNS].sort_values(["asset_id", "date"]).reset_index(drop=True)


def _materialise_direct_exposures(
    diagnostics: pd.DataFrame,
    *,
    margin_lookback: int,
    short_return_window: int,
    long_return_window: int,
    volatility_window: int,
    adv_window: int,
) -> pd.DataFrame:
    specs = (
        ("margin_financing_growth_20", "raw_margin_growth_20", margin_lookback),
        ("return_20", "return_20", short_return_window),
        ("return_60", "return_60", long_return_window),
        ("realized_volatility_20", "realized_volatility_20", volatility_window),
        ("log_adv20", "log_adv20", adv_window),
    )
    pieces = []
    for name, column, lookback in specs:
        item = diagnostics[["date", "asset_id", "market", column]].rename(
            columns={column: "factor_value"}
        )
        item["factor_name"] = name
        item["lookback_window"] = int(lookback)
        item["date"] = item["date"].dt.date
        pieces.append(item[FACTOR_COLUMNS])
    return pd.concat(pieces, ignore_index=True).sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _validate_parameters(**values: float | int) -> None:
    for key in (
        "margin_lookback",
        "short_return_window",
        "long_return_window",
        "volatility_window",
        "adv_window",
    ):
        if int(values[key]) < 1:
            raise ValueError(f"{key} must be positive")
    if int(values["long_return_window"]) <= int(values["short_return_window"]):
        raise ValueError("long_return_window must exceed short_return_window")
    if int(values["min_cross_section"]) < 8:
        raise ValueError("min_cross_section must be at least 8")
    if not 0 <= float(values["winsor_lower"]) < float(values["winsor_upper"]) <= 1:
        raise ValueError("winsor limits must satisfy 0 <= lower < upper <= 1")
    if float(values["scale_epsilon"]) <= 0:
        raise ValueError("scale_epsilon must be positive")
