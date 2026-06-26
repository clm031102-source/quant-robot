import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_stock_tradeability_mask_cache import build_cn_stock_tradeability_mask_cache


class CNStockTradeabilityMaskCacheTests(unittest.TestCase):
    def test_builds_year_partitioned_mask_cache_from_official_feeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "mask_cache"
            bars = pd.DataFrame(
                [
                    {
                        "date": "2025-01-02",
                        "asset_id": "CN_XSHE_000001",
                        "symbol": "000001.SZ",
                        "market": "CN",
                        "exchange": "XSHE",
                        "open": 10.0,
                        "high": 10.0,
                        "low": 10.0,
                        "close": 10.0,
                        "volume": 1000.0,
                        "amount": 10_000_000.0,
                    },
                    {
                        "date": "2025-01-03",
                        "asset_id": "CN_XSHE_000001",
                        "symbol": "000001.SZ",
                        "market": "CN",
                        "exchange": "XSHE",
                        "open": 10.0,
                        "high": 11.0,
                        "low": 10.5,
                        "close": 11.0,
                        "volume": 1000.0,
                        "amount": 11_000_000.0,
                    },
                ]
            )
            stk_limit = pd.DataFrame(
                [
                    {
                        "date": "2025-01-03",
                        "asset_id": "CN_XSHE_000001",
                        "up_limit": 11.0,
                        "down_limit": 9.0,
                    }
                ]
            )

            result = build_cn_stock_tradeability_mask_cache(
                bars=bars,
                stk_limit=stk_limit,
                output_root=output_root,
                market="CN",
            )

            self.assertEqual(result["stage"], "cn_stock_tradeability_mask_cache")
            self.assertEqual(result["summary"]["years"], [2025])
            self.assertEqual(result["summary"]["rows"], 2)
            self.assertEqual(result["summary"]["entry_blocked_rows"], 1)
            written = output_root / "processed" / "tradeability_masks" / "frequency=1d" / "market=CN" / "year=2025"
            self.assertTrue(any(written.glob("part-00000.*")))
            cached = pd.read_parquet(next(written.glob("*.parquet")))
            self.assertIn("entry_tradeable", cached.columns)
            self.assertFalse(bool(cached.loc[cached["date"].astype(str) == "2025-01-03", "entry_tradeable"].iloc[0]))

    def test_mask_cache_carries_stock_basic_metadata_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_root = Path(tmp) / "mask_cache"
            bars = pd.DataFrame(
                [
                    {
                        "date": "2024-04-29",
                        "asset_id": "CN_XSHE_000005",
                        "symbol": "000005.SZ",
                        "market": "CN",
                        "exchange": "XSHE",
                        "open": 1.0,
                        "high": 1.0,
                        "low": 1.0,
                        "close": 1.0,
                        "volume": 1000.0,
                        "amount": 1_000_000.0,
                    }
                ]
            )
            stock_basic = pd.DataFrame(
                [
                    {
                        "asset_id": "CN_XSHE_000005",
                        "symbol": "000005.SZ",
                        "name": "ST星源(退)",
                        "stock_market": "主板",
                        "exchange": "XSHE",
                        "list_date": "1990-12-10",
                        "delist_date": "2024-04-26",
                        "is_active": False,
                        "list_status": "D",
                    }
                ]
            )

            result = build_cn_stock_tradeability_mask_cache(
                bars=bars,
                stock_basic=stock_basic,
                output_root=output_root,
                market="CN",
            )

            self.assertTrue(result["summary"]["stock_basic_supplied"])
            self.assertEqual(result["summary"]["metadata_mask_hit_rows"], 1)
            self.assertEqual(result["summary"]["delisted_or_inactive_flag_rows"], 1)
            written = output_root / "processed" / "tradeability_masks" / "frequency=1d" / "market=CN" / "year=2024"
            cached = pd.read_parquet(next(written.glob("*.parquet")))
            self.assertIn("delisted_or_inactive_flag", cached.columns)
            self.assertTrue(bool(cached["delisted_or_inactive_flag"].iloc[0]))
            self.assertFalse(bool(cached["entry_tradeable"].iloc[0]))


if __name__ == "__main__":
    unittest.main()
