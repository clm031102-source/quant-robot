import unittest

import pandas as pd

from quant_robot.factors.industry_breadth_regime import (
    INDUSTRY_BREADTH_REGIME_FACTOR_NAMES,
    compute_industry_breadth_regime_factors,
)


class IndustryBreadthRegimeFactorTests(unittest.TestCase):
    def test_computes_industry_breadth_regime_candidates(self) -> None:
        dates = list(pd.bdate_range("2023-01-02", periods=90))
        assets = [f"CN_XSHG_{idx:06d}" for idx in range(12)]
        rows = []
        meta_rows = []
        for asset_idx, asset in enumerate(assets):
            industry = "equipment" if asset_idx < 6 else "software"
            meta_rows.append({"asset_id": asset, "industry": industry})
            for date_idx, signal_date in enumerate(dates):
                trend = 1.0 + 0.002 * date_idx
                industry_wave = 1.0 + (0.0015 * date_idx if industry == "equipment" else -0.0005 * date_idx)
                idio = 1.0 + 0.0003 * ((asset_idx * 7 + date_idx) % 11)
                rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset,
                        "market": "CN",
                        "adj_close": 10.0 * trend * industry_wave * idio,
                        "amount": 50_000_000.0 + asset_idx * 1_000_000.0 + date_idx * 10_000.0,
                    }
                )
        bars = pd.DataFrame(rows)
        stock_basic = pd.DataFrame(meta_rows)

        result = compute_industry_breadth_regime_factors(
            bars,
            stock_basic=stock_basic,
            min_industry_assets=3,
        )

        self.assertEqual(set(result["factor_name"].unique()), set(INDUSTRY_BREADTH_REGIME_FACTOR_NAMES))
        self.assertEqual(result["market"].unique().tolist(), ["CN"])
        self.assertGreater(result["factor_value"].notna().sum(), 0)
        self.assertIn("industry_breadth_repair_laggard_rebound_20", set(result["factor_name"]))

    def test_unknown_factor_name_is_rejected(self) -> None:
        bars = pd.DataFrame(
            {
                "date": [pd.Timestamp("2024-01-02")],
                "asset_id": ["CN_XSHG_600000"],
                "market": ["CN"],
                "adj_close": [10.0],
                "amount": [1.0],
            }
        )
        with self.assertRaises(ValueError):
            compute_industry_breadth_regime_factors(bars, factor_names=("unknown_factor",))


if __name__ == "__main__":
    unittest.main()

