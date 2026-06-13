import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_residual_data_gap_review import run_residual_data_gap_review


class ResidualDataGapReviewCliTests(unittest.TestCase):
    def test_cli_writes_residual_review_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rehearsal_path = root / "data_gap_rehearsal.json"
            output_dir = root / "out"
            rehearsal_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_4_6_data_gap_resolution_rehearsal",
                        "summary": {"source_gap_rows": 1, "sample_resolution_rows": 0, "rehearsed_blocking_gap_rows": 1},
                        "rehearsed_ledger_rows": [
                            {
                                "gap_id": "DG-open",
                                "asset_id": "A",
                                "symbol": "000001.SZ",
                                "missing_date": "2024-01-01",
                                "resolution_status": "needs_review",
                                "evidence_note": "No local resolution recorded yet.",
                                "recommended_command": "python scripts\\run_data_quality_audit.py",
                                "blocks_api_boundary": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            pack = run_residual_data_gap_review(data_gap_rehearsal=rehearsal_path, data_gap_ledger=None, output_dir=output_dir)

            self.assertEqual(pack["summary"]["residual_gap_rows"], 1)
            self.assertTrue((output_dir / "residual_data_gap_review_pack.json").exists())
            self.assertTrue((output_dir / "residual_data_gap_review_pack.md").exists())
            self.assertTrue((output_dir / "residual_data_gap_rows.csv").exists())
            self.assertTrue((output_dir / "residual_gap_review_template.csv").exists())
            self.assertTrue((output_dir / "residual_gap_action_queue.csv").exists())
            self.assertTrue((output_dir / "residual_gap_status_options.csv").exists())

    def test_cli_uses_current_resolution_ledger_when_supplied(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rehearsal_path = root / "data_gap_rehearsal.json"
            ledger_path = root / "data_gap_resolution_ledger.json"
            output_dir = root / "out"
            rehearsal_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_4_6_data_gap_resolution_rehearsal",
                        "summary": {"source_gap_rows": 1, "sample_resolution_rows": 1, "rehearsed_blocking_gap_rows": 0},
                        "rehearsed_ledger_rows": [],
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_4_2_data_gap_resolution_ledger",
                        "summary": {"gap_rows": 1, "blocking_gap_rows": 1},
                        "ledger_rows": [
                            {
                                "gap_id": "DG-open",
                                "asset_id": "A",
                                "symbol": "000001.SZ",
                                "missing_date": "2024-01-01",
                                "resolution_status": "backfill_required",
                                "evidence_note": "raw target row absent while peers traded",
                                "recommended_command": "python scripts\\batch_import_etf_csv.py",
                                "blocks_api_boundary": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            pack = run_residual_data_gap_review(data_gap_rehearsal=rehearsal_path, data_gap_ledger=ledger_path, output_dir=output_dir)

            self.assertEqual(pack["source_stage"], "phase_4_2_data_gap_resolution_ledger")
            self.assertEqual(pack["summary"]["residual_gap_rows"], 1)
            self.assertEqual(pack["residual_rows"][0]["resolution_status"], "backfill_required")


if __name__ == "__main__":
    unittest.main()
