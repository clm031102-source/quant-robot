import tempfile
import unittest
from pathlib import Path

from scripts.run_public_technical_failure_reversal_neutral_dedup import (
    run_public_technical_failure_reversal_neutral_dedup_cli,
)
from tests.unit.test_public_technical_failure_reversal_neutral_dedup import _synthetic_round156_frames
from quant_robot.ops.public_technical_failure_reversal_neutral_dedup import DEFAULT_LEAD_FACTOR_NAME


class PublicTechnicalFailureReversalNeutralDedupCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_round156_outputs_from_injected_frames(self) -> None:
        lead_frame, labels, reference_frame, exposure_frame = _synthetic_round156_frames(
            implementation_locked=False,
        )
        prescreen_report = {
            "results": [{"factor_name": DEFAULT_LEAD_FACTOR_NAME, "horizon": 5, "research_lead": True}],
            "summary": {"research_lead_count": 1},
        }

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            result = run_public_technical_failure_reversal_neutral_dedup_cli(
                output_dir=output,
                lead_factor_frame=lead_frame,
                labels=labels,
                reference_factor_frame=reference_frame[reference_frame["factor_name"] == "independent_public_reference"],
                exposure_frame=exposure_frame,
                prescreen_report_payload=prescreen_report,
                min_cross_section=20,
                min_ic_observations=4,
                min_industry_neutral_icir=0.0,
                min_residual_icir=0.0,
            )

            self.assertEqual(result["stage"], "public_technical_failure_reversal_neutral_dedup")
            self.assertTrue((output / "public_technical_failure_reversal_neutral_dedup.json").exists())
            self.assertTrue((output / "public_technical_failure_reversal_reference_correlations.csv").exists())


if __name__ == "__main__":
    unittest.main()
