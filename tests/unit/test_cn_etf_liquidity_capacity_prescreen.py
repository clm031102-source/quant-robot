import unittest

import pandas as pd

from quant_robot.ops.cn_etf_liquidity_capacity_prescreen import (
    build_historical_liquidity_capacity_review,
    summarize_cn_etf_liquidity_capacity_prescreen,
)


class CnEtfLiquidityCapacityPrescreenTests(unittest.TestCase):
    def test_stable_independent_capacity_feasible_signal_passes_research_gate_only(self) -> None:
        factors, labels, references, adv20 = _statistical_frames(adv20_cny=20_000_000.0)

        result = summarize_cn_etf_liquidity_capacity_prescreen(
            factors,
            labels,
            references,
            adv20,
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
        self.assertNotIn("top_quantile_capacity_below_threshold", row["blockers"])
        self.assertFalse(row["promotion_allowed"])
        self.assertFalse(result["decision"]["walk_forward_allowed"])
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["paper_signal_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])

    def test_low_top_quantile_adv20_blocks_otherwise_stable_signal(self) -> None:
        factors, labels, references, adv20 = _statistical_frames(adv20_cny=5_000_000.0)

        result = summarize_cn_etf_liquidity_capacity_prescreen(
            factors,
            labels,
            references,
            adv20,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=15,
            min_year_ic_observations=5,
            min_usable_years=3,
        )

        row = result["results"][0]
        self.assertFalse(row["research_lead"])
        self.assertAlmostEqual(row["p10_one_way_participation_rate"], 0.02)
        self.assertIn("top_quantile_capacity_below_threshold", row["blockers"])
        self.assertEqual(result["decision"]["next_action"], "stop_loss_liquidity_capacity_and_rotate_scheduler")

    def test_missing_capacity_rows_fail_closed(self) -> None:
        factors, labels, references, _ = _statistical_frames(adv20_cny=20_000_000.0)
        adv20 = pd.DataFrame(columns=["date", "asset_id", "market", "adv20"])

        result = summarize_cn_etf_liquidity_capacity_prescreen(
            factors,
            labels,
            references,
            adv20,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=15,
            min_year_ic_observations=5,
            min_usable_years=3,
        )

        row = result["results"][0]
        self.assertFalse(row["research_lead"])
        self.assertEqual(row["top_quantile_adv20_observations"], 0)
        self.assertIn("top_quantile_capacity_evidence_missing", row["blockers"])

    def test_historical_review_quarantines_stale_legacy_promotion(self) -> None:
        review = build_historical_liquidity_capacity_review()

        self.assertIn("liquidity_10", review["closed_factor_names"])
        self.assertIn("amount_stability_60", review["closed_factor_names"])
        self.assertEqual(review["legacy_candidate_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")
        self.assertEqual(review["current_strict_gate_expected_paper_ready"], 0)
        self.assertFalse(review["legacy_candidate_reuse_allowed"])
        self.assertFalse(review["parameter_rescue_allowed"])


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
                        "factor_name": "etf_amihud_improvement_5_60",
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
                    }
                )
                reference_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "factor_name": "liquidity_20",
                        "factor_value": float((asset_index * 13 + date_index * 5) % 31),
                        "lookback_window": 20,
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
