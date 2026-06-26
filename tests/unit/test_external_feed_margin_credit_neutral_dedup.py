import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.external_feed_margin_credit_neutral_dedup import (
    _gate,
    build_external_feed_margin_credit_neutral_dedup_from_frames,
    write_external_feed_margin_credit_neutral_dedup,
)
from tests.unit.test_external_feed_margin_credit_prescreen import _synthetic_margin_detail
from tests.unit.test_external_feed_northbound_prescreen import _synthetic_bars


class ExternalFeedMarginCreditNeutralDedupTests(unittest.TestCase):
    def test_round193_audits_reference_redundancy_residual_ic_and_blocks_promotion(self) -> None:
        bars = _synthetic_bars(days=58, assets=12, start="2024-01-02")
        margin = _synthetic_margin_detail(bars, raw_dates=pd.bdate_range("2024-01-02", periods=52))

        result = build_external_feed_margin_credit_neutral_dedup_from_frames(
            bars=bars,
            margin_detail=margin,
            prescreen_report=_round192_prescreen_report(),
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-12-31",
            include_final_holdout=False,
            horizon=1,
            execution_lag=0,
            lookback=5,
            sample_every_n_dates=2,
            min_cross_section=6,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
        )

        self.assertEqual(result["stage"], "external_feed_margin_credit_neutral_dedup")
        self.assertEqual(result["summary"]["margin_credit_factor_count"], 2)
        self.assertGreaterEqual(result["summary"]["residual_factor_count"], 2)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertIn("industry_metadata_missing_or_not_pit", result["gate"]["blockers"])
        self.assertIn("portfolio_grid_blocked_before_cost_capacity_walk_forward", result["gate"]["blockers"])
        self.assertIn("reference_factor_correlations", result)
        self.assertIn("style_exposure_correlations", result)
        self.assertIn("residual_ic_summaries", result)
        self.assertTrue(
            any(row["correlation_observations"] > 0 for row in result["reference_factor_correlations"]),
            "reference dedup must sample on lead dates so overlap is audited",
        )
        residual_names = {row["factor_name"] for row in result["residual_ic_summaries"]}
        self.assertIn("margin_balance_crowding_reversal_20__style_residual", residual_names)
        self.assertIn("margin_financing_acceleration_exhaustion_20__style_residual", residual_names)
        self.assertTrue(result["sampling_policy"]["ic_uses_all_dates"])
        self.assertTrue(result["sampling_policy"]["sampling_used_for_correlations_only"])

    def test_writer_emits_json_markdown_and_audit_csvs(self) -> None:
        bars = _synthetic_bars(days=58, assets=12, start="2024-01-02")
        result = build_external_feed_margin_credit_neutral_dedup_from_frames(
            bars=bars,
            margin_detail=_synthetic_margin_detail(bars, raw_dates=pd.bdate_range("2024-01-02", periods=52)),
            prescreen_report=_round192_prescreen_report(),
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-12-31",
            horizon=1,
            execution_lag=0,
            lookback=5,
            sample_every_n_dates=2,
            min_cross_section=6,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_external_feed_margin_credit_neutral_dedup(output, result)

            self.assertTrue((output / "external_feed_margin_credit_neutral_dedup.json").exists())
            self.assertTrue((output / "external_feed_margin_credit_neutral_dedup.md").exists())
            self.assertTrue((output / "external_feed_margin_credit_reference_correlations.csv").exists())
            self.assertTrue((output / "external_feed_margin_credit_style_exposures.csv").exists())
            self.assertTrue((output / "external_feed_margin_credit_residual_ic.csv").exists())

    def test_reference_dedup_samples_reference_factors_on_lead_dates(self) -> None:
        bars = _synthetic_bars(days=220, assets=12, start="2023-07-03")
        margin = _synthetic_margin_detail(bars, raw_dates=pd.bdate_range("2024-02-01", periods=60))

        result = build_external_feed_margin_credit_neutral_dedup_from_frames(
            bars=bars,
            margin_detail=margin,
            prescreen_report=_round192_prescreen_report(),
            analysis_start_date="2023-07-01",
            analysis_end_date="2024-12-31",
            include_final_holdout=False,
            horizon=1,
            execution_lag=0,
            lookback=5,
            sample_every_n_dates=5,
            min_cross_section=6,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
        )

        self.assertTrue(
            any(row["correlation_observations"] > 0 for row in result["reference_factor_correlations"]),
            "reference factors must be filtered to the sampled lead dates instead of sampled independently",
        )

    def test_gate_blocks_weak_style_residual_ic_and_moderate_reference_redundancy(self) -> None:
        gate = _gate(
            margin_factors=pd.DataFrame(
                {
                    "date": [pd.Timestamp("2024-01-02")],
                    "asset_id": ["CN_XSHE_000001"],
                    "market": ["CN"],
                    "factor_name": ["margin_balance_crowding_reversal_20"],
                    "factor_value": [1.0],
                }
            ),
            reference_correlations=[
                {
                    "redundancy_class": "moderately_redundant",
                    "blockers": ["moderate_reference_correlation_with_lead"],
                }
            ],
            style_exposure_correlations=[],
            residual_ic_summaries=[
                {
                    "mean_spearman_ic": 0.002,
                    "ic_t_stat": 0.8,
                    "minimum_observation_gate_passed": True,
                }
            ],
            prescreen_report=_round192_prescreen_report(),
        )

        self.assertIn("style_residual_ic_not_material", gate["blockers"])
        self.assertIn("margin_credit_moderately_redundant_with_price_volume_reference", gate["blockers"])


def _round192_prescreen_report() -> dict:
    return {
        "stage": "external_feed_margin_credit_prescreen",
        "summary": {"research_lead_count": 0, "candidate_count": 2, "test_count": 2},
        "results": [
            {
                "factor_name": "margin_balance_crowding_reversal_20",
                "horizon": 1,
                "research_lead": False,
                "fdr_significant": True,
                "mean_spearman_ic": 0.05,
                "blockers": ["quantile_monotonicity_weak"],
            },
            {
                "factor_name": "margin_financing_acceleration_exhaustion_20",
                "horizon": 1,
                "research_lead": False,
                "fdr_significant": True,
                "mean_spearman_ic": 0.03,
                "blockers": ["quantile_monotonicity_weak"],
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
