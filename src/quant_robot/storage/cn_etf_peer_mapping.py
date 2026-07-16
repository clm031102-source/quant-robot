from __future__ import annotations

import hashlib
import unicodedata
from datetime import timedelta
from pathlib import Path
from typing import Mapping

import pandas as pd

from quant_robot.assets.etf_universe import cn_etf_asset
from quant_robot.storage.dataset_store import DatasetStore


CN_ETF_PEER_MAPPING_COLUMNS = [
    "asset_id",
    "symbol",
    "peer_id",
    "peer_name",
    "list_date",
    "valid_from",
    "valid_to",
    "known_from",
    "mapping_method",
    "source",
]


def build_cn_etf_peer_mapping_history(
    snapshots: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    dated_snapshots = sorted(
        (pd.Timestamp(snapshot).normalize(), frame)
        for snapshot, frame in snapshots.items()
    )
    rows: list[pd.DataFrame] = []
    for index, (snapshot_date, frame) in enumerate(dated_snapshots):
        if frame.empty or "symbol" not in frame or "index_code" not in frame:
            continue
        source = frame.copy()
        source["symbol"] = source["symbol"].fillna("").astype(str).str.upper().str.strip()
        source["index_code"] = source["index_code"].fillna("").astype(str).str.upper().str.strip()
        source = source[source["symbol"].ne("") & source["index_code"].ne("")].copy()
        if source.empty:
            continue
        list_dates = (
            pd.to_datetime(source["list_date"], errors="coerce")
            if "list_date" in source
            else pd.Series(pd.NaT, index=source.index)
        )
        valid_from = list_dates.where(list_dates.gt(snapshot_date), snapshot_date)
        valid_to = (
            dated_snapshots[index + 1][0] - timedelta(days=1)
            if index + 1 < len(dated_snapshots)
            else pd.NaT
        )
        mapped = pd.DataFrame(
            {
                "asset_id": [
                    cn_etf_asset(str(symbol), str(name)).asset_id
                    for symbol, name in zip(
                        source["symbol"],
                        source["name"] if "name" in source else pd.Series("", index=source.index),
                    )
                ],
                "symbol": source["symbol"],
                "peer_id": source["index_code"],
                "peer_name": source["index_name"] if "index_name" in source else "",
                "list_date": list_dates.dt.date,
                "valid_from": pd.to_datetime(valid_from).dt.date,
                "valid_to": valid_to.date() if pd.notna(valid_to) else pd.NaT,
                "known_from": snapshot_date.date(),
                "mapping_method": "official_index_code",
                "source": f"tushare_etf_basic:{snapshot_date.date().isoformat()}",
            }
        )
        rows.append(_drop_empty_validity_intervals(mapped))
    if not rows:
        return pd.DataFrame(columns=CN_ETF_PEER_MAPPING_COLUMNS)
    return (
        pd.concat(rows, ignore_index=True)[CN_ETF_PEER_MAPPING_COLUMNS]
        .drop_duplicates(["asset_id", "known_from", "peer_id"], keep="last")
        .sort_values(["asset_id", "known_from", "peer_id"])
        .reset_index(drop=True)
    )


def build_cn_etf_peer_mapping_history_from_fund_basic(
    snapshots: Mapping[str, pd.DataFrame],
) -> pd.DataFrame:
    dated_snapshots = sorted(
        (pd.Timestamp(snapshot).normalize(), frame)
        for snapshot, frame in snapshots.items()
    )
    rows: list[pd.DataFrame] = []
    for index, (snapshot_date, frame) in enumerate(dated_snapshots):
        if frame.empty or "symbol" not in frame or "benchmark" not in frame:
            continue
        source = frame.copy()
        source["symbol"] = source["symbol"].fillna("").astype(str).str.upper().str.strip()
        source["benchmark"] = source["benchmark"].fillna("").astype(str).str.strip()
        if "is_etf" in source:
            source = source[source["is_etf"].fillna(False).astype(bool)]
        source = source[
            source["symbol"].str.endswith((".SH", ".SZ"))
            & source["benchmark"].ne("")
        ].copy()
        if source.empty:
            continue
        canonical = source["benchmark"].map(_canonical_benchmark_text)
        list_dates = (
            pd.to_datetime(source["list_date"], errors="coerce")
            if "list_date" in source
            else pd.Series(pd.NaT, index=source.index)
        )
        valid_from = list_dates.where(list_dates.gt(snapshot_date), snapshot_date)
        valid_to = (
            dated_snapshots[index + 1][0] - timedelta(days=1)
            if index + 1 < len(dated_snapshots)
            else pd.NaT
        )
        mapped = pd.DataFrame(
            {
                "asset_id": [
                    cn_etf_asset(str(symbol), str(name)).asset_id
                    for symbol, name in zip(
                        source["symbol"],
                        source["name"] if "name" in source else pd.Series("", index=source.index),
                    )
                ],
                "symbol": source["symbol"],
                "peer_id": canonical.map(
                    lambda value: f"BENCHMARK:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:20]}"
                ),
                "peer_name": source["benchmark"],
                "list_date": list_dates.dt.date,
                "valid_from": pd.to_datetime(valid_from).dt.date,
                "valid_to": valid_to.date() if pd.notna(valid_to) else pd.NaT,
                "known_from": snapshot_date.date(),
                "mapping_method": "official_benchmark_text",
                "source": f"tushare_fund_basic:{snapshot_date.date().isoformat()}",
            }
        )
        rows.append(_drop_empty_validity_intervals(mapped))
    if not rows:
        return pd.DataFrame(columns=CN_ETF_PEER_MAPPING_COLUMNS)
    return (
        pd.concat(rows, ignore_index=True)[CN_ETF_PEER_MAPPING_COLUMNS]
        .drop_duplicates(["asset_id", "known_from", "peer_id"], keep="last")
        .sort_values(["asset_id", "known_from", "peer_id"])
        .reset_index(drop=True)
    )


def load_cn_etf_peer_mapping(root: str | Path) -> pd.DataFrame:
    return DatasetStore(root).read_frame(
        "metadata/cn_etf_peer_mapping",
        {"market": "CN_ETF"},
    )


def _canonical_benchmark_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(value)).upper()
    return "".join(normalized.split())


def _drop_empty_validity_intervals(frame: pd.DataFrame) -> pd.DataFrame:
    valid_from = pd.to_datetime(frame["valid_from"], errors="coerce")
    valid_to = pd.to_datetime(frame["valid_to"], errors="coerce")
    return frame[valid_to.isna() | valid_from.le(valid_to)].copy()
