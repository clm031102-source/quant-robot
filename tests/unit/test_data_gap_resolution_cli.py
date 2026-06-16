import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_data_gap_resolution import run_data_gap_resolution


class DataGapResolutionCliTests(unittest.TestCase):
    def test_run_data_gap_resolution_writes_ledger_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = root / "data_quality_gap_audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_3_1_data_quality_gap_audit",
                        "missing_dates": [
                            {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            resolution_path = root / "gap_resolutions.csv"
            resolution_path.write_text(
                "gap_id,resolution_status,evidence_note,reviewed_by,reviewed_at\n"
                "DG-ETF_A-20240103,resolved_with_backfill,Backfilled from local CSV,research,2026-06-01\n",
                encoding="utf-8",
            )
            output_dir = root / "data_gap_resolution"

            ledger = run_data_gap_resolution(
                data_quality_audit=audit_path,
                resolution_file=resolution_path,
                output_dir=output_dir,
            )

            self.assertEqual(ledger["stage"], "phase_4_2_data_gap_resolution_ledger")
            self.assertTrue((output_dir / "data_gap_resolution_ledger.json").exists())
            self.assertTrue((output_dir / "data_gap_resolution_ledger.md").exists())
            self.assertTrue((output_dir / "data_gap_resolution_rows.csv").exists())
            self.assertTrue((output_dir / "data_gap_resolution_action_queue.csv").exists())
            self.assertTrue((output_dir / "gap_resolutions_template.csv").exists())
            self.assertTrue((output_dir / "data_gap_resolution_status_options.csv").exists())
            self.assertTrue((output_dir / "data_gap_resolution_validation.csv").exists())
            payload = json.loads((output_dir / "data_gap_resolution_ledger.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["gap_rows"], 1)
            self.assertEqual(payload["summary"]["resolved_with_backfill"], 1)
            self.assertFalse(payload["summary"]["blocks_api_boundary"])
            self.assertEqual(payload["resolution_validation"]["summary"]["validation_errors"], 0)
            template_text = (output_dir / "gap_resolutions_template.csv").read_text(encoding="utf-8")
            status_options_text = (output_dir / "data_gap_resolution_status_options.csv").read_text(encoding="utf-8")
            validation_text = (output_dir / "data_gap_resolution_validation.csv").read_text(encoding="utf-8")
            self.assertIn("DG-ETF_A-20240103", template_text)
            self.assertIn("accepted_non_trading_day", status_options_text)
            self.assertIn("issue_type", validation_text)

    def test_run_data_gap_resolution_uses_default_review_file_from_output_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = root / "data_quality_gap_audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_3_1_data_quality_gap_audit",
                        "missing_dates": [
                            {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "data_gap_resolution"
            output_dir.mkdir()
            (output_dir / "gap_resolutions_review.csv").write_text(
                "gap_id,resolution_status,evidence_note,reviewed_by,reviewed_at\n"
                "DG-ETF_A-20240103,backfill_required,Raw target row absent while peer ETFs traded,codex,2026-06-09\n",
                encoding="utf-8",
            )

            with patch("scripts.run_data_gap_resolution.DEFAULT_RESOLUTION_FILE", root / "missing.csv"):
                ledger = run_data_gap_resolution(data_quality_audit=audit_path, output_dir=output_dir)

            self.assertEqual(ledger["summary"]["backfill_required"], 1)
            self.assertTrue(ledger["summary"]["blocks_api_boundary"])
            self.assertEqual(ledger["resolution_validation"]["summary"]["applied_resolution_rows"], 1)

    def test_run_data_gap_resolution_uses_default_committed_resolution_file_when_review_file_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = root / "data_quality_gap_audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_3_1_data_quality_gap_audit",
                        "missing_dates": [
                            {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            default_resolution_path = root / "committed_gap_resolutions.csv"
            default_resolution_path.write_text(
                "gap_id,resolution_status,evidence_note,reviewed_by,reviewed_at\n"
                "DG-ETF_A-20240103,accepted_suspension_or_no_trade,Reviewed suspension,codex,2026-06-16\n",
                encoding="utf-8",
            )
            output_dir = root / "data_gap_resolution"

            with patch(
                "scripts.run_data_gap_resolution.DEFAULT_RESOLUTION_FILE",
                default_resolution_path,
                create=True,
            ):
                ledger = run_data_gap_resolution(data_quality_audit=audit_path, output_dir=output_dir)

            self.assertEqual(ledger["summary"]["accepted_suspension_or_no_trade"], 1)
            self.assertEqual(ledger["summary"]["blocking_gap_rows"], 0)
            self.assertFalse(ledger["summary"]["blocks_api_boundary"])
            self.assertEqual(ledger["resolution_validation"]["summary"]["applied_resolution_rows"], 1)

    def test_run_data_gap_resolution_prefers_committed_resolution_over_stale_review_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit_path = root / "data_quality_gap_audit.json"
            audit_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_3_1_data_quality_gap_audit",
                        "missing_dates": [
                            {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            default_resolution_path = root / "committed_gap_resolutions.csv"
            default_resolution_path.write_text(
                "gap_id,resolution_status,evidence_note,reviewed_by,reviewed_at\n"
                "DG-ETF_A-20240103,accepted_suspension_or_no_trade,Reviewed suspension,codex,2026-06-16\n",
                encoding="utf-8",
            )
            output_dir = root / "data_gap_resolution"
            output_dir.mkdir()
            (output_dir / "gap_resolutions_review.csv").write_text(
                "gap_id,resolution_status,evidence_note,reviewed_by,reviewed_at\n"
                "DG-ETF_A-20240103,backfill_required,Stale local review,codex,2026-06-09\n",
                encoding="utf-8",
            )

            with patch("scripts.run_data_gap_resolution.DEFAULT_RESOLUTION_FILE", default_resolution_path):
                ledger = run_data_gap_resolution(data_quality_audit=audit_path, output_dir=output_dir)

            self.assertEqual(ledger["summary"]["accepted_suspension_or_no_trade"], 1)
            self.assertEqual(ledger["summary"]["backfill_required"], 0)
            self.assertFalse(ledger["summary"]["blocks_api_boundary"])


if __name__ == "__main__":
    unittest.main()
