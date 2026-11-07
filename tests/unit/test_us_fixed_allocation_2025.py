"""Only invented prices/actions; no external source or historical execution."""
import copy
from datetime import date, timedelta
from decimal import Decimal as D, getcontext, localcontext
import unittest

from quant_robot.research import us_fixed_allocation_2025 as m


def fixture(*, true_calendar=False):
    first, last = ((date(2024, 12, 1), date(2025, 12, 31)) if true_calendar
                   else (date(2000, 12, 1), date(2001, 3, 30)))
    dates = []
    while first <= last:
        if first.weekday() < 5: dates.append(first.isoformat())
        first += timedelta(days=1)
    rows = []
    for i, day in enumerate(dates):
        prices = {a: dict(open="10", high="10", low="10", close="10", volume="1000000",
                          adj_close=None) for a in m.ASSETS}
        if i == len(dates)-1:
            for p in prices.values():
                for key in ("high", "low", "close", "volume"): p[key] = None
        rows.append(dict(date=day, prices=prices, terminal_open_only=i == len(dates)-1,
                         execution={a: dict(suspended=False, buy_blocked=False, sell_blocked=False) for a in m.ASSETS}))
    decision = max(d for d in dates if d[:7] == dates[0][:7])
    return dict(schema="us_fixed_allocation_2025_fixture_v1",
        evidence_kind="artificial_values_true_calendar" if true_calendar else "artificial",
        assets=list(m.ASSETS), days=rows, dividends=[], first_decision_date=decision,
        terminal_date=dates[-1], method_sha256=m.METHOD_SHA,
        provenance=dict(constructed_from_market_data=False, split_policy_verified=True,
                        capital_gains_present=False, holding_window_splits_absent=True,
                        calendar="invented_weekdays_not_official_calendar", test_injected_values=True))


def prepared(f):
    true = f["evidence_kind"] == "artificial_values_true_calendar"
    ctx = m._ExecutionContext("known_history_conditional" if true else "artificial", m.METHOD_SHA,
         m.digest(f), m.digest(f["provenance"]), "a"*64 if true else None, test_values=true)
    return m.prepare(f, context=ctx), ctx


