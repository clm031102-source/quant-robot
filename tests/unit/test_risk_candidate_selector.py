import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.risk_candidate_selector import build_risk_candidate_pack, write_risk_candidate_pack


class RiskCandidateSelectorTests(unittest.TestCase):
    def test_selects_candidate_that_passes_walk_forward_paper_and_daily_risk(self):
        promotion = {
            "candidates": [
                {
                    "case_id": "current_case",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_10",
                    "promotion_rank": 1,
                    "score": 40.0,
                    "duplicate_of": None,
                    "walk_forward": {
                        "validation_status": "accepted",
                        "test_sharpe": 0.8,
                        "test_relative_return": 0.05,
                        "test_max_drawdown": -0.22,
                        "test_trades": 80,
                    },
                    "paper": {"matched": True, "sharpe": 0.6, "max_drawdown": -0.12, "total_return": 0.2},
                },
                {
                    "case_id": "safer_case",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_20",
                    "promotion_rank": 2,
                    "score": 30.0,
                    "duplicate_of": None,
                    "walk_forward": {
                        "validation_status": "accepted",
                        "test_sharpe": 0.7,
                        "test_relative_return": 0.03,
                        "test_max_drawdown": -0.12,
                        "test_trades": 60,
                    },
                    "paper": {"matched": True, "sharpe": 0.55, "max_drawdown": -0.08, "total_return": 0.12},
                },
                {
                    "case_id": "duplicate_case",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_120",
                    "promotion_rank": 3,
                    "score": 35.0,
                    "duplicate_of": "safer_case",
                    "walk_forward": {
                        "validation_status": "accepted",
                        "test_sharpe": 0.9,
                        "test_relative_return": 0.04,
                        "test_max_drawdown": -0.10,
                        "test_trades": 70,
                    },
                    "paper": {"matched": True, "sharpe": 0.65, "max_drawdown": -0.07, "total_return": 0.15},
                },
            ]
        }
        daily = {
            "candidate": {"case_id": "current_case"},
            "decision": {"status": "blocked", "non_manual_blocking_reasons": ["risk_max_drawdown_breach"]},
        }

        pack = build_risk_candidate_pack(promotion, daily, max_drawdown_limit=0.2)

        self.assertEqual(pack["stage"], "phase_5_1_risk_candidate_selector")
        self.assertEqual(pack["selection_status"], "risk_candidate_selected")
        self.assertEqual(pack["selected_candidate"]["case_id"], "safer_case")
        self.assertEqual(pack["summary"]["risk_eligible_candidates"], 1)
        current = next(row for row in pack["candidates"] if row["case_id"] == "current_case")
        self.assertIn("walk_forward_drawdown_breach", current["rejection_reasons"])
        self.assertIn("daily_ops_current_candidate_blocked", current["rejection_reasons"])
        duplicate = next(row for row in pack["candidates"] if row["case_id"] == "duplicate_case")
        self.assertIn("duplicate_candidate", duplicate["rejection_reasons"])
        self.assertFalse(pack["live_boundary_allowed"])

    def test_no_eligible_candidate_fails_closed_with_next_actions(self):
        promotion = {
            "candidates": [
                {
                    "case_id": "case_a",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_10",
                    "promotion_rank": 1,
                    "duplicate_of": None,
                    "walk_forward": {
                        "validation_status": "accepted",
                        "test_sharpe": 0.8,
                        "test_relative_return": 0.04,
                        "test_max_drawdown": -0.25,
                        "test_trades": 80,
                    },
                    "paper": {"matched": True, "sharpe": 0.6, "max_drawdown": -0.21, "total_return": 0.2},
                }
            ]
        }

        pack = build_risk_candidate_pack(promotion, {"decision": {"status": "blocked"}}, max_drawdown_limit=0.2)

        self.assertEqual(pack["selection_status"], "no_risk_eligible_candidate")
        self.assertIsNone(pack["selected_candidate"])
        self.assertFalse(pack["paper_trading_allowed"])
        self.assertIn("run_constrained_candidate_search", [item["action"] for item in pack["next_actions"]])

    def test_aggressive_growth_tier_can_select_high_return_candidate_without_live_boundary(self):
        promotion = {
            "candidates": [
                {
                    "case_id": "strict_case",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_10",
                    "promotion_rank": 1,
                    "score": 30.0,
                    "duplicate_of": None,
                    "walk_forward": {
                        "validation_status": "accepted",
                        "test_sharpe": 0.7,
                        "test_relative_return": 0.03,
                        "test_max_drawdown": -0.16,
                        "test_trades": 80,
                    },
                    "paper": {"matched": True, "sharpe": 0.58, "max_drawdown": -0.12, "total_return": 0.18},
                },
                {
                    "case_id": "aggressive_case",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_20",
                    "promotion_rank": 2,
                    "score": 42.0,
                    "duplicate_of": None,
                    "walk_forward": {
                        "validation_status": "accepted",
                        "test_sharpe": 0.9,
                        "test_relative_return": 0.09,
                        "test_max_drawdown": -0.27,
                        "test_trades": 100,
                    },
                    "paper": {"matched": True, "sharpe": 0.62, "max_drawdown": -0.28, "total_return": 0.95},
                },
            ]
        }
        tiers = [
            {
                "tier_id": "capital_preservation",
                "label": "Capital Preservation",
                "max_drawdown_limit": 0.20,
                "min_walk_forward_sharpe": 0.3,
                "min_relative_return": 0.0,
                "min_paper_sharpe": 0.5,
                "min_paper_calmar": 1.0,
                "min_trades": 20,
                "priority": 1,
            },
            {
                "tier_id": "aggressive_growth",
                "label": "Aggressive Growth",
                "max_drawdown_limit": 0.30,
                "min_walk_forward_sharpe": 0.3,
                "min_relative_return": 0.0,
                "min_paper_sharpe": 0.5,
                "min_paper_calmar": 1.0,
                "min_trades": 20,
                "priority": 3,
            },
        ]

        pack = build_risk_candidate_pack(
            promotion,
            {"decision": {"status": "blocked"}},
            max_drawdown_limit=0.2,
            risk_tiers=tiers,
            primary_risk_tier="capital_preservation",
        )

        self.assertEqual(pack["stage"], "phase_5_4_risk_tier_policy")
        self.assertEqual(pack["selection_status"], "risk_tier_candidate_selected")
        self.assertEqual(pack["selected_candidate"]["case_id"], "aggressive_case")
        self.assertEqual(pack["selected_candidate"]["risk_tier"], "aggressive_growth")
        self.assertFalse(pack["selected_candidate"]["live_order_allowed"])
        self.assertFalse(pack["live_boundary_allowed"])
        self.assertEqual(pack["summary"]["tier_eligible_candidates"], 2)
        self.assertEqual(pack["summary"]["risk_tier_counts"]["aggressive_growth"], 1)
        aggressive = next(row for row in pack["candidates"] if row["case_id"] == "aggressive_case")
        self.assertIn("aggressive_growth", aggressive["eligible_risk_tiers"])
        self.assertIn("walk_forward_drawdown_breach", aggressive["risk_tier_rejections"]["capital_preservation"])

    def test_write_risk_candidate_pack_outputs_json_markdown_and_csvs(self):
        pack = build_risk_candidate_pack(
            {"candidates": []},
            {"decision": {"status": "blocked"}},
            max_drawdown_limit=0.2,
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_risk_candidate_pack(output_dir, pack)

            self.assertTrue((output_dir / "risk_candidate_pack.json").exists())
            self.assertTrue((output_dir / "risk_candidate_pack.md").exists())
            self.assertTrue((output_dir / "risk_candidate_candidates.csv").exists())
            self.assertTrue((output_dir / "risk_candidate_summary.csv").exists())
            self.assertIn("risk_eligible_candidates", (output_dir / "risk_candidate_summary.csv").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
