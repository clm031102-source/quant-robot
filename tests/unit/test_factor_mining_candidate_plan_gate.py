import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.factor_mining_candidate_plan_gate import (
    build_factor_mining_candidate_plan_gate,
    default_cn_stock_pre_mining_control_plan,
    default_cn_stock_promotion_policy,
    validate_candidate_plan_gate_packet,
    write_factor_mining_candidate_plan_gate,
)


def _candidate_plan() -> dict:
    return {
        "stage": "example_preregistration",
        "research_control_plan": default_cn_stock_pre_mining_control_plan(),
        "evaluation_gate": {
            "required_metrics": [
                "mean_spearman_ic",
                "industry_neutral_ic",
                "size_liquidity_neutral_ic",
                "limit_up_down_tradeability_audit",
            ],
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "promotion_policy": default_cn_stock_promotion_policy(),
        "candidates": [
            {
                "factor_name": "lottery_max_return_reversal_20",
                "family": "max_effect_reversal",
                "market": "CN",
                "asset_type": "stock",
                "registration_status": "pre_registered",
                "hypothesis_source": "public_reference:max_effect_reversal",
                "economic_rationale": "Public MAX-effect hypothesis with A-share tradeability controls.",
                "portfolio_backtest_allowed": False,
                "promotion_allowed": False,
            }
        ],
    }


class FactorMiningCandidatePlanGateTests(unittest.TestCase):
    def test_research_gate_clears_only_when_all_pre_mining_controls_are_declared(self) -> None:
        packet = build_factor_mining_candidate_plan_gate(_candidate_plan(), gate_stage="discovery")

        self.assertEqual(packet["stage"], "factor_mining_candidate_plan_gate")
        self.assertEqual(packet["status"], "research_ready")
        self.assertTrue(packet["decision"]["candidate_plan_gate_cleared"])
        self.assertTrue(packet["decision"]["research_screen_allowed"])
        self.assertFalse(packet["decision"]["portfolio_grid_allowed"])
        self.assertFalse(packet["decision"]["promotion_allowed"])
        self.assertEqual(packet["decision"]["blockers"], [])
        self.assertIn("cn_stock_tradeability", {area["area_id"] for area in packet["control_area_rows"]})
        self.assertIn("portfolio_construction", {area["area_id"] for area in packet["control_area_rows"]})
        self.assertIn("source_sample_integrity", {area["area_id"] for area in packet["control_area_rows"]})

    def test_blocks_missing_tradeability_pit_neutralization_and_statistics_controls(self) -> None:
        plan = _candidate_plan()
        plan["research_control_plan"] = {
            "declared_controls": {
                "cn_stock_tradeability": ["st_flag_filter"],
                "strict_statistics": ["deflated_sharpe"],
            }
        }

        packet = build_factor_mining_candidate_plan_gate(plan, gate_stage="discovery")

        self.assertEqual(packet["status"], "blocked")
        self.assertFalse(packet["decision"]["candidate_plan_gate_cleared"])
        blockers = packet["decision"]["blockers"]
        self.assertIn("missing_control_area:financial_pit_timing", blockers)
        self.assertIn("missing_control_area:industry_style_neutralization", blockers)
        self.assertIn("missing_control_area:china_market_regime", blockers)
        self.assertTrue(any(blocker.startswith("missing_controls:cn_stock_tradeability") for blocker in blockers))
        self.assertTrue(any(blocker.startswith("missing_controls:strict_statistics") for blocker in blockers))
        self.assertIn("missing_control_area:source_sample_integrity", blockers)

    def test_discovery_gate_blocks_missing_source_sample_integrity_controls(self) -> None:
        plan = _candidate_plan()
        plan["research_control_plan"]["declared_controls"]["source_sample_integrity"] = [
            "endpoint_permission_or_cache_manifest",
            "point_in_time_available_date_semantics",
        ]

        packet = build_factor_mining_candidate_plan_gate(plan, gate_stage="discovery")

        self.assertEqual(packet["status"], "blocked")
        blockers = packet["decision"]["blockers"]
        self.assertIn("missing_control_area:source_sample_integrity", blockers)
        self.assertTrue(any(blocker.startswith("missing_controls:source_sample_integrity") for blocker in blockers))

    def test_default_promotion_policy_requires_strict_statistical_reality_checks(self) -> None:
        policy = default_cn_stock_promotion_policy()

        for key in (
            "requires_data_source_availability_proof",
            "requires_full_sample_regime_coverage",
            "requires_future_function_static_audit",
            "requires_deflated_sharpe_or_fdr",
            "requires_cpcv_or_purged_walk_forward",
            "requires_white_reality_check_or_multiple_test_adjustment",
            "requires_parameter_sensitivity_heatmap",
            "requires_profit_drawdown_winrate_report",
        ):
            self.assertTrue(policy[key])

    def test_promotion_stage_requires_promotion_ready_quality_gate(self) -> None:
        quality_gate = {
            "status": "classified",
            "decision": {
                "startup_gate_cleared": True,
                "promotion_gate_cleared": False,
                "promotion_blockers": ["promotion_control_not_implemented:risk_budget_position_sizing"],
            },
        }

        packet = build_factor_mining_candidate_plan_gate(
            _candidate_plan(),
            gate_stage="promotion",
            quality_gate=quality_gate,
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertIn("quality_gate_not_promotion_ready", packet["decision"]["blockers"])
        self.assertFalse(packet["decision"]["promotion_allowed"])

    def test_blocks_candidate_plan_that_allows_portfolio_or_promotion_too_early(self) -> None:
        plan = _candidate_plan()
        plan["candidates"][0]["portfolio_backtest_allowed"] = True
        plan["promotion_policy"]["promotion_allowed"] = True

        packet = build_factor_mining_candidate_plan_gate(plan, gate_stage="discovery")

        self.assertIn("candidate_portfolio_backtest_allowed_before_prescreen", packet["decision"]["blockers"])
        self.assertIn("plan_promotion_allowed_before_validation", packet["decision"]["blockers"])

    def test_discovery_gate_allows_documented_blocked_candidates_when_active_candidates_remain(self) -> None:
        plan = _candidate_plan()
        plan["candidates"].append(
            {
                "factor_name": "pit_forecast_profit_revision_event_1q",
                "family": "forecast_revision_event",
                "market": "CN",
                "asset_type": "stock",
                "registration_status": "blocked_by_endpoint_availability",
                "hypothesis_source": "tushare_endpoint:event_revision",
                "economic_rationale": "Forecast revision event candidate is logged but frozen until endpoint proof exists.",
                "portfolio_backtest_allowed": False,
                "promotion_allowed": False,
            }
        )

        packet = build_factor_mining_candidate_plan_gate(plan, gate_stage="discovery")

        self.assertTrue(packet["decision"]["candidate_plan_gate_cleared"])
        self.assertEqual(packet["summary"]["active_candidate_count"], 1)
        self.assertEqual(packet["summary"]["inactive_candidate_count"], 1)
        inactive = next(row for row in packet["candidate_rows"] if row["factor_name"] == "pit_forecast_profit_revision_event_1q")
        self.assertFalse(inactive["active_for_gate"])

    def test_write_and_validate_candidate_plan_gate_packet(self) -> None:
        packet = build_factor_mining_candidate_plan_gate(_candidate_plan(), gate_stage="discovery")

        with tempfile.TemporaryDirectory() as tmp:
            write_factor_mining_candidate_plan_gate(tmp, packet)
            path = Path(tmp) / "factor_mining_candidate_plan_gate.json"
            loaded = validate_candidate_plan_gate_packet(path)

        self.assertEqual(loaded["status"], "research_ready")
        self.assertTrue(loaded["decision"]["candidate_plan_gate_cleared"])

    def test_blocks_active_candidate_without_hypothesis_source(self) -> None:
        plan = _candidate_plan()
        del plan["candidates"][0]["hypothesis_source"]

        packet = build_factor_mining_candidate_plan_gate(plan, gate_stage="discovery")

        self.assertEqual(packet["status"], "blocked")
        self.assertIn("candidate_missing_hypothesis_source", packet["decision"]["blockers"])

    def test_blocks_hibernated_candidate_family_before_new_screening(self) -> None:
        plan = _candidate_plan()
        plan["family_rotation_policy"] = {
            "hibernated_families": [
                {"family": "max_effect_reversal", "reason": "prior long-cycle validation rejected standalone alpha"}
            ],
            "blocked_families": [],
            "current_family_id": "max_effect_reversal",
            "current_family_round_count": 1,
            "max_rounds_before_review": 3,
            "three_round_review_completed": True,
        }

        packet = build_factor_mining_candidate_plan_gate(plan, gate_stage="discovery")

        self.assertEqual(packet["status"], "blocked")
        self.assertIn("candidate_family_hibernated:max_effect_reversal", packet["decision"]["blockers"])
        rotation = packet["family_rotation_policy"]
        self.assertIn("max_effect_reversal", rotation["hibernated_families"])

    def test_requires_three_round_review_when_family_round_budget_is_used(self) -> None:
        plan = _candidate_plan()
        plan["family_rotation_policy"] = {
            "hibernated_families": [],
            "blocked_families": [],
            "current_family_id": "max_effect_reversal",
            "current_family_round_count": 3,
            "max_rounds_before_review": 3,
            "three_round_review_completed": False,
        }

        packet = build_factor_mining_candidate_plan_gate(plan, gate_stage="discovery")

        self.assertEqual(packet["status"], "blocked")
        self.assertIn("family_rotation_review_required_after_round_limit", packet["decision"]["blockers"])

    def test_blocks_missing_strict_promotion_policy_requirements(self) -> None:
        plan = _candidate_plan()
        for key in (
            "requires_no_lookahead_audit",
            "requires_final_holdout_read_once",
            "requires_industry_style_neutralization",
            "requires_source_performance_evidence",
        ):
            del plan["promotion_policy"][key]

        packet = build_factor_mining_candidate_plan_gate(plan, gate_stage="discovery")

        self.assertEqual(packet["status"], "blocked")
        blockers = packet["decision"]["blockers"]
        self.assertIn("promotion_policy_missing:requires_no_lookahead_audit", blockers)
        self.assertIn("promotion_policy_missing:requires_final_holdout_read_once", blockers)
        self.assertIn("promotion_policy_missing:requires_industry_style_neutralization", blockers)
        self.assertIn("promotion_policy_missing:requires_source_performance_evidence", blockers)

    def test_markdown_lists_strict_promotion_policy_requirements(self) -> None:
        packet = build_factor_mining_candidate_plan_gate(_candidate_plan(), gate_stage="discovery")

        markdown = packet["markdown"]

        self.assertIn("requires_no_lookahead_audit", markdown)
        self.assertIn("requires_parameter_sensitivity", markdown)
        self.assertIn("requires_source_performance_evidence", markdown)


if __name__ == "__main__":
    unittest.main()
