import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.public_technical_failure_reversal_preregistration import (
    build_public_technical_failure_reversal_preregistration,
    write_public_technical_failure_reversal_preregistration,
)
from quant_robot.ops.public_technical_failure_reversal_prescreen import (
    build_public_technical_failure_reversal_prescreen,
    summarize_public_technical_failure_reversal_prescreen_from_features,
    write_public_technical_failure_reversal_prescreen,
)
from quant_robot.ops.public_reference_multi_family_prescreen import (
    _add_cross_sectional_features,
    _add_forward_return_columns,
    _feature_frame,
)
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_public_reference_multi_family_prescreen import (
    _synthetic_factor_inputs,
    _synthetic_moneyflow_inputs,
    _synthetic_public_reference_bars,
)


class PublicTechnicalFailureReversalPrescreenTests(unittest.TestCase):
    def test_summarize_evaluates_all_round154_candidates_without_promotion(self) -> None:
        bars = _synthetic_public_reference_bars(days=140, assets=45)
        features = _feature_frame(
            bars,
            factor_inputs=_synthetic_factor_inputs(bars),
            moneyflow_inputs=_synthetic_moneyflow_inputs(bars),
        )
        features = _add_cross_sectional_features(features)
        features = _add_forward_return_columns(features, horizons=(5,), execution_lag=1)
        prereg = build_public_technical_failure_reversal_preregistration()

        result = summarize_public_technical_failure_reversal_prescreen_from_features(
            features,
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
        )

        self.assertEqual(result["stage"], "public_technical_failure_reversal_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["test_count"], 8)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertTrue(result["multiple_testing_policy"]["counts_all_round154_candidates"])
        self.assertIn(
            result["summary"]["next_direction"],
            {
                "round156_public_technical_failure_reversal_neutral_dedup_before_portfolio_grid",
                "round156_rotate_after_public_technical_failure_reversal_prescreen_failure",
            },
        )

    def test_builds_prescreen_from_preregistration_and_blocks_final_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = _synthetic_public_reference_bars(include_holdout=True)
            store = DatasetStore(root)
            for year in sorted(pd.to_datetime(bars["date"]).dt.year.unique()):
                year_frame = bars[pd.to_datetime(bars["date"]).dt.year == year]
                store.write_frame(
                    year_frame,
                    "processed/bars",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )
                store.write_frame(
                    _synthetic_factor_inputs(year_frame),
                    "processed/factor_inputs",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )
                store.write_frame(
                    _synthetic_moneyflow_inputs(year_frame),
                    "processed/moneyflow_inputs",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )
            prereg_dir = root / "prereg"
            prereg = build_public_technical_failure_reversal_preregistration()
            write_public_technical_failure_reversal_preregistration(prereg_dir, prereg)

            result = build_public_technical_failure_reversal_prescreen(
                bars_roots=[root],
                factor_input_root=root,
                moneyflow_input_root=root,
                preregistration_json=prereg_dir / "public_technical_failure_reversal_preregistration.json",
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
            )

            output = root / "output"
            write_public_technical_failure_reversal_prescreen(output, result)
            self.assertTrue((output / "public_technical_failure_reversal_prescreen.json").exists())
            self.assertTrue((output / "public_technical_failure_reversal_prescreen_results.csv").exists())

        self.assertEqual(result["stage"], "public_technical_failure_reversal_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["test_count"], 8)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])


if __name__ == "__main__":
    unittest.main()
