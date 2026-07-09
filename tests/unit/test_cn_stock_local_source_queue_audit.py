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
        self.assertIn("report_rc_quota_blocked", packet["decision"]["blockers"])
        self.assertIn("no_local_no_provider_source_ready", packet["decision"]["blockers"])
        self.assertEqual(
            packet["decision"]["next_action"],
            "wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight",
        )
        self.assertTrue(rows["analyst_report_revision"]["evidence_present"])
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
        self.assertEqual(packet["decision"]["blockers"], [])
        self.assertEqual(
            packet["decision"]["next_action"],
            "analyst_monthly_cache_preflight_then_frozen_prescreen",
        )

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
        self.assertEqual(packet["summary"]["evidence_ready_active_source_count"], 0)
        self.assertFalse(packet["decision"]["provider_factor_batch_allowed"])
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
