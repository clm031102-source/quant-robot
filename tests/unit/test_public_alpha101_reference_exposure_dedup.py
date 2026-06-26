import unittest

import pandas as pd

from quant_robot.ops.public_alpha101_reference_exposure_dedup import (
    DEFAULT_LEAD_FACTOR_NAME,
    NEXT_REVIEW_DIRECTION,
    summarize_public_alpha101_reference_exposure_dedup,
)


def _synthetic_frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = list(pd.bdate_range("2015-07-01", periods=4)) + list(pd.bdate_range("2016-01-04", periods=4))
    lead_rows = []
    label_rows = []
    reference_rows = []
    exposure_rows = []
    for signal_date in dates:
        failure_year = signal_date.year == 2015
        for asset_idx in range(42):
            asset_id = f"CN_XSHE_{asset_idx:06d}"
            lead_value = float(asset_idx)
            forward_return = (-lead_value if failure_year else lead_value) / 1000.0
            common = {"date": signal_date, "asset_id": asset_id, "market": "CN"}
            lead_rows.append(
                common
                | {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "factor_value": lead_value,
                    "amount": 25_000_000.0,
                    "adv20_amount": 25_000_000.0 + asset_idx * 100_000.0,
                }
            )
            label_rows.append(common | {"horizon": 5, "forward_return": forward_return})
            reference_rows.append(
                common
                | {
                    "factor_name": "pv_lowvol_reversal_blend_20",
                    "factor_value": lead_value * 1.5,
                    "amount": 25_000_000.0,
                    "adv20_amount": 25_000_000.0,
                }
            )
            reference_rows.append(
                common
                | {
                    "factor_name": "independent_reference",
                    "factor_value": float((asset_idx * 11) % 42),
                    "amount": 25_000_000.0,
                    "adv20_amount": 25_000_000.0,
                }
            )
            exposure_rows.append(
                common
                | {
                    "beta_120": lead_value,
                    "downside_beta_120": lead_value * 0.8,
                    "market_corr_60": lead_value * 0.7,
                    "residual_vol_60": lead_value * 0.6,
                    "adv20_amount": 25_000_000.0 + asset_idx * 100_000.0,
                }
            )
    return pd.DataFrame(lead_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows), pd.DataFrame(exposure_rows)


class PublicAlpha101ReferenceExposureDedupTests(unittest.TestCase):
    def test_summarizes_redundancy_exposure_and_yearly_failure(self) -> None:
        lead_frame, labels, reference_frame, exposure_frame = _synthetic_frames()
        prescreen_report = {
            "results": [
                {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "horizon": 5,
                    "research_lead": True,
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_public_alpha101_reference_exposure_dedup(
            lead_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=2,
        )

        self.assertEqual(result["stage"], "public_alpha101_reference_exposure_dedup")
        self.assertEqual(result["lead_factor_name"], DEFAULT_LEAD_FACTOR_NAME)
        self.assertEqual(result["next_direction"], NEXT_REVIEW_DIRECTION)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertIn("lead_highly_redundant_with_reference_factor", result["gate"]["blockers"])
        self.assertIn("lead_high_exposure_to_market_or_liquidity_proxy", result["gate"]["blockers"])
        self.assertIn("twenty_fifteen_regime_failure_unexplained", result["gate"]["blockers"])
        self.assertIn("yearly_ic_instability", result["gate"]["blockers"])

        reference_classes = {row["factor_name"]: row["redundancy_class"] for row in result["reference_correlations"]}
        self.assertEqual(reference_classes["pv_lowvol_reversal_blend_20"], "highly_redundant")
        self.assertEqual(reference_classes["independent_reference"], "unique")
        beta_row = next(row for row in result["exposure_correlations"] if row["exposure_name"] == "beta_120")
        self.assertEqual(beta_row["exposure_class"], "high_exposure")


if __name__ == "__main__":
    unittest.main()
