import unittest

import pandas as pd

from quant_robot.ops.cn_etf_market_residual_volatility_prescreen import (
    build_historical_volatility_regime_review,
    summarize_cn_etf_market_residual_volatility_prescreen,
)


class CnEtfMarketResidualVolatilityPrescreenTests(unittest.TestCase):
    def test_stable_independent_capacity_feasible_signal_passes_research_gate_only(self) -> None:
        factors, labels, references, adv20 = _statistical_frames(adv20_cny=20_000_000.0)

        result = summarize_cn_etf_market_residual_volatility_prescreen(
            factors,
            labels,
            references,
            adv20,
            expected_candidate_names=("etf_idio_vol_low_60",),
            expected_reference_names=("low_volatility_60",),
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=15,
            min_year_ic_observations=5,
            min_usable_years=3,
        )

        self.assertEqual(result["summary"]["research_lead_count"], 1)
        row = result["results"][0]
        self.assertTrue(row["research_lead"])
        self.assertEqual(row["top_quantile_adv20_p10_cny"], 20_000_000.0)
        self.assertAlmostEqual(row["p10_one_way_participation_rate"], 0.005)
        self.assertFalse(row["promotion_allowed"])
        self.assertFalse(result["decision"]["walk_forward_allowed"])
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["paper_signal_allowed"])
        self.assertEqual(
            result["decision"]["next_action"],
            "backfill_2024h2_2025_then_freeze_walk_forward",
        )

    def test_low_capacity_blocks_otherwise_stable_signal_and_triggers_stop_loss(self) -> None:
        factors, labels, references, adv20 = _statistical_frames(adv20_cny=5_000_000.0)

        result = summarize_cn_etf_market_residual_volatility_prescreen(
            factors,
            labels,
            references,
            adv20,
            expected_candidate_names=("etf_idio_vol_low_60",),
            expected_reference_names=("low_volatility_60",),
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=15,
            min_year_ic_observations=5,
            min_usable_years=3,
        )

        row = result["results"][0]
        self.assertFalse(row["research_lead"])
        self.assertIn("top_quantile_capacity_below_threshold", row["blockers"])
        self.assertEqual(
            result["decision"]["next_action"],
            "stop_loss_volatility_regime_and_activate_peer_relative_value",
        )

    def test_all_nan_historical_reference_fails_closed(self) -> None:
        factors, labels, references, adv20 = _statistical_frames(adv20_cny=20_000_000.0)
        references["factor_value"] = float("nan")

        result = summarize_cn_etf_market_residual_volatility_prescreen(
            factors,
            labels,
            references,
            adv20,
            expected_candidate_names=("etf_idio_vol_low_60",),
            expected_reference_names=("low_volatility_60",),
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=15,
            min_year_ic_observations=5,
            min_usable_years=3,
        )

        row = result["results"][0]
        self.assertFalse(row["research_lead"])
        self.assertIn("historical_reference_evidence_incomplete", row["blockers"])
        self.assertEqual(result["reference_correlations"][0]["daily_observations"], 0)

    def test_historical_review_closes_previously_tested_subfamilies(self) -> None:
        review = build_historical_volatility_regime_review()

        self.assertIn("low_volatility_20", review["closed_factor_names"])
        self.assertIn("state_adaptive_trend_defense_60", review["closed_factor_names"])
        self.assertIn("formula_range_contraction_breakout_20", review["closed_factor_names"])
        self.assertEqual(review["remaining_candidate_count"], 3)
        self.assertTrue(review["last_chance_batch"])
        self.assertFalse(review["sign_flip_rescue_allowed"])
        self.assertFalse(review["portfolio_grid_before_prescreen_lead_allowed"])


def _statistical_frames(
    *,
    adv20_cny: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    factor_rows = []
    label_rows = []
    reference_rows = []
    adv20_rows = []
    date_index = 0
    for year in (2021, 2022, 2023):
        for signal_date in pd.bdate_range(f"{year}-01-04", periods=8):
            for asset_index in range(30):
                asset_id = f"CN_ETF_XSHG_{510000 + asset_index}"
                signal = float(asset_index)
                forward_score = signal + float((asset_index * (date_index % 5 + 1)) % 7) * 0.75
                factor_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "factor_name": "etf_idio_vol_low_60",
                        "factor_value": signal,
                        "lookback_window": 180,
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
                    }
                )
                reference_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "factor_name": "low_volatility_60",
                        "factor_value": float((asset_index * 13 + date_index * 5) % 31),
                        "lookback_window": 60,
                    }
                )
                adv20_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "adv20": adv20_cny,
                    }
                )
            date_index += 1
    return (
        pd.DataFrame(factor_rows),
        pd.DataFrame(label_rows),
        pd.DataFrame(reference_rows),
        pd.DataFrame(adv20_rows),
    )


if __name__ == "__main__":
    unittest.main()
