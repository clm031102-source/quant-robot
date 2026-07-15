import unittest

import pandas as pd

from quant_robot.ops.cn_etf_skip_momentum_prescreen import (
    build_historical_price_rotation_stop_loss_review,
    summarize_cn_etf_skip_momentum_prescreen,
)


class CnEtfSkipMomentumPrescreenTests(unittest.TestCase):
    def test_stable_independent_signal_passes_research_gate_only(self) -> None:
        factors, labels, references = _statistical_frames(mode="stable", years=(2021, 2022, 2023))

        result = summarize_cn_etf_skip_momentum_prescreen(
            factors,
            labels,
            references,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=15,
            min_year_ic_observations=5,
            min_usable_years=3,
        )

        self.assertEqual(result["summary"]["candidate_count"], 1)
        self.assertEqual(result["summary"]["test_count"], 1)
        self.assertEqual(result["summary"]["research_lead_count"], 1)
        row = result["results"][0]
        self.assertTrue(row["fdr_significant"])
        self.assertTrue(row["research_lead"])
        self.assertGreater(row["mean_rank_ic"], 0.02)
        self.assertGreaterEqual(row["usable_years"], 3)
        self.assertGreaterEqual(row["positive_year_rate"], 0.60)
        self.assertLess(row["max_abs_reference_correlation"], 0.85)
        self.assertFalse(row["promotion_allowed"])
        self.assertFalse(result["decision"]["walk_forward_allowed"])
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])

    def test_rank_equivalent_historical_reference_blocks_otherwise_stable_signal(self) -> None:
        factors, labels, _ = _statistical_frames(mode="stable", years=(2021, 2022, 2023))
        references = factors.rename(columns={"factor_name": "reference_name"}).copy()
        references["factor_name"] = "momentum_60"
        references = references.drop(columns=["reference_name"])

        result = summarize_cn_etf_skip_momentum_prescreen(
            factors,
            labels,
            references,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=15,
            min_year_ic_observations=5,
            min_usable_years=3,
        )

        row = result["results"][0]
        self.assertGreaterEqual(row["max_abs_reference_correlation"], 0.999)
        self.assertFalse(row["research_lead"])
        self.assertIn("historical_reference_duplicate", row["blockers"])
        self.assertEqual(result["decision"]["next_action"], "close_price_rotation_and_rotate_scheduler")

    def test_one_year_signal_fails_year_stability_gate(self) -> None:
        factors, labels, references = _statistical_frames(mode="stable", years=(2023,))

        result = summarize_cn_etf_skip_momentum_prescreen(
            factors,
            labels,
            references,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=5,
            min_year_ic_observations=5,
            min_usable_years=3,
        )

        row = result["results"][0]
        self.assertEqual(row["usable_years"], 1)
        self.assertFalse(row["research_lead"])
        self.assertIn("usable_years_below_threshold", row["blockers"])

    def test_non_significant_signal_fails_fdr_gate(self) -> None:
        factors, labels, references = _statistical_frames(mode="noise", years=(2021, 2022, 2023))

        result = summarize_cn_etf_skip_momentum_prescreen(
            factors,
            labels,
            references,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=15,
            min_year_ic_observations=5,
            min_usable_years=3,
        )

        row = result["results"][0]
        self.assertFalse(row["fdr_significant"])
        self.assertFalse(row["research_lead"])
        self.assertIn("not_fdr_significant_after_multiple_testing", row["blockers"])

    def test_historical_review_closes_tested_paths_without_rescue(self) -> None:
        review = build_historical_price_rotation_stop_loss_review()

        self.assertIn("momentum_60", review["closed_factor_names"])
        self.assertIn("market_relative_strength_60", review["closed_factor_names"])
        self.assertIn("tail_guard_reversal", review["closed_subfamilies"])
        self.assertFalse(review["parameter_rescue_allowed"])
        self.assertEqual(
            review["remaining_candidate_names"],
            [
                "etf_skip5_momentum_60",
                "etf_skip20_momentum_120",
                "fip_smooth_momentum_skip5_60",
            ],
        )


def _statistical_frames(*, mode: str, years: tuple[int, ...]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    factor_rows = []
    label_rows = []
    reference_rows = []
    date_index = 0
    for year in years:
        for signal_date in pd.bdate_range(f"{year}-01-04", periods=8):
            for asset_index in range(30):
                asset_id = f"CN_ETF_XSHG_{510000 + asset_index}"
                signal = float(asset_index)
                if mode == "stable":
                    forward_score = signal + float((asset_index * (date_index % 5 + 1)) % 7) * 0.75
                else:
                    forward_score = float((asset_index * 11 + date_index * 7) % 31)
                reference_value = float((asset_index * 13 + date_index * 5) % 31)
                factor_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "factor_name": "etf_skip5_momentum_60",
                        "factor_value": signal,
                        "lookback_window": 65,
                    }
                )
                label_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": forward_score / 10_000.0,
                        "entry_date": signal_date + pd.offsets.BDay(1),
                        "exit_date": signal_date + pd.offsets.BDay(6),
                    }
                )
                reference_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "factor_name": "momentum_60",
                        "factor_value": reference_value,
                        "lookback_window": 60,
                    }
                )
            date_index += 1
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows)
