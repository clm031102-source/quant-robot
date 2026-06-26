import tempfile
import unittest
from pathlib import Path

from quant_robot.factors.public_trend_strength_state import PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES
from scripts.run_public_trend_strength_state_residual_prescreen import (
    run_public_trend_strength_state_residual_prescreen_cli,
)
from tests.unit.test_public_trend_strength_state_residual_prescreen import _synthetic_frames


class PublicTrendStrengthStateResidualPrescreenCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_round219_outputs_from_injected_frames(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = run_public_trend_strength_state_residual_prescreen_cli(
                output_dir=output,
                factor_frame=factor_frame,
                labels=labels,
                reference_factor_frame=reference_frame,
                exposure_frame=exposure_frame,
                candidate_factor_names=PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES,
                horizons=(5,),
                min_cross_section=15,
                min_ic_observations=4,
                min_industry_neutral_icir=0.0,
                min_residual_icir=0.0,
            )

            self.assertEqual(result["stage"], "public_trend_strength_state_residual_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 6)
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])
            self.assertTrue((output / "public_trend_strength_state_residual_prescreen.json").exists())
            self.assertTrue((output / "public_trend_strength_state_residual_prescreen_results.csv").exists())
            self.assertTrue((output / "public_trend_strength_state_residual_ic_observations.csv").exists())


if __name__ == "__main__":
    unittest.main()
