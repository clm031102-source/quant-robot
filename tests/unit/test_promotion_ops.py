import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.promotion_console import build_promotion_operations_console


class PromotionOperationsConsoleTests(unittest.TestCase):
    def test_console_summarizes_gate_report_and_live_review_blockers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "promotion_report.json"
            provider_path = root / "provider_status.json"
            quality_path = root / "quality_report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "summary": {"candidates": 2, "blocked": 1, "research_only": 0, "paper_ready": 1, "manual_live_review": 0, "duplicates": 1},
                        "candidates": [
                            {
                                "promotion_rank": 1,
                                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                                "market": "CN_ETF",
                                "factor_name": "liquidity_10",
                                "promotion_status": "paper_ready",
                                "score": 42.9,
                                "blocking_reasons": [],
                                "warnings": ["missing_dates_present", "providers_not_ready_for_live_review"],
                                "walk_forward": {"test_sharpe": 0.78, "test_relative_return": 0.05, "test_trades": 76},
                                "paper": {"matched": True, "risk_profile_id": "balanced_fast_guard", "sharpe": 0.52, "max_drawdown": -0.21},
                                "duplicate_of": None,
                            },
                            {
                                "promotion_rank": 2,
                                "case_id": "CN_ETF_liquidity_20_top1_cost5_reb5",
                                "market": "CN_ETF",
                                "factor_name": "liquidity_20",
                                "promotion_status": "blocked",
                                "score": 0.0,
                                "blocking_reasons": ["duplicate_signal_candidate"],
                                "warnings": ["duplicate_of:CN_ETF_liquidity_10_top1_cost5_reb5"],
                                "walk_forward": {"test_sharpe": 0.78, "test_relative_return": 0.05, "test_trades": 76},
                                "paper": {"matched": True, "risk_profile_id": "balanced_fast_guard", "sharpe": 0.52, "max_drawdown": -0.21},
                                "duplicate_of": "CN_ETF_liquidity_10_top1_cost5_reb5",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            provider_path.write_text(
                json.dumps({"providers": {"tushare": {"ready": False, "markets": ["CN", "CN_ETF"], "missing": ["TUSHARE_TOKEN is not set"]}}}),
                encoding="utf-8",
            )
            quality_path.write_text(json.dumps({"duplicate_bars": 0, "missing_date_rows": 3, "zero_volume_rows": 0}), encoding="utf-8")

            paper_observation = {
                "summary": {
                    "observed_candidates": 1,
                    "completed_candidates": 1,
                    "total_guard_events": 10,
                }
            }

            console = build_promotion_operations_console(report_path, provider_path, quality_path, paper_observation)

            self.assertEqual(console["stage"], "phase_2_8_promotion_operations")
            self.assertFalse(console["live_review_allowed"])
            self.assertEqual(console["summary"]["paper_ready"], 1)
            self.assertEqual(console["top_candidate"]["case_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")
            self.assertEqual(console["top_candidate"]["risk_profile_id"], "balanced_fast_guard")
            self.assertIn("providers_not_ready_for_live_review", console["live_review_blockers"])
            self.assertIn("missing_dates_present", console["live_review_blockers"])
            self.assertEqual(console["duplicate_clusters"][0]["canonical_case_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")
            self.assertEqual(console["duplicate_registry_summary"]["duplicate_members"], 1)
            self.assertEqual(console["duplicate_members"][0]["suppression_reason"], "duplicate_signal_candidate")
            self.assertEqual(console["next_actions"][0]["action"], "refresh_data_quality")
            self.assertTrue(console["evidence"]["paper_observation_complete"])
            self.assertFalse(any(action["action"] == "extend_paper_observation" for action in console["next_actions"]))
            self.assertIn("Research only", console["safety"])

    def test_live_review_provider_blockers_are_scoped_to_candidate_market(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_path = root / "promotion_report.json"
            provider_path = root / "provider_status.json"
            quality_path = root / "quality_report.json"
            report_path.write_text(
                json.dumps(
                    {
                        "summary": {"candidates": 1, "blocked": 0, "research_only": 0, "paper_ready": 1, "manual_live_review": 0, "duplicates": 0},
                        "candidates": [
                            {
                                "promotion_rank": 1,
                                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                                "market": "CN_ETF",
                                "factor_name": "liquidity_10",
                                "promotion_status": "paper_ready",
                                "score": 42.9,
                                "blocking_reasons": [],
                                "warnings": ["providers_not_ready_for_live_review"],
                                "walk_forward": {"test_sharpe": 0.78, "test_relative_return": 0.05, "test_trades": 76},
                                "paper": {"matched": True, "risk_profile_id": "balanced_fast_guard", "sharpe": 0.52, "max_drawdown": -0.21},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            provider_path.write_text(
                json.dumps(
                    {
                        "providers": {
                            "akshare": {"ready": True, "markets": ["CN", "CN_ETF"]},
                            "yfinance": {"ready": False, "markets": ["HK", "US"]},
                            "ccxt": {"ready": False, "markets": ["CRYPTO"]},
                        }
                    }
                ),
                encoding="utf-8",
            )
            quality_path.write_text(json.dumps({"duplicate_bars": 0, "missing_date_rows": 0, "zero_volume_rows": 0}), encoding="utf-8")

            console = build_promotion_operations_console(
                report_path,
                provider_path,
                quality_path,
                {"summary": {"observed_candidates": 1, "completed_candidates": 1}},
            )

            self.assertNotIn("providers_not_ready_for_live_review", console["live_review_blockers"])
            self.assertTrue(console["evidence"]["candidate_market_provider_ready"])


if __name__ == "__main__":
    unittest.main()
