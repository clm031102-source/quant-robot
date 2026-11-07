"""Pure invented calendars, prices, corporate actions and execution constraints."""
import copy
from datetime import date, timedelta
from decimal import Decimal as D, getcontext, localcontext
import unittest

from quant_robot.research import us_monthly_rotation as m


def fixture():
    dates, d = [], date(2000, 12, 1)
    while d <= date(2002, 4, 1):
        if d.weekday() < 5: dates.append(d.isoformat())
        d += timedelta(days=1)
    ends = [i for i in range(len(dates)-1) if dates[i][:7] != dates[i+1][:7]]
    first = ends[12]
    days = []
    for i, day in enumerate(dates):
        adj = ("1",)*4 if i < first else (("1.4", "1.3", ".8", ".7") if i < ends[13] else (".8", ".7", "1.5", "1.6"))
        prices = {a: dict(open="10", high="10", low="10", close="10", adj_close=v, volume="1000000") for a, v in zip(m.ASSETS, adj)}
        row = dict(date=day, prices=prices, execution={a: dict(suspended=False, buy_blocked=False, sell_blocked=False) for a in m.ASSETS})
        if i == len(dates)-1:
            row["terminal_open_only"] = True
            for a in m.ASSETS:
                for key in ("high", "low", "close", "adj_close", "volume"): row["prices"][a][key] = None
        days.append(row)
    return dict(schema="us_monthly_rotation_fixture_v1", evidence_kind="artificial", assets=list(m.ASSETS),
                days=days, dividends=[], first_decision_date=dates[first], terminal_date=dates[-1],
                method_sha256=m.METHOD_SHA, provenance=dict(constructed_from_market_data=False,
                    split_policy_verified=True, capital_gains_present=False, calendar="invented_weekdays_not_market_calendar"))


def prepared(f):
    c = m._ExecutionContext("artificial", m.METHOD_SHA, m.digest(f), m.digest(f["provenance"]))
    return m.prepare(f, context=c), c


def set_price(f, i, a, price):
    r = f["days"][i]["prices"][a]
    r["open"] = price
    if i != len(f["days"])-1:
        r["close"] = r["high"] = r["low"] = price


