import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_desktop_validation_summary import build_desktop_validation_summary, run_desktop_validation_summary


class DesktopValidationSummaryTests(unittest.TestCase):
    def test_build_summary_includes_walk_forward_counts_and_promotion_blockers(self):
        rows = [
            {
                "case_id": "CN_large_resid_liq_vol_amt_gate_20_top5_cost20_reb1_regime150",
                "validation_status": "accepted",
                "factor_name": "large_resid_liq_vol_amt_gate_20",
                "regime_lookback": "150",
                "top_n": "5",
                "cost_bps": "20",
                "mean_test_sharpe": "1.2",
                "mean_test_relative_return": "0.3",
                "worst_test_max_drawdown": "-0.2",
                "accepted_folds": "2",
                "folds": "2",
                "adjusted_ic_p_value": "0.01",
            },
            {
                "case_id": "CN_large_resid_liq_vol_amt_20_top20_cost30_reb1_regime120",
                "validation_status": "rejected",
                "factor_name": "large_resid_liq_vol_amt_20",
                "regime_lookback": "120",
                "top_n": "20",
                "cost_bps": "30",
                "mean_test_sharpe": "-0.1",
                "mean_test_relative_return": "-0.2",
                "worst_test_max_drawdown": "-0.5",
                "accepted_folds": "0",
                "folds": "2",
                "adjusted_ic_p_value": "1.0",
            },
        ]
        promotion = {
            "summary": {"blocked": 1, "research_only": 1, "paper_ready": 0},
            "candidates": [
                {
                    "case_id": "CN_large_resid_liq_vol_amt_20_top20_cost30_reb1_regime120",
                    "promotion_status": "blocked",
                    "blocking_reasons": ["walk_forward_not_accepted", "oos_drawdown_above_limit"],
                }
            ],
        }

        summary = build_desktop_validation_summary(
            rows,
            promotion_report=promotion,
            generated_at="2026-06-16 16:30:00 +08:00",
        )

        self.assertIn("Accepted: 1 / 2", summary)
        self.assertIn("large_resid_liq_vol_amt_gate_20", summary)
        self.assertIn("regime=150", summary)
        self.assertIn("walk_forward_not_accepted", summary)
        self.assertIn("research-to-paper only", summary)

    def test_run_summary_reads_files_and_writes_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaderboard = root / "walk_forward_leaderboard.csv"
            leaderboard.write_text(
                "case_id,validation_status,factor_name,regime_lookback,top_n,cost_bps,mean_test_sharpe\n"
                "case_a,accepted,large_resid_liq_vol_amt_gate_20,150,5,20,1.2\n",
                encoding="utf-8",
            )
            promotion = root / "promotion_report.json"
            promotion.write_text(json.dumps({"summary": {"research_only": 1}, "candidates": []}), encoding="utf-8")
            output = root / "summary.md"

            result = run_desktop_validation_summary(
                walk_forward_leaderboard=leaderboard,
                promotion_report=promotion,
                output=output,
                generated_at="2026-06-16 16:30:00 +08:00",
            )

            self.assertEqual(result, output)
            self.assertTrue(output.exists())
            self.assertIn("case_a", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
