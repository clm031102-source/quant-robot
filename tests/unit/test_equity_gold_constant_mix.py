import copy
import json
import unittest
from datetime import date, timedelta
from decimal import Decimal, localcontext, getcontext
from pathlib import Path
from tempfile import TemporaryDirectory

from quant_robot.research import equity_gold_constant_mix as m


def rising_fixture(sessions=70, events=None):
    f = m.make_fixture(sessions, events or [20, 40])
    for row in f["bars"][m.ASSETS[0]][22:]:
        row.update(open="2.40", close="2.40")
    return f


def extend_action_calendar(f, count=3):
    day = date.fromisoformat(f["dates"][-1])
    for _ in range(count):
        day += timedelta(days=1)
        f["dates"].append(day.isoformat())


class ConstantMixTests(unittest.TestCase):
    def test_exit_fee_shortfall_uses_free_then_locked_cash_without_negative_spendable(self):
        with localcontext(m.CONTEXT):
            for free in (Decimal(".10"), Decimal("5")):
                with self.subTest(free=free):
                    p = m._prepare(m.make_fixture(35, [20]))
                    a = m._Account(p, "constant_mix", 5, 0)
                    a.i, a.cash = 22, free
                    a.q = dict.fromkeys(m.ASSETS, 100)
                    a.lots = {x: [dict(start_index=21, initial=100, remaining=100)] for x in m.ASSETS}
                    p["bars"][m.ASSETS[0]][22]["open"] = Decimal("1")
                    p["bars"][m.ASSETS[1]][22]["open"] = Decimal(".001")
                    self.assertTrue(a.fill(m.ASSETS[0], "sell", 100, "risk_exit"))
                    self.assertTrue(a.fill(m.ASSETS[1], "sell", 100, "risk_exit"))
                    self.assertEqual(a.cash, free+Decimal("90.10"))
                    self.assertGreaterEqual(a.cash-a.unavailable, 0)
                    expected_locked_used = max(Decimal("4.90")-free, Decimal(0))
                    self.assertEqual(a.fills[-1]["fee_payment"]["from_locked_sale"], expected_locked_used)
                    self.assertEqual(sum(a.fills[-1]["fee_payment"].values()), Decimal(5))
                    self.assertEqual(a.unavailable, Decimal(95)-expected_locked_used)
            p = m._prepare(m.make_fixture(35, [20]))
            a = m._Account(p, "constant_mix", 5, 0); a.i = 22; a.cash = Decimal(".10")
            a.q[m.ASSETS[1]] = 100
            p["bars"][m.ASSETS[1]][22]["open"] = Decimal(".001")
            self.assertFalse(a.fill(m.ASSETS[1], "sell", 100, "risk_exit"))
            self.assertEqual(a.cash, Decimal(".10"))
            self.assertEqual(a.q[m.ASSETS[1]], 100)
            self.assertEqual(a.rejections[-1]["reason"], "cannot_finance_exit_fee")

    def test_artificial_identity_date_and_context_invalid_valid(self):
        before = m._context_record(getcontext())
        f = m.make_fixture(35, [20])
        bad = copy.deepcopy(f)
        bad["bars"][m.ASSETS[0]][0]["open"] = "not_a_decimal"
        with self.assertRaises(ValueError):
            m.run_account(bad)
        self.assertEqual(before, m._context_record(getcontext()))
        r = m.run_account(f)
        self.assertEqual(before, m._context_record(getcontext()))
        self.assertFalse(r["historical_returns_computed"])
        self.assertEqual(r["runtime"]["context_initial"]["prec"], 40)
        for key, value in (("source_nature", "real"), ("assets", ["510300", "518880"])):
            bad = copy.deepcopy(f); bad[key] = value
            with self.assertRaises(ValueError): m.run_account(bad)
        bad = copy.deepcopy(f); bad["dates"] = [d.replace("2001", "2020") for d in bad["dates"]]
        with self.assertRaises(ValueError): m.run_account(bad)

    def test_same_actual_initial_basket_all_costs_and_cash(self):
        r = m.run_matrix(m.make_fixture(35, [20]))
        self.assertEqual(r["account_count"], 27)
        self.assertTrue(all(r["same_actual_initial_baskets"].values()))
        for key, account in r["accounts"].items():
            self.assertTrue(account["summary"]["attribution_reconciled"])
            if key.endswith("/cash"):
                self.assertEqual(Decimal(account["summary"]["terminal_cash"]), 10000)
                self.assertEqual(account["fills"], [])

    def test_small_gap_allowed_excess_gap_cancel_no_other_budget_transfer(self):
        f = m.make_fixture(35, [20])
        f["bars"][m.ASSETS[0]][21]["open"] = "1.201"
        small = m.run_account(f)
        self.assertEqual(len([x for x in small["fills"] if x["index"] == 21]), 2)
        f["bars"][m.ASSETS[0]][21]["open"] = "1.24"
        # Both legs may have available combined cash, but cannot borrow the other's budget.
        f["bars"][m.ASSETS[1]][21]["buy_blocked"] = True
        gap = m.run_account(f)
        self.assertEqual(len([x for x in gap["fills"] if x["index"] == 21]), 0)
        rejected = [x for x in gap["rejections"] if x["index"] == 21]
        self.assertIn("frozen_budget_or_spendable_cash", [x["reason"] for x in rejected])
        self.assertEqual(gap["event_attempts"][0]["buy_orders"][0]["quantity"],
                         small["event_attempts"][0]["buy_orders"][0]["quantity"])
        for e in (small, gap):
            event = e["event_attempts"][0]
            self.assertLessEqual(sum(Decimal(x["frozen_budget"]) for x in event["buy_orders"]),
                                 Decimal(event["buy_available_after_reserve"]))

    def test_sell_then_next_day_buy_and_locked_cash(self):
        r = m.run_account(rising_fixture())
        sells = [f for f in r["fills"] if f["index"] == 40]
        buys = [f for f in r["fills"] if f["index"] == 41]
        self.assertTrue(sells and buys)
        self.assertTrue(all(f["side"] == "sell" for f in sells))
        self.assertTrue(all(f["side"] == "buy" for f in buys))
        for f in sells:
            self.assertEqual(f["before"]["spendable_cash"], f["after"]["spendable_cash"])
            self.assertGreater(Decimal(f["after"]["locked_sale_cash"]), 0)
        day = next(x for x in r["days"] if x["index"] == 40)
        self.assertEqual(Decimal(day["after"]["locked_sale_cash"]), 0)

    def test_failed_sell_never_credits_expected_cash(self):
        f = rising_fixture()
        f["bars"][m.ASSETS[0]][40]["sell_blocked"] = True
        r = m.run_account(f)
        event = r["event_attempts"][1]
        self.assertEqual(event["sell_fills"], 0)
        self.assertLess(Decimal(event["buy_planning_cash"]), 200)
        self.assertEqual(sum(x["quantity"] for x in event["buy_orders"]), 0)
        self.assertTrue(all(Decimal(d["after"]["book_cash"]) >= 0 for d in r["days"]))

    def test_percentage_fee_reserve_and_no_252_exit(self):
        with localcontext(m.CONTEXT):
            self.assertEqual(m._reserve(Decimal(1000000)), Decimal(2000))
            self.assertEqual(m._fee(Decimal(1000000), 10), Decimal("500.00"))
        r = m.run_account(m.make_fixture(310, [20]), "drift")
        self.assertEqual([f["index"] for f in r["fills"]], [21, 21, 309, 309])

    def test_record_ex_pay_once_and_pay_after_orders(self):
        f = m.make_fixture(45, [20, 34])
        f["actions"] = [dict(event_id="D", asset=m.ASSETS[0], known_index=20,
                              record_index=25, ex_index=30, pay_index=35,
                              cash_per_share=".01", share_multiplier="1")]
        r = m.run_account(f)
        logs = r["action_records"]
        self.assertEqual([x["kind"] for x in logs], ["record_right", "ex_receivable", "pay_after_fills"])
        amount = Decimal(logs[1]["amount"])
        self.assertEqual(amount, Decimal(logs[0]["quantity"])*Decimal(".01"))
        self.assertEqual(Decimal(r["attribution"]["dividend_entitlement"]), amount)
        self.assertEqual(Decimal(logs[2]["after"]["book_cash"])-Decimal(logs[2]["before"]["book_cash"]), amount)
        event = r["event_attempts"][1]
        self.assertEqual(event["buy_planning_index"], 34)
        day35 = next(d for d in r["days"] if d["index"] == 35)
        self.assertEqual(Decimal(day35["attribution"]["dividend_entitlement"]), 0)

    def test_action_sequence_calendar_and_warmup_rights(self):
        f = m.make_fixture(35, [20])
        a = dict(event_id="D", asset=m.ASSETS[0], known_index=1, record_index=5,
                 ex_index=22, pay_index=23, cash_per_share=".10", share_multiplier="1")
        f["actions"] = [a]
        self.assertEqual(m.run_account(f)["action_records"], [])
        a["record_index"] = 22
        with self.assertRaisesRegex(ValueError, "sequence"): m.run_account(f)
        a["record_index"] = 5; a["pay_index"] = 36
        with self.assertRaisesRegex(ValueError, "calendar"): m.run_account(f)
        a["pay_index"] = 23; a["share_multiplier"] = "10"
        with self.assertRaisesRegex(ValueError, "conversion"): m.run_account(f)

    def test_terminal_right_receivable_and_zero_quantity_not_double_counted(self):
        for ex, expected in ((30, "terminal_unexercised_rights"), (29, "terminal_receivables")):
            f = m.make_fixture(30, [20]); extend_action_calendar(f)
            f["actions"] = [dict(event_id="D", asset=m.ASSETS[0], known_index=20,
                                  record_index=28, ex_index=ex, pay_index=31,
                                  cash_per_share=".01", share_multiplier="1")]
            r = m.run_account(f)
            self.assertTrue(r["summary"]["terminal_unsettled"])
            self.assertTrue(r["summary"][expected])
            other = "terminal_receivables" if ex == 30 else "terminal_unexercised_rights"
            self.assertFalse(r["summary"][other])
            cash = m.run_account(f, "cash")
            self.assertFalse(cash["summary"]["terminal_unsettled"])

    def test_five_complete_flat_days_and_quarter_eligibility(self):
        f = m.make_fixture(50, [20, 28, 30])
        for a in m.ASSETS:
            for row in f["bars"][a][22:]: row.update(open=".80", close=".80")
        r = m.run_account(f)
        self.assertTrue(any(x["index"] == 22 and x["kind"] == "daily_2percent_pause" for x in r["risk_records"]))
        self.assertTrue(any(x["index"] == 23 and x["kind"] == "flat_cooldown_started" for x in r["risk_records"]))
        self.assertFalse(any(x["side"] == "buy" and 22 <= x["index"] <= 30 for x in r["fills"]))
        self.assertTrue(any(x["side"] == "buy" and x["index"] == 31 for x in r["fills"]))
        self.assertEqual(r["event_attempts"][1]["status"], "skipped_cash_or_not_eligible_at_previous_close")

    def test_40percent_peak_not_reset_cash_not_repeated_but_reentry_triggers(self):
        f = m.make_fixture(55, [20, 30])
        for a in m.ASSETS:
            for row in f["bars"][a][22:]: row.update(open=".50", close=".50")
        r = m.run_account(f)
        dd = [x["index"] for x in r["risk_records"] if x["kind"] == "global_40percent_pause"]
        self.assertIn(22, dd); self.assertIn(31, dd)
        self.assertFalse(any(i in dd for i in range(24, 31)))
        self.assertTrue(all(Decimal(d["peak"]) >= 10000 for d in r["days"]))
        self.assertFalse(r["summary"]["risk_ceiling_pass"])

    def test_risk_after_sell_cancels_next_buy_and_keeps_fill(self):
        f = rising_fixture()
        for a in m.ASSETS:
            f["bars"][a][40]["close"] = ".80"
            for row in f["bars"][a][41:]: row.update(open=".80", close=".80")
        r = m.run_account(f)
        self.assertTrue(any(x["index"] == 40 and x["side"] == "sell" for x in r["fills"]))
        self.assertFalse(any(x["index"] == 41 and x["side"] == "buy" for x in r["fills"]))
        self.assertTrue(any(x["index"] == 41 and x["phase"] == "risk_exit" for x in r["fills"]))

    def test_prior_capacity_zero_current_expost_fail_and_unknown_separate(self):
        f = m.make_fixture(35, [20])
        for row in f["bars"][m.ASSETS[0]][1:21]: row["volume"] = "0"
        self.assertFalse(any(x["asset"] == m.ASSETS[0] and x["side"] == "buy" for x in m.run_account(f)["fills"]))
        f = m.make_fixture(35, [20]); f["bars"][m.ASSETS[0]][21]["volume"] = "1"
        f["bars"][m.ASSETS[0]][21]["buy_blocked"] = None
        r = m.run_account(f)
        self.assertTrue(r["capacity_failures"] and r["unknown_execution_constraints"])
        self.assertTrue(any(x["asset"] == m.ASSETS[0] and x["side"] == "buy" for x in r["fills"]))
        del f["bars"][m.ASSETS[0]][0]["volume"]
        with self.assertRaises(KeyError): m.run_account(f)

    def test_terminal_overrides_pending_buy_and_residual_is_unsettled(self):
        f = rising_fixture(42, [20, 40])
        r = m.run_account(f)
        self.assertTrue(all(x["side"] == "sell" for x in r["fills"] if x["index"] == 41))
        self.assertEqual(r["event_attempts"][1]["status"], "cancelled_by_terminal_or_carried_risk")
        f["bars"][m.ASSETS[0]][41]["sell_blocked"] = True
        self.assertTrue(m.run_account(f)["summary"]["terminal_unsettled"])

    def test_exdate_target_uses_previous_NAV_not_new_receivable(self):
        f = m.make_fixture(45, [20, 30])
        f["actions"] = [dict(event_id="D", asset=m.ASSETS[0], known_index=20, record_index=28,
                              ex_index=30, pay_index=33, cash_per_share=".10", share_multiplier="1")]
        r = m.run_account(f)
        prior = next(x for x in r["days"] if x["index"] == 29)
        self.assertEqual(r["event_attempts"][1]["previous_NAV"], prior["NAV"])

    def test_bootstrap_shared_indices_and_exclusive_persistence(self):
        annual = {}
        for minimum, slip in m.COSTS:
            values = {str(2001+i): str(i+1) for i in range(10)}
            annual[f"min{minimum}_slip{slip}"] = {"constant_mix": values, "drift": dict.fromkeys(values, "0")}
        r = m.paired_annual_bootstrap(annual)
        self.assertEqual(len(set(r["lower"].values())), 1)
        self.assertEqual(len(r["endpoint_keys"]), 18)
        self.assertEqual(r["N"], 10)
        with TemporaryDirectory() as td:
            p = Path(td)/"artificial"
            result = m.run_matrix(m.make_fixture(25, [20]), p)
            self.assertEqual(len(result["accounts"]), 27)
            self.assertFalse(result["artificial_method_checks"]["checks"]["ten_annual_buckets"])
            self.assertFalse(result["artificial_method_checks"]["qualified"])
            self.assertEqual(json.loads((p/"result.json").read_text())["source_nature"], m.SOURCE)
            with self.assertRaises(FileExistsError): m.run_matrix(m.make_fixture(25, [20]), p)

    def test_fixed_matrix_checks_do_not_use_counterfactual_fee_cell_to_rescue(self):
        summaries, annual, events = {}, {}, {}
        for minimum, slip in m.COSTS:
            cost = f"min{minimum}_slip{slip}"
            annual[cost] = {}
            for policy in ("constant_mix", "drift", "cash"):
                key = cost+"/"+policy
                value = "10" if policy == "constant_mix" else "1"
                annual[cost][policy] = {str(2001+i): value for i in range(10)}
                summaries[key] = dict(initial_two_assets_filled=True, terminal_unsettled=False,
                                      capacity_pass=True, risk_ceiling_pass=True, attribution_reconciled=True,
                                      terminal_cash_netPnL="100", terminal_cash="10100" if policy == "constant_mix" else "10010")
                events[key] = [dict(date=f"{2001+i//4}-01-01", sell_fills=1, buy_fills=1) for i in range(40)]
        stats = {"lower": {"min5_slip10/net": 1, "min5_slip10/increment": 1}}
        good = m._matrix_checks(summaries, annual, events, stats)
        self.assertTrue(good["all_artificial_checks_pass"])
        summaries["min5_slip10/constant_mix"]["terminal_cash_netPnL"] = "-1"
        self.assertFalse(m._matrix_checks(summaries, annual, events, stats)["all_artificial_checks_pass"])


if __name__ == "__main__":
    unittest.main()
