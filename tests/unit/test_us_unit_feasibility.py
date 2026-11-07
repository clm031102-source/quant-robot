from __future__ import annotations

import copy
import json
import unittest
from decimal import Decimal, Inexact, ROUND_DOWN, getcontext, localcontext
from fractions import Fraction

from quant_robot.research.us_unit_feasibility import ASSETS, calculate


def artificial_prices(value="100"):
    return {symbol: value for symbol in ASSETS}


class UnitFeasibilityTests(unittest.TestCase):
    def test_hand_calculated_four_results_and_deployment_not_fees(self):
        prices = dict(SPY="500", EFA="100", IEF="100", GLD="300", SPYM="50", GLDM="50")
        result = calculate(prices)
        self.assertEqual(set(result["results"]), {
            "old_primary", "old_stress", "proposed_primary", "proposed_stress"})
        old = result["results"]["old_primary"]
        new = result["results"]["proposed_primary"]
        self.assertEqual([x["quantity"] for x in old["legs"]], [0, 2, 2, 0])
        self.assertEqual([x["quantity"] for x in new["legs"]], [4, 2, 2, 4])
        self.assertEqual(old["summary"]["cash_remaining_usd"], "597.60")
        self.assertEqual(new["summary"]["cash_remaining_usd"], "195.20")
        self.assertEqual(new["summary"]["economic_deployment_ratio"], "0.8")
        self.assertEqual(new["summary"]["fill_notional_deployment_ratio"], "0.8008")
        self.assertEqual(new["summary"]["commission_usd"], "4.00")
        pressure = result["results"]["proposed_stress"]["summary"]
        self.assertEqual(pressure["cash_remaining_usd"], "187.60")
        self.assertEqual(pressure["fill_notional_usd"], "802.40")
        self.assertEqual(pressure["commission_usd"], "10.00")
        self.assertFalse(result["return_computed"])
        self.assertFalse(result["qualified"])
        self.assertEqual(result["account_count"], 0)
        json.dumps(result, allow_nan=False)

    def test_exact_budget_boundary_and_no_cross_leg_cash_rescue(self):
        prices = artificial_prices("500")
        prices["SPY"] = "246.25"
        row = calculate(prices)["results"]["old_primary"]
        leg = row["legs"][0]
        self.assertEqual(leg["buy_price_usd"], "246.50")
        self.assertEqual(leg["quantity"], 1)
        self.assertEqual(leg["cash_spent_usd"], "247.50")
        prices["SPY"] = "246.26"
        row = calculate(prices)["results"]["old_primary"]
        self.assertEqual(row["summary"]["zero_share_legs"], 4)
        self.assertEqual(row["summary"]["cash_remaining_usd"], "1000.00")
        for leg in row["legs"]:
            self.assertEqual(leg["commission_usd"], "0.00")
            self.assertTrue(leg["next_quantity_infeasible"])

    def test_half_cent_per_share_commission_rounds_up_and_binds(self):
        leg = calculate(artificial_prices("0.009"))["results"]["old_primary"]["legs"][0]
        self.assertEqual(leg["buy_price_usd"], "0.01")
        self.assertEqual(leg["quantity"], 16500)
        self.assertEqual(leg["commission_usd"], "82.50")
        self.assertEqual(leg["cash_spent_usd"], "247.50")
        self.assertEqual(leg["next_quantity_cost_usd"], "247.52")
        # Independently inspect an odd selected quantity: fee is a half-cent before ceiling.
        leg = calculate(artificial_prices("0.02"))["results"]["old_primary"]["legs"][0]
        self.assertEqual(leg["quantity"], 7071)
        self.assertEqual(leg["commission_usd"], "35.36")
        self.assertEqual(leg["cash_spent_usd"], "247.49")

    def test_price_ceiling_does_not_lose_long_decimal_tail(self):
        # Above an exact zero-slippage cent boundary after the10bp factor:
        # 10/1001 + positive tail must round to0.02, not0.01.
        value = "0.00999000999000999000999000999000999000999000999000999001"
        leg = calculate(artificial_prices(value))["results"]["old_primary"]["legs"][0]
        self.assertEqual(leg["buy_price_usd"], "0.02")
        tiny = "0." + "0" * 60 + "1"
        leg = calculate(artificial_prices(tiny))["results"]["old_primary"]["legs"][0]
        self.assertEqual(leg["buy_price_usd"], "0.01")

    def test_independent_exhaustive_fraction_oracle(self):
        prices = dict(SPY="0.02", EFA="1.001", IEF="123.123", GLD="246.26", SPYM="50.005", GLDM="999999")
        result = calculate(prices)
        for scenario in result["results"].values():
            slip = 10 if scenario["cost_case"] == "primary" else 30
            minimum = 100 if scenario["cost_case"] == "primary" else 250
            for leg in scenario["legs"]:
                with self.subTest(scenario=scenario["cost_case"], symbol=leg["symbol"]):
                    exact = Fraction(prices[leg["symbol"]]) * Fraction(10000 + slip, 10000) * 100
                    price_cents = -(-exact.numerator // exact.denominator)
                    def cost(q):
                        return 0 if q == 0 else q * price_cents + max(minimum, -(-(q * 5) // 10))
                    feasible = [q for q in range(24750 // price_cents + 1) if cost(q) <= 24750]
                    self.assertEqual(leg["quantity"], max(feasible))
                    self.assertGreater(cost(leg["quantity"] + 1), 24750)
                    self.assertLessEqual(cost(leg["quantity"]), 24750)
            cash = Decimal(scenario["summary"]["cash_remaining_usd"])
            spent = sum(Decimal(x["cash_spent_usd"]) for x in scenario["legs"])
            self.assertEqual(cash + spent, Decimal("1000"))
            self.assertGreaterEqual(cash, Decimal("10"))

    def test_rejects_nonpositive_nonfinite_and_nonliteral_prices(self):
        for bad in (0, 1.5, True, None, Decimal("1"), "0", "0.000", "-1", "-0",
                    "NaN", "Infinity", "-Infinity", "sNaN", " 1", "1 ", "+1", "1e2",
                    "01", ".5", "1.", "1,000", "1\n"):
            with self.subTest(bad=repr(bad)):
                prices = artificial_prices(); prices["SPY"] = bad
                with self.assertRaises(ValueError): calculate(prices)
        for bad in ([], {}, {**artificial_prices(), "QQQ": "100"}):
            with self.assertRaises(ValueError): calculate(bad)
        prices = artificial_prices(); del prices["GLDM"]
        with self.assertRaises(ValueError): calculate(prices)

    def test_context_isolation_and_input_immutability(self):
        prices = artificial_prices("123.123456789123456789")
        original = copy.deepcopy(prices)
        expected = calculate(prices)
        with localcontext() as ambient:
            ambient.prec = 5
            ambient.rounding = ROUND_DOWN
            ambient.traps[Inexact] = True
            ambient.flags[Inexact] = True
            before = str(getcontext())
            self.assertEqual(calculate(prices), expected)
            with self.assertRaises(ValueError): calculate({**prices, "SPY": "NaN"})
            self.assertEqual(str(getcontext()), before)
        self.assertEqual(prices, original)
        self.assertEqual(expected["arithmetic"]["decimal_precision"], 50)
        self.assertEqual(expected["arithmetic"]["traps"], ["DivisionByZero", "InvalidOperation", "Overflow"])


if __name__ == "__main__":
    unittest.main()
