import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_stock_tradeability_data_readiness_audit import (
    build_cn_stock_tradeability_data_readiness_audit,
)


def _write_parquet(path: Path, frame: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path, index=False)


class CnStockTradeabilityDataReadinessAuditTests(unittest.TestCase):
    def test_marks_direct_mining_blocked_when_only_proxy_tradeability_data_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2015-01-05", "2015-01-06"]).date,
                    "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
                    "symbol": ["000001.SZ", "000001.SZ"],
                    "market": ["CN", "CN"],
                    "open": [10.0, 10.1],
                    "high": [10.4, 10.2],
                    "low": [9.9, 9.8],
                    "close": [10.2, 9.9],
                    "volume": [1000.0, 1100.0],
                    "amount": [10000.0, 11000.0],
                }
            )
            metadata = pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "exchange": ["XSHE"],
                    "name": ["Ping An Bank"],
                    "is_active": [True],
                    "list_date": [pd.Timestamp("1991-04-03").date()],
                    "delist_date": [pd.Timestamp("2027-01-01").date()],
                    "stock_market": ["main"],
                }
            )
            _write_parquet(
                root / "processed/bars/frequency=1d/market=CN/year=2015/part-00000.parquet",
                bars,
            )
            _write_parquet(
                root / "metadata/tushare_stock_basic/list_status=L/snapshot=2026-06-21/part-00000.parquet",
                metadata,
            )

            packet = build_cn_stock_tradeability_data_readiness_audit(
                data_roots=[root],
                expected_start="2015-01-01",
                expected_end="2015-01-06",
            )

            self.assertEqual(packet["stage"], "cn_stock_tradeability_data_readiness_audit")
            self.assertEqual(packet["status"], "direct_mining_blocked")
            self.assertFalse(packet["decision"]["direct_factor_generation_allowed"])
            control_status = {row["control_id"]: row["status"] for row in packet["control_rows"]}
            self.assertEqual(control_status["new_listing_age_filter"], "ready")
            self.assertEqual(control_status["board_permission_filter"], "ready")
            self.assertEqual(control_status["limit_up_down_filter"], "proxy_only")
            self.assertEqual(control_status["suspension_filter"], "proxy_only")
            self.assertEqual(control_status["st_flag_filter"], "blocked_missing_official_history")
            self.assertEqual(control_status["delisting_risk_filter"], "blocked_missing_official_history")
            self.assertIn("tushare_stk_limit_or_limit_list", packet["missing_data_feeds"])
            self.assertEqual(packet["summary"]["expected_window_coverage"], "covered")
            self.assertEqual(
                packet["decision"]["next_round_direction"],
                "round198_continue_long_cycle_tradeability_backfill_until_manifest_coverage_then_mask_integration",
            )

    def test_all_official_tradeability_feeds_ready_allows_direct_mining_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2015-01-05"]).date,
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "market": ["CN"],
                    "open": [10.0],
                    "high": [10.4],
                    "low": [9.9],
                    "close": [10.2],
                    "volume": [1000.0],
                    "amount": [10000.0],
                    "up_limit": [11.0],
                    "down_limit": [9.0],
                    "is_suspended": [False],
                    "is_st": [False],
                    "is_delisted": [False],
                }
            )
            metadata = pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "exchange": ["XSHE"],
                    "name": ["Ping An Bank"],
                    "is_active": [True],
                    "list_date": [pd.Timestamp("1991-04-03").date()],
                    "delist_date": [None],
                    "stock_market": ["main"],
                    "list_status": ["L"],
                }
            )
            _write_parquet(
                root / "processed/bars/frequency=1d/market=CN/year=2015/part-00000.parquet",
                bars,
            )
            _write_parquet(
                root / "metadata/tushare_stock_basic/list_status=L/snapshot=2026-06-21/part-00000.parquet",
                metadata,
            )

            packet = build_cn_stock_tradeability_data_readiness_audit(data_roots=[root])

            self.assertEqual(packet["status"], "tradeability_data_ready")
            self.assertTrue(packet["decision"]["direct_factor_generation_allowed"])
            self.assertEqual(packet["decision"]["blockers"], [])
            self.assertEqual(
                packet["decision"]["next_round_direction"],
                "round198_tradeability_controls_ready_for_quality_gate_closeout_after_manifest_coverage",
            )

    def test_official_tradeability_datasets_close_proxy_blockers_without_bar_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-02"]).date,
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "market": ["CN"],
                    "open": [10.0],
                    "high": [10.4],
                    "low": [9.9],
                    "close": [10.2],
                    "volume": [1000.0],
                    "amount": [10000.0],
                }
            )
            metadata_l = pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "exchange": ["XSHE"],
                    "name": ["Ping An Bank"],
                    "is_active": [True],
                    "list_status": ["L"],
                    "list_date": [pd.Timestamp("1991-04-03").date()],
                    "delist_date": [None],
                    "stock_market": ["main"],
                }
            )
            metadata_d = metadata_l.copy()
            metadata_d["asset_id"] = ["CN_XSHE_000002"]
            metadata_d["symbol"] = ["000002.SZ"]
            metadata_d["is_active"] = [False]
            metadata_d["list_status"] = ["D"]
            metadata_d["delist_date"] = [pd.Timestamp("2024-01-03").date()]
            limit = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-02"]).date,
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "up_limit": [11.0],
                    "down_limit": [9.0],
                }
            )
            suspension = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-02"]).date,
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "suspend_reason": ["meeting"],
                }
            )
            namechange = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2024-01-02"]).date,
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "name": ["*ST Sample"],
                    "is_st_name": [True],
                }
            )
            _write_parquet(root / "processed/bars/frequency=1d/market=CN/year=2024/part-00000.parquet", bars)
            _write_parquet(
                root / "metadata/tushare_stock_basic/list_status=L/snapshot=2026-06-23/part-00000.parquet",
                metadata_l,
            )
            _write_parquet(
                root / "metadata/tushare_stock_basic/list_status=D/snapshot=2026-06-23/part-00000.parquet",
                metadata_d,
            )
            _write_parquet(
                root / "processed/tradeability_stk_limit/frequency=1d/market=CN/year=2024/part-00000.parquet",
                limit,
            )
            _write_parquet(
                root / "processed/tradeability_suspension/frequency=1d/market=CN/year=2024/part-00000.parquet",
                suspension,
            )
            _write_parquet(
                root / "processed/tradeability_namechange/frequency=1d/market=CN/year=2024/part-00000.parquet",
                namechange,
            )

            packet = build_cn_stock_tradeability_data_readiness_audit(data_roots=[root])

            self.assertEqual(packet["status"], "tradeability_data_ready")
            control_status = {row["control_id"]: row["status"] for row in packet["control_rows"]}
            self.assertEqual(control_status["limit_up_down_filter"], "ready")
            self.assertEqual(control_status["suspension_filter"], "ready")
            self.assertEqual(control_status["st_flag_filter"], "ready")
            self.assertEqual(control_status["delisting_risk_filter"], "ready")

    def test_partial_official_feed_coverage_blocks_expected_long_window_direct_mining(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2015-01-05", "2015-03-05"]).date,
                    "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
                    "symbol": ["000001.SZ", "000001.SZ"],
                    "market": ["CN", "CN"],
                    "open": [10.0, 10.5],
                    "high": [10.4, 10.7],
                    "low": [9.9, 10.2],
                    "close": [10.2, 10.4],
                    "volume": [1000.0, 1200.0],
                    "amount": [10000.0, 12500.0],
                }
            )
            metadata_l = pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "exchange": ["XSHE"],
                    "name": ["Ping An Bank"],
                    "is_active": [True],
                    "list_status": ["L"],
                    "list_date": [pd.Timestamp("1991-04-03").date()],
                    "delist_date": [None],
                    "stock_market": ["main"],
                }
            )
            metadata_d = metadata_l.copy()
            metadata_d["asset_id"] = ["CN_XSHE_000002"]
            metadata_d["symbol"] = ["000002.SZ"]
            metadata_d["is_active"] = [False]
            metadata_d["list_status"] = ["D"]
            metadata_d["delist_date"] = [pd.Timestamp("2015-02-01").date()]
            limit = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2015-01-05"]).date,
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "up_limit": [11.0],
                    "down_limit": [9.0],
                }
            )
            suspension = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2015-01-05"]).date,
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "suspend_reason": ["meeting"],
                }
            )
            namechange = pd.DataFrame(
                {
                    "date": pd.to_datetime(["2015-01-05"]).date,
                    "asset_id": ["CN_XSHE_000001"],
                    "symbol": ["000001.SZ"],
                    "name": ["*ST Sample"],
                    "is_st_name": [True],
                    "start_date": [pd.Timestamp("2015-01-05").date()],
                    "ann_date": [pd.Timestamp("2015-01-05").date()],
                }
            )
            coverage = pd.DataFrame(
                {
                    "feed": [
                        "tradeability_stk_limit",
                        "tradeability_suspension",
                        "tradeability_namechange",
                    ],
                    "start_date": ["2015-01-01", "2015-01-01", "2015-01-01"],
                    "end_date": ["2015-01-31", "2015-01-31", "2015-01-31"],
                    "market": ["CN", "CN", "CN"],
                    "shard_id": ["20150101_20150131"] * 3,
                }
            )
            _write_parquet(root / "processed/bars/frequency=1d/market=CN/year=2015/part-00000.parquet", bars)
            _write_parquet(root / "metadata/tushare_stock_basic/list_status=L/snapshot=2026-06-23/part-00000.parquet", metadata_l)
            _write_parquet(root / "metadata/tushare_stock_basic/list_status=D/snapshot=2026-06-23/part-00000.parquet", metadata_d)
            _write_parquet(root / "processed/tradeability_stk_limit/frequency=1d/market=CN/year=2015/part-00000.parquet", limit)
            _write_parquet(root / "processed/tradeability_suspension/frequency=1d/market=CN/year=2015/part-00000.parquet", suspension)
            _write_parquet(root / "processed/tradeability_namechange/frequency=1d/market=CN/year=2015/part-00000.parquet", namechange)
            _write_parquet(
                root / "metadata/tushare_tradeability_feed_coverage/market=CN/shard=20150101_20150131/part-00000.parquet",
                coverage,
            )

            packet = build_cn_stock_tradeability_data_readiness_audit(
                data_roots=[root],
                expected_start="2015-01-01",
                expected_end="2015-03-31",
            )

            self.assertEqual(packet["status"], "direct_mining_blocked")
            self.assertFalse(packet["decision"]["direct_factor_generation_allowed"])
            control_status = {row["control_id"]: row["status"] for row in packet["control_rows"]}
            self.assertEqual(control_status["limit_up_down_filter"], "partial_coverage")
            self.assertEqual(control_status["suspension_filter"], "partial_coverage")
            self.assertEqual(control_status["st_flag_filter"], "partial_coverage")
            self.assertEqual(packet["summary"]["limit_feed_expected_window_coverage"], "incomplete")


if __name__ == "__main__":
    unittest.main()
