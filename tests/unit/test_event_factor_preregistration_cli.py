import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_event_factor_preregistration import run_event_factor_preregistration


class EventFactorPreregistrationCliTests(unittest.TestCase):
    def test_cli_runner_writes_artifacts_with_injected_adapter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "event_round146"

            result = run_event_factor_preregistration(
                output_dir=output_dir,
                adapter=_AlwaysAvailableEventAdapter(),
                sample_symbols=("000001.SZ",),
                ann_dates=("20240105",),
                periods=("20240331",),
            )

            self.assertEqual(result["stage"], "event_factor_preregistration")
            self.assertTrue(result["summary"]["passes"])
            self.assertIn("forecast_ann_date", result["event_cross_section_probe"])
            self.assertTrue((output_dir / "event_factor_preregistration.json").exists())
            self.assertTrue((output_dir / "event_factor_preregistration.md").exists())
            self.assertTrue((output_dir / "event_factor_candidates.csv").exists())
            self.assertTrue((output_dir / "event_endpoint_probe.csv").exists())


class _AlwaysAvailableEventAdapter:
    def fetch_event_endpoint(self, endpoint, **kwargs):
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "ann_date": ["20240331"],
                "end_date": ["20240331"],
                "ex_date": ["20240601"],
                "float_date": ["20240601"],
                "amount": [1000.0],
                "holder_num": [10000.0],
                "hold_ratio": [5.0],
                "pledge_ratio": [3.0],
            }
        )


if __name__ == "__main__":
    unittest.main()
