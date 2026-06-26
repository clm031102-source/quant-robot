import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.cn_calendar_seasonality_preregistration import (
    build_cn_calendar_seasonality_preregistration,
    write_cn_calendar_seasonality_preregistration,
)
from scripts.run_cn_calendar_seasonality_residual_prescreen import (
    run_cn_calendar_seasonality_residual_prescreen_cli,
)
from tests.unit.test_cn_calendar_seasonality_residual_prescreen import _calendar_bars, _stock_basic


class CNCalendarSeasonalityResidualPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_outputs_from_csv_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_root = root / "bars"
            bars_root.mkdir()
            stock_basic_path = root / "stock_basic.csv"
            prereg_dir = root / "prereg"
            output_dir = root / "output"
            _calendar_bars(days=100, assets=30).to_csv(bars_root / "bars.csv", index=False)
            _stock_basic(30).to_csv(stock_basic_path, index=False)
            write_cn_calendar_seasonality_preregistration(
                prereg_dir,
                build_cn_calendar_seasonality_preregistration(),
            )

            result = run_cn_calendar_seasonality_residual_prescreen_cli(
                bars_roots=[bars_root],
                stock_basic=stock_basic_path,
                preregistration_json=prereg_dir / "cn_calendar_seasonality_preregistration.json",
                output_dir=output_dir,
                analysis_start_date="2020-01-01",
                analysis_end_date="2020-12-31",
                min_cross_section=15,
                min_ic_observations=4,
                min_signal_date_amount=0,
                min_industries=2,
                min_assets_per_industry=2,
                min_calendar_dates=3,
            )

            self.assertEqual(result["summary"]["candidate_count"], 8)
            self.assertTrue((output_dir / "cn_calendar_seasonality_residual_prescreen.json").exists())
            self.assertTrue((output_dir / "cn_calendar_seasonality_residual_prescreen.md").exists())
            self.assertTrue((output_dir / "cn_calendar_seasonality_residual_prescreen_results.csv").exists())


if __name__ == "__main__":
    unittest.main()
