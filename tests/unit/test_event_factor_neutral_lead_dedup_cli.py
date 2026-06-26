import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_event_factor_neutral_lead_dedup import run_event_factor_neutral_lead_dedup_cli
from quant_robot.ops.event_factor_neutral_lead_dedup import DEFAULT_LEAD_FACTOR_NAME
from tests.unit.test_event_factor_neutral_lead_dedup import _lead_rows


class EventFactorNeutralLeadDedupCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_audit_csvs_with_injected_frames(self) -> None:
        dates = list(pd.bdate_range("2024-01-02", periods=6))
        lead_frame, labels, reference_frame, exposure_frame = _lead_rows(dates, implementation_locked=False)
        prescreen_report = {
            "results": [
                {"factor_name": DEFAULT_LEAD_FACTOR_NAME, "horizon": 20, "research_lead": True}
            ],
            "summary": {"research_lead_count": 1},
        }
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "round148"
            result = run_event_factor_neutral_lead_dedup_cli(
                output_dir=output_dir,
                lead_factor_frame=lead_frame,
                labels=labels,
                reference_factor_frame=reference_frame,
                exposure_frame=exposure_frame,
                prescreen_report_payload=prescreen_report,
                min_cross_section=20,
                min_ic_observations=4,
                min_residual_icir=0.0,
            )

            self.assertEqual(result["stage"], "event_factor_neutral_lead_dedup")
            self.assertTrue((output_dir / "event_factor_neutral_lead_dedup.json").exists())
            self.assertTrue((output_dir / "event_factor_neutral_lead_dedup.md").exists())
            self.assertTrue((output_dir / "event_factor_lead_reference_correlations.csv").exists())
            self.assertTrue((output_dir / "event_factor_lead_exposure_correlations.csv").exists())
            self.assertTrue((output_dir / "event_factor_lead_residual_ic_observations.csv").exists())


if __name__ == "__main__":
    unittest.main()
