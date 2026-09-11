import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.paper.simulator import _apply_fills, _simulate_fills
from scripts.run_paper_simulation import run_simulation
from scripts.run_paper_batch import load_paper_batch_config, _run_profile_attempt
from scripts.run_paper_profile_optimizer import load_paper_profile_optimizer_config


def intent(asset, quantity):
    return {
        "intent_id": asset,
        "asset_id": asset,
        "market": "CN_ETF",
        "side": "buy" if quantity > 0 else "sell",
        "signed_quantity": quantity,
        "signal_date": "2024-01-02",
        "execution_date": "2024-01-03",
    }


class PaperMinimumCommissionTests(unittest.TestCase):
    def fills(self, quantities, cash, *, commission_bps=0.5, impact_bps=0):
        intents = [intent(asset, quantity) for asset, quantity in quantities.items()]
        prices = pd.DataFrame([
            {"asset_id": asset, "market": "CN_ETF", "latest_price": 1.0,
             "volume": 100000, "amount": 100000}
            for asset in quantities
        ])
        return _simulate_fills(
            intents, prices, commission_bps, 0, impact_bps, 0.01 if impact_bps else None,
            cash, minimum_commission=5,
        )[0]

    def test_buy_preserves_largest_affordable_lot_after_minimum_commission(self):
        for cash, quantity in [(1005, 1000), (1004, 900), (105, 100), (104, 0)]:
            with self.subTest(cash=cash):
                fills = self.fills({"ETF": 1000}, cash)
                self.assertEqual(sum(row["quantity"] for row in fills), quantity)
                positions = {}
                ending_cash = _apply_fills(positions, cash, fills)
                self.assertAlmostEqual(ending_cash, cash - quantity - (5 if quantity else 0))
                self.assertGreaterEqual(ending_cash, 0)

    def test_sells_then_buys_charge_once_per_order_and_conserve_cash(self):
        fills = self.fills({"BUY": 1000, "SELL": -1000}, 10)
        self.assertEqual([row["side"] for row in fills], ["sell", "buy"])
        self.assertEqual([row["commission_fee"] for row in fills], [5, 5])
        positions = {"SELL": 1000}
        cash = _apply_fills(positions, 10, fills)
        self.assertAlmostEqual(cash, 0)
        self.assertEqual(positions.get("BUY"), 1000)
        self.assertEqual(positions.get("SELL", 0), 0)

    def test_proportional_commission_can_exceed_minimum(self):
        fills = self.fills({"ETF": 100000}, 100010, commission_bps=1)
        self.assertEqual(fills[0]["quantity"], 100000)
        self.assertEqual(fills[0]["commission_fee"], 10)

    def test_affordability_recomputes_impact_at_the_final_quantity(self):
        fills = self.fills({"ETF": 1000}, 1005, impact_bps=10)
        self.assertEqual(fills[0]["quantity"], 900)
        self.assertEqual(fills[0]["commission_fee"], 5)
        self.assertAlmostEqual(fills[0]["market_impact_fee"], 0.81)
        self.assertAlmostEqual(_apply_fills({}, 1005, fills), 99.19)

    def test_no_fill_has_no_minimum_charge(self):
        self.assertEqual(self.fills({"ETF": 0}, 1000), [])

    def test_sell_cannot_borrow_cash_to_pay_its_minimum_commission(self):
        prices = pd.DataFrame([{"asset_id": "ETF", "market": "CN_ETF", "latest_price": 0.04}])
        for cash, count in [(0, 0), (1, 1)]:
            with self.subTest(cash=cash):
                fills, events = _simulate_fills(
                    [intent("ETF", -100)], prices, 0.5, 0, 0, None, cash, minimum_commission=5,
                )
                self.assertEqual(len(fills), count)
                self.assertGreaterEqual(_apply_fills({"ETF": 100}, cash, fills), 0)
                if not count:
                    self.assertEqual(events[0]["reason"], "insufficient_cash_for_fees")

    def test_public_simulation_applies_and_records_minimum_commission(self):
        result = run_simulation(
            source="fixture", market="CN_ETF", factor_windows=(2,),
            factor_name="momentum_2", top_n=1, initial_cash=3000,
            commission_bps=0.5, slippage_bps=0, minimum_commission=5,
        )
        self.assertEqual(result["request"]["minimum_commission"], 5)
        self.assertTrue(result["fills"])
        self.assertTrue(all(row["commission_fee"] >= 5 for row in result["fills"]))
        self.assertGreaterEqual(result["metrics"]["ending_cash"], 0)

    def test_invalid_minimum_commission_is_rejected(self):
        for value in [-1, float("nan"), float("inf")]:
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "minimum_commission"):
                run_simulation(source="fixture", market="CN_ETF", minimum_commission=value)

    def test_batch_profile_transmits_its_minimum_commission_to_real_fills(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({
                "source": "fixture", "initial_cash": 3000, "minimum_commission": 5,
                "risk_profiles": [{"profile_id": "stress", "minimum_commission": 7}],
            }))
            config = load_paper_batch_config(path)
            attempt = _run_profile_attempt({
                "case_id": "CN_ETF_momentum_2_top1_cost5_reb1", "market": "CN_ETF",
                "factor_name": "momentum_2", "factor_windows": "(2,)", "top_n": 1,
                "cost_bps": 5,
            }, config, config.risk_profiles[0])
        self.assertEqual(attempt["status"], "completed", attempt)
        self.assertEqual(attempt["result"]["request"]["minimum_commission"], 7)
        self.assertTrue(attempt["result"]["fills"])
        self.assertTrue(all(fill["commission_fee"] >= 7 for fill in attempt["result"]["fills"]))

    def test_optimizer_loads_minimum_commission(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps({"minimum_commission": 5}))
            self.assertEqual(load_paper_profile_optimizer_config(path).minimum_commission, 5)
