import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_event_factor_pit_ic_prescreen import _stock_basic, _synthetic_bars


class ForecastGuidanceUncertaintyPitIcPrescreenCliTests(unittest.TestCase):
    def test_runner_writes_forecast_guidance_uncertainty_outputs(self) -> None:
        from scripts.run_forecast_guidance_uncertainty_pit_ic_prescreen import (
            forecast_guidance_uncertainty_candidate_specs,
            run_forecast_guidance_uncertainty_pit_ic_prescreen_cli,
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "processed"
            report_dir = root / "report"
            stock_basic_path = root / "stock_basic.csv"
            bars = _synthetic_bars(days=16, assets=4)
            DatasetStore(store_root).write_frame(
                bars,
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            _stock_basic(4).to_csv(stock_basic_path, index=False)
            forecast = pd.DataFrame(
                {
                    "ts_code": ["000000.SZ", "000001.SZ", "000002.SZ", "000003.SZ"] * 8,
                    "ann_date": [date.strftime("%Y%m%d") for date in pd.bdate_range("2024-01-02", periods=8) for _ in range(4)],
                    "end_date": ["20240331"] * 32,
                    "p_change_min": [10.0, 20.0, -10.0, 40.0] * 8,
                    "p_change_max": [30.0, 22.0, 10.0, 80.0] * 8,
                    "net_profit_min": [100.0, 120.0, -20.0, 60.0] * 8,
                    "net_profit_max": [200.0, 122.0, 20.0, 120.0] * 8,
                }
            )

            result = run_forecast_guidance_uncertainty_pit_ic_prescreen_cli(
                bars_roots=[store_root],
                stock_basic_path=stock_basic_path,
                output_dir=report_dir,
                event_frames={"forecast": forecast},
                analysis_start_date="2024-01-01",
                analysis_end_date="2024-12-31",
                horizons=(1,),
                execution_lag=0,
                min_cross_section=4,
                min_ic_observations=4,
            )

            self.assertEqual(result["stage"], "event_factor_pit_ic_prescreen")
            self.assertEqual(result["report_title"], "Round256 Forecast Guidance Uncertainty PIT/IC Prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 3)
            self.assertEqual(
                result["summary"]["next_direction"],
                "round257_rotate_after_forecast_guidance_uncertainty_zero_research_leads",
            )
            self.assertEqual(
                {spec.factor_name for spec in forecast_guidance_uncertainty_candidate_specs()},
                {
                    "event_forecast_guidance_confidence_1q",
                    "event_forecast_uncertainty_compression_1q",
                    "event_forecast_positive_floor_skew_1q",
                },
            )
            self.assertFalse(result["holdout_policy"]["final_holdout_included"])
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertTrue((report_dir / "event_factor_pit_ic_prescreen.json").exists())
            self.assertTrue((report_dir / "event_factor_pit_ic_prescreen.md").exists())
            self.assertTrue((report_dir / "event_factor_pit_ic_prescreen_results.csv").exists())
            self.assertIn(
                "# Round256 Forecast Guidance Uncertainty PIT/IC Prescreen",
                (report_dir / "event_factor_pit_ic_prescreen.md").read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
