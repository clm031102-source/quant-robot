import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.cn_stock_family_rotation_decision import (
    EXPECTED_STARTUP_NEXT_DIRECTION,
    NEXT_PREREGISTRATION_DIRECTION,
    build_cn_stock_family_rotation_decision,
    write_cn_stock_family_rotation_decision,
)

ROUND218_NEXT_DIRECTION = "round218_family_rotation_after_profitability_quality_stratified_failure"
ROUND219_PREREGISTRATION_DIRECTION = "round219_public_trend_strength_state_preregistration"
ROUND219_SELECTED_FAMILY = "public_trend_strength_state_residual"
ROUND219_REQUIRED_CONTROLS = [
    "public_formula_source_registered",
    "no_same_day_forward_label_leakage",
    "tradeability_mask_required",
    "industry_style_residual_evaluation",
    "reference_dedup_against_rsrs_supertrend_bollinger_donchian",
    "multiple_testing_accounting",
    "no_portfolio_grid_before_ic_shape_residual_prescreen",
    "china_regime_coverage_required",
]


def _startup_packet() -> dict:
    return {
        "status": "cleared",
        "repeatable_mining_protocol": {
            "source_audit": "docs/research/cn_stock_cn_tradeability_limit_event_proxy_prescreen_round160_2026-06-23.md",
            "next_direction": EXPECTED_STARTUP_NEXT_DIRECTION,
            "recently_rejected_directions": [
                "tradeability_limit_event_portfolio_grid_after_round160_zero_proxy_leads",
                "price_volume_shock_reversal_parameter_tuning_after_round158_zero_residual_leads",
                "public_rsrs_parameter_tuning_after_neutral_dedup_failure",
                "profitability_event_revision_portfolio_grid_after_zero_neutral_leads",
                "industry_breadth_bridge_as_standalone_promotion_candidate",
            ],
        },
    }


def _round218_startup_packet() -> dict:
    return {
        "status": "cleared",
        "repeatable_mining_protocol": {
            "source_audit": "docs/research/cn_stock_round218_method_control_startup_gate_optimization_2026-06-24.md",
            "next_direction": ROUND218_NEXT_DIRECTION,
            "recently_rejected_directions": [
                "profitability_quality_formula_tuning_after_round217_zero_fdr_leads",
                "direct_event_factor_standalone_alpha_after_residual_dedup_failure",
                "standalone_valuation_reversion_after_residual_ic_collapse",
                "external_northbound_crowding_after_zero_long_cycle_leads",
            ],
        },
    }


def _round219_family_candidates() -> list[dict]:
    return [
        {
            "family_id": ROUND219_SELECTED_FAMILY,
            "status": "eligible",
            "score": 89,
            "data_readiness": "ready_from_adjusted_ohlcv_and_tradeability_masks",
            "novelty_vs_recent_failures": "public_state_indicators_not_rsrs_supertrend_or_52w_reuse",
            "public_reference_tags": ["ADX", "KAMA", "Aroon", "Choppiness", "WilliamsR"],
            "required_controls": ROUND219_REQUIRED_CONTROLS,
            "reason": (
                "Uses public trend-strength and range-state formulas as lagged state variables, then screens "
                "residual cross-sectional IC before any portfolio grid."
            ),
            "next_action": ROUND219_PREREGISTRATION_DIRECTION,
        },
        {
            "family_id": "direct_profitability_quality_formula_tuning",
            "status": "hibernated",
            "score": 0,
            "data_readiness": "tested",
            "novelty_vs_recent_failures": "failed_round217",
            "reason": "Round217 produced zero Bonferroni/FDR leads across full profitability-quality shards.",
            "next_action": "do_not_tune_direct_formula_family_before_new_mechanism",
        },
    ]


def _round219_candidate_seed() -> dict:
    return {
        "family": ROUND219_SELECTED_FAMILY,
        "next_direction": ROUND219_PREREGISTRATION_DIRECTION,
        "mechanism": "Lagged public trend-strength state gates residual cross-sectional stock selection.",
        "candidate_ideas": [
            "adx_trend_strength_exhaustion_reversal_14_20",
            "adx_choppiness_mean_reversion_quality_14_20",
            "kama_efficiency_trend_decay_10_30",
            "aroon_range_exhaustion_reversal_25_20",
            "williams_range_failure_reversal_14_20",
            "trend_strength_state_residual_composite_20",
        ],
        "mandatory_controls": ROUND219_REQUIRED_CONTROLS,
        "promotion_policy": {
            "portfolio_grid_allowed_before_residual_prescreen": False,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
        },
    }


