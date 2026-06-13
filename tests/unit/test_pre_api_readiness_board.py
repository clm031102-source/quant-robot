import unittest

from quant_robot.ops.pre_api_readiness_board import build_pre_api_readiness_board


class PreApiReadinessBoardTests(unittest.TestCase):
    def test_board_consolidates_evidence_tracks_blockers_and_actions(self):
        review_packet = {
            "selected_candidate": {"case_id": "case_a", "promotion_status": "paper_ready"},
            "manual_review_gate": {
                "allowed": False,
                "reasons": ["missing_dates_present", "providers_not_ready_for_live_review"],
            },
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        }
        data_quality = {"summary": {"missing_date_rows": 6, "duplicate_bars": 0, "zero_volume_rows": 0}}
        data_gap_resolution = {
            "summary": {
                "gap_rows": 6,
                "blocking_gap_rows": 6,
                "blocks_api_boundary": True,
                "needs_review": 6,
            }
        }
        provider_evidence = {"summary": {"providers": 4, "ready_providers": 0, "parquet_ready": False}}
        provider_remediation = {
            "summary": {
                "remediation_items": 7,
                "dependency_items": 4,
                "credential_items": 1,
                "adapter_items": 1,
                "storage_items": 1,
                "blocks_api_boundary": True,
            }
        }
        paper_observation = {"summary": {"observed_candidates": 5, "completed_candidates": 5, "total_guard_events": 3550}}
        duplicate_registry = {"summary": {"duplicate_members": 4, "clusters": 1}}
        manual_rehearsal = {
            "gate_status": "blocked",
            "blockers": ["data_quality_clean_blocked", "provider_readiness_blocked"],
            "dry_run": {
                "would_cross_live_boundary": False,
                "broker_connection": "disabled",
                "account_reads": "disabled",
                "order_placement": "disabled",
            },
        }
        evidence_refresh = {
            "refresh_status": "action_required",
            "ordered_actions": [
                {"priority": 1, "track_id": "data_quality", "command": "python scripts\\run_data_quality_audit.py", "reason": "audit gaps"},
                {"priority": 2, "track_id": "provider_readiness", "command": "python scripts\\run_provider_evidence.py", "reason": "audit providers"},
            ],
        }

        board = build_pre_api_readiness_board(
            review_packet=review_packet,
            data_quality=data_quality,
            data_gap_resolution=data_gap_resolution,
            provider_evidence=provider_evidence,
            provider_remediation=provider_remediation,
            paper_observation=paper_observation,
            duplicate_registry=duplicate_registry,
            manual_rehearsal=manual_rehearsal,
            evidence_refresh=evidence_refresh,
        )

        self.assertEqual(board["stage"], "phase_4_0_pre_api_readiness_board")
        self.assertEqual(board["overall_status"], "blocked")
        self.assertFalse(board["boundary"]["would_cross_live_boundary"])
        items = {item["track_id"]: item for item in board["readiness_items"]}
        self.assertEqual(items["data_quality"]["status"], "block")
        self.assertEqual(items["data_gap_resolution"]["status"], "block")
        self.assertIn("blocking_gap_rows=6", items["data_gap_resolution"]["evidence"])
        self.assertEqual(items["provider_readiness"]["status"], "block")
        self.assertEqual(items["provider_remediation"]["status"], "block")
        self.assertIn("remediation_items=7", items["provider_remediation"]["evidence"])
        self.assertEqual(items["paper_observation"]["status"], "pass")
        self.assertEqual(items["duplicate_registry"]["status"], "warn")
        self.assertEqual(items["manual_review_gate"]["status"], "block")
        blockers = {item["blocker_id"]: item for item in board["blocker_register"]}
        self.assertIn("data_quality_missing_dates", blockers)
        self.assertIn("data_gap_resolution_blocking_gaps", blockers)
        self.assertIn("provider_readiness_not_ready", blockers)
        self.assertIn("provider_remediation_items_open", blockers)
        self.assertEqual(board["next_local_actions"][0]["command"], "python scripts\\run_data_quality_audit.py")
        self.assertTrue(any("run_data_gap_evidence.py" in action["command"] for action in board["next_local_actions"]))
        self.assertTrue(any("run_data_gap_resolution.py" in action["command"] for action in board["next_local_actions"]))
        self.assertTrue(any("run_provider_remediation.py" in action["command"] for action in board["next_local_actions"]))
        self.assertIn("No broker", board["markdown"])

    def test_provider_remediation_can_clear_when_reviewed_items_are_non_blocking(self):
        review_packet = {
            "selected_candidate": {"case_id": "case_a", "promotion_status": "paper_ready"},
            "manual_review_gate": {"allowed": True, "reasons": []},
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        }
        provider_remediation = {
            "summary": {
                "remediation_items": 2,
                "blocking_remediation_items": 0,
                "dependency_items": 2,
                "credential_items": 0,
                "adapter_items": 0,
                "storage_items": 0,
                "blocks_api_boundary": False,
            }
        }

        board = build_pre_api_readiness_board(
            review_packet=review_packet,
            data_quality={"summary": {"missing_date_rows": 0, "duplicate_bars": 0, "zero_volume_rows": 0}},
            provider_evidence={"summary": {"providers": 1, "ready_providers": 1, "parquet_ready": True}},
            provider_remediation=provider_remediation,
            paper_observation={"summary": {"observed_candidates": 1, "completed_candidates": 1, "total_guard_events": 0}},
            duplicate_registry={"summary": {"duplicate_members": 0, "clusters": 0}},
            manual_rehearsal={"gate_status": "ready", "blockers": [], "dry_run": {"would_cross_live_boundary": False}},
            evidence_refresh={"refresh_status": "clear", "ordered_actions": []},
        )

        items = {item["track_id"]: item for item in board["readiness_items"]}
        self.assertEqual(items["provider_remediation"]["status"], "pass")
        self.assertIn("blocking_remediation_items=0", items["provider_remediation"]["evidence"])

    def test_provider_readiness_is_scoped_to_selected_candidate_market(self):
        review_packet = {
            "selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "promotion_status": "paper_ready"},
            "manual_review_gate": {"allowed": True, "reasons": []},
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        }
        provider_evidence = {
            "summary": {"providers": 4, "ready_providers": 1, "parquet_ready": True},
            "market_matrix": [
                {"market": "CN_ETF", "provider": "akshare", "coverage_status": "implemented_ready", "ready": True},
                {"market": "CN_ETF", "provider": "tushare", "coverage_status": "implemented_blocked", "ready": False},
                {"market": "HK", "provider": "yfinance", "coverage_status": "implemented_blocked", "ready": False},
                {"market": "CRYPTO", "provider": "ccxt", "coverage_status": "implemented_blocked", "ready": False},
            ],
        }

        board = build_pre_api_readiness_board(
            review_packet=review_packet,
            data_quality={"summary": {"missing_date_rows": 0, "duplicate_bars": 0, "zero_volume_rows": 0}},
            provider_evidence=provider_evidence,
            paper_observation={"summary": {"observed_candidates": 1, "completed_candidates": 1, "total_guard_events": 0}},
            duplicate_registry={"summary": {"duplicate_members": 0, "clusters": 0}},
            manual_rehearsal={"gate_status": "ready", "blockers": [], "dry_run": {"would_cross_live_boundary": False}},
            evidence_refresh={"refresh_status": "clear", "ordered_actions": []},
        )

        items = {item["track_id"]: item for item in board["readiness_items"]}
        self.assertEqual(items["provider_readiness"]["status"], "pass")
        self.assertIn("market=CN_ETF", items["provider_readiness"]["evidence"])
        self.assertIn("ready_market_providers=1/2", items["provider_readiness"]["evidence"])

    def test_nonblocking_gap_resolution_clears_missing_date_readiness_blockers(self):
        review_packet = {
            "selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "promotion_status": "paper_ready"},
            "manual_review_gate": {"allowed": False, "reasons": ["missing_dates_present"]},
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        }
        data_quality = {"summary": {"missing_date_rows": 2, "duplicate_bars": 0, "zero_volume_rows": 0}}
        data_gap_resolution = {
            "summary": {
                "gap_rows": 2,
                "blocking_gap_rows": 0,
                "blocks_api_boundary": False,
                "needs_review": 0,
                "accepted_non_trading_day": 1,
                "accepted_suspension_or_no_trade": 1,
            }
        }

        board = build_pre_api_readiness_board(
            review_packet=review_packet,
            data_quality=data_quality,
            data_gap_resolution=data_gap_resolution,
            provider_evidence={
                "summary": {"providers": 2, "ready_providers": 1, "parquet_ready": True},
                "market_matrix": [{"market": "CN_ETF", "provider": "akshare", "coverage_status": "implemented_ready", "ready": True}],
            },
            paper_observation={"summary": {"observed_candidates": 1, "completed_candidates": 1, "total_guard_events": 0}},
            duplicate_registry={"summary": {"duplicate_members": 0, "clusters": 0}},
            manual_rehearsal={"gate_status": "blocked", "blockers": ["missing_dates_present"], "dry_run": {"would_cross_live_boundary": False}},
            evidence_refresh={"refresh_status": "clear", "ordered_actions": []},
        )

        items = {item["track_id"]: item for item in board["readiness_items"]}
        blockers = {item["blocker_id"]: item for item in board["blocker_register"]}
        self.assertEqual(items["data_quality"]["status"], "pass")
        self.assertEqual(items["data_gap_resolution"]["status"], "pass")
        self.assertEqual(items["manual_review_gate"]["status"], "pass")
        self.assertNotIn("data_quality_missing_dates", blockers)
        self.assertNotIn("missing_dates_present", blockers)

    def test_manual_live_review_disabled_is_reported_as_one_blocker(self):
        review_packet = {
            "selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "promotion_status": "paper_ready"},
            "manual_review_gate": {"allowed": False, "reasons": ["manual_live_review_not_enabled"]},
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        }

        board = build_pre_api_readiness_board(
            review_packet=review_packet,
            data_quality={"summary": {"missing_date_rows": 0, "duplicate_bars": 0, "zero_volume_rows": 0}},
            data_gap_resolution={"summary": {"gap_rows": 0, "blocking_gap_rows": 0, "blocks_api_boundary": False}},
            provider_evidence={
                "summary": {"providers": 2, "ready_providers": 2, "parquet_ready": True},
                "market_matrix": [
                    {"market": "CN_ETF", "provider": "akshare", "coverage_status": "implemented_ready", "ready": True},
                    {"market": "CN_ETF", "provider": "tushare", "coverage_status": "implemented_ready", "ready": True},
                ],
            },
            provider_remediation={"summary": {"remediation_items": 0, "blocking_remediation_items": 0, "blocks_api_boundary": False}},
            paper_observation={"summary": {"observed_candidates": 1, "completed_candidates": 1, "total_guard_events": 0}},
            duplicate_registry={"summary": {"duplicate_members": 0, "clusters": 0}},
            manual_rehearsal={
                "gate_status": "blocked",
                "blockers": ["manual_live_review_not_enabled", "manual_live_review_enabled_blocked"],
                "dry_run": {"would_cross_live_boundary": False},
            },
            evidence_refresh={"refresh_status": "action_required", "ordered_actions": []},
        )

        blocker_ids = [item["blocker_id"] for item in board["blocker_register"]]
        self.assertEqual(blocker_ids, ["manual_live_review_not_enabled"])
        self.assertEqual(board["summary"]["blockers"], 1)


if __name__ == "__main__":
    unittest.main()
