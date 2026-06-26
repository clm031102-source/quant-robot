import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.cn_stock_family_rotation_decision import EXPECTED_STARTUP_NEXT_DIRECTION
from scripts.run_cn_stock_family_rotation_decision import run_cn_stock_family_rotation_decision

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


class CNStockFamilyRotationDecisionCliTests(unittest.TestCase):
    def test_cli_writes_rotation_decision_from_startup_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            startup_path = root / "startup_gate.json"
            output_dir = root / "rotation"
            startup_path.write_text(
                json.dumps(
                    {
                        "status": "cleared",
                        "repeatable_mining_protocol": {
                            "source_audit": "round160.md",
                            "next_direction": EXPECTED_STARTUP_NEXT_DIRECTION,
                            "recently_rejected_directions": [
                                "tradeability_limit_event_portfolio_grid_after_round160_zero_proxy_leads"
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = run_cn_stock_family_rotation_decision(
                startup_gate=startup_path,
                output_dir=output_dir,
            )

            self.assertTrue(result["decision"]["rotation_decision_cleared"])
            self.assertTrue((output_dir / "cn_stock_family_rotation_decision.json").exists())
            self.assertTrue((output_dir / "cn_stock_family_rotation_decision.md").exists())

    def test_cli_accepts_custom_round218_family_rotation_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            startup_path = root / "startup_gate.json"
            family_path = root / "family_candidates.json"
            seed_path = root / "candidate_seed.json"
            output_dir = root / "rotation"
            startup_path.write_text(
                json.dumps(
                    {
                        "status": "cleared",
                        "repeatable_mining_protocol": {
                            "source_audit": "round218.md",
                            "next_direction": ROUND218_NEXT_DIRECTION,
                            "recently_rejected_directions": [
                                "profitability_quality_formula_tuning_after_round217_zero_fdr_leads"
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )
            family_path.write_text(
                json.dumps(
                    [
                        {
                            "family_id": ROUND219_SELECTED_FAMILY,
                            "status": "eligible",
                            "score": 89,
                            "data_readiness": "ready_from_adjusted_ohlcv_and_tradeability_masks",
                            "novelty_vs_recent_failures": "public_state_indicators_not_rsrs_supertrend_or_52w_reuse",
                            "public_reference_tags": ["ADX", "KAMA", "Aroon", "Choppiness", "WilliamsR"],
                            "required_controls": ROUND219_REQUIRED_CONTROLS,
                            "reason": "Lagged public trend-strength state with residual IC pre-screen.",
                            "next_action": ROUND219_PREREGISTRATION_DIRECTION,
                        },
                        {
                            "family_id": "direct_profitability_quality_formula_tuning",
                            "status": "hibernated",
                            "score": 0,
                            "data_readiness": "tested",
                            "novelty_vs_recent_failures": "failed_round217",
                            "reason": "Round217 produced zero FDR leads.",
                            "next_action": "do_not_reopen_without_new_mechanism",
                        },
                    ]
                ),
                encoding="utf-8",
            )
            seed_path.write_text(
                json.dumps(
                    {
                        "family": ROUND219_SELECTED_FAMILY,
                        "next_direction": ROUND219_PREREGISTRATION_DIRECTION,
                        "candidate_ideas": [
                            "adx_trend_strength_exhaustion_reversal_14_20",
                            "kama_efficiency_trend_decay_10_30",
                        ],
                        "mandatory_controls": ROUND219_REQUIRED_CONTROLS,
                    }
                ),
                encoding="utf-8",
            )

            result = run_cn_stock_family_rotation_decision(
                startup_gate=startup_path,
                output_dir=output_dir,
                selected_family_id=ROUND219_SELECTED_FAMILY,
                expected_startup_next_direction=ROUND218_NEXT_DIRECTION,
                next_preregistration_direction=ROUND219_PREREGISTRATION_DIRECTION,
                selected_required_controls=ROUND219_REQUIRED_CONTROLS,
                family_candidates_json=family_path,
                candidate_plan_seed_json=seed_path,
            )

            self.assertTrue(result["decision"]["rotation_decision_cleared"])
            self.assertEqual(result["decision"]["selected_family"], ROUND219_SELECTED_FAMILY)
            self.assertEqual(result["decision"]["next_direction"], ROUND219_PREREGISTRATION_DIRECTION)
            self.assertEqual(result["candidate_plan_seed"]["family"], ROUND219_SELECTED_FAMILY)


if __name__ == "__main__":
    unittest.main()
