import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.factors.listing_age_board import LISTING_AGE_BOARD_FACTOR_NAMES
from quant_robot.ops.listing_age_board_residual_prescreen import (
    FAMILY,
    NEXT_DIRECTION_WITHOUT_LEADS,
    STAGE,
    summarize_listing_age_board_residual_prescreen,
    write_listing_age_board_residual_prescreen,
)


def _synthetic_frames(*, assets: int = 54) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = list(pd.bdate_range("2018-01-02", periods=8)) + list(pd.bdate_range("2019-01-02", periods=8))
    factor_rows = []
    label_rows = []
    reference_rows = []
    exposure_rows = []
    for signal_date in dates:
        for asset_idx in range(assets):
            industry = "bank" if asset_idx < assets // 3 else "tech" if asset_idx < 2 * assets // 3 else "industrial"
            true_signal = float(asset_idx % (assets // 3))
            exposure_value = float((asset_idx * 17) % assets)
            common = {
                "date": signal_date,
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "market": "CN",
            }
            for horizon in (5, 20):
                label_rows.append(common | {"horizon": horizon, "forward_return": true_signal / (1000.0 + horizon)})
            exposure_rows.append(
                common
                | {
                    "industry": industry,
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0 + exposure_value * 10_000.0,
                    "log_adv20_amount": exposure_value,
                    "log_amount": exposure_value * 0.8,
                    "realized_vol_20": exposure_value * 0.3,
                    "amount_trend_20_60": exposure_value * 0.01,
                    "return_20": float((asset_idx * 7) % assets),
                    "return_1d": 0.01,
                }
            )
            reference_rows.append(
                common
                | {
                    "factor_name": "independent_reference",
                    "factor_value": float((asset_idx * 13) % assets),
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0,
                }
            )
            for factor_name in LISTING_AGE_BOARD_FACTOR_NAMES:
                if factor_name == "listing_age_log_seasoned_252":
                    factor_value = true_signal + exposure_value * 0.01
                elif factor_name == "listing_age_board_compound_risk_avoidance":
                    factor_value = true_signal * 0.7 + float((asset_idx * 5) % assets) * 0.02
                else:
                    factor_value = float((asset_idx * (len(factor_name) % 11 + 3)) % assets)
                factor_rows.append(
                    common
                    | {
                        "factor_name": factor_name,
                        "factor_value": factor_value,
                        "amount": 50_000_000.0,
                        "adv20_amount": 50_000_000.0,
                        "family": FAMILY,
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows), pd.DataFrame(exposure_rows)


class ListingAgeBoardResidualPrescreenTests(unittest.TestCase):
    def test_residual_prescreen_retags_round259_family_without_promotion(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames()

        result = summarize_listing_age_board_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=LISTING_AGE_BOARD_FACTOR_NAMES,
            horizons=(5, 20),
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_icir=0.0,
            min_industry_neutral_icir=0.0,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["source_context"]["candidate_family"], FAMILY)
        self.assertTrue(result["source_context"]["non_daily_basic_non_forecast_family"])
        self.assertEqual(result["summary"]["candidate_count"], len(LISTING_AGE_BOARD_FACTOR_NAMES))
        self.assertEqual(result["summary"]["test_count"], len(LISTING_AGE_BOARD_FACTOR_NAMES) * 2)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_grid_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_high_threshold_blocks_all_candidates_and_rotates(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)

        result = summarize_listing_age_board_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=LISTING_AGE_BOARD_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_mean_ic=1.01,
            min_residual_icir=99.0,
        )

        self.assertEqual(result["summary"]["residual_research_lead_count"], 0)
        self.assertEqual(result["summary"]["next_direction"], NEXT_DIRECTION_WITHOUT_LEADS)
        self.assertTrue(all("residual_mean_ic_below_threshold" in row["blockers"] for row in result["results"]))

    def test_writer_outputs_structured_round259_audit_files(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)
        result = summarize_listing_age_board_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=LISTING_AGE_BOARD_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_icir=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_listing_age_board_residual_prescreen(output, result)
            self.assertTrue((output / "listing_age_board_residual_prescreen.json").exists())
            self.assertTrue((output / "listing_age_board_residual_prescreen.md").exists())
            self.assertTrue((output / "listing_age_board_residual_prescreen_results.csv").exists())
            self.assertTrue((output / "listing_age_board_reference_correlations.csv").exists())
            self.assertTrue((output / "listing_age_board_residual_ic_observations.csv").exists())


if __name__ == "__main__":
    unittest.main()
