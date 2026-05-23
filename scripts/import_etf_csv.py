from __future__ import annotations

import argparse
import os
import json
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.assets.etf_universe import resolve_cn_etf_asset
from quant_robot.data.adapters.tradingview_csv_adapter import parse_tradingview_csv
from quant_robot.data.normalize import normalize_ohlcv
from quant_robot.data.quality import validate_market_data
from quant_robot.data.quality_report import build_quality_report
from quant_robot.storage.dataset_store import DatasetStore


def import_etf_csv(
    input_path: str | Path,
    output_dir: str | Path,
    symbol: str,
    source: str = "tradingview_csv",
    frequency: str = "1d",
) -> dict[str, Any]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    asset = resolve_cn_etf_asset(symbol)
    _validate_symbol_matches_path(Path(input_path), asset.symbol)
    with _import_lock(output_root):
        raw = parse_tradingview_csv(input_path)
        if "amount" not in raw.columns:
            raw["amount"] = pd.to_numeric(raw["close"], errors="coerce") * pd.to_numeric(raw["volume"], errors="coerce")
        raw["adj_close"] = raw.get("adj_close", raw["close"])
        bars = normalize_ohlcv(raw, asset, source=source, frequency=frequency)
        validate_market_data(bars)
        written = _merge_write_processed_bars(bars, output_root, frequency)
        observed_dates = sorted(set(pd.to_datetime(bars["date"]).dt.date))
        report = build_quality_report(bars, expected_dates=observed_dates)
        report_path = output_root / "quality_report_cn_etf.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "source": source,
        "market": asset.market,
        "symbol": asset.symbol,
        "asset_id": asset.asset_id,
        "rows": int(len(bars)),
        "written": [str(path) for path in written],
        "quality_report": report,
    }


@contextmanager
def _import_lock(output_root: Path):
    lock_path = output_root / ".import_etf_csv.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError("ETF CSV import is already running for this output directory") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _validate_symbol_matches_path(input_path: Path, symbol: str) -> None:
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", input_path.stem)
    if match is None:
        return
    expected_code = symbol.split(".", 1)[0]
    if match.group(1) != expected_code:
        raise ValueError(f"CSV filename code {match.group(1)} does not match symbol {symbol}")


def _merge_write_processed_bars(bars: pd.DataFrame, output_root: Path, frequency: str) -> list[Path]:
    store = DatasetStore(output_root)
    written = []
    years = pd.to_datetime(bars["date"]).dt.year.astype(str)
    for year, year_bars in bars.groupby(years):
        partitions = {"frequency": frequency, "market": "CN_ETF", "year": str(year)}
        if store.exists("processed/bars", partitions):
            existing = store.read_frame("processed/bars", partitions)
            existing = existing[existing["asset_id"] != year_bars.iloc[0]["asset_id"]]
            year_bars = pd.concat([existing, year_bars], ignore_index=True)
        written.append(store.write_frame(year_bars, "processed/bars", partitions))
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Import a TradingView-exported A-share ETF CSV into local processed bars.")
    parser.add_argument("input")
    parser.add_argument("--symbol", required=True, help="ETF symbol such as 510300.SH or 159915.SZ")
    parser.add_argument("--output-dir", default="data/processed/etf_csv")
    parser.add_argument("--source", default="tradingview_csv")
    parser.add_argument("--frequency", default="1d")
    args = parser.parse_args()
    result = import_etf_csv(args.input, args.output_dir, args.symbol, args.source, args.frequency)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))


if __name__ == "__main__":
    main()
