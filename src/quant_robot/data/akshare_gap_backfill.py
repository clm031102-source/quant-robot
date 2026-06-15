from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

import pandas as pd

from quant_robot.assets.etf_universe import resolve_cn_etf_asset
from quant_robot.data.adapters.akshare_adapter import AkshareAdapter
from quant_robot.data.adapters.base import FetchRequest
from quant_robot.data.normalize import normalize_ohlcv
from quant_robot.data.quality import validate_market_data
from quant_robot.data.quality_report import build_quality_report
from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.processed_bars import load_processed_bars


STAGE = "phase_4_17_akshare_gap_backfill"


class GapBackfillAdapter(Protocol):
    def fetch_ohlcv(self, asset: Any, request: FetchRequest) -> pd.DataFrame:
        ...


def run_akshare_gap_backfill(
    gap_rows: list[dict[str, Any]],
    processed_root: str | Path,
    output_dir: str | Path,
    adapter: GapBackfillAdapter | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    raw_dir = output_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    backfill_adapter = adapter or AkshareAdapter()
    processed_path = Path(processed_root)
    result_rows: list[dict[str, Any]] = []
    fetched_bars: list[pd.DataFrame] = []

    for gap in gap_rows:
        result, bars = _fetch_gap(gap, backfill_adapter, raw_dir)
        result_rows.append(result)
        if bars is not None and not bars.empty:
            fetched_bars.append(bars)

    written = _merge_write_processed_bars(fetched_bars, processed_path)
    quality_report = _build_quality_report_if_available(processed_path)
    report = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "safety": "Research only. AKShare data backfill only; no broker connection, no account reads, no order placement, no live trading.",
        "summary": _summary(result_rows),
        "processed_root": str(processed_path),
        "written": [str(path) for path in written],
        "quality_report": quality_report,
        "rows": result_rows,
    }
    _write_report(output_path, report)
    return report


def _fetch_gap(
    gap: dict[str, Any],
    adapter: GapBackfillAdapter,
    raw_dir: Path,
) -> tuple[dict[str, Any], pd.DataFrame | None]:
    symbol = str(gap.get("symbol", "")).strip()
    missing_date = str(gap.get("missing_date", "")).strip()
    gap_id = str(gap.get("gap_id", "")).strip()
    base = {
        "gap_id": gap_id,
        "symbol": symbol,
        "missing_date": missing_date,
        "provider": "akshare",
        "local_only": True,
    }
    try:
        asset = resolve_cn_etf_asset(symbol)
        raw = adapter.fetch_ohlcv(asset, FetchRequest(missing_date, missing_date))
        if raw.empty:
            return {**base, "status": "no_target_row_from_provider", "rows": 0, "evidence_note": "AKShare returned no target row for the missing date."}, None
        raw = _target_date_rows(raw, missing_date)
        if raw.empty:
            return {**base, "status": "no_target_row_from_provider", "rows": 0, "evidence_note": "AKShare returned data, but not for the missing date."}, None
        raw_path = raw_dir / f"{symbol.replace('.', '_')}_{missing_date.replace('-', '')}.csv"
        raw.to_csv(raw_path, index=False)
        bars = normalize_ohlcv(raw, asset, source="akshare_gap_backfill", frequency="1d")
        validate_market_data(bars)
        return {
            **base,
            "status": "resolved_with_provider",
            "rows": int(len(bars)),
            "raw_path": str(raw_path),
            "evidence_note": "AKShare returned target row and it was merged into processed bars.",
        }, bars
    except Exception as exc:  # pragma: no cover - live provider failures vary
        return {**base, "status": "provider_error", "rows": 0, "evidence_note": str(exc)}, None


def _target_date_rows(raw: pd.DataFrame, missing_date: str) -> pd.DataFrame:
    frame = raw.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    target = pd.to_datetime(missing_date).date()
    return frame[frame["date"] == target].reset_index(drop=True)


def _merge_write_processed_bars(frames: list[pd.DataFrame], processed_root: Path) -> list[Path]:
    if not frames:
        return []
    bars = pd.concat(frames, ignore_index=True)
    store = DatasetStore(processed_root)
    written: list[Path] = []
    years = pd.to_datetime(bars["date"]).dt.year.astype(str)
    for year, group in bars.groupby(years):
        partitions = {"frequency": "1d", "market": "CN_ETF", "year": str(year)}
        merged = group
        if store.exists("processed/bars", partitions):
            existing = store.read_frame("processed/bars", partitions)
            merged = pd.concat([existing, group], ignore_index=True)
        merged = merged.drop_duplicates(["asset_id", "timestamp", "frequency"], keep="last")
        validate_market_data(merged)
        written.append(store.write_frame(merged, "processed/bars", partitions))
    return written


def _build_quality_report_if_available(processed_root: Path) -> dict[str, Any] | None:
    try:
        processed = load_processed_bars(processed_root, "CN_ETF")
    except FileNotFoundError:
        return None
    observed_dates = sorted(set(pd.to_datetime(processed["date"]).dt.date))
    expected_dates = observed_dates if int(processed["asset_id"].nunique()) > 1 else list(pd.bdate_range(min(observed_dates), max(observed_dates)).date)
    return build_quality_report(processed, expected_dates=expected_dates)


def _summary(rows: list[dict[str, Any]]) -> dict[str, int | bool]:
    statuses = [str(row.get("status", "")) for row in rows]
    resolved = statuses.count("resolved_with_provider")
    empty = statuses.count("no_target_row_from_provider")
    errors = statuses.count("provider_error")
    return {
        "gap_rows": len(rows),
        "resolved_with_provider": resolved,
        "no_target_row_from_provider": empty,
        "provider_error": errors,
        "blocks_api_boundary": empty > 0 or errors > 0,
    }


def _write_report(output_dir: Path, report: dict[str, Any]) -> None:
    (output_dir / "akshare_gap_backfill_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(report.get("rows", [])).to_csv(output_dir / "akshare_gap_backfill_rows.csv", index=False)
