from __future__ import annotations

import numpy as np
import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


OFFICIAL_TRADEABILITY_EVENT_FACTOR_NAMES = (
    "official_limit_down_reopen_rebound_5",
    "official_limit_up_crowding_avoidance_3",
    "official_limit_down_pressure_avoidance_5",
    "official_post_suspension_reopen_risk_avoidance_10",
    "official_st_name_risk_avoidance_20",
    "official_tradeability_cleanliness_20",
    "official_limit_state_recovery_quality_5",
)


def compute_official_tradeability_event_factors(
    bars: pd.DataFrame,
    tradeability_masks: pd.DataFrame,
    factor_names: tuple[str, ...] | None = None,
) -> pd.DataFrame:
    requested = _resolve_requested_factor_names(factor_names)
    _require_columns(bars, ["date", "asset_id", "market", "amount"], "bars")
    _require_columns(tradeability_masks, ["date", "asset_id", "market"], "tradeability masks")

    frame = _build_feature_frame(bars, tradeability_masks)
    values_by_name = {
        "official_limit_down_reopen_rebound_5": _cs_z(frame, frame["post_limit_down_reopen_5"] - 0.25 * frame["recent_blocked_20"]),
        "official_limit_up_crowding_avoidance_3": _cs_z(frame, -frame["recent_limit_up_3"]),
        "official_limit_down_pressure_avoidance_5": _cs_z(frame, -frame["recent_limit_down_5"]),
        "official_post_suspension_reopen_risk_avoidance_10": _cs_z(frame, -frame["post_suspension_reopen_10"]),
        "official_st_name_risk_avoidance_20": _cs_z(frame, -frame["recent_st_20"]),
        "official_tradeability_cleanliness_20": _cs_z(frame, -frame["recent_blocked_20"]),
        "official_limit_state_recovery_quality_5": _cs_z(
            frame,
            frame["post_limit_down_reopen_5"]
            - frame["post_limit_up_reopen_5"]
            - 0.50 * frame["recent_suspended_20"],
        ),
    }
    pieces = [_factor_frame(frame, name, values_by_name[name]) for name in requested]
    if not pieces:
        return pd.DataFrame(columns=FACTOR_COLUMNS)
    return pd.concat(pieces, ignore_index=True)[FACTOR_COLUMNS].sort_values(
        ["asset_id", "date", "factor_name"]
    ).reset_index(drop=True)


def _resolve_requested_factor_names(factor_names: tuple[str, ...] | None) -> tuple[str, ...]:
    if factor_names is None:
        return OFFICIAL_TRADEABILITY_EVENT_FACTOR_NAMES
    supported = set(OFFICIAL_TRADEABILITY_EVENT_FACTOR_NAMES)
    unknown = [name for name in factor_names if name not in supported]
    if unknown:
        raise ValueError(f"Unsupported official tradeability event factor_names: {', '.join(unknown)}")
    return factor_names


def _build_feature_frame(bars: pd.DataFrame, masks: pd.DataFrame) -> pd.DataFrame:
    mask_features = _tradeability_mask_features(masks)
    bar_frame = bars[["date", "asset_id", "market", "amount"]].copy()
    bar_frame["date"] = pd.to_datetime(bar_frame["date"], errors="coerce").dt.normalize()
    bar_frame["asset_id"] = bar_frame["asset_id"].astype(str)
    bar_frame["market"] = bar_frame["market"].fillna("CN").astype(str).str.upper()
    bar_frame["amount"] = pd.to_numeric(bar_frame["amount"], errors="coerce")
    merged = bar_frame.merge(mask_features, on=["date", "asset_id", "market"], how="left", validate="many_to_one")
    for column in _FEATURE_COLUMNS:
        if column not in merged:
            merged[column] = 0.0
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0.0)
    return merged


_FEATURE_COLUMNS = (
    "recent_limit_up_3",
    "recent_limit_down_5",
    "recent_blocked_20",
    "recent_suspended_20",
    "recent_st_20",
    "post_suspension_reopen_10",
    "post_limit_up_reopen_5",
    "post_limit_down_reopen_5",
)


def _tradeability_mask_features(masks: pd.DataFrame) -> pd.DataFrame:
    frame = masks.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.normalize()
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].fillna("CN").astype(str).str.upper()
    frame = frame.dropna(subset=["date", "asset_id", "market"]).sort_values(["asset_id", "date"]).reset_index(drop=True)
    if frame.empty:
        return pd.DataFrame(columns=["date", "asset_id", "market", *_FEATURE_COLUMNS])
    for column in ["limit_up_official", "limit_down_official", "suspended_official", "st_flag_official", "fully_tradeable"]:
        if column not in frame:
            frame[column] = False
        frame[column] = frame[column].fillna(False).astype(bool)
    frame["official_blocked"] = (
        frame["limit_up_official"]
        | frame["limit_down_official"]
        | frame["suspended_official"]
        | frame["st_flag_official"]
        | (~frame["fully_tradeable"])
    )

    pieces = []
    for _, group in frame.groupby("asset_id", sort=False):
        item = group.copy()
        limit_up = item["limit_up_official"].astype(float)
        limit_down = item["limit_down_official"].astype(float)
        suspended = item["suspended_official"].astype(float)
        st_flag = item["st_flag_official"].astype(float)
        blocked = item["official_blocked"].astype(float)
        fully_tradeable = item["fully_tradeable"].astype(bool)
        item["recent_limit_up_3"] = limit_up.rolling(3, min_periods=1).sum()
        item["recent_limit_down_5"] = limit_down.rolling(5, min_periods=1).sum()
        item["recent_blocked_20"] = blocked.rolling(20, min_periods=1).sum()
        item["recent_suspended_20"] = suspended.rolling(20, min_periods=1).sum()
        item["recent_st_20"] = st_flag.rolling(20, min_periods=1).sum()
        item["post_suspension_reopen_10"] = (
            fully_tradeable.astype(float) * suspended.shift(1).rolling(10, min_periods=1).sum().fillna(0.0)
        )
        item["post_limit_up_reopen_5"] = (
            fully_tradeable.astype(float) * limit_up.shift(1).rolling(5, min_periods=1).sum().fillna(0.0)
        )
        item["post_limit_down_reopen_5"] = (
            fully_tradeable.astype(float) * limit_down.shift(1).rolling(5, min_periods=1).sum().fillna(0.0)
        )
        pieces.append(item[["date", "asset_id", "market", *_FEATURE_COLUMNS]])
    return pd.concat(pieces, ignore_index=True).drop_duplicates(["date", "asset_id", "market"], keep="last")


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
            "lookback_window": 20,
        }
    )


def _require_columns(frame: pd.DataFrame, required: list[str], label: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{label} are missing columns: {', '.join(missing)}")
