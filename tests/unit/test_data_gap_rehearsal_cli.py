import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_data_gap_rehearsal import run_data_gap_rehearsal


class DataGapRehearsalCliTests(unittest.TestCase):
    def test_run_data_gap_rehearsal_writes_rehearsal_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = root / "data_quality_gap_audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_3_1_data_quality_gap_audit",
                        "missing_dates": [
                            {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"},
                            {"asset_id": "ETF_B", "symbol": "159915.SZ", "missing_date": "2024-01-04"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "data_gap_rehearsal"

            rehearsal = run_data_gap_rehearsal(data_quality_audit=audit_path, output_dir=output_dir, sample_size=1)

            self.assertEqual(rehearsal["stage"], "phase_4_6_data_gap_resolution_rehearsal")
            self.assertTrue((output_dir / "data_gap_rehearsal.json").exists())
            self.assertTrue((output_dir / "data_gap_rehearsal.md").exists())
            self.assertTrue((output_dir / "sample_gap_resolutions.csv").exists())
            self.assertTrue((output_dir / "rehearsed_data_gap_rows.csv").exists())
            self.assertTrue((output_dir / "data_gap_rehearsal_summary.csv").exists())
            payload = json.loads((output_dir / "data_gap_rehearsal.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["sample_resolution_rows"], 1)
            self.assertEqual(payload["summary"]["rehearsed_blocking_gap_rows"], 1)


if __name__ == "__main__":
    unittest.main()
