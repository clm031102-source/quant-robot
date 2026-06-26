import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.ops.negative_ic_trend_accumulation_prescreen import (
    build_negative_ic_trend_accumulation_prescreen,
    compute_negative_ic_trend_accumulation_factors,
)


def _synthetic_negative_ic_bars(days: int = 110, assets: int = 42, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 8.0 + asset_idx * 0.05
        for day_idx, signal_date in enumerate(dates):
            trend = (asset_idx % 9) * 0.0007
            cycle = ((day_idx % 19) - 9) * 0.0008
            price = max(1.0, price * (1.0 + trend + cycle))
            high = price * (1.01 + (asset_idx % 3) * 0.001)
            low = price * 0.99
            amount = 18_000_000 + asset_idx * 120_000 + (day_idx % 7) * 90_000
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


class NegativeIcTrendAccumulationPrescreenTests(unittest.TestCase):
    def test_computes_all_round106_factor_names_without_positive_direction_names(self) -> None:
        factors = compute_negative_ic_trend_accumulation_factors(
            _synthetic_negative_ic_bars(),
            min_signal_date_amount=10_000_000,
        )

        names = set(factors["factor_name"])
        self.assertEqual(len(names), 10)
        self.assertIn("anti_volume_weighted_momentum_quality_20", names)
        self.assertIn("anti_money_pressure_efficiency_20", names)
        self.assertIn("overheat_avoidance_composite_20_60", names)
        self.assertTrue(all(("anti" in name or "avoidance" in name or "exhaustion" in name) for name in names))
        forbidden_names = {
            "volume_weighted_momentum_quality_20",
            "amount_accumulation_breakout_20_60",
            "money_pressure_efficiency_20",
            "turnover_expansion_momentum_10_40",
        }
        self.assertFalse(names.intersection(forbidden_names))
        self.assertTrue((factors["amount"] >= 10_000_000).all())
        self.assertTrue((factors["adv20_amount"] >= 10_000_000).all())

    def test_builds_prescreen_without_reading_final_holdout_and_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            bars = _synthetic_negative_ic_bars(include_holdout=True)
            store = DatasetStore(root)
            store.write_frame(
                bars[bars["date"].dt.year == 2025],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                bars[bars["date"].dt.year == 2026],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2026"},
            )

            result = build_negative_ic_trend_accumulation_prescreen(
                bars_roots=[root],
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

        self.assertEqual(result["stage"], "negative_ic_trend_accumulation_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 10)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["label_rows"], 0)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertEqual(result["promotion_policy"]["requires_next_gate"], "candidate_correlation_dedup_before_portfolio_grid")
        self.assertEqual(result["promotion_policy"]["next_allowed_action"], "candidate_correlation_dedup_if_research_leads_survive")
        self.assertEqual(set(result["summary"]["horizons"]), {5})


if __name__ == "__main__":
    unittest.main()
