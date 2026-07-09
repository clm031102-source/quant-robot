import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.cn_stock_local_source_queue_audit import (
    build_cn_stock_local_source_queue_audit,
    write_cn_stock_local_source_queue_audit,
)


class CnStockLocalSourceQueueAuditTests(unittest.TestCase):
    def test_blocks_no_provider_factor_batch_when_only_active_source_requires_provider(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)

            packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )

        rows = {row["source_id"]: row for row in packet["source_rows"]}
        self.assertEqual(packet["stage"], "cn_stock_local_source_queue_audit")
        self.assertEqual(packet["summary"]["active_source_count"], 1)
        self.assertEqual(packet["summary"]["evidence_ready_active_source_count"], 1)
        self.assertGreaterEqual(packet["summary"]["hibernated_or_closed_source_count"], 8)
        self.assertFalse(packet["decision"]["no_provider_factor_batch_allowed"])
        self.assertFalse(packet["decision"]["provider_factor_batch_allowed"])
        self.assertTrue(packet["decision"]["local_prescreen_allowed"])
        self.assertEqual(packet["summary"]["local_prescreen_ready_source_count"], 1)
        self.assertIn("report_rc_quota_blocked", packet["decision"]["blockers"])
        self.assertIn("no_local_no_provider_source_ready", packet["decision"]["blockers"])
        self.assertEqual(
            packet["decision"]["next_action"],
            "wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight",
        )
        self.assertTrue(rows["analyst_report_revision"]["evidence_present"])
        self.assertTrue(rows["analyst_report_revision"]["local_prescreen_allowed"])
        self.assertTrue(rows["analyst_report_revision"]["provider_required"])
        self.assertEqual(rows["analyst_report_revision"]["status"], "active_source_accumulation")
        self.assertEqual(rows["daily_basic_direct"]["status"], "hibernated")

    def test_provider_ready_source_clears_when_provider_request_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)

            packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=True,
            )

        self.assertEqual(packet["decision"]["status"], "cleared")
        self.assertFalse(packet["decision"]["no_provider_factor_batch_allowed"])
        self.assertTrue(packet["decision"]["provider_factor_batch_allowed"])
        self.assertTrue(packet["decision"]["local_prescreen_allowed"])
        self.assertEqual(packet["decision"]["blockers"], [])
        self.assertEqual(
            packet["decision"]["next_action"],
            "analyst_monthly_cache_preflight_then_frozen_prescreen",
        )

    def test_lpr_macro_regime_source_stays_maintenance_only_after_walk_forward_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (processed / "round695_external_feeds_lpr_repaired_20260709").mkdir(parents=True)
            (reports / "round695_external_feed_lpr_repaired_coverage_audit_20260709").mkdir(parents=True)

            packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )

        rows = {row["source_id"]: row for row in packet["source_rows"]}
        lpr_row = rows["external_macro_lpr_regime"]
        self.assertEqual(lpr_row["status"], "source_maintenance_only")
        self.assertTrue(lpr_row["evidence_present"])
        self.assertFalse(lpr_row["provider_required"])
        self.assertFalse(lpr_row["local_prescreen_allowed"])
        self.assertEqual(
            lpr_row["allowed_next_action"],
            "new_lpr_macro_interaction_source_gate_only_after_round738_rejection",
        )
        self.assertFalse(packet["decision"]["no_provider_factor_batch_allowed"])
        self.assertFalse(packet["decision"]["provider_factor_batch_allowed"])
        self.assertEqual(packet["decision"]["status"], "blocked")
        self.assertIn("report_rc_quota_blocked", packet["decision"]["blockers"])
        self.assertIn("no_local_no_provider_source_ready", packet["decision"]["blockers"])
        self.assertEqual(packet["summary"]["no_provider_ready_source_count"], 0)
        self.assertEqual(
            packet["decision"]["next_action"],
            "wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight",
        )

    def test_calendar_seasonality_stays_hibernated_after_cost_capacity_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "cn_calendar_pre_holiday_cost_capacity_preflight_round165_20260623").mkdir(parents=True)

            packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )

        rows = {row["source_id"]: row for row in packet["source_rows"]}
        calendar_row = rows["calendar_seasonality"]
        self.assertEqual(calendar_row["status"], "hibernated")
        self.assertTrue(calendar_row["evidence_present"])
        self.assertFalse(calendar_row["provider_required"])
        self.assertFalse(calendar_row["local_prescreen_allowed"])
        self.assertEqual(
            calendar_row["allowed_next_action"],
            "do_not_reenter_pre_holiday_or_calendar_windows_after_round165_failure",
        )
        self.assertIn("pre_holiday_window_tuning", calendar_row["blocked_actions"])
        self.assertIn("walk_forward_after_round165_failure", calendar_row["blocked_actions"])
        self.assertEqual(packet["summary"]["no_provider_ready_source_count"], 0)
        self.assertFalse(packet["decision"]["no_provider_factor_batch_allowed"])

    def test_listing_age_board_structural_stays_hibernated_after_zero_residual_leads(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round259_listing_age_board_full_core_20260626").mkdir(parents=True)

            packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )

        rows = {row["source_id"]: row for row in packet["source_rows"]}
        listing_row = rows["listing_age_board_structural"]
        self.assertEqual(listing_row["status"], "hibernated")
        self.assertTrue(listing_row["evidence_present"])
        self.assertFalse(listing_row["provider_required"])
        self.assertFalse(listing_row["local_prescreen_allowed"])
        self.assertEqual(
            listing_row["allowed_next_action"],
            "use_listing_age_and_board_as_risk_control_not_alpha_source",
        )
        self.assertIn("listing_age_threshold_tuning", listing_row["blocked_actions"])
        self.assertIn("sign_flip_after_residual_collapse", listing_row["blocked_actions"])
        self.assertEqual(packet["summary"]["no_provider_ready_source_count"], 0)
        self.assertFalse(packet["decision"]["no_provider_factor_batch_allowed"])

    def test_missing_active_source_evidence_is_reported_as_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            packet = build_cn_stock_local_source_queue_audit(
                processed_root=root / "processed",
                reports_root=root / "reports",
                provider_request_allowed=True,
            )

        rows = {row["source_id"]: row for row in packet["source_rows"]}
        self.assertFalse(rows["analyst_report_revision"]["evidence_present"])
        self.assertFalse(rows["analyst_report_revision"]["local_prescreen_allowed"])
        self.assertEqual(packet["summary"]["evidence_ready_active_source_count"], 0)
        self.assertEqual(packet["summary"]["local_prescreen_ready_source_count"], 0)
        self.assertFalse(packet["decision"]["provider_factor_batch_allowed"])
        self.assertFalse(packet["decision"]["local_prescreen_allowed"])
        self.assertIn("active_source_evidence_missing:analyst_report_revision", packet["decision"]["blockers"])

    def test_writer_outputs_json_markdown_and_source_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            output = root / "out"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)

            packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )
            write_cn_stock_local_source_queue_audit(output, packet)

            json_path = output / "cn_stock_local_source_queue_audit.json"
            self.assertTrue(json_path.exists())
            self.assertTrue((output / "cn_stock_local_source_queue_audit.md").exists())
            self.assertTrue((output / "cn_stock_local_source_queue_rows.csv").exists())
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["decision"]["next_action"], packet["decision"]["next_action"])


if __name__ == "__main__":
    unittest.main()
