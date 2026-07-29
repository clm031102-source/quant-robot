from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


FACTOR_NAME = "etf_delayed_nav_premium_innovation_reversal_60"
DIRECT_EXPOSURE_NAMES = (
    "raw_nav_premium",
    "return_20",
    "return_60",
    "realized_volatility_20",
    "log_adv20",
)


@dataclass(frozen=True)
class DelayedNavPremiumInnovationResult:
    factors: pd.DataFrame
    diagnostics: pd.DataFrame
    direct_exposures: pd.DataFrame
    adv20: pd.DataFrame


def compute_etf_delayed_nav_premium_innovation(
    bars: pd.DataFrame,
    nav: pd.DataFrame,
    *,
    eligible_keys: pd.DataFrame,
    official_sessions: Sequence[pd.Timestamp],
    premium_lookback: int = 60,
    return_windows: tuple[int, int] = (20, 60),
    volatility_window: int = 20,
    adv_window: int = 20,
) -> DelayedNavPremiumInnovationResult:
    _validate_parameters(
        premium_lookback=premium_lookback,
        return_windows=return_windows,
        volatility_window=volatility_window,
        adv_window=adv_window,
    )
    bar_frame = _normalise_bars(bars, official_sessions=official_sessions)
    keys = _normalise_eligible_keys(eligible_keys, bar_frame)
    nav_frame = _normalise_nav(nav)
    diagnostics = keys.merge(
        bar_frame,
        on=["date", "asset_id", "market"],
        how="left",
        validate="one_to_one",
    )
    pieces = []
    for asset_id, group in diagnostics.groupby("asset_id", sort=False):
        item = group.sort_values("date").copy()
        asset_nav = nav_frame.loc[nav_frame["asset_id"].eq(asset_id)].copy()
        if asset_nav.empty:
            item["nav_date"] = pd.NaT
            item["known_from"] = pd.NaT
            item["latest_unit_nav"] = np.nan
        else:
            asset_nav = (
                asset_nav.sort_values(["known_from", "nav_date"])
                .drop_duplicates("known_from", keep="last")
                .rename(columns={"unit_nav": "latest_unit_nav"})
            )
            item = pd.merge_asof(
                item.sort_values("date"),
                asset_nav[["known_from", "nav_date", "latest_unit_nav"]],
                left_on="date",
                right_on="known_from",
                direction="backward",
                allow_exact_matches=True,
            )
        close = pd.to_numeric(item["close"], errors="coerce").where(
            pd.to_numeric(item["close"], errors="coerce") > 0.0
        )
        latest_nav = pd.to_numeric(item["latest_unit_nav"], errors="coerce").where(
            pd.to_numeric(item["latest_unit_nav"], errors="coerce") > 0.0
        )
        item["nav_premium"] = close / latest_nav - 1.0
        prior_median = item["nav_premium"].shift(1).rolling(
            premium_lookback,
            min_periods=premium_lookback,
        ).median()
        complete_premium_window = (
            item["session_index"] - item["session_index"].shift(premium_lookback)
        ).eq(premium_lookback)
        item["prior_premium_median"] = prior_median.where(complete_premium_window)
        item["premium_innovation"] = item["nav_premium"] - item["prior_premium_median"]
        item["factor_value"] = -item["premium_innovation"]
        _add_bar_exposures(
            item,
            return_windows=return_windows,
            volatility_window=volatility_window,
            adv_window=adv_window,
        )
        pieces.append(item)
    diagnostics = pd.concat(pieces, ignore_index=True).sort_values(
        ["asset_id", "date"]
    ).reset_index(drop=True)

    factors = diagnostics[["date", "asset_id", "market", "factor_value"]].copy()
    factors["factor_name"] = FACTOR_NAME
    factors["lookback_window"] = int(premium_lookback)
    factors["date"] = factors["date"].dt.date
    factors = factors[FACTOR_COLUMNS].sort_values(["asset_id", "date"]).reset_index(drop=True)

    exposure_specs = (
        ("raw_nav_premium", "nav_premium", premium_lookback),
        ("return_20", "return_20", return_windows[0]),
        ("return_60", "return_60", return_windows[1]),
        ("realized_volatility_20", "realized_volatility_20", volatility_window),
        ("log_adv20", "log_adv20", adv_window),
    )
    exposure_frames = []
    for factor_name, source_column, lookback in exposure_specs:
        item = diagnostics[["date", "asset_id", "market", source_column]].rename(
            columns={source_column: "factor_value"}
        )
        item["factor_name"] = factor_name
        item["lookback_window"] = int(lookback)
        item["date"] = item["date"].dt.date
        exposure_frames.append(item[FACTOR_COLUMNS])
    direct_exposures = pd.concat(exposure_frames, ignore_index=True).sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)
    adv20 = diagnostics[["date", "asset_id", "market", "adv20"]].copy()
    adv20["date"] = adv20["date"].dt.date
    return DelayedNavPremiumInnovationResult(
        factors=factors,
        diagnostics=diagnostics,
        direct_exposures=direct_exposures,
        adv20=adv20.sort_values(["asset_id", "date"]).reset_index(drop=True),
    )


