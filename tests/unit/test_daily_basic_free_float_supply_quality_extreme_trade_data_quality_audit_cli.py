import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit import (
    run_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_cli,
)
from tests.unit.test_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit import (
    _extreme_trades,
    _mixed_basis_bars,
)


class DailyBasicFreeFloatSupplyQualityExtremeTradeDataQualityAuditCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_csv_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars_root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            preflight = Path(tmp) / "preflight.json"
            DatasetStore(bars_root).write_frame(
                _mixed_basis_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            preflight.write_text(json.dumps({"extreme_trades": _extreme_trades()}), encoding="utf-8")

            result = run_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit_cli(
                bars_roots=[bars_root],
                preflight_report=preflight,
                output_dir=output,
                analysis_start_date="2025-06-01",
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
            )

            self.assertEqual(result["stage"], "daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit")
            self.assertTrue((output / "daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit.json").exists())
            self.assertTrue((output / "daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit.md").exists())
            self.assertTrue((output / "daily_basic_free_float_supply_quality_extreme_trade_asset_path_audit.csv").exists())
            self.assertTrue((output / "daily_basic_free_float_supply_quality_extreme_trade_date_basis_audit.csv").exists())
            payload = json.loads(
                (output / "daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(payload["summary"]["phantom_alpha_trade_count"], 1)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
