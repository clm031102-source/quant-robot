import unittest

import pandas as pd

from quant_robot.data.sources.tushare_mapping import (
    map_tushare_adj_factor,
    map_tushare_daily,
    map_tushare_stock_basic,
    map_tushare_trade_cal,
)


class TushareMappingTests(unittest.TestCase):
    def test_map_daily_converts_units_and_dates(self):
        source = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": ["20240102"],
                "open": [10.0],
                "high": [11.0],
                "low": [9.5],
                "close": [10.5],
                "vol": [123.0],
                "amount": [456.0],
            }
        )

        result = map_tushare_daily(source)

        self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(str(result.loc[0, "date"]), "2024-01-02")
        self.assertEqual(result.loc[0, "volume"], 12300.0)
        self.assertEqual(result.loc[0, "amount"], 456000.0)

    def test_map_adj_factor_contract(self):
        source = pd.DataFrame({"ts_code": ["000001.SZ"], "trade_date": ["20240102"], "adj_factor": [101.2]})

        result = map_tushare_adj_factor(source)

        self.assertEqual(list(result.columns), ["symbol", "date", "adj_factor"])
        self.assertEqual(result.loc[0, "adj_factor"], 101.2)

    def test_map_trade_cal_keeps_open_days(self):
        source = pd.DataFrame(
            {
                "exchange": ["SSE", "SSE"],
                "cal_date": ["20240101", "20240102"],
                "is_open": [0, 1],
            }
        )

        result = map_tushare_trade_cal(source, open_only=True)

        self.assertEqual(len(result), 1)
        self.assertEqual(str(result.loc[0, "date"]), "2024-01-02")

    def test_map_stock_basic_builds_asset_fields(self):
        source = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "symbol": ["000001"],
                "name": ["平安银行"],
                "exchange": ["SZSE"],
                "list_status": ["L"],
            }
        )

        result = map_tushare_stock_basic(source)

        self.assertEqual(result.loc[0, "asset_id"], "CN_XSHE_000001")
        self.assertEqual(result.loc[0, "market"], "CN")
        self.assertEqual(result.loc[0, "currency"], "CNY")

    def test_map_stock_basic_maps_beijing_exchange(self):
        source = pd.DataFrame(
            {
                "ts_code": ["430047.BJ"],
                "symbol": ["430047"],
                "name": ["诺思兰德"],
                "exchange": ["BSE"],
                "list_status": ["L"],
            }
        )

        result = map_tushare_stock_basic(source)

        self.assertEqual(result.loc[0, "asset_id"], "CN_XBEI_430047")
        self.assertEqual(result.loc[0, "exchange"], "XBEI")


if __name__ == "__main__":
    unittest.main()
