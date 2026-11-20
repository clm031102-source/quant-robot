from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from quant_robot.assets.universe import resolve_asset
from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.data.quality import validate_market_data
from quant_robot.data.updater import update_universe_cache
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.storage.market_cache import MarketCache
from quant_robot.storage.parquet_store import ParquetStore


def _make_raw_bars(symbol: str, start: str, n_days: int, base: float = 10.0, adj_mult: float = 1.0) -> pd.DataFrame:
    d0 = pd.to_datetime(start).date()
    rows = []
    px = base
    for i in range(n_days):
        d = d0 + timedelta(days=i)
        px = round(px * (1.0 + 0.002 * ((i % 5) - 1.5)), 4)
        rows.append(
            {
                "date": d,
                "open": round(px * 0.998, 4),
                "high": round(px * 1.01, 4),
                "low": round(px * 0.99, 4),
                "close": px,
                "adj_close": round(px * adj_mult, 4),
                "volume": 100000.0,
                "amount": px * 100000.0,
                "source": "mock",
            }
        )
    return pd.DataFrame(rows)


class CoreDataTests(unittest.TestCase):
    def test_resolve_assets_for_cn_and_us_etf(self) -> None:
        cn = resolve_asset("510300", "CN_ETF")
        self.assertEqual(cn.symbol, "510300.SH")
        self.assertEqual(cn.lot_size, 100.0)
        self.assertEqual(cn.currency, "CNY")

        sz = resolve_asset("159915", "CN_ETF")
        self.assertEqual(sz.symbol, "159915.SZ")

        us = resolve_asset("spym", "US_ETF")
        self.assertEqual(us.symbol, "SPYM")
        self.assertEqual(us.lot_size, 1.0)
        self.assertEqual(us.currency, "USD")

    def test_demo_fixtures_validate_and_compute_factors(self) -> None:
        bars = load_demo_market_bars()
        validate_market_data(bars)
        factors = compute_basic_factors(bars, windows=(2, 3), factor_names=("momentum_2", "volatility_3"))
        self.assertFalse(factors.empty)
        self.assertSetEqual(set(factors["factor_name"].unique()), {"momentum_2", "volatility_3"})

    def test_parquet_store_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = ParquetStore(tmp)
            df = pd.DataFrame({"date": [date(2026, 1, 2)], "asset_id": ["A"], "val": [1.5]})
            store.write_dataset(df, "sample")
            loaded = store.read_dataset("sample")
            self.assertEqual(len(loaded), 1)
            self.assertAlmostEqual(float(loaded["val"].iloc[0]), 1.5)

    def test_market_cache_incremental_upsert_and_split_auto_refresh(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = MarketCache(Path(tmp) / "cache")
            calls: list[tuple[str, str]] = []

            def fake_fetcher(market: str, symbol: str, *, start_date: str, end_date: str) -> pd.DataFrame:
                calls.append((start_date, end_date))
                # First run returns 20 days at adj_mult=1.0; second run simulates dividend shift adj_mult=0.95
                if len(calls) == 1:
                    return _make_raw_bars(symbol, "2026-01-01", 20, base=10.0, adj_mult=1.0)
                return _make_raw_bars(symbol, start_date, 30, base=10.0, adj_mult=0.95)

            r1 = update_universe_cache(cache, "US_ETF", ["SPYM"], default_start="2026-01-01", end_date="2026-01-20", fetcher=fake_fetcher)
            self.assertEqual(r1["ok_count"], 1)
            self.assertEqual(len(cache.load_symbol("US_ETF", "SPYM")), 20)

            # Second update detects adj_close shift on overlap and triggers full refresh from default_start
            r2 = update_universe_cache(cache, "US_ETF", ["SPYM"], default_start="2026-01-01", end_date="2026-01-30", fetcher=fake_fetcher)
            self.assertEqual(r2["ok_count"], 1)
            self.assertEqual(len(calls), 3)  # initial + incremental + auto full refresh
            self.assertEqual(calls[-1][0], "2026-01-01")

    def test_updater_gracefully_uses_cache_on_network_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = MarketCache(Path(tmp) / "cache")
            cache.upsert_symbol("US_ETF", "SPYM", _make_raw_bars("SPYM", "2026-01-01", 10))

            def failing_fetcher(*args, **kwargs):
                raise RuntimeError("transient timeout")

            rep = update_universe_cache(cache, "US_ETF", ["SPYM"], end_date="2026-01-15", fetcher=failing_fetcher)
            self.assertEqual(rep["error_count"], 1)
            self.assertEqual(rep["symbols"][0]["status"], "error_using_cache")
            self.assertEqual(rep["symbols"][0]["total_rows"], 10)


if __name__ == "__main__":
    unittest.main()
