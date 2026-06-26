import unittest

import pandas as pd

from quant_robot.ops.turnover_repair_dedup_sensitivity import (
    summarize_turnover_repair_dedup_sensitivity,
)


def _round124_like_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "factor_name": "turnover_rate_f_low_participation_budget_100k_20",
                "horizon": 20,
                "mean_spearman_ic": 0.1033,
                "icir": 0.6485,
                "ic_t_stat": 33.35,
                "ic_positive_rate": 0.753,
                "quantile_spread": 0.0673,
                "quantile_monotonicity": 0.9,
                "avg_top_quantile_turnover": 0.278,
                "max_estimated_participation": 0.0001,
                "median_estimated_participation": 0.000015,
                "extreme_forward_return_rate": 0.0203,
                "raw_factor_spearman_corr": 1.0,
                "capacity_clean": True,
                "research_lead": True,
                "blockers": "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
            },
            {
                "factor_name": "turnover_rate_low_participation_budget_100k_20",
                "horizon": 20,
                "mean_spearman_ic": 0.0973,
                "icir": 0.5563,
                "ic_t_stat": 28.61,
                "ic_positive_rate": 0.719,
                "quantile_spread": 0.0648,
                "quantile_monotonicity": 0.9,
                "avg_top_quantile_turnover": 0.232,
                "max_estimated_participation": 0.0001,
                "median_estimated_participation": 0.000015,
                "extreme_forward_return_rate": 0.0194,
                "raw_factor_spearman_corr": 1.0,
                "capacity_clean": True,
                "research_lead": True,
                "blockers": "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
            },
            {
                "factor_name": "turnover_rate_f_low_participation_budget_100k_20",
                "horizon": 5,
                "mean_spearman_ic": 0.0775,
                "icir": 0.4917,
                "ic_t_stat": 25.36,
                "ic_positive_rate": 0.708,
                "quantile_spread": 0.0327,
                "quantile_monotonicity": 1.0,
                "avg_top_quantile_turnover": 0.278,
                "max_estimated_participation": 0.0001,
                "median_estimated_participation": 0.000015,
                "extreme_forward_return_rate": 0.0049,
                "raw_factor_spearman_corr": 1.0,
                "capacity_clean": True,
                "research_lead": True,
                "blockers": "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
            },
            {
                "factor_name": "turnover_rate_low_participation_budget_100k_20",
                "horizon": 5,
                "mean_spearman_ic": 0.0718,
                "icir": 0.4257,
                "ic_t_stat": 21.95,
                "ic_positive_rate": 0.677,
                "quantile_spread": 0.0302,
                "quantile_monotonicity": 1.0,
                "avg_top_quantile_turnover": 0.232,
                "max_estimated_participation": 0.0001,
                "median_estimated_participation": 0.000015,
                "extreme_forward_return_rate": 0.0047,
                "raw_factor_spearman_corr": 1.0,
                "capacity_clean": True,
                "research_lead": True,
                "blockers": "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
            },
            {
                "factor_name": "turnover_rate_f_low_adv_soft_rank_20",
                "horizon": 5,
                "mean_spearman_ic": 0.0522,
                "icir": 0.3030,
                "ic_t_stat": 15.63,
                "ic_positive_rate": 0.62,
                "quantile_spread": 0.0227,
                "quantile_monotonicity": 0.7,
                "avg_top_quantile_turnover": 0.115,
                "max_estimated_participation": 0.0001,
                "median_estimated_participation": 0.0000045,
                "extreme_forward_return_rate": 0.0048,
                "raw_factor_spearman_corr": 0.7899,
                "capacity_clean": True,
                "research_lead": True,
                "blockers": "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
            },
        ]
    )


class TurnoverRepairDedupSensitivityTests(unittest.TestCase):
    def test_summarizes_redundancy_capacity_and_single_champion_next_step(self) -> None:
        result = summarize_turnover_repair_dedup_sensitivity(
            _round124_like_rows(),
            capital_grid=[100_000, 500_000, 1_000_000, 5_000_000],
        )

        self.assertEqual(result["stage"], "turnover_repair_dedup_sensitivity")
        self.assertEqual(result["summary"]["input_research_lead_rows"], 5)
        self.assertEqual(result["summary"]["unique_research_lead_factor_names"], 3)
        self.assertEqual(result["summary"]["raw_source_clusters"], 2)
        self.assertEqual(result["summary"]["raw_clone_lead_rows"], 4)
        self.assertEqual(result["summary"]["high_redundancy_lead_rows"], 1)
        self.assertEqual(result["summary"]["nonredundant_research_leads"], 0)
        self.assertEqual(result["summary"]["capacity_clean_lead_rows_at_all_capitals"], 5)
        self.assertEqual(result["portfolio_conversion_policy"]["allowed_candidate_count"], 1)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertEqual(result["champion"]["factor_name"], "turnover_rate_f_low_participation_budget_100k_20")
        self.assertEqual(result["champion"]["horizon"], 20)
        self.assertEqual(result["next_direction"], "round126_turnover_repair_champion_costed_portfolio_conversion")
        self.assertIn("dedup_revealed_zero_independent_new_alpha", result["promotion_policy"]["blockers"])

        max_rows = [
            row
            for row in result["capital_sensitivity"]
            if row["factor_name"] == result["champion"]["factor_name"]
            and row["horizon"] == result["champion"]["horizon"]
            and row["capital"] == 5_000_000
        ]
        self.assertEqual(len(max_rows), 1)
        self.assertLessEqual(max_rows[0]["scaled_max_estimated_participation"], 0.01)

    def test_capacity_failure_blocks_portfolio_conversion(self) -> None:
        rows = _round124_like_rows()
        rows.loc[0, "max_estimated_participation"] = 0.001

        result = summarize_turnover_repair_dedup_sensitivity(
            rows,
            capital_grid=[100_000, 500_000, 1_000_000, 5_000_000],
        )

        self.assertEqual(result["portfolio_conversion_policy"]["allowed_candidate_count"], 0)
        self.assertIn("small_capital_capacity_stress_failed", result["gate"]["next_action_blockers"])
        self.assertEqual(result["next_direction"], "round126_rotate_after_turnover_repair_capacity_or_dedup_failure")


if __name__ == "__main__":
    unittest.main()
