import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.ops.market_residual_risk_premia_prescreen import (
    build_equal_weight_market_proxy,
    build_market_residual_risk_premia_prescreen,
    compute_market_residual_risk_premia_factors,
)


def _synthetic_residual_bars(days: int = 180, assets: int = 45, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 12.0 + asset_idx * 0.05
        for day_idx, date in enumerate(dates):
            market_wave = ((day_idx % 23) - 11) * 0.0008
            beta_load = 0.25 + (asset_idx % 9) * 0.08
            idio = ((asset_idx * 3 + day_idx) % 13 - 6) * 0.0004
            price = max(1.0, price * (1.0 + beta_load * market_wave + idio))
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * (1.012 + (asset_idx % 3) * 0.001),
                    "low": price * (0.988 - (asset_idx % 3) * 0.001),
                    "amount": 22_000_000 + asset_idx * 120_000 + (day_idx % 5) * 80_000,
                }
            )
    return pd.DataFrame(rows)


class MarketResidualRiskPremiaPrescreenTests(unittest.TestCase):
    def test_equal_weight_market_proxy_uses_same_date_returns_not_future_rows(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=3)
        base_rows = []
        prices_by_asset = {
            "000001.SZ": [100.0, 110.0, 90.0],
            "000002.SZ": [50.0, 45.0, 54.0],
            "000003.SZ": [10.0, 10.0, 15.0],
        }
        for asset_id, prices in prices_by_asset.items():
            for date, price in zip(dates, prices):
                base_rows.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "symbol": asset_id,
                        "market": "CN",
                        "adj_close": price,
                        "high": price * 1.01,
                        "low": price * 0.99,
                        "amount": 20_000_000.0,
                    }
                )
        bars = pd.DataFrame(base_rows)
        proxy = build_equal_weight_market_proxy(bars, min_signal_date_amount=0)
        day2_return = proxy.loc[proxy["date"] == dates[1], "market_equal_weight_return"].iloc[0]
        self.assertAlmostEqual(day2_return, 0.0, places=12)

        changed_future = bars.copy()
        changed_future.loc[changed_future["date"] == dates[2], "adj_close"] *= 50.0
        changed_proxy = build_equal_weight_market_proxy(changed_future, min_signal_date_amount=0)
        changed_day2_return = changed_proxy.loc[
            changed_proxy["date"] == dates[1], "market_equal_weight_return"
        ].iloc[0]
        self.assertAlmostEqual(changed_day2_return, day2_return, places=12)

    def test_computes_all_round110_registered_factor_names(self) -> None:
        factors = compute_market_residual_risk_premia_factors(
            _synthetic_residual_bars(),
            min_signal_date_amount=10_000_000,
        )

        self.assertEqual(factors["factor_name"].nunique(), 10)
        self.assertIn("low_beta_120", set(factors["factor_name"]))
        self.assertIn("downside_beta_low_120", set(factors["factor_name"]))
        self.assertIn("residual_reversal_5_60", set(factors["factor_name"]))
        self.assertIn("positive_residual_skew_60", set(factors["factor_name"]))
        self.assertTrue((factors["amount"] >= 10_000_000).all())
        self.assertTrue((factors["adv20_amount"] >= 10_000_000).all())

    def test_builds_prescreen_without_reading_final_holdout_and_blocks_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            bars = _synthetic_residual_bars(include_holdout=True)
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

            result = build_market_residual_risk_premia_prescreen(
                bars_roots=[root],
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=10_000_000,
            )

        self.assertEqual(result["stage"], "market_residual_risk_premia_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 10)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["label_rows"], 0)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertEqual(
            result["promotion_policy"]["requires_next_gate"],
            "market_exposure_diagnostic_for_round111_leads",
        )
        self.assertEqual(set(result["summary"]["horizons"]), {5})


if __name__ == "__main__":
    unittest.main()

