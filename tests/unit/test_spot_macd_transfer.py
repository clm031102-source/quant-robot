from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D, localcontext, getcontext, ROUND_DOWN, InvalidOperation
import ast
import hashlib
import inspect
import unittest

import numpy as np
from quant_robot.research import indicator_combinations as legacy
from quant_robot.research import spot_macd_transfer as m


def constant_fixture(n=12, warmup=40, price="100"):
    f = m.fixed_artificial_fixture(sessions=n, warmup=warmup)
    for row in f["daily"]:
        for key in ("open", "high", "low", "close"):
            row[key] = price
    for row in f["execution"]:
        row["open"] = price
    return f


def forced_prepared(n=12, state=True, price="100"):
    # Private state-machine tests: invented price fixture, explicit desired-state trace.
    p = m.validate_synthetic_fixture(constant_fixture(n, price=price))
    return replace(p, states=(state,)*len(p.states))


class SourceAndSignalTests(unittest.TestCase):
    def test_nonfinite_computed_histogram_is_rejected_not_long(self):
        closes = [f"1e{300-10*i}" for i in range(33)] + ["1e-20"]
        with self.assertRaisesRegex(ValueError, "Nonfinite computed MACD histogram"):
            m.macd_frame(closes)
        warmup = m.macd_frame(["100"]*33)
        self.assertTrue(warmup.desired.isna().all())

    def test_invalid_numeric_string_preserves_ambient_context(self):
        for public_entry in (m.run_account, m.run_synthetic_suite):
            f = constant_fixture()
            f["daily"][0]["close"] = "not_a_decimal"
            with localcontext() as ambient:
                ambient.clear_flags()
                ambient.traps[InvalidOperation] = False
                before = m.context_record(ambient)
                with self.assertRaises(InvalidOperation):
                    public_entry(f)
                self.assertEqual(before, m.context_record(getcontext()))

    def test_public_rejects_real_identity_calendar_and_source_wrapper(self):
        for mutation in (lambda f:f.update(asset_id="BTCUSDT"),
                         lambda f:f.update(calendar_origin="2019-01-01"),
                         lambda f:f.update(source_path="actual.zip")):
            f = constant_fixture(); mutation(f)
            with self.assertRaises(ValueError):
                m.run_account(f)

    def test_exact_coverage_and_numeric_guard(self):
        for mutation in (lambda f:f["daily"].pop(),
                         lambda f:f["execution"][1].update(open_time=f["execution"][0]["open_time"]),
                         lambda f:f["daily"][0].update(volume="NaN"),
                         lambda f:f["daily"][0].update(high="99"),
                         lambda f:f["daily"][0].update(close=100.0)):
            f = constant_fixture(); mutation(f)
            with self.assertRaises(ValueError):
                m.validate_synthetic_fixture(f)

    def test_exact_original_frozen_signal_and_causal_prefix(self):
        source = inspect.getsource(legacy.indicator_frame)
        source = ast.get_source_segment(source, ast.parse(source).body[0])
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),
                         "62dc2f56b0eb3db8068a7a8d07248f5e53c4a0a0e4243b9e74217da45c32254d")
        f = m.fixed_artificial_fixture(sessions=100, warmup=40)
        bars = [dict(r, asset_id=m.SYMBOL, amount="12345") for r in f["daily"]]
        with localcontext(m.context(28)):
            expected = legacy.indicator_frame(bars, [])
        actual = m.macd_frame([r["close"] for r in bars])
        np.testing.assert_array_equal(actual.signal_price, expected.signal_price)
        np.testing.assert_array_equal(actual.macd_histogram, expected.macd_histogram)
        self.assertEqual(actual.desired.tolist(), expected.macd_positive.tolist())
        prefix = m.macd_frame([r["close"] for r in bars[:71]])
        np.testing.assert_array_equal(prefix.macd_histogram, actual.macd_histogram.iloc[:71])

    def test_float_and_finance_context_do_not_mutate_ambient(self):
        f = m.fixed_artificial_fixture(sessions=65, warmup=40)
        expected = m.run_account(f)
        with localcontext() as ambient:
            ambient.prec = 12; ambient.rounding = ROUND_DOWN
            D(1)/D(3)
            before = m.context_record(ambient)
            actual = m.run_account(f)
            self.assertEqual(before, m.context_record(getcontext()))
        self.assertEqual(expected, actual)
        self.assertEqual(actual["signal_arithmetic"]["decimal"]["prec"], 28)
        self.assertTrue(actual["signal_arithmetic"]["decimal"]["flags"]["Inexact"])
        self.assertEqual(actual["signal_arithmetic"]["floating"]["dtype"], "float64")
        self.assertEqual(actual["decimal_context"]["prec"], 40)


