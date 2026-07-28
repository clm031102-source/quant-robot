from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


FACTOR_NAME = "etf_residual_share_creation_crowding_reversal_20"
DIRECT_EXPOSURE_NAMES = (
    "share_creation_20",
    "return_20",
    "return_60",
    "realized_volatility_20",
    "log_adv20",
    "log_total_size",
)


@dataclass(frozen=True)
class ResidualShareCreationCrowdingResult:
    factors: pd.DataFrame
    diagnostics: pd.DataFrame
    direct_exposures: pd.DataFrame
    adv20: pd.DataFrame


def compute_etf_residual_share_creation_crowding(
    bars: pd.DataFrame,
    fund_structure: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame,
    share_lookback: int = 20,
    short_return_window: int = 20,
    long_return_window: int = 60,
    volatility_window: int = 20,
    adv_window: int = 20,
    min_cross_section: int = 30,
    winsor_lower: float = 0.01,
    winsor_upper: float = 0.99,
    scale_epsilon: float = 1e-12,
) -> ResidualShareCreationCrowdingResult:
    """Build the frozen residual share-creation crowding-reversal candidate."""

    _validate_parameters(
        share_lookback=share_lookback,
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
    share_features = _build_share_features(
        fund_structure,
        sessions=bar_frame[["date", "market", "session_index"]].drop_duplicates(),
        share_lookback=share_lookback,
    )
    diagnostics = features.merge(
        share_features,
        on=["date", "asset_id", "market"],
        how="left",
        validate="one_to_one",
    )
    diagnostics = keys.merge(
        diagnostics,
        on=["date", "asset_id", "market"],
        how="left",
        validate="one_to_one",
    ).sort_values(["asset_id", "date"]).reset_index(drop=True)
    diagnostics["factor_value"] = np.nan
    diagnostics["share_creation_residual"] = np.nan
    for _, indices in diagnostics.groupby(["date", "market"], sort=True).groups.items():
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
        diagnostics.loc[residuals.index, "share_creation_residual"] = residuals
        diagnostics.loc[residuals.index, "factor_value"] = -residuals

    factors = _materialise_factor(diagnostics, lookback_window=long_return_window)
    direct_exposures = _materialise_direct_exposures(
        diagnostics,
        share_lookback=share_lookback,
        short_return_window=short_return_window,
        long_return_window=long_return_window,
        volatility_window=volatility_window,
        adv_window=adv_window,
    )
    adv20 = diagnostics[["date", "asset_id", "market", "adv20"]].copy()
    adv20["date"] = adv20["date"].dt.date
    return ResidualShareCreationCrowdingResult(
        factors=factors,
        diagnostics=diagnostics,
        direct_exposures=direct_exposures,
        adv20=adv20.sort_values(["asset_id", "date"]).reset_index(drop=True),
    )


def _normalise_bars(bars: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "asset_id", "market", "adj_close", "amount"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(f"CN ETF bars are missing columns: {', '.join(missing)}")
    frame = bars[list(required)].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    if frame.duplicated(["date", "asset_id", "market"]).any():
        raise ValueError("CN ETF bars contain duplicate asset-date rows")
    sessions = (
        frame[["date", "market"]]
        .drop_duplicates()
        .sort_values(["market", "date"])
        .reset_index(drop=True)
    )
    sessions["session_index"] = sessions.groupby("market", sort=False).cumcount()
    return (
        frame.merge(sessions, on=["date", "market"], how="left", validate="many_to_one")
        .sort_values(["asset_id", "date"])
        .reset_index(drop=True)
    )


def _normalise_eligible_keys(
    eligible_keys: pd.DataFrame,
    bars: pd.DataFrame,
) -> pd.DataFrame:
    required = {"date", "asset_id", "market"}
    missing = sorted(required - set(eligible_keys.columns))
    if missing:
        raise ValueError(f"eligible keys are missing columns: {', '.join(missing)}")
    keys = eligible_keys[list(required)].copy()
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.normalize()
    keys["asset_id"] = keys["asset_id"].astype(str)
    keys["market"] = keys["market"].astype(str).str.upper()
    if keys.duplicated(["date", "asset_id", "market"]).any():
        raise ValueError("eligible keys contain duplicate asset-date rows")
    bar_keys = bars[["date", "asset_id", "market"]]
    merged = keys.merge(
        bar_keys,
        on=["date", "asset_id", "market"],
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    if merged["_merge"].ne("both").any():
        raise ValueError("eligible keys are not a subset of CN ETF bars")
    return keys.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _build_bar_features(
    bars: pd.DataFrame,
    *,
    short_return_window: int,
    long_return_window: int,
    volatility_window: int,
    adv_window: int,
) -> pd.DataFrame:
    pieces: list[pd.DataFrame] = []
    for _, group in bars.groupby(["market", "asset_id"], sort=False):
        item = group.sort_values("date").copy()
        price = item["adj_close"].where(item["adj_close"] > 0.0)
        amount = item["amount"].where(item["amount"] > 0.0)
        session_index = item["session_index"]
        item["return_20"] = _exact_return(
            price,
            session_index,
            short_return_window,
        )
        item["return_60"] = _exact_return(
            price,
            session_index,
            long_return_window,
        )
        daily_return = _exact_return(price, session_index, 1)
        volatility = daily_return.rolling(
            volatility_window,
            min_periods=volatility_window,
        ).std(ddof=0)
        volatility_complete = (
            session_index - session_index.shift(volatility_window)
        ).eq(volatility_window)
        item["realized_volatility_20"] = volatility.where(volatility_complete)
        adv = amount.rolling(adv_window, min_periods=adv_window).mean()
        adv_complete = (
            session_index - session_index.shift(adv_window - 1)
        ).eq(adv_window - 1)
        item["adv20"] = adv.where(adv_complete)
        item["log_adv20"] = np.log(item["adv20"].where(item["adv20"] > 0.0))
        pieces.append(item)
    return pd.concat(pieces, ignore_index=True)[
        [
            "date",
            "asset_id",
            "market",
            "return_20",
            "return_60",
            "realized_volatility_20",
            "adv20",
            "log_adv20",
        ]
    ]


def _build_share_features(
    fund_structure: pd.DataFrame,
    *,
    sessions: pd.DataFrame,
    share_lookback: int,
) -> pd.DataFrame:
    required = {
        "date",
        "known_from",
        "asset_id",
        "market",
        "exchange",
        "total_share",
        "total_size",
    }
    missing = sorted(required - set(fund_structure.columns))
    if missing:
        raise ValueError(f"fund structure is missing columns: {', '.join(missing)}")
    frame = fund_structure[list(required)].copy()
    frame["source_date"] = pd.to_datetime(frame.pop("date"), errors="raise").dt.normalize()
    frame["known_from"] = pd.to_datetime(frame["known_from"], errors="raise").dt.normalize()
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    frame["exchange"] = frame["exchange"].astype(str).str.upper()
    frame["total_share"] = pd.to_numeric(frame["total_share"], errors="coerce")
    frame["total_size"] = pd.to_numeric(frame["total_size"], errors="coerce")
    if frame.duplicated(["source_date", "asset_id", "market"]).any():
        raise ValueError("fund structure contains duplicate asset-source-date rows")
    if frame.duplicated(["known_from", "asset_id", "market"]).any():
        raise ValueError("fund structure contains duplicate asset-known-from rows")
    if frame["known_from"].le(frame["source_date"]).any():
        raise ValueError("fund structure known_from must be later than source date")

    session_map = sessions.rename(columns={"date": "source_date"})
    frame = frame.merge(
        session_map,
        on=["source_date", "market"],
        how="left",
        validate="many_to_one",
    )
    if frame["session_index"].isna().any():
        raise ValueError("fund structure source date is outside the bar session calendar")
    lag_calendar = sessions.rename(
        columns={"date": "share_lag_date", "session_index": "lag_session_index"}
    )
    frame["lag_session_index"] = frame["session_index"] - share_lookback
    frame = frame.merge(
        lag_calendar,
        on=["market", "lag_session_index"],
        how="left",
        validate="many_to_one",
    )
    lagged = frame[
        ["source_date", "asset_id", "market", "total_share"]
    ].rename(
        columns={
            "source_date": "share_lag_date",
            "total_share": "lagged_total_share",
        }
    )
    frame = frame.merge(
        lagged,
        on=["share_lag_date", "asset_id", "market"],
        how="left",
        validate="many_to_one",
    )
    current_share = frame["total_share"].where(frame["total_share"] > 0.0)
    lagged_share = frame["lagged_total_share"].where(frame["lagged_total_share"] > 0.0)
    frame["raw_share_creation_20"] = np.log(current_share / lagged_share)
    frame["log_total_size"] = np.log(frame["total_size"].where(frame["total_size"] > 0.0))
    frame["exchange_sse"] = frame["exchange"].eq("SSE").astype(float)
    frame["date"] = frame["known_from"]
    return frame[
        [
            "date",
            "asset_id",
            "market",
            "source_date",
            "known_from",
            "raw_share_creation_20",
            "log_total_size",
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
        "raw_share_creation_20",
        "return_20",
        "return_60",
        "realized_volatility_20",
        "log_adv20",
        "log_total_size",
    ]
    numeric = daily[columns].apply(pd.to_numeric, errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    valid = numeric.notna().all(axis=1) & daily["exchange_sse"].notna()
    if int(valid.sum()) < min_cross_section:
        return None
    usable = numeric.loc[valid].copy()
    standardized = pd.DataFrame(index=usable.index)
    for column in columns:
        values = usable[column]
        lower = float(values.quantile(winsor_lower))
        upper = float(values.quantile(winsor_upper))
        clipped = values.clip(lower=lower, upper=upper)
        scale = float(clipped.std(ddof=0))
        if not np.isfinite(scale) or scale <= scale_epsilon:
            return None
        standardized[column] = (clipped - float(clipped.mean())) / scale
    x_columns = [
        "return_20",
        "return_60",
        "realized_volatility_20",
        "log_adv20",
        "log_total_size",
    ]
    x = np.column_stack(
        [
            np.ones(len(standardized)),
            standardized[x_columns].to_numpy(dtype=float),
        ]
    )
    exchange = daily.loc[standardized.index, "exchange_sse"].to_numpy(dtype=float)
    if np.unique(exchange).size > 1:
        x = np.column_stack([x, exchange])
    y = standardized["raw_share_creation_20"].to_numpy(dtype=float)
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
    share_lookback: int,
    short_return_window: int,
    long_return_window: int,
    volatility_window: int,
    adv_window: int,
) -> pd.DataFrame:
    specifications = (
        ("share_creation_20", "raw_share_creation_20", share_lookback),
        ("return_20", "return_20", short_return_window),
        ("return_60", "return_60", long_return_window),
        ("realized_volatility_20", "realized_volatility_20", volatility_window),
        ("log_adv20", "log_adv20", adv_window),
        ("log_total_size", "log_total_size", 1),
    )
    pieces = []
    for factor_name, source_column, lookback in specifications:
        item = diagnostics[["date", "asset_id", "market", source_column]].rename(
            columns={source_column: "factor_value"}
        )
        item["factor_name"] = factor_name
        item["lookback_window"] = int(lookback)
        item["date"] = item["date"].dt.date
        pieces.append(item[FACTOR_COLUMNS])
    return pd.concat(pieces, ignore_index=True).sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _exact_return(
    values: pd.Series,
    session_index: pd.Series,
    periods: int,
) -> pd.Series:
    lagged = values.shift(periods)
    complete = (session_index - session_index.shift(periods)).eq(periods)
    return (values / lagged - 1.0).where(complete)


def _validate_parameters(**parameters: float | int) -> None:
    for name in (
        "share_lookback",
        "short_return_window",
        "long_return_window",
        "volatility_window",
        "adv_window",
    ):
        if int(parameters[name]) < 1:
            raise ValueError(f"{name} must be positive")
    if int(parameters["long_return_window"]) <= int(parameters["short_return_window"]):
        raise ValueError("long_return_window must exceed short_return_window")
    if int(parameters["min_cross_section"]) < 8:
        raise ValueError("min_cross_section must be at least 8")
    lower = float(parameters["winsor_lower"])
    upper = float(parameters["winsor_upper"])
    if not 0.0 <= lower < upper <= 1.0:
        raise ValueError("winsor limits must satisfy 0 <= lower < upper <= 1")
    if float(parameters["scale_epsilon"]) <= 0.0:
        raise ValueError("scale_epsilon must be positive")
