import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.ic_portfolio_gap_audit import (
    build_ic_portfolio_gap_audit,
    load_leaderboard_rows,
    render_ic_portfolio_gap_markdown,
    write_ic_portfolio_gap_audit,
)


class IcPortfolioGapAuditTests(unittest.TestCase):
    def test_flags_strong_ic_cases_that_fail_long_only_translation(self):
        rows = [
            {
                "case_id": "strong_ic_failed_long_only",
                "factor_name": "formula_pv_corr_reversal_20",
                "decision_status": "rejected",
                "decision_reasons": "['relative_return_below_threshold']",
                "total_return": 0.1389,
                "relative_return": -23.59,
                "sharpe": 0.18,
                "overlap_autocorr_adjusted_sharpe": 0.11,
                "mean_rank_ic": 0.0757,
                "rank_ic_t_stat": 10.88,
                "long_short_mean_return": 0.0082,
                "capacity_limited_trades": 0,
                "extreme_trade_return_flag": False,
            },
            {
                "case_id": "weak_ic_failed",
                "factor_name": "weak_formula",
                "decision_status": "rejected",
                "decision_reasons": "['relative_return_below_threshold']",
                "total_return": -0.12,
                "relative_return": -1.5,
                "sharpe": -0.3,
                "mean_rank_ic": 0.004,
                "rank_ic_t_stat": 0.3,
                "long_short_mean_return": -0.001,
                "capacity_limited_trades": 0,
                "extreme_trade_return_flag": False,
            },
            {
                "case_id": "strong_ic_capacity_blocked",
                "factor_name": "formula_volume_contraction_reversal_20",
                "decision_status": "rejected",
                "decision_reasons": "['relative_return_below_threshold', 'capacity_limited_trades_present']",
                "total_return": -0.03,
                "relative_return": -23.8,
                "sharpe": 0.02,
                "mean_rank_ic": 0.0802,
                "rank_ic_t_stat": 10.25,
                "long_short_mean_return": 0.0108,
                "capacity_limited_trades": 3,
                "extreme_trade_return_flag": False,
            },
        ]

        audit = build_ic_portfolio_gap_audit(rows, source_report="round12.csv")

        self.assertEqual(audit["summary"]["cases"], 3)
        self.assertEqual(audit["summary"]["strong_rank_ic_cases"], 2)
        self.assertEqual(audit["summary"]["ic_to_portfolio_gap_cases"], 2)
        self.assertEqual(audit["summary"]["exclusion_signal_cases"], 2)
        self.assertEqual(audit["summary"]["capacity_limited_cases"], 1)
        self.assertEqual(audit["summary"]["promotable_long_only_cases"], 0)
        self.assertIn("bottom_quantile_exclusion_overlay", audit["recommended_next_actions"])
        self.assertIn("capacity_filter_or_liquidity_gate", audit["recommended_next_actions"])
        self.assertIn("stop_raw_formula_topn_sweeps", audit["recommended_next_actions"])

        by_case = {row["case_id"]: row for row in audit["case_audits"]}
        self.assertEqual(by_case["strong_ic_failed_long_only"]["translation_status"], "translation_gap")
        self.assertIn("strong_rank_ic", by_case["strong_ic_failed_long_only"]["tags"])
        self.assertIn("exclusion_signal_candidate", by_case["strong_ic_failed_long_only"]["tags"])
        self.assertEqual(by_case["weak_ic_failed"]["translation_status"], "weak_or_unproven_signal")
        self.assertIn("capacity_blocked", by_case["strong_ic_capacity_blocked"]["tags"])

        by_factor = {row["factor_name"]: row for row in audit["factor_summary"]}
        self.assertEqual(by_factor["formula_pv_corr_reversal_20"]["strong_rank_ic_cases"], 1)
        self.assertEqual(by_factor["formula_volume_contraction_reversal_20"]["capacity_limited_cases"], 1)

    def test_writer_emits_json_markdown_and_case_csv(self):
        audit = build_ic_portfolio_gap_audit(
            [
                {
                    "case_id": "case_a",
                    "factor_name": "factor_a",
                    "total_return": 0.2,
                    "relative_return": -0.1,
                    "sharpe": 0.2,
                    "mean_rank_ic": 0.04,
                    "rank_ic_t_stat": 3.0,
                    "long_short_mean_return": 0.006,
                    "capacity_limited_trades": 0,
                }
            ],
            source_report="leaderboard.csv",
        )

        markdown = render_ic_portfolio_gap_markdown(audit)

        self.assertIn("IC-to-Portfolio Gap Audit", markdown)
        self.assertIn("bottom_quantile_exclusion_overlay", markdown)
        with tempfile.TemporaryDirectory() as tmp:
            write_ic_portfolio_gap_audit(tmp, audit)

            self.assertTrue((Path(tmp) / "ic_portfolio_gap_audit.json").exists())
            self.assertTrue((Path(tmp) / "ic_portfolio_gap_audit.md").exists())
            self.assertTrue((Path(tmp) / "case_audits.csv").exists())
            self.assertTrue((Path(tmp) / "factor_summary.csv").exists())

    def test_load_leaderboard_rows_accepts_partial_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "partial_leaderboard.jsonl"
            path.write_text(
                '{"case_id": "case_a", "factor_name": "factor_a"}\n'
                '{"case_id": "case_b", "factor_name": "factor_b"}\n',
                encoding="utf-8",
            )

            rows = load_leaderboard_rows(path)

        self.assertEqual([row["case_id"] for row in rows], ["case_a", "case_b"])


if __name__ == "__main__":
    unittest.main()
