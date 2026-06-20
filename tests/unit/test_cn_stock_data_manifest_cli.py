import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_cn_stock_data_manifest import run_cn_stock_data_manifest
from quant_robot.storage.dataset_store import DatasetStore


class CnStockDataManifestCliTests(unittest.TestCase):
    def test_cli_runner_loads_cn_bars_and_moneyflow_then_writes_manifest(self) -> None:
        bars = pd.DataFrame(
            {
                "date": ["2024-01-02", "2024-01-03"],
                "asset_id": ["000001.SZ", "000001.SZ"],
                "symbol": ["000001.SZ", "000001.SZ"],
                "market": ["CN", "CN"],
                "asset_type": ["stock", "stock"],
                "adj_close": [10.0, 10.1],
                "volume": [1000, 1100],
                "amount": [10000.0, 11100.0],
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

        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.run_cn_stock_data_manifest.load_processed_bars", return_value=bars) as load_bars:
                with patch("scripts.run_cn_stock_data_manifest.load_moneyflow_inputs", return_value=moneyflow) as load_moneyflow:
                    manifest = run_cn_stock_data_manifest(data_root=Path("data/processed/demo"), output_dir=Path(tmp))
            self.assertTrue((Path(tmp) / "cn_stock_data_manifest.json").exists())
            self.assertTrue((Path(tmp) / "cn_stock_data_manifest.md").exists())

        load_bars.assert_called_once_with(Path("data/processed/demo"), "CN")
        load_moneyflow.assert_called_once_with(Path("data/processed/demo"), "CN")
        self.assertEqual(manifest["status"], "cleared")

    def test_cli_runner_keeps_missing_moneyflow_as_review_warning(self) -> None:
        bars = pd.DataFrame(
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
        )

        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.run_cn_stock_data_manifest.load_processed_bars", return_value=bars):
                with patch(
                    "scripts.run_cn_stock_data_manifest.load_moneyflow_inputs",
                    side_effect=FileNotFoundError("missing moneyflow"),
                ):
                    manifest = run_cn_stock_data_manifest(data_root=Path("data/processed/demo"), output_dir=Path(tmp))

        self.assertEqual(manifest["status"], "review_required")
        self.assertIn("moneyflow_inputs_missing", manifest["decision"]["warnings"])

    def test_cli_runner_accepts_authority_bars_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "store"
            output_dir = root / "manifest"
            bars = pd.DataFrame(
                {
                    "asset_id": ["000001.SZ", "000001.SZ"],
                    "symbol": ["000001.SZ", "000001.SZ"],
                    "market": ["CN", "CN"],
                    "exchange": ["XSHE", "XSHE"],
                    "asset_type": ["stock", "stock"],
                    "frequency": ["1d", "1d"],
                    "source": ["fixture", "fixture"],
                    "date": ["2024-01-02", "2024-01-03"],
                    "timestamp": ["2024-01-02T08:00:00Z", "2024-01-03T08:00:00Z"],
                    "timezone": ["Asia/Shanghai", "Asia/Shanghai"],
                    "calendar": ["XSHG", "XSHG"],
                    "open": [10.0, 10.1],
                    "high": [10.2, 10.3],
                    "low": [9.9, 10.0],
                    "close": [10.1, 10.2],
                    "adj_close": [10.1, 10.2],
                    "volume": [1000, 1100],
                    "amount": [10100.0, 11220.0],
                    "vwap": [10.1, 10.2],
                    "currency": ["CNY", "CNY"],
                    "adjusted": [True, True],
                    "ingested_at": ["2024-01-04T00:00:00Z", "2024-01-04T00:00:00Z"],
                }
            )
            DatasetStore(store_root).write_frame(
                bars,
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            config_path = root / "authority_bars.json"
            config_path.write_text(
                json.dumps(
                    {
                        "market": "CN",
                        "segments": [{"root": str(store_root), "end_date": "2024-01-03"}],
                    }
                ),
                encoding="utf-8",
            )

            manifest = run_cn_stock_data_manifest(data_root=config_path, output_dir=output_dir, market="CN")

            self.assertEqual(manifest["summary"]["bar_rows"], 2)
            self.assertEqual(manifest["summary"]["source_root"], str(config_path))
            self.assertTrue((output_dir / "cn_stock_data_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