class USFixedAllocation2025Tests(unittest.TestCase):
    def test_twenty_days_not_thirteen_months_first_cash_buys_D4(self):
        f = fixture()
        for row in f["days"][:-1]:
            for bar in row["prices"].values(): bar["adj_close"] = "never-decoded-as-signal"
        p, ctx = prepared(f)
        self.assertEqual(len(p.normalized["signals"]), 3)
        first = p.normalized["first"]
        r = m.run_prepared(p, "primary", context=ctx)
        self.assertEqual(min(x["index"] for x in r["fills"]), first+4)
        self.assertTrue(all(x["index"] > first for x in r["days"]))
        self.assertEqual(r["monthly_events"][0]["targets"], dict.fromkeys(m.ASSETS, 24))
        self.assertTrue(all(x["weights"]["fixed_quarters"] == dict.fromkeys(m.ASSETS, "0.25") for x in r["signals"]))
        self.assertEqual(len({x["date"] for x in r["signals"]}), len(r["signals"]))
        self.assertNotIn("returns", r["signals"][0])
        self.assertFalse(r["historical_returns_computed"])

    def test_short_warmup_duplicate_and_partial_first_month_rejected(self):
        for mutation in ("warmup", "duplicate", "first"):
            with self.subTest(mutation=mutation):
                f = fixture()
                if mutation == "warmup": f["days"] = f["days"][2:]
                elif mutation == "duplicate": f["days"].insert(5, copy.deepcopy(f["days"][5]))
                else: f["first_decision_date"] = f["days"][21]["date"]
                with self.assertRaises(ValueError): prepared(f)

    def test_unchanged_pure_ledger_full_balances_and_future_prefix(self):
        f = fixture(); p, ctx = prepared(f)
        actual = m.run_prepared(p, "primary", context=ctx)
        with localcontext(m.CONTEXT): reference = m.serial(m.kernel._Account(p, "fixed_quarters", "1.00", 10).run())
        for key in reference:
            self.assertEqual(actual[key], reference[key], key)
        f2 = copy.deepcopy(f)
        cut = p.normalized["first"]+12
        for row in f2["days"][cut:-1]:
            for b in row["prices"].values():
                for k in ("open", "high", "low", "close"): b[k] = "12"
                b["volume"] = "2000000"
        changed = m.run_artificial(f2)
        self.assertEqual([d for d in actual["days"] if d["index"] < cut],
                         [d for d in changed["days"] if d["index"] < cut])

    def test_whole_shares_zero_legs_and_fixed_three_identities(self):
        f = fixture()
        for row in f["days"]:
            for key in ("open", "high", "low", "close"):
                if row["prices"]["GLD"][key] is not None: row["prices"]["GLD"][key] = "1000"
        p, ctx = prepared(f)
        for role, (policy, minimum, slip) in m.COSTS.items():
            r = m.run_prepared(p, role, context=ctx)
            self.assertEqual((r["policy"], r["minimum_commission"], r["slippage_bps"]), (policy, minimum, slip))
            self.assertTrue(all(type(x["quantity"]) is int for x in r["fills"]))
            if role != "cash":
                self.assertEqual({x["asset"] for x in r["zero_share_target_legs"]}, {"GLD"})
                self.assertIn("GLD", {x["asset"] for x in r["zero_share_buy_legs"]})
                self.assertEqual({x["asset"] for x in r["monthly_events"][0]["buy_orders"] if x["quantity"] == 0}, {"GLD"})
                self.assertEqual(r["unheld_asset_sessions"]["GLD"], len(r["days"]))
            else:
                self.assertEqual(r["fills"], [])
                self.assertEqual(D(r["summary"]["terminal_book_NAV"]), 1000)
                self.assertEqual(D(r["summary"]["total_commission"]), 0)
        with self.assertRaises(ValueError): m.run_prepared(p, "rotation", context=ctx)

    def test_terminal_open_only_pending_receivable_and_sale_lock(self):
        f = fixture()
        f["dividends"] = [dict(id="unpaid", symbol="SPY", ex_date=f["days"][-2]["date"], amount_per_share=".10")]
        r = m.run_artificial(f)
        s = r["summary"]
        self.assertTrue(s["terminal_inventory_closed"])
        self.assertGreater(D(s["terminal_locked_cash"]), 0)
        self.assertGreater(D(s["terminal_receivables"]), 0)
        self.assertFalse(s["terminal_fully_settled"])
        self.assertEqual(D(s["terminal_cash_only_net_profit"]),
                         D(s["terminal_spendable_cash"])+D(s["terminal_locked_cash"])-1000)
        self.assertTrue(all(x["side"] == "sell" for x in r["fills"] if x["date"] == f["terminal_date"]))
        self.assertNotIn(f["terminal_date"], [x["date"] for x in r["signals"]])
        self.assertTrue(all(x["phase"] != "close" for x in r["risk_observations"] if x["date"] == f["terminal_date"]))
        self.assertEqual(r["statistics"]["status"], "not_applicable_single_selected_year")

    def test_unknown_flags_are_disclosed_and_warmup_rights_not_inherited(self):
        f = fixture()
        for row in f["days"]: row.pop("execution")
        r = m.run_artificial(f)
        self.assertGreater(len(r["unknown_execution_constraints"]), 0)
        f["dividends"] = [dict(id="old", symbol="SPY", ex_date=f["first_decision_date"], amount_per_share="bad")]
        with self.assertRaisesRegex(ValueError, "no_inherited_warmup_dividend"): prepared(f)

    def test_input_failure_and_success_leave_ambient_context_unchanged(self):
        before = m.kernel.context_record(getcontext())
        f = fixture(); f["days"][0]["prices"]["SPY"]["open"] = "not-a-number"
        with self.assertRaises(Exception): prepared(f)
        self.assertEqual(m.kernel.context_record(getcontext()), before)
        p, ctx = prepared(fixture()); m.run_prepared(p, "cash", context=ctx)
        self.assertEqual(m.kernel.context_record(getcontext()), before)
        p.normalized["bars"][0]["SPY"]["volume"] = D(3)
        with self.assertRaisesRegex(ValueError, "prepared_role_context_binding"): m.run_prepared(p, "cash", context=ctx)

    def test_true_calendar_artificial_identity_and_fixed_dates(self):
        f = fixture(true_calendar=True); p, ctx = prepared(f)
        self.assertEqual(len(p.normalized["signals"]), 12)
        self.assertEqual([s["date"][:7] for s in p.normalized["signals"].values()],
                         ["2024-12"]+[f"2025-{i:02}" for i in range(1, 12)])
        # No full-year account needed to validate the private identity boundary.
        self.assertEqual(ctx.output_kind, "artificial_values_true_calendar")
        self.assertFalse(ctx.historical)
        with self.assertRaisesRegex(ValueError, "public_artificial_only"): m.run_artificial(f)
        f["terminal_date"] = f["days"][-2]["date"]
        with self.assertRaises(ValueError): prepared(f)
        for field in ("capital_gains_present", "holding_window_splits_absent"):
            wrong = fixture(); wrong["provenance"][field] = field == "capital_gains_present"
            with self.assertRaisesRegex(ValueError, "fixed_action_identity_required"): prepared(wrong)


if __name__ == "__main__":
    unittest.main()
