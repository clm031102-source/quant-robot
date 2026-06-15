import unittest

from quant_robot.ops.manual_review_rehearsal import build_manual_review_rehearsal


class ManualReviewRehearsalTests(unittest.TestCase):
    def test_rehearsal_blocks_manual_review_without_crossing_live_boundaries(self):
        review_packet = {
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
            "manual_review_gate": {
                "allowed": False,
                "reasons": ["missing_dates_present", "providers_not_ready_for_live_review", "manual_live_review_not_enabled"],
            },
            "selected_candidate": {"case_id": "case_a", "promotion_status": "paper_ready"},
        }
        data_quality = {"summary": {"missing_date_rows": 6}}
        provider_evidence = {"summary": {"providers": 4, "ready_providers": 0, "parquet_ready": False}}
        paper_observation = {"summary": {"observed_candidates": 1, "completed_candidates": 1}}
        duplicate_registry = {"summary": {"duplicate_members": 4, "clusters": 1}}

        rehearsal = build_manual_review_rehearsal(
            review_packet,
            data_quality=data_quality,
            provider_evidence=provider_evidence,
            paper_observation=paper_observation,
            duplicate_registry=duplicate_registry,
        )

        self.assertEqual(rehearsal["stage"], "phase_3_5_manual_review_gate_rehearsal")
        self.assertEqual(rehearsal["gate_status"], "blocked")
        self.assertFalse(rehearsal["dry_run"]["would_cross_live_boundary"])
        requirements = {item["requirement_id"]: item for item in rehearsal["requirements"]}
        self.assertEqual(requirements["research_boundary"]["status"], "pass")
        self.assertEqual(requirements["data_quality_clean"]["status"], "block")
        self.assertEqual(requirements["provider_readiness"]["status"], "block")
        self.assertEqual(requirements["paper_observation"]["status"], "pass")
        self.assertEqual(requirements["duplicate_registry_review"]["status"], "warn")
        self.assertIn("missing_dates_present", rehearsal["blockers"])
        self.assertIn("No broker", rehearsal["markdown"])

    def test_provider_requirement_is_scoped_to_selected_candidate_market(self):
        review_packet = {
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
            "manual_review_gate": {"allowed": False, "reasons": ["manual_live_review_not_enabled"]},
            "selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "promotion_status": "paper_ready"},
        }
        provider_evidence = {
            "summary": {"providers": 4, "ready_providers": 1, "parquet_ready": True},
            "market_matrix": [
                {"market": "CN_ETF", "provider": "akshare", "coverage_status": "implemented_ready", "ready": True},
                {"market": "HK", "provider": "yfinance", "coverage_status": "implemented_blocked", "ready": False},
            ],
        }

        rehearsal = build_manual_review_rehearsal(
            review_packet,
            data_quality={"summary": {"missing_date_rows": 0}},
            provider_evidence=provider_evidence,
            paper_observation={"summary": {"observed_candidates": 1, "completed_candidates": 1}},
            duplicate_registry={"summary": {"duplicate_members": 0, "clusters": 0}},
        )

        requirements = {item["requirement_id"]: item for item in rehearsal["requirements"]}
        self.assertEqual(requirements["provider_readiness"]["status"], "pass")
        self.assertIn("market=CN_ETF", requirements["provider_readiness"]["evidence"])

    def test_nonblocking_gap_resolution_clears_manual_review_missing_date_blockers(self):
        review_packet = {
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
            "manual_review_gate": {
                "allowed": False,
                "reasons": ["missing_dates_present", "manual_live_review_not_enabled"],
            },
            "selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "promotion_status": "paper_ready"},
        }
        data_gap_resolution = {
            "summary": {
                "gap_rows": 6,
                "blocking_gap_rows": 0,
                "blocks_api_boundary": False,
            }
        }

        rehearsal = build_manual_review_rehearsal(
            review_packet,
            data_quality={"summary": {"missing_date_rows": 6, "duplicate_bars": 0, "zero_volume_rows": 0}},
            data_gap_resolution=data_gap_resolution,
            provider_evidence={
                "summary": {"providers": 4, "ready_providers": 3, "parquet_ready": True},
                "market_matrix": [
                    {"market": "CN_ETF", "provider": "akshare", "coverage_status": "implemented_ready", "ready": True},
                    {"market": "CN_ETF", "provider": "tushare", "coverage_status": "implemented_ready", "ready": True},
                ],
            },
            paper_observation={"summary": {"observed_candidates": 1, "completed_candidates": 1}},
            duplicate_registry={"summary": {"duplicate_members": 4, "clusters": 1}},
        )

        requirements = {item["requirement_id"]: item for item in rehearsal["requirements"]}
        self.assertEqual(requirements["data_quality_clean"]["status"], "pass")
        self.assertIn("gap_resolution=non_blocking", requirements["data_quality_clean"]["evidence"])
        self.assertNotIn("missing_dates_present", rehearsal["blockers"])
        self.assertNotIn("data_quality_clean_blocked", rehearsal["blockers"])
        self.assertEqual(rehearsal["blockers"], ["manual_live_review_not_enabled", "manual_live_review_enabled_blocked"])


if __name__ == "__main__":
    unittest.main()
