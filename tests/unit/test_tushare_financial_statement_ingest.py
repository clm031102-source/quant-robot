import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.ingest.tushare_financial_statements import run_tushare_financial_statement_ingest
from quant_robot.storage.dataset_store import DatasetStore


class FakeFinancialStatementAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_income_statement(self, period: str, ts_code: str = "") -> pd.DataFrame:
        self.calls.append(("income", ts_code, period))
        period_date = pd.to_datetime(period, format="%Y%m%d").date()
        ann_date = (pd.Timestamp(period_date) + pd.Timedelta(days=25)).date()
        return pd.DataFrame(
            {
                "symbol": [ts_code],
                "ann_date": [ann_date],
                "end_date": [period_date],
                "report_type": ["1"],
                "comp_type": ["1"],
                "end_type": ["1"],
                "netprofit": [120.0],
                "n_income": [125.0],
                "n_income_attr_p": [120.0],
                "total_revenue": [1000.0],
                "revenue": [900.0],
                "total_cogs": [800.0],
                "operate_profit": [150.0],
                "total_profit": [145.0],
                "income_tax": [25.0],
            }
        )

    def fetch_balance_sheet(self, period: str, ts_code: str = "") -> pd.DataFrame:
        self.calls.append(("balancesheet", ts_code, period))
        period_date = pd.to_datetime(period, format="%Y%m%d").date()
        ann_date = (pd.Timestamp(period_date) + pd.Timedelta(days=25)).date()
        return pd.DataFrame(
            {
                "symbol": [ts_code],
                "ann_date": [ann_date],
                "end_date": [period_date],
                "report_type": ["1"],
                "comp_type": ["1"],
                "end_type": ["1"],
                "total_assets": [1200.0],
                "total_liab": [700.0],
                "total_cur_assets": [500.0],
                "total_cur_liab": [300.0],
                "total_hldr_eqy_exc_min_int": [480.0],
                "total_hldr_eqy_inc_min_int": [500.0],
                "total_liab_hldr_eqy": [1200.0],
                "inventories": [80.0],
                "accounts_receiv": [90.0],
                "accounts_pay": [60.0],
            }
        )

    def fetch_cashflow_statement(self, period: str, ts_code: str = "") -> pd.DataFrame:
        self.calls.append(("cashflow", ts_code, period))
        period_date = pd.to_datetime(period, format="%Y%m%d").date()
        ann_date = (pd.Timestamp(period_date) + pd.Timedelta(days=25)).date()
        return pd.DataFrame(
            {
                "symbol": [ts_code],
                "ann_date": [ann_date],
                "end_date": [period_date],
                "report_type": ["1"],
                "comp_type": ["1"],
                "end_type": ["1"],
                "net_profit": [121.0],
                "n_cashflow_act": [98.0],
                "free_cashflow": [75.0],
                "c_cash_equ_end_period": [220.0],
                "c_cash_equ_beg_period": [200.0],
            }
        )


class TushareFinancialStatementIngestTests(unittest.TestCase):
    def test_statement_ingest_writes_combined_pit_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            adapter = FakeFinancialStatementAdapter()

            result = run_tushare_financial_statement_ingest(
                adapter,
                ["20240331"],
                Path(tmp),
                ts_codes=["000001.SZ", "600519.SH"],
            )

            self.assertEqual(result["dataset"], "financial_statement")
            self.assertEqual(result["processed_rows"], 2)
            self.assertEqual(result["summary"]["required_column_groups_passing"], 2)
            self.assertEqual(len(adapter.calls), 6)
            processed = DatasetStore(Path(tmp)).read_frame(
                "processed/financial_statement_inputs",
                {"frequency": "1q", "market": "CN", "year": "2024"},
            )
            self.assertEqual(set(processed["asset_id"]), {"CN_XSHE_000001", "CN_XSHG_600519"})
            self.assertIn("netprofit", processed.columns)
            self.assertIn("n_cashflow_act", processed.columns)
            self.assertIn("total_assets", processed.columns)
            self.assertEqual(set(processed["source"]), {"tushare_financial_statement"})
            manifest = json.loads((Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            self.assertIn("income:000001.SZ:20240331", manifest["completed"])
            self.assertIn("balancesheet:000001.SZ:20240331", manifest["completed"])
            self.assertIn("cashflow:000001.SZ:20240331", manifest["completed"])


if __name__ == "__main__":
    unittest.main()
