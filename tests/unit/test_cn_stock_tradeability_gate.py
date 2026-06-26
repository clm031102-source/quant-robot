import unittest

import pandas as pd

from quant_robot.ops.cn_stock_tradeability_gate import (
    CNStockTradeabilityPolicy,
    build_cn_stock_tradeability_frame,
    build_cn_stock_tradeability_report,
)


class CNStockTradeabilityGateTests(unittest.TestCase):
    def test_blocks_st_new_listing_board_and_zero_volume_rows(self) -> None:
        bars = pd.DataFrame(
            [
                _bar("CN_XSHG_600001", "600001.SH", "2024-01-02", 10.0, 10.0, 10.0, 10.0, 1000, 10000, "XSHG"),
                _bar("CN_XSHG_600001", "600001.SH", "2024-01-03", 10.0, 10.1, 9.9, 10.0, 1000, 10000, "XSHG"),
                _bar("CN_XSHG_600002", "600002.SH", "2024-01-03", 10.0, 10.1, 9.9, 10.0, 1000, 10000, "XSHG"),
                _bar("CN_XSHE_300001", "300001.SZ", "2024-01-03", 10.0, 10.1, 9.9, 10.0, 1000, 10000, "XSHE"),
                _bar("CN_XBEI_920001", "920001.BJ", "2024-01-03", 10.0, 10.1, 9.9, 10.0, 1000, 10000, "XBEI"),
                _bar("CN_XSHG_600003", "600003.SH", "2024-01-03", 10.0, 10.1, 9.9, 10.0, 0, 0, "XSHG"),
            ]
        )
        stock_basic = pd.DataFrame(
            [
                _basic("CN_XSHG_600001", "600001.SH", "正常银行", "主板", "XSHG", "2020-01-01"),
                _basic("CN_XSHG_600002", "600002.SH", "*ST 风险", "主板", "XSHG", "2020-01-01"),
                _basic("CN_XSHE_300001", "300001.SZ", "创业科技", "创业板", "XSHE", "2023-12-15"),
                _basic("CN_XBEI_920001", "920001.BJ", "北交公司", "北交所", "XBEI", "2020-01-01"),
                _basic("CN_XSHG_600003", "600003.SH", "零量股份", "主板", "XSHG", "2020-01-01"),
            ]
        )

        frame = build_cn_stock_tradeability_frame(bars, stock_basic)
        by_asset = frame[frame["date"].astype(str) == "2024-01-03"].set_index("asset_id")

        self.assertTrue(bool(by_asset.loc["CN_XSHG_600001", "can_buy"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600001", "can_sell"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600002", "st_flag"]))
        self.assertFalse(bool(by_asset.loc["CN_XSHG_600002", "can_buy"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHE_300001", "new_listing_flag"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHE_300001", "board_permission_blocked"]))
        self.assertFalse(bool(by_asset.loc["CN_XSHE_300001", "can_buy"]))
        self.assertTrue(bool(by_asset.loc["CN_XBEI_920001", "board_permission_blocked"]))
        self.assertFalse(bool(by_asset.loc["CN_XBEI_920001", "can_buy"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600003", "suspended_proxy"]))
        self.assertFalse(bool(by_asset.loc["CN_XSHG_600003", "can_sell"]))

    def test_limit_up_blocks_buy_and_limit_down_blocks_sell(self) -> None:
        bars = pd.DataFrame(
            [
                _bar("CN_XSHG_600010", "600010.SH", "2024-01-02", 10.0, 10.0, 10.0, 10.0, 1000, 10000, "XSHG"),
                _bar("CN_XSHG_600010", "600010.SH", "2024-01-03", 11.0, 11.0, 10.8, 11.0, 1000, 11000, "XSHG"),
                _bar("CN_XSHG_600011", "600011.SH", "2024-01-02", 10.0, 10.0, 10.0, 10.0, 1000, 10000, "XSHG"),
                _bar("CN_XSHG_600011", "600011.SH", "2024-01-03", 9.0, 9.2, 9.0, 9.0, 1000, 9000, "XSHG"),
            ]
        )
        stock_basic = pd.DataFrame(
            [
                _basic("CN_XSHG_600010", "600010.SH", "涨停股", "主板", "XSHG", "2020-01-01"),
                _basic("CN_XSHG_600011", "600011.SH", "跌停股", "主板", "XSHG", "2020-01-01"),
            ]
        )

        frame = build_cn_stock_tradeability_frame(
            bars,
            stock_basic,
            policy=CNStockTradeabilityPolicy(limit_tolerance=0.001),
        )
        by_asset = frame[frame["date"].astype(str) == "2024-01-03"].set_index("asset_id")

        self.assertTrue(bool(by_asset.loc["CN_XSHG_600010", "limit_up_like"]))
        self.assertFalse(bool(by_asset.loc["CN_XSHG_600010", "can_buy"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600010", "can_sell"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600011", "limit_down_like"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600011", "can_buy"]))
        self.assertFalse(bool(by_asset.loc["CN_XSHG_600011", "can_sell"]))

    def test_official_tradeability_feeds_override_proxy_flags(self) -> None:
        bars = pd.DataFrame(
            [
                _bar("CN_XSHG_600020", "600020.SH", "2024-01-02", 10.0, 10.0, 10.0, 10.0, 1000, 10000, "XSHG"),
                _bar("CN_XSHG_600020", "600020.SH", "2024-01-03", 10.9, 11.0, 10.8, 11.0, 1000, 11000, "XSHG"),
                _bar("CN_XSHG_600021", "600021.SH", "2024-01-02", 10.0, 10.0, 10.0, 10.0, 1000, 10000, "XSHG"),
                _bar("CN_XSHG_600021", "600021.SH", "2024-01-03", 9.1, 9.2, 9.0, 9.0, 1000, 9000, "XSHG"),
                _bar("CN_XSHG_600022", "600022.SH", "2024-01-03", 10.0, 10.1, 9.9, 10.0, 1000, 10000, "XSHG"),
                _bar("CN_XSHG_600023", "600023.SH", "2024-01-03", 10.0, 10.1, 9.9, 10.0, 1000, 10000, "XSHG"),
            ]
        )
        stock_basic = pd.DataFrame(
            [
                _basic("CN_XSHG_600020", "600020.SH", "normal_a", "main", "XSHG", "2020-01-01"),
                _basic("CN_XSHG_600021", "600021.SH", "normal_b", "main", "XSHG", "2020-01-01"),
                _basic("CN_XSHG_600022", "600022.SH", "normal_c", "main", "XSHG", "2020-01-01"),
                _basic("CN_XSHG_600023", "600023.SH", "normal_d", "main", "XSHG", "2020-01-01"),
            ]
        )
        stk_limit = pd.DataFrame(
            [
                {"asset_id": "CN_XSHG_600020", "date": "2024-01-03", "up_limit": 11.0, "down_limit": 9.0},
                {"asset_id": "CN_XSHG_600021", "date": "2024-01-03", "up_limit": 11.0, "down_limit": 9.0},
            ]
        )
        suspension = pd.DataFrame(
            [{"asset_id": "CN_XSHG_600022", "date": "2024-01-03", "suspend_type": "S"}]
        )
        namechange = pd.DataFrame(
            [
                {
                    "asset_id": "CN_XSHG_600023",
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-10",
                    "available_date": "2024-01-02",
                    "is_st_name": True,
                }
            ]
        )

        frame = build_cn_stock_tradeability_frame(
            bars,
            stock_basic,
            stk_limit=stk_limit,
            suspension=suspension,
            namechange=namechange,
            policy=CNStockTradeabilityPolicy(limit_tolerance=0.001),
        )
        by_asset = frame[frame["date"].astype(str) == "2024-01-03"].set_index("asset_id")

        self.assertTrue(bool(by_asset.loc["CN_XSHG_600020", "limit_up_official"]))
        self.assertFalse(bool(by_asset.loc["CN_XSHG_600020", "can_buy"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600020", "can_sell"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600021", "limit_down_official"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600021", "can_buy"]))
        self.assertFalse(bool(by_asset.loc["CN_XSHG_600021", "can_sell"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600022", "suspended_official"]))
        self.assertFalse(bool(by_asset.loc["CN_XSHG_600022", "can_buy"]))
        self.assertTrue(bool(by_asset.loc["CN_XSHG_600023", "st_flag_official"]))
        self.assertFalse(bool(by_asset.loc["CN_XSHG_600023", "can_sell"]))

    def test_empty_arrow_backed_bars_keep_boolean_flag_dtypes(self) -> None:
        bars = pd.DataFrame(
            {
                "date": pd.Series([], dtype="string[pyarrow]"),
                "asset_id": pd.Series([], dtype="string[pyarrow]"),
                "symbol": pd.Series([], dtype="string[pyarrow]"),
                "market": pd.Series([], dtype="string[pyarrow]"),
                "exchange": pd.Series([], dtype="string[pyarrow]"),
                "open": pd.Series([], dtype="float64"),
                "high": pd.Series([], dtype="float64"),
                "low": pd.Series([], dtype="float64"),
                "close": pd.Series([], dtype="float64"),
                "volume": pd.Series([], dtype="float64"),
                "amount": pd.Series([], dtype="float64"),
            }
        )

        frame = build_cn_stock_tradeability_frame(bars)

        self.assertEqual(len(frame), 0)
        self.assertEqual(str(frame["st_flag"].dtype), "bool")
        self.assertEqual(str(frame["st_flag_official"].dtype), "bool")

    def test_report_counts_flagged_rows(self) -> None:
        bars = pd.DataFrame(
            [
                _bar("CN_XSHG_600001", "600001.SH", "2024-01-03", 10.0, 10.1, 9.9, 10.0, 1000, 10000, "XSHG"),
                _bar("CN_XBEI_920001", "920001.BJ", "2024-01-03", 10.0, 10.1, 9.9, 10.0, 1000, 10000, "XBEI"),
            ]
        )
        stock_basic = pd.DataFrame(
            [
                _basic("CN_XSHG_600001", "600001.SH", "正常银行", "主板", "XSHG", "2020-01-01"),
                _basic("CN_XBEI_920001", "920001.BJ", "北交公司", "北交所", "XBEI", "2020-01-01"),
            ]
        )

        report = build_cn_stock_tradeability_report(bars, stock_basic)

        self.assertEqual(report["summary"]["rows"], 2)
        self.assertEqual(report["summary"]["board_permission_blocked_rows"], 1)
        self.assertEqual(report["summary"]["can_buy_rows"], 1)


def _bar(
    asset_id: str,
    symbol: str,
    date: str,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float,
    amount: float,
    exchange: str,
) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "symbol": symbol,
        "market": "CN",
        "exchange": exchange,
        "asset_type": "stock",
        "date": date,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "adj_close": close,
        "volume": volume,
        "amount": amount,
    }


def _basic(
    asset_id: str,
    symbol: str,
    name: str,
    stock_market: str,
    exchange: str,
    list_date: str,
    *,
    is_active: bool = True,
    delist_date: str | None = None,
) -> dict[str, object]:
    return {
        "asset_id": asset_id,
        "symbol": symbol,
        "market": "CN",
        "exchange": exchange,
        "asset_type": "stock",
        "name": name,
        "stock_market": stock_market,
        "list_date": list_date,
        "delist_date": delist_date,
        "is_active": is_active,
    }


if __name__ == "__main__":
    unittest.main()
