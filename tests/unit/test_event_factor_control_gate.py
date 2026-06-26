import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.event_factor_control_gate import (
    build_event_factor_control_gate,
    render_event_factor_control_gate_markdown,
    write_event_factor_control_gate,
)


class EventFactorControlGateTests(unittest.TestCase):
    def test_passes_when_event_controls_are_closed_without_alpha_claims(self) -> None:
        result = build_event_factor_control_gate(_policy())

        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["closed_controls"], 3)
        self.assertEqual(result["summary"]["hibernated_controls"], 1)
        self.assertEqual(result["summary"]["coverage_blocked_controls"], 1)
        self.assertTrue(result["promotion_policy"]["non_event_direct_factor_generation_allowed"])
        self.assertFalse(result["promotion_policy"]["event_factor_portfolio_grid_allowed"])
        self.assertFalse(result["promotion_policy"]["standalone_event_alpha_claim_allowed"])

    def test_blocks_missing_pit_neutral_audit_or_alpha_claims(self) -> None:
        policy = _policy()
        policy["controls"][0]["pit_signal_date_audit_required"] = False
        policy["controls"][1]["neutralized_ic_audit_required"] = False
        policy["controls"][2]["standalone_alpha_claim_allowed"] = True

        result = build_event_factor_control_gate(policy)

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("missing_pit_signal_date_audit:earnings_forecast_events", result["summary"]["blockers"])
        self.assertIn("missing_neutralized_ic_audit:dividend_ex_right_events", result["summary"]["blockers"])
        self.assertIn(
            "standalone_event_alpha_claim_allowed:buyback_holder_change_unlock_events",
            result["summary"]["blockers"],
        )

    def test_blocked_endpoints_must_disable_family_mining(self) -> None:
        policy = _policy()
        policy["controls"][2]["blocked_endpoints"] = ["share_float", "pledge_stat"]
        policy["controls"][2]["family_mining_allowed"] = True

        result = build_event_factor_control_gate(policy)

        self.assertFalse(result["summary"]["passes"])
        self.assertIn(
            "blocked_endpoints_must_block_family:buyback_holder_change_unlock_events",
            result["summary"]["blockers"],
        )

    def test_write_outputs(self) -> None:
        result = build_event_factor_control_gate(_policy())
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "gate"

            write_event_factor_control_gate(output_dir, result)

            self.assertTrue((output_dir / "event_factor_control_gate.json").exists())
            self.assertTrue((output_dir / "event_control_rows.csv").exists())
            markdown = render_event_factor_control_gate_markdown(result)
            self.assertIn("Event Factor Control Gate", markdown)
            self.assertIn("Closed controls: 3", markdown)


def _policy() -> dict[str, object]:
    return {
        "scope_id": "cn_stock_event_factor_controls",
        "controls": [
            {
                "control_id": "earnings_forecast_events",
                "dataset_refs": ["reports/round146_event_factor_preregistration", "reports/round147_pit_ic_prescreen"],
                "usable_endpoints": ["forecast"],
                "blocked_endpoints": [],
                "control_action": "hibernate",
                "family_mining_allowed": False,
                "pit_signal_date_audit_required": True,
                "neutralized_ic_audit_required": True,
                "standalone_alpha_claim_allowed": False,
                "evidence": "Forecast events were PIT-tested and weak/negative after neutralized IC checks.",
                "next_action": "Retest only under a new preregistered orthogonal event hypothesis.",
            },
            {
                "control_id": "dividend_ex_right_events",
                "dataset_refs": ["reports/round146_event_factor_preregistration", "reports/round148_neutral_dedup"],
                "usable_endpoints": ["dividend"],
                "blocked_endpoints": [],
                "control_action": "controlled_retest_only",
                "family_mining_allowed": False,
                "pit_signal_date_audit_required": True,
                "neutralized_ic_audit_required": True,
                "standalone_alpha_claim_allowed": False,
                "evidence": "Dividend lead was redundant to public yield/value exposure after residualization.",
                "next_action": "Use only with public-yield residualization and yearly stability checks.",
            },
            {
                "control_id": "buyback_holder_change_unlock_events",
                "dataset_refs": ["reports/round146_event_factor_preregistration", "reports/round147_pit_ic_prescreen"],
                "usable_endpoints": ["repurchase", "holder_number", "top_holder"],
                "blocked_endpoints": ["share_float", "pledge_stat"],
                "control_action": "coverage_blocked",
                "family_mining_allowed": False,
                "pit_signal_date_audit_required": True,
                "neutralized_ic_audit_required": True,
                "standalone_alpha_claim_allowed": False,
                "evidence": "Usable event endpoints were weak; missing endpoints have 0-row coverage.",
                "next_action": "Backfill missing endpoints before re-entering this event family.",
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
