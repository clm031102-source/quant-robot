import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_data_gap_evidence import run_data_gap_evidence


class DataGapEvidenceCliTests(unittest.TestCase):
    def test_run_data_gap_evidence_writes_pack_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gap_rows = root / "gap_rows.csv"
            raw_dir = root / "raw"
            output_dir = root / "out"
            raw_dir.mkdir()
            gap_rows.write_text(
                "gap_id,asset_id,symbol,missing_date,resolution_status\n"
                "DG-CN_ETF_XSHG_510500-20240102,CN_ETF_XSHG_510500,510500.SH,2024-01-02,needs_review\n",
                encoding="utf-8",
            )
            (raw_dir / "510500_SH_1d.csv").write_text(
                "time,open,high,low,close,Volume\n"
                "2024-01-01,1,1,1,1,100\n",
                encoding="utf-8",
            )

            pack = run_data_gap_evidence(gap_rows=gap_rows, raw_dir=raw_dir, output_dir=output_dir)

            self.assertEqual(pack["stage"], "phase_4_16_data_gap_evidence_pack")
            self.assertTrue((output_dir / "data_gap_evidence_pack.json").exists())
            self.assertTrue((output_dir / "data_gap_evidence_pack.md").exists())
            self.assertTrue((output_dir / "data_gap_evidence_rows.csv").exists())
            self.assertTrue((output_dir / "data_gap_evidence_action_queue.csv").exists())
            payload = json.loads((output_dir / "data_gap_evidence_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["gap_rows"], 1)
            self.assertEqual(payload["summary"]["raw_target_files_found"], 1)
            rows_text = (output_dir / "data_gap_evidence_rows.csv").read_text(encoding="utf-8")
            self.assertIn("raw target row absent", rows_text)


if __name__ == "__main__":
    unittest.main()
