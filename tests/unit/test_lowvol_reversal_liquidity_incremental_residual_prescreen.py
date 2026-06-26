import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.lowvol_reversal_liquidity_incremental_residual_prescreen import (
    NEXT_REVIEW_DIRECTION,
    build_lowvol_reversal_liquidity_incremental_residual_prescreen,
    candidate_reference_correlations,
    compute_lowvol_reversal_liquidity_incremental_residual_factors,
)
from quant_robot.storage.dataset_store import DatasetStore


def _synthetic_ohlcv_bars(days: int = 190, assets: int = 48) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        price = 9.0 + asset_idx * 0.04
        for day_idx, date in enumerate(dates):
            cycle = ((day_idx % 17) - 8) * 0.0008
            drift = (asset_idx % 7) * 0.00025
            open_price = max(1.0, price * (1.0 + cycle * 0.3))
            close = max(1.0, open_price * (1.0 + drift + cycle))
            high = max(open_price, close) * 1.012
            low = min(open_price, close) * 0.988
            volume = 900_000 + asset_idx * 18_000 + (day_idx % 9) * 6_000
            amount = volume * close
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "adj_close": close,
                    "volume": volume,
                    "amount": amount,
                    "vwap": amount / volume,
                }
            )
            price = close
    return pd.DataFrame(rows)


class LowvolReversalLiquidityIncrementalResidualPrescreenTests(unittest.TestCase):
    def test_reference_correlations_filter_to_candidate_sample_dates(self) -> None:
        candidate_dates = pd.bdate_range("2025-02-03", periods=20)
        reference_dates = pd.bdate_range("2025-01-02", periods=60)
        candidate_rows = []
        reference_rows = []
        for signal_date in candidate_dates:
            for asset_idx in range(35):
                candidate_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": f"CN_XSHE_{asset_idx:06d}",
                        "market": "CN",
                        "factor_name": "candidate_a",
                        "factor_value": float(asset_idx),
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                    }
                )
        for signal_date in reference_dates:
            for asset_idx in range(35):
                reference_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": f"CN_XSHE_{asset_idx:06d}",
                        "market": "CN",
                        "factor_name": "reference_a",
                        "factor_value": float(asset_idx),
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                    }
                )

        rows = candidate_reference_correlations(
            pd.DataFrame(candidate_rows),
            pd.DataFrame(reference_rows),
            sample_every_n_dates=10,
            min_cross_section=20,
        )

        self.assertEqual(rows[0]["correlation_observations"], 2)
        self.assertEqual(rows[0]["redundancy_class"], "highly_redundant")

    def test_computes_all_round119_incremental_residual_candidates(self) -> None:
        factors = compute_lowvol_reversal_liquidity_incremental_residual_factors(
            _synthetic_ohlcv_bars(),
            min_signal_date_amount=1_000_000,
        )

        names = set(factors["factor_name"])
        self.assertEqual(len(names), 8)
        self.assertIn("qlib_blend_residual_vs_lowvol_cluster_5", names)
        self.assertIn("range_contraction_incremental_residual_20", names)
        self.assertIn("pv_lowvol_cluster_residual_spread_20", names)
        self.assertTrue((factors["amount"] >= 1_000_000).all())
        self.assertIn("beta_120", factors.columns)
        self.assertIn("market_corr_60", factors.columns)

    def test_builds_prescreen_and_keeps_portfolio_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            DatasetStore(root).write_frame(
                _synthetic_ohlcv_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = build_lowvol_reversal_liquidity_incremental_residual_prescreen(
                bars_roots=[root],
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
                sample_every_n_dates=5,
            )

        self.assertEqual(result["stage"], "lowvol_reversal_liquidity_incremental_residual_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertEqual(result["summary"]["next_direction"], NEXT_REVIEW_DIRECTION)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertGreaterEqual(len(result["reference_correlations"]), 8)
        self.assertGreaterEqual(len(result["exposure_correlations"]), 8)
        self.assertGreater(
            max(row["correlation_observations"] for row in result["reference_correlations"]),
            0,
        )
        self.assertIn(
            "range_contraction_incremental_residual_20",
            {row["candidate_factor_name"] for row in result["reference_correlations"] if row["correlation_observations"] > 0},
        )


if __name__ == "__main__":
    unittest.main()
