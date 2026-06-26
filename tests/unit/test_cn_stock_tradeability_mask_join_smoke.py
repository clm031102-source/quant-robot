import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_stock_tradeability_mask_join_smoke import (
    run_cn_stock_tradeability_mask_join_smoke,
)


class CNStockTradeabilityMaskJoinSmokeTests(unittest.TestCase):
    def test_smoke_proves_factor_matrix_join_and_portfolio_execution_masks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "report"
            factors = pd.DataFrame(
                {
                    "date": [pd.Timestamp("2024-01-01").date()] * 3,
                    "asset_id": ["ENTRY_BLOCKED", "EXIT_DELAYED", "TRADEABLE"],
                    "symbol": ["600020.SH", "600021.SH", "600022.SH"],
                    "market": ["CN", "CN", "CN"],
                    "factor_name": ["masked_factor", "masked_factor", "masked_factor"],
                    "factor_value": [30.0, 20.0, 10.0],
                }
            )
            bars = pd.DataFrame(
                [
                    *_asset_bars("ENTRY_BLOCKED", "600020.SH", [10.0, 11.0, 11.5, 12.0]),
                    *_asset_bars("EXIT_DELAYED", "600021.SH", [20.0, 20.0, 18.0, 22.0]),
                    *_asset_bars("TRADEABLE", "600022.SH", [30.0, 30.0, 33.0, 34.0]),
                ]
            )
            stock_basic = pd.DataFrame(
                [
                    _basic("ENTRY_BLOCKED", "600020.SH"),
                    _basic("EXIT_DELAYED", "600021.SH"),
                    _basic("TRADEABLE", "600022.SH"),
                ]
            )
            stk_limit = pd.DataFrame(
                [
                    {"asset_id": "ENTRY_BLOCKED", "date": "2024-01-02", "up_limit": 11.0, "down_limit": 9.0},
                    {"asset_id": "EXIT_DELAYED", "date": "2024-01-03", "up_limit": 22.0, "down_limit": 18.0},
                ]
            )

            result = run_cn_stock_tradeability_mask_join_smoke(
                factors=factors,
                bars=bars,
                stock_basic=stock_basic,
                stk_limit=stk_limit,
                suspension=pd.DataFrame(),
                namechange=pd.DataFrame(),
                output_dir=output_dir,
                top_n=3,
                holding_period=1,
                execution_lag=1,
            )

            self.assertEqual(result["stage"], "cn_stock_tradeability_mask_join_smoke")
            self.assertEqual(result["summary"]["factor_matrix_join_status"], "pass")
            self.assertEqual(result["summary"]["portfolio_execution_mask_status"], "pass")
            self.assertEqual(result["summary"]["factor_rows"], 3)
            self.assertEqual(result["summary"]["factor_rows_with_tradeability_mask"], 3)
            self.assertGreaterEqual(result["summary"]["official_mask_hit_rows"], 2)
            self.assertEqual(result["backtest_metrics"]["trades_filtered_entry_tradeability"], 1)
            self.assertEqual(result["backtest_metrics"]["trades_delayed_exit_tradeability"], 1)
            self.assertEqual(result["backtest_metrics"]["trades_filtered_exit_tradeability"], 0)
            self.assertEqual(result["summary"]["backtest_trades"], 2)
            self.assertFalse(result["promotion_allowed"])
            self.assertTrue((output_dir / "cn_stock_tradeability_mask_join_smoke.json").exists())


def _asset_bars(asset_id: str, symbol: str, closes: list[float]) -> list[dict[str, object]]:
    rows = []
    for date, close in zip(pd.date_range("2024-01-01", periods=len(closes)).date, closes):
        rows.append(
            {
                "date": date,
                "asset_id": asset_id,
                "symbol": symbol,
                "market": "CN",
                "exchange": "XSHG",
                "open": close,
                "high": close,
                "low": close,
                "close": close,
                "adj_close": close,
                "volume": 1000,
                "amount": 10000,
            }
        )
    return rows


def _basic(asset_id: str, symbol: str) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "symbol": symbol,
        "market": "CN",
        "exchange": "XSHG",
        "name": "normal",
        "stock_market": "main",
        "list_date": "2020-01-01",
        "delist_date": "",
        "is_active": True,
    }


if __name__ == "__main__":
    unittest.main()
