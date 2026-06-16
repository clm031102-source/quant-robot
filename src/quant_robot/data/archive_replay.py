from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.data.ingest.tushare_moneyflow_inputs import (
    _normalize_moneyflow,
    _quality_report as _moneyflow_quality_report,
    _write_processed_by_year as _write_moneyflow_by_year,
)
from quant_robot.data.ingest.tushare_pipeline import (
    _normalize_tushare_daily,
    _write_processed_by_year as _write_bars_by_year,
)
from quant_robot.storage.dataset_store import DatasetStore


def replay_tushare_archive_to_processed(
    daily_roots: list[str | Path],
    moneyflow_roots: list[str | Path],
    output_dir: str | Path,
    market: str = "CN",
) -> dict[str, Any]:
    market = market.upper()
    output_path = Path(output_dir)
    store = DatasetStore(output_path)
    daily_raw = _read_raw_partitions(daily_roots, "raw/tushare/daily")
    moneyflow_raw = _read_raw_partitions(moneyflow_roots, "raw/tushare/moneyflow")

    daily_processed = _normalize_tushare_daily(daily_raw, market) if not daily_raw.empty else pd.DataFrame()
    if not daily_processed.empty:
        _write_bars_by_year(store, daily_processed, market)

    moneyflow_processed = _normalize_moneyflow(moneyflow_raw, market) if not moneyflow_raw.empty else pd.DataFrame()
    if not moneyflow_processed.empty:
        _write_moneyflow_by_year(store, moneyflow_processed, market)

    result = {
        "market": market,
        "daily_roots": [str(Path(root)) for root in daily_roots],
        "moneyflow_roots": [str(Path(root)) for root in moneyflow_roots],
        "output_dir": str(output_path),
        "daily": {
            "raw_rows": int(len(daily_raw)),
            "processed_rows": int(len(daily_processed)),
            "assets": int(daily_processed["asset_id"].nunique()) if not daily_processed.empty else 0,
        },
        "moneyflow": {
            "raw_rows": int(len(moneyflow_raw)),
            "processed_rows": int(len(moneyflow_processed)),
            "quality_report": _moneyflow_quality_report(moneyflow_processed, market),
        },
    }
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "archive_replay_manifest.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result


def _read_raw_partitions(roots: list[str | Path], dataset: str) -> pd.DataFrame:
    frames = []
    for root in roots:
        root_path = Path(root)
        store = DatasetStore(root_path)
        dataset_path = root_path / dataset
        for partition in sorted(dataset_path.glob("trade_date=*")):
            trade_date = partition.name.split("=", 1)[1]
            frames.append(store.read_frame(dataset, {"trade_date": trade_date}))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates().reset_index(drop=True)
