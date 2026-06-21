import unittest

import pandas as pd

from quant_robot.assets.models import Asset
from quant_robot.data.adapters.base import FetchRequest
from quant_robot.data.adapters.tushare_adapter import TushareAdapter


class FakeTushareClient:
    def __init__(self) -> None:
        self.calls = []

    def daily(self, **kwargs):
        self.calls.append(("daily", kwargs))
        return pd.DataFrame(
            {
                "ts_code": [kwargs.get("ts_code", "000001.SZ") or "000001.SZ"],
                "trade_date": [kwargs.get("trade_date", "20240102") or "20240102"],
                "open": [10.0],
                "high": [11.0],
                "low": [9.5],
                "close": [10.5],
                "vol": [100.0],
                "amount": [200.0],
            }
        )

    def fund_daily(self, **kwargs):
        self.calls.append(("fund_daily", kwargs))
        return pd.DataFrame(
            {
                "ts_code": [kwargs.get("ts_code", "510300.SH") or "510300.SH"],
                "trade_date": [kwargs.get("trade_date", "20240102") or "20240102"],
                "open": [4.0],
                "high": [4.1],
                "low": [3.9],
                "close": [4.05],
                "vol": [1000.0],
                "amount": [4050.0],
            }
        )

    def daily_basic(self, **kwargs):
        self.calls.append(("daily_basic", kwargs))
        return pd.DataFrame(
            {
                "ts_code": [kwargs.get("ts_code", "000001.SZ") or "000001.SZ"],
                "trade_date": [kwargs.get("trade_date", "20240102") or "20240102"],
                "turnover_rate": [1.25],
                "turnover_rate_f": [2.5],
                "volume_ratio": [1.1],
                "pe": [8.1],
                "pe_ttm": [7.9],
                "pb": [0.8],
                "ps": [1.2],
                "ps_ttm": [1.1],
                "dv_ratio": [3.0],
                "dv_ttm": [3.2],
                "total_share": [1000.0],
                "float_share": [800.0],
                "free_share": [600.0],
                "total_mv": [120000.0],
                "circ_mv": [90000.0],
            }
        )

    def moneyflow(self, **kwargs):
        self.calls.append(("moneyflow", kwargs))
        return pd.DataFrame(
            {
                "ts_code": [kwargs.get("ts_code", "000001.SZ") or "000001.SZ"],
                "trade_date": [kwargs.get("trade_date", "20240102") or "20240102"],
                "buy_sm_vol": [10.0],
                "buy_sm_amount": [100.0],
                "sell_sm_vol": [8.0],
                "sell_sm_amount": [80.0],
                "buy_md_vol": [30.0],
                "buy_md_amount": [300.0],
                "sell_md_vol": [25.0],
                "sell_md_amount": [250.0],
                "buy_lg_vol": [50.0],
                "buy_lg_amount": [500.0],
                "sell_lg_vol": [45.0],
                "sell_lg_amount": [450.0],
                "buy_elg_vol": [70.0],
                "buy_elg_amount": [700.0],
                "sell_elg_vol": [65.0],
                "sell_elg_amount": [650.0],
                "net_mf_vol": [12.0],
                "net_mf_amount": [120.0],
            }
        )

    def fina_indicator(self, **kwargs):
        self.calls.append(("fina_indicator", kwargs))
        return pd.DataFrame(
            {
                "ts_code": [kwargs.get("ts_code", "000001.SZ") or "000001.SZ"],
                "ann_date": ["20240425"],
                "end_date": [kwargs.get("period", "20240331") or "20240331"],
                "roe": [11.2],
                "roa": [0.92],
                "grossprofit_margin": [28.5],
                "netprofit_margin": [12.3],
                "netprofit_yoy": [8.7],
                "or_yoy": [6.5],
                "ocfps": [1.24],
                "cfps": [1.8],
            }
        )

    def adj_factor(self, **kwargs):
        self.calls.append(("adj_factor", kwargs))
        return pd.DataFrame({"ts_code": ["000001.SZ"], "trade_date": ["20240102"], "adj_factor": [100.0]})

    def trade_cal(self, **kwargs):
        self.calls.append(("trade_cal", kwargs))
        return pd.DataFrame({"exchange": ["SSE"], "cal_date": ["20240102"], "is_open": [1]})

    def stock_basic(self, **kwargs):
        self.calls.append(("stock_basic", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["000001.SZ"],
                "symbol": ["000001"],
                "area": ["深圳"],
                "industry": ["银行"],
                "market": ["主板"],
                "name": ["平安银行"],
                "exchange": ["SZSE"],
                "list_status": ["L"],
                "list_date": ["19910403"],
                "delist_date": [None],
                "is_hs": ["S"],
            }
        )

    def fund_basic(self, **kwargs):
        self.calls.append(("fund_basic", kwargs))
        return pd.DataFrame(
            {
                "ts_code": ["510300.SH"],
                "name": ["CSI 300 ETF"],
                "market": [kwargs.get("market", "E")],
                "fund_type": ["ETF"],
                "type": ["ETF"],
                "invest_type": ["Passive"],
                "status": ["L"],
                "list_date": ["20120528"],
                "delist_date": [None],
                "found_date": ["20120528"],
            }
        )


