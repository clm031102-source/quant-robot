import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.public_alpha101_capacity_safe_prescreen import (
    ROUND115_NEXT_DEDUP_DIRECTION,
    build_public_alpha101_capacity_safe_prescreen,
    compute_public_alpha101_capacity_safe_factors,
)
from quant_robot.storage.dataset_store import DatasetStore


def _synthetic_ohlcv_bars(days: int = 120, assets: int = 45, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=8))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        price = 8.0 + asset_idx * 0.05
        for day_idx, date in enumerate(dates):
            drift = (asset_idx % 6) * 0.0004
            wave = ((day_idx % 13) - 6) * 0.001
            open_price = max(1.0, price * (1.0 + wave * 0.3))
            close = max(1.0, open_price * (1.0 + drift + wave))
            high = max(open_price, close) * 1.012
            low = min(open_price, close) * 0.988
            volume = 800_000 + asset_idx * 15_000 + (day_idx % 7) * 5_000
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


class PublicAlpha101CapacitySafePrescreenTests(unittest.TestCase):
    def test_computes_all_round114_candidate_factor_names(self) -> None:
        factors = compute_public_alpha101_capacity_safe_factors(
            _synthetic_ohlcv_bars(),
            min_signal_date_amount=1_000_000,
        )

        names = set(factors["factor_name"])
        self.assertEqual(len(names), 10)
        self.assertIn("alpha101_intraday_close_position_reversal", names)
        self.assertIn("alpha101_price_volume_corr_reversal_20", names)
        self.assertIn("qlib_alpha158_return_std_position_blend_20", names)
        self.assertIn("alpha101_vwap_proxy_reversion_liquid_20", names)
        self.assertTrue((factors["amount"] >= 1_000_000).all())

    def test_builds_prescreen_from_bars_without_touching_final_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            bars = _synthetic_ohlcv_bars(include_holdout=True)
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

            result = build_public_alpha101_capacity_safe_prescreen(
                bars_roots=[root],
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
            )

        self.assertEqual(result["stage"], "public_alpha101_capacity_safe_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 10)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["label_rows"], 0)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertIn(
            result["summary"]["next_direction"],
            {ROUND115_NEXT_DEDUP_DIRECTION, "round116_family_rotation_after_public_alpha101_prescreen_failure"},
        )


if __name__ == "__main__":
    unittest.main()
