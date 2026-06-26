import unittest

import pandas as pd

from quant_robot.ops.alpha101_rank_pv_reversal_residual_prescreen import (
    DEFAULT_RESIDUAL_FACTOR_NAME,
    NEXT_HIBERNATE_OR_ROTATE_DIRECTION,
    NEXT_RESIDUAL_WALK_FORWARD_PREREGISTRATION_DIRECTION,
    residualize_alpha101_rank_pv_reversal_signal_frame,
    summarize_alpha101_rank_pv_reversal_residual_prescreen,
)


def _round129_report() -> dict:
    return {
        "stage": "alpha101_rank_pv_reversal_reference_dedup",
        "summary": {
            "reference_highly_redundant_count": 3,
            "reference_moderately_redundant_count": 4,
        },
        "gate": {"blockers": ["lead_highly_redundant_with_reference_factor", "yearly_ic_instability"]},
        "next_direction": "round130_alpha101_rank_pv_reversal_hibernate_or_orthogonalize_after_dedup",
    }


def _signal_and_labels(*, incremental: bool) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2024-01-02", periods=10)
    signal_rows = []
    label_rows = []
    for date_idx, signal_date in enumerate(dates):
        for asset_idx in range(42):
            asset_id = f"{asset_idx:06d}.SZ"
            linear_ref = float(asset_idx)
            curved_component = -abs(asset_idx - 20.5) + ((asset_idx + date_idx) % 5) * 0.03
            if incremental:
                lead_value = 0.80 * linear_ref + 0.70 * curved_component
                rank_noise = ((asset_idx * (date_idx + 3)) % 17 - 8) * 0.12
                forward_return = (curved_component + rank_noise) * 0.001
            else:
                lead_value = 1.10 * linear_ref
                forward_return = curved_component * 0.001
            signal_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "lead_value": lead_value,
                    "pv_corr_reversal_capacity_safe_20": linear_ref,
                    "pv_lowvol_reversal_blend_20": linear_ref * 1.4 + 2.0,
                    "raw_neg_pv_corr_20": -linear_ref * 0.5,
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0,
                }
            )
            label_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 20,
                    "forward_return": forward_return,
                }
            )
    return pd.DataFrame(signal_rows), pd.DataFrame(label_rows)


class Alpha101RankPvReversalResidualPrescreenTests(unittest.TestCase):
    def test_residual_prescreen_allows_walk_forward_preregistration_when_incremental_ic_survives(self) -> None:
        signal_frame, labels = _signal_and_labels(incremental=True)

        residual_frame, diagnostics = residualize_alpha101_rank_pv_reversal_signal_frame(
            signal_frame,
            min_cross_section=20,
        )
        result = summarize_alpha101_rank_pv_reversal_residual_prescreen(
            residual_frame,
            labels,
            residual_diagnostics=diagnostics,
            round129_report=_round129_report(),
            min_cross_section=20,
            min_ic_observations=5,
            max_yearly_failure_count=0,
        )

        self.assertEqual(result["stage"], "alpha101_rank_pv_reversal_residual_prescreen")
        self.assertEqual(result["residual_factor_name"], DEFAULT_RESIDUAL_FACTOR_NAME)
        self.assertGreater(result["summary"]["residual_rows"], 300)
        self.assertGreater(result["residual_diagnostics_summary"]["median_r_squared"], 0.50)
        self.assertGreater(result["residual_ic_summary"]["mean_spearman_ic"], 0.50)
        self.assertEqual(result["gate"]["blockers"], [])
        self.assertTrue(result["residual_walk_forward_policy"]["residual_walk_forward_preregistration_allowed"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertEqual(result["next_direction"], NEXT_RESIDUAL_WALK_FORWARD_PREREGISTRATION_DIRECTION)

    def test_residual_prescreen_hibernates_when_no_independent_signal_remains(self) -> None:
        signal_frame, labels = _signal_and_labels(incremental=False)

        residual_frame, diagnostics = residualize_alpha101_rank_pv_reversal_signal_frame(
            signal_frame,
            min_cross_section=20,
        )
        result = summarize_alpha101_rank_pv_reversal_residual_prescreen(
            residual_frame,
            labels,
            residual_diagnostics=diagnostics,
            round129_report=_round129_report(),
            min_cross_section=20,
            min_ic_observations=5,
            min_residual_std=1e-6,
        )

        self.assertEqual(result["next_direction"], NEXT_HIBERNATE_OR_ROTATE_DIRECTION)
        self.assertFalse(result["residual_walk_forward_policy"]["residual_walk_forward_preregistration_allowed"])
        self.assertIn("residual_signal_variance_too_low", result["gate"]["blockers"])
        self.assertIn("residual_ic_observations_below_threshold", result["gate"]["blockers"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
