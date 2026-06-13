import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_data_quality_audit import run_data_quality_audit


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


if __name__ == "__main__":
    unittest.main()
