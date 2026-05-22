from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.data.ingest.tushare_pipeline import run_tushare_daily_ingest
from quant_robot.data.normalize import normalize_ohlcv
from quant_robot.data.quality import validate_market_data
from quant_robot.data.quality_report import build_quality_report


def run_ingest(
    source: str,
    market: str,
    output_dir: Path | str,
    start_date: str = "2024-01-02",
    end_date: str = "2024-01-06",
) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if source == "tushare-fixture":
        return run_tushare_daily_ingest(_FixtureTushareAdapter(), start_date, end_date, output_path)
    if source == "tushare":
        return run_tushare_daily_ingest(TushareAdapter(), start_date, end_date, output_path)
    if source != "fixture":
        raise RuntimeError("Supported sources are fixture, tushare-fixture, and tushare")
    asset = _fixture_asset(market)
    raw = _fixture_raw_bars()
    bars = normalize_ohlcv(raw, asset, source="fixture", frequency="1d")
    validate_market_data(bars)
    report = build_quality_report(bars)
    bars.to_csv(output_path / "bars.csv", index=False)
    (output_path / "quality_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return {"source": source, "market": market, "rows": int(len(bars)), "quality_report": report}


class _FixtureTushareAdapter:
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.date_range(start_date, end_date, freq="D")
        return pd.DataFrame({"exchange": "SSE", "date": dates.date, "is_open": 1})

    def fetch_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        date = pd.to_datetime(trade_date, format="%Y%m%d")
        close = 10.0 + (date.day % 10) * 0.1
        return pd.DataFrame(
            {
                "symbol": ["000001.SZ", "600519.SH"],
                "date": [date.date(), date.date()],
                "open": [close * 0.99, close * 1.99],
                "high": [close * 1.02, close * 2.02],
                "low": [close * 0.98, close * 1.98],
                "close": [close, close * 2.0],
                "volume": [10000.0, 20000.0],
                "amount": [close * 10000.0, close * 40000.0],
            }
        )


def _fixture_asset(market: str) -> Asset:
    market_upper = market.upper()
    if market_upper == "CN":
        return Asset("CN_XSHE_000001", "000001.SZ", "CN", "XSHE", "stock", "CNY", "Asia/Shanghai", "XSHE")
    if market_upper == "US":
        return Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS")
    if market_upper == "HK":
        return Asset("HK_XHKG_0700", "0700.HK", "HK", "XHKG", "stock", "HKD", "Asia/Hong_Kong", "XHKG")
    if market_upper == "CRYPTO":
        return Asset("CRYPTO_BINANCE_BTC_USDT", "BTC/USDT", "CRYPTO", "BINANCE", "crypto_spot", "USDT", "UTC", "24/7")
    raise ValueError(f"Unsupported fixture market: {market}")


def _fixture_raw_bars() -> pd.DataFrame:
    closes = pd.Series([10.0, 10.2, 10.1, 10.5, 10.8], dtype=float)
    volume = pd.Series([1000, 1200, 1100, 1300, 1250], dtype=float)
    return pd.DataFrame(
        {
            "date": pd.date_range("2024-01-02", periods=5).date,
            "open": closes * 0.99,
            "high": closes * 1.02,
            "low": closes * 0.98,
            "close": closes,
            "adj_close": closes,
            "volume": volume,
            "amount": closes * volume,
        }
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest market data into the local research framework.")
    parser.add_argument("--source", default="fixture")
    parser.add_argument("--market", default="CN")
    parser.add_argument("--output-dir", default="data/processed/ingest_fixture")
    parser.add_argument("--start-date", default="2024-01-02")
    parser.add_argument("--end-date", default="2024-01-06")
    args = parser.parse_args()
    result = run_ingest(args.source, args.market, Path(args.output_dir), args.start_date, args.end_date)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
