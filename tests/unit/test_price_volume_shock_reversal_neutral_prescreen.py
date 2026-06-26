import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.price_volume_shock_reversal_neutral_prescreen import (
    NEXT_DIRECTION_WITH_LEADS,
    NEXT_DIRECTION_WITHOUT_LEADS,
    build_price_volume_shock_reversal_feature_frame,
    summarize_price_volume_shock_reversal_neutral_prescreen_from_features,
    write_price_volume_shock_reversal_neutral_prescreen,
)
from quant_robot.ops.price_volume_shock_reversal_preregistration import (
    build_price_volume_shock_reversal_preregistration,
)
from tests.unit.test_public_reference_multi_family_prescreen import _synthetic_public_reference_bars


def _stock_basic(assets: int = 45) -> pd.DataFrame:
    rows = []
    for asset_idx in range(assets):
        industry = "bank" if asset_idx < assets // 3 else "tech" if asset_idx < 2 * assets // 3 else "industrial"
        rows.append({"asset_id": f"CN_XSHE_{asset_idx:06d}", "industry": industry})
    return pd.DataFrame(rows)


class PriceVolumeShockReversalNeutralPrescreenTests(unittest.TestCase):
    def test_neutral_prescreen_evaluates_all_round157_candidates_without_promotion(self) -> None:
        bars = _synthetic_public_reference_bars(days=150, assets=45)
        features = build_price_volume_shock_reversal_feature_frame(bars, horizons=(5,), execution_lag=1)
        prereg = build_price_volume_shock_reversal_preregistration()

        result = summarize_price_volume_shock_reversal_neutral_prescreen_from_features(
            features,
            stock_basic=_stock_basic(45),
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
            min_industries=2,
            min_assets_per_industry=2,
        )

        self.assertEqual(result["stage"], "price_volume_shock_reversal_neutral_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["test_count"], 8)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["industry_neutral_rows"], 0)
        self.assertGreater(result["summary"]["residual_rows"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_grid_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_neutral_prescreen"])
        self.assertEqual(result["multiple_testing_policy"]["round157_candidate_count"], 8)
        self.assertIn(result["summary"]["next_direction"], {NEXT_DIRECTION_WITH_LEADS, NEXT_DIRECTION_WITHOUT_LEADS})
        self.assertEqual(len(result["results"]), 8)
        for row in result["results"]:
            self.assertIn("raw_mean_spearman_ic", row)
            self.assertIn("industry_neutral_mean_spearman_ic", row)
            self.assertIn("residual_mean_spearman_ic", row)
            self.assertFalse(row["promotion_allowed"])

    def test_high_residual_threshold_blocks_portfolio_grid_and_rotates(self) -> None:
        bars = _synthetic_public_reference_bars(days=90, assets=36)
        features = build_price_volume_shock_reversal_feature_frame(bars, horizons=(5,), execution_lag=1)
        prereg = build_price_volume_shock_reversal_preregistration()

        result = summarize_price_volume_shock_reversal_neutral_prescreen_from_features(
            features,
            stock_basic=_stock_basic(36),
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            min_cross_section=18,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
            min_residual_mean_ic=0.99,
            min_residual_icir=99.0,
        )

        self.assertEqual(result["summary"]["residual_research_lead_count"], 0)
        self.assertEqual(result["summary"]["next_direction"], NEXT_DIRECTION_WITHOUT_LEADS)
        self.assertTrue(
            all("residual_mean_ic_below_threshold" in row["blockers"] for row in result["results"])
        )

    def test_writer_outputs_structured_files(self) -> None:
        bars = _synthetic_public_reference_bars(days=80, assets=36)
        features = build_price_volume_shock_reversal_feature_frame(bars, horizons=(5,), execution_lag=1)
        prereg = build_price_volume_shock_reversal_preregistration()
        result = summarize_price_volume_shock_reversal_neutral_prescreen_from_features(
            features,
            stock_basic=_stock_basic(36),
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            min_cross_section=18,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_price_volume_shock_reversal_neutral_prescreen(output, result)
            self.assertTrue((output / "price_volume_shock_reversal_neutral_prescreen.json").exists())
            self.assertTrue((output / "price_volume_shock_reversal_neutral_prescreen.md").exists())
            self.assertTrue((output / "price_volume_shock_reversal_neutral_prescreen_results.csv").exists())
            self.assertTrue((output / "price_volume_shock_reversal_reference_correlations.csv").exists())


if __name__ == "__main__":
    unittest.main()
