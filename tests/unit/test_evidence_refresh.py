import unittest

from quant_robot.ops.evidence_refresh import build_evidence_refresh_plan


class EvidenceRefreshPlanTests(unittest.TestCase):
    def test_refresh_plan_turns_review_blockers_into_ordered_tracks(self):
        review_packet = {
            "stage": "phase_2_9_promotion_review_packet",
            "review_status": "blocked",
            "selected_candidate": {
                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                "market": "CN_ETF",
                "factor_name": "liquidity_10",
                "risk_profile_id": "balanced_fast_guard",
                "promotion_status": "paper_ready",
            },
            "manual_review_gate": {
                "status": "blocked",
                "allowed": False,
                "reasons": ["missing_dates_present", "providers_not_ready_for_live_review", "manual_live_review_not_enabled"],
            },
            "checklist": [
                {"check_id": "research_boundary", "status": "pass", "evidence": "Research only. No broker connection."},
                {"check_id": "provider_readiness", "status": "block", "evidence": "providers_not_ready_for_live_review"},
                {"check_id": "data_quality", "status": "block", "evidence": "missing_date_rows=6, duplicate_bars=0"},
                {"check_id": "paper_observation", "status": "pass", "evidence": "matched=True"},
                {"check_id": "duplicate_cluster", "status": "warn", "evidence": "4 duplicates"},
            ],
            "duplicate_clusters": [{"canonical_case_id": "CN_ETF_liquidity_10_top1_cost5_reb5", "duplicate_count": 4}],
            "evidence": {"providers_ready": False, "missing_date_rows": 6, "duplicate_bars": 0, "zero_volume_rows": 0},
            "next_actions": [{"action": "refresh_data_quality", "reason": "local evidence still has missing coverage"}],
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        }

        plan = build_evidence_refresh_plan(review_packet)

        self.assertEqual(plan["stage"], "phase_3_0_evidence_refresh")
        self.assertEqual(plan["selected_candidate"]["case_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")
        self.assertEqual(plan["refresh_status"], "action_required")
        tracks = {track["track_id"]: track for track in plan["tracks"]}
        self.assertEqual(tracks["data_quality"]["status"], "action_required")
        self.assertEqual(tracks["provider_readiness"]["status"], "action_required")
        self.assertEqual(tracks["paper_observation"]["status"], "continue")
        self.assertEqual(tracks["duplicate_resolution"]["status"], "action_required")
        self.assertEqual(tracks["manual_review_gate"]["status"], "blocked")
        self.assertEqual(plan["ordered_actions"][0]["track_id"], "data_quality")
        commands = " ".join(action["command"] for action in plan["ordered_actions"])
        self.assertIn("run_data_quality_audit.py", commands)
        self.assertIn("run_provider_evidence.py", commands)
        self.assertIn("run_paper_observation.py", commands)
        self.assertIn("run_duplicate_registry.py", commands)
        self.assertIn("run_manual_review_rehearsal.py", commands)
        self.assertIn("run_promotion_review.py", commands)
        self.assertIn("CN_ETF_liquidity_10_top1_cost5_reb5", plan["markdown"])
        self.assertIn("Research only", plan["markdown"])

    def test_provider_track_uses_candidate_market_readiness_evidence(self):
        review_packet = {
            "stage": "phase_2_9_promotion_review_packet",
            "review_status": "blocked",
            "selected_candidate": {
                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                "market": "CN_ETF",
                "promotion_status": "paper_ready",
            },
            "manual_review_gate": {
                "status": "blocked",
                "allowed": False,
                "reasons": ["missing_dates_present", "manual_live_review_not_enabled"],
            },
            "checklist": [
                {"check_id": "provider_readiness", "status": "pass", "evidence": "candidate market providers ready=1/2"},
                {"check_id": "data_quality", "status": "block", "evidence": "missing_date_rows=6"},
                {"check_id": "paper_observation", "status": "pass", "evidence": "matched=True"},
                {"check_id": "duplicate_cluster", "status": "pass", "evidence": "no duplicate cluster"},
            ],
            "duplicate_clusters": [],
            "evidence": {
                "candidate_market_provider_ready": True,
                "candidate_market_ready_providers": 1,
                "candidate_market_providers": 2,
                "providers_ready": False,
                "missing_date_rows": 6,
                "duplicate_bars": 0,
                "zero_volume_rows": 0,
            },
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        }

        plan = build_evidence_refresh_plan(review_packet)

        tracks = {track["track_id"]: track for track in plan["tracks"]}
        self.assertEqual(tracks["provider_readiness"]["status"], "clear")
        self.assertEqual(tracks["provider_readiness"]["evidence"], "candidate market providers ready=1/2")

    def test_completed_paper_observation_is_clear(self):
        review_packet = {
            "stage": "phase_2_9_promotion_review_packet",
            "review_status": "blocked",
            "selected_candidate": {
                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                "market": "CN_ETF",
                "promotion_status": "paper_ready",
            },
            "manual_review_gate": {
                "status": "blocked",
                "allowed": False,
                "reasons": ["missing_dates_present", "manual_live_review_not_enabled"],
            },
            "checklist": [
                {"check_id": "provider_readiness", "status": "pass", "evidence": "candidate market providers ready=1/2"},
                {"check_id": "data_quality", "status": "block", "evidence": "missing_date_rows=6"},
                {"check_id": "paper_observation", "status": "pass", "evidence": "matched=True"},
                {"check_id": "duplicate_cluster", "status": "pass", "evidence": "no duplicate cluster"},
            ],
            "duplicate_clusters": [],
            "evidence": {
                "paper_observation_complete": True,
                "paper_observed_candidates": 5,
                "paper_completed_candidates": 5,
                "missing_date_rows": 6,
                "duplicate_bars": 0,
                "zero_volume_rows": 0,
            },
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        }

        plan = build_evidence_refresh_plan(review_packet)

        tracks = {track["track_id"]: track for track in plan["tracks"]}
        self.assertEqual(tracks["paper_observation"]["status"], "clear")
        self.assertEqual(tracks["paper_observation"]["actions"], [])
        self.assertEqual(tracks["paper_observation"]["evidence"], "observed_candidates=5, completed_candidates=5")
        self.assertNotIn("run_paper_batch.py", " ".join(action["command"] for action in plan["ordered_actions"]))

    def test_refresh_plan_uses_current_gap_provider_and_duplicate_evidence(self):
        review_packet = {
            "stage": "phase_2_9_promotion_review_packet",
            "review_status": "blocked",
            "selected_candidate": {
                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                "market": "CN_ETF",
                "promotion_status": "paper_ready",
            },
            "manual_review_gate": {
                "status": "blocked",
                "allowed": False,
                "reasons": ["missing_dates_present", "manual_live_review_not_enabled"],
            },
            "checklist": [
                {"check_id": "provider_readiness", "status": "pass", "evidence": "candidate market providers ready=1/2"},
                {"check_id": "data_quality", "status": "block", "evidence": "missing_date_rows=6"},
                {"check_id": "paper_observation", "status": "pass", "evidence": "matched=True"},
                {"check_id": "duplicate_cluster", "status": "warn", "evidence": "4 duplicates"},
            ],
            "duplicate_clusters": [{"canonical_case_id": "CN_ETF_liquidity_10_top1_cost5_reb5", "duplicate_count": 4}],
            "evidence": {
                "candidate_market_provider_ready": True,
                "candidate_market_ready_providers": 1,
                "candidate_market_providers": 2,
                "missing_date_rows": 6,
                "duplicate_bars": 0,
                "zero_volume_rows": 0,
            },
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        }

        plan = build_evidence_refresh_plan(
            review_packet,
            data_gap_resolution={
                "summary": {
                    "gap_rows": 6,
                    "blocking_gap_rows": 0,
                    "blocks_api_boundary": False,
                }
            },
            provider_evidence={
                "summary": {"providers": 4, "ready_providers": 3, "parquet_ready": True},
                "market_matrix": [
                    {"market": "CN_ETF", "provider": "akshare", "coverage_status": "implemented_ready", "ready": True},
                    {"market": "CN_ETF", "provider": "tushare", "coverage_status": "implemented_ready", "ready": True},
                ],
            },
            duplicate_registry={"summary": {"duplicate_members": 4, "clusters": 1}},
        )

        tracks = {track["track_id"]: track for track in plan["tracks"]}
        self.assertEqual(tracks["data_quality"]["status"], "clear")
        self.assertEqual(tracks["provider_readiness"]["evidence"], "market=CN_ETF, ready_market_providers=2/2, parquet_ready=True")
        self.assertEqual(tracks["duplicate_resolution"]["status"], "clear")
        self.assertEqual(tracks["manual_review_gate"]["status"], "blocked")
        self.assertEqual(tracks["manual_review_gate"]["evidence"], "manual_live_review_not_enabled")
        commands = " ".join(action["command"] for action in plan["ordered_actions"])
        self.assertNotIn("run_data_quality_audit.py", commands)
        self.assertNotIn("run_provider_evidence.py", commands)
        self.assertNotIn("run_duplicate_registry.py", commands)


if __name__ == "__main__":
    unittest.main()
