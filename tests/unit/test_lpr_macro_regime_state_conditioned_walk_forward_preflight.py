import unittest

import pandas as pd

from quant_robot.ops.lpr_macro_regime_state_conditioned_walk_forward_preflight import (
    summarize_lpr_macro_regime_state_conditioned_walk_forward_preflight,
)


ANOMALY = "public_anomaly_residual_equal_weight_20_industry_size_liquidity_vol_residual"
WILLIAMS = "williams_range_failure_reversal_14_20_industry_size_liquidity_vol_residual"


def _round735_report() -> dict[str, object]:
    return {
        "stage": "lpr_macro_regime_state_conditioned_reference_dedup",
        "summary": {"passes": True},
        "decision": {
            "walk_forward_preflight_allowed_next": True,
            "walk_forward_preflight_allowed": False,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
        },
        "candidate_results": [
            {
                "source_id": "source_a",
                "factor_name": ANOMALY,
                "base_factor_name": "public_anomaly_residual_equal_weight_20",
                "horizon": 5,
                "state": "gap_widening",
                "state_dates": 8,
                "median_cross_section": 6,
                "reference_redundancy_class": "unique",
                "exposure_class": "moderate_exposure",
                "max_exposure_name": "realized_vol_20",
                "state_conditioned_reference_dedup_pass": True,
                "walk_forward_preflight_allowed_next": True,
                "requirements": ["state_conditioned_moderate_exposure_requires_walk_forward_challenge"],
            },
            {
                "source_id": "source_b",
                "factor_name": WILLIAMS,
                "base_factor_name": "williams_range_failure_reversal_14_20",
                "horizon": 5,
                "state": "gap_widening",
                "state_dates": 8,
                "median_cross_section": 6,
                "reference_redundancy_class": "unique",
                "exposure_class": "low_exposure",
                "max_exposure_name": "return_20",
                "state_conditioned_reference_dedup_pass": True,
                "walk_forward_preflight_allowed_next": True,
                "requirements": [],
            },
        ],
        "live_boundary_allowed": False,
    }


class LPRMacroRegimeStateConditionedWalkForwardPreflightTests(unittest.TestCase):
    def test_clears_distinct_candidates_and_records_exposure_challenge(self) -> None:
        result = summarize_lpr_macro_regime_state_conditioned_walk_forward_preflight(
            _round735_report(),
            _factor_frame(duplicate=False),
            _state_frame(),
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-01-31",
            min_state_dates=8,
            min_median_cross_section=6,
            min_pair_observations=4,
            min_corr_cross_section=6,
            train_state_dates=4,
            test_state_dates=2,
            step_state_dates=2,
            min_walk_forward_folds=2,
        )

        self.assertEqual(result["stage"], "lpr_macro_regime_state_conditioned_walk_forward_preflight")
        self.assertEqual(result["status"], "cleared")
        self.assertTrue(result["preflight_policy"]["walk_forward_preflight_cleared"])
        self.assertEqual(result["summary"]["frozen_walk_forward_candidates"], 2)
        self.assertEqual(result["summary"]["walk_forward_folds"], 2)
        self.assertFalse(result["portfolio_grid_policy"]["portfolio_grid_allowed"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        anomaly = next(row for row in result["candidate_table"] if row["factor_name"] == ANOMALY)
        self.assertTrue(anomaly["moderate_exposure_challenge_required"])
        self.assertIn("challenge_realized_vol_20_exposure_in_walk_forward", anomaly["challenge_requirements"])

    def test_clusters_duplicate_factor_values_before_freezing(self) -> None:
        result = summarize_lpr_macro_regime_state_conditioned_walk_forward_preflight(
            _round735_report(),
            _factor_frame(duplicate=True),
            _state_frame(),
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-01-31",
            min_state_dates=8,
            min_median_cross_section=6,
            min_pair_observations=4,
            min_corr_cross_section=6,
            candidate_high_corr_threshold=0.95,
            train_state_dates=4,
            test_state_dates=2,
            step_state_dates=2,
            min_walk_forward_folds=2,
        )

        self.assertEqual(result["status"], "cleared")
        self.assertEqual(result["summary"]["frozen_walk_forward_candidates"], 1)
        frozen = {row["factor_name"] for row in result["frozen_candidates"]}
        self.assertEqual(frozen, {WILLIAMS})
        duplicate = next(row for row in result["candidate_table"] if row["factor_name"] == ANOMALY)
        self.assertEqual(duplicate["preflight_status"], "cluster_duplicate")
        self.assertIn("factor_value_duplicate_or_high_similarity_with_lower_exposure_candidate", duplicate["blockers"])

    def test_blocks_when_reference_dedup_did_not_allow_walk_forward_preflight(self) -> None:
        report = _round735_report()
        report["decision"] = {"walk_forward_preflight_allowed_next": False}

        result = summarize_lpr_macro_regime_state_conditioned_walk_forward_preflight(
            report,
            _factor_frame(duplicate=False),
            _state_frame(),
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-01-31",
            min_state_dates=1,
            min_median_cross_section=1,
            min_pair_observations=1,
            min_corr_cross_section=1,
            train_state_dates=4,
            test_state_dates=2,
            step_state_dates=2,
            min_walk_forward_folds=1,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("reference_dedup_not_allowed_for_walk_forward_preflight", result["decision"]["blockers"])
        self.assertFalse(result["preflight_policy"]["walk_forward_preflight_cleared"])


def _factor_frame(*, duplicate: bool) -> pd.DataFrame:
    rows = []
    dates = pd.bdate_range("2024-01-02", periods=8)
    for signal_date in dates:
        for asset_idx in range(6):
            values = {
                ANOMALY: float(asset_idx),
                WILLIAMS: float(asset_idx) if duplicate else (1.0 if asset_idx in {0, 2, 4} else -1.0),
            }
            for factor_name, value in values.items():
                rows.append(
                    {
                        "date": signal_date,
                        "asset_id": f"{asset_idx:06d}.SZ",
                        "market": "CN",
                        "factor_name": factor_name,
                        "factor_value": value,
                    }
                )
    return pd.DataFrame(rows)


def _state_frame() -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=8)
    return pd.DataFrame({"available_date": dates, "lpr_shibor_gap_state": ["gap_widening"] * len(dates)})


if __name__ == "__main__":
    unittest.main()
