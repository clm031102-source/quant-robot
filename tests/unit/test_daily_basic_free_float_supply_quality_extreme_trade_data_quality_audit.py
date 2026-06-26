import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit import (
    NEXT_PRICE_BASIS_REPAIR,
    STAGE,
    build_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit,
    summarize_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit,
)
from quant_robot.storage.dataset_store import DatasetStore


def _mixed_basis_bars() -> pd.DataFrame:
    dates = pd.bdate_range("2025-06-26", periods=6)
    rows = []
    for idx, trade_date in enumerate(dates):
        close = 10.0 + idx * 0.2
        adjusted = trade_date >= pd.Timestamp("2025-07-01")
        rows.append(
            {
                "date": trade_date,
                "asset_id": "CN_XSHE_TEST1",
                "symbol": "TEST1.SZ",
                "market": "CN",
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "adj_close": close * 100.0 if adjusted else close,
                "amount": 100_000_000.0,
                "volume": 10_000_000.0,
                "adjusted": adjusted,
                "source": "synthetic",
            }
        )
    for idx, trade_date in enumerate(dates):
        close = 20.0 + idx * 0.1
        rows.append(
            {
                "date": trade_date,
                "asset_id": "CN_XSHE_TEST2",
                "symbol": "TEST2.SZ",
                "market": "CN",
                "open": close,
                "high": close * 1.01,
                "low": close * 0.99,
                "close": close,
                "adj_close": close,
                "amount": 100_000_000.0,
                "volume": 10_000_000.0,
                "adjusted": False,
                "source": "synthetic",
            }
        )
    return pd.DataFrame(rows)


def _extreme_trades() -> list[dict[str, object]]:
    return [
        {
            "case_id": "case_a",
            "guard_mode": "block_stress_rebalance_dates",
            "cost_bps": 10.0,
            "portfolio_value": 100_000.0,
            "signal_date": "2025-06-27",
            "entry_date": "2025-06-30",
            "exit_date": "2025-07-01",
            "asset_id": "CN_XSHE_TEST1",
            "market": "CN",
            "gross_return": 100.81818181818181,
            "net_return": 100.816,
            "weighted_return": 1.00816,
            "target_notional": 1000.0,
            "entry_amount": 100_000_000.0,
            "participation_rate": 0.00001,
        }
    ]


class DailyBasicFreeFloatSupplyQualityExtremeTradeDataQualityAuditTests(unittest.TestCase):
    def test_mixed_price_basis_extreme_trade_is_classified_as_phantom_alpha(self) -> None:
        result = summarize_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
            extreme_trades=_extreme_trades(),
            bars=_mixed_basis_bars(),
            price_ratio_jump_threshold=1.5,
            plausible_close_return_abs_threshold=0.5,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["summary"]["extreme_trade_count"], 1)
        self.assertEqual(result["summary"]["mixed_price_basis_trade_count"], 1)
        self.assertEqual(result["summary"]["phantom_alpha_trade_count"], 1)
        self.assertEqual(result["next_direction"], NEXT_PRICE_BASIS_REPAIR)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        audit = result["asset_path_audit"][0]
        self.assertEqual(audit["data_quality_class"], "mixed_price_basis_phantom_alpha")
        self.assertTrue(audit["entry_adjusted"] is False)
        self.assertTrue(audit["exit_adjusted"] is True)
        self.assertGreater(audit["ratio_jump"], 50.0)
        self.assertLess(abs(audit["close_gross_return"]), 0.5)
        self.assertGreater(audit["adj_gross_return"], 50.0)

    def test_date_basis_audit_detects_market_wide_adjusted_flag_transition(self) -> None:
        result = summarize_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
            extreme_trades=_extreme_trades(),
            bars=_mixed_basis_bars(),
            price_ratio_jump_threshold=1.5,
        )

        dates = {row["date"]: row for row in result["date_basis_audit"]}
        self.assertIn("2025-07-01", dates)
        self.assertGreaterEqual(dates["2025-07-01"]["adjusted_true"], 1)
        self.assertGreater(dates["2025-07-01"]["median_ratio_jump"], 1.5)
        self.assertIn("market_wide_price_basis_transition", result["gate"]["blockers"])

    def test_date_basis_audit_ignores_small_adjusted_count_churn(self) -> None:
        rows = []
        for trade_date, adjusted_count in [
            (pd.Timestamp("2025-06-30"), 1),
            (pd.Timestamp("2025-07-01"), 2),
        ]:
            for idx in range(100):
                adjusted = idx < adjusted_count
                close = 10.0 + idx * 0.01
                rows.append(
                    {
                        "date": trade_date,
                        "asset_id": f"CN_XSHE_CHURN{idx:03d}",
                        "symbol": f"CHURN{idx:03d}.SZ",
                        "market": "CN",
                        "close": close,
                        "adj_close": close,
                        "amount": 100_000_000.0,
                        "volume": 10_000_000.0,
                        "adjusted": adjusted,
                        "source": "synthetic",
                    }
                )

        result = summarize_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
            extreme_trades=[],
            bars=pd.DataFrame(rows),
            price_ratio_jump_threshold=1.5,
        )

        self.assertEqual(result["summary"]["market_wide_transition_date_count"], 0)
        self.assertNotIn("market_wide_price_basis_transition", result["gate"]["blockers"])

    def test_build_writes_audit_from_dataset_store_without_final_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            DatasetStore(root).write_frame(
                _mixed_basis_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = build_daily_basic_free_float_supply_quality_extreme_trade_data_quality_audit(
                bars_roots=[root],
                extreme_trades=_extreme_trades(),
                analysis_start_date="2025-06-01",
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
            )

        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertEqual(result["data_window"]["max_bar_date"], "2025-07-03")
        self.assertEqual(result["summary"]["phantom_alpha_trade_count"], 1)


if __name__ == "__main__":
    unittest.main()
