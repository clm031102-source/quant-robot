import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.high_52week_quality_prescreen import (
    build_high_52week_quality_prescreen,
    compute_high_52week_quality_factors,
)
from quant_robot.storage.dataset_store import DatasetStore


def _synthetic_high_52w_bars(days: int = 340, assets: int = 45, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2024-09-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=15))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 8.0 + asset_idx * 0.03
        for day_idx, signal_date in enumerate(dates):
            drift = (asset_idx % 7) * 0.00035
            cycle = ((day_idx % 23) - 11) * 0.00045
            price = max(1.0, price * (1.0 + drift + cycle))
            high = price * (1.01 + (asset_idx % 4) * 0.001)
            low = price * 0.99
            amount = 20_000_000 + asset_idx * 150_000 + (day_idx % 9) * 80_000
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": high,
                    "low": low,
                    "amount": amount,
                }
            )
    return pd.DataFrame(rows)


class High52WeekQualityPrescreenTests(unittest.TestCase):
    def test_computes_all_round207_factor_names_with_capacity_columns(self) -> None:
        factors = compute_high_52week_quality_factors(
            _synthetic_high_52w_bars(),
            min_signal_date_amount=10_000_000,
        )

        names = set(factors["factor_name"])
        self.assertEqual(len(names), 4)
        self.assertIn("high_52w_proximity_liquid_quality_252_20", names)
        self.assertIn("high_52w_pullback_resilience_252_20", names)
        self.assertIn("high_52w_breakout_amount_confirmation_252_20", names)
        self.assertIn("high_52w_low_drawdown_residual_anchor_252_60", names)
        self.assertTrue((factors["amount"] >= 10_000_000).all())
        self.assertTrue((factors["adv20_amount"] >= 10_000_000).all())

    def test_computes_round208_inverse_overextension_factor_names(self) -> None:
        inverse_specs = [
            {"factor_name": "avoid_high_52w_proximity_overextension_252_20"},
            {"factor_name": "avoid_high_52w_breakout_amount_exhaustion_252_20"},
            {"factor_name": "avoid_high_52w_pullback_failure_252_20"},
            {"factor_name": "avoid_high_52w_low_drawdown_crowding_252_60"},
        ]

        factors = compute_high_52week_quality_factors(
            _synthetic_high_52w_bars(),
            candidate_specs=inverse_specs,
            min_signal_date_amount=10_000_000,
        )

        names = set(factors["factor_name"])
        self.assertEqual(len(names), 4)
        self.assertEqual(names, {spec["factor_name"] for spec in inverse_specs})
        self.assertGreater(len(factors), 0)

    def test_builds_prescreen_without_final_holdout_or_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            bars = _synthetic_high_52w_bars(include_holdout=True)
            store = DatasetStore(root)
            store.write_frame(
                bars[pd.to_datetime(bars["date"]).dt.year < 2026],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                bars[pd.to_datetime(bars["date"]).dt.year == 2026],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2026"},
            )

            result = build_high_52week_quality_prescreen(
                bars_roots=[root],
                candidate_plan_json="configs/factor_mining_candidate_plan_round207_52week_high_quality_20260624.json",
                analysis_start_date="2024-09-02",
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

        self.assertEqual(result["stage"], "high_52week_quality_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 4)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["label_rows"], 0)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertNotIn("Round207", result["promotion_policy"]["reason"])
        self.assertNotIn("round207", result["promotion_policy"]["requires_next_gate"])
        self.assertEqual(set(result["summary"]["horizons"]), {5})


if __name__ == "__main__":
    unittest.main()
