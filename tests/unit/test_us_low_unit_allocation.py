import copy
from datetime import date, timedelta
from decimal import Decimal as D, getcontext, setcontext, Inexact
import unittest

from quant_robot.research import us_low_unit_allocation as m


def fixture(*, new=True, split=True, end="2001-05-31"):
    assets = m.NEW_ASSETS if new else m.OLD_ASSETS
    start, finish = date(2001, 1, 1), date.fromisoformat(end)
    dates = []
    while start <= finish:
        if start.weekday() < 5:
            dates.append(start.isoformat())
        start += timedelta(days=1)
    rows = []
    for day in dates:
        prices = {}
        for a in assets:
            value = "140" if new and split and a == "GLDM" and day >= "2001-02-15" else "70"
            prices[a] = dict(open=value, high=value, low=value, close=value, volume="1000000")
        rows.append(dict(date=day, prices=prices, capacity_volume=dict.fromkeys(assets, "1000000"),
                         execution={a: dict(suspended=False, buy_blocked=False, sell_blocked=False) for a in assets}))
    rows[-1]["terminal_open_only"] = True
    for a in assets:
        for field in ("high", "low", "close", "volume"):
            rows[-1]["prices"][a][field] = None
        rows[-1]["capacity_volume"][a] = None
    return dict(assets=list(assets), days=rows, first_decision_date="2001-01-31", terminal_date=dates[-1],
                dividends=[], splits=[dict(id="synthetic_split", symbol="GLDM", effective_date="2001-02-15",
                                           numerator=1, denominator=2)] if new and split else [],
                provenance=dict(constructed_from_market_data=False))


