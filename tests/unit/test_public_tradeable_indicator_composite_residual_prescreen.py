import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.public_tradeable_indicator_composite_preregistration import (
    default_public_tradeable_indicator_composite_candidate_specs,
)
from quant_robot.ops.public_tradeable_indicator_composite_residual_prescreen import (
    NEXT_DIRECTION_WITHOUT_LEADS,
    STAGE,
    load_public_tradeable_indicator_composite_bars,
    summarize_public_tradeable_indicator_composite_residual_prescreen,
    write_public_tradeable_indicator_composite_residual_prescreen,
)


ROUND264_CANDIDATE_NAMES = tuple(
    spec.factor_name for spec in default_public_tradeable_indicator_composite_candidate_specs()
)


def _synthetic_round265_frames(
    *,
    assets: int = 60,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = list(pd.bdate_range("2015-01-05", periods=8)) + list(pd.bdate_range("2018-01-03", periods=8))
    factor_rows = []
    label_rows = []
    reference_rows = []
    exposure_rows = []
    for signal_date in dates:
        for asset_idx in range(assets):
            industry = "bank" if asset_idx < assets // 3 else "tech" if asset_idx < 2 * assets // 3 else "industrial"
            within_industry_rank = float(asset_idx % (assets // 3))
            exposure_value = float((asset_idx * 11) % assets)
            common = {
                "date": signal_date,
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "market": "CN",
            }
            label_rows.append(common | {"horizon": 5, "forward_return": within_industry_rank / 1000.0})
            exposure_rows.append(
                common
                | {
                    "industry": industry,
                    "amount": 60_000_000.0,
                    "adv20_amount": 65_000_000.0 + exposure_value * 10_000.0,
                    "log_adv20_amount": exposure_value * 0.05,
                    "log_amount": exposure_value * 0.04,
                    "realized_vol_20": exposure_value * 0.02,
                    "amount_trend_20_60": exposure_value * 0.001,
                    "return_20": float((asset_idx * 7) % assets) / 100.0,
                    "return_1d": 0.001,
                }
            )
            reference_rows.append(
                common
                | {
                    "factor_name": "donchian_position_20",
                    "factor_value": float((asset_idx * 13) % assets),
                    "amount": 60_000_000.0,
                    "adv20_amount": 60_000_000.0,
                }
            )
            reference_rows.append(
                common
                | {
                    "factor_name": "bollinger_reversal_20",
                    "factor_value": float((asset_idx * 17) % assets),
                    "amount": 60_000_000.0,
                    "adv20_amount": 60_000_000.0,
                }
            )
            for name in ROUND264_CANDIDATE_NAMES:
                if name == "mfi_cmf_exhaustion_reversal_liquid_14_20":
                    factor_value = within_industry_rank + exposure_value * 0.01
                elif name == "supertrend_pullback_absorption_quality_10_3_20":
                    factor_value = within_industry_rank * 0.8 + float((asset_idx * 5) % assets) * 0.02
                else:
                    factor_value = float((asset_idx * (len(name) % 13 + 3)) % assets)
                factor_rows.append(
                    common
                    | {
                        "factor_name": name,
                        "factor_value": factor_value,
                        "amount": 60_000_000.0,
                        "adv20_amount": 60_000_000.0,
                        "family": "public_tradeable_indicator_composite",
                    }
                )
    return (
        pd.DataFrame(factor_rows),
        pd.DataFrame(label_rows),
        pd.DataFrame(reference_rows),
        pd.DataFrame(exposure_rows),
    )


class PublicTradeableIndicatorCompositeResidualPrescreenTests(unittest.TestCase):
    def test_round265_loader_reads_only_bars_tree_not_other_cn_processed_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_dir = root / "processed" / "bars" / "frequency=1d" / "market=CN" / "year=2015"
            moneyflow_dir = root / "processed" / "moneyflow_inputs" / "frequency=1d" / "market=CN" / "year=2015"
            bars_dir.mkdir(parents=True)
            moneyflow_dir.mkdir(parents=True)
            pd.DataFrame(
                {
                    "date": ["2015-01-05"],
                    "asset_id": ["CN_XSHE_000001"],
                    "market": ["CN"],
                    "open": [10.0],
                    "high": [10.5],
                    "low": [9.5],
                    "close": [10.2],
                    "adj_close": [10.2],
                    "amount": [60_000_000.0],
                }
            ).to_parquet(bars_dir / "part-00000.parquet")
            pd.DataFrame(
                {
                    "date": ["2015-01-05"],
                    "asset_id": ["CN_XSHE_BAD"],
                    "market": ["CN"],
                    "net_mf_amount": [999.0],
                }
            ).to_parquet(moneyflow_dir / "part-00000.parquet")

            bars = load_public_tradeable_indicator_composite_bars(
                [root],
                analysis_start_date="2015-01-01",
                analysis_end_date="2015-12-31",
                include_final_holdout=False,
            )

            self.assertEqual(bars["asset_id"].tolist(), ["CN_XSHE_000001"])
            self.assertIn("high", bars.columns)
            self.assertNotIn("net_mf_amount", bars.columns)

    def test_residual_prescreen_freezes_round264_candidates_without_portfolio_or_promotion(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_round265_frames()

        result = summarize_public_tradeable_indicator_composite_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=ROUND264_CANDIDATE_NAMES,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_industry_neutral_icir=0.0,
            min_residual_icir=0.0,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["source_context"]["source_preregistration_round"], 264)
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["test_count"], 8)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["industry_neutral_rows"], 0)
        self.assertGreater(result["summary"]["residual_rows"], 0)
        self.assertEqual(result["summary"]["portfolio_grid_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])

        self.assertEqual(len(result["results"]), 8)
        for row in result["results"]:
            self.assertIn("raw_mean_spearman_ic", row)
            self.assertIn("industry_neutral_mean_spearman_ic", row)
            self.assertIn("residual_mean_spearman_ic", row)
            self.assertIn("quantile_spread", row)
            self.assertIn("quantile_monotonicity", row)
            self.assertIn("avg_top_quantile_turnover", row)
            self.assertIn("twenty_fifteen_mean_spearman_ic", row)
            self.assertIn("twenty_fifteen_ic_observations", row)
            self.assertIn("reference_highly_redundant_count", row)
            self.assertFalse(row["promotion_allowed"])
            self.assertFalse(row["portfolio_grid_allowed"])

    def test_high_residual_threshold_blocks_all_candidates_and_rotates_family(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_round265_frames(assets=45)

        result = summarize_public_tradeable_indicator_composite_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=ROUND264_CANDIDATE_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_mean_ic=1.01,
            min_residual_icir=99.0,
        )

        self.assertEqual(result["summary"]["residual_research_lead_count"], 0)
        self.assertEqual(result["summary"]["next_direction"], NEXT_DIRECTION_WITHOUT_LEADS)
        self.assertTrue(result["family_rotation_policy"]["rotate_if_zero_leads"])
        self.assertTrue(all("residual_mean_ic_below_threshold" in row["blockers"] for row in result["results"]))

    def test_writer_outputs_round265_residual_prescreen_artifacts(self) -> None:
        factor_frame, labels, reference_frame, exposure_frame = _synthetic_round265_frames(assets=45)
        result = summarize_public_tradeable_indicator_composite_residual_prescreen(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            candidate_factor_names=ROUND264_CANDIDATE_NAMES,
            horizons=(5,),
            min_cross_section=15,
            min_ic_observations=4,
            min_residual_icir=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_public_tradeable_indicator_composite_residual_prescreen(output, result)
            self.assertTrue((output / "public_tradeable_indicator_composite_residual_prescreen.json").exists())
            self.assertTrue((output / "public_tradeable_indicator_composite_residual_prescreen.md").exists())
            self.assertTrue((output / "public_tradeable_indicator_composite_residual_prescreen_results.csv").exists())
            self.assertTrue((output / "public_tradeable_indicator_composite_reference_correlations.csv").exists())
            self.assertTrue((output / "public_tradeable_indicator_composite_residual_ic_observations.csv").exists())


if __name__ == "__main__":
    unittest.main()
