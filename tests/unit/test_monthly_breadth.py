"""Invented prices and calendar only. No source files or financial admission."""
import copy
from datetime import date, timedelta
from decimal import Decimal, getcontext, localcontext
import unittest

from quant_robot.research import monthly_breadth as m


def fixture():
    days, current = [], date(2000, 12, 1)
    while current <= date(2002, 3, 1):
        if current.weekday() < 5:
            days.append(current.isoformat())
        current += timedelta(days=1)
    ends = [i for i in range(len(days)-1) if days[i][:7] != days[i+1][:7]]
    first = ends[12]
    decisions = [i for i in ends[12:] if i+2 < len(days)-1]
    bars = {a: [dict(open="1.20", close="1.20", volume="10000000", suspended=False,
                    buy_blocked=False, sell_blocked=False) for _ in days] for a in m.ASSETS}
    for asset, price in zip(m.ASSETS, ("1.30", "1.10")):
        for row in bars[asset][first:]:
            row.update(open=price, close=price)
        bars[asset][-1].update(close=None, terminal_close_not_observed=True)
    return dict(artifact_type="artificial_monthly_breadth_fixture_v1", source_nature=m.SOURCE,
                constructed_from_market_data=False, assets=list(m.ASSETS), dates=days, bars=bars,
                month_end_sessions=[days[i] for i in ends], first_signal_index=first,
                monthly_decision_indices=decisions, event_indices=[i+1 for i in decisions],
                terminal_index=len(days)-1, actions=[], actions_complete=True)


