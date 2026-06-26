import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.tradeability_structure_quality_prescreen import (
    build_tradeability_structure_quality_prescreen,
    compute_tradeability_structure_quality_factors,
)
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_tradeability_structure_quality_prescreen import (
    run_tradeability_structure_quality_prescreen_cli,
)


ROUND209_SPECS = [
    {"factor_name": "tradeability_persistence_quality_20"},
    {"factor_name": "entry_exit_friction_avoidance_20"},
    {"factor_name": "limit_lock_pressure_avoidance_20"},
    {"factor_name": "metadata_survivorship_quality_120"},
]


def _synthetic_bars(days: int = 90, assets: int = 36, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2024-09-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        price = 8.0 + asset_idx * 0.05
        for day_idx, signal_date in enumerate(dates):
            price = max(1.0, price * (1.0 + (asset_idx % 5) * 0.0002 + ((day_idx % 11) - 5) * 0.0003))
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": f"CN_XSHE_{asset_idx:06d}",
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 15_000_000 + asset_idx * 120_000 + (day_idx % 7) * 90_000,
                }
            )
    return pd.DataFrame(rows)


def _synthetic_masks(bars: pd.DataFrame) -> pd.DataFrame:
    rows = []
    ordered = bars.sort_values(["asset_id", "date"]).reset_index(drop=True)
    for asset_id, group in ordered.groupby("asset_id", sort=False):
        asset_num = int(str(asset_id).rsplit("_", 1)[-1])
        for day_idx, row in enumerate(group.itertuples(index=False)):
            limit_up = (asset_num + day_idx) % 29 == 0
            limit_down = (asset_num + day_idx) % 37 == 0
            suspended = asset_num % 17 == 0 and day_idx % 13 == 0
            st_flag = asset_num % 19 == 0
            new_listing = day_idx < 8 and asset_num % 7 == 0
            board_blocked = asset_num % 23 == 0
            delisted = day_idx > len(group) - 4 and asset_num % 31 == 0
            can_buy = not (limit_up or suspended or st_flag or new_listing or board_blocked or delisted)
            can_sell = not (limit_down or suspended or st_flag or new_listing or board_blocked or delisted)
            rows.append(
                {
                    "date": row.date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "entry_tradeable": can_buy,
                    "exit_tradeable": can_sell,
                    "fully_tradeable": can_buy and can_sell,
                    "can_buy": can_buy,
                    "can_sell": can_sell,
                    "suspended_official": suspended,
                    "limit_up_official": limit_up,
                    "limit_down_official": limit_down,
                    "st_flag_official": st_flag,
                    "new_listing_flag": new_listing,
                    "delisted_or_inactive_flag": delisted,
                    "board_permission_blocked": board_blocked,
                }
            )
    return pd.DataFrame(rows)


class TradeabilityStructureQualityPrescreenTests(unittest.TestCase):
    def test_computes_round209_factor_names_from_current_and_lagged_masks(self) -> None:
        bars = _synthetic_bars(days=70, assets=36)
        masks = _synthetic_masks(bars)

        full = compute_tradeability_structure_quality_factors(
            bars,
            masks,
            candidate_specs=ROUND209_SPECS,
            min_signal_date_amount=10_000_000,
        )

        self.assertEqual(set(full["factor_name"]), {spec["factor_name"] for spec in ROUND209_SPECS})
        self.assertGreater(len(full), 0)
        self.assertTrue((full["amount"] >= 10_000_000).all())
        self.assertTrue((full["adv20_amount"] >= 10_000_000).all())
        self.assertIn("entry_blocked_rate_20", full.columns)
        self.assertIn("official_blocked_rate_20", full.columns)

        sample_date = pd.Timestamp(full["date"].sort_values().unique()[20])
        truncated = compute_tradeability_structure_quality_factors(
            bars[bars["date"] <= sample_date],
            masks[masks["date"] <= sample_date],
            candidate_specs=ROUND209_SPECS,
            min_signal_date_amount=10_000_000,
        )
        full_sample = full[
            (full["date"] == sample_date)
            & (full["asset_id"] == "CN_XSHE_000005")
            & (full["factor_name"] == "tradeability_persistence_quality_20")
        ]["factor_value"].iloc[0]
        truncated_sample = truncated[
            (truncated["date"] == sample_date)
            & (truncated["asset_id"] == "CN_XSHE_000005")
            & (truncated["factor_name"] == "tradeability_persistence_quality_20")
        ]["factor_value"].iloc[0]
        self.assertAlmostEqual(float(full_sample), float(truncated_sample), places=12)

    def test_builds_prescreen_without_holdout_or_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_root = root / "bars"
            mask_root = root / "masks"
            plan_path = root / "round209_plan.json"
            bars = _synthetic_bars(include_holdout=True)
            masks = _synthetic_masks(bars)
            store = DatasetStore(bars_root)
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
            mask_store = DatasetStore(mask_root)
            mask_store.write_frame(
                masks[pd.to_datetime(masks["date"]).dt.year < 2026],
                "processed/tradeability_masks",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            plan_path.write_text(json.dumps({"candidates": ROUND209_SPECS}), encoding="utf-8")

            result = build_tradeability_structure_quality_prescreen(
                bars_roots=[bars_root],
                tradeability_mask_root=mask_root,
                candidate_plan_json=plan_path,
                analysis_start_date="2024-09-02",
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=10_000_000,
            )

        self.assertEqual(result["stage"], "tradeability_structure_quality_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 4)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["label_rows"], 0)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertTrue(result["tradeability_mask_policy"]["mask_cache_required"])

    def test_cli_writes_structured_round209_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_root = root / "bars"
            mask_root = root / "masks"
            output_dir = root / "out"
            plan_path = root / "round209_plan.json"
            bars = _synthetic_bars()
            masks = _synthetic_masks(bars)
            DatasetStore(bars_root).write_frame(
                bars,
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(mask_root).write_frame(
                masks,
                "processed/tradeability_masks",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            plan_path.write_text(json.dumps({"candidates": ROUND209_SPECS}), encoding="utf-8")

            result = run_tradeability_structure_quality_prescreen_cli(
                bars_roots=[bars_root],
                tradeability_mask_root=mask_root,
                candidate_plan_json=plan_path,
                output_dir=output_dir,
                analysis_start_date="2024-09-02",
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=10_000_000,
            )

            self.assertEqual(result["stage"], "tradeability_structure_quality_prescreen")
            self.assertTrue((output_dir / "tradeability_structure_quality_prescreen.json").exists())
            self.assertTrue((output_dir / "tradeability_structure_quality_prescreen.md").exists())
            self.assertTrue((output_dir / "tradeability_structure_quality_prescreen_results.csv").exists())


if __name__ == "__main__":
    unittest.main()
