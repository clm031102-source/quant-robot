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
                "mean_test_annualized_return": "0.18",
                "test_overlap_autocorr_adjusted_sharpe": "0.8",
                "test_overlap_effective_sample_size": "42",
                "test_overlap_risk_flag": "True",
                "mean_test_relative_return": "0.3",
                "mean_test_win_rate": "0.61",
                "worst_test_max_drawdown": "-0.2",
                "total_test_trades": "88",
                "test_capacity_limited_trades": "0",
                "test_max_participation_rate": "0.04",
                "accepted_folds": "2",
                "folds": "2",
                "adjusted_ic_p_value": "0.01",
                "test_tail_ic_p_value": "0.40",
                "test_tail_significance_status": "not_significant",
            },
            {
                "case_id": "CN_large_resid_liq_vol_amt_20_top20_cost30_reb1_regime120",
                "validation_status": "rejected",
                "factor_name": "large_resid_liq_vol_amt_20",
                "regime_lookback": "120",
                "top_n": "20",
                "cost_bps": "30",
                "mean_test_sharpe": "-0.1",
                "test_overlap_autocorr_adjusted_sharpe": "-0.2",
                "test_overlap_effective_sample_size": "18",
                "test_overlap_risk_flag": "False",
                "mean_test_relative_return": "-0.2",
                "worst_test_max_drawdown": "-0.5",
                "accepted_folds": "0",
                "folds": "2",
                "adjusted_ic_p_value": "1.0",
                "test_tail_ic_p_value": "1.0",
                "test_tail_significance_status": "insufficient_data",
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
        self.assertIn("Tail IC p", summary)
        self.assertIn("Adj Sharpe", summary)
        self.assertIn("Ann Ret", summary)
        self.assertIn("Win Rate", summary)
        self.assertIn("Trades", summary)
        self.assertIn("Cap Trades", summary)
        self.assertIn("Max Part", summary)
        self.assertIn("0.18", summary)
        self.assertIn("0.61", summary)
        self.assertIn("88", summary)
        self.assertIn("Eff N", summary)
        self.assertIn("0.8", summary)
        self.assertIn("42", summary)
        self.assertIn("not_significant", summary)

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
            promotion.write_text(
                json.dumps(
                    {
                        "summary": {"research_only": 1},
                        "candidates": [{"case_id": "case_a", "promotion_status": "research_only"}],
                    }
                ),
                encoding="utf-8",
            )
            regime = root / "market_regime_coverage_pack.json"
            regime.write_text(
                json.dumps(
                    {
                        "status": "sufficient",
                        "summary": {
                            "covered_regimes": 3,
                            "allowed_rows": 8,
                            "blocked_rows": 6,
                            "regimes": ["bear", "bull", "sideways"],
                        },
                        "decision": {"blockers": []},
                    }
                ),
                encoding="utf-8",
            )
            data_quality = root / "data_quality_gap_audit.json"
            data_quality.write_text(
                json.dumps(
                    {
                        "summary": {
                            "assets": 2,
                            "missing_date_rows": 4,
                            "duplicate_bars": 1,
                            "zero_volume_rows": 0,
                        },
                        "repair_actions": [
                            {"action": "backfill_missing_dates", "priority": 1},
                            {"action": "deduplicate_bars", "priority": 2},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "summary.md"

            result = run_desktop_validation_summary(
                walk_forward_leaderboard=leaderboard,
                promotion_report=promotion,
                data_quality_audit=data_quality,
                market_regime_coverage=regime,
                output=output,
                generated_at="2026-06-16 16:30:00 +08:00",
            )

            self.assertEqual(result, output)
            self.assertTrue(output.exists())
            text = output.read_text(encoding="utf-8")
            self.assertIn("case_a", text)
            self.assertIn("Data Quality", text)
            self.assertIn("Missing date rows: 4", text)
            self.assertIn("deduplicate_bars", text)
            self.assertIn("Market Regime Coverage", text)
            self.assertIn("sufficient", text)
            self.assertIn("Allowed rows: 8", text)
            self.assertIn("Blocked rows: 6", text)

    def test_run_summary_rejects_manifest_count_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaderboard = root / "walk_forward_leaderboard.csv"
            leaderboard.write_text(
                "case_id,validation_status,factor_name,regime_lookback,top_n,cost_bps,mean_test_sharpe\n"
                "case_a,accepted,large_resid_liq_vol_amt_gate_20,150,5,20,1.2\n",
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps({"summary": {"cases": 2, "accepted": 1, "rejected": 1}}),
                encoding="utf-8",
            )
            output = root / "summary.md"

            with self.assertRaisesRegex(ValueError, "manifest summary does not match leaderboard"):
                run_desktop_validation_summary(
                    walk_forward_leaderboard=leaderboard,
                    walk_forward_manifest=manifest,
                    promotion_report=None,
                    output=output,
                    generated_at="2026-06-16 16:30:00 +08:00",
                )

    def test_run_summary_rejects_promotion_case_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaderboard = root / "walk_forward_leaderboard.csv"
            leaderboard.write_text(
                "case_id,validation_status,factor_name,regime_lookback,top_n,cost_bps,mean_test_sharpe\n"
                "case_a,accepted,large_resid_liq_vol_amt_gate_20,150,5,20,1.2\n",
                encoding="utf-8",
            )
            promotion = root / "promotion_report.json"
            promotion.write_text(
                json.dumps(
                    {
                        "summary": {"blocked": 1},
                        "candidates": [{"case_id": "case_b", "promotion_status": "blocked"}],
                    }
                ),
                encoding="utf-8",
            )
            output = root / "summary.md"

            with self.assertRaisesRegex(ValueError, "promotion report candidates do not match leaderboard"):
                run_desktop_validation_summary(
                    walk_forward_leaderboard=leaderboard,
                    promotion_report=promotion,
                    output=output,
                    generated_at="2026-06-16 16:30:00 +08:00",
                )


if __name__ == "__main__":
    unittest.main()
