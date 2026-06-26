import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.factors.daily_basic_public_anomaly_residual_ensemble import (
    DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES,
)
from quant_robot.ops.public_anomaly_residual_ensemble_prescreen import (
    NEXT_DIRECTION_WITHOUT_LEADS,
    STAGE,
    build_public_anomaly_residual_ensemble_factor_frame,
    summarize_public_anomaly_residual_ensemble_prescreen,
    write_public_anomaly_residual_ensemble_prescreen,
)
from tests.unit.test_daily_basic_public_anomaly_residual_ensemble_factors import (
    _bars as _daily_basic_public_bars,
    _daily_basic_inputs as _daily_basic_public_inputs,
)


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
            reference_rows.append(
                common
                | {
                    "factor_name": "independent_reference",
                    "factor_value": float((asset_idx * 13) % assets),
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0,
                }
            )
            for factor_name in DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES:
                if factor_name == "public_anomaly_residual_equal_weight_20":
                    factor_value = true_signal + exposure_value * 0.01
                elif factor_name == "public_anomaly_residual_agreement_20":
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
                        "family": "public_anomaly_residual_ensemble_risk_budget",
                    }
                )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows), pd.DataFrame(exposure_rows)


class PublicAnomalyResidualEnsemblePrescreenTests(unittest.TestCase):
    def test_residual_prescreen_evaluates_round228_candidates_without_promotion(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames()

        result = summarize_public_anomaly_residual_ensemble_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_icir=0.0,
            min_industry_neutral_icir=0.0,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["source_context"]["source_audit"], "docs/research/cn_stock_round228_public_anomaly_residual_ensemble_preregistration_2026-06-24.md")
        self.assertEqual(result["source_context"]["candidate_family"], "public_anomaly_residual_ensemble_risk_budget")
        self.assertEqual(result["summary"]["candidate_count"], 4)
        self.assertEqual(result["summary"]["test_count"], 4)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["industry_neutral_rows"], 0)
        self.assertGreater(result["summary"]["residual_rows"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_grid_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])

    def test_high_residual_threshold_blocks_all_candidates_and_rotates_family(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)

        result = summarize_public_anomaly_residual_ensemble_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_mean_ic=1.01,
            min_residual_icir=99.0,
        )

        self.assertEqual(result["summary"]["residual_research_lead_count"], 0)
        self.assertEqual(result["summary"]["next_direction"], NEXT_DIRECTION_WITHOUT_LEADS)
        self.assertTrue(all("residual_mean_ic_below_threshold" in row["blockers"] for row in result["results"]))

    def test_factor_frame_builder_computes_public_anomaly_source_and_capacity_fields(self) -> None:
        bars = _daily_basic_public_bars(day_count=80)
        daily_basic = _daily_basic_public_inputs(day_count=80)
        exposure = _exposure_from_bars(bars)

        factors = build_public_anomaly_residual_ensemble_factor_frame(
            bars,
            daily_basic,
            exposure,
            candidate_factor_names=("public_anomaly_residual_equal_weight_20",),
            min_signal_date_amount=1_000,
        )

        self.assertFalse(factors.empty)
        self.assertEqual(set(factors["factor_name"]), {"public_anomaly_residual_equal_weight_20"})
        self.assertEqual(set(factors["family"]), {"public_anomaly_residual_ensemble_risk_budget"})
        self.assertIn("amount", factors.columns)
        self.assertIn("adv20_amount", factors.columns)
        self.assertNotIn("CN_TEST_ILLIQUID", set(factors.dropna(subset=["factor_value"])["asset_id"]))

    def test_writer_outputs_structured_round229_audit_files(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_frames(assets=45)
        result = summarize_public_anomaly_residual_ensemble_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_icir=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_public_anomaly_residual_ensemble_prescreen(output, result)
            self.assertTrue((output / "public_anomaly_residual_ensemble_prescreen.json").exists())
            self.assertTrue((output / "public_anomaly_residual_ensemble_prescreen.md").exists())
            self.assertTrue((output / "public_anomaly_residual_ensemble_prescreen_results.csv").exists())
            self.assertTrue((output / "public_anomaly_residual_ensemble_reference_correlations.csv").exists())
            self.assertTrue((output / "public_anomaly_residual_ensemble_residual_ic_observations.csv").exists())


def _exposure_from_bars(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame["asset_id"] = frame["asset_id"].astype(str)
    frame["market"] = frame["market"].astype(str)
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    rows = []
    for asset_id, group in frame.sort_values(["asset_id", "date"]).groupby("asset_id", sort=False):
        group = group.copy()
        group["adv20_amount"] = group["amount"].rolling(20, min_periods=5).mean()
        group["industry"] = "bank" if "VALUE" in str(asset_id) else "tech"
        group["log_adv20_amount"] = group["adv20_amount"].where(group["adv20_amount"] > 0).apply("log")
        group["log_amount"] = group["amount"].where(group["amount"] > 0).apply("log")
        group["realized_vol_20"] = group["adj_close"].pct_change().rolling(20, min_periods=5).std(ddof=0)
        group["amount_trend_20_60"] = 0.0
        group["return_20"] = group["adj_close"].pct_change(20)
        group["return_1d"] = group["adj_close"].pct_change()
        rows.append(group)
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
