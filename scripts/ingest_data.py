from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.tushare_adapter import TushareAdapter
from quant_robot.data.ingest.tushare_factor_inputs import run_tushare_daily_basic_ingest
from quant_robot.data.ingest.tushare_financial_inputs import run_tushare_fina_indicator_ingest
from quant_robot.data.ingest.tushare_moneyflow_inputs import run_tushare_moneyflow_ingest
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
    symbols: list[str] | None = None,
) -> dict[str, object]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if source == "tushare-fixture":
        return run_tushare_daily_ingest(_FixtureTushareAdapter(), start_date, end_date, output_path, market=market)
    if source == "tushare":
        return run_tushare_daily_ingest(TushareAdapter(), start_date, end_date, output_path, market=market)
    if source == "tushare-factor-fixture":
        return run_tushare_daily_basic_ingest(_FixtureTushareAdapter(), start_date, end_date, output_path, market=market)
    if source == "tushare-factor":
        return run_tushare_daily_basic_ingest(TushareAdapter(), start_date, end_date, output_path, market=market)
    if source == "tushare-moneyflow-fixture":
        return run_tushare_moneyflow_ingest(_FixtureTushareAdapter(), start_date, end_date, output_path, market=market)
    if source == "tushare-moneyflow":
        return run_tushare_moneyflow_ingest(TushareAdapter(), start_date, end_date, output_path, market=market)
    if source == "tushare-fina-indicator-fixture":
        return run_tushare_fina_indicator_ingest(
            _FixtureTushareAdapter(),
            _quarter_end_periods(start_date, end_date),
            output_path,
            market=market,
            ts_codes=symbols,
        )
    if source == "tushare-fina-indicator":
        return run_tushare_fina_indicator_ingest(
            TushareAdapter(),
            _quarter_end_periods(start_date, end_date),
            output_path,
            market=market,
            ts_codes=symbols or _default_financial_smoke_symbols(),
        )
    if source != "fixture":
        raise RuntimeError(
            "Supported sources are fixture, tushare-fixture, tushare, "
            "tushare-factor-fixture, tushare-factor, tushare-moneyflow-fixture, "
            "tushare-moneyflow, tushare-fina-indicator-fixture, and tushare-fina-indicator"
        )
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

    def fetch_etf_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        date = pd.to_datetime(trade_date, format="%Y%m%d")
        close = 4.0 + (date.day % 10) * 0.02
        return pd.DataFrame(
            {
                "symbol": ["510300.SH", "159915.SZ"],
                "date": [date.date(), date.date()],
                "open": [close * 0.99, close * 0.79],
                "high": [close * 1.02, close * 0.82],
                "low": [close * 0.98, close * 0.78],
                "close": [close, close * 0.8],
                "volume": [100000.0, 200000.0],
                "amount": [close * 100000.0, close * 0.8 * 200000.0],
            }
        )

    def fetch_daily_basic_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        date = pd.to_datetime(trade_date, format="%Y%m%d").date()
        return pd.DataFrame(
            {
                "symbol": ["000001.SZ", "600519.SH"],
                "date": [date, date],
                "turnover_rate": [1.0, 0.5],
                "turnover_rate_f": [1.2, 0.6],
                "volume_ratio": [1.1, 0.9],
                "pe": [8.0, 30.0],
                "pe_ttm": [7.5, 28.0],
                "pb": [0.8, 10.0],
                "ps": [1.2, 15.0],
                "ps_ttm": [1.1, 14.0],
                "dv_ratio": [3.0, 1.5],
                "dv_ttm": [3.2, 1.6],
                "total_share": [1000.0, 2000.0],
                "float_share": [800.0, 1200.0],
                "free_share": [600.0, 1000.0],
                "total_mv": [120000.0, 300000.0],
                "circ_mv": [90000.0, 200000.0],
            }
        )

    def fetch_moneyflow_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        date = pd.to_datetime(trade_date, format="%Y%m%d").date()
        return pd.DataFrame(
            {
                "symbol": ["000001.SZ", "600519.SH"],
                "date": [date, date],
                "buy_sm_vol": [10.0, 11.0],
                "buy_sm_amount": [100.0, 110.0],
                "sell_sm_vol": [8.0, 9.0],
                "sell_sm_amount": [80.0, 90.0],
                "buy_md_vol": [30.0, 31.0],
                "buy_md_amount": [300.0, 310.0],
                "sell_md_vol": [25.0, 26.0],
                "sell_md_amount": [250.0, 260.0],
                "buy_lg_vol": [50.0, 51.0],
                "buy_lg_amount": [500.0, 510.0],
                "sell_lg_vol": [45.0, 46.0],
                "sell_lg_amount": [450.0, 460.0],
                "buy_elg_vol": [70.0, 71.0],
                "buy_elg_amount": [700.0, 710.0],
                "sell_elg_vol": [65.0, 66.0],
                "sell_elg_amount": [650.0, 660.0],
                "net_mf_vol": [12.0, 13.0],
                "net_mf_amount": [120.0, 130.0],
            }
        )

    def fetch_fina_indicator(self, period: str, ts_code: str = "") -> pd.DataFrame:
        period_date = pd.to_datetime(period, format="%Y%m%d").date()
        ann_date = (pd.Timestamp(period_date) + pd.Timedelta(days=25)).date()
        symbols = [ts_code] if ts_code else ["000001.SZ", "600519.SH"]
        return pd.DataFrame(
            {
                "symbol": symbols,
                "ann_date": [ann_date] * len(symbols),
                "end_date": [period_date] * len(symbols),
                "roe": [11.2 + index for index, _ in enumerate(symbols)],
                "roa": [0.92 + index for index, _ in enumerate(symbols)],
                "grossprofit_margin": [28.5 + index for index, _ in enumerate(symbols)],
                "netprofit_margin": [12.3 + index for index, _ in enumerate(symbols)],
                "netprofit_yoy": [8.7 + index for index, _ in enumerate(symbols)],
                "or_yoy": [6.5 + index for index, _ in enumerate(symbols)],
                "ocfps": [1.24 + index for index, _ in enumerate(symbols)],
                "cfps": [1.8 + index for index, _ in enumerate(symbols)],
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


def _quarter_end_periods(start_date: str, end_date: str) -> list[str]:
    quarters = pd.period_range(start=pd.to_datetime(start_date), end=pd.to_datetime(end_date), freq="Q")
    return [period.end_time.strftime("%Y%m%d") for period in quarters]


def _default_financial_smoke_symbols() -> list[str]:
    return ["000001.SZ"]


def _parse_symbols(value: str) -> list[str] | None:
    symbols = [item.strip() for item in value.split(",") if item.strip()]
    return symbols or None


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
    parser.add_argument("--symbols", default="", help="Comma-separated symbols for symbol-scoped financial ingests.")
    args = parser.parse_args()
    result = run_ingest(
        args.source,
        args.market,
        Path(args.output_dir),
        args.start_date,
        args.end_date,
        symbols=_parse_symbols(args.symbols),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
