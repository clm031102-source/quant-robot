from __future__ import annotations

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.normalize import normalize_ohlcv


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
    ]


def load_demo_market_bars() -> pd.DataFrame:
    frames = [normalize_ohlcv(_raw_bars(asset), asset, "fixture", "1d") for asset in demo_assets()]
    return pd.concat(frames, ignore_index=True).sort_values(["asset_id", "date"]).reset_index(drop=True)


def _raw_bars(asset: Asset) -> pd.DataFrame:
    dates = pd.date_range("2024-01-02", periods=14, freq="D")
    prices = pd.Series(_price_path(asset.asset_id), dtype=float)
    volume = pd.Series(
        [1000, 1150, 980, 1210, 1320, 1260, 1410, 1380, 1500, 1460, 1580, 1640, 1700, 1680],
        dtype=float,
    )
    return pd.DataFrame(
        {
            "date": dates.date,
            "open": prices * 0.992,
            "high": prices * 1.018,
            "low": prices * 0.982,
            "close": prices,
            "adj_close": prices,
            "volume": volume,
            "amount": prices * volume,
        }
    )


def _price_path(asset_id: str) -> list[float]:
    paths = {
        "CN_XSHG_600519": [100, 101, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112],
        "CN_XSHE_000001": [20, 19.8, 20.3, 20.7, 20.1, 20.8, 21.2, 21.1, 21.6, 21.9, 22.0, 22.5, 22.3, 22.8],
        "HK_XHKG_0700": [50, 50.5, 49.8, 51.2, 52, 51.6, 53, 54, 53.5, 55, 55.6, 56, 55.2, 56.4],
        "HK_XHKG_0005": [38, 37.7, 38.1, 38.3, 38.0, 38.6, 39.1, 38.8, 39.4, 39.7, 39.3, 40.0, 40.2, 40.5],
        "US_XNAS_AAPL": [200, 202, 204, 203, 207, 211, 213, 214, 218, 220, 219, 224, 226, 225],
        "US_XNAS_MSFT": [310, 311, 314, 313, 316, 320, 322, 321, 325, 327, 330, 333, 331, 335],
        "CRYPTO_BINANCE_BTC_USDT": [
            30000,
            30300,
            30100,
            30900,
            31500,
            31200,
            31800,
            33000,
            32600,
            33400,
            34100,
            33600,
            34400,
            35200,
        ],
        "CRYPTO_BINANCE_ETH_USDT": [2200, 2250, 2230, 2310, 2360, 2330, 2410, 2460, 2430, 2510, 2580, 2550, 2630, 2670],
    }
    return paths[asset_id]