class WalletTests(unittest.TestCase):
    def setUp(self):
        self.guard = localcontext(m.context()); self.guard.__enter__()

    def tearDown(self):
        self.guard.__exit__(None, None, None)

    def test_future_open_cannot_resize_full_cash_buy(self):
        a = m._Account((10, 0), "strategy"); a.price = D(100)
        order = a.plan("buy", D(100), "new_cycle", 0, "c1")
        self.assertEqual(order["quantity"], D(10))
        a.observe(D("100.1"), 0, "prefill")
        self.assertIsNone(a.fill(order, D("100.1"), 0))
        self.assertEqual((a.cash, a.q, a.fills), (D(1000), D(0), []))

    def test_buy_base_fee_sell_quote_fee_fifo_dust_and_terminal_haircut(self):
        a = m._Account((10, 0), "strategy"); a.price = D(100300)
        order = a.plan("buy", D(100), "new_cycle", 0, "c1")
        fill = a.fill(order, a.price, 0)
        self.assertEqual(fill["quantity"], D(".00997"))
        self.assertEqual(fill["base_fee"], D(".00000997"))
        self.assertEqual(a.q, D(".00996003"))
        a.exit_reason = "signal_off"
        sell = a.plan("sell", D(100), "signal_off", 1, "c1")
        a.fill(sell, a.price, 1)
        self.assertEqual(a.q, D(".00000003"))
        self.assertTrue(a.economic_flat)
        self.assertFalse(a.q == 0)
        old_lot = a.lots[0]
        order2 = a.plan("buy", D(100), "new_cycle", 2, "c2")
        a.fill(order2, a.price, 2)
        a.exit_reason = "terminal"
        a.fill(a.plan("sell", D(100), "terminal", 3, "c2"), a.price, 3)
        self.assertEqual(old_lot["remaining_BTC"], 0)
        summary = a.finish(3, "2001-01-04")
        self.assertEqual(summary["terminal_evaluation_NAV"], a.cash)
        self.assertGreater(summary["mark_NAV"], a.cash)
        self.assertTrue(summary["terminal_strict_unsettled"])
        self.assertEqual(summary["strict_completed_episodes"], 1)
        self.assertGreaterEqual(summary["sampled_DD_including_terminal_haircut"], summary["sampled_DD_before_haircut"])

    def test_bought_substep_and_notional_block_are_not_exited_dust(self):
        a = m._Account((10, 0), "strategy"); a.price = D(500000); a.cash = D(5)
        buy = a.plan("buy", D(100), "new_cycle", 0, "c1")
        a.fill(buy, a.price, 0)
        self.assertEqual(a.q, D(".00000999"))
        self.assertFalse(a.economic_flat)
        a.exit_reason = "risk"
        self.assertIsNone(a.plan("sell", D(100), "risk", 1))
        a.q, a.price, a.exited_residual = D(".00002"), D(100000), True
        self.assertFalse(a.economic_flat)
        self.assertIsNone(a.plan("sell", D(100), "risk", 1))

    def test_dust_persistent_dd_can_cool_but_reentry_retriggers(self):
        a = m._Account((10, 0), "strategy")
        a.cash, a.q, a.price = D(599), D(".00000001"), D(100)
        a.exited_residual, a.paused, a.previous_dd = True, True, D(".400999999")
        for day in range(5):
            a.start_day(day)
            self.assertFalse(a.observe(D(100), day, "close"))
            a.end_day(day, f"artificial{day}")
        self.assertEqual(a.cooldown, 5)
        a.start_day(5)
        self.assertFalse(a.paused)
        a.fill(a.plan("buy", D(100), "new_cycle", 5, "c1"), D(100), 5)
        self.assertTrue(a.paused)
        self.assertEqual(a.cooldown, 0)
        self.assertTrue(a.risks[-1]["DD_event"])

    def test_dust_fresh_dd_cross_and_new_daily_loss_reset(self):
        a = m._Account((10, 0), "strategy")
        a.cash, a.q, a.price = D("599.999"), D(".000009"), D(200)
        a.exited_residual = True; a.previous_dd = D(".3999992"); a.cooldown = 4
        a.start_day(0)
        self.assertTrue(a.observe(D(100), 0, "open"))
        self.assertTrue(a.risks[-1]["fresh_DD_cross"])
        self.assertEqual(a.cooldown, 0)
        b = m._Account((10, 0), "strategy")
        b.cash, b.q, b.price, b.peak = D(500), D(".000009"), D(10000000), D(590)
        b.exited_residual=True; b.cooldown=4; b.start_day(0)
        self.assertTrue(b.observe(D(8000000), 0, "open"))
        self.assertTrue(b.risks[-1]["daily_event"])
        self.assertEqual(b.cooldown, 0)

    def test_legal_exit_day_excluded_and_five_complete_days(self):
        a = m._Account((10, 0), "strategy"); a.price = D(100300)
        a.fill(a.plan("buy", D(100), "new_cycle", 0, "c1"), a.price, 0)
        a.paused=True; a.exit_reason="risk"
        a.fill(a.plan("sell", D(100), "risk", 1, "c1"), a.price, 1)
        a.end_day(1, "exitday")
        self.assertEqual(a.cooldown, 0)
        for day in range(2, 7):
            a.start_day(day); self.assertTrue(a.paused)
            a.observe(a.price, day, "close"); a.end_day(day, "flatday")
        self.assertEqual(a.cooldown, 5)
        a.start_day(7); self.assertFalse(a.paused)

    def test_prefill_breach_is_permanent_and_no_new_same_open_sell(self):
        p = forced_prepared(n=5)
        minutes = list(p.execution); minutes[1] = replace(minutes[1], open=D(90))
        p = replace(p, execution=tuple(minutes))
        result = m._run_prepared(p, (10, 0), "strategy")
        self.assertTrue(any(r["index"] == 1 and r["phase"] == "00:03_prefill" and r["daily_event"] for r in result["risk_records"]))
        self.assertFalse(any(f["index"] == 1 and f["side"] == "sell" for f in result["fills"]))
        self.assertTrue(any(f["index"] == 2 and f["side"] == "sell" for f in result["fills"]))


