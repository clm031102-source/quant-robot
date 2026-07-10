import unittest

import pandas as pd

from quant_robot.ops.factor_statistical_reality_check import (
    benjamini_hochberg,
    build_factor_statistical_reality_check,
    build_parameter_sensitivity_heatmap,
    build_purged_cpcv_splits,
    deflated_sharpe_probability,
    probabilistic_sharpe_probability,
)


class FactorStatisticalRealityCheckTests(unittest.TestCase):
    def test_deflated_sharpe_penalizes_multiple_trials(self) -> None:
        psr = probabilistic_sharpe_probability(
            observed_sharpe=0.8,
            benchmark_sharpe=0.0,
            observations=120,
        )
        low_trial_dsr = deflated_sharpe_probability(
            observed_sharpe=0.8,
            observations=120,
            trial_count=1,
        )
        high_trial_dsr = deflated_sharpe_probability(
            observed_sharpe=0.8,
            observations=120,
            trial_count=100,
        )

        self.assertGreater(psr, 0.5)
        self.assertAlmostEqual(psr, low_trial_dsr)
        self.assertLess(high_trial_dsr, low_trial_dsr)
        self.assertGreaterEqual(high_trial_dsr, 0.0)
        self.assertLessEqual(high_trial_dsr, 1.0)

    def test_benjamini_hochberg_flags_prefix(self) -> None:
        rows = benjamini_hochberg([0.001, 0.02, 0.20], alpha=0.05)

        self.assertEqual([row["significant"] for row in rows], [True, True, False])
        self.assertEqual([row["rank"] for row in rows], [1, 2, 3])

    def test_cpcv_splits_apply_purge_and_embargo(self) -> None:
        dates = pd.date_range("2024-01-01", periods=12, freq="D")

        splits = build_purged_cpcv_splits(
            dates,
            n_groups=4,
            test_group_count=1,
            purge_observations=1,
            embargo_observations=1,
        )

        self.assertEqual(len(splits), 4)
        middle = next(split for split in splits if split["test_groups"] == [1])
        self.assertEqual(middle["test_observations"], 3)
        self.assertEqual(middle["purged_observations"], 2)
        self.assertNotIn("2024-01-03", middle["train_dates"])
        self.assertNotIn("2024-01-07", middle["train_dates"])
        self.assertIn("2024-01-04", middle["test_dates"])

    def test_parameter_sensitivity_finds_stable_peak(self) -> None:
        experiments = pd.DataFrame(
            [
                {"lookback": 5, "top_n": 20, "sharpe": 0.60},
                {"lookback": 5, "top_n": 30, "sharpe": 0.62},
                {"lookback": 10, "top_n": 20, "sharpe": 0.80},
                {"lookback": 10, "top_n": 30, "sharpe": 0.82},
                {"lookback": 20, "top_n": 20, "sharpe": 0.78},
                {"lookback": 20, "top_n": 30, "sharpe": 0.79},
            ]
        )

        heatmap = build_parameter_sensitivity_heatmap(
            experiments,
            x_param="lookback",
            y_param="top_n",
            metric="sharpe",
            neighbor_min_fraction=0.90,
            min_neighbor_count=3,
        )

        self.assertEqual(heatmap["best_cell"]["x"], 10)
        self.assertEqual(heatmap["best_cell"]["y"], 30)
        self.assertTrue(heatmap["best_cell"]["stable_peak"])

    def test_report_combines_deflated_sharpe_fdr_cpcv_and_sensitivity(self) -> None:
        experiments = pd.DataFrame(
            [
                {
                    "case_id": "strong_a",
                    "factor_name": "quality_value",
                    "date": "2024-01-01",
                    "test_overlap_autocorr_adjusted_sharpe": 1.25,
                    "test_overlap_effective_sample_size": 252,
                    "p_value": 0.001,
                    "lookback": 20,
                    "top_n": 50,
                    "period_return": 0.012,
                },
                {
                    "case_id": "strong_b",
                    "factor_name": "quality_value",
                    "date": "2024-01-02",
                    "test_overlap_autocorr_adjusted_sharpe": 1.10,
                    "test_overlap_effective_sample_size": 252,
                    "p_value": 0.004,
                    "lookback": 40,
                    "top_n": 50,
                    "period_return": 0.008,
                },
                {
                    "case_id": "weak_a",
                    "factor_name": "turnover_noise",
                    "date": "2024-01-03",
                    "test_overlap_autocorr_adjusted_sharpe": 0.20,
                    "test_overlap_effective_sample_size": 80,
                    "p_value": 0.40,
                    "lookback": 20,
                    "top_n": 100,
                    "period_return": -0.004,
                },
                {
                    "case_id": "weak_b",
                    "factor_name": "turnover_noise",
                    "date": "2024-01-04",
                    "test_overlap_autocorr_adjusted_sharpe": -0.10,
                    "test_overlap_effective_sample_size": 80,
                    "p_value": 0.80,
                    "lookback": 40,
                    "top_n": 100,
                    "period_return": -0.010,
                },
            ]
        )

        report = build_factor_statistical_reality_check(
            experiments,
            date_column="date",
            cpcv_return_column="period_return",
            x_param="lookback",
            y_param="top_n",
            sensitivity_metric="test_overlap_autocorr_adjusted_sharpe",
            cpcv_groups=2,
            cpcv_test_group_count=1,
            min_deflated_sharpe_probability=0.80,
        )

        self.assertEqual(report["summary"]["rows"], 4)
        self.assertEqual(report["summary"]["hypothesis_count"], 4)
        self.assertGreaterEqual(report["summary"]["deflated_sharpe_pass_count"], 1)
        self.assertGreaterEqual(report["summary"]["fdr_significant_count"], 2)
        self.assertGreaterEqual(report["summary"]["statistical_candidate_count"], 1)
        self.assertEqual(report["summary"]["cpcv_split_count"], 2)
        self.assertEqual(report["cpcv_evaluation"]["status"], "evaluated")
        self.assertGreater(report["summary"]["cpcv_evaluated_case_count"], 0)
        self.assertEqual(report["sensitivity"]["x_param"], "lookback")

    def test_cpcv_split_plan_without_realized_returns_is_blocked(self) -> None:
        experiments = pd.DataFrame(
            [
                {
                    "case_id": "case_a",
                    "date": date,
                    "test_sharpe": 0.8,
                    "test_trades": 50,
                    "p_value": 0.01,
                }
                for date in pd.date_range("2024-01-01", periods=8, freq="D")
            ]
        )

        report = build_factor_statistical_reality_check(
            experiments,
            date_column="date",
            cpcv_groups=4,
            cpcv_test_group_count=1,
        )

        self.assertEqual(report["cpcv_evaluation"]["status"], "missing_return_column")
        self.assertIn("cpcv_returns_not_evaluated", report["summary"]["blockers"])
        self.assertFalse(report["promotion_policy"]["portfolio_backtest_allowed"])


if __name__ == "__main__":
    unittest.main()
