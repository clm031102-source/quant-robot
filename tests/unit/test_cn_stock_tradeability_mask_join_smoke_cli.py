import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_cn_stock_tradeability_mask_join_smoke import run_cn_stock_tradeability_mask_join_smoke_cli


class CNStockTradeabilityMaskJoinSmokeCliTests(unittest.TestCase):
    def test_cli_writes_smoke_artifacts_from_csv_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factors_path = root / "factors.csv"
            bars_path = root / "bars.csv"
            stock_basic_path = root / "stock_basic.csv"
            stk_limit_path = root / "stk_limit.csv"
            output_dir = root / "report"
            pd.DataFrame(
                {
                    "date": ["2024-01-01"],
                    "asset_id": ["ENTRY_BLOCKED"],
                    "symbol": ["600020.SH"],
                    "market": ["CN"],
                    "factor_name": ["masked_factor"],
                    "factor_value": [1.0],
                }
            ).to_csv(factors_path, index=False)
            pd.DataFrame(_asset_bars("ENTRY_BLOCKED", "600020.SH", [10.0, 11.0, 12.0])).to_csv(
                bars_path,
                index=False,
            )
            pd.DataFrame([_basic("ENTRY_BLOCKED", "600020.SH")]).to_csv(stock_basic_path, index=False)
            pd.DataFrame(
                [{"asset_id": "ENTRY_BLOCKED", "date": "2024-01-02", "up_limit": 11.0, "down_limit": 9.0}]
            ).to_csv(stk_limit_path, index=False)

            result = run_cn_stock_tradeability_mask_join_smoke_cli(
                factors_path=factors_path,
                bars_path=bars_path,
                stock_basic_path=stock_basic_path,
                stk_limit_path=stk_limit_path,
                output_dir=output_dir,
                top_n=1,
            )

            self.assertEqual(result["summary"]["factor_matrix_join_status"], "pass")
            self.assertEqual(result["backtest_metrics"]["trades_filtered_entry_tradeability"], 1)
            self.assertTrue((output_dir / "cn_stock_tradeability_mask_join_smoke.json").exists())
            payload = json.loads(
                (output_dir / "cn_stock_tradeability_mask_join_smoke.json").read_text(encoding="utf-8")
            )
            self.assertFalse(payload["promotion_allowed"])


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
