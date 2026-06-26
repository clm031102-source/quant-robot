import unittest

import pandas as pd

from quant_robot.ops.daily_basic_free_float_supply_quality_residual_stability_audit import (
    NEXT_REVIEW_DIRECTION,
    POST_REVIEW_HIBERNATE_DIRECTION,
    POST_REVIEW_STRICT_PREFLIGHT_DIRECTION,
    summarize_daily_basic_free_float_supply_quality_residual_stability_audit,
)


def _ic_rows(months: list[str], values: list[float], *, factor_name: str = "lead") -> list[dict[str, object]]:
    rows = []
    for month, value in zip(months, values):
        signal_date = pd.Timestamp(month + "-05")
        rows.append(
            {
                "factor_name": factor_name,
                "horizon": 20,
                "date": signal_date.date().isoformat(),
                "spearman_ic": value,
                "cross_section": 120,
            }
        )
    return rows


class DailyBasicFreeFloatSupplyQualityResidualStabilityAuditTests(unittest.TestCase):
    def test_routes_persistent_non_onset_failure_to_hibernation_after_review(self) -> None:
        months = ["2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12", "2024-01", "2024-02"]
        residual_values = [-0.05, -0.04, 0.05, 0.06, 0.04, 0.03, -0.03, 0.04]
        raw_values = [0.02, 0.01, 0.05, 0.04, 0.03, 0.03, 0.01, 0.04]
        market_state = pd.DataFrame(
            {
                "date": [pd.Timestamp(month + "-05") for month in months],
                "trend_state": ["stress", "stress", "neutral", "neutral", "neutral", "neutral", "neutral", "neutral"],
                "breadth_state": ["weak", "weak", "mixed", "mixed", "mixed", "mixed", "mixed", "mixed"],
                "volatility_state": ["high_vol", "high_vol", "normal_vol", "normal_vol", "normal_vol", "normal_vol", "normal_vol", "normal_vol"],
            }
        )

        result = summarize_daily_basic_free_float_supply_quality_residual_stability_audit(
            raw_ic_observations=_ic_rows(months, raw_values, factor_name="raw"),
            residual_ic_observations=_ic_rows(months, residual_values, factor_name="residual"),
            market_state_frame=market_state,
            strict_clean_residual_ic_observations=_ic_rows(months, residual_values, factor_name="strict"),
            coverage_onset_observations=2,
            min_ic_observations=4,
        )

        self.assertEqual(result["next_direction"], NEXT_REVIEW_DIRECTION)
        self.assertEqual(result["recommended_post_review_direction"], POST_REVIEW_HIBERNATE_DIRECTION)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertIn("residual_failure_persists_after_coverage_onset", result["gate"]["blockers"])
        self.assertIn("residual_failure_in_non_stress_regime", result["gate"]["blockers"])
        self.assertIn("strict_clean_residual_ic_below_threshold", result["gate"]["blockers"])
        self.assertEqual(result["summary"]["post_onset_failed_month_count"], 1)

    def test_routes_onset_or_stress_only_failure_to_strict_preflight_after_review(self) -> None:
        months = ["2023-07", "2023-08", "2023-09", "2023-10", "2023-11", "2023-12", "2024-01", "2024-02"]
        residual_values = [-0.05, -0.04, 0.07, -0.005, 0.06, 0.05, 0.04, 0.04]
        raw_values = [0.02, 0.01, 0.05, 0.04, 0.03, 0.03, 0.03, 0.04]
        market_state = pd.DataFrame(
            {
                "date": [pd.Timestamp(month + "-05") for month in months],
                "trend_state": ["stress", "stress", "neutral", "stress", "neutral", "neutral", "neutral", "neutral"],
                "breadth_state": ["weak", "weak", "mixed", "mixed", "mixed", "mixed", "mixed", "mixed"],
                "volatility_state": ["high_vol", "high_vol", "normal_vol", "normal_vol", "normal_vol", "normal_vol", "normal_vol", "normal_vol"],
            }
        )

        result = summarize_daily_basic_free_float_supply_quality_residual_stability_audit(
            raw_ic_observations=_ic_rows(months, raw_values, factor_name="raw"),
            residual_ic_observations=_ic_rows(months, residual_values, factor_name="residual"),
            market_state_frame=market_state,
            strict_clean_residual_ic_observations=_ic_rows(months, residual_values, factor_name="strict"),
            coverage_onset_observations=2,
            min_ic_observations=4,
        )

        self.assertEqual(result["next_direction"], NEXT_REVIEW_DIRECTION)
        self.assertEqual(result["recommended_post_review_direction"], POST_REVIEW_STRICT_PREFLIGHT_DIRECTION)
        self.assertTrue(result["stability_repair_candidate"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertIn("coverage_onset_or_stress_only_residual_failure", result["gate"]["observations"])
        self.assertNotIn("residual_failure_persists_after_coverage_onset", result["gate"]["blockers"])
        self.assertEqual(result["summary"]["post_onset_failed_month_count"], 1)


if __name__ == "__main__":
    unittest.main()
