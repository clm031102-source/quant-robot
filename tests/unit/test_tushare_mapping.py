import unittest

import pandas as pd

from quant_robot.data.sources.tushare_mapping import (
    MONEYFLOW_COLUMNS,
    map_tushare_adj_factor,
    map_tushare_daily,
    map_tushare_daily_basic,
    map_tushare_moneyflow,
    map_tushare_stock_basic,
    map_tushare_trade_cal,
)


class TushareMappingTests(unittest.TestCase):
    def test_map_daily_returns_standard_empty_frame_for_empty_provider_response(self):
        result = map_tushare_daily(pd.DataFrame())

        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), ["symbol", "date", "open", "high", "low", "close", "volume", "amount"])

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

    def test_map_daily_basic_normalizes_numeric_fields(self):
        source = pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "trade_date": ["20240102"],
                "turnover_rate": ["1.25"],
                "turnover_rate_f": ["2.50"],
                "volume_ratio": ["1.10"],
                "pe": ["8.1"],
                "pe_ttm": ["7.9"],
                "pb": ["0.8"],
                "ps": ["1.2"],
                "ps_ttm": ["1.1"],
                "dv_ratio": ["3.0"],
                "dv_ttm": ["3.2"],
                "total_share": ["1000"],
                "float_share": ["800"],
                "free_share": ["600"],
                "total_mv": ["120000"],
                "circ_mv": ["90000"],
            }
        )

        result = map_tushare_daily_basic(source)

        self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(str(result.loc[0, "date"]), "2024-01-02")
        self.assertAlmostEqual(result.loc[0, "turnover_rate"], 1.25)
        self.assertAlmostEqual(result.loc[0, "pe_ttm"], 7.9)
        self.assertAlmostEqual(result.loc[0, "circ_mv"], 90000.0)

    def test_map_daily_basic_returns_standard_empty_frame_for_empty_provider_response(self):
        result = map_tushare_daily_basic(pd.DataFrame())

        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), [
            "symbol",
            "date",
            "turnover_rate",
            "turnover_rate_f",
            "volume_ratio",
            "pe",
            "pe_ttm",
            "pb",
            "ps",
            "ps_ttm",
            "dv_ratio",
            "dv_ttm",
            "total_share",
            "float_share",
            "free_share",
            "total_mv",
            "circ_mv",
        ])

    def test_map_daily_basic_creates_missing_optional_columns(self):
        source = pd.DataFrame({"ts_code": ["600519.SH"], "trade_date": ["20240102"], "pb": ["5.5"]})

        result = map_tushare_daily_basic(source)

        self.assertEqual(
            list(result.columns),
            [
                "symbol",
                "date",
                "turnover_rate",
                "turnover_rate_f",
                "volume_ratio",
                "pe",
                "pe_ttm",
                "pb",
                "ps",
                "ps_ttm",
                "dv_ratio",
                "dv_ttm",
                "total_share",
                "float_share",
                "free_share",
                "total_mv",
                "circ_mv",
            ],
        )
        self.assertAlmostEqual(result.loc[0, "pb"], 5.5)
        self.assertTrue(pd.isna(result.loc[0, "pe_ttm"]))

    def test_map_moneyflow_returns_standard_empty_frame_for_empty_provider_response(self):
        result = map_tushare_moneyflow(pd.DataFrame())

        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), MONEYFLOW_COLUMNS)

    def test_map_moneyflow_normalizes_numeric_fields_and_sorts_rows(self):
        source = pd.DataFrame(
            {
                "ts_code": ["600519.SH", "000001.SZ"],
                "trade_date": ["20240102", "20240102"],
                "buy_sm_vol": ["10", "20"],
                "buy_sm_amount": ["100.5", "200.5"],
                "sell_sm_vol": ["8", "18"],
                "sell_sm_amount": ["80.5", "180.5"],
                "buy_md_vol": ["30", "40"],
                "buy_md_amount": ["300.5", "400.5"],
                "sell_md_vol": ["25", "35"],
                "sell_md_amount": ["250.5", "350.5"],
                "buy_lg_vol": ["50", "60"],
                "buy_lg_amount": ["500.5", "600.5"],
                "sell_lg_vol": ["45", "55"],
                "sell_lg_amount": ["450.5", "550.5"],
                "buy_elg_vol": ["70", "80"],
                "buy_elg_amount": ["700.5", "800.5"],
                "sell_elg_vol": ["65", "75"],
                "sell_elg_amount": ["650.5", "750.5"],
                "net_mf_vol": ["12", "22"],
                "net_mf_amount": ["120.5", "220.5"],
            }
        )

        result = map_tushare_moneyflow(source)

        self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(str(result.loc[0, "date"]), "2024-01-02")
        self.assertEqual(result.loc[1, "symbol"], "600519.SH")
        self.assertAlmostEqual(result.loc[0, "buy_sm_amount"], 200.5)
        self.assertAlmostEqual(result.loc[0, "net_mf_amount"], 220.5)

    def test_map_moneyflow_requires_identity_columns(self):
        with self.assertRaises(ValueError):
            map_tushare_moneyflow(pd.DataFrame({"ts_code": ["000001.SZ"], "buy_sm_amount": [1.0]}))

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