class LowUnitAllocationTests(unittest.TestCase):
    def test_full_split_account_conserves_wealth_and_cash_timing(self):
        result = m.run_artificial(fixture(), "new_primary")
        split = next(x for x in result["actions"] if x["kind"] == "reverse_split_cash_in_lieu")
        e = split["item"]
        self.assertEqual(e["old_quantity"], 3)
        self.assertEqual(e["whole_quantity"], 1)
        self.assertEqual(D(e["fractional_right"]), D(".5"))
        self.assertEqual(D(e["modeled_net"]), D("68.89"))
        self.assertEqual(split["before"]["spendable_cash"], split["after"]["spendable_cash"])
        day = next(d for d in result["days"] if d["date"] == "2001-02-15")
        self.assertEqual(D(day["PnL"]), -D(e["NAV_cost"]))
        self.assertEqual(D(day["attribution"]["carried_exposure"]), 0)
        self.assertTrue(result["summary"]["terminal_inventory_closed"])
        payment = next(x for x in result["actions"] if x["kind"] == "cash_in_lieu_payment")
        self.assertEqual({d["index"]: d["date"] for d in result["days"]}[payment["index"]], "2001-04-02")
        self.assertEqual(sum(D(x["PnL"]) for x in result["days"]), D(result["summary"]["terminal_book_net_profit"]))

    def test_stress_late_CIL_and_terminal_cash_are_separate(self):
        result = m.run_artificial(fixture(end="2001-03-30"), "new_stress")
        summary = result["summary"]
        self.assertGreater(D(summary["terminal_cash_in_lieu_receivable"]), 0)
        self.assertEqual(D(summary["terminal_dividend_receivable"]), 0)
        self.assertGreater(D(summary["terminal_locked_cash"]), 0)
        self.assertEqual(D(summary["terminal_settled_cash"]), D(summary["strict_available_cash"]))
        self.assertEqual(D(summary["terminal_cash_only_net_profit"]),
                         D(summary["strict_available_cash"])+D(summary["terminal_locked_cash"])-1000)
        self.assertEqual(D(summary["terminal_book_net_profit"])-D(summary["terminal_cash_only_net_profit"]),
                         D(summary["terminal_cash_in_lieu_receivable"]))
        self.assertFalse(summary["withdrawal_clock_verified"])

    def test_split_uses_open_not_future_close_and_adjusts_pending_orders(self):
        f = fixture()
        prepared = m.prepare(f, "new_primary")
        account = m._Account(prepared, "fixed_quarters", "1.00", 10)
        account.i = prepared.normalized["dates"].index("2001-02-15")
        account.q["GLDM"] = 3
        account.lots["GLDM"] = [dict(index=24, initial=3, remaining=3, original_cost=D("211"), remaining_cost=D("211"))]
        order = dict(asset="GLDM", quantity=3, capacity=9, planned_price=D("70"), budget=D("215"), capacity_notional=D("999"))
        account.pending = dict(targets={"GLDM": 5}, sell_orders=[], buy_orders=[order])
        account.p["bars"][account.i]["GLDM"]["close"] = D("1")
        account.apply_splits()
        e = account.day_cil[0]
        self.assertEqual(e["modeled_net"], D("68.89"))
        self.assertEqual(account.pending["targets"]["GLDM"], 2)
        self.assertEqual(order["quantity"], 1)
        self.assertEqual(order["planned_price"], D("140"))
        self.assertEqual(order["budget"], D("215"))
        self.assertEqual(order["capacity_notional"], D("999"))
        self.assertEqual(sum(x["remaining"] for x in account.lots["GLDM"]), 1)
        self.assertEqual(sum(x["remaining_cost"] for x in account.lots["GLDM"])+e["released_fraction_cost"], D("211"))

    def test_nominal_capacity_is_frozen_and_open_gap_only_rejects(self):
        prepared = m.prepare(fixture(new=False, split=False), "old_primary")
        account = m._Account(prepared, "fixed_quarters", "1.00", 10)
        account.i = prepared.normalized["first"]+4
        a = "SPY"
        account.p["bars"][account.i][a]["open"] = D("101")
        order = dict(asset=a, side="buy", quantity=1, capacity=1, capacity_notional=D("100"),
                     planned_price=D("70"), planned_index=account.i-1, due_index=account.i,
                     budget=D("200"), phase="monthly_buy")
        self.assertFalse(account.fill(order))
        self.assertEqual(account.rejections[-1]["reason"], "frozen_nominal_capacity")
        self.assertEqual(account.cash, 1000)
        self.assertEqual(order["quantity"], 1)
        # Full-day source volume does not rescue the predecision capacity.
        account.p["bars"][account.i][a]["volume"] = D("9999999999")
        self.assertEqual(account.capacity_notional(a, account.i), D("700000"))

    def test_cil_fee_capped_at_gross_never_borrows_or_double_charges(self):
        prepared = m.prepare(fixture(), "new_stress")
        account = m._Account(prepared, "fixed_quarters", "2.50", 30)
        account.i = prepared.normalized["dates"].index("2001-02-15")
        account.q["GLDM"] = 1
        account.lots["GLDM"] = [dict(index=24, initial=1, remaining=1, original_cost=D(1), remaining_cost=D(1))]
        account.p["bars"][account.i]["GLDM"]["open"] = D("1")
        account.apply_splits()
        e = account.day_cil[0]
        self.assertEqual(e["modeled_net"], 0)
        self.assertGreater(e["assessed_cost_above_gross"], 0)
        self.assertEqual(account.cash, 1000)
        self.assertEqual(account.total_fee, 0)
        self.assertEqual(account.total_cil_cost, D(".5"))

    def test_split_capacity_uses_consistent_nominal_amount_not_volume_jump(self):
        f = fixture()
        for row in f["days"][:-1]:
            row["capacity_volume"]["GLDM"] = "500" if row["date"] >= "2001-02-15" else "1000"
        p = m.prepare(f, "new_primary")
        account = m._Account(p, "fixed_quarters", "1.00", 10)
        account.i = p.normalized["dates"].index("2001-02-15")
        account.apply_splits()
        self.assertEqual(account.capacity_notional("GLDM", account.i), D("700"))
        self.assertEqual(account.capacity("GLDM", account.i), 5)
        self.assertEqual(account.capacity_notional("GLDM", account.i+1), D("700"))
        self.assertEqual(account.capacity("GLDM", account.i+1), 5)

    def test_buy_capacity_counts_adverse_planning_price_before_open(self):
        f = fixture(new=False, split=False)
        for row in f["days"][:-1]:
            row["capacity_volume"] = dict.fromkeys(m.OLD_ASSETS, "300")
        result = m.run_artificial(f, "old_primary")
        first = result["monthly_events"][0]
        for order in first["buy_orders"]:
            self.assertEqual(D(order["capacity_notional"]), 210)
            self.assertEqual(D(order["capacity_reference_price"]), D("70.07"))
            self.assertEqual(order["capacity"], 2)
            self.assertEqual(order["quantity"], 2)

    def test_risk_recovery_keeps_peak_and_does_not_retrigger_same_flat_breach(self):
        f = fixture(new=False, split=False, end="2001-02-23")
        for row in f["days"]:
            if row["date"] >= "2001-02-08":
                for values in row["prices"].values():
                    for field in ("open", "high", "low", "close"):
                        if values[field] is not None:
                            values[field] = "1"
        result = m.run_artificial(f, "old_primary")
        days = {d["date"]: d for d in result["days"]}
        self.assertTrue(days["2001-02-09"]["paused"])
        self.assertEqual(days["2001-02-16"]["cooldown"], 5)
        self.assertFalse(days["2001-02-19"]["paused"])
        self.assertFalse(days["2001-02-20"]["paused"])
        self.assertEqual(D(days["2001-02-20"]["peak"]), 1000)
        self.assertGreater(D(days["2001-02-20"]["observed_maxDD"]), D(".40"))

    def test_no_split_sibling_matches_prior_arithmetic_on_constant_high_capacity(self):
        from quant_robot.research import us_monthly_rotation as old
        f = fixture(new=False, split=False)
        p = m.prepare(f, "old_primary")
        p.normalized.pop("splits")
        p.normalized.pop("capacity_volume")
        previous = old._Account(p, "fixed_quarters", "1.00", 10)
        with m.localcontext(m.CONTEXT):
            expected = old.serial(previous.run())
        actual = m.run_artificial(f, "old_primary")
        self.assertEqual(expected["fills"], actual["fills"])
        self.assertEqual([d["NAV"] for d in expected["days"]], [d["NAV"] for d in actual["days"]])
        self.assertEqual(expected["summary"]["terminal_cash_only_net_profit"], actual["summary"]["terminal_cash_only_net_profit"])

    def test_cash_and_identity_and_decimal_context_boundaries(self):
        result = m.run_artificial(fixture(new=False, split=False), "cash")
        self.assertEqual(result["fills"], [])
        self.assertEqual(D(result["summary"]["terminal_book_NAV"]), 1000)
        self.assertEqual(result["summary"]["zero_target_legs"], 0)
        with self.assertRaisesRegex(ValueError, "real_asset_identity"):
            m.run_artificial(fixture(), "old_primary")
        with self.assertRaisesRegex(ValueError, "external_numeric"):
            m.run_known_history(fixture(), "new_primary", method_sha256="", registration_sha256="", numeric_marker_sha256="")
        saved = getcontext().copy()
        try:
            getcontext().prec = 7
            getcontext().traps[Inexact] = True
            getcontext().clear_flags()
            initial = getcontext().copy()
            f = fixture(); f["days"][0]["prices"]["GLDM"]["open"] = "NaN"
            with self.assertRaises(ValueError):
                m.run_artificial(f)
            self.assertEqual(getcontext().prec, initial.prec)
            self.assertEqual(getcontext().flags, initial.flags)
            self.assertEqual(getcontext().traps, initial.traps)
        finally:
            setcontext(saved)

    def test_split_and_dividend_and_terminal_contract_rejects(self):
        for mutate in (lambda f: f["splits"][0].update(numerator=True),
                       lambda f: f["splits"].append(copy.deepcopy(f["splits"][0])),
                       lambda f: f["days"][-1]["prices"]["GLDM"].update(close="1"),
                       lambda f: f["days"][0]["capacity_volume"].update(GLDM="-1")):
            f = fixture(); mutate(f)
            with self.assertRaises(ValueError):
                m.run_artificial(f)


if __name__ == "__main__":
    unittest.main()
