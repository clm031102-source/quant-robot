import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_cn_stock_data_manifest import run_cn_stock_data_manifest


class CnStockDataManifestCliTests(unittest.TestCase):
    def test_cli_runner_validates_calendar_and_passes_expected_sessions(self) -> None:
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
        moneyflow = pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "asset_id": ["000001.SZ"],
                "symbol": ["000001.SZ"],
                "market": ["CN"],
                "net_mf_amount": [100.0],
            }
        )
        calendar = pd.DataFrame(
            {"market": ["CN"], "date": ["2024-01-02"], "is_open": [1], "source": ["tushare"]}
        )
        calendar_manifest = {
            "provider": "tushare",
            "endpoint": "trade_cal",
            "effective_range": {"start": "2024-01-02", "end": "2024-01-02"},
            "summary": {"session_date_sha256": "calendar-sha"},
            "artifact": {"sha256": "artifact-sha"},
        }

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calendar_path = root / "calendar.csv"
            calendar_manifest_path = root / "calendar.json"
            calendar.to_csv(calendar_path, index=False)
            calendar_manifest_path.write_text(json.dumps(calendar_manifest), encoding="utf-8")
            with (
                patch("scripts.run_cn_stock_data_manifest.load_processed_bars", return_value=bars),
                patch("scripts.run_cn_stock_data_manifest.load_moneyflow_inputs", return_value=moneyflow),
                patch(
                    "scripts.run_cn_stock_data_manifest.validate_cn_trading_calendar_artifact",
                    return_value=calendar_manifest,
                ) as validate_calendar,
            ):
                manifest = run_cn_stock_data_manifest(
                    data_root=Path("data/processed/demo"),
                    output_dir=root / "report",
                    calendar_path=calendar_path,
                    calendar_manifest_path=calendar_manifest_path,
                )

        validate_calendar.assert_called_once_with(calendar_path, calendar_manifest_path)
        self.assertEqual(manifest["summary"]["expected_market_sessions"], 1)
        self.assertEqual(manifest["status"], "cleared")

    def test_cli_runner_requires_calendar_paths_as_a_pair(self) -> None:
        with self.assertRaisesRegex(ValueError, "calendar_path and calendar_manifest_path"):
            run_cn_stock_data_manifest(
                data_root=Path("data/processed/demo"),
                output_dir=Path("data/reports/demo"),
                calendar_path=Path("calendar.csv"),
            )

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

    def test_cli_runner_loads_separate_authority_bar_and_moneyflow_configs(self) -> None:
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
        moneyflow = pd.DataFrame(
            {
                "date": ["2024-01-02"],
                "asset_id": ["000001.SZ"],
                "symbol": ["000001.SZ"],
                "market": ["CN"],
                "net_mf_amount": [100.0],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_config = root / "bars.json"
            moneyflow_config = root / "moneyflow.json"
            bars_config.write_text(json.dumps({"market": "CN", "segments": []}), encoding="utf-8")
            moneyflow_config.write_text(json.dumps({"market": "CN", "segments": []}), encoding="utf-8")
            with (
                patch(
                    "scripts.run_cn_stock_data_manifest.load_authority_processed_bars_from_config",
                    return_value=bars,
                ) as load_bars,
                patch("scripts.run_cn_stock_data_manifest.load_moneyflow_inputs", return_value=moneyflow) as load_moneyflow,
            ):
                manifest = run_cn_stock_data_manifest(
                    data_root=bars_config,
                    moneyflow_root=moneyflow_config,
                    output_dir=root / "report",
                )

            load_bars.assert_called_once_with(bars_config, ("CN",))
            load_moneyflow.assert_called_once_with(moneyflow_config, "CN")
            self.assertEqual(manifest["summary"]["source_root"], str(bars_config))
            self.assertEqual(manifest["summary"]["moneyflow_source_root"], str(moneyflow_config))


if __name__ == "__main__":
    unittest.main()