class CycleAndSuiteTests(unittest.TestCase):
    def test_252_strategy_no_reentry_and_holding_fixed_cycles(self):
        p = forced_prepared(n=260)
        strategy = m._run_prepared(p, (10, 0), "strategy")
        holding = m._run_prepared(p, (10, 0), "holding")
        self.assertEqual([(f["index"], f["side"]) for f in strategy["fills"]], [(0,"buy"),(252,"sell")])
        self.assertEqual([(f["index"], f["side"]) for f in holding["fills"]], [(0,"buy"),(252,"sell"),(253,"buy"),(259,"sell")])

    def test_holding_rejected_first_cycle_does_not_daily_retry(self):
        p = forced_prepared(n=255)
        minutes=list(p.execution); minutes[0]=replace(minutes[0],open=D(101))
        result=m._run_prepared(replace(p,execution=tuple(minutes)),(10,0),"holding")
        self.assertEqual([f["index"] for f in result["fills"] if f["side"]=="buy"],[253])
        self.assertEqual(result["cycles"][0]["entry_status"],"execution_rejected")
        self.assertGreater(result["summary"]["full_cash_days"],250)

    def test_terminal_intent_blocks_new_signal_and_capacity_is_expost(self):
        p=forced_prepared(n=5,state=False)
        states=list(p.states);states[-1]=True
        self.assertEqual(m._run_prepared(replace(p,states=tuple(states)),(10,0),"strategy")["fills"],[])
        p=forced_prepared(n=5)
        normal=m._run_prepared(p,(10,0),"strategy")
        minutes=list(p.execution);minutes[0]=replace(minutes[0],volume=D(0))
        bad=m._run_prepared(replace(p,execution=tuple(minutes)),(10,0),"strategy")
        self.assertEqual(normal["fills"],bad["fills"])
        self.assertEqual(normal["daily_NAV"],bad["daily_NAV"])
        self.assertTrue(bad["summary"]["execution_capacity_unverified"])
        self.assertFalse(bad["summary"]["common_valid"])

    def test_short_27_cost_roles_are_explicit_and_cash_identity(self):
        result=m.run_synthetic_suite(m.fixed_artificial_fixture(sessions=45,warmup=40))
        self.assertEqual(result["account_count"],27)
        self.assertFalse(result["full_fixed_statistics_completed"])
        self.assertFalse(result["qualified"])
        self.assertEqual(len(result["summaries"]),27)
        self.assertTrue(result["checks"]["all9_cash_identity"])
        for fee,slip in m.CASES:
            for role in m.ROLES:
                self.assertIn(f"fee{fee}_slip{slip}/{role}",result["summaries"])

    def test_bootstrap_exact_shared_index_stream_and_units(self):
        accounts={}; values=np.arange(1827,dtype=float)%31-15
        for j,(fee,slip) in enumerate(m.CASES):
            for role in ("strategy","holding"):
                vec=values+j if role=="strategy" else np.zeros(1827)
                accounts[f"fee{fee}_slip{slip}/{role}"]={"evidence_class":"synthetic_only","fixture_sha256":"artificial",
                    "daily_NAV":[{"PnL":str(v)} for v in vec]}
        result=m.paired_bootstrap(accounts)
        rng=np.random.Generator(np.random.PCG64(20261107))
        reference=[]
        for _ in range(5000):
            starts=rng.integers(0,1827,size=92)
            indices=[(int(start)+offset)%1827 for start in starts for offset in range(20)][:1827]
            reference.append(values[indices].mean())
        lower=float(np.quantile(reference,.05/18,method="linear"))
        self.assertEqual(result["lower"]["fee5_slip0/net"],lower)
        self.assertEqual(result["lower"]["fee5_slip0/net"],result["lower"]["fee5_slip0/minus_holding"])
        self.assertAlmostEqual(result["lower"]["fee20_slip30/net"],lower+8,places=12)
        self.assertEqual(result["units"],"USDT/observed interval")
        accounts["fee20_slip30/strategy"]["fixture_sha256"]="wrong"
        with self.assertRaises(ValueError):m.paired_bootstrap(accounts)


if __name__ == "__main__":
    unittest.main()
