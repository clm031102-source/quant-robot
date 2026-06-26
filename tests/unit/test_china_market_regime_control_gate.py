import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.china_market_regime_control_gate import (
    build_china_market_regime_control_gate,
    render_china_market_regime_control_gate_markdown,
    write_china_market_regime_control_gate,
)


class ChinaMarketRegimeControlGateTests(unittest.TestCase):
    def test_passes_when_all_regime_controls_are_pit_and_not_alpha_claims(self) -> None:
        result = build_china_market_regime_control_gate(_policy())

        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["summary"]["implemented_controls"], 4)
        self.assertEqual(result["summary"]["blocked_alpha_claim_controls"], 0)
        self.assertTrue(result["promotion_policy"]["regime_controls_allowed_for_stratification"])
        self.assertFalse(result["promotion_policy"]["standalone_regime_alpha_claim_allowed"])

    def test_blocks_missing_available_date_and_alpha_claims(self) -> None:
        policy = _policy()
        policy["controls"][0]["available_date_required"] = False
        policy["controls"][1]["standalone_alpha_claim_allowed"] = True

        result = build_china_market_regime_control_gate(policy)

        self.assertFalse(result["summary"]["passes"])
        self.assertIn("missing_available_date_required:policy_liquidity_regime", result["summary"]["blockers"])
        self.assertIn("standalone_alpha_claim_allowed:credit_cycle_proxy", result["summary"]["blockers"])

    def test_write_outputs(self) -> None:
        result = build_china_market_regime_control_gate(_policy())
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "gate"

            write_china_market_regime_control_gate(output_dir, result)

            self.assertTrue((output_dir / "china_market_regime_control_gate.json").exists())
            self.assertTrue((output_dir / "china_market_regime_control_gate.md").exists())
            self.assertTrue((output_dir / "control_rows.csv").exists())
            markdown = render_china_market_regime_control_gate_markdown(result)
            self.assertIn("China Market Regime Control Gate", markdown)
            self.assertIn("Implemented controls: 4", markdown)


def _policy() -> dict[str, object]:
    return {
        "scope_id": "cn_stock_china_market_regime_controls",
        "controls": [
            {
                "control_id": "policy_liquidity_regime",
                "dataset_refs": ["processed/external_macro_rates"],
                "usable_fields": ["shibor_on", "shibor_1w", "shibor_1m", "shibor_3m", "shibor_1y"],
                "blocked_fields": ["lpr_1y", "lpr_5y"],
                "available_date_required": True,
                "pit_join_required": True,
                "standalone_alpha_claim_allowed": False,
            },
            {
                "control_id": "credit_cycle_proxy",
                "dataset_refs": ["processed/external_margin_detail"],
                "usable_fields": ["rzye", "rzmre", "rzrqye"],
                "blocked_fields": [],
                "available_date_required": True,
                "pit_join_required": True,
                "standalone_alpha_claim_allowed": False,
            },
            {
                "control_id": "northbound_margin_turnover_temperature",
                "dataset_refs": ["processed/external_hk_hold", "processed/external_hsgt_flow"],
                "usable_fields": ["hold_vol", "hold_ratio", "north_money"],
                "blocked_fields": [],
                "available_date_required": True,
                "pit_join_required": True,
                "standalone_alpha_claim_allowed": False,
            },
            {
                "control_id": "index_location_state",
                "dataset_refs": ["processed/external_index_state"],
                "usable_fields": ["close", "turnover_rate", "pe", "pe_ttm", "pb"],
                "blocked_fields": [],
                "available_date_required": True,
                "pit_join_required": True,
                "standalone_alpha_claim_allowed": False,
            },
        ],
    }


if __name__ == "__main__":
    unittest.main()
