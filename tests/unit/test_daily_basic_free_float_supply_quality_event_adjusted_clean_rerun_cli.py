import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun import (
    run_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_cli,
)
from tests.unit.test_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun import (
    _round139_audit_payload,
)
from tests.unit.test_daily_basic_non_price_public_carry_prescreen import (
    _synthetic_bars,
    _synthetic_daily_basic,
)


class DailyBasicFreeFloatSupplyQualityEventAdjustedCleanRerunCliTests(unittest.TestCase):
    def test_cli_writes_event_adjusted_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars_root = Path(tmp) / "processed"
            daily_basic_root = Path(tmp) / "daily_basic"
            output = Path(tmp) / "output"
            audit_report = Path(tmp) / "round139.json"
            bars = _synthetic_bars(days=80, assets=40)
            bars["close"] = bars["adj_close"]
            bars["volume"] = 1_000_000.0
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
            audit_report.write_text(json.dumps(_round139_audit_payload()), encoding="utf-8")

            result = run_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_cli(
                bars_roots=[bars_root],
                daily_basic_roots=[daily_basic_root],
                round139_audit_report=audit_report,
                output_dir=output,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
                cost_bps_values=(10.0,),
                portfolio_values=(100_000.0,),
                guard_modes=("none",),
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

            self.assertEqual(result["stage"], "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun")
            self.assertTrue((output / "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun.json").exists())
            self.assertTrue((output / "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun.md").exists())
            self.assertTrue(
                (output / "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun_leaderboard.csv").exists()
            )
            self.assertTrue((output / "daily_basic_free_float_supply_quality_event_adjusted_event_paths.csv").exists())
            payload = json.loads(
                (output / "daily_basic_free_float_supply_quality_event_adjusted_clean_rerun.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])
            self.assertEqual(payload["event_exclusion_summary"]["requested_event_path_count"], 2)


if __name__ == "__main__":
    unittest.main()