class TushareAdapterTests(unittest.TestCase):
    def test_fetch_ohlcv_uses_injected_client_and_maps_daily_data(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)
        asset = Asset("CN_XSHE_000001", "000001.SZ", "CN", "XSHE", "stock", "CNY", "Asia/Shanghai", "XSHE")
        request = FetchRequest(start="2024-01-01", end="2024-01-31", frequency="1d", adjustment="none")

        result = adapter.fetch_ohlcv(asset, request)

        self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(result.loc[0, "volume"], 10000.0)
        self.assertEqual(client.calls[0][0], "daily")
        self.assertEqual(client.calls[0][1]["ts_code"], "000001.SZ")

    def test_fetch_daily_by_trade_date_supports_full_market_mode(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_daily_by_trade_date("20240102")

        self.assertEqual(result.loc[0, "amount"], 200000.0)
        self.assertEqual(client.calls[0][1]["trade_date"], "20240102")

    def test_fetch_cn_etf_ohlcv_uses_fund_daily_endpoint(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)
        asset = Asset("CN_ETF_XSHG_510300", "510300.SH", "CN_ETF", "XSHG", "etf", "CNY", "Asia/Shanghai", "XSHG")
        request = FetchRequest(start="2024-01-01", end="2024-01-31", frequency="1d", adjustment="none")

        result = adapter.fetch_ohlcv(asset, request)

        self.assertTrue(adapter.supports(asset))
        self.assertEqual(result.loc[0, "symbol"], "510300.SH")
        self.assertEqual(result.loc[0, "volume"], 100000.0)
        self.assertEqual(client.calls[0][0], "fund_daily")
        self.assertEqual(client.calls[0][1]["ts_code"], "510300.SH")

    def test_fetch_etf_daily_by_trade_date_supports_full_market_mode(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_etf_daily_by_trade_date("20240102")

        self.assertEqual(result.loc[0, "symbol"], "510300.SH")
        self.assertEqual(client.calls[0][0], "fund_daily")
        self.assertEqual(client.calls[0][1]["trade_date"], "20240102")

    def test_fetch_daily_basic_by_trade_date_maps_research_inputs(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_daily_basic_by_trade_date("20240102")

        self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(result.loc[0, "date"].isoformat(), "2024-01-02")
        self.assertAlmostEqual(result.loc[0, "turnover_rate"], 1.25)
        self.assertAlmostEqual(result.loc[0, "total_mv"], 120000.0)
        self.assertEqual(client.calls[0][0], "daily_basic")
        self.assertEqual(client.calls[0][1]["trade_date"], "20240102")

    def test_fetch_moneyflow_by_trade_date_maps_research_inputs(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_moneyflow_by_trade_date("2024-01-02")

        self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(result.loc[0, "date"].isoformat(), "2024-01-02")
        self.assertAlmostEqual(result.loc[0, "buy_lg_amount"], 500.0)
        self.assertAlmostEqual(result.loc[0, "net_mf_amount"], 120.0)
        self.assertEqual(client.calls[0][0], "moneyflow")
        self.assertEqual(client.calls[0][1]["trade_date"], "20240102")

    def test_fetch_fina_indicator_maps_pit_profitability_fields(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_fina_indicator(period="2024-03-31")

        self.assertEqual(result.loc[0, "symbol"], "000001.SZ")
        self.assertEqual(result.loc[0, "ann_date"].isoformat(), "2024-04-25")
        self.assertEqual(result.loc[0, "end_date"].isoformat(), "2024-03-31")
        self.assertAlmostEqual(result.loc[0, "roe"], 11.2)
        self.assertEqual(client.calls[0][0], "fina_indicator")
        self.assertEqual(client.calls[0][1]["period"], "20240331")

    def test_fetch_metadata_methods_map_contracts(self):
        adapter = TushareAdapter(client=FakeTushareClient())

        self.assertEqual(str(adapter.fetch_trade_calendar("20240101", "20240131").loc[0, "date"]), "2024-01-02")
        stock_basic = adapter.fetch_stock_basic()
        self.assertEqual(stock_basic.loc[0, "asset_id"], "CN_XSHE_000001")
        self.assertEqual(stock_basic.loc[0, "industry"], "银行")
        self.assertEqual(adapter.fetch_adj_factor("000001.SZ", "20240101", "20240131").loc[0, "adj_factor"], 100.0)

    def test_fetch_stock_basic_requests_industry_metadata_fields(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)

        adapter.fetch_stock_basic()

        call = client.calls[-1]
        self.assertEqual(call[0], "stock_basic")
        fields = call[1]["fields"]
        self.assertIn("industry", fields)
        self.assertIn("area", fields)
        self.assertIn("list_date", fields)

    def test_fetch_fund_basic_maps_etf_metadata(self):
        client = FakeTushareClient()
        adapter = TushareAdapter(client=client)

        result = adapter.fetch_fund_basic("E")

        self.assertEqual(result.loc[0, "symbol"], "510300.SH")
        self.assertTrue(bool(result.loc[0, "is_etf"]))
        self.assertEqual(client.calls[0][0], "fund_basic")
        self.assertEqual(client.calls[0][1]["market"], "E")


if __name__ == "__main__":
    unittest.main()
