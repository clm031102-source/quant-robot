import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun import (
    run_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_cli,
)
from tests.unit.test_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun import (
    _mixed_basis_portfolio_frames,
)
from tests.unit.test_daily_basic_non_price_public_carry_prescreen import _synthetic_daily_basic


class DailyBasicFreeFloatSupplyQualityPriceBasisRepairPreflightRerunCliTests(unittest.TestCase):
    def test_cli_writes_repaired_rerun_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars_root = Path(tmp) / "processed"
            daily_basic_root = Path(tmp) / "daily_basic"
            output = Path(tmp) / "output"
            _, bars, _ = _mixed_basis_portfolio_frames()
            daily_basic = _synthetic_daily_basic(days=80, assets=40)
            DatasetStore(bars_root).write_frame(
                bars,
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(daily_basic_root).write_frame(
                daily_basic,
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_cli(
                bars_roots=[bars_root],
                daily_basic_roots=[daily_basic_root],
                output_dir=output,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
                cost_bps_values=(10.0,),
                portfolio_values=(100_000.0,),
                top_n=5,
                holding_period=5,
                rebalance_interval=5,
                min_cross_section=20,
                min_signal_amount=0.0,
                min_signal_date_amount=0.0,
                max_calendar_holding_days=15,
                min_overlap_adjusted_sharpe=-10.0,
                min_oos_overlap_adjusted_sharpe=-10.0,
                train_end_date="2025-02-28",
                test_start_date="2025-03-03",
            )

            self.assertEqual(result["stage"], "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun")
            self.assertTrue((output / "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun.json").exists())
            self.assertTrue((output / "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun.md").exists())
            self.assertTrue(
                (output / "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun_leaderboard.csv").exists()
            )
            payload = json.loads(
                (
                    output
                    / "daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(payload["price_basis_repair_summary"]["price_basis"], "close")
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
