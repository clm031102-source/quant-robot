import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit import (
    NEXT_EVENT_ADJUSTED_RERUN,
    STAGE,
    build_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit,
    summarize_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit,
)
from quant_robot.storage.dataset_store import DatasetStore


def _true_close_extreme_bars() -> pd.DataFrame:
    rows = []
    dates = pd.bdate_range("2025-01-02", periods=8)
    scenarios = {
        "CN_XSHE_LIMIT": [10.0, 11.0, 12.1, 13.0, 14.0, 15.0, 16.0, 17.0],
        "CN_XSHE_NEW": [20.0, 20.5, 21.0, 22.0, 24.0, 26.0, 28.0, 30.0],
        "CN_XBEI_BSE": [8.0, 8.5, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0],
        "CN_XSHG_CLEAN": [30.0, 30.5, 31.0, 32.0, 35.0, 39.0, 44.0, 49.0],
    }
    for asset_id, prices in scenarios.items():
        for idx, trade_date in enumerate(dates):
            close = prices[idx]
            prev = prices[idx - 1] if idx else close
            limit_lock = asset_id == "CN_XSHE_LIMIT" and idx in {1, 2}
            low_amount = asset_id == "CN_XBEI_BSE"
            rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "open": close if limit_lock else prev,
                    "high": close,
                    "low": close if limit_lock else min(prev, close) * 0.99,
                    "close": close,
                    "adj_close": close,
                    "amount": 5_000_000.0 if low_amount else 100_000_000.0,
                    "volume": 100_000.0 if low_amount else 10_000_000.0,
                    "adjusted": False,
                }
            )
    return pd.DataFrame(rows)


def _true_close_extreme_trades() -> list[dict[str, object]]:
    base = {
        "guard_mode": "none",
        "cost_bps": 10.0,
        "portfolio_value": 100_000.0,
        "signal_date": "2025-01-02",
        "entry_date": "2025-01-03",
        "exit_date": "2025-01-13",
        "market": "CN",
        "target_notional": 1000.0,
        "entry_amount": 100_000_000.0,
        "participation_rate": 0.00001,
    }
    return [
        {
            **base,
            "case_id": "case_limit_10bps",
            "asset_id": "CN_XSHE_LIMIT",
            "gross_return": 0.5454545454545454,
            "net_return": 0.543,
            "weighted_return": 0.00543,
        },
        {
            **base,
            "case_id": "case_limit_20bps_duplicate",
            "asset_id": "CN_XSHE_LIMIT",
            "gross_return": 0.5454545454545454,
            "net_return": 0.542,
            "weighted_return": 0.00542,
        },
        {
            **base,
            "case_id": "case_new_listing",
            "asset_id": "CN_XSHE_NEW",
            "gross_return": 0.46341463414634143,
            "net_return": 0.461,
            "weighted_return": 0.00461,
        },
        {
            **base,
            "case_id": "case_bse_low_amount",
            "asset_id": "CN_XBEI_BSE",
            "gross_return": 0.6470588235294117,
            "net_return": 0.645,
            "weighted_return": 0.00645,
            "entry_amount": 5_000_000.0,
        },
        {
            **base,
            "case_id": "case_clean_extreme",
            "asset_id": "CN_XSHG_CLEAN",
            "gross_return": 0.6065573770491803,
            "net_return": 0.604,
            "weighted_return": 0.00604,
        },
    ]


def _stock_metadata() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "asset_id": "CN_XSHE_LIMIT",
                "symbol": "LIMIT.SZ",
                "market": "CN",
                "exchange": "XSHE",
                "name": "limit name",
                "is_active": True,
                "list_date": "2020-01-01",
                "delist_date": None,
                "stock_market": "主板",
            },
            {
                "asset_id": "CN_XSHE_NEW",
                "symbol": "NEW.SZ",
                "market": "CN",
                "exchange": "XSHE",
                "name": "new name",
                "is_active": True,
                "list_date": "2024-12-15",
                "delist_date": None,
                "stock_market": "创业板",
            },
            {
                "asset_id": "CN_XBEI_BSE",
                "symbol": "BSE.BJ",
                "market": "CN",
                "exchange": "XBEI",
                "name": "bse name",
                "is_active": True,
                "list_date": "2020-01-01",
                "delist_date": None,
                "stock_market": "北交所",
            },
            {
                "asset_id": "CN_XSHG_CLEAN",
                "symbol": "CLEAN.SH",
                "market": "CN",
                "exchange": "XSHG",
                "name": "clean name",
                "is_active": True,
                "list_date": "2018-01-01",
                "delist_date": None,
                "stock_market": "主板",
            },
        ]
    )


class DailyBasicFreeFloatSupplyQualityTrueCloseExtremeTradeLiquidityLimitAuditTests(unittest.TestCase):
    def test_audit_blocks_limit_new_listing_bse_and_dedupes_repeated_case_rows(self) -> None:
        result = summarize_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit(
            extreme_trades=_true_close_extreme_trades(),
            bars=_true_close_extreme_bars(),
            stock_metadata=_stock_metadata(),
            min_listing_days=120,
            min_entry_amount=10_000_000.0,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["summary"]["raw_extreme_trade_count"], 5)
        self.assertEqual(result["summary"]["unique_trade_path_count"], 4)
        self.assertEqual(result["summary"]["entry_limit_up_like_unique_paths"], 1)
        self.assertEqual(result["summary"]["new_listing_unique_paths"], 1)
        self.assertEqual(result["summary"]["bse_unique_paths"], 1)
        self.assertEqual(result["summary"]["low_entry_amount_unique_paths"], 1)
        self.assertEqual(result["summary"]["no_obvious_tradeability_blocker_unique_paths"], 1)
        self.assertEqual(result["next_direction"], NEXT_EVENT_ADJUSTED_RERUN)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        limit_row = next(row for row in result["trade_path_audit"] if row["asset_id"] == "CN_XSHE_LIMIT")
        self.assertIn("entry_limit_up_buy_execution_risk", limit_row["blockers"])
        self.assertEqual(limit_row["duplicate_case_rows"], 2)

    def test_build_loads_trades_bars_and_metadata_from_dataset_store(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            metadata_root = Path(tmp) / "metadata"
            report = Path(tmp) / "round138.json"
            DatasetStore(root).write_frame(
                _true_close_extreme_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(metadata_root).write_frame(
                _stock_metadata(),
                "metadata/tushare_stock_basic",
                {"snapshot": "2026-06-21"},
            )
            report.write_text(
                json.dumps({"extreme_trades": _true_close_extreme_trades()}),
                encoding="utf-8",
            )

            result = build_daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit(
                bars_roots=[root],
                stock_metadata_roots=[metadata_root],
                repaired_rerun_report=report,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
            )

        self.assertEqual(result["summary"]["unique_trade_path_count"], 4)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertEqual(result["data_window"]["bar_assets"], 4)


if __name__ == "__main__":
    unittest.main()
