"""Hand-calculated synthetic invariants; no market files, requests or backtests."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from quant_robot.research.crypto_carry_model import CarryModel, FeeScenario, Leg, TradingRule, dec

D = Decimal
T0 = datetime(2001, 1, 1, tzinfo=timezone.utc)


def model(*, fees=None, minimum="10", spot_cash="500", futures_cash="500"):
    result = CarryModel(start=T0, spot_rule=TradingRule("0.001", "0.001", minimum),
                        futures_rule=TradingRule("0.001", "0.001", minimum),
                        fees=fees or FeeScenario("0", "0", "0"),
                        spot_cash=spot_cash, futures_cash=futures_cash)
    result.queue_quote(T0, spot="1000")
    result.run(T0)
    return result


def hedge(m, q="0.4"):
    assert m.register_plan((Leg("spot_buy", q), Leg("short_open", q)))
    m.run(T0 + timedelta(minutes=2))


def funding_exit_with_dust(short_quantity="0.049"):
    """Funding interrupts a pending paired reduction; no artificial pause/state edit."""
    m = CarryModel(start=T0, spot_rule=TradingRule("0.00001", "0.00001", "10"),
                   futures_rule=TradingRule("0.001", "0.001", "10"),
                   fees=FeeScenario("0.001", "0", "0"))
    m.queue_quote(T0, spot="1000")
    m.run(T0)
    assert m.register_plan((Leg("spot_buy", "0.05"), Leg("short_open", short_quantity)))
    m.run(T0 + timedelta(minutes=2))
    assert m.register_plan((Leg("short_close", short_quantity), Leg("spot_sell", short_quantity)), kind="rebalance")
    m.queue_funding(T0 + timedelta(minutes=3), rate="-0.5", mark="1000")
    m.run(T0 + timedelta(minutes=4))
    return m


class CryptoCarryModelTests(unittest.TestCase):
    def test_event_mark_breach_is_latched_before_positive_funding_can_mask_it(self):
        m = model()
        hedge(m)
        at = T0 + timedelta(minutes=3, milliseconds=15)
        m.queue_funding(at, rate='.2', mark='1200')
        m.run(at)
        # Before funding: equity420 < notional480. After96 receipt: equity516.
        self.assertEqual(m.funding_cash, D('96'))
        self.assertEqual(m.futures_equity, D('516'))
        self.assertTrue(m.paused)
        self.assertIn('futures_wallet_below_1x', m.failures)
        observed = next(r for r in m.journal if r['event']=='risk_observation'
                        and r['observation']=='funding_event_mark_before_cash')
        self.assertEqual((D(observed['futures_equity']), D(observed['short_mark_notional'])),
                         (D('420'), D('480')))
        funding = next(i for i,r in enumerate(m.journal) if r['event']=='funding')
        self.assertLess(m.journal.index(observed), funding)

    def test_strict_kernel_day_end_missing_close_leaves_clock_and_event_unconsumed(self):
        m = model()
        at = T0 + timedelta(days=1)
        m.queue_day_end(at, completed_close=True)
        with self.assertRaisesRegex(ValueError,'completed final minute'):
            m.run(at)
        self.assertEqual(m.now, T0)
        self.assertEqual(m.daily_reference, D('1000'))
        self.assertEqual(m._events[0][3], 'day_end')
        m.queue_completed_close(closed_at=at, available_at=at, spot='1000', future='1000', mark='1000')
        m.run(at)
        self.assertEqual(m.daily_reference, D('1000'))
        self.assertEqual([r for r in m.journal if r['event']=='day_end'][-1]['day'], '2001-01-01')

    def test_base_asset_fee_keeps_actual_net_BTC_and_residual(self):
        m = model(fees=FeeScenario("0.001", "0.0005", "0"))
        self.assertTrue(m.register_plan((Leg("spot_buy", "0.05"), Leg("short_open", "0.049"))))
        m.run(T0 + timedelta(minutes=2))
        self.assertEqual(m.base_fee_btc, D("0.00005"))
        self.assertEqual(m.spot_btc, D("0.04995"))
        self.assertEqual(m.short_btc, D("0.049"))
        self.assertEqual(m.delta_btc, D("0.00095"))
        self.assertEqual(m.nav, D("999.9255"))
        self.assertEqual(m.futures_cash, D("499.9755"))
        self.assertFalse(m.snapshot()["qualified"])
        self.assertEqual(m.snapshot()["real_forward"], 0)

    def test_short_entry_VWAP_realization_and_mark_are_not_double_counted(self):
        m = model(minimum="0")
        hedge(m, "0.1")
        m.queue_quote(T0 + timedelta(minutes=3), spot="1100")
        m.run(T0 + timedelta(minutes=3))
        self.assertTrue(m.register_plan((Leg("spot_buy", "0.1"), Leg("short_open", "0.1"))))
        m.run(T0 + timedelta(minutes=5))
        self.assertEqual(m.entry_vwap, D("1050"))
        self.assertEqual(m.unrealized_futures, D("-10"))
        self.assertTrue(m.register_plan((Leg("short_close", "0.1"), Leg("spot_sell", "0.1")), kind="rebalance"))
        m.run(T0 + timedelta(minutes=7))
        self.assertEqual(m.realized_futures, D("-5"))
        self.assertEqual(m.unrealized_futures, D("-5"))
        self.assertEqual(m.entry_vwap, D("1050"))
        self.assertEqual(m.nav, D("1000"))

    def test_price_jump_keeps_global_NAV_but_breaks_gross_and_wallet_1x(self):
        m = model()
        hedge(m)
        m.queue_quote(T0 + timedelta(minutes=3), spot="2000")
        m.run(T0 + timedelta(minutes=3))
        self.assertEqual(m.nav, D("1000"))
        self.assertEqual(m.gross, D("1600"))
        self.assertEqual(m.futures_equity, D("100"))
        self.assertIn("gross_over_100_percent", m.failures)
        self.assertIn("futures_wallet_below_1x", m.failures)
        self.assertTrue(m.paused)
        self.assertEqual(m.plan.kind, "risk_exit")

    def test_futures_125_percent_entry_buffer_and_transfer_floor(self):
        m = model(fees=FeeScenario("0", "0.001", "0"))
        self.assertTrue(m.register_plan((Leg("spot_buy", "0.4"), Leg("short_open", "0.4"))))
        m.run(T0 + timedelta(minutes=2))
        self.assertEqual(m.short_btc, 0)
        self.assertEqual(m.spot_btc, D("0.4"))
        self.assertTrue(any(row.get("reason") == "futures_125_percent_buffer" for row in m.journal))
        self.assertEqual(m.plan.kind, "repair")
        other = model()
        hedge(other)
        self.assertFalse(other.equalize_cash())
        self.assertEqual(other.futures_cash, D("500"))
        self.assertFalse(other.request_transfer("futures", "1"))

    def test_five_minute_transfer_is_not_cash_in_both_wallets(self):
        m = model()
        self.assertTrue(m.request_transfer("spot", "100"))
        self.assertEqual(m.spot_cash, D("400"))
        self.assertEqual(m.futures_cash, D("500"))
        self.assertEqual(m.nav, D("1000"))
        self.assertEqual(m.transfer.amount, D("100"))
        self.assertFalse(m.register_plan((Leg("spot_buy", "0.01"),)))
        m.run(T0 + timedelta(minutes=5) - timedelta(microseconds=1))
        self.assertEqual(m.futures_cash, D("500"))
        m.run(T0 + timedelta(minutes=5))
        self.assertIsNone(m.transfer)
        self.assertEqual(m.futures_cash, D("600"))
        self.assertEqual(m.nav, D("1000"))

    def test_unconfirmed_transfer_never_auto_arrives(self):
        m = model()
        m.request_transfer("spot", "100", confirmed=False)
        m.run(T0 + timedelta(minutes=10))
        self.assertEqual(m.futures_cash, D("500"))
        self.assertEqual(m.transfer.amount, D("100"))
        self.assertEqual(m.nav, D("1000"))
        self.assertIn("unconfirmed_transfer", m.unresolved)

    def test_exact_funding_timestamp_and_prior_position_order(self):
        m = model()
        m.register_plan((Leg("spot_buy", "0.1"), Leg("short_open", "0.1")))
        at = T0 + timedelta(minutes=2)
        m.queue_funding(at, rate="0.01", mark="1000")
        m.queue_funding(at + timedelta(milliseconds=15), rate="0.01", mark="1000")
        m.queue_funding(at + timedelta(hours=1), rate="-0.002", mark="1000")
        m.run(at + timedelta(hours=1))
        events = [row for row in m.journal if row["event"] == "funding"]
        self.assertEqual([D(row["quantity_before"]) for row in events], [D("0"), D("0.1"), D("0.1")])
        self.assertEqual([D(row["cash_delta"]) for row in events], [D("0"), D("1"), D("-0.2")])
        self.assertIn(".015000", events[1]["time"])
        self.assertEqual(m.funding_cash, D("0.8"))
        with self.assertRaises(ValueError):
            m.queue_funding(at, rate="1", mark="1000")

    def test_late_same_time_funding_cannot_rewrite_prior_order(self):
        m = model()
        hedge(m, "0.1")
        with self.assertRaises(ValueError):
            m.queue_funding(m.now, rate="0.01", mark="1000")

    def test_second_leg_failure_retains_first_leg_then_repairs_with_fees(self):
        m = model(fees=FeeScenario("0.001", "0", "0"))
        m.register_plan((Leg("spot_buy", "0.05"), Leg("short_open", "0.049")))
        at = T0 + timedelta(minutes=2)
        m.queue_quote(at, spot="1000", future="100", mark="1000")
        m.run(at)
        self.assertEqual(m.spot_btc, D("0.04995"))
        self.assertEqual(m.short_btc, 0)
        self.assertEqual(m.plan.kind, "repair")
        self.assertIn("pair_repair", m.unresolved)
        m.run(at + timedelta(minutes=1))
        self.assertEqual(m.spot_btc, D("0.00095"))
        self.assertEqual(m.spot_cash, D("498.951"))
        self.assertEqual(m.nav, D("999.901"))
        self.assertNotIn("pair_repair", m.unresolved)
        self.assertFalse(m.actually_flat)

    def test_low_notional_exit_does_not_close_only_one_leg(self):
        m = model()
        hedge(m, "0.02")
        m.queue_quote(T0 + timedelta(minutes=3), spot="100")
        m.run(T0 + timedelta(minutes=3))
        self.assertFalse(m.request_exit())
        self.assertEqual(m.short_btc, D("0.02"))
        self.assertEqual(m.spot_btc, D("0.02"))
        self.assertIsNone(m.plan)
        self.assertIn("exit_constraints", m.unresolved)

    def test_stable_excess_delta_enters_one_future_repair_plan(self):
        m = model()
        m.register_plan((Leg("spot_buy", "0.02"), Leg("short_open", "0.01")))
        m.run(T0 + timedelta(minutes=2))
        self.assertEqual(m.delta_btc, D("0.01"))
        self.assertEqual(m.plan.kind, "repair")
        m.run(T0 + timedelta(minutes=3))
        self.assertEqual(m.delta_btc, 0)
        self.assertIsNone(m.plan)
        self.assertNotIn("delta_residual", m.unresolved)

    def test_exit_priority_promotes_without_starving_second_leg(self):
        m = model()
        hedge(m, "0.1")
        self.assertTrue(m.request_exit())
        number = m.plan.number
        m.run(T0 + timedelta(minutes=3))
        self.assertEqual(m.short_btc, 0)
        self.assertEqual(m.spot_btc, D("0.1"))
        self.assertTrue(m.request_exit(terminal=True))
        self.assertTrue(m.request_exit(terminal=True))
        self.assertEqual(m.plan.number, number)
        self.assertEqual(m.plan.index, 1)
        m.run(T0 + timedelta(minutes=4))
        self.assertTrue(m.actually_flat)

    def test_drawdown_latch_resumes_after_five_complete_days_without_erasing_failure(self):
        m = model()
        hedge(m)
        hit = T0 + timedelta(hours=12)
        m.queue_funding(hit, rate="-1.025", mark="1000")
        m.run(hit + timedelta(minutes=2))
        self.assertEqual(m.nav, D("590"))
        self.assertTrue(m.actually_flat)
        self.assertEqual(m.dd_events, 1)
        self.assertFalse(m.dd_armed)
        for offset in range(6):
            m.queue_day_end(T0 + timedelta(days=offset + 1) - timedelta(microseconds=1))
        m.run(T0 + timedelta(days=6))
        self.assertEqual(m.cooldown_days, 5)
        self.assertEqual(m.dd_events, 1)
        resume = T0 + timedelta(days=6, minutes=2)
        m.queue_resume(resume)
        m.run(resume)
        self.assertFalse(m.paused)
        self.assertEqual(m.peak, D("1000"))
        self.assertEqual(m.financial_verdict, "failed")
        self.assertFalse(m.dd_armed)

    def test_dust_is_not_flat_and_disqualifying_dust_resets_cooldown(self):
        m = model(fees=FeeScenario("0.001", "0", "0"))
        m.register_plan((Leg("spot_buy", "0.01"),))
        m.run(T0 + timedelta(minutes=1))
        # Fee leaves .00999 BTC: below 10 USDT minimum notional, too large for .1% NAV.
        self.assertFalse(m.has_tradable_spot())
        self.assertFalse(m.actually_flat)
        m.paused = True
        m.cooldown_days = 4
        m.queue_quote(T0 + timedelta(minutes=2), spot="1000")
        m.run(T0 + timedelta(minutes=2))
        self.assertEqual(m.cooldown_days, 0)
        self.assertFalse(m.cooldown_eligible())

    def test_terminal_dust_write_down_preserves_inventory_and_updates_DD(self):
        m = model(fees=FeeScenario("0.001", "0", "0"))
        m.register_plan((Leg("spot_buy", "0.05"), Leg("short_open", "0.049")))
        m.queue_quote(T0 + timedelta(minutes=2), spot="1000", future="100", mark="1000")
        m.run(T0 + timedelta(minutes=3))
        before = m.spot_btc
        result = m.finish()
        self.assertEqual(m.spot_btc, before)
        self.assertFalse(result["inventory_deleted"])
        self.assertEqual(D(result["book_nav"]), D("999.901"))
        self.assertEqual(D(result["conservative_terminal_nav"]), D("998.951"))
        self.assertEqual(m.max_drawdown, D("0.001049"))
        with self.assertRaises(ValueError):
            m.queue_quote(T0 + timedelta(days=1), spot="1000")
        with self.assertRaises(ValueError):
            m.run(T0 + timedelta(days=1))

    def test_eligible_dust_can_count_cooldown_but_never_becomes_actually_flat(self):
        m = model(fees=FeeScenario("0.001", "0", "0"))
        m.register_plan((Leg("spot_buy", "0.05"), Leg("short_open", "0.049")))
        m.queue_quote(T0 + timedelta(minutes=2), spot="1000", future="100", mark="1000")
        m.run(T0 + timedelta(minutes=3))
        m.paused = True  # Separate pause fixture; this does not alter cash or inventory.
        m.queue_quote(T0 + timedelta(minutes=4), spot="1000")
        for day in range(6):
            m.queue_day_end(T0 + timedelta(days=day + 1) - timedelta(microseconds=1))
        m.run(T0 + timedelta(days=6))
        self.assertEqual(m.cooldown_days, 5)
        self.assertTrue(m.cooldown_eligible())
        self.assertFalse(m.actually_flat)
        m.queue_quote(T0 + timedelta(days=6, minutes=1), spot="2000")
        m.run(T0 + timedelta(days=6, minutes=1))
        self.assertEqual(m.cooldown_days, 0)
        self.assertFalse(m.cooldown_eligible())

    def test_actual_funding_risk_exit_retains_eligible_dust_then_recovers(self):
        m = funding_exit_with_dust()
        self.assertEqual(m.funding_cash, D("-24.5"))
        self.assertEqual(m.spot_btc, D("0.00095"))
        self.assertEqual(m.short_btc, 0)
        self.assertEqual(m.nav, D("975.401"))
        self.assertTrue(m.paused)
        self.assertFalse(m.actually_flat)
        self.assertFalse(m.has_tradable_spot())
        self.assertNotIn("exit_constraints", m.unresolved)
        self.assertTrue(m.cooldown_eligible())
        for day in range(6):
            m.queue_day_end(T0 + timedelta(days=day + 1) - timedelta(microseconds=1))
        m.run(T0 + timedelta(days=6))
        self.assertEqual(m.cooldown_days, 5)
        m.queue_resume(T0 + timedelta(days=6, minutes=2))
        m.run(T0 + timedelta(days=6, minutes=2))
        self.assertFalse(m.paused)
        self.assertFalse(m.actually_flat)
        result = m.finish()
        self.assertEqual(result["real_forward"], 0)
        self.assertFalse(result["qualified"])
        self.assertEqual(m.spot_btc, D("0.00095"))

    def test_actual_risk_exit_with_excess_dust_cannot_start_cooldown(self):
        m = funding_exit_with_dust("0.048")
        self.assertEqual(m.spot_btc, D("0.00195"))
        self.assertEqual(m.short_btc, 0)
        self.assertFalse(m.has_tradable_spot())
        self.assertTrue(m.paused)
        self.assertFalse(m.actually_flat)
        self.assertNotIn("exit_constraints", m.unresolved)
        for day in range(6):
            m.queue_day_end(T0 + timedelta(days=day + 1) - timedelta(microseconds=1))
        m.run(T0 + timedelta(days=6))
        self.assertFalse(m.cooldown_eligible())
        self.assertEqual(m.cooldown_days, 0)

    def test_dust_sized_spot_does_not_hide_unclosed_futures(self):
        m = model()
        hedge(m, "0.02")
        m.queue_quote(T0 + timedelta(minutes=3), spot="10")
        m.run(T0 + timedelta(minutes=3))
        self.assertLess(m.spot_btc * m.spot_price, D("0.001") * m.nav)
        self.assertFalse(m.request_exit())
        self.assertEqual(m.short_btc, D("0.02"))
        self.assertIn("exit_constraints", m.unresolved)
        self.assertFalse(m.cooldown_eligible())
        self.assertTrue(m.finish()["terminal_unsettled"])

    def test_orders_are_future_only_and_all_or_none_capacity(self):
        m = model()
        with self.assertRaises(ValueError):
            m.register_plan((Leg("spot_buy", "0.01"),), first_at=m.now)
        self.assertFalse(m.register_plan((Leg("spot_buy", "0.02", capacity="0.019"),)))
        self.assertEqual(m.spot_cash, D("500"))
        self.assertEqual(m.spot_btc, 0)
        with self.assertRaises(ValueError):
            dec(0.1)
        with self.assertRaises(ValueError):
            TradingRule("0.001", "0", "10")


if __name__ == "__main__":
    unittest.main()
