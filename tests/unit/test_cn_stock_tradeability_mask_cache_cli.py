import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_cn_stock_tradeability_mask_cache import run_cn_stock_tradeability_mask_cache_cli


class CNStockTradeabilityMaskCacheCliTests(unittest.TestCase):
    def test_cli_reads_only_requested_year_and_writes_mask_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bars"
            official = Path(tmp) / "official"
            output_root = Path(tmp) / "cache"
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
                        "adj_close": 10.0,
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
                        "adj_close": 11.0,
                        "volume": 1000.0,
                        "amount": 11_000_000.0,
                    },
                ]
            )
            DatasetStore(root).write_frame(bars, "processed/bars", {"frequency": "1d", "market": "CN", "year": "2025"})
            DatasetStore(official).write_frame(
                pd.DataFrame(
                    [
                        {
                            "date": "2025-01-03",
                            "asset_id": "CN_XSHE_000001",
                            "up_limit": 11.0,
                            "down_limit": 9.0,
                        }
                    ]
                ),
                "processed/tradeability_stk_limit",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_cn_stock_tradeability_mask_cache_cli(
                bars_path=root,
                stk_limit_path=official,
                output_root=output_root,
                years=(2025,),
            )

            self.assertEqual(result["summary"]["years"], [2025])
            self.assertEqual(result["summary"]["entry_blocked_rows"], 1)
            self.assertTrue(
                (output_root / "processed" / "tradeability_masks" / "frequency=1d" / "market=CN" / "year=2025").exists()
            )

    def test_cli_markdown_report_summarizes_all_requested_years(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "bars"
            output_root = Path(tmp) / "cache"
            bars = pd.DataFrame(
                [
                    {
                        "date": "2024-01-02",
                        "asset_id": "CN_XSHE_000001",
                        "symbol": "000001.SZ",
                        "market": "CN",
                        "exchange": "XSHE",
                        "open": 10.0,
                        "high": 10.2,
                        "low": 9.8,
                        "close": 10.0,
                        "adj_close": 10.0,
                        "volume": 1000.0,
                        "amount": 10_000_000.0,
                    },
                    {
                        "date": "2025-01-02",
                        "asset_id": "CN_XSHE_000001",
                        "symbol": "000001.SZ",
                        "market": "CN",
                        "exchange": "XSHE",
                        "open": 10.0,
                        "high": 10.2,
                        "low": 9.8,
                        "close": 10.0,
                        "adj_close": 10.0,
                        "volume": 1000.0,
                        "amount": 10_000_000.0,
                    },
                ]
            )
            store = DatasetStore(root)
            store.write_frame(
                bars.iloc[[0]],
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            store.write_frame(
                bars.iloc[[1]],
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            run_cn_stock_tradeability_mask_cache_cli(
                bars_path=root,
                output_root=output_root,
                years=(2024, 2025),
            )

            markdown = (output_root / "cn_stock_tradeability_mask_cache.md").read_text(encoding="utf-8")
            self.assertIn("- Years: [2024, 2025]", markdown)
            self.assertIn("- Rows: 2", markdown)

    def test_cli_merges_multiple_bars_roots_for_split_year_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            first_root = Path(tmp) / "bars_first"
            second_root = Path(tmp) / "bars_second"
            output_root = Path(tmp) / "cache"
            first_rows = pd.DataFrame(
                [
                    _bar("2023-07-03", 10.0),
                    _bar("2023-07-04", 10.1),
                ]
            )
            second_rows = pd.DataFrame(
                [
                    _bar("2023-07-04", 10.2),
                    _bar("2023-07-05", 10.3),
                ]
            )
            DatasetStore(first_root).write_frame(
                first_rows,
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2023"},
            )
            DatasetStore(second_root).write_frame(
                second_rows,
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2023"},
            )

            result = run_cn_stock_tradeability_mask_cache_cli(
                bars_path=(first_root, second_root),
                output_root=output_root,
                years=(2023,),
            )

            self.assertEqual(result["summary"]["rows"], 3)
            cached_path = output_root / "processed" / "tradeability_masks" / "frequency=1d" / "market=CN" / "year=2023"
            cached = pd.read_parquet(next(cached_path.glob("*.parquet")))
            self.assertEqual(sorted(cached["date"].astype(str).tolist()), ["2023-07-03", "2023-07-04", "2023-07-05"])

    def test_cli_keeps_prior_year_namechange_interval_active_in_requested_year(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars_root = Path(tmp) / "bars"
            official_root = Path(tmp) / "official"
            output_root = Path(tmp) / "cache"
            DatasetStore(bars_root).write_frame(
                pd.DataFrame([_bar("2025-01-03", 10.0)]),
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store = DatasetStore(official_root)
            store.write_frame(
                pd.DataFrame(
                    [
                        {
                            "asset_id": "CN_XSHE_000001",
                            "start_date": "2024-12-20",
                            "end_date": "2025-01-10",
                            "name": "*ST测试",
                        }
                    ]
                ),
                "processed/tradeability_namechange",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            store.write_frame(
                pd.DataFrame(
                    [
                        {
                            "asset_id": "CN_XSHE_000002",
                            "start_date": "2025-02-01",
                            "end_date": "2025-02-10",
                            "name": "*ST无关",
                        }
                    ]
                ),
                "processed/tradeability_namechange",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_cn_stock_tradeability_mask_cache_cli(
                bars_path=bars_root,
                namechange_path=official_root,
                output_root=output_root,
                years=(2025,),
            )

            self.assertEqual(result["summary"]["official_mask_hit_rows"], 1)
            cached_path = output_root / "processed" / "tradeability_masks" / "frequency=1d" / "market=CN" / "year=2025"
            cached = pd.read_parquet(next(cached_path.glob("*.parquet")))
            self.assertTrue(bool(cached["st_flag_official"].iloc[0]))
            self.assertFalse(bool(cached["entry_tradeable"].iloc[0]))

    def test_cli_stock_basic_path_blocks_delisted_rows_in_requested_year(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars_root = Path(tmp) / "bars"
            metadata_root = Path(tmp) / "metadata"
            output_root = Path(tmp) / "cache"
            DatasetStore(bars_root).write_frame(
                pd.DataFrame(
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
                            "adj_close": 1.0,
                            "volume": 1000.0,
                            "amount": 1_000_000.0,
                        }
                    ]
                ),
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            DatasetStore(metadata_root).write_frame(
                pd.DataFrame(
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
                ),
                "metadata/tushare_stock_basic",
                {"list_status": "D", "snapshot": "2026-06-23"},
            )

            result = run_cn_stock_tradeability_mask_cache_cli(
                bars_path=bars_root,
                stock_basic_path=metadata_root,
                output_root=output_root,
                years=(2024,),
            )

            self.assertTrue(result["summary"]["stock_basic_supplied_for_all_years"])
            self.assertEqual(result["summary"]["metadata_mask_hit_rows"], 1)
            cached_path = output_root / "processed" / "tradeability_masks" / "frequency=1d" / "market=CN" / "year=2024"
            cached = pd.read_parquet(next(cached_path.glob("*.parquet")))
            self.assertTrue(bool(cached["delisted_or_inactive_flag"].iloc[0]))
            self.assertFalse(bool(cached["entry_tradeable"].iloc[0]))
            markdown = (output_root / "cn_stock_tradeability_mask_cache.md").read_text(encoding="utf-8")
            self.assertIn("- Stock basic supplied: True", markdown)

def _bar(date: str, close: float) -> dict[str, object]:
    return {
        "date": date,
        "asset_id": "CN_XSHE_000001",
        "symbol": "000001.SZ",
        "market": "CN",
        "exchange": "XSHE",
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "adj_close": close,
        "volume": 1000.0,
        "amount": close * 1000.0,
    }


if __name__ == "__main__":
    unittest.main()
