import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.round266_direction_optimization_gate import (
    ROUND266_NEXT_DIRECTION,
    SELECTED_DIRECTION_ID,
    build_round266_direction_optimization_gate,
    write_round266_direction_optimization_gate,
)


def _startup_packet() -> dict:
    return {
        "status": "cleared",
        "repeatable_mining_protocol": {
            "source_audit": "docs/research/cn_stock_round265_public_tradeable_indicator_composite_residual_prescreen_2026-06-26.md",
            "next_direction": "round266_rotate_after_public_tradeable_indicator_composite_residual_prescreen_failure",
            "recently_rejected_directions": [
                "round265_public_tradeable_indicator_composite_parameter_tuning_after_zero_residual_leads",
                "round263_recovering_historical_leads_after_zero_recovery_candidates",
            ],
        },
        "round_state": {
            "last_completed_round": 265,
            "next_round": 266,
            "family_rotation_required": True,
            "next_direction": "round266_rotate_after_public_tradeable_indicator_composite_residual_prescreen_failure",
            "blocked_reentry_families": [
                "public_tradeable_indicator_composite_after_round265_zero_residual_leads",
                "low_turnover_repair_parameter_grid_after_round126_zero_walkforward_candidates",
                "daily_basic_direct_portfolio_grid_after_round257_zero_strict_research_leads",
            ],
            "required_before_next_round": [
                "round266_rotate_to_new_orthogonal_family_required",
                "round266_candidate_plan_gate_required_before_any_prescreen",
            ],
        },
    }


class Round266DirectionOptimizationGateTests(unittest.TestCase):
    def test_clears_control_implementation_direction_and_blocks_direct_factor_generation(self) -> None:
        result = build_round266_direction_optimization_gate(_startup_packet())

        self.assertEqual(result["stage"], "round266_direction_optimization_gate")
        self.assertEqual(result["round"], 266)
        self.assertTrue(result["decision"]["direction_gate_cleared"])
        self.assertEqual(result["decision"]["selected_direction"], SELECTED_DIRECTION_ID)
        self.assertEqual(result["decision"]["next_direction"], ROUND266_NEXT_DIRECTION)
        self.assertFalse(result["decision"]["direct_factor_generation_allowed"])
        self.assertTrue(result["decision"]["candidate_plan_required_before_prescreen"])
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])
        self.assertGreaterEqual(result["summary"]["method_area_count"], 8)
        self.assertGreaterEqual(result["summary"]["blocked_or_hibernated_direction_count"], 10)
        self.assertIn(
            "public_tradeable_indicator_composite",
            {row["direction_id"] for row in result["direction_rows"] if row["status"] == "hibernated"},
        )
        self.assertIn("a_share_real_tradeability", {row["area_id"] for row in result["method_area_rows"]})
        self.assertIn("strict_statistics", {row["area_id"] for row in result["method_area_rows"]})

    def test_blocks_stale_startup_round(self) -> None:
        startup = _startup_packet()
        startup["round_state"]["next_round"] = 265

        result = build_round266_direction_optimization_gate(startup)

        self.assertFalse(result["decision"]["direction_gate_cleared"])
        self.assertIn("startup_round_state_not_round266", result["decision"]["blockers"])

    def test_blocks_reentry_into_hibernated_family(self) -> None:
        result = build_round266_direction_optimization_gate(
            _startup_packet(),
            selected_direction_id="public_tradeable_indicator_composite",
        )

        self.assertFalse(result["decision"]["direction_gate_cleared"])
        self.assertIn(
            "selected_direction_not_eligible:public_tradeable_indicator_composite",
            result["decision"]["blockers"],
        )

    def test_writer_outputs_json_markdown_and_direction_csv(self) -> None:
        result = build_round266_direction_optimization_gate(_startup_packet())

        with tempfile.TemporaryDirectory() as tmp:
            write_round266_direction_optimization_gate(tmp, result)
            root = Path(tmp)
            self.assertTrue((root / "round266_direction_optimization_gate.json").exists())
            self.assertTrue((root / "round266_direction_optimization_gate.md").exists())
            self.assertTrue((root / "round266_direction_rows.csv").exists())
            payload = json.loads((root / "round266_direction_optimization_gate.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["decision"]["next_direction"], ROUND266_NEXT_DIRECTION)


if __name__ == "__main__":
    unittest.main()
