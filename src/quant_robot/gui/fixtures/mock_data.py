from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from quant_robot.assets.etf_universe import default_cn_etf_assets
from quant_robot.assets.models import Asset
from quant_robot.data.normalize import normalize_ohlcv

DATA_MODE = "demo_fixture"
DEMO_NOTICE = "Demo fixture data only. No broker account, no live trading, no order placement."


def demo_strategies() -> list[dict[str, object]]:
    return [
        {
            "name": "Multi-market momentum research",
            "markets": ["CN", "CN_ETF", "HK", "US", "CRYPTO"],
            "factor": "momentum_2",
            "status": "demo",
        },
        {
            "name": "ETF liquidity reversal sandbox",
            "markets": ["CN_ETF"],
            "factor": "reversal_3",
            "status": "demo",
        },
    ]


def market_statuses() -> list[dict[str, object]]:
    return [
        _market("CN", "A-shares", "AKShare / Tushare", "2026-05-22 09:30 CST", 24, 0, 0, "fixture-ready"),
        _market("CN_ETF", "A-share ETFs", "TradingView CSV / AKShare / Tushare", "2026-05-22 09:30 CST", 48, 0, 0, "fixture-ready"),
        _market("HK", "Hong Kong stocks", "yfinance / AKShare", "2026-05-22 09:30 HKT", 24, 0, 1, "fixture-ready"),
        _market("US", "US stocks", "yfinance", "2026-05-21 16:00 ET", 24, 0, 0, "fixture-ready"),
        _market("CRYPTO", "Crypto spot", "ccxt", "2026-05-22 00:00 UTC", 24, 0, 0, "fixture-ready"),
    ]


def risk_snapshot() -> dict[str, object]:
    return {
        "account_connected": False,
        "volatility": 0.142,
        "max_drawdown": -0.036,
        "var_95": -0.018,
        "gross_exposure": 1.0,
        "net_exposure": 1.0,
        "loss_streak": 2,
        "anomalies": [
            {"level": "info", "message": "Risk monitor is using demo fixture outputs."},
            {"level": "warn", "message": "No live account, cash, or margin data is connected."},
        ],
    }


def task_logs() -> dict[str, list[dict[str, str]]]:
    return {
        "research": [
            {"time": "2026-05-22 09:10", "level": "info", "message": "Loaded demo multi-market fixture."},
            {"time": "2026-05-22 09:11", "level": "info", "message": "Computed IC, Rank IC, groups, and long-short returns."},
        ],
        "backtest": [
            {"time": "2026-05-22 09:12", "level": "info", "message": "Ran next-date research backtest on demo data."},
            {"time": "2026-05-22 09:12", "level": "warn", "message": "Metrics are not live performance and are not investment advice."},
        ],
        "errors": [],
    }


def report_entries() -> list[dict[str, str]]:
    return [
        {"name": "Demo metrics JSON", "path": "data/reports/gui_demo/metrics.json", "kind": "json"},
        {"name": "Demo equity curve CSV", "path": "data/reports/gui_demo/equity_curve.csv", "kind": "csv"},
        {"name": "Demo IC CSV", "path": "data/reports/gui_demo/ic.csv", "kind": "csv"},
    ]


