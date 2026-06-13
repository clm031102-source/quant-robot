import unittest

from quant_robot.ops.residual_data_gap_review import build_residual_data_gap_review_pack


class ResidualDataGapReviewTests(unittest.TestCase):
    def test_pack_extracts_residual_blocking_gap_rows(self):
        rehearsal = {
            "stage": "phase_4_6_data_gap_resolution_rehearsal",
            "summary": {
                "source_gap_rows": 3,
                "sample_resolution_rows": 1,
                "source_blocking_gap_rows": 3,
                "rehearsed_blocking_gap_rows": 2,
                "blocker_delta": 1,
                "blocks_api_boundary_after_rehearsal": True,
            },
            "rehearsed_ledger_rows": [
                {
                    "gap_id": "DG-accepted",
                    "asset_id": "A",
                    "symbol": "000001.SZ",
                    "missing_date": "2024-01-01",
                    "resolution_status": "accepted_non_trading_day",
                    "evidence_note": "accepted",
                    "recommended_command": "python scripts\\run_data_gap_resolution.py",
                    "blocks_api_boundary": False,
                    "local_only": True,
                },
                {
                    "gap_id": "DG-open-1",
                    "asset_id": "B",
                    "symbol": "000002.SZ",
                    "missing_date": "2024-01-02",
                    "resolution_status": "needs_review",
                    "evidence_note": "No local resolution recorded yet.",
                    "recommended_command": "python scripts\\run_data_quality_audit.py",
                    "blocks_api_boundary": True,
                    "local_only": True,
                },
                {
                    "gap_id": "DG-open-2",
                    "asset_id": "C",
                    "symbol": "000003.SZ",
                    "missing_date": "2024-01-03",
                    "resolution_status": "backfill_required",
                    "evidence_note": "needs backfill",
                    "recommended_command": "python scripts\\batch_import_etf_csv.py",
                    "blocks_api_boundary": True,
                    "local_only": True,
                },
            ],
        }

        pack = build_residual_data_gap_review_pack(rehearsal)

        self.assertEqual(pack["stage"], "phase_4_14_residual_data_gap_review_pack")
        self.assertEqual(pack["summary"]["residual_gap_rows"], 2)
        self.assertEqual(pack["summary"]["sample_cleared_gap_rows"], 1)
        self.assertTrue(pack["summary"]["blocks_api_boundary_after_review"])
        self.assertEqual([row["gap_id"] for row in pack["residual_rows"]], ["DG-open-1", "DG-open-2"])
        self.assertEqual(len(pack["review_template_rows"]), 2)
        self.assertEqual(pack["review_template_rows"][0]["resolution_status"], "needs_review")
        self.assertIn("run_data_gap_evidence.py", pack["action_queue"][2]["command"])
        self.assertIn("--resolution-file", pack["action_queue"][3]["command"])
        self.assertIn("No broker", pack["safety"])
        self.assertIn("Residual Data Gap Review Pack", pack["markdown"])

    def test_pack_prefers_current_resolution_ledger_when_supplied(self):
        rehearsal = {
            "stage": "phase_4_6_data_gap_resolution_rehearsal",
            "summary": {
                "source_gap_rows": 2,
                "sample_resolution_rows": 1,
                "source_blocking_gap_rows": 2,
                "rehearsed_blocking_gap_rows": 1,
            },
            "rehearsed_ledger_rows": [
                {
                    "gap_id": "DG-sample-cleared",
                    "asset_id": "A",
                    "symbol": "000001.SZ",
                    "missing_date": "2024-01-01",
                    "resolution_status": "accepted_non_trading_day",
                    "evidence_note": "rehearsal only",
                    "recommended_command": "python scripts\\run_data_gap_resolution.py",
                    "blocks_api_boundary": False,
                }
            ],
        }
        current_ledger = {
            "stage": "phase_4_2_data_gap_resolution_ledger",
            "summary": {"gap_rows": 2, "blocking_gap_rows": 2, "backfill_required": 2},
            "ledger_rows": [
                {
                    "gap_id": "DG-open-1",
                    "asset_id": "B",
                    "symbol": "000002.SZ",
                    "missing_date": "2024-01-02",
                    "resolution_status": "backfill_required",
                    "evidence_note": "raw target row absent while peers traded",
                    "recommended_command": "python scripts\\batch_import_etf_csv.py",
                    "blocks_api_boundary": True,
                    "local_only": True,
                },
                {
                    "gap_id": "DG-open-2",
                    "asset_id": "C",
                    "symbol": "000003.SZ",
                    "missing_date": "2024-01-03",
                    "resolution_status": "backfill_required",
                    "evidence_note": "raw target row absent while peers traded",
                    "recommended_command": "python scripts\\batch_import_etf_csv.py",
                    "blocks_api_boundary": True,
                    "local_only": True,
                },
            ],
        }

        pack = build_residual_data_gap_review_pack(rehearsal, data_gap_ledger=current_ledger)

        self.assertEqual(pack["summary"]["source_gap_rows"], 2)
        self.assertEqual(pack["summary"]["source_blocking_gap_rows"], 2)
        self.assertEqual(pack["summary"]["residual_gap_rows"], 2)
        self.assertEqual([row["resolution_status"] for row in pack["residual_rows"]], ["backfill_required", "backfill_required"])
        self.assertEqual(pack["source_stage"], "phase_4_2_data_gap_resolution_ledger")


if __name__ == "__main__":
    unittest.main()
