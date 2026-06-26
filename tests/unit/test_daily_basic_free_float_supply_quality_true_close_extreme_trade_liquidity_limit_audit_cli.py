import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit import (
    run_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_cli,
)
from tests.unit.test_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit import (
    _stock_metadata,
    _true_close_extreme_bars,
    _true_close_extreme_trades,
)


class DailyBasicFreeFloatSupplyQualityTrueCloseExtremeTradeLiquidityLimitAuditCliTests(unittest.TestCase):
    def test_cli_writes_tradeability_audit_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bars_root = Path(tmp) / "processed"
            metadata_root = Path(tmp) / "metadata"
            output = Path(tmp) / "output"
            report = Path(tmp) / "round138.json"
            DatasetStore(bars_root).write_frame(
                _true_close_extreme_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(metadata_root).write_frame(
                _stock_metadata(),
                "metadata/tushare_stock_basic",
                {"snapshot": "2026-06-21"},
            )
            report.write_text(
                json.dumps({"extreme_trades": _true_close_extreme_trades()}),
                encoding="utf-8",
            )

            result = run_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit_cli(
                bars_roots=[bars_root],
                stock_metadata_roots=[metadata_root],
                repaired_rerun_report=report,
                output_dir=output,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
            )

            self.assertEqual(
                result["stage"],
                "daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit",
            )
            self.assertTrue(
                (
                    output
                    / "daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit.json"
                ).exists()
            )
            self.assertTrue(
                (
                    output
                    / "daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit.md"
                ).exists()
            )
            self.assertTrue(
                (
                    output
                    / "daily_basic_free_float_supply_quality_true_close_extreme_trade_path_audit.csv"
                ).exists()
            )
            payload = json.loads(
                (
                    output
                    / "daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["unique_trade_path_count"], 4)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
