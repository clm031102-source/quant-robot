from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


LISTING_AGE_BOARD_FACTOR_NAMES = (
    "listing_age_log_seasoned_252",
    "listing_age_young_overhang_avoidance_252",
    "listing_age_mid_seasoning_252_1000",
    "fresh_listing_opening_risk_avoidance_120",
    "board_permission_mainboard_preference",
    "growth_board_permission_risk_avoidance",
    "listing_age_board_compound_risk_avoidance",
)


def compute_listing_age_board_factors(
    bars: pd.DataFrame,
    *,
    stock_basic: pd.DataFrame | None,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    required = ["date", "asset_id", "market"]
    missing = [column for column in required if column not in bars.columns]
    if missing:
        raise ValueError(
            "Bars are missing columns for listing-age/board factor calculation: "
            + ", ".join(missing)
        )
    requested = _resolve_requested_factor_names(factor_names)
    frame = _feature_frame(bars, stock_basic)
    if frame.empty:
        return pd.DataFrame(columns=FACTOR_COLUMNS)

    valid = frame["listing_age_days"].ge(0) & frame["list_date"].notna()
    delist_date = pd.to_datetime(frame["delist_date"], errors="coerce")
    valid = valid & (delist_date.isna() | (frame["date"] <= delist_date))

    log_age = np.log1p(frame["listing_age_days"].where(valid))
    young_overhang_252 = ((252.0 - frame["listing_age_days"]).clip(lower=0.0, upper=252.0) / 252.0).where(valid)
    fresh_120 = ((120.0 - frame["listing_age_days"]).clip(lower=0.0, upper=120.0) / 120.0).where(valid)
    mid_target = np.log1p(650.0)
    mid_width = np.log1p(1000.0) - np.log1p(252.0)
    mid_seasoning = (1.0 - (log_age - mid_target).abs() / mid_width).clip(lower=-1.0, upper=1.0).where(valid)
    permission_risk = (
        0.75 * frame["is_star_board"].astype(float)
        + 0.75 * frame["is_gem_board"].astype(float)
        + 1.00 * frame["is_bse_board"].astype(float)
    ).where(valid)
    mainboard_preference = (frame["is_main_board"].astype(float) - permission_risk).where(valid)

    values_by_name = {
        "listing_age_log_seasoned_252": _cs_z(frame, log_age),
        "listing_age_young_overhang_avoidance_252": -_cs_z(frame, young_overhang_252),
        "listing_age_mid_seasoning_252_1000": _cs_z(frame, mid_seasoning),
        "fresh_listing_opening_risk_avoidance_120": -_cs_z(frame, fresh_120),
        "board_permission_mainboard_preference": _cs_z(frame, mainboard_preference),
        "growth_board_permission_risk_avoidance": -_cs_z(frame, permission_risk),
        "listing_age_board_compound_risk_avoidance": _cs_z(frame, log_age) - 0.50 * _cs_z(frame, permission_risk),
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return LISTING_AGE_BOARD_FACTOR_NAMES
    supported = set(LISTING_AGE_BOARD_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported listing-age/board factor_names: {', '.join(unknown)}")
    return factor_names


def _feature_frame(bars: pd.DataFrame, stock_basic: pd.DataFrame | None) -> pd.DataFrame:
    frame = bars[["date", "asset_id", "market"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str)
    frame = frame.dropna(subset=["date", "asset_id"]).drop_duplicates(["date", "asset_id", "market"])
    meta = _normalise_stock_basic(stock_basic)
    if meta.empty:
        for column in (
            "symbol",
            "exchange",
            "stock_market",
            "list_date",
            "delist_date",
            "is_star_board",
            "is_gem_board",
            "is_bse_board",
            "is_main_board",
        ):
            frame[column] = pd.NA
    else:
        frame = frame.merge(meta, on="asset_id", how="left", validate="many_to_one")
    frame["list_date"] = pd.to_datetime(frame["list_date"], errors="coerce")
    frame["delist_date"] = pd.to_datetime(frame["delist_date"], errors="coerce")
    frame["listing_age_days"] = (frame["date"] - frame["list_date"]).dt.days.astype("float")
    for column in ["is_star_board", "is_gem_board", "is_bse_board", "is_main_board"]:
        frame[column] = frame[column].fillna(False).astype(bool)
    return frame.replace([np.inf, -np.inf], np.nan).sort_values(["asset_id", "date"]).reset_index(drop=True)


def _normalise_stock_basic(stock_basic: pd.DataFrame | None) -> pd.DataFrame:
    if stock_basic is None or stock_basic.empty or "asset_id" not in stock_basic:
        return pd.DataFrame()
    frame = stock_basic.copy()
    frame["asset_id"] = frame["asset_id"].astype(str)
    for column in ["symbol", "exchange", "stock_market"]:
        if column not in frame:
            frame[column] = ""
        frame[column] = frame[column].fillna("").astype(str)
    for column in ["list_date", "delist_date"]:
        if column not in frame:
            frame[column] = pd.NaT
        frame[column] = pd.to_datetime(frame[column], errors="coerce")

    symbol = frame["symbol"].str.upper()
    stock_market = frame["stock_market"].astype(str)
    exchange = frame["exchange"].str.upper()
    frame["is_bse_board"] = exchange.eq("XBEI") | symbol.str.endswith(".BJ") | stock_market.str.contains("北交", na=False)
    frame["is_star_board"] = symbol.str.startswith(("688", "689")) | stock_market.str.contains("科创", na=False)
    frame["is_gem_board"] = symbol.str.startswith(("300", "301")) | stock_market.str.contains("创业", na=False)
    frame["is_main_board"] = ~(frame["is_bse_board"] | frame["is_star_board"] | frame["is_gem_board"])
    columns = [
        "asset_id",
        "symbol",
        "exchange",
        "stock_market",
        "list_date",
        "delist_date",
        "is_bse_board",
        "is_star_board",
        "is_gem_board",
        "is_main_board",
    ]
    return frame[columns].sort_values(["asset_id", "list_date"]).drop_duplicates("asset_id", keep="last")


def _cs_z(frame: pd.DataFrame, values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    grouped = numeric.groupby([frame["date"], frame["market"]], sort=False)
    mean = grouped.transform("mean")
    std = grouped.transform(lambda item: item.std(ddof=0))
    return ((numeric - mean) / std.where(std > 1e-12)).replace([np.inf, -np.inf], np.nan)


def _factor_frame(frame: pd.DataFrame, name: str, values: pd.Series) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": frame["date"].dt.date.to_numpy(),
            "asset_id": frame["asset_id"].to_numpy(),
            "market": frame["market"].to_numpy(),
            "factor_name": name,
            "factor_value": values.to_numpy(),
            "lookback_window": 252 if "252" in name else 120,
        }
    )
