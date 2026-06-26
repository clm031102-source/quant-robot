import tempfile
import unittest
from pathlib import Path

from scripts.run_cn_calendar_pre_holiday_cost_capacity_preflight import (
    run_cn_calendar_pre_holiday_cost_capacity_preflight_cli,
)
from tests.unit.test_cn_calendar_seasonality_residual_prescreen import _calendar_bars, _stock_basic


class CNCalendarPreHolidayCostCapacityPreflightCliTests(unittest.TestCase):
    def test_cli_writes_outputs_from_csv_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_root = root / "bars"
            bars_root.mkdir()
            stock_basic_path = root / "stock_basic.csv"
            output_dir = root / "output"
            _calendar_bars(days=130, assets=30).to_csv(bars_root / "bars.csv", index=False)
            _stock_basic(30).to_csv(stock_basic_path, index=False)

            result = run_cn_calendar_pre_holiday_cost_capacity_preflight_cli(
                bars_roots=[bars_root],
                stock_basic=stock_basic_path,
                output_dir=output_dir,
                analysis_start_date="2020-01-01",
                analysis_end_date="2020-12-31",
                cost_bps_values=(0.0,),
                portfolio_values=(100_000.0,),
                top_n=5,
                holding_period=5,
                rebalance_interval=1,
                min_signal_amount=0.0,
                min_signal_date_amount=0.0,
                min_cross_section=15,
                min_industries=2,
                min_assets_per_industry=2,
                min_overlap_adjusted_sharpe=-10.0,
            )

            self.assertEqual(result["thresholds"]["factor_name"], "pre_holiday_liquidity_avoidance_5_3")
            self.assertTrue((output_dir / "cn_calendar_pre_holiday_cost_capacity_preflight.json").exists())
            self.assertTrue((output_dir / "cn_calendar_pre_holiday_cost_capacity_preflight.md").exists())
            self.assertTrue((output_dir / "cn_calendar_pre_holiday_cost_capacity_preflight_leaderboard.csv").exists())


if __name__ == "__main__":
    unittest.main()
