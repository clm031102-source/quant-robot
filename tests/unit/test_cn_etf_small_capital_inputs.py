from __future__ import annotations

import json
import unittest
from pathlib import Path

from quant_robot.ops.cn_etf_small_capital_inputs import SmallCapitalInputs


class CnEtfSmallCapitalInputsTests(unittest.TestCase):
    def test_round_trip_costs_cover_base_and_minimum_fee_stress(self):
        inputs = SmallCapitalInputs.from_mapping(_inputs())

        self.assertAlmostEqual(inputs.round_trip_cost_bps(3000, minimum_fee_cny=0), 21.0)
        self.assertAlmostEqual(
            inputs.round_trip_cost_bps(3000, minimum_fee_cny=5),
            53.333333333333336,
        )
        self.assertAlmostEqual(inputs.round_trip_cost_bps(1000, minimum_fee_cny=5), 120.0)

    def test_config_matches_frozen_operator_inputs(self):
        payload = json.loads(
            Path("configs/cn_etf_small_capital_inputs_20260729.json").read_text(
                encoding="utf-8"
            )
        )

        inputs = SmallCapitalInputs.from_mapping(payload)

        self.assertEqual(inputs.minimum_capital_cny, 1000)
        self.assertEqual(inputs.maximum_capital_cny, 3000)
        self.assertEqual(inputs.max_holding_sessions, 252)
        self.assertEqual(inputs.minimum_paper_days, 20)
        self.assertEqual(inputs.minimum_paper_fills, 30)
        self.assertEqual(inputs.minimum_market_regimes, 2)

    def test_rejects_capital_drawdown_and_holding_drift(self):
        payload = _inputs()
        payload["capital_cny"]["minimum"] = 999
        with self.assertRaisesRegex(ValueError, "capital"):
            SmallCapitalInputs.from_mapping(payload)

        payload = _inputs()
        payload["absolute_max_drawdown"] = 0.41
        with self.assertRaisesRegex(ValueError, "absolute_max_drawdown"):
            SmallCapitalInputs.from_mapping(payload)

        payload = _inputs()
        payload["paper_promotion_max_drawdown"] = 0.09
        with self.assertRaisesRegex(ValueError, "paper_promotion_max_drawdown"):
            SmallCapitalInputs.from_mapping(payload)

        payload = _inputs()
        payload["max_holding_sessions"] = 0
        with self.assertRaisesRegex(ValueError, "max_holding_sessions"):
            SmallCapitalInputs.from_mapping(payload)

    def test_rejects_any_enabled_external_execution_boundary(self):
        for key in _inputs()["boundaries"]:
            with self.subTest(key=key):
                payload = _inputs()
                payload["boundaries"][key] = True
                with self.assertRaisesRegex(ValueError, key):
                    SmallCapitalInputs.from_mapping(payload)

    def test_round_trip_cost_rejects_invalid_notional_or_minimum_fee(self):
        inputs = SmallCapitalInputs.from_mapping(_inputs())

        with self.assertRaisesRegex(ValueError, "notional"):
            inputs.round_trip_cost_bps(0)
        with self.assertRaisesRegex(ValueError, "minimum_fee"):
            inputs.round_trip_cost_bps(1000, minimum_fee_cny=-1)


def _inputs():
    return {
        "schema_version": 1,
        "as_of_date": "2026-07-29",
        "capital_cny": {"minimum": 1000, "maximum": 3000},
        "commission_bps_per_side": 0.5,
        "slippage_bps_per_side": 10.0,
        "minimum_commission_cny_stress": 5.0,
        "absolute_max_drawdown": 0.4,
        "paper_promotion_max_drawdown": 0.08,
        "max_holding_sessions": 252,
        "max_single_position_cny": 1000,
        "max_daily_loss_cny": 60,
        "max_one_way_adv_participation": 0.01,
        "minimum_paper_days": 20,
        "minimum_paper_fills": 30,
        "minimum_market_regimes": 2,
        "boundaries": {
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "live_boundary_allowed": False,
        },
    }


if __name__ == "__main__":
    unittest.main()