class CNStockFamilyRotationDecisionTests(unittest.TestCase):
    def test_selects_china_regime_temperature_and_freezes_failed_families(self) -> None:
        result = build_cn_stock_family_rotation_decision(_startup_packet())

        self.assertEqual(result["stage"], "cn_stock_family_rotation_decision")
        self.assertEqual(result["decision"]["selected_family"], "china_market_regime_temperature_interaction")
        self.assertEqual(result["decision"]["next_direction"], NEXT_PREREGISTRATION_DIRECTION)
        self.assertTrue(result["decision"]["rotation_decision_cleared"])
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])
        frozen = {row["family_id"] for row in result["family_rows"] if row["status"] == "hibernated"}
        self.assertIn("tradeability_limit_events", frozen)
        self.assertIn("industry_relative_strength_breadth_bridge", frozen)
        self.assertIn("pit_profitability_event_revision", frozen)
        selected = next(row for row in result["family_rows"] if row["status"] == "selected_for_preregistration")
        self.assertIn("lagged_market_temperature_state", selected["required_controls"])
        self.assertIn("industry_style_residual_evaluation", selected["required_controls"])

    def test_blocks_when_startup_gate_has_not_absorbed_round160_failure(self) -> None:
        startup = _startup_packet()
        startup["repeatable_mining_protocol"]["next_direction"] = "round160_cn_tradeability_limit_event_proxy_prescreen"

        result = build_cn_stock_family_rotation_decision(startup)

        self.assertFalse(result["decision"]["rotation_decision_cleared"])
        self.assertIn("startup_gate_not_pointing_to_round161_rotation", result["decision"]["blockers"])

    def test_blocks_when_selected_family_reuses_hibernated_tradeability_line(self) -> None:
        result = build_cn_stock_family_rotation_decision(
            _startup_packet(),
            selected_family_id="tradeability_limit_events",
        )

        self.assertFalse(result["decision"]["rotation_decision_cleared"])
        self.assertIn("selected_family_is_hibernated:tradeability_limit_events", result["decision"]["blockers"])

    def test_accepts_custom_rotation_policy_after_round218_review(self) -> None:
        result = build_cn_stock_family_rotation_decision(
            _round218_startup_packet(),
            expected_startup_next_direction=ROUND218_NEXT_DIRECTION,
            selected_family_id=ROUND219_SELECTED_FAMILY,
            next_preregistration_direction=ROUND219_PREREGISTRATION_DIRECTION,
            selected_required_controls=ROUND219_REQUIRED_CONTROLS,
            family_candidates=_round219_family_candidates(),
            candidate_plan_seed=_round219_candidate_seed(),
        )

        self.assertTrue(result["decision"]["rotation_decision_cleared"])
        self.assertEqual(result["decision"]["selected_family"], ROUND219_SELECTED_FAMILY)
        self.assertEqual(result["decision"]["next_direction"], ROUND219_PREREGISTRATION_DIRECTION)
        self.assertEqual(result["candidate_plan_seed"]["family"], ROUND219_SELECTED_FAMILY)
        selected = next(row for row in result["family_rows"] if row["family_id"] == ROUND219_SELECTED_FAMILY)
        self.assertEqual(selected["status"], "selected_for_preregistration")
        self.assertIn("public_formula_source_registered", selected["required_controls"])
        self.assertIn("reference_dedup_against_rsrs_supertrend_bollinger_donchian", selected["required_controls"])

    def test_custom_rotation_policy_reports_expected_direction_blocker(self) -> None:
        startup = _round218_startup_packet()
        startup["repeatable_mining_protocol"]["next_direction"] = "round218_stale_direction"

        result = build_cn_stock_family_rotation_decision(
            startup,
            expected_startup_next_direction=ROUND218_NEXT_DIRECTION,
            selected_family_id=ROUND219_SELECTED_FAMILY,
            next_preregistration_direction=ROUND219_PREREGISTRATION_DIRECTION,
            selected_required_controls=ROUND219_REQUIRED_CONTROLS,
            family_candidates=_round219_family_candidates(),
            candidate_plan_seed=_round219_candidate_seed(),
        )

        self.assertFalse(result["decision"]["rotation_decision_cleared"])
        self.assertIn(
            f"startup_gate_not_pointing_to:{ROUND218_NEXT_DIRECTION}",
            result["decision"]["blockers"],
        )

    def test_write_outputs_json_markdown_and_family_csv(self) -> None:
        result = build_cn_stock_family_rotation_decision(_startup_packet())

        with tempfile.TemporaryDirectory() as tmp:
            write_cn_stock_family_rotation_decision(tmp, result)
            root = Path(tmp)
            self.assertTrue((root / "cn_stock_family_rotation_decision.json").exists())
            self.assertTrue((root / "cn_stock_family_rotation_decision.md").exists())
            self.assertTrue((root / "cn_stock_family_rotation_family_rows.csv").exists())
            payload = json.loads((root / "cn_stock_family_rotation_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["decision"]["next_direction"], NEXT_PREREGISTRATION_DIRECTION)


if __name__ == "__main__":
    unittest.main()
