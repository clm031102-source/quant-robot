import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_data_quality_audit import run_data_quality_audit
from quant_robot.storage.dataset_store import DatasetStore


class DataQualityGapAuditCliTests(unittest.TestCase):
    def test_run_data_quality_audit_writes_json_markdown_and_missing_dates_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "audit"
            bars = pd.DataFrame(
                {
                    "asset_id": ["ETF_A", "ETF_A", "ETF_B", "ETF_B", "ETF_B"],
                    "symbol": ["510300.SH", "510300.SH", "159915.SZ", "159915.SZ", "159915.SZ"],
                    "market": ["CN_ETF", "CN_ETF", "CN_ETF", "CN_ETF", "CN_ETF"],
                    "date": ["2024-01-02", "2024-01-04", "2024-01-02", "2024-01-03", "2024-01-04"],
                    "volume": [100, 120, 200, 210, 220],
                }
            )

            result = run_data_quality_audit(bars=bars, output_dir=output_dir, data_root=root, market="CN_ETF")

            self.assertEqual(result["summary"]["missing_date_rows"], 1)
            self.assertTrue((output_dir / "data_quality_gap_audit.json").exists())
            self.assertTrue((output_dir / "data_quality_gap_audit.md").exists())
            self.assertTrue((output_dir / "missing_dates.csv").exists())
            payload = json.loads((output_dir / "data_quality_gap_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["stage"], "phase_3_1_data_quality_gap_audit")

    def test_run_data_quality_audit_accepts_authority_bars_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "store"
            output_dir = root / "audit"
            bars = pd.DataFrame(
                {
                    "asset_id": ["CN_A", "CN_A", "CN_B"],
                    "symbol": ["000001.SZ", "000001.SZ", "000002.SZ"],
                    "market": ["CN", "CN", "CN"],
                    "exchange": ["XSHE", "XSHE", "XSHE"],
                    "asset_type": ["stock", "stock", "stock"],
                    "frequency": ["1d", "1d", "1d"],
                    "source": ["fixture", "fixture", "fixture"],
                    "date": ["2024-01-02", "2024-01-04", "2024-01-02"],
                    "timestamp": [
                        "2024-01-02T08:00:00Z",
                        "2024-01-04T08:00:00Z",
                        "2024-01-02T08:00:00Z",
                    ],
                    "timezone": ["Asia/Shanghai", "Asia/Shanghai", "Asia/Shanghai"],
                    "calendar": ["XSHG", "XSHG", "XSHG"],
                    "open": [10.0, 10.5, 20.0],
                    "high": [10.1, 10.6, 20.1],
                    "low": [9.9, 10.4, 19.9],
                    "close": [10.0, 10.5, 20.0],
                    "adj_close": [10.0, 10.5, 20.0],
                    "volume": [100, 120, 200],
                    "amount": [1000.0, 1260.0, 4000.0],
                    "vwap": [10.0, 10.5, 20.0],
                    "currency": ["CNY", "CNY", "CNY"],
                    "adjusted": [True, True, True],
                    "ingested_at": ["2024-01-05T00:00:00Z", "2024-01-05T00:00:00Z", "2024-01-05T00:00:00Z"],
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
                        "segments": [{"root": str(store_root), "end_date": "2024-01-04"}],
                    }
                ),
                encoding="utf-8",
            )

            result = run_data_quality_audit(data_root=config_path, market="CN", output_dir=output_dir)

            self.assertEqual(result["summary"]["rows"], 3)
            self.assertEqual(result["summary"]["markets"], ["CN"])
            self.assertEqual(result["source_root"], str(config_path))
            self.assertTrue((output_dir / "data_quality_gap_audit.json").exists())


if __name__ == "__main__":
    unittest.main()