def _normalise_bars(
    bars: pd.DataFrame,
    *,
    official_sessions: Sequence[pd.Timestamp],
) -> pd.DataFrame:
    required = {"date", "asset_id", "market", "close", "adj_close", "amount"}
    missing = sorted(required - set(bars.columns))
    if missing:
        raise ValueError(f"CN ETF bars are missing columns: {', '.join(missing)}")
    frame = bars[list(required)].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="raise").dt.normalize()
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str).str.upper()
    for column in ("close", "adj_close", "amount"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if frame.duplicated(["date", "asset_id", "market"]).any():
        raise ValueError("CN ETF bars contain duplicate asset-date rows")
    sessions = pd.DatetimeIndex(pd.to_datetime(pd.Series(official_sessions), errors="raise"))
    sessions = sessions.normalize().drop_duplicates().sort_values()
    session_map = pd.Series(range(len(sessions)), index=sessions)
    frame["session_index"] = frame["date"].map(session_map)
    if frame["session_index"].isna().any():
        raise ValueError("CN ETF bars contain dates outside the official session calendar")
    frame["session_index"] = frame["session_index"].astype(int)
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _normalise_eligible_keys(
    eligible_keys: pd.DataFrame,
    bars: pd.DataFrame,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market"]
    missing = [column for column in required if column not in eligible_keys.columns]
    if missing:
        raise ValueError("eligible keys are missing columns: " + ", ".join(missing))
    keys = eligible_keys[required].copy()
    keys["date"] = pd.to_datetime(keys["date"], errors="raise").dt.normalize()
    keys["asset_id"] = keys["asset_id"].astype(str)
    keys["market"] = keys["market"].astype(str).str.upper()
    if keys.duplicated(required).any():
        raise ValueError("eligible keys contain duplicate rows")
    merged = keys.merge(
        bars[required],
        on=required,
        how="left",
        indicator=True,
        validate="one_to_one",
    )
    if merged["_merge"].ne("both").any():
        raise ValueError("eligible keys are not a subset of CN ETF bars")
    return keys.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _normalise_nav(nav: pd.DataFrame) -> pd.DataFrame:
    required = {
        "nav_date",
        "ann_date",
        "known_from",
        "asset_id",
        "unit_nav",
        "is_pit_usable",
        "source",
    }
    missing = sorted(required - set(nav.columns))
    if missing:
        raise ValueError(f"Tushare NAV source is missing columns: {', '.join(missing)}")
    frame = nav[list(required)].copy()
    for column in ("nav_date", "ann_date", "known_from"):
        frame[column] = pd.to_datetime(frame[column], errors="coerce").dt.normalize()
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["unit_nav"] = pd.to_numeric(frame["unit_nav"], errors="coerce")
    usable = (
        frame["is_pit_usable"].fillna(False).astype(bool)
        & frame["source"].eq("tushare_fund_nav")
        & frame["nav_date"].notna()
        & frame["ann_date"].notna()
        & frame["known_from"].notna()
        & frame["ann_date"].ge(frame["nav_date"])
        & frame["known_from"].gt(frame["nav_date"])
        & frame["known_from"].gt(frame["ann_date"])
        & frame["unit_nav"].gt(0.0)
    )
    frame = frame.loc[usable].copy()
    if frame.duplicated(["asset_id", "nav_date"]).any():
        raise ValueError("Tushare NAV source contains duplicate asset-date rows")
    return frame.sort_values(["asset_id", "known_from", "nav_date"]).reset_index(drop=True)


def _add_bar_exposures(
    item: pd.DataFrame,
    *,
    return_windows: tuple[int, int],
    volatility_window: int,
    adv_window: int,
) -> None:
    adjusted = pd.to_numeric(item["adj_close"], errors="coerce").where(
        pd.to_numeric(item["adj_close"], errors="coerce") > 0.0
    )
    for window, name in zip(return_windows, ("return_20", "return_60"), strict=True):
        item[name] = _exact_change(adjusted, item["session_index"], window)
    daily_return = _exact_change(adjusted, item["session_index"], 1)
    volatility = daily_return.rolling(
        volatility_window,
        min_periods=volatility_window,
    ).std(ddof=0)
    volatility_complete = (
        item["session_index"] - item["session_index"].shift(volatility_window)
    ).eq(volatility_window)
    item["realized_volatility_20"] = volatility.where(volatility_complete)
    amount = pd.to_numeric(item["amount"], errors="coerce").where(
        pd.to_numeric(item["amount"], errors="coerce") > 0.0
    )
    adv = amount.rolling(adv_window, min_periods=adv_window).mean()
    adv_complete = (
        item["session_index"] - item["session_index"].shift(adv_window - 1)
    ).eq(adv_window - 1)
    item["adv20"] = adv.where(adv_complete)
    item["log_adv20"] = np.log(item["adv20"].where(item["adv20"] > 0.0))


def _exact_change(
    values: pd.Series,
    session_index: pd.Series,
    periods: int,
) -> pd.Series:
    lagged = values.shift(periods)
    complete = (session_index - session_index.shift(periods)).eq(periods)
    return (values / lagged - 1.0).where(complete)


def _validate_parameters(
    *,
    premium_lookback: int,
    return_windows: tuple[int, int],
    volatility_window: int,
    adv_window: int,
) -> None:
    if premium_lookback < 1:
        raise ValueError("premium_lookback must be positive")
    if len(return_windows) != 2 or not 0 < return_windows[0] < return_windows[1]:
        raise ValueError("return_windows must contain two increasing positive values")
    if volatility_window < 1 or adv_window < 1:
        raise ValueError("volatility_window and adv_window must be positive")