class MonthlyBreadthTests(unittest.TestCase):
    def test_four_sign_states_exact_equality_and_distinct_discordance(self):
        for signs in ((0, 0), (0, 1), (1, 0), (1, 1)):
            with self.subTest(signs=signs):
                self.assertEqual(m._weights(signs, "breadth"), (Decimal(sum(signs))/4,)*2)
                self.assertEqual(m._weights(signs, "own_trend"), tuple(Decimal(s)/2 for s in signs))
        f = fixture()
        d = f["first_signal_index"]
        f["bars"][m.ASSETS[0]][d]["close"] = "1.20"
        self.assertEqual(m.signal_frame(f)[0]["signs"], [0, 0])
        f["bars"][m.ASSETS[0]][d]["close"] = "1.20000000000001"
        self.assertEqual(m.signal_frame(f)[0]["signs"], [1, 0])

    def test_ex_distribution_TR_and_actual_pay_cash_are_separate(self):
        f = fixture()
        d = f["first_signal_index"]
        for a in m.ASSETS:
            for row in f["bars"][a][:f["terminal_index"]]:
                row.update(open="1.20", close="1.20")
        ex = d-2
        for row in f["bars"][m.ASSETS[0]][ex:f["terminal_index"]]:
            row.update(open="1.10", close="1.10")
        f["actions"] = [dict(event_id="invented_warmup", asset=m.ASSETS[0], known_index=ex-2,
            record_index=ex-1, ex_index=ex, pay_index=d+3, cash_per_share=".10", share_multiplier="1")]
        signals = m.signal_frame(f)
        self.assertEqual(signals[0]["TR"][m.ASSETS[0]], "100")
        self.assertEqual(signals[0]["signs"], [0, 0])
        result = m.run_account(f, "monthly_50_50")
        self.assertEqual(result["action_records"], [])  # no held record-date units in warmup
        f = fixture()
        record = f["event_indices"][0]+2
        f["actions"] = [dict(event_id="invented_held", asset=m.ASSETS[0], known_index=record-1,
            record_index=record, ex_index=record+1, pay_index=record+2, cash_per_share=".01", share_multiplier="1")]
        result = m.run_account(f)
        records = result["action_records"]
        self.assertEqual([r["kind"] for r in records], ["record_right", "ex_receivable", "pay_after_fills"])
        self.assertEqual(result["attribution"]["dividend_entitlement"], records[1]["amount"])
        self.assertEqual(records[1]["amount"], records[2]["amount"])

    def test_calendar_action_and_identity_guards(self):
        cases = []
        f = fixture(); f["month_end_sessions"].pop(4); cases.append(f)
        f = fixture(); f["actions_complete"] = False; cases.append(f)
        for bad in (dict(record_index=12, ex_index=12, share_multiplier="1"),
                    dict(record_index=12, ex_index=13, share_multiplier="10"),
                    dict(record_index=12, ex_index=13, share_multiplier="1", known_index=14)):
            f = fixture()
            f["actions"] = [dict(event_id="bad", asset=m.ASSETS[0], known_index=10,
                record_index=12, ex_index=13, pay_index=14, cash_per_share=".01", share_multiplier="1") | bad]
            cases.append(f)
        f = fixture(); f["constructed_from_market_data"] = True; cases.append(f)
        for f in cases:
            with self.subTest(case=cases.index(f)), self.assertRaises(ValueError):
                m.run_account(f)

    def test_two_phase_initial_and_terminal_priority(self):
        f = fixture(); r = m.run_account(f)
        first = f["event_indices"][0]
        self.assertEqual(min(x["index"] for x in r["fills"]), first+1)
        self.assertTrue(all(x["phase"] == "monthly_buy" for x in r["fills"] if x["index"] == first+1))
        event = r["event_attempts"][0]
        self.assertEqual(event["signal_index"], first-1)
        self.assertEqual(event["targets"], {m.ASSETS[0]: 1900, m.ASSETS[1]: 2200})
        self.assertEqual(event["reserve"], "40.00")
        self.assertTrue(r["signal_frame"][-1]["terminal_overrides"])
        self.assertEqual(len(r["event_attempts"]), len(f["event_indices"]))
        terminal = f["terminal_index"]
        self.assertTrue(all(x["side"] == "sell" and x["phase"] == "terminal" for x in r["fills"] if x["index"] == terminal))
        self.assertTrue(r["days"][-1]["terminal_open_stub"])
        self.assertFalse(r["summary"]["terminal_unsettled"])
        self.assertTrue(r["summary"]["terminal_inventory_and_rights_closed"])
        self.assertFalse(r["summary"]["terminal_cash_netPnL_is_fully_settled"])
        self.assertGreater(Decimal(r["summary"]["terminal_locked_sale_cash"]), 0)

    def test_gap_budget_frozen_and_no_reallocation(self):
        f = fixture(); original = m.run_account(f)
        buy = f["event_indices"][0]+1
        f["bars"][m.ASSETS[0]][buy]["open"] = "1.301"
        f["bars"][m.ASSETS[1]][buy]["open"] = "4.00"
        changed = m.run_account(f)
        self.assertEqual(original["event_attempts"][0]["buy_orders"], changed["event_attempts"][0]["buy_orders"])
        filled = [x for x in changed["fills"] if x["index"] == buy]
        self.assertEqual([x["asset"] for x in filled], [m.ASSETS[0]])
        self.assertEqual(filled[0]["quantity"], original["event_attempts"][0]["buy_orders"][0]["quantity"])
        self.assertTrue(any(x["index"] == buy and x["reason"] == "frozen_budget_or_spendable_cash" for x in changed["rejections"]))
        # An inexpensive first leg never transfers its unused frozen budget.
        f["bars"][m.ASSETS[0]][buy]["open"] = ".60"
        self.assertTrue(any(x["index"] == buy and x["asset"] == m.ASSETS[1] and x["reason"] == "frozen_budget_or_spendable_cash"
                            for x in m.run_account(f)["rejections"]))

    def test_future_input_does_not_change_prefix_or_prior_capacity(self):
        f = fixture(); original = m.run_account(f)
        buy = f["event_indices"][0]+1
        for a in m.ASSETS:
            for row in f["bars"][a][buy+3:f["terminal_index"]]:
                row.update(open="1.80", close="1.80", volume="20000000")
            f["bars"][a][buy]["volume"] = "100"
        changed = m.run_account(f)
        self.assertEqual(original["event_attempts"][0]["buy_orders"], changed["event_attempts"][0]["buy_orders"])
        self.assertEqual([x for x in original["fills"] if x["index"] == buy], [x for x in changed["fills"] if x["index"] == buy])
        self.assertEqual(original["signal_frame"][0], changed["signal_frame"][0])
        self.assertTrue(changed["capacity_failures"])
        self.assertEqual(changed["capacity_failures"][0]["reason"], "ex_post_day_volume_failed_trade_retained")

    def test_risk_exit_five_full_days_next_month_not_daily(self):
        f = fixture(); first = f["event_indices"][0]
        drop = first+3
        for a in m.ASSETS:
            for row in f["bars"][a][drop:f["terminal_index"]]:
                row.update(open=".30", close=".30")
        r = m.run_account(f, "monthly_50_50")
        hits = [x for x in r["risk_records"] if x["kind"] == "global_40percent_pause"]
        self.assertTrue(hits)
        start = next(x["index"] for x in r["risk_records"] if x["kind"] == "flat_cooldown_started")
        eligible = next(x["index"] for x in r["risk_records"] if x["kind"] == "eligible_from_next_session_only_next_month")
        self.assertEqual(eligible, start+5)
        self.assertTrue(all(x["index"] in {i+1 for i in f["event_indices"]} for x in r["fills"] if x["side"] == "buy"))
        self.assertGreaterEqual(Decimal(r["summary"]["observed_maxDD"]), Decimal(".40"))
        self.assertTrue(all(Decimal(x["peak"]) >= 10000 for x in r["days"]))

    def test_unknown_execution_is_disclosed_and_known_block_rejects(self):
        f = fixture(); buy = f["event_indices"][0]+1
        f["bars"][m.ASSETS[0]][buy]["buy_blocked"] = None
        f["bars"][m.ASSETS[1]][buy]["suspended"] = True
        r = m.run_account(f)
        self.assertTrue(any(x["index"] == buy and x["asset"] == m.ASSETS[0] for x in r["fills"]))
        self.assertTrue(r["unknown_execution_constraints"])
        self.assertTrue(any(x["index"] == buy and x["reason"] == "known_execution_constraint" for x in r["rejections"]))
        self.assertFalse(r["qualified"])

    def test_fee_rate_cost_identity_cash_and_context_isolation(self):
        before = m._context_record(getcontext())
        with localcontext(m.CONTEXT):
            self.assertEqual(m._fee(Decimal("10000"), 0), Decimal("1.00"))
            self.assertEqual(m._fee(Decimal("10000"), 5), Decimal("5.00"))
            self.assertEqual(m._reserve(Decimal("200000")), Decimal("80.00"))
        f = fixture(); f["bars"][m.ASSETS[0]][0]["open"] = "not-a-decimal"
        with self.assertRaises(Exception): m.run_account(f)
        self.assertEqual(before, m._context_record(getcontext()))
        for minimum, slip in ((False, 0), (0, False), (5.0, 10), (5, 10.0)):
            with self.subTest(cost=(minimum, slip)), self.assertRaises(ValueError):
                m.run_account(fixture(), minimum=minimum, slip=slip)
        r = m.run_account(fixture(), "cash", 0, 0)
        self.assertEqual(r["fills"], [])
        self.assertEqual(r["summary"]["terminal_cash"], "10000")
        self.assertEqual(r["summary"]["total_commission"], "0")
        self.assertEqual(before, m._context_record(getcontext()))

    def test_terminal_pending_record_right_not_double_counted(self):
        f = fixture(); terminal = f["terminal_index"]
        # Future action dates exist in the explicit calendar, but no later prices.
        f["dates"] += ["2002-03-04", "2002-03-05"]
        f["actions"] = [dict(event_id="future_right", asset=m.ASSETS[0], known_index=terminal-2,
            record_index=terminal-1, ex_index=terminal+1, pay_index=terminal+2, cash_per_share=".01", share_multiplier="1")]
        r = m.run_account(f, "monthly_50_50")
        self.assertTrue(r["summary"]["terminal_unsettled"])
        self.assertFalse(r["summary"]["unexercised_rights_included_in_NAV"])
        self.assertEqual(r["summary"]["terminal_receivables"], {})
        self.assertTrue(r["summary"]["terminal_unexercised_rights"])

    def test_terminal_open_does_not_receive_later_pay_cash(self):
        f = fixture(); terminal = f["terminal_index"]
        f["actions"] = [dict(event_id="terminal_pay", asset=m.ASSETS[0], known_index=terminal-3,
            record_index=terminal-2, ex_index=terminal-1, pay_index=terminal, cash_per_share=".01", share_multiplier="1")]
        r = m.run_account(f, "monthly_50_50")
        self.assertEqual([x["kind"] for x in r["action_records"]], ["record_right", "ex_receivable"])
        self.assertTrue(r["summary"]["terminal_unsettled"])
        amount = Decimal(r["summary"]["terminal_receivables"]["terminal_pay"]["amount"])
        self.assertGreater(amount, 0)
        self.assertEqual(Decimal(r["summary"]["terminal_book_NAV"]), Decimal(r["summary"]["terminal_cash"])+amount)
        locked = Decimal(r["summary"]["terminal_locked_sale_cash"])
        self.assertGreater(locked, 0)
        self.assertEqual(Decimal(r["summary"]["terminal_spendable_cash"])+locked, Decimal(r["summary"]["terminal_cash"]))
        self.assertEqual(r["days"][-1]["after"]["locked_sale_cash"], r["summary"]["terminal_locked_sale_cash"])

    def test_fixed_paired_bootstrap_27_endpoints(self):
        annual = {}
        for minimum, slip in m.COSTS:
            annual[f"min{minimum}_slip{slip}"] = {
                p: {str(2002+y): str((y-3)*(j+1)+minimum-slip) for y in range(9)}
                for j, p in enumerate(m.POLICIES)}
        r = m.paired_annual_bootstrap(annual)
        self.assertEqual((r["N"], r["block"], r["starts_per_replication"], r["truncate_rows_to"]), (9, 2, 5, 9))
        self.assertEqual(len(r["endpoint_keys"]), 27)
        self.assertTrue(r["shared_indices_for_all27"])
        self.assertEqual(r["quantile"], .05/27)
        # All net vectors differ only by constants: paired replicate shifts hold.
        self.assertAlmostEqual(r["lower"]["min5_slip0/breadth_net"]-r["lower"]["min0_slip0/breadth_net"], 5)
        self.assertFalse(r["historical_returns_computed"])
        self.assertFalse(r["qualified"])


if __name__ == "__main__":
    unittest.main()
