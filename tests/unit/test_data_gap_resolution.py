import unittest

from quant_robot.ops.data_gap_resolution import (
    build_data_gap_resolution_ledger,
    build_resolution_template_rows,
    resolution_status_options,
)


class DataGapResolutionTests(unittest.TestCase):
    def test_ledger_turns_missing_dates_into_open_local_resolution_rows(self):
        audit = {
            "stage": "phase_3_1_data_quality_gap_audit",
            "source_root": "data\\processed\\etf_csv",
            "summary": {"missing_date_rows": 2, "assets_with_gaps": 2},
            "missing_dates": [
                {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"},
                {"asset_id": "ETF_B", "symbol": "159915.SZ", "missing_date": "2024-01-04"},
            ],
            "repair_actions": [
                {
                    "action": "inspect_missing_dates",
                    "command": "python scripts\\run_data_quality_audit.py",
                    "reason": "Regenerate missing-date rows.",
                }
            ],
        }

        ledger = build_data_gap_resolution_ledger(audit)

        self.assertEqual(ledger["stage"], "phase_4_2_data_gap_resolution_ledger")
        self.assertEqual(ledger["source_stage"], "phase_3_1_data_quality_gap_audit")
        self.assertEqual(ledger["summary"]["gap_rows"], 2)
        self.assertEqual(ledger["summary"]["needs_review"], 2)
        self.assertEqual(ledger["summary"]["blocking_gap_rows"], 2)
        self.assertTrue(ledger["summary"]["blocks_api_boundary"])
        self.assertEqual(ledger["ledger_rows"][0]["gap_id"], "DG-ETF_A-20240103")
        self.assertEqual(ledger["ledger_rows"][0]["resolution_status"], "needs_review")
        self.assertEqual(ledger["ledger_rows"][0]["evidence_note"], "No local resolution recorded yet.")
        self.assertTrue(ledger["ledger_rows"][0]["blocks_api_boundary"])
        self.assertTrue(ledger["ledger_rows"][0]["local_only"])
        self.assertIn("run_data_quality_audit.py", ledger["ledger_rows"][0]["recommended_command"])
        self.assertIn("2024-01-03", ledger["markdown"])
        self.assertIn("Research only", ledger["safety"])

    def test_ledger_applies_local_resolution_overrides_without_external_calls(self):
        audit = {
            "stage": "phase_3_1_data_quality_gap_audit",
            "missing_dates": [
                {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"},
                {"asset_id": "ETF_B", "symbol": "159915.SZ", "missing_date": "2024-01-04"},
            ],
        }
        resolution_rows = [
            {
                "gap_id": "DG-ETF_A-20240103",
                "resolution_status": "accepted_non_trading_day",
                "evidence_note": "Local exchange calendar marks this as closed.",
                "reviewed_by": "research",
                "reviewed_at": "2026-06-01",
            }
        ]

        ledger = build_data_gap_resolution_ledger(audit, resolution_rows=resolution_rows)

        self.assertEqual(ledger["summary"]["gap_rows"], 2)
        self.assertEqual(ledger["summary"]["accepted_non_trading_day"], 1)
        self.assertEqual(ledger["summary"]["needs_review"], 1)
        self.assertEqual(ledger["summary"]["blocking_gap_rows"], 1)
        self.assertTrue(ledger["summary"]["blocks_api_boundary"])
        self.assertFalse(ledger["ledger_rows"][0]["blocks_api_boundary"])
        self.assertEqual(ledger["ledger_rows"][0]["resolution_status"], "accepted_non_trading_day")
        self.assertEqual(ledger["ledger_rows"][0]["reviewed_by"], "research")
        self.assertTrue(ledger["ledger_rows"][1]["blocks_api_boundary"])

    def test_ledger_recommends_akshare_backfill_for_backfill_required_rows(self):
        audit = {
            "stage": "phase_3_1_data_quality_gap_audit",
            "missing_dates": [
                {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"},
            ],
        }
        resolution_rows = [
            {
                "gap_id": "DG-ETF_A-20240103",
                "resolution_status": "backfill_required",
                "evidence_note": "Raw target row absent while peer ETFs traded.",
            }
        ]

        ledger = build_data_gap_resolution_ledger(audit, resolution_rows=resolution_rows)

        commands = [row["command"] for row in ledger["action_queue"]]
        self.assertTrue(any("run_akshare_gap_backfill.py" in command for command in commands))

    def test_resolution_template_rows_are_fillable_and_status_options_explain_boundary_effects(self):
        ledger = {
            "ledger_rows": [
                {
                    "gap_id": "DG-ETF_A-20240103",
                    "asset_id": "ETF_A",
                    "symbol": "510300.SH",
                    "missing_date": "2024-01-03",
                    "resolution_status": "needs_review",
                }
            ]
        }

        template_rows = build_resolution_template_rows(ledger)
        status_options = resolution_status_options()

        self.assertEqual(template_rows[0]["gap_id"], "DG-ETF_A-20240103")
        self.assertEqual(template_rows[0]["asset_id"], "ETF_A")
        self.assertEqual(template_rows[0]["resolution_status"], "needs_review")
        self.assertEqual(template_rows[0]["evidence_note"], "")
        self.assertEqual(template_rows[0]["reviewed_by"], "")
        self.assertEqual(template_rows[0]["reviewed_at"], "")
        self.assertIn("accepted_non_trading_day", template_rows[0]["allowed_statuses"])
        self.assertIn("local", template_rows[0]["review_guidance"].lower())
        options_by_status = {row["resolution_status"]: row for row in status_options}
        self.assertTrue(options_by_status["needs_review"]["blocks_api_boundary"])
        self.assertTrue(options_by_status["backfill_required"]["blocks_api_boundary"])
        self.assertFalse(options_by_status["resolved_with_backfill"]["blocks_api_boundary"])
        self.assertFalse(options_by_status["accepted_non_trading_day"]["blocks_api_boundary"])

    def test_ledger_reports_invalid_unknown_and_duplicate_resolution_rows(self):
        audit = {
            "stage": "phase_3_1_data_quality_gap_audit",
            "missing_dates": [
                {"asset_id": "ETF_A", "symbol": "510300.SH", "missing_date": "2024-01-03"},
                {"asset_id": "ETF_B", "symbol": "159915.SZ", "missing_date": "2024-01-04"},
            ],
        }
        resolution_rows = [
            {
                "gap_id": "DG-ETF_A-20240103",
                "resolution_status": "resolved_with_backfill",
                "evidence_note": "Local CSV now includes the row.",
            },
            {
                "gap_id": "DG-ETF_A-20240103",
                "resolution_status": "accepted_non_trading_day",
                "evidence_note": "Duplicate row should be reported and ignored.",
            },
            {
                "gap_id": "DG-ETF_B-20240104",
                "resolution_status": "done",
                "evidence_note": "Invalid status should not be applied.",
            },
            {
                "gap_id": "DG-UNKNOWN-20240105",
                "resolution_status": "resolved_with_backfill",
                "evidence_note": "Unknown gap should be ignored.",
            },
        ]

        ledger = build_data_gap_resolution_ledger(audit, resolution_rows=resolution_rows)

        validation = ledger["resolution_validation"]
        self.assertEqual(validation["summary"]["resolution_rows"], 4)
        self.assertEqual(validation["summary"]["applied_resolution_rows"], 1)
        self.assertEqual(validation["summary"]["duplicate_gap_id_rows"], 1)
        self.assertEqual(validation["summary"]["invalid_status_rows"], 1)
        self.assertEqual(validation["summary"]["unknown_gap_id_rows"], 1)
        self.assertEqual(validation["summary"]["validation_errors"], 3)
        issue_types = {row["issue_type"] for row in validation["rows"]}
        self.assertEqual(issue_types, {"duplicate_gap_id", "invalid_status", "unknown_gap_id"})
        self.assertEqual(ledger["ledger_rows"][0]["resolution_status"], "resolved_with_backfill")
        self.assertEqual(ledger["ledger_rows"][1]["resolution_status"], "needs_review")
        self.assertEqual(ledger["summary"]["blocking_gap_rows"], 1)


if __name__ == "__main__":
    unittest.main()
