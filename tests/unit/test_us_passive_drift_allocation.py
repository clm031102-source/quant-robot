import copy
from decimal import Decimal as D, Inexact, getcontext, setcontext
import unittest

from quant_robot.research import us_low_unit_allocation as base
from quant_robot.research import us_passive_drift_allocation as m
from tests.unit.test_us_low_unit_allocation import fixture


def set_price(row, asset, value):
    for key in ("open", "high", "low", "close"):
        if row["prices"][asset][key] is not None:
            row["prices"][asset][key] = value


class PassiveDriftAllocationTests(unittest.TestCase):
    def test_initial_prefix_inherits_cash_budgets_capacity_and_fills(self):
        f = fixture(split=False)
        original = copy.deepcopy(f)
        for role in m.ROLES:
            with self.subTest(role=role):
                monthly = base.run_artificial(f, "new_" + role)
                drift = m.run_artificial(f, role)
                cut = next(e["decision_index"] for e in drift["monthly_events"]
                           if e["status"] == "skipped_passive_drift_while_invested")
                self.assertEqual([d for d in drift["days"] if d["index"] <= cut],
                                 [d for d in monthly["days"] if d["index"] <= cut])
                self.assertEqual(drift["monthly_events"][0], monthly["monthly_events"][0])
                self.assertEqual([x for x in drift["fills"] if x["index"] <= cut],
                                 [x for x in monthly["fills"] if x["index"] <= cut])
        self.assertEqual(f, original)

    def test_invested_month_end_has_no_orders_or_dividend_reinvestment(self):
        f = fixture(split=False)
        f["dividends"] = [dict(id="invented_dividend", symbol="SPYM",
                               ex_date="2001-02-08", amount_per_share="2")]
        for row in f["days"]:
            if row["date"] >= "2001-02-20":
                set_price(row, "SPYM", "120")
        result = m.run_artificial(f)
        skips = [e for e in result["monthly_events"]
                 if e["status"] == "skipped_passive_drift_while_invested"]
        self.assertEqual(len(skips), 3)
        for e in skips:
            self.assertEqual((e["targets"], e["sell_orders"], e["buy_orders"]), ({}, [], []))
            self.assertTrue(any(e["pre_decision_balances"]["quantities"].values()))
        self.assertEqual(len(result["fills"]), 8)  # Four initial buys and four terminal exits.
        self.assertEqual({x["phase"] for x in result["fills"]}, {"monthly_buy", "terminal"})
        self.assertTrue(any(x["kind"] == "dividend_payment" for x in result["actions"]))
        self.assertTrue(result["summary"]["terminal_inventory_closed"])

    def test_missing_leg_is_not_topped_up_while_other_legs_are_held(self):
        f = fixture(split=False)
        next(row for row in f["days"] if row["date"] == "2001-02-06")["execution"]["SPYM"]["buy_blocked"] = True
        result = m.run_artificial(f)
        self.assertFalse(any(x["asset"] == "SPYM" for x in result["fills"]))
        self.assertTrue(any(x["reason"] == "known_execution_constraint" for x in result["rejections"]))
        self.assertGreater(result["summary"]["skipped_invested_month_ends"], 0)
        self.assertEqual(len(result["fills"]), 6)

    def test_all_rejected_initial_orders_retry_only_at_normal_month_end(self):
        f = fixture(split=False)
        first_buy = next(row for row in f["days"] if row["date"] == "2001-02-06")
        for flags in first_buy["execution"].values():
            flags["buy_blocked"] = True
        result = m.run_artificial(f)
        self.assertEqual(len(result["rejections"]), 4)
        dates = {d["index"]: d["date"] for d in result["days"]}
        buys = [x for x in result["fills"] if x["side"] == "buy"]
        self.assertEqual(len(buys), 4)
        self.assertEqual({dates[x["index"]] for x in buys}, {"2001-03-06"})
        self.assertEqual(result["monthly_events"][1]["date"], "2001-02-28")
        self.assertTrue(result["monthly_events"][1]["targets"])

    def test_risk_exit_flat_cooldown_and_next_month_entry_keep_peak(self):
        f = fixture(split=False)
        for row in f["days"]:
            if row["date"] >= "2001-02-08":
                for asset in base.NEW_ASSETS:
                    set_price(row, asset, "30")
        result = m.run_artificial(f)
        days = {d["date"]: d for d in result["days"]}
        self.assertEqual(days["2001-02-16"]["cooldown"], 5)
        self.assertFalse(days["2001-02-19"]["paused"])
        self.assertFalse(days["2001-02-20"]["paused"])
        self.assertEqual(D(days["2001-02-20"]["peak"]), 1000)
        self.assertGreater(D(days["2001-02-20"]["observed_maxDD"]), D(".4"))
        second = next(e for e in result["monthly_events"] if e["date"] == "2001-02-28")
        self.assertTrue(second["targets"])
        buys = [x for x in result["fills"] if x["side"] == "buy"]
        dates = {d["index"]: d["date"] for d in result["days"]}
        self.assertEqual(dates[buys[4]["index"]], "2001-03-06")
        self.assertTrue(any(x["phase"] == "risk_exit" for x in result["fills"]))
        # A new active position below the continuous peak still triggers risk.
        self.assertTrue(days["2001-03-06"]["paused"])
        self.assertTrue(result["summary"]["terminal_inventory_closed"])

    def test_pending_risk_exit_or_pause_cannot_be_turned_into_drift_entry(self):
        f = fixture(split=False)
        prepared = base.prepare(f, "new_primary")
        for paused, risk_due in ((True, None), (False, 45)):
            with self.subTest(paused=paused, risk_due=risk_due):
                account = m._DriftAccount(prepared, "fixed_quarters", "1.00", 10)
                account.paused, account.risk_due = paused, risk_due
                account.q["SPYM"] = 1
                account.decision(prepared.normalized["first"])
                self.assertEqual(account.events[-1]["status"], "skipped_cash_risk_or_terminal")
                self.assertIsNone(account.pending)

    def test_reverse_split_CIL_delays_and_terminal_balances_inherit(self):
        for role, delay in (("primary", 45), ("stress", 90)):
            with self.subTest(role=role):
                result = m.run_artificial(fixture(end="2001-03-30"), role)
                split = next(x for x in result["actions"] if x["kind"] == "reverse_split_cash_in_lieu")
                item = split["item"]
                self.assertEqual(item["old_quantity"], 3)
                self.assertEqual(item["whole_quantity"], 1)
                self.assertEqual(D(item["fractional_right"]), D(".5"))
                self.assertEqual(item["payment_delay_calendar_days"], delay)
                summary = result["summary"]
                self.assertGreater(D(summary["terminal_cash_in_lieu_receivable"]), 0)
                self.assertGreater(D(summary["terminal_locked_cash"]), 0)
                self.assertEqual(D(summary["cash_and_locked_sale_proceeds_net_profit"]),
                                 D(summary["strict_available_cash"])+D(summary["terminal_locked_cash"])-1000)
                self.assertTrue(summary["terminal_inventory_closed"])

    def test_identity_roles_historical_boundary_and_ambient_context(self):
        for bad in ("cash", "new_primary", "old_primary", None):
            with self.assertRaisesRegex(ValueError, "fixed_passive_drift_role"):
                m.run_artificial(fixture(), bad)
        f = fixture()
        f["provenance"]["constructed_from_market_data"] = True
        with self.assertRaisesRegex(ValueError, "artificial_values_only"):
            m.run_artificial(f)
        with self.assertRaisesRegex(ValueError, "external_numeric_claim_hashes"):
            m.run_known_history(f, "primary", method_sha256="", registration_sha256="", numeric_marker_sha256="")
        with self.assertRaisesRegex(ValueError, "fixed_2021_2025_window"):
            m.run_known_history(f, "primary", method_sha256="a"*64,
                                registration_sha256="b"*64, numeric_marker_sha256="c"*64)
        saved = getcontext().copy()
        try:
            getcontext().prec = 7
            getcontext().traps[Inexact] = True
            getcontext().clear_flags()
            before = getcontext().copy()
            result = m.run_artificial(fixture())
            self.assertEqual(getcontext().flags, before.flags)
            self.assertEqual(getcontext().traps, before.traps)
            self.assertEqual(getcontext().prec, before.prec)
        finally:
            setcontext(saved)
        self.assertEqual(result["strategy_id"], m.STRATEGY_ID)
        self.assertEqual(result["holding_policy"], m.HOLDING_POLICY)
        self.assertEqual(result["entry_allocation_policy"], "fixed_quarters")
        self.assertEqual(result["role"], "new_primary")
        self.assertEqual(result["scenario_role"], "primary")
        self.assertEqual(result["evidence_kind"], "artificial")
        self.assertFalse(result["historical_returns_computed"])
        self.assertFalse(result["qualified"])
        self.assertEqual(result["real_forward"], 0)


if __name__ == "__main__":
    unittest.main()
