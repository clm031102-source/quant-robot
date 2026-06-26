import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.ops.capacity_safe_price_volume_prescreen import (
    build_capacity_safe_price_volume_prescreen,
    compute_capacity_safe_price_volume_factors,
    summarize_capacity_safe_price_volume_prescreen,
)


def _synthetic_bars(days: int = 90, assets: int = 40, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 10.0 + asset_idx * 0.03
        for day_idx, date in enumerate(dates):
            seasonal = ((day_idx % 17) - 8) * 0.001
            drift = (asset_idx % 7) * 0.0005
            price = max(1.0, price * (1.0 + seasonal + drift))
            high = price * 1.015
            low = price * 0.985
            amount = 20_000_000 + asset_idx * 100_000 + (day_idx % 5) * 50_000
            rows.append(
                {
                    "date": date,
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


class CapacitySafePriceVolumePrescreenTests(unittest.TestCase):
    def test_summarizes_ic_quantiles_turnover_and_blocks_direct_promotion(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=8)
        rows = []
        labels = []
        for date in dates:
            for asset_idx in range(40):
                asset_id = f"{asset_idx:06d}.SZ"
                signal = float(asset_idx)
                rows.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "synthetic_rank_signal",
                        "factor_value": signal,
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                    }
                )
                labels.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": signal / 10_000.0,
                        "entry_date": date + pd.Timedelta(days=1),
                        "exit_date": date + pd.Timedelta(days=6),
                    }
                )

        result = summarize_capacity_safe_price_volume_prescreen(
            pd.DataFrame(rows),
            pd.DataFrame(labels),
            min_cross_section=20,
            min_ic_observations=4,
        )

        self.assertEqual(result["summary"]["candidate_count"], 1)
        self.assertEqual(result["summary"]["test_count"], 1)
        self.assertEqual(result["summary"]["research_lead_count"], 1)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        row = result["results"][0]
        self.assertGreater(row["mean_spearman_ic"], 0.99)
        self.assertGreater(row["ic_t_stat"], 10.0)
        self.assertTrue(row["fdr_significant"])
        self.assertTrue(row["research_lead"])
        self.assertGreater(row["quantile_spread"], 0.0)
        self.assertLess(row["avg_top_quantile_turnover"], 0.05)

    def test_builds_long_cycle_prescreen_from_bars_without_reading_final_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            bars = _synthetic_bars(include_holdout=True)
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

            result = build_capacity_safe_price_volume_prescreen(
                bars_roots=[root],
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

        self.assertEqual(result["stage"], "capacity_safe_price_volume_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 10)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["label_rows"], 0)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertEqual(
            set(result["summary"]["horizons"]),
            {5},
        )

    def test_computes_all_pre_registered_factor_names(self) -> None:
        factors = compute_capacity_safe_price_volume_factors(_synthetic_bars(), min_signal_date_amount=10_000_000)

        self.assertEqual(factors["factor_name"].nunique(), 10)
        self.assertIn("pv_lowvol_reversal_blend_20", set(factors["factor_name"]))
        self.assertIn("bollinger_reversal_lowvol_liquid_20", set(factors["factor_name"]))
        self.assertIn("donchian_pullback_lowvol_liquid_20", set(factors["factor_name"]))
        self.assertTrue((factors["amount"] >= 10_000_000).all())

    def test_summarizer_streams_per_factor_instead_of_all_factor_merge(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=5)
        factor_rows = []
        labels = []
        for factor_name in ["signal_a", "signal_b"]:
            for date in dates:
                for asset_idx in range(35):
                    asset_id = f"{asset_idx:06d}.SZ"
                    factor_rows.append(
                        {
                            "date": date,
                            "asset_id": asset_id,
                            "market": "CN",
                            "factor_name": factor_name,
                            "factor_value": float(asset_idx),
                            "amount": 20_000_000.0,
                            "adv20_amount": 20_000_000.0,
                        }
                    )
        for date in dates:
            for asset_idx in range(35):
                asset_id = f"{asset_idx:06d}.SZ"
                labels.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": asset_idx / 10_000.0,
                        "entry_date": date + pd.Timedelta(days=1),
                        "exit_date": date + pd.Timedelta(days=6),
                    }
                )
        original_merge = pd.DataFrame.merge

        def guarded_merge(left, *args, **kwargs):
            if "factor_name" in left.columns and left["factor_name"].nunique() > 1:
                raise AssertionError("summarizer attempted an all-factor merge")
            return original_merge(left, *args, **kwargs)

        with patch.object(pd.DataFrame, "merge", guarded_merge):
            result = summarize_capacity_safe_price_volume_prescreen(
                pd.DataFrame(factor_rows),
                pd.DataFrame(labels),
                min_cross_section=20,
                min_ic_observations=4,
            )

        self.assertEqual(result["summary"]["test_count"], 2)
        self.assertEqual(result["summary"]["research_lead_count"], 2)


if __name__ == "__main__":
    unittest.main()
