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

    def test_local_prescreen_next_action_waits_when_latest_cache_is_already_prescreened(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            prescreen = reports / "round729_analyst_report_revision_jan_jun_local_prescreen_20260709"
            prescreen.mkdir(parents=True)
            (prescreen / "analyst_report_revision_prescreen.json").write_text(
                json.dumps({"data_window": {"max_report_date": "2024-06-30"}}),
                encoding="utf-8",
            )

            packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )

        rows = {row["source_id"]: row for row in packet["source_rows"]}
        analyst_row = rows["analyst_report_revision"]
        self.assertEqual(analyst_row["latest_source_cache_period"], "202406")
        self.assertEqual(analyst_row["latest_prescreen_period"], "202406")
        self.assertTrue(analyst_row["local_prescreen_current"])
        self.assertEqual(
            packet["decision"]["local_prescreen_next_action"],
            "local_prescreen_current_wait_for_report_rc_quota_reset_then_analyst_monthly_cache_preflight",
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

    def test_statement_source_closeout_requires_round691_694_report_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)

            missing_packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )
            rows = {row["source_id"]: row for row in missing_packet["source_rows"]}
            self.assertEqual(rows["financial_statement_adjacent_realized"]["status"], "closed")
            self.assertFalse(rows["financial_statement_adjacent_realized"]["evidence_present"])
            self.assertIn(
                "financial_statement_adjacent_realized",
                [
                    row["source_id"]
                    for row in missing_packet["source_rows"]
                    if row["evidence_required"] and not row["evidence_present"]
                ],
            )

            (
                reports / "round691_financial_reporting_timeliness_residual_ic_shape_prescreen_20260709"
            ).mkdir(parents=True)
            present_packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )

        rows = {row["source_id"]: row for row in present_packet["source_rows"]}
        statement_row = rows["financial_statement_adjacent_realized"]
        self.assertTrue(statement_row["evidence_present"])
        self.assertEqual(
            statement_row["matched_report_paths"],
            [
                str(
                    reports
                    / "round691_financial_reporting_timeliness_residual_ic_shape_prescreen_20260709"
                )
            ],
        )
        self.assertEqual(present_packet["summary"]["no_provider_ready_source_count"], 0)
        self.assertFalse(present_packet["decision"]["no_provider_factor_batch_allowed"])

    def test_hk_hold_daily_source_requires_round697_or_698_report_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)

            missing_packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )
            rows = {row["source_id"]: row for row in missing_packet["source_rows"]}
            self.assertEqual(rows["northbound_hk_hold_daily"]["status"], "source_maintenance_only")
            self.assertFalse(rows["northbound_hk_hold_daily"]["evidence_present"])

            (reports / "round697_hk_hold_source_symbol_composition_audit_20260709").mkdir(parents=True)
            present_packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )

        rows = {row["source_id"]: row for row in present_packet["source_rows"]}
        hk_hold_row = rows["northbound_hk_hold_daily"]
        self.assertTrue(hk_hold_row["evidence_present"])
        self.assertFalse(hk_hold_row["local_prescreen_allowed"])
        self.assertEqual(present_packet["summary"]["no_provider_ready_source_count"], 0)

    def test_margin_financing_source_requires_prior_margin_or_rotation_report_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)

            missing_packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )
            rows = {row["source_id"]: row for row in missing_packet["source_rows"]}
            self.assertEqual(rows["margin_financing"]["status"], "hibernated")
            self.assertFalse(rows["margin_financing"]["evidence_present"])

            (reports / "round193_external_margin_credit_neutral_dedup_20260623").mkdir(parents=True)
            present_packet = build_cn_stock_local_source_queue_audit(
                processed_root=processed,
                reports_root=reports,
                provider_request_allowed=False,
            )

        rows = {row["source_id"]: row for row in present_packet["source_rows"]}
        margin_row = rows["margin_financing"]
        self.assertTrue(margin_row["evidence_present"])
        self.assertFalse(margin_row["local_prescreen_allowed"])
        self.assertEqual(present_packet["summary"]["no_provider_ready_source_count"], 0)

    def test_all_non_validation_closed_or_hibernated_sources_require_report_evidence(self) -> None:
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
        required_sources = {
            "financial_statement_adjacent_realized",
            "forecast_express_event",
            "share_unlock_pledge",
            "repurchase_contextual_repair",
            "index_rebalance_passive_flow",
            "dragon_tiger_attention",
            "northbound_hk_hold_daily",
            "margin_financing",
            "daily_basic_direct",
            "calendar_seasonality",
            "listing_age_board_structural",
            "low_turnover_public_technical_alpha101",
        }
        for source_id in required_sources:
            self.assertTrue(rows[source_id]["evidence_required"], source_id)
            self.assertFalse(rows[source_id]["evidence_present"], source_id)
            self.assertFalse(rows[source_id]["local_prescreen_allowed"], source_id)

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
