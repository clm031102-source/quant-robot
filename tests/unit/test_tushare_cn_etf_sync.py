import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.tushare_cn_etf_sync import (
    build_cn_etf_rotation_membership,
    build_cn_etf_rotation_pool,
    run_tushare_cn_etf_sync,
)
from quant_robot.storage.dataset_store import DatasetStore


class FakeTushareCnEtfSyncAdapter:
    def __init__(self) -> None:
        self.fund_basic_kwargs = {}
        self.daily_calls = []
        self.share_size_calls = []
        self.fund_portfolio_calls = []

    def fetch_fund_basic(self, market: str = "E", status: str = "L") -> pd.DataFrame:
        self.fund_basic_kwargs = {"market": market, "status": status}
        return pd.DataFrame(
            {
                "symbol": ["510300.SH", "159915.SZ", "501001.SH", "588000.SH", "510500.SH"],
                "name": ["CSI 300 ETF", "ChiNext ETF", "Listed LOF", "STAR 50 ETF", "CSI 500 ETF"],
                "fund_type": ["Equity", "Equity", "Mixed", "ETF", "Equity"],
                "type": ["ETF", "ETF", "LOF", "ETF", "ETF"],
                "market": ["E", "E", "E", "E", "E"],
                "status": ["L", "L", "L", "L", "D"],
                "list_date": [
                    pd.Timestamp("2012-06-01").date(),
                    pd.Timestamp("2015-01-01").date(),
                    pd.Timestamp("2016-01-01").date(),
                    pd.Timestamp("2026-01-01").date(),
                    pd.Timestamp("2013-01-01").date(),
                ],
                "delist_date": [pd.NaT, pd.NaT, pd.NaT, pd.NaT, pd.Timestamp("2024-01-01").date()],
                "is_active": [True, True, True, True, False],
                "is_exchange_traded": [True, True, True, True, True],
                "is_etf": [True, True, False, True, True],
            }
        )

    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        dates = pd.date_range(start_date, end_date, freq="D")
        return pd.DataFrame({"exchange": "SSE", "date": dates.date, "is_open": 1})

    def fetch_etf_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        self.daily_calls.append(trade_date)
        date = pd.to_datetime(trade_date, format="%Y%m%d").date()
        return pd.DataFrame(
            {
                "symbol": ["510300.SH", "159915.SZ"],
                "date": [date, date],
                "open": [4.0, 2.0],
                "high": [4.1, 2.1],
                "low": [3.9, 1.9],
                "close": [4.05, 2.05],
                "volume": [100000.0, 200000.0],
                "amount": [405000.0, 410000.0],
            }
        )

    def fetch_etf_share_size_by_trade_date(self, trade_date: str, exchange: str = "") -> pd.DataFrame:
        self.share_size_calls.append((trade_date, exchange))
        date = pd.to_datetime(trade_date, format="%Y%m%d").date()
        if exchange == "SSE":
            return pd.DataFrame(
                {
                    "symbol": ["510300.SH"],
                    "date": [date],
                    "name": ["CSI 300 ETF"],
                    "total_share": [10_000_000.0],
                    "total_size": [40_000_000.0],
                    "nav": [4.0],
                    "close": [4.05],
                    "exchange": ["SSE"],
                }
            )
        return pd.DataFrame(
            {
                "symbol": ["159915.SZ"],
                "date": [date],
                "name": ["ChiNext ETF"],
                "total_share": [20_000_000.0],
                "total_size": [41_000_000.0],
                "nav": [2.0],
                "close": [2.05],
                "exchange": ["SZSE"],
            }
        )

    def fetch_fund_portfolio(self, ts_code: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        self.fund_portfolio_calls.append((ts_code, start_date, end_date))
        if ts_code == "510300.SH":
            return pd.DataFrame(
                {
                    "fund_symbol": ["510300.SH", "510300.SH"],
                    "known_date": [pd.Timestamp("2024-01-10").date(), pd.Timestamp("2024-01-10").date()],
                    "period_end_date": [pd.Timestamp("2023-12-31").date(), pd.Timestamp("2023-12-31").date()],
                    "stock_symbol": ["600519.SH", "000001.SZ"],
                    "mkv": [60.0, 40.0],
                    "amount": [1.0, 2.0],
                    "stk_mkv_ratio": [6.0, 4.0],
                    "stk_float_ratio": [0.1, 0.2],
                }
            )
        if ts_code == "159915.SZ":
            return pd.DataFrame(
                {
                    "fund_symbol": ["159915.SZ"],
                    "known_date": [pd.Timestamp("2024-01-11").date()],
                    "period_end_date": [pd.Timestamp("2023-12-31").date()],
                    "stock_symbol": ["300750.SZ"],
                    "mkv": [100.0],
                    "amount": [3.0],
                    "stk_mkv_ratio": [10.0],
                    "stk_float_ratio": [0.3],
                }
            )
        return pd.DataFrame()


class TushareCnEtfSyncTests(unittest.TestCase):
    def test_rotation_pool_filters_low_liquidity_zero_volume_extreme_returns_and_short_history(self):
        universe = pd.DataFrame(
            {
                "symbol": ["510300.SH", "159915.SZ", "588000.SH", "512100.SH"],
                "name": ["Liquid ETF", "Low Amount ETF", "Extreme ETF", "Short ETF"],
            }
        )
        bars = pd.DataFrame(
            {
                "asset_id": ["CN_ETF_XSHG_510300"] * 3
                + ["CN_ETF_XSHE_159915"] * 3
                + ["CN_ETF_XSHG_588000"] * 3
                + ["CN_ETF_XSHG_512100"],
                "symbol": ["510300.SH"] * 3 + ["159915.SZ"] * 3 + ["588000.SH"] * 3 + ["512100.SH"],
                "date": list(pd.date_range("2024-01-02", periods=3).date) * 3 + [pd.Timestamp("2024-01-02").date()],
                "market": ["CN_ETF"] * 10,
                "close": [1.0, 1.01, 1.02, 2.0, 2.0, 2.0, 3.0, 9.5, 9.6, 4.0],
                "volume": [100.0, 110.0, 120.0, 10.0, 0.0, 10.0, 100.0, 100.0, 100.0, 100.0],
                "amount": [2_000_000.0, 2_100_000.0, 2_200_000.0, 10_000.0, 0.0, 10_000.0, 2_000_000.0, 2_000_000.0, 2_000_000.0, 2_000_000.0],
            }
        )

        pool = build_cn_etf_rotation_pool(
            universe,
            bars,
            min_history_rows=3,
            min_median_amount=1_000_000.0,
            max_zero_volume_ratio=0.0,
            extreme_return_threshold=0.5,
        )

        self.assertEqual(pool["eligible_symbols"], ["510300.SH"])
        self.assertEqual(
            {row["symbol"]: row["exclusion_reasons"] for row in pool["excluded"]},
            {
                "159915.SZ": ["median_amount_below_threshold", "zero_volume_ratio_above_threshold"],
                "588000.SH": ["extreme_return_rows_present"],
                "512100.SH": ["insufficient_history_rows"],
            },
        )

    def test_rotation_membership_preserves_historical_delisted_etfs_without_current_survivorship_filter(self):
        fund_basic = pd.DataFrame(
            {
                "symbol": ["510300.SH", "510500.SH", "501001.SH", "159915.SZ"],
                "name": ["Current ETF", "Delisted ETF", "Listed LOF", "Low Amount ETF"],
                "fund_type": ["ETF", "ETF", "LOF", "ETF"],
                "type": ["ETF", "ETF", "LOF", "ETF"],
                "market": ["E", "E", "E", "E"],
                "status": ["L", "D", "L", "L"],
                "list_date": [
                    pd.Timestamp("2020-01-01").date(),
                    pd.Timestamp("2020-01-01").date(),
                    pd.Timestamp("2020-01-01").date(),
                    pd.Timestamp("2020-01-01").date(),
                ],
                "delist_date": [pd.NaT, pd.Timestamp("2024-01-04").date(), pd.NaT, pd.NaT],
                "is_exchange_traded": [True, True, True, True],
                "is_etf": [True, True, False, True],
            }
        )
        dates = list(pd.date_range("2024-01-02", periods=4).date)
        bars = pd.DataFrame(
            {
                "asset_id": ["CN_ETF_XSHG_510300"] * 4
                + ["CN_ETF_XSHG_510500"] * 4
                + ["CN_ETF_XSHG_501001"] * 4
                + ["CN_ETF_XSHE_159915"] * 4,
                "symbol": ["510300.SH"] * 4 + ["510500.SH"] * 4 + ["501001.SH"] * 4 + ["159915.SZ"] * 4,
                "date": dates * 4,
                "market": ["CN_ETF"] * 16,
                "close": [1.0, 1.01, 1.02, 1.03] * 4,
                "volume": [100.0, 100.0, 100.0, 100.0] * 4,
                "amount": [2_000_000.0, 2_100_000.0, 2_200_000.0, 2_300_000.0] * 3
                + [10_000.0, 10_000.0, 10_000.0, 10_000.0],
            }
        )

        membership = build_cn_etf_rotation_membership(
            fund_basic,
            bars,
            min_history_rows=2,
            min_median_amount=1_000_000.0,
            max_zero_volume_ratio=0.0,
            extreme_return_threshold=0.5,
        )

        current = membership[(membership["symbol"] == "510300.SH") & (membership["date"] == pd.Timestamp("2024-01-03").date())].iloc[0]
        delisted_before = membership[(membership["symbol"] == "510500.SH") & (membership["date"] == pd.Timestamp("2024-01-03").date())].iloc[0]
        delisted_on = membership[(membership["symbol"] == "510500.SH") & (membership["date"] == pd.Timestamp("2024-01-04").date())].iloc[0]
        lof = membership[(membership["symbol"] == "501001.SH") & (membership["date"] == pd.Timestamp("2024-01-03").date())].iloc[0]
        low_amount = membership[(membership["symbol"] == "159915.SZ") & (membership["date"] == pd.Timestamp("2024-01-03").date())].iloc[0]

        self.assertTrue(bool(current["is_rotation_member"]))
        self.assertTrue(bool(delisted_before["is_rotation_member"]))
        self.assertFalse(bool(delisted_on["is_rotation_member"]))
        self.assertIn("not_listed_on_date", delisted_on["exclusion_reasons"])
        self.assertFalse(bool(lof["is_rotation_member"]))
        self.assertIn("not_etf", lof["exclusion_reasons"])
        self.assertFalse(bool(low_amount["is_rotation_member"]))
        self.assertIn("median_amount_below_threshold", low_amount["exclusion_reasons"])

    def test_sync_fetches_all_status_fund_basic_filters_universe_and_ingests_fund_daily(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = FakeTushareCnEtfSyncAdapter()

            result = run_tushare_cn_etf_sync(
                adapter=adapter,
                start_date="2024-01-02",
                end_date="2024-01-03",
                output_dir=root / "processed",
                report_dir=root / "reports",
                as_of="2024-12-31",
                source="tushare-fixture",
                min_rotation_history_rows=2,
            )

            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["primary_market"], "CN_ETF")
            self.assertEqual(adapter.fund_basic_kwargs, {"market": "E", "status": ""})
            self.assertEqual(adapter.daily_calls, ["20240102", "20240103"])
            self.assertEqual(
                adapter.share_size_calls,
                [
                    ("20240102", "SSE"),
                    ("20240102", "SZSE"),
                    ("20240103", "SSE"),
                    ("20240103", "SZSE"),
                ],
            )
            self.assertEqual(
                adapter.fund_portfolio_calls,
                [
                    ("159915.SZ", "2024-01-02", "2024-01-03"),
                    ("510300.SH", "2024-01-02", "2024-01-03"),
                ],
            )
            self.assertEqual(result["universe"]["eligible_symbols"], ["159915.SZ", "510300.SH"])
            self.assertEqual(result["ingest"]["processed_rows"], 4)
            self.assertEqual(result["etf_share_size"]["processed_rows"], 4)
            self.assertEqual(result["fund_portfolio_baskets"]["processed_rows"], 3)
            self.assertGreater(result["rotation_membership"]["rows"], 0)
            self.assertEqual(result["survivorship_policy"]["historical_delisted_etfs"], "preserved_when_listed_on_date")
            self.assertEqual(result["auxiliary_datasets"]["etf_share_size"], "enabled")
            self.assertEqual(result["auxiliary_datasets"]["etf_moneyflow_baskets"], "enabled")
            self.assertFalse(result["live_boundary_allowed"])
            self.assertEqual(result["auxiliary_feature_policy"]["cn_stock_moneyflow"], "auxiliary_only")

            saved_pack = json.loads((root / "reports" / "tushare_cn_etf_sync_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_pack["status"], "completed")
            self.assertEqual(saved_pack["etf_share_size"]["dataset"], "etf_share_size")
            saved_universe = DatasetStore(root / "processed").read_frame(
                "metadata/cn_etf_universe",
                {"as_of": "2024-12-31", "market": "CN_ETF"},
            )
            self.assertEqual(saved_universe["symbol"].tolist(), ["159915.SZ", "510300.SH"])
            saved_share_size = DatasetStore(root / "processed").read_frame(
                "processed/etf_share_size",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )
            self.assertEqual(set(saved_share_size["asset_id"]), {"CN_ETF_XSHG_510300", "CN_ETF_XSHE_159915"})
            saved_baskets = DatasetStore(root / "processed").read_frame(
                "metadata/etf_moneyflow_baskets",
                {"market": "CN_ETF"},
            )
            self.assertEqual(set(saved_baskets["etf_asset_id"]), {"CN_ETF_XSHG_510300", "CN_ETF_XSHE_159915"})
            self.assertEqual(set(saved_baskets["stock_asset_id"]), {"CN_XSHG_600519", "CN_XSHE_000001", "CN_XSHE_300750"})
            saved_membership = DatasetStore(root / "processed").read_frame(
                "metadata/cn_etf_rotation_membership",
                {"market": "CN_ETF"},
            )
            self.assertEqual(set(saved_membership["symbol"]), {"159915.SZ", "510300.SH"})
            self.assertTrue(saved_membership["is_rotation_member"].any())


if __name__ == "__main__":
    unittest.main()
