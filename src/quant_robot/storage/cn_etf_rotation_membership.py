from __future__ import annotations

from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


def load_cn_etf_rotation_membership(root: str | Path, market: str = "CN_ETF") -> pd.DataFrame:
    frame = DatasetStore(root).read_frame("metadata/cn_etf_rotation_membership", {"market": market.upper()})
    required = {"date", "asset_id", "is_rotation_member"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"CN_ETF rotation membership missing required columns: {missing}")
    frame = frame.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["is_rotation_member"] = _coerce_bool(frame["is_rotation_member"])
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def filter_signals_to_cn_etf_rotation_membership(
    signals: pd.DataFrame,
    *,
    root: str | Path | None,
    market: str,
    required: bool = False,
    min_history_rows_to_date: int | None = None,
    min_live_members: int | None = None,
) -> pd.DataFrame:
    if signals.empty or market.upper() != "CN_ETF":
        return signals.reset_index(drop=True)
    if root is None:
        if required:
            raise ValueError("rotation_membership_root is required for CN_ETF rotation membership filtering")
        return signals.reset_index(drop=True)
    try:
        membership = load_cn_etf_rotation_membership(root, market)
    except FileNotFoundError:
        if required:
            raise
        return signals.reset_index(drop=True)
    active = membership[membership["is_rotation_member"]].copy()
    if min_history_rows_to_date is not None and min_history_rows_to_date > 0:
        if "history_rows_to_date" not in active.columns:
            raise ValueError("CN_ETF rotation maturity filter requires history_rows_to_date")
        active = active[pd.to_numeric(active["history_rows_to_date"], errors="coerce") >= int(min_history_rows_to_date)]
    active = _filter_active_by_live_member_count(active, min_live_members)
    active = active[["asset_id", "date"]].drop_duplicates()
    frame = signals.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame["asset_id"] = frame["asset_id"].astype(str)
    filtered = frame.merge(active.assign(_rotation_member=True), on=["asset_id", "date"], how="left")
    filtered = filtered[filtered["_rotation_member"].fillna(False)].drop(columns=["_rotation_member"])
    return filtered.sort_values(["date", "asset_id", "factor_name"]).reset_index(drop=True)


def _filter_active_by_live_member_count(active: pd.DataFrame, min_live_members: int | None) -> pd.DataFrame:
    if min_live_members is None or min_live_members <= 0 or active.empty:
        return active
    counts = active.groupby("date")["asset_id"].transform("nunique")
    return active[counts >= int(min_live_members)].reset_index(drop=True)


def _coerce_bool(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.fillna(False).astype(bool)
    text = series.fillna("").astype(str).str.strip().str.lower()
    return text.isin({"1", "true", "t", "yes", "y"})
