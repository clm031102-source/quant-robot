import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.aggressive_turnover_capacity_audit import (
    build_aggressive_turnover_capacity_audit,
    render_aggressive_turnover_capacity_markdown,
    write_aggressive_turnover_capacity_audit,
)


class AggressiveTurnoverCapacityAuditTests(unittest.TestCase):
    def test_flags_high_return_low_turnover_as_capacity_repair_failed_not_promotion(self):
        rows = [
            {
                "case_id": "CN_turnover_rate_low_top100_cost10_reb5",
                "factor_name": "turnover_rate_low",
                "total_return": 51.276,
                "annualized_return": 0.2125,
                "sharpe": 1.983,
                "overlap_autocorr_adjusted_sharpe": 0.961,
                "max_drawdown": -0.184,
                "win_rate": 0.593,
                "mean_rank_ic": 0.1028,
                "rank_ic_t_stat": 13.61,
                "capacity_limited_trades": 1437,
                "max_participation_rate": 166.67,
                "extreme_trade_return_flag": True,
                "relative_return": 27.54,
                "decision_reasons": "['capacity_limited_trades_present']",
            },
            {
                "case_id": "CN_turnover_rate_low_large_mv_top100_cost10_reb5",
                "factor_name": "turnover_rate_low_large_mv",
                "total_return": 0.668,
                "annualized_return": 0.0297,
                "sharpe": 0.457,
                "overlap_autocorr_adjusted_sharpe": 0.244,
                "max_drawdown": -0.366,
                "win_rate": 0.522,
                "mean_rank_ic": 0.0339,
                "rank_ic_t_stat": 3.95,
                "capacity_limited_trades": 0,
                "max_participation_rate": 0.0019,
                "extreme_trade_return_flag": False,
                "relative_return": -23.07,
                "decision_reasons": "['relative_return_below_threshold']",
            },
        ]

        audit = build_aggressive_turnover_capacity_audit(
            rows,
            source_report="round83/leaderboard.csv",
            target_factors=["turnover_rate_low"],
        )

        self.assertEqual(audit["summary"]["raw_high_return_leads"], 1)
        self.assertEqual(audit["summary"]["raw_capacity_blocked_leads"], 1)
        self.assertEqual(audit["summary"]["promotion_review_candidates"], 0)
        self.assertEqual(audit["summary"]["capacity_repair_failed_pairs"], 1)
        pair = audit["pair_audits"][0]
        self.assertEqual(pair["pair_status"], "research_lead_capacity_repair_failed")
        self.assertTrue(pair["raw"]["drawdown_within_user_tolerance"])
        self.assertIn("capacity_limited_trades_present", pair["raw"]["hard_blockers"])
        self.assertIn("extreme_trade_return_flag", pair["raw"]["hard_blockers"])
        self.assertIn("benchmark_relative_return_negative", pair["repair"]["soft_warnings"])
        self.assertIn("overlap_adjusted_sharpe_below_floor", pair["repair"]["soft_warnings"])
        self.assertFalse(pair["repair"]["promotion_review_candidate"])
        self.assertLess(pair["repair"]["total_return_capture_ratio"], 0.05)
        self.assertIn("capacity_repair_not_raw_promotion", audit["recommended_next_actions"])

    def test_marks_capacity_clean_repair_as_review_candidate_under_aggressive_profile(self):
        rows = [
            {
                "case_id": "raw_case",
                "factor_name": "turnover_rate_f_low",
                "total_return": 20.0,
                "annualized_return": 0.18,
                "sharpe": 1.6,
                "overlap_autocorr_adjusted_sharpe": 0.8,
                "max_drawdown": -0.29,
                "mean_rank_ic": 0.08,
                "rank_ic_t_stat": 8.0,
                "capacity_limited_trades": 20,
                "max_participation_rate": 0.2,
                "relative_return": 10.0,
            },
            {
                "case_id": "repair_case",
                "factor_name": "turnover_rate_f_low_large_mv",
                "total_return": 6.0,
                "annualized_return": 0.14,
                "sharpe": 1.2,
                "overlap_autocorr_adjusted_sharpe": 0.75,
                "max_drawdown": -0.27,
                "mean_rank_ic": 0.05,
                "rank_ic_t_stat": 4.0,
                "capacity_limited_trades": 0,
                "max_participation_rate": 0.004,
                "extreme_trade_return_flag": False,
                "relative_return": 1.2,
            },
        ]

        audit = build_aggressive_turnover_capacity_audit(
            rows,
            target_factors=["turnover_rate_f_low"],
            min_repair_overlap_sharpe=0.7,
            min_repair_relative_return=0.0,
        )

        pair = audit["pair_audits"][0]
        self.assertEqual(pair["pair_status"], "capacity_repaired_review_candidate")
        self.assertTrue(pair["repair"]["promotion_review_candidate"])
        self.assertEqual(audit["summary"]["promotion_review_candidates"], 1)
        self.assertIn("walk_forward_oos_validation_for_capacity_repair", audit["recommended_next_actions"])

    def test_writer_emits_json_markdown_and_csv(self):
        audit = build_aggressive_turnover_capacity_audit(
            [
                {
                    "case_id": "raw_case",
                    "factor_name": "turnover_rate_low",
                    "total_return": 3.0,
                    "sharpe": 1.1,
                    "overlap_autocorr_adjusted_sharpe": 0.8,
                    "max_drawdown": -0.2,
                    "capacity_limited_trades": 1,
                    "relative_return": 1.0,
                }
            ],
            target_factors=["turnover_rate_low"],
        )

        markdown = render_aggressive_turnover_capacity_markdown(audit)

        self.assertIn("Aggressive Turnover Capacity Audit", markdown)
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_aggressive_turnover_capacity_audit(output_dir, audit)

            self.assertTrue((output_dir / "aggressive_turnover_capacity_audit.json").exists())
            self.assertTrue((output_dir / "aggressive_turnover_capacity_audit.md").exists())
            self.assertTrue((output_dir / "pair_audits.csv").exists())
            payload = json.loads((output_dir / "aggressive_turnover_capacity_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["pairs"], 1)


if __name__ == "__main__":
    unittest.main()
