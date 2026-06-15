import unittest

from quant_robot.ops.review_packet import build_promotion_review_packet


class PromotionReviewPacketTests(unittest.TestCase):
    def test_review_packet_turns_ops_console_into_auditable_candidate_packet(self):
        console = {
            "stage": "phase_2_8_promotion_operations",
            "generated_at": "2026-06-01T00:00:00+00:00",
            "source_report": "data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json",
            "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
            "summary": {"candidates": 2, "blocked": 1, "research_only": 0, "paper_ready": 1, "manual_live_review": 0, "duplicates": 1},
            "live_review_allowed": False,
            "live_review_blockers": ["providers_not_ready_for_live_review", "missing_dates_present", "manual_live_review_not_enabled"],
            "top_candidate": {
                "rank": 1,
                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                "market": "CN_ETF",
                "factor_name": "liquidity_10",
                "promotion_status": "paper_ready",
                "score": 42.9617,
                "risk_profile_id": "balanced_fast_guard",
                "paper_matched": True,
                "paper_sharpe": 0.5247,
                "paper_max_drawdown": -0.2141,
                "test_sharpe": 0.7846,
                "test_relative_return": 0.0564,
                "test_trades": 76,
                "blocking_reasons": [],
                "warnings": ["missing_dates_present", "providers_not_ready_for_live_review"],
                "duplicate_of": None,
            },
            "candidates": [],
            "duplicate_clusters": [
                {
                    "canonical_case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                    "duplicate_count": 1,
                    "duplicates": ["CN_ETF_liquidity_20_top1_cost5_reb5"],
                }
            ],
            "duplicate_registry_summary": {"canonical_candidates": 1, "duplicate_members": 1, "clusters": 1},
            "evidence": {
                "provider_status_present": True,
                "quality_report_present": True,
                "providers_ready": False,
                "candidate_market_provider_ready": True,
                "candidate_market_ready_providers": 1,
                "candidate_market_providers": 2,
                "missing_date_rows": 3,
            },
            "next_actions": [{"action": "refresh_data_quality", "reason": "local evidence still has missing or stale quality coverage"}],
        }

        packet = build_promotion_review_packet(console)

        self.assertEqual(packet["stage"], "phase_2_9_promotion_review_packet")
        self.assertEqual(packet["selected_candidate"]["case_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")
        self.assertEqual(packet["review_status"], "blocked")
        checklist = {item["check_id"]: item for item in packet["checklist"]}
        self.assertEqual(checklist["research_boundary"]["status"], "pass")
        self.assertEqual(checklist["provider_readiness"]["status"], "pass")
        self.assertEqual(checklist["data_quality"]["status"], "block")
        self.assertEqual(checklist["paper_observation"]["status"], "pass")
        self.assertEqual(checklist["duplicate_cluster"]["status"], "warn")
        self.assertEqual(packet["duplicate_registry_summary"]["duplicate_members"], 1)
        self.assertEqual(packet["manual_review_gate"]["status"], "blocked")
        self.assertIn("CN_ETF_liquidity_10_top1_cost5_reb5", packet["markdown"])
        self.assertIn("Research only", packet["markdown"])
        self.assertIn("refresh_data_quality", packet["markdown"])


if __name__ == "__main__":
    unittest.main()
