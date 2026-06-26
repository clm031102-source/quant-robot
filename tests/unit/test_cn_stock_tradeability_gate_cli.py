import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_cn_stock_tradeability_gate import run_cn_stock_tradeability_gate


class CNStockTradeabilityGateCliTests(unittest.TestCase):
    def test_cli_writes_report_artifacts_from_csv_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_path = root / "bars.csv"
            stock_basic_path = root / "stock_basic.csv"
            output_dir = root / "report"
            pd.DataFrame(
                [
                    {
                        "asset_id": "CN_XSHG_600001",
                        "symbol": "600001.SH",
                        "market": "CN",
                        "exchange": "XSHG",
                        "asset_type": "stock",
                        "date": "2024-01-03",
                        "open": 10.0,
                        "high": 10.1,
                        "low": 9.9,
                        "close": 10.0,
                        "adj_close": 10.0,
                        "volume": 1000,
                        "amount": 10000,
                    }
                ]
            ).to_csv(bars_path, index=False)
            pd.DataFrame(
                [
                    {
                        "asset_id": "CN_XSHG_600001",
                        "symbol": "600001.SH",
                        "market": "CN",
                        "exchange": "XSHG",
                        "asset_type": "stock",
                        "name": "正常银行",
                        "stock_market": "主板",
                        "list_date": "2020-01-01",
                        "delist_date": "",
                        "is_active": True,
                    }
                ]
            ).to_csv(stock_basic_path, index=False)

            report = run_cn_stock_tradeability_gate(
                bars_path=bars_path,
                stock_basic_path=stock_basic_path,
                output_dir=output_dir,
            )

            self.assertEqual(report["summary"]["rows"], 1)
            self.assertTrue((output_dir / "cn_stock_tradeability_gate.json").exists())
            self.assertTrue((output_dir / "cn_stock_tradeability_gate.md").exists())
            payload = json.loads((output_dir / "cn_stock_tradeability_gate.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["can_buy_rows"], 1)
            markdown = (output_dir / "cn_stock_tradeability_gate.md").read_text(encoding="utf-8")
            self.assertIn("CN Stock Tradeability Gate", markdown)

    def test_cli_accepts_official_tradeability_feed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_path = root / "bars.csv"
            stock_basic_path = root / "stock_basic.csv"
            stk_limit_path = root / "stk_limit.csv"
            suspension_path = root / "suspension.csv"
            namechange_path = root / "namechange.csv"
            output_dir = root / "report"
            pd.DataFrame(
                [
                    _bar("CN_XSHG_600020", "600020.SH", "2024-01-03", 11.0),
                    _bar("CN_XSHG_600021", "600021.SH", "2024-01-03", 9.0),
                    _bar("CN_XSHG_600022", "600022.SH", "2024-01-03", 10.0),
                    _bar("CN_XSHG_600023", "600023.SH", "2024-01-03", 10.0),
                ]
            ).to_csv(bars_path, index=False)
            pd.DataFrame(
                [
                    _basic("CN_XSHG_600020", "600020.SH"),
                    _basic("CN_XSHG_600021", "600021.SH"),
                    _basic("CN_XSHG_600022", "600022.SH"),
                    _basic("CN_XSHG_600023", "600023.SH"),
                ]
            ).to_csv(stock_basic_path, index=False)
            pd.DataFrame(
                [
                    {"asset_id": "CN_XSHG_600020", "date": "2024-01-03", "up_limit": 11.0, "down_limit": 9.0},
                    {"asset_id": "CN_XSHG_600021", "date": "2024-01-03", "up_limit": 11.0, "down_limit": 9.0},
                ]
            ).to_csv(stk_limit_path, index=False)
            pd.DataFrame(
                [{"asset_id": "CN_XSHG_600022", "date": "2024-01-03", "suspend_type": "S"}]
            ).to_csv(suspension_path, index=False)
            pd.DataFrame(
                [
                    {
                        "asset_id": "CN_XSHG_600023",
                        "start_date": "2024-01-01",
                        "end_date": "2024-01-10",
                        "available_date": "2024-01-02",
                        "is_st_name": True,
                    }
                ]
            ).to_csv(namechange_path, index=False)

            report = run_cn_stock_tradeability_gate(
                bars_path=bars_path,
                stock_basic_path=stock_basic_path,
                stk_limit_path=stk_limit_path,
                suspension_path=suspension_path,
                namechange_path=namechange_path,
                output_dir=output_dir,
            )

            self.assertEqual(report["summary"]["limit_up_official_rows"], 1)
            self.assertEqual(report["summary"]["limit_down_official_rows"], 1)
            self.assertEqual(report["summary"]["suspended_official_rows"], 1)
            self.assertEqual(report["summary"]["st_flag_official_rows"], 1)

def _bar(asset_id: str, symbol: str, date: str, close: float) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "symbol": symbol,
        "market": "CN",
        "exchange": "XSHG",
        "asset_type": "stock",
        "date": date,
        "open": close,
        "high": close,
        "low": close,
        "close": close,
        "adj_close": close,
        "volume": 1000,
        "amount": 10000,
    }


def _basic(asset_id: str, symbol: str) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "symbol": symbol,
        "market": "CN",
        "exchange": "XSHG",
        "asset_type": "stock",
        "name": "normal",
        "stock_market": "main",
        "list_date": "2020-01-01",
        "delist_date": "",
        "is_active": True,
    }


if __name__ == "__main__":
    unittest.main()
