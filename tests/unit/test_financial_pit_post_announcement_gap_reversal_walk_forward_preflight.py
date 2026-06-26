import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.financial_pit_post_announcement_gap_reversal_walk_forward_preflight import (
    EXPECTED_STARTUP_NEXT_DIRECTION,
    NEXT_WALK_FORWARD_DIRECTION,
    build_candidate_pair_correlations,
    summarize_financial_pit_post_announcement_gap_reversal_walk_forward_preflight,
    write_financial_pit_post_announcement_gap_reversal_walk_forward_preflight,
)


LOW_LIQ = "pead_gap_overreaction_reversal_low_liquidity_penalized_1_5"
BASE = "pead_gap_overreaction_reversal_1_5"
QUALITY = "pead_gap_overreaction_reversal_quality_conditioned_1_5"


class FinancialPitPostAnnouncementGapReversalWalkForwardPreflightTests(unittest.TestCase):
    def test_preflight_dedupes_correlated_leads_and_never_promotes(self) -> None:
        result = summarize_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(
            residual_report=_residual_report(),
            factor_frame=_factor_frame(),
            startup_gate=_startup_gate(),
            portfolio_policy=_portfolio_policy(),
            regime_policy=_regime_policy(),
            min_pair_observations=3,
            min_corr_cross_section=5,
            candidate_high_corr_threshold=0.95,
        )

        self.assertEqual(result["stage"], "financial_pit_post_announcement_gap_reversal_reference_dedup_walk_forward_preflight")
        self.assertEqual(result["status"], "cleared")
        self.assertEqual(result["preflight_policy"]["next_direction"], NEXT_WALK_FORWARD_DIRECTION)
        self.assertTrue(result["preflight_policy"]["walk_forward_preflight_cleared"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        frozen = [row["factor_name"] for row in result["frozen_candidates"]]
        self.assertIn(LOW_LIQ, frozen)
        self.assertIn(QUALITY, frozen)
        duplicate = next(row for row in result["candidate_table"] if row["factor_name"] == BASE)
        self.assertEqual(duplicate["preflight_status"], "cluster_duplicate")
        self.assertEqual(duplicate["cluster_representative"], LOW_LIQ)

    def test_pair_correlation_uses_cross_sectional_dates(self) -> None:
        correlations = build_candidate_pair_correlations(
            _factor_frame(),
            [LOW_LIQ, BASE, QUALITY],
            min_corr_cross_section=5,
            min_pair_observations=3,
        )

        high = next(row for row in correlations if {row["factor_name"], row["other_factor_name"]} == {LOW_LIQ, BASE})
        low = next(row for row in correlations if {row["factor_name"], row["other_factor_name"]} == {LOW_LIQ, QUALITY})
        self.assertGreater(high["mean_abs_spearman_corr"], 0.99)
        self.assertLess(low["mean_abs_spearman_corr"], 0.95)

    def test_blocks_wrong_startup_direction(self) -> None:
        gate = _startup_gate()
        gate["repeatable_mining_protocol"]["next_direction"] = "keep_blind_mining"

        result = summarize_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(
            residual_report=_residual_report(),
            factor_frame=_factor_frame(),
            startup_gate=gate,
            portfolio_policy=_portfolio_policy(),
            regime_policy=_regime_policy(),
            min_pair_observations=3,
            min_corr_cross_section=5,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("startup_gate_next_direction_mismatch", result["decision"]["blockers"])
        self.assertFalse(result["preflight_policy"]["walk_forward_preflight_cleared"])

    def test_write_outputs(self) -> None:
        result = summarize_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(
            residual_report=_residual_report(),
            factor_frame=_factor_frame(),
            startup_gate=_startup_gate(),
            portfolio_policy=_portfolio_policy(),
            regime_policy=_regime_policy(),
            min_pair_observations=3,
            min_corr_cross_section=5,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(output, result)
            self.assertTrue((output / "financial_pit_post_announcement_gap_reversal_walk_forward_preflight.json").exists())
            self.assertTrue((output / "financial_pit_post_announcement_gap_reversal_walk_forward_preflight.md").exists())
            self.assertTrue((output / "financial_pit_post_announcement_gap_reversal_walk_forward_candidates.csv").exists())
            self.assertTrue((output / "financial_pit_post_announcement_gap_reversal_candidate_pair_correlations.csv").exists())


def _residual_report() -> dict:
    return {
        "stage": "financial_pit_post_announcement_gap_reversal_residual_prescreen",
        "summary": {
            "passes": True,
            "research_lead_count": 3,
            "next_direction": EXPECTED_STARTUP_NEXT_DIRECTION,
        },
        "holdout_policy": {
            "final_holdout_included": False,
            "analysis_start_date": "2015-01-01",
            "analysis_end_date": "2025-12-31",
        },
        "results": [
            _result_row(LOW_LIQ, mean_ic=0.14, t_stat=4.0, reference_corr=0.70),
            _result_row(BASE, mean_ic=0.12, t_stat=3.4, reference_corr=0.69),
            _result_row(QUALITY, mean_ic=0.07, t_stat=2.3, reference_corr=0.58),
        ],
    }


def _result_row(factor_name: str, *, mean_ic: float, t_stat: float, reference_corr: float) -> dict:
    return {
        "factor_name": factor_name,
        "horizon": 5,
        "ic_observations": 30,
        "mean_spearman_ic": mean_ic,
        "icir": mean_ic * 5,
        "ic_t_stat": t_stat,
        "fdr_significant": True,
        "ic_positive_rate": 0.7,
        "quantile_spread": 0.01,
        "quantile_monotonicity": 0.8,
        "mean_industry_neutral_rank_ic": mean_ic,
        "industry_neutral_rank_ic_t_stat": t_stat,
        "mean_size_neutral_rank_ic": mean_ic * 0.8,
        "size_neutral_rank_ic_t_stat": t_stat * 0.8,
        "mean_liquidity_neutral_rank_ic": mean_ic * 0.9,
        "liquidity_neutral_rank_ic_t_stat": t_stat * 0.9,
        "reference_max_abs_correlation": reference_corr,
        "reference_mean_abs_correlation": 0.2,
        "reference_top_match": "fina_profit_growth_quality_spread",
        "research_lead": True,
        "promotion_allowed": False,
    }


def _factor_frame() -> pd.DataFrame:
    rows = []
    dates = pd.bdate_range("2025-01-02", periods=6)
    assets = [f"A{i:02d}" for i in range(20)]
    for trade_date in dates:
        for idx, asset_id in enumerate(assets):
            common = float(idx)
            values = {
                LOW_LIQ: common,
                BASE: common * 1.01 + 0.001,
                QUALITY: float((idx % 5) - 2),
            }
            for factor_name, value in values.items():
                rows.append(
                    {
                        "date": trade_date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": factor_name,
                        "factor_value": value,
                    }
                )
    return pd.DataFrame(rows)


def _startup_gate() -> dict:
    return {
        "status": "cleared",
        "decision": {"startup_gate_cleared": True, "blockers": []},
        "repeatable_mining_protocol": {"next_direction": EXPECTED_STARTUP_NEXT_DIRECTION},
        "live_boundary_allowed": False,
    }


def _portfolio_policy() -> dict:
    return {
        "market": "CN",
        "asset_type": "stock",
        "risk_budget": {"max_single_name_weight": 0.05, "max_position_adv_participation": 0.01},
        "drawdown_controls": {"max_drawdown_soft_tolerance": 0.3, "hard_stop_drawdown_threshold": 0.45},
        "required_metric_pack": ["total_return", "annual_return", "sharpe", "max_drawdown", "win_rate", "capacity_usage"],
    }


def _regime_policy() -> dict:
    return {
        "scope_id": "cn_stock_china_market_regime_controls",
        "market": "CN",
        "asset_type": "stock",
        "controls": [
            {"control_id": "policy_liquidity_regime"},
            {"control_id": "credit_cycle_proxy"},
            {"control_id": "northbound_margin_turnover_temperature"},
            {"control_id": "index_location_state"},
        ],
    }


if __name__ == "__main__":
    unittest.main()
