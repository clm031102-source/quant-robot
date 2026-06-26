import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.historical_lead_recovery_audit import (
    build_historical_lead_recovery_audit,
    write_historical_lead_recovery_audit,
)


class HistoricalLeadRecoveryAuditTests(unittest.TestCase):
    def test_rejects_high_return_round126_when_conversion_gates_fail(self) -> None:
        audit = build_historical_lead_recovery_audit(
            turnover_conversion=_turnover_conversion_packet(),
            market_residual_dedup=_dedup_packet(
                factor_name="beta_adjusted_range_contraction_60",
                blockers=[
                    "lead_highly_redundant_with_reference_factor",
                    "lead_high_exposure_to_market_or_liquidity_proxy",
                    "twenty_fifteen_regime_failure_unexplained",
                    "yearly_ic_instability",
                ],
                yearly_failure=True,
            ),
            public_alpha101_dedup=_dedup_packet(
                factor_name="qlib_alpha158_return_std_position_blend_20",
                blockers=[
                    "lead_highly_redundant_with_reference_factor",
                    "lead_high_exposure_to_market_or_liquidity_proxy",
                ],
            ),
            public_reference_replay=_public_reference_replay_packet(),
        )

        self.assertEqual(audit["stage"], "historical_lead_recovery_audit")
        self.assertEqual(audit["status"], "historical_leads_rejected_rotate_family")
        self.assertEqual(audit["summary"]["candidate_count"], 5)
        self.assertEqual(audit["summary"]["recovery_candidate_count"], 0)
        self.assertEqual(audit["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(audit["summary"]["portfolio_conversion_failed_candidates"], 1)
        self.assertGreaterEqual(audit["summary"]["redundancy_or_exposure_blocked_candidates"], 2)
        self.assertGreaterEqual(audit["summary"]["quantile_shape_blocked_candidates"], 2)
        turnover = next(row for row in audit["candidate_rows"] if row["source_round"] == "round126")
        self.assertFalse(turnover["recovery_candidate"])
        self.assertIn("portfolio_conversion_failure", turnover["failure_class"])
        self.assertIn("max_drawdown_below_user_soft_floor", turnover["blockers"])
        self.assertIn("zero_walk_forward_allowed_candidates", turnover["blockers"])
        self.assertIn("Round126 failed", audit["round126_failure_analysis"]["notes"][0])
        self.assertTrue(audit["decision"]["family_rotation_required"])

    def test_soft_next_gate_blocker_can_still_be_recovery_candidate(self) -> None:
        audit = build_historical_lead_recovery_audit(
            public_reference_replay={
                "stage": "public_reference_multi_family_prescreen",
                "results": [
                    {
                        "factor_name": "clean_public_factor",
                        "family": "public",
                        "horizon": 20,
                        "mean_spearman_ic": 0.04,
                        "icir": 0.5,
                        "ic_t_stat": 8.0,
                        "ic_positive_rate": 0.65,
                        "quantile_spread": 0.02,
                        "quantile_monotonicity": 0.8,
                        "blockers": ["promotion_requires_later_walk_forward_cost_capacity_regime_gates"],
                        "promotion_allowed": False,
                    }
                ],
            },
            public_reference_specs=[
                ("clean_public_factor", 20, "round999", "public_clean_test"),
            ],
        )

        row = audit["candidate_rows"][0]
        self.assertEqual(audit["status"], "historical_leads_need_walk_forward_recovery")
        self.assertTrue(row["recovery_candidate"])
        self.assertFalse(row["promotion_allowed"])
        self.assertEqual(row["failure_class"], "next_gate_only")
        self.assertFalse(audit["decision"]["family_rotation_required"])
        self.assertTrue(audit["decision"]["portfolio_grid_allowed"])

    def test_writer_emits_json_markdown_and_csv(self) -> None:
        audit = build_historical_lead_recovery_audit(
            turnover_conversion=_turnover_conversion_packet(),
            public_reference_replay=_public_reference_replay_packet(),
        )
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_historical_lead_recovery_audit(output, audit)

            self.assertTrue((output / "historical_lead_recovery_audit.json").exists())
            self.assertTrue((output / "historical_lead_recovery_audit.md").exists())
            self.assertTrue((output / "historical_lead_recovery_rows.csv").exists())
            markdown = (output / "historical_lead_recovery_audit.md").read_text(encoding="utf-8")
            self.assertIn("Historical Lead Recovery Audit", markdown)
            self.assertIn("Round126 Failure Analysis", markdown)


def _turnover_conversion_packet() -> dict:
    return {
        "stage": "turnover_repair_champion_portfolio_conversion",
        "summary": {
            "factor_names": ["turnover_rate_f_low_participation_budget_100k_20"],
            "walk_forward_allowed_candidates": 0,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "blockers": [
                "costed_conversion_is_not_walk_forward",
                "regime_coverage_not_yet_verified",
                "final_holdout_not_read",
                "dedup_revealed_zero_independent_new_alpha",
            ],
        },
        "leaderboard": [
            {
                "case_id": "best",
                "factor_name": "turnover_rate_f_low_participation_budget_100k_20",
                "holding_period": 20,
                "total_return": 10.94,
                "annualized_return": 0.119,
                "sharpe": 0.224,
                "overlap_autocorr_adjusted_sharpe": 0.226,
                "overlap_newey_west_t_stat_mean": 1.061,
                "max_drawdown": -0.696,
                "win_rate": 0.558,
                "hard_blocked": True,
                "blockers": "overlap_adjusted_sharpe_below_min;calendar_holding_gate_filtered_trades;extreme_trade_return_present;max_drawdown_below_user_floor",
                "extreme_trade_return_rate": 0.016,
                "max_abs_trade_gross_return": 205.39,
                "calendar_limited_trades": 126,
                "capacity_limited_trades": 0,
            }
        ],
    }


def _dedup_packet(*, factor_name: str, blockers: list[str], yearly_failure: bool = False) -> dict:
    return {
        "stage": "lead_exposure_dedup",
        "lead_factor_name": factor_name,
        "horizon": 20,
        "lead_ic_summary": {
            "mean_spearman_ic": 0.05,
            "icir": 0.37,
            "ic_t_stat": 18.8,
            "positive_ic_rate": 0.67,
        },
        "summary": {
            "exposure_high_count": 2,
            "reference_highly_redundant_count": 1,
            "yearly_failure_count": 1 if yearly_failure else 0,
            "monthly_failure_count": 12,
        },
        "gate": {"blockers": blockers},
        "promotion_policy": {"promotion_allowed": False, "portfolio_grid_allowed": False},
        "yearly_ic": [
            {
                "year": 2015,
                "failure": yearly_failure,
                "mean_spearman_ic": -0.10 if yearly_failure else 0.02,
                "positive_ic_rate": 0.24 if yearly_failure else 0.55,
            }
        ],
        "reference_correlations": [{"max_abs_correlation": 0.98}],
        "exposure_correlations": [{"max_abs_correlation": 0.91}],
    }


def _public_reference_replay_packet() -> dict:
    return {
        "stage": "public_reference_multi_family_prescreen",
        "results": [
            {
                "factor_name": "alpha101_rank_pv_reversal_liquid_20",
                "family": "public_formula_alpha101",
                "horizon": 20,
                "mean_spearman_ic": 0.047,
                "icir": 0.479,
                "ic_t_stat": 24.6,
                "ic_positive_rate": 0.681,
                "quantile_spread": -0.031,
                "quantile_monotonicity": -0.3,
                "research_lead": False,
                "promotion_allowed": False,
                "fdr_significant": True,
                "blockers": [
                    "top_minus_bottom_quantile_not_positive",
                    "quantile_monotonicity_weak",
                    "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
                ],
            },
            {
                "factor_name": "main_force_divergence_reversal_5_20",
                "family": "smart_money_flow",
                "horizon": 5,
                "mean_spearman_ic": 0.034,
                "icir": 0.239,
                "ic_t_stat": 12.3,
                "ic_positive_rate": 0.585,
                "quantile_spread": 0.003,
                "quantile_monotonicity": -0.1,
                "research_lead": False,
                "promotion_allowed": False,
                "fdr_significant": True,
                "blockers": [
                    "icir_below_threshold",
                    "quantile_monotonicity_weak",
                    "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
                ],
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
