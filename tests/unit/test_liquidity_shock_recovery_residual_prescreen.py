import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.factors.liquidity_shock_recovery import LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES
from quant_robot.ops.liquidity_shock_recovery_residual_prescreen import (
    FAMILY,
    NEXT_DIRECTION_WITHOUT_LEADS,
    STAGE,
    build_liquidity_shock_recovery_factor_frame,
    summarize_liquidity_shock_recovery_residual_prescreen,
    write_liquidity_shock_recovery_residual_prescreen,
)
from tests.unit.test_liquidity_shock_recovery_factors import _bars


class LiquidityShockRecoveryResidualPrescreenTests(unittest.TestCase):
    def test_residual_prescreen_evaluates_round230_candidates_without_promotion(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames()

        result = summarize_liquidity_shock_recovery_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_icir=0.0,
            min_industry_neutral_icir=0.0,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["source_context"]["source_audit"], "docs/research/cn_stock_round230_liquidity_shock_recovery_preregistration_2026-06-24.md")
        self.assertEqual(result["source_context"]["candidate_family"], FAMILY)
        self.assertEqual(result["summary"]["candidate_count"], 5)
        self.assertEqual(result["summary"]["test_count"], 5)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["industry_neutral_rows"], 0)
        self.assertGreater(result["summary"]["residual_rows"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_grid_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])

    def test_high_residual_threshold_blocks_all_candidates_and_rotates_family(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)

        result = summarize_liquidity_shock_recovery_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_mean_ic=1.01,
            min_residual_icir=99.0,
        )

        self.assertEqual(result["summary"]["residual_research_lead_count"], 0)
        self.assertEqual(result["summary"]["next_direction"], NEXT_DIRECTION_WITHOUT_LEADS)
        self.assertTrue(all("residual_mean_ic_below_threshold" in row["blockers"] for row in result["results"]))

    def test_factor_frame_builder_computes_liquidity_source_and_capacity_fields(self) -> None:
        bars = _bars()
        exposure = _exposure_from_bars(bars)

        factors = build_liquidity_shock_recovery_factor_frame(
            bars,
            exposure,
            candidate_factor_names=("amihud_shock_reversal_recovery_20_5",),
            min_signal_date_amount=1_000,
        )

        self.assertFalse(factors.empty)
        self.assertEqual(set(factors["factor_name"]), {"amihud_shock_reversal_recovery_20_5"})
        self.assertEqual(set(factors["family"]), {FAMILY})
        self.assertIn("amount", factors.columns)
        self.assertIn("adv20_amount", factors.columns)

    def test_writer_outputs_structured_round230_audit_files(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)
        result = summarize_liquidity_shock_recovery_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_icir=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_liquidity_shock_recovery_residual_prescreen(output, result)
            self.assertTrue((output / "liquidity_shock_recovery_residual_prescreen.json").exists())
            self.assertTrue((output / "liquidity_shock_recovery_residual_prescreen.md").exists())
            self.assertTrue((output / "liquidity_shock_recovery_residual_prescreen_results.csv").exists())
            self.assertTrue((output / "liquidity_shock_recovery_residual_ic_observations.csv").exists())


def _synthetic_frames(*, assets: int = 54) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = list(pd.bdate_range("2018-01-02", periods=8)) + list(pd.bdate_range("2019-01-02", periods=8))
    factor_rows = []
    label_rows = []
    reference_rows = []
    exposure_rows = []
    for signal_date in dates:
        for asset_idx in range(assets):
            industry = "bank" if asset_idx < assets // 3 else "tech" if asset_idx < 2 * assets // 3 else "industrial"
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
            for factor_name in LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES:
                if factor_name == "amihud_shock_reversal_recovery_20_5":
                    factor_value = true_signal + exposure_value * 0.01
                elif factor_name == "volume_shock_absorption_reversal_20_5":
                    factor_value = true_signal * 0.7 + float((asset_idx * 5) % assets) * 0.02
                else:
                    factor_value = float((asset_idx * (len(factor_name) % 11 + 3)) % assets)
                factor_rows.append(
                    common
                    | {
                        "factor_name": factor_name,
                        "factor_value": factor_value,
                        "amount": 50_000_000.0,
                        "adv20_amount": 50_000_000.0,
                        "family": FAMILY,
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows), pd.DataFrame(exposure_rows)


def _exposure_from_bars(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    rows = []
    for asset_id, group in frame.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        item = group.copy()
        item["adv20_amount"] = item["amount"].rolling(20, min_periods=5).mean()
        item["industry"] = "bank" if str(asset_id).endswith("0") else "tech"
        item["log_adv20_amount"] = item["adv20_amount"].where(item["adv20_amount"] > 0).apply("log")
        item["log_amount"] = item["amount"].where(item["amount"] > 0).apply("log")
        item["realized_vol_20"] = item["adj_close"].pct_change().rolling(20, min_periods=5).std(ddof=0)
        item["amount_trend_20_60"] = 0.0
        item["return_20"] = item["adj_close"].pct_change(20)
        item["return_1d"] = item["adj_close"].pct_change()
        rows.append(item)
    return pd.concat(rows, ignore_index=True)[
        [
            "date",
            "asset_id",
            "market",
            "amount",
            "adv20_amount",
            "industry",
            "log_adv20_amount",
            "log_amount",
            "realized_vol_20",
            "amount_trend_20_60",
            "return_20",
            "return_1d",
        ]
    ]


if __name__ == "__main__":
    unittest.main()
