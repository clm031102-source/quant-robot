import copy
import importlib.util
from pathlib import Path
import unittest
from decimal import localcontext

from quant_robot.research import us_low_unit_allocation as production
from quant_robot.research import us_low_unit_allocation_verification as verifier

SPEC = importlib.util.spec_from_file_location("low_unit_artificial_fixtures", Path(__file__).with_name("test_us_low_unit_allocation.py"))
F = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(F)


class LowUnitIndependentVerificationTests(unittest.TestCase):
    def test_all_five_roles_with_independent_cash_and_rights_replay(self):
        for role in ("old_primary", "old_stress", "new_primary", "new_stress", "cash"):
            with self.subTest(role=role):
                new = role.startswith("new_")
                fixture = F.fixture(new=new, split=new)
                account = production.run_artificial(fixture, role)
                self.assertEqual(verifier.verify_account(fixture, account)["status"], "recorded_account_consistent")

    def test_pending_orders_mechanically_change_units(self):
        fixture = F.fixture()
        fixture["splits"][0]["effective_date"] = "2001-03-01"
        for row in fixture["days"]:
            price = "140" if row["date"] >= "2001-03-01" else "70"
            for key in ("open", "high", "low", "close"):
                if row["prices"]["GLDM"][key] is not None:
                    row["prices"]["GLDM"][key] = price
        account = production.run_artificial(fixture, "new_primary")
        self.assertTrue(any(a["item"]["pending_before"] for a in account["actions"] if a["kind"] == "reverse_split_cash_in_lieu"))
        self.assertEqual(verifier.verify_account(fixture, account)["status"], "recorded_account_consistent")

    def test_saved_cash_in_lieu_net_or_payment_timing_corruption_rejected(self):
        fixture = F.fixture()
        account = production.run_artificial(fixture, "new_primary")
        for field, value in (("modeled_net", "999"), ("earliest_payment_date", "2001-02-15")):
            with self.subTest(field=field):
                bad = copy.deepcopy(account)
                action = next(a for a in bad["actions"] if a["kind"] == "reverse_split_cash_in_lieu")
                action["item"][field] = value
                with self.assertRaises(ValueError):
                    verifier.verify_account(fixture, bad)

    def test_cash_summary_and_FIFO_corruption_rejected(self):
        fixture = F.fixture()
        account = production.run_artificial(fixture, "new_stress")
        for which in ("cash", "FIFO", "capacity"):
            with self.subTest(which=which):
                bad = copy.deepcopy(account)
                if which == "cash":
                    bad["summary"]["strict_available_cash"] = "10000"
                elif which == "FIFO":
                    bad["FIFO_lots"]["GLDM"][0]["remaining_cost"] = "1"
                else:
                    bad["intents"][0]["capacity_notional"] = "999999999"
                with self.assertRaises(ValueError):
                    verifier.verify_account(fixture, bad)

    def test_omitted_fixed_quarter_decision_is_rejected(self):
        fixture = F.fixture(new=False, split=False)
        account = production.run_artificial(fixture, "old_primary")
        account["monthly_events"][0]["targets"] = {}
        with self.assertRaisesRegex(ValueError, "fixed_decision_eligibility"):
            verifier.verify_account(fixture, account)

    def test_role_and_external_claim_identity_are_not_relabelable(self):
        fixture = F.fixture(new=False, split=False)
        account = production.run_artificial(fixture, "old_primary")
        bad = copy.deepcopy(account); bad["role"] = "new_primary"
        with self.assertRaisesRegex(ValueError, "role_asset_basket"):
            verifier.verify_account(fixture, bad)
        account["registration_sha256"] = "a"*64
        account["numeric_marker_sha256"] = "b"*64
        self.assertEqual(verifier.verify_account(fixture, account, expected_registration="a"*64,
                                                expected_marker="b"*64)["status"], "recorded_account_consistent")
        for kwargs in ({"expected_registration": "c"*64, "expected_marker": "b"*64},
                       {"expected_registration": "a"*64, "expected_marker": "c"*64}, {}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                verifier.verify_account(fixture, account, **kwargs)

    def test_missing_buy_plan_and_four_leg_snapshot_are_rejected(self):
        fixture = F.fixture(new=False, split=False)
        account = production.run_artificial(fixture, "old_primary")
        for which in ("plan", "snapshot", "intent"):
            bad = copy.deepcopy(account)
            event = next(e for e in bad["monthly_events"] if "buy_planning_index" in e)
            if which == "plan":
                del event["buy_planning_index"]
            elif which == "snapshot":
                event["buy_orders"].pop()
            else:
                index = next(i for i, order in enumerate(bad["intents"]) if order["phase"] == "monthly_buy")
                bad["intents"].pop(index)
            # Check the new fixed-order guard directly: no bookkeeping corruption
            # or stale intent IDs can mask whether this missing-order guard works.
            with self.subTest(which=which), localcontext(verifier.CONTEXT), self.assertRaises(ValueError):
                verifier._verify_recorded_budgets(fixture, bad)

    def test_short_monthly_sell_and_terminal_exit_are_rejected(self):
        fixture = F.fixture(new=False, split=False)
        for row in fixture["days"]:
            if row["date"] >= "2001-02-12":
                for field in ("open", "high", "low", "close"):
                    if row["prices"]["SPY"][field] is not None: row["prices"]["SPY"][field] = "200"
        account = production.run_artificial(fixture, "old_primary")
        self.assertEqual(verifier.verify_account(fixture, account)["status"], "recorded_account_consistent")
        for phase in ("monthly_sell", "terminal"):
            bad = copy.deepcopy(account)
            intent = next(x for x in bad["intents"] if x["phase"] == phase and x["quantity"] > 0)
            intent["quantity"] -= 1
            with self.subTest(phase=phase), localcontext(verifier.CONTEXT), self.assertRaisesRegex(ValueError, "fixed_order_intent"):
                verifier._verify_recorded_budgets(fixture, bad)

    def test_risk_cancellation_before_open_and_inside_buy_iteration_are_valid(self):
        # Pre-open loss cancels the entire increase list before iteration.
        fixture = F.fixture(new=False, split=False)
        for row in fixture["days"]:
            if "2001-02-12" <= row["date"] < "2001-03-06":
                for field in ("open", "high", "low", "close"):
                    row["prices"]["SPY"][field] = "200"
            if row["date"] >= "2001-03-06":
                for a in fixture["assets"]:
                    for field in ("open", "high", "low", "close"):
                        if row["prices"][a][field] is not None: row["prices"][a][field] = "10"
        account = production.run_artificial(fixture, "old_primary")
        canceled = next(e for e in account["monthly_events"] if e["date"] == "2001-02-28")
        self.assertTrue(any(verifier.decimal(v) > 0 for v in canceled["planned_costs"].values()))
        self.assertEqual(canceled["buy_orders"], [])
        self.assertFalse(any(x["phase"] == "monthly_buy" and x["due_index"] == canceled["buy_index"]
                             for x in account["intents"]))
        self.assertTrue(any(x["phase"] == "risk_exit" for x in account["intents"]))
        self.assertEqual(verifier.verify_account(fixture, account)["status"], "recorded_account_consistent")
        bad = copy.deepcopy(account)
        sell = next(x for x in bad["intents"] if x["phase"] == "risk_exit" and x["quantity"])
        sell["quantity"] -= 1
        with localcontext(verifier.CONTEXT), self.assertRaisesRegex(ValueError, "fixed_order_intent"):
            verifier._verify_recorded_budgets(fixture, bad)
        # A high per-share cost at a tiny artificial price triggers the 2% rule
        # during a four-leg buy iteration; remaining frozen intents stay recorded.
        fixture = F.fixture(new=False, split=False)
        for row in fixture["days"]:
            for a in fixture["assets"]:
                for field in ("open", "high", "low", "close"):
                    if row["prices"][a][field] is not None: row["prices"][a][field] = "0.02"
        account = production.run_artificial(fixture, "old_primary")
        self.assertTrue(any(x.get("reason") == "risk_cancelled_increase" for x in account["rejections"]))
        self.assertEqual(verifier.verify_account(fixture, account)["status"], "recorded_account_consistent")


if __name__ == "__main__":
    unittest.main()
