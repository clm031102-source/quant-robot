import unittest

import pandas as pd

from quant_robot.ops.alpha101_rank_pv_reversal_reference_dedup import (
    DEFAULT_LEAD_FACTOR_NAME,
    NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION,
    summarize_alpha101_rank_pv_reversal_reference_dedup,
)


def _synthetic_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    dates = pd.bdate_range("2024-01-02", periods=8)
    factor_rows = []
    label_rows = []
    reference_rows = []
    for date_idx, signal_date in enumerate(dates):
        for asset_idx in range(36):
            asset_id = f"{asset_idx:06d}.SZ"
            lead_value = float(asset_idx + date_idx * 0.01)
            forward_return = lead_value * 0.001
            factor_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "factor_value": lead_value,
                    "adv20_amount": 50_000_000.0 + asset_idx,
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
            reference_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "pv_corr_reversal_capacity_safe_20",
                    "factor_value": lead_value * 2.0,
                }
            )
            reference_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "independent_reference",
                    "factor_value": float((asset_idx * 7 + date_idx) % 36),
                }
            )
    report = {
        "results": [
            {"factor_name": DEFAULT_LEAD_FACTOR_NAME, "horizon": 5, "research_lead": True},
            {"factor_name": DEFAULT_LEAD_FACTOR_NAME, "horizon": 10, "research_lead": True},
            {"factor_name": DEFAULT_LEAD_FACTOR_NAME, "horizon": 20, "research_lead": True},
        ],
        "summary": {"research_lead_count": 3, "candidate_count": 20, "test_count": 60},
    }
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows), report


class Alpha101RankPvReversalReferenceDedupTests(unittest.TestCase):
    def test_blocks_redundant_round128_lead_and_counts_unique_factor_once(self) -> None:
        factor_frame, labels, reference_frame, report = _synthetic_frames()

        result = summarize_alpha101_rank_pv_reversal_reference_dedup(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            prescreen_report=report,
            min_cross_section=20,
            min_ic_observations=5,
        )

        self.assertEqual(result["stage"], "alpha101_rank_pv_reversal_reference_dedup")
        self.assertEqual(result["lead_factor_name"], DEFAULT_LEAD_FACTOR_NAME)
        self.assertEqual(result["lead_evidence"]["round128_research_lead_rows"], 3)
        self.assertEqual(result["lead_evidence"]["round128_unique_lead_factor_count"], 1)
        self.assertEqual(result["lead_evidence"]["round128_factor_horizon_test_count"], 60)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertEqual(result["next_direction"], NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION)
        self.assertIn("lead_highly_redundant_with_reference_factor", result["gate"]["blockers"])
        self.assertIn("round128_three_horizons_are_one_unique_factor", result["gate"]["required_before"])
        classes = {row["factor_name"]: row["redundancy_class"] for row in result["reference_correlations"]}
        self.assertEqual(classes["pv_corr_reversal_capacity_safe_20"], "highly_redundant")
        self.assertEqual(classes["independent_reference"], "unique")
        self.assertGreater(result["lead_ic_summary"]["mean_spearman_ic"], 0.90)


if __name__ == "__main__":
    unittest.main()
