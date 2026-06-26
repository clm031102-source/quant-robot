import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.factors.industry_leader_lag import INDUSTRY_LEADER_LAG_FACTOR_NAMES
from quant_robot.ops.industry_leader_lag_residual_prescreen import (
    NEXT_DIRECTION_WITHOUT_LEADS,
    STAGE,
    build_industry_leader_lag_sharded_residual_prescreen,
    summarize_industry_leader_lag_residual_prescreen,
    write_industry_leader_lag_residual_prescreen,
)
from quant_robot.storage.dataset_store import DatasetStore


def _synthetic_frames(*, assets: int = 54) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = list(pd.bdate_range("2018-01-02", periods=8)) + list(pd.bdate_range("2019-01-02", periods=8))
    factor_rows = []
    label_rows = []
    reference_rows = []
    exposure_rows = []
    for signal_date in dates:
        for asset_idx in range(assets):
            industry = "tech" if asset_idx < assets // 3 else "bank" if asset_idx < 2 * assets // 3 else "industrial"
            true_signal = float(asset_idx % (assets // 3))
            exposure_value = float((asset_idx * 17) % assets)
            common = {
                "date": signal_date,
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "market": "CN",
            }
            label_rows.append(common | {"horizon": 5, "forward_return": true_signal / 1000.0})
            exposure_rows.append(
                common
                | {
                    "industry": industry,
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0 + exposure_value * 10_000.0,
                    "log_adv20_amount": exposure_value,
                    "log_amount": exposure_value * 0.8,
                    "realized_vol_20": exposure_value * 0.3,
                    "amount_trend_20_60": exposure_value * 0.01,
                    "return_20": float((asset_idx * 7) % assets),
                    "return_1d": 0.0,
                }
            )
            reference_rows.append(
                common
                | {
                    "factor_name": "donchian_position_20",
                    "factor_value": exposure_value,
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0,
                }
            )
            for factor_name in INDUSTRY_LEADER_LAG_FACTOR_NAMES:
                factor_value = true_signal + exposure_value * 0.01 if factor_name.endswith("composite_20") else true_signal
                factor_rows.append(
                    common
                    | {
                        "factor_name": factor_name,
                        "factor_value": factor_value,
                        "amount": 50_000_000.0,
                        "adv20_amount": 50_000_000.0,
                        "family": "industry_leader_lag_residual_diffusion",
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows), pd.DataFrame(exposure_rows)


def _synthetic_stock_basic(assets_per_industry: int = 6) -> pd.DataFrame:
    rows = []
    for industry in ("tech", "bank", "industrial"):
        for index in range(assets_per_industry):
            rows.append({"asset_id": f"CN_{industry.upper()}_{index:03d}", "industry": industry})
    return pd.DataFrame(rows)


def _synthetic_sharded_bars(assets_per_industry: int = 6) -> pd.DataFrame:
    dates = pd.bdate_range("2023-10-02", "2025-03-31")
    rows = []
    for industry_idx, industry in enumerate(("tech", "bank", "industrial")):
        for asset_idx in range(assets_per_industry):
            asset_id = f"CN_{industry.upper()}_{asset_idx:03d}"
            price = 8.0 + industry_idx * 2.0 + asset_idx * 0.25
            leader = asset_idx == 0
            for day_idx, signal_date in enumerate(dates):
                drift = 0.0015 * (industry_idx + 1) if leader else 0.0002 * (asset_idx + 1)
                wave = ((day_idx + asset_idx) % 11 - 5) * 0.001
                price = max(1.0, price * (1.0 + drift + wave))
                amount = (40_000_000.0 if leader else 12_000_000.0 + asset_idx * 1_000_000.0) * (
                    1.0 + day_idx * 0.0005
                )
                rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "symbol": asset_id.replace("CN_", "") + ".SZ",
                        "market": "CN",
                        "open": price * 0.999,
                        "high": price * 1.01,
                        "low": price * 0.99,
                        "close": price,
                        "adj_close": price,
                        "volume": amount / price,
                        "amount": amount,
                        "vwap": price,
                    }
                )
    return pd.DataFrame(rows)


class IndustryLeaderLagResidualPrescreenTests(unittest.TestCase):
    def test_residual_prescreen_evaluates_registered_round220_candidates_without_promotion(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames()

        result = summarize_industry_leader_lag_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=INDUSTRY_LEADER_LAG_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_icir=0.0,
            min_industry_neutral_icir=0.0,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["summary"]["candidate_count"], 6)
        self.assertEqual(result["summary"]["test_count"], 6)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["industry_neutral_rows"], 0)
        self.assertGreater(result["summary"]["residual_rows"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_grid_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])
        self.assertEqual(result["source_context"]["candidate_family"], "industry_leader_lag_residual_diffusion")
        for row in result["results"]:
            self.assertIn("residual_mean_spearman_ic", row)
            self.assertFalse(row["promotion_allowed"])

    def test_high_residual_threshold_blocks_all_candidates_and_rotates_family(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)

        result = summarize_industry_leader_lag_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=INDUSTRY_LEADER_LAG_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_mean_ic=1.01,
            min_residual_icir=99.0,
        )

        self.assertEqual(result["summary"]["residual_research_lead_count"], 0)
        self.assertEqual(result["summary"]["next_direction"], NEXT_DIRECTION_WITHOUT_LEADS)
        self.assertTrue(all("residual_mean_ic_below_threshold" in row["blockers"] for row in result["results"]))

    def test_writer_outputs_structured_round220_audit_files(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)
        result = summarize_industry_leader_lag_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=INDUSTRY_LEADER_LAG_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_icir=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_industry_leader_lag_residual_prescreen(output, result)
            self.assertTrue((output / "industry_leader_lag_residual_prescreen.json").exists())
            self.assertTrue((output / "industry_leader_lag_residual_prescreen.md").exists())
            self.assertTrue((output / "industry_leader_lag_residual_prescreen_results.csv").exists())
            self.assertTrue((output / "industry_leader_lag_reference_correlations.csv").exists())
            self.assertTrue((output / "industry_leader_lag_residual_ic_observations.csv").exists())

    def test_sharded_prescreen_uses_padding_but_keeps_signal_dates_inside_analysis_window(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = _synthetic_sharded_bars()
            store = DatasetStore(root)
            for year in sorted(bars["date"].dt.year.unique()):
                store.write_frame(
                    bars[bars["date"].dt.year == year],
                    "processed/bars",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )

            result = build_industry_leader_lag_sharded_residual_prescreen(
                bars_roots=[root],
                stock_basic=_synthetic_stock_basic(),
                candidate_factor_names=("industry_leader_laggard_gap_reversion_5_20",),
                analysis_start_date="2024-01-02",
                analysis_end_date="2025-02-28",
                lookback_calendar_days=90,
                forward_calendar_days=30,
                horizons=(5,),
                min_signal_date_amount=1_000,
                min_cross_section=9,
                min_ic_observations=2,
                min_industries=2,
                min_assets_per_industry=2,
                min_industry_neutral_icir=-99.0,
                min_residual_icir=-99.0,
            )

        self.assertEqual(result["stage"], STAGE)
        self.assertTrue(result["source_context"]["sharded_full_cycle_prescreen"])
        self.assertTrue(result["sharding_policy"]["enabled"])
        self.assertTrue(result["sharding_policy"]["streaming_summary"])
        self.assertEqual(result["sharding_policy"]["shard_count"], 2)
        self.assertLess(result["sharding_policy"]["shards"][0]["load_start_date"], "2024-01-02")
        self.assertGreaterEqual(result["sharding_policy"]["shards"][1]["load_end_date"], "2025-03-01")
        self.assertEqual(result["summary"]["candidate_count"], 1)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["label_rows"], 0)
        observed_dates = [
            pd.Timestamp(row["date"])
            for row in result["raw_ic_observations"]
            + result["industry_neutral_ic_observations"]
            + result["residual_ic_observations"]
        ]
        self.assertTrue(observed_dates)
        self.assertGreaterEqual(min(observed_dates), pd.Timestamp("2024-01-02"))
        self.assertLessEqual(max(observed_dates), pd.Timestamp("2025-02-28"))


if __name__ == "__main__":
    unittest.main()
