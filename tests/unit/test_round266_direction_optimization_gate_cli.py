import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_round266_direction_optimization_gate import run_round266_direction_optimization_gate_cli


def _startup_packet() -> dict:
    return {
        "status": "cleared",
        "repeatable_mining_protocol": {
            "source_audit": "docs/research/cn_stock_round265_public_tradeable_indicator_composite_residual_prescreen_2026-06-26.md",
            "next_direction": "round266_rotate_after_public_tradeable_indicator_composite_residual_prescreen_failure",
            "recently_rejected_directions": [
                "round265_public_tradeable_indicator_composite_parameter_tuning_after_zero_residual_leads",
            ],
        },
        "round_state": {
            "last_completed_round": 265,
            "next_round": 266,
            "family_rotation_required": True,
            "next_direction": "round266_rotate_after_public_tradeable_indicator_composite_residual_prescreen_failure",
            "required_before_next_round": [
                "round266_rotate_to_new_orthogonal_family_required",
                "round266_candidate_plan_gate_required_before_any_prescreen",
            ],
        },
    }


class Round266DirectionOptimizationGateCliTests(unittest.TestCase):
    def test_cli_writes_round266_gate_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            startup = root / "startup.json"
            output = root / "out"
            startup.write_text(json.dumps(_startup_packet()), encoding="utf-8")

            result = run_round266_direction_optimization_gate_cli(startup_gate=startup, output_dir=output)

            self.assertTrue(result["decision"]["direction_gate_cleared"])
            self.assertTrue((output / "round266_direction_optimization_gate.json").exists())
            self.assertTrue((output / "round266_direction_optimization_gate.md").exists())
            self.assertTrue((output / "round266_direction_rows.csv").exists())

    def test_cli_raises_when_direction_gate_is_blocked(self) -> None:
        packet = _startup_packet()
        packet["round_state"]["next_round"] = 265
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            startup = root / "startup.json"
            startup.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "startup_round_state_not_round266"):
                run_round266_direction_optimization_gate_cli(startup_gate=startup, output_dir=root / "out")


if __name__ == "__main__":
    unittest.main()