class USMonthlyRotationTests(unittest.TestCase):
    def test_positive_top2_ties_equal_zero_and_matched_gross_control(self):
        f = fixture(); p, c = prepared(f); first = p.normalized["first"]
        for a, adj in zip(m.ASSETS, ("2", "2", "2", "1")):
            f["days"][first]["prices"][a]["adj_close"] = adj
        p, _ = prepared(f); s = p.normalized["signals"][first]
        self.assertEqual(s["ranked_positive"], ["SPY", "EFA", "IEF"])
        self.assertEqual(s["weights"]["rotation"], dict(SPY=D(".5"), EFA=D(".5"), IEF=D(0), GLD=D(0)))
        self.assertEqual(s["weights"]["positive_equal"]["GLD"], 0)
        with localcontext(m.CONTEXT): self.assertEqual(s["weights"]["positive_equal"]["SPY"], D(1)/3)
        for a in m.ASSETS: f["days"][first]["prices"][a]["adj_close"] = "1"
        p, _ = prepared(f); self.assertEqual(p.normalized["signals"][first]["positive"], [])
        f["days"][first]["prices"]["IEF"]["adj_close"] = "1.00000001"
        p, _ = prepared(f); s = p.normalized["signals"][first]
        self.assertEqual(s["intended_gross"], D(".5"))
        self.assertEqual(s["weights"]["positive_equal"]["IEF"], D(".5"))

    def test_first_buy_D4_raw_price_and_three_session_settlement(self):
        f = fixture(); r = m.run_artificial(f); events = r["monthly_events"]
        first = events[0]["decision_index"]
        self.assertEqual(min(x["index"] for x in r["fills"]), first+4)
        self.assertEqual(events[0]["targets"], dict(SPY=49, EFA=49, IEF=0, GLD=0))
        sell_index = events[1]["sell_index"]
        sold = [x for x in r["fills"] if x["index"] == sell_index]
        self.assertEqual({x["asset"] for x in sold}, {"SPY", "EFA"})
        releases = [x for x in r["actions"] if x["kind"] == "sale_cash_release" and x["item"]["sale_index"] == sell_index]
        self.assertEqual({x["index"] for x in releases}, {sell_index+3})
        self.assertEqual(events[1]["buy_planning_index"], sell_index+2)
        self.assertGreater(D(events[1]["exact_next_open_due_cash"]), 0)
        self.assertLess(D(events[1]["buy_planning_balances"]["spendable_cash"]), D(events[1]["buy_available_after_buffer"]))
        self.assertTrue(all(x["price"] == "10.01" for x in r["fills"] if x["side"] == "buy"))

    def test_free_cash_and_known_due_only_excludes_receivables(self):
        f = fixture(); p, c = prepared(f)
        with localcontext(m.CONTEXT):
            a = m._Account(p, "rotation", "1.00", 10)
            a.decision(p.normalized["first"]); a.i = a.pending["plan_index"]
            a.cash = D("20")
            a.locks = [dict(id="due", amount=D("100"), release_index=a.i+1), dict(id="later", amount=D("300"), release_index=a.i+2)]
            a.receivables = {"unpaid":dict(amount=D("1000"), earliest_payment_date="2004-01-01")}
            a.plan_buys(a.pending)
            self.assertEqual(a.pending["buy_available_after_buffer"], D("110"))
            self.assertEqual(sum(o["budget"] for o in a.pending["buy_orders"]), D("110"))

    def test_open_gap_rejects_whole_frozen_leg_without_other_budget(self):
        f = fixture(); base = m.run_artificial(f); buy = base["monthly_events"][0]["buy_index"]
        set_price(f, buy, "SPY", "10.01")
        set_price(f, buy, "EFA", "11")
        changed = m.run_artificial(f)
        self.assertEqual(base["monthly_events"][0]["buy_orders"], changed["monthly_events"][0]["buy_orders"])
        fills = [x for x in changed["fills"] if x["index"] == buy]
        self.assertEqual([x["asset"] for x in fills], ["SPY"])
        self.assertEqual(fills[0]["quantity"], 49)
        self.assertTrue(any(x["index"] == buy and x["reason"] == "frozen_budget_or_spendable_cash" for x in changed["rejections"]))
        set_price(f, buy, "SPY", "5")
        third = m.run_artificial(f)
        self.assertTrue(any(x["index"] == buy and x["reason"] == "frozen_budget_or_spendable_cash" for x in third["rejections"]))

    def test_dividend_ex_held_only_halfup_withholding_45_calendar_days(self):
        f = fixture(); p, _ = prepared(f); buy = p.normalized["first"]+4
        f["dividends"] = [dict(id="no_prior_holding", symbol="SPY", ex_date=f["days"][buy]["date"], amount_per_share=".10"),
                          dict(id="held", symbol="SPY", ex_date=f["days"][buy+1]["date"], amount_per_share=".10")]
        r = m.run_artificial(f)
        ex = [x for x in r["actions"] if x["kind"] == "ex_entitlement"]
        self.assertEqual([x["id"] for x in ex], ["held"])
        self.assertEqual(ex[0]["item"]["quantity"], 49)
        self.assertEqual(ex[0]["item"]["gross"], "4.90")
        self.assertEqual(ex[0]["item"]["amount"], "3.43")
        earliest = (date.fromisoformat(f["days"][buy+1]["date"])+timedelta(days=45)).isoformat()
        due_index = next(i for i, x in enumerate(f["days"]) if x["date"] >= earliest)
        pays = [x for x in r["actions"] if x["kind"] == "dividend_payment"]
        self.assertEqual(len(pays), 1); self.assertEqual(pays[0]["index"], due_index)
        self.assertEqual(r["summary"]["total_net_dividend"], "3.43")

    def test_open_risk_exits_next_open_never_same_trigger_and_five_flat_sessions(self):
        f = fixture(); p, _ = prepared(f); bad = p.normalized["first"]+6
        for i in range(bad, len(f["days"])):
            for a in ("SPY", "EFA"): set_price(f, i, a, "1")
        r = m.run_artificial(f)
        exits = [x for x in r["fills"] if x["phase"] == "risk_exit"]
        self.assertTrue(exits); self.assertEqual(min(x["index"] for x in exits), bad+1)
        self.assertFalse(any(x["index"] == bad for x in exits))
        first_risk = next(x for x in r["risk_records"] if x.get("trigger"))
        self.assertEqual(first_risk["index"], bad)
        self.assertTrue(first_risk["DD_trigger"])
        resume = next(x for x in r["risk_records"] if x.get("kind") == "resume_only_at_next_monthly_decision")
        self.assertEqual(resume["index"], bad+7)  # exit bad+1, complete flat bad+2..+6
        self.assertTrue(all(D(x["peak"]) >= 1000 for x in r["days"]))
        self.assertTrue(all(x["index"] in {e["buy_index"] for e in r["monthly_events"] if "buy_index" in e}
                            for x in r["fills"] if x["side"] == "buy"))

    def test_terminal_open_preserves_locks_and_unpaid_dividend_without_close(self):
        f = fixture(); terminal = len(f["days"])-1
        f["dividends"] = [dict(id="terminal_ex", symbol="GLD", ex_date=f["terminal_date"], amount_per_share=".20")]
        r = m.run_artificial(f); s = r["summary"]
        self.assertTrue(s["terminal_inventory_closed"])
        self.assertGreater(D(s["terminal_locked_cash"]), 0)
        self.assertGreater(D(s["terminal_receivables"]), 0)
        self.assertEqual(D(s["terminal_cash_only_net_profit"]), D(s["terminal_book_cash"])-1000)
        self.assertEqual(D(s["terminal_book_NAV"]), D(s["terminal_book_cash"])+D(s["terminal_receivables"]))
        self.assertTrue(all(x["side"] == "sell" for x in r["fills"] if x["index"] == terminal))
        self.assertTrue(all(x["observed_full_day_volume"] is None for x in r["fills"] if x["index"] == terminal))
        self.assertFalse(s["terminal_fully_settled"])

    def test_prior_volume_and_future_changes_do_not_rewrite_orders(self):
        f = fixture(); base = m.run_artificial(f); buy = base["monthly_events"][0]["buy_index"]
        for a in m.ASSETS: f["days"][buy]["prices"][a]["volume"] = "0"
        for i in range(buy+1, len(f["days"])-1):
            for a in m.ASSETS:
                f["days"][i]["prices"][a]["adj_close"] = "9"
        r = m.run_artificial(f)
        self.assertEqual(base["monthly_events"][0]["buy_orders"], r["monthly_events"][0]["buy_orders"])
        self.assertEqual([(x["asset"], x["quantity"], x["notional"]) for x in base["fills"] if x["index"] == buy],
                         [(x["asset"], x["quantity"], x["notional"]) for x in r["fills"] if x["index"] == buy])
        self.assertEqual(base["signals"][0], r["signals"][0])

    def test_costs_levy_unknown_execution_and_cash(self):
        with localcontext(m.CONTEXT):
            self.assertEqual(m._fee(71, ".35"), D(".36"))
            self.assertEqual(m._fee(1, "2.50"), D("2.50"))
        f = fixture()
        for row in f["days"]: row.pop("execution")
        r = m.run_artificial(f)
        self.assertTrue(r["unknown_execution_constraints"])
        for fill in r["fills"]:
            if fill["side"] == "sell": self.assertEqual(fill["sell_levy"], "0.25")
        cash = m.run_artificial(f, "cash", "0.35", 0)
        self.assertEqual(cash["fills"], [])
        self.assertEqual(cash["summary"]["terminal_book_NAV"], "1000.00")
        self.assertEqual(cash["summary"]["total_commission"], "0")

    def test_validation_mutation_and_context_failure_are_closed(self):
        ambient = m.context_record(getcontext())
        f = fixture(); f["days"][0]["prices"]["SPY"]["open"] = "not-a-decimal"
        with self.assertRaises(Exception): m.run_artificial(f)
        self.assertEqual(ambient, m.context_record(getcontext()))
        f = fixture(); f["provenance"]["capital_gains_present"] = True
        with self.assertRaises(ValueError): m.run_artificial(f)
        f = fixture(); f["evidence_kind"] = "known_history_conditional"
        with self.assertRaises(ValueError): m.run_artificial(f)
        p, c = prepared(fixture()); p.normalized["bars"][0]["SPY"]["open"] = D(20)
        with self.assertRaises(ValueError): m.run_prepared(p, "rotation", "1.00", 10, context=c)
        for minimum, slip in ((1.0, 10), ("1.00", False), ("5.00", 10)):
            with self.subTest(cost=(minimum, slip)), self.assertRaises(ValueError):
                m.run_artificial(fixture(), minimum=minimum, slip=slip)
        m.run_artificial(fixture(), "cash", "0.35", 0)
        self.assertEqual(ambient, m.context_record(getcontext()))

    def test_fixed_19year_shared_bootstrap_structure(self):
        p, c = prepared(fixture()); annual = {}
        for minimum, slip in m.COSTS:
            annual[f"min{minimum}_slip{slip}"] = {
                policy:{str(2006+y):str((y-8)*(j+1)-slip) for y in range(19)} for j, policy in enumerate(m.POLICIES)}
        s = m.fixed_statistics(annual, context=c)
        self.assertEqual((s["N"], s["block"], s["starts_per_replication"], s["truncate_rows_to"]), (19, 2, 10, 19))
        self.assertEqual(len(s["endpoint_keys"]), 27)
        self.assertTrue(s["shared_indices_for_all27"])
        self.assertEqual(s["quantiles"], [.025, .975])
        self.assertFalse(s["historical_returns_computed"])
        self.assertAlmostEqual(s["lower"]["min0.35_slip0/net"]-s["lower"]["min0.35_slip10/net"], 10)

    def test_artificial_injected_private_identity_stays_artificial(self):
        f = fixture(); f["evidence_kind"] = "artificial_values_true_calendar"
        c = m._ExecutionContext("known_history_conditional", m.METHOD_SHA, m.digest(f),
                                m.digest(f["provenance"]), "a"*64, test_values=True)
        p = m.prepare(f, context=c)
        r = m.run_prepared(p, "cash", "0.35", 0, context=c)
        self.assertEqual(r["evidence_kind"], "artificial_values_true_calendar")
        self.assertFalse(r["historical_returns_computed"])
        self.assertTrue(r["test_injected_values"])
        with self.assertRaises(ValueError): m.run_artificial(f)


if __name__ == "__main__": unittest.main()