def demo_assets() -> list[Asset]:
    return [
        Asset("CN_XSHG_600519", "600519.SH", "CN", "XSHG", "stock", "CNY", "Asia/Shanghai", "XSHG"),
        Asset("CN_XSHE_000001", "000001.SZ", "CN", "XSHE", "stock", "CNY", "Asia/Shanghai", "XSHE"),
        Asset("HK_XHKG_0700", "0700.HK", "HK", "XHKG", "stock", "HKD", "Asia/Hong_Kong", "XHKG"),
        Asset("HK_XHKG_0005", "0005.HK", "HK", "XHKG", "stock", "HKD", "Asia/Hong_Kong", "XHKG"),
        Asset("US_XNAS_AAPL", "AAPL", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS"),
        Asset("US_XNAS_MSFT", "MSFT", "US", "XNAS", "stock", "USD", "America/New_York", "XNYS"),
        Asset("CRYPTO_BINANCE_BTC_USDT", "BTC/USDT", "CRYPTO", "BINANCE", "crypto_spot", "USDT", "UTC", "24/7"),
        Asset("CRYPTO_BINANCE_ETH_USDT", "ETH/USDT", "CRYPTO", "BINANCE", "crypto_spot", "USDT", "UTC", "24/7"),
        *default_cn_etf_assets()[:4],
    ]


def demo_bars() -> pd.DataFrame:
    frames = [normalize_ohlcv(_raw_bars(asset), asset, "demo_fixture", "1d") for asset in demo_assets()]
    return pd.concat(frames, ignore_index=True)


def serialized_assets() -> list[dict[str, object]]:
    return [asdict(asset) for asset in demo_assets()]


def _market(
    market: str,
    label: str,
    source: str,
    updated_at: str,
    rows: int,
    missing_values: int,
    anomalies: int,
    status: str,
) -> dict[str, object]:
    return {
        "market": market,
        "label": label,
        "source": source,
        "updated_at": updated_at,
        "rows": rows,
        "missing_values": missing_values,
        "anomalies": anomalies,
        "status": status,
        "data_mode": DATA_MODE,
    }


def _raw_bars(asset: Asset) -> pd.DataFrame:
    dates = pd.date_range("2024-01-02", periods=12, freq="D")
    prices = pd.Series(_price_path(asset.asset_id), dtype=float)
    volume = pd.Series([1000, 1150, 980, 1210, 1320, 1260, 1410, 1380, 1500, 1460, 1580, 1640], dtype=float)
    amount = prices * volume
    return pd.DataFrame(
        {
            "date": dates.date,
            "open": prices * 0.992,
            "high": prices * 1.018,
            "low": prices * 0.982,
            "close": prices,
            "adj_close": prices,
            "volume": volume,
            "amount": amount,
        }
    )


def _price_path(asset_id: str) -> list[float]:
    paths = {
        "CN_XSHG_600519": [100, 101, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111],
        "CN_XSHE_000001": [20, 19.8, 20.3, 20.7, 20.1, 20.8, 21.2, 21.1, 21.6, 21.9, 22.0, 22.5],
        "HK_XHKG_0700": [50, 50.5, 49.8, 51.2, 52, 51.6, 53, 54, 53.5, 55, 55.6, 56],
        "HK_XHKG_0005": [38, 37.7, 38.1, 38.3, 38.0, 38.6, 39.1, 38.8, 39.4, 39.7, 39.3, 40.0],
        "US_XNAS_AAPL": [200, 202, 204, 203, 207, 211, 213, 214, 218, 220, 219, 224],
        "US_XNAS_MSFT": [310, 311, 314, 313, 316, 320, 322, 321, 325, 327, 330, 333],
        "CRYPTO_BINANCE_BTC_USDT": [30000, 30300, 30100, 30900, 31500, 31200, 31800, 33000, 32600, 33400, 34100, 33600],
        "CRYPTO_BINANCE_ETH_USDT": [2200, 2250, 2230, 2310, 2360, 2330, 2410, 2460, 2430, 2510, 2580, 2550],
        "CN_ETF_XSHG_510300": [3.50, 3.53, 3.55, 3.51, 3.60, 3.66, 3.64, 3.70, 3.76, 3.73, 3.80, 3.86],
        "CN_ETF_XSHG_510500": [5.20, 5.16, 5.25, 5.31, 5.28, 5.37, 5.44, 5.41, 5.50, 5.58, 5.55, 5.64],
        "CN_ETF_XSHE_159915": [2.10, 2.13, 2.09, 2.16, 2.22, 2.18, 2.25, 2.31, 2.28, 2.35, 2.42, 2.38],
        "CN_ETF_XSHG_588000": [1.02, 1.01, 1.04, 1.07, 1.05, 1.09, 1.12, 1.10, 1.14, 1.18, 1.16, 1.20],
    }
    return paths[asset_id]
