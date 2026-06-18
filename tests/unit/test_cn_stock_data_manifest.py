import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_stock_data_manifest import (
    build_cn_stock_data_manifest,
    validate_cn_stock_data_manifest_packet,
    write_cn_stock_data_manifest,
)


class CnStockDataManifestTests(unittest.TestCase):
    def test_manifest_summarizes_cn_stock_bars_and_moneyflow_inputs(self) -> None:
        bars = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03", "2024-01-02", "2024-01-03"],
                "asset_id": ["000001.SZ", "000001.SZ", "000002.SZ", "000002.SZ"],
                "symbol": ["000001.SZ", "000001.SZ", "000002.SZ", "000002.SZ"],
                "market": ["CN", "CN", "CN", "CN"],
                "asset_type": ["stock", "stock", "stock", "stock"],
                "adj_close": [10.0, 10.5, 20.0, 40.5],
                "volume": [1000, 0, 2000, 2100],
                "amount": [10000.0, 0.0, 20000.0, 22000.0],
            }
        )
        moneyflow = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "asset_id": ["000001.SZ", "000001.SZ"],
                "symbol": ["000001.SZ", "000001.SZ"],
                "market": ["CN", "CN"],
                "net_mf_amount": [100.0, 120.0],
            }
        )

        manifest = build_cn_stock_data_manifest(bars=bars, moneyflow_inputs=moneyflow, source_root=Path("data/processed/demo"))

        self.assertEqual(manifest["status"], "review_required")
        self.assertEqual(manifest["summary"]["bar_rows"], 4)
        self.assertEqual(manifest["summary"]["bar_symbols"], 2)
        self.assertEqual(manifest["summary"]["moneyflow_symbols"], 1)
        self.assertEqual(manifest["summary"]["date_start"], "2024-01-02")
        self.assertEqual(manifest["summary"]["date_end"], "2024-01-03")
        self.assertEqual(manifest["summary"]["bar_years"], [2024])
        self.assertEqual(manifest["summary"]["bar_trade_dates_by_year"], {"2024": 2})
        self.assertIn("zero_volume_rows_present", manifest["decision"]["warnings"])
        self.assertIn("extreme_return_rows_present", manifest["decision"]["warnings"])
        self.assertIn("moneyflow_symbol_coverage_below_bars", manifest["decision"]["warnings"])
        self.assertFalse(manifest["live_boundary_allowed"])

    def test_manifest_blocks_non_cn_or_non_stock_bars(self) -> None:
        bars = pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "asset_id": ["510300.SH"],
                "symbol": ["510300.SH"],
                "market": ["CN_ETF"],
                "asset_type": ["etf"],
                "adj_close": [4.0],
                "volume": [1000],
                "amount": [4000.0],
            }
        )

        manifest = build_cn_stock_data_manifest(bars=bars, moneyflow_inputs=None, source_root=Path("data/processed/demo"))

        self.assertEqual(manifest["status"], "blocked")
        self.assertIn("non_cn_rows_present", manifest["decision"]["blockers"])
        self.assertIn("non_stock_rows_present", manifest["decision"]["blockers"])

    def test_write_manifest_outputs_json_markdown_and_symbol_coverage(self) -> None:
        manifest = build_cn_stock_data_manifest(
            bars=pd.DataFrame(
                {
                    "date": ["2024-01-02"],
                    "asset_id": ["000001.SZ"],
                    "symbol": ["000001.SZ"],
                    "market": ["CN"],
                    "asset_type": ["stock"],
                    "adj_close": [10.0],
                    "volume": [1000],
                    "amount": [10000.0],
                }
            ),
            moneyflow_inputs=None,
            source_root=Path("data/processed/demo"),
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_cn_stock_data_manifest(Path(tmp), manifest)

            self.assertTrue((Path(tmp) / "cn_stock_data_manifest.json").exists())
            self.assertTrue((Path(tmp) / "cn_stock_data_manifest.md").exists())
            self.assertTrue((Path(tmp) / "cn_stock_symbol_coverage.csv").exists())

    def test_validate_manifest_accepts_cleared_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_stock_data_manifest.json"
            path.write_text(
                """{
                  "generated_at": "%s",
                  "status": "cleared",
                  "summary": {"source_root": "data/processed/demo", "bar_rows": 10, "bar_symbols": 2},
                  "decision": {"data_manifest_cleared": true, "blockers": [], "warnings": []},
                  "live_boundary_allowed": false
                }"""
                % date.today().isoformat(),
                encoding="utf-8",
            )

            packet = validate_cn_stock_data_manifest_packet(path, expected_source_root=Path("data/processed/demo"))

        self.assertEqual(packet["status"], "cleared")

    def test_validate_manifest_blocks_review_required_without_explicit_ack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_stock_data_manifest.json"
            path.write_text(
                """{
                  "generated_at": "%s",
                  "status": "review_required",
                  "summary": {"source_root": "data/processed/demo", "bar_rows": 10, "bar_symbols": 2},
                  "decision": {"data_manifest_cleared": false, "blockers": [], "warnings": ["moneyflow_inputs_missing"]},
                  "live_boundary_allowed": false
                }"""
                % date.today().isoformat(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "review required"):
                validate_cn_stock_data_manifest_packet(path)

            packet = validate_cn_stock_data_manifest_packet(path, allow_review_required=True)

        self.assertEqual(packet["status"], "review_required")

    def test_validate_manifest_rejects_blocked_or_mismatched_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_stock_data_manifest.json"
            path.write_text(
                """{
                  "generated_at": "%s",
                  "status": "blocked",
                  "summary": {"source_root": "data/processed/demo", "bar_rows": 0, "bar_symbols": 0},
                  "decision": {"data_manifest_cleared": false, "blockers": ["bars_missing"], "warnings": []},
                  "live_boundary_allowed": false
                }"""
                % date.today().isoformat(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "blocked"):
                validate_cn_stock_data_manifest_packet(path)

    def test_validate_manifest_rejects_stale_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cn_stock_data_manifest.json"
            path.write_text(
                """{
                  "generated_at": "%s",
                  "status": "cleared",
                  "summary": {"source_root": "data/processed/demo", "bar_rows": 10, "bar_symbols": 2},
                  "decision": {"data_manifest_cleared": true, "blockers": [], "warnings": []},
                  "live_boundary_allowed": false
                }"""
                % (date.today() - timedelta(days=1)).isoformat(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "generated today"):
                validate_cn_stock_data_manifest_packet(path)


if __name__ == "__main__":
    unittest.main()
