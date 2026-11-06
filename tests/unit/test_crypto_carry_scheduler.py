"""Synthetic daily timing and midminute-risk counterexamples, no source files."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest

from quant_robot.research.crypto_carry_model import CarryModel, FeeScenario, TradingRule
from quant_robot.research.crypto_carry_policy import CompletedPrices, VolumeMinute
from quant_robot.research.crypto_carry_scheduler import CompletedPrefix, SyntheticCarryScheduler, TransferConfirmation

D = Decimal
T0 = datetime(2001, 1, 1, tzinfo=timezone.utc)
MINUTE = timedelta(minutes=1)


def prefix(at, *, price="1000", volume="100", received_at=None):
    received_at = received_at or at
    rows = tuple(VolumeMinute(at-(19-i)*MINUTE, max(at-(19-i)*MINUTE, received_at), volume) for i in range(20))
    return CompletedPrefix(CompletedPrices(at, received_at, price, price, price), rows, rows)


def scheduler(*, spot_cash="500", futures_cash="500", initial_prefix=True, hedged=False, price="1000", volume="100"):
    model = CarryModel(start=T0, spot_rule=TradingRule(".001", ".001", "10"),
        futures_rule=TradingRule(".001", ".001", "10"), fees=FeeScenario(".001", ".0005", ".0002"),
        spot_cash=spot_cash, futures_cash=futures_cash)
    if hedged:
        model.spot_btc = model.short_btc = D(".4")
        model.entry_vwap = D("1000")
        model.spot_cost = D("400")
        model.peak = model.daily_reference = D("1000")
    result = SyntheticCarryScheduler(model)
    result.queue_opening(T0, spot=price)
    result.advance(T0, prefix=prefix(T0, price=price, volume=volume) if initial_prefix else None)
    return result


def opening(s, minute, *, price="1000"):
    s.queue_opening(T0+minute*MINUTE, spot=price)


class CryptoCarrySchedulerTests(unittest.TestCase):
    def test_no_transfer_0002_then_0003_0004_with_no_duplicate_decision(self):
        s = scheduler()
        result = s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        number = s.model.plan.number
        self.assertEqual(s.model.plan.legs[0].side, "spot_buy")
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        self.assertEqual(s.model.plan.number, number)
        opening(s, 3); opening(s, 4)
        s.advance(T0+3*MINUTE, prefix=prefix(T0+3*MINUTE))
        self.assertGreater(s.model.spot_btc, 0)
        self.assertEqual(s.model.short_btc, 0)
        self.assertEqual(s.model.plan.index, 1)
        s.advance(T0+4*MINUTE, prefix=prefix(T0+4*MINUTE))
        self.assertEqual(s.model.short_btc, D(".399"))
        fills = [row['time'] for row in s.model.journal if row['event'] == 'leg_filled']
        self.assertEqual(fills, [(T0+3*MINUTE).isoformat(), (T0+4*MINUTE).isoformat()])
        self.assertFalse(result['qualified'])
        self.assertEqual(result['real_forward'], 0)

    def test_transfer_waits_five_full_minutes_then_0008_0009(self):
        s = scheduler(spot_cash="600", futures_cash="400")
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        self.assertEqual(s.model.transfer.amount, D("100"))
        self.assertFalse(s.model.transfer.confirmed)
        self.assertEqual(s.model.spot_cash, D("500"))
        self.assertEqual(s.model.futures_cash, D("400"))
        self.assertEqual(s.model.nav, D("1000"))
        s.advance(T0+6*MINUTE, prefix=prefix(T0+6*MINUTE))
        self.assertIsNone(s.model.plan)
        receipt = TransferConfirmation(T0+7*MINUTE, T0+7*MINUTE, "spot", "100")
        s.advance(T0+7*MINUTE, prefix=prefix(T0+7*MINUTE), confirmation=receipt)
        self.assertIsNone(s.model.transfer)
        self.assertIsNotNone(s.model.plan)
        self.assertFalse(any(row['event'] == 'leg_filled' for row in s.model.journal))
        opening(s, 8); opening(s, 9)
        s.advance(T0+9*MINUTE, prefix=prefix(T0+9*MINUTE))
        fills = [row['time'] for row in s.model.journal if row['event'] == 'leg_filled']
        self.assertEqual(fills, [(T0+8*MINUTE).isoformat(), (T0+9*MINUTE).isoformat()])

    def test_missing_or_late_confirmation_does_not_credit_or_enter(self):
        s = scheduler(spot_cash="600", futures_cash="400")
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        s.advance(T0+7*MINUTE, prefix=prefix(T0+7*MINUTE))
        self.assertIn("unconfirmed_transfer", s.model.unresolved)
        self.assertIsNone(s.model.plan)
        late = TransferConfirmation(T0+8*MINUTE, T0+7*MINUTE, "spot", "100")
        result = s.advance(T0+8*MINUTE, prefix=prefix(T0+8*MINUTE), confirmation=late)
        self.assertEqual(s.model.futures_cash, D("400"))
        self.assertIsNotNone(s.model.transfer)
        self.assertIsNone(s.model.plan)
        self.assertIsNone(result['pending_daily_transfer'])

    def test_arrival_without_0007_prefix_cancels_day_without_late_reassessment(self):
        s = scheduler(spot_cash="600", futures_cash="400")
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        receipt = TransferConfirmation(T0+7*MINUTE, T0+7*MINUTE, "spot", "100")
        s.advance(T0+7*MINUTE, confirmation=receipt)
        s.advance(T0+8*MINUTE, prefix=prefix(T0+8*MINUTE))
        self.assertIsNone(s.model.transfer)
        self.assertIsNone(s.model.plan)
        next_day = T0+timedelta(days=1, minutes=2)
        s.advance(next_day, prefix=prefix(next_day))
        self.assertIsNotNone(s.model.plan)

    def test_skipped_0002_and_late_prefix_never_catch_up(self):
        s = scheduler()
        s.advance(T0+3*MINUTE, prefix=prefix(T0+3*MINUTE))
        self.assertIsNone(s.model.plan)
        next_day = T0+timedelta(days=1, minutes=2)
        s.advance(next_day, prefix=prefix(next_day))
        self.assertIsNotNone(s.model.plan)
        late = scheduler()
        at = T0+2*MINUTE+timedelta(milliseconds=1)
        late.advance(at, prefix=prefix(T0+2*MINUTE, received_at=at))
        late.advance(T0+3*MINUTE, prefix=prefix(T0+3*MINUTE))
        self.assertIsNone(late.model.plan)

    def test_pending_second_leg_keeps_original_capacity_and_due(self):
        s = scheduler()
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        number, capacity = s.model.plan.number, s.model.plan.legs[1].capacity
        opening(s, 3); opening(s, 4)
        s.advance(T0+3*MINUTE, prefix=prefix(T0+3*MINUTE, volume=".1"))
        self.assertEqual(s.model.plan.number, number)
        self.assertEqual(s.model.plan.legs[1].capacity, capacity)
        s.advance(T0+4*MINUTE, prefix=prefix(T0+4*MINUTE, volume=".1"))
        self.assertEqual(s.model.short_btc, D(".399"))

    def test_actual_future_opening_can_reject_fixed_quantity(self):
        s = scheduler()
        opening(s, 3, price="2000")
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        self.assertEqual(s.model.plan.legs[0].quantity, D(".400"))
        s.advance(T0+3*MINUTE, prefix=prefix(T0+3*MINUTE))
        self.assertEqual(s.model.spot_btc, 0)
        self.assertEqual(s.model.short_btc, 0)
        self.assertTrue(any(row['event'] == 'leg_rejected' for row in s.model.journal))

    def test_missing_execution_opening_blocks_whole_group_without_stale_fill(self):
        s = scheduler()
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        result = s.advance(T0+3*MINUTE, prefix=prefix(T0+3*MINUTE))
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['reason'], 'due_fill_requires_explicit_execution_opening')
        self.assertEqual(s.model.now, T0+2*MINUTE)
        self.assertEqual(s.model.spot_btc, 0)
        opening(s, 3)
        s.advance(T0+3*MINUTE, prefix=prefix(T0+3*MINUTE))
        self.assertGreater(s.model.spot_btc, 0)

    def test_midminute_funding_exit_binds_prior_completed_capacity_before_fill(self):
        s = scheduler(spot_cash="100", futures_cash="500", hedged=True)
        hit = T0+timedelta(seconds=15, milliseconds=15)
        s.queue_funding(hit, rate="-.5", mark="1000")
        opening(s, 1); opening(s, 2)
        s.advance(T0+MINUTE, prefix=prefix(T0+MINUTE))
        number = s.model.plan.number
        self.assertEqual(s.bindings[number]['trigger_at'], hit.isoformat())
        self.assertEqual(s.bindings[number]['prefix_end'], T0.isoformat())
        self.assertEqual(s.model.short_btc, 0)
        self.assertEqual(s.model.plan.index, 1)
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        self.assertEqual(s.model.spot_btc, 0)
        self.assertTrue(s.model.paused)
        fills = [row for row in s.model.journal if row['event'] == 'leg_filled']
        self.assertEqual([row['number'] for row in fills], [number, number])
        self.assertEqual([row['side'] for row in fills], ['short_close', 'spot_sell'])
        self.assertEqual(s.model.nav, D("799.24004"))
        self.assertIsNotNone(s.model.transfer)
        self.assertFalse(s.model.transfer.confirmed)
        self.assertEqual(s.model.transfer.due, T0+7*MINUTE)

    def test_midminute_exit_missing_trigger_prefix_cannot_use_later_volume(self):
        s = scheduler(spot_cash="100", futures_cash="500", hedged=True, initial_prefix=False)
        hit = T0+timedelta(seconds=15, milliseconds=15)
        s.queue_funding(hit, rate="-.5", mark="1000")
        opening(s, 1)
        result = s.advance(T0+MINUTE, prefix=prefix(T0+MINUTE))
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(s.model.now, hit)
        self.assertEqual(s.model.short_btc, D(".4"))
        self.assertEqual(s.model.spot_btc, D(".4"))
        self.assertIn('missing_received_capacity_prefix', s.bindings[s.model.plan.number]['blocked_reason'])
        self.assertFalse(any(row['event'] == 'leg_filled' for row in s.model.journal))
        again = s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        self.assertEqual(again['status'], 'blocked')
        self.assertEqual(s.model.now, hit)

    def test_terminal_promotes_pending_reduction_without_starving_then_exits_rest(self):
        s = scheduler(spot_cash="100", futures_cash="560", hedged=True, price="1200")
        number = s.model.plan.number
        for minute in range(1, 5):
            opening(s, minute, price="1200")
        s.advance(T0+MINUTE, prefix=prefix(T0+MINUTE, price="1200"))
        self.assertEqual(s.model.plan.index, 1)
        s.request_terminal_exit()
        s.request_terminal_exit()
        self.assertEqual(s.model.plan.number, number)
        self.assertEqual(s.model.plan.kind, 'terminal_exit')
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE, price="1200"))
        self.assertGreater(s.model.short_btc, 0)
        self.assertIsNone(s.model.transfer)
        self.assertEqual(s.model.plan.kind, 'terminal_exit')
        s.advance(T0+3*MINUTE, prefix=prefix(T0+3*MINUTE, price="1200"))
        s.advance(T0+4*MINUTE, prefix=prefix(T0+4*MINUTE, price="1200"))
        self.assertEqual(s.model.short_btc, 0)
        self.assertFalse(s.model.has_tradable_spot())
        fills = [row for row in s.model.journal if row['event'] == 'leg_filled']
        self.assertEqual([row['number'] for row in fills[:2]], [number, number])

    def test_external_kernel_progress_and_changed_prefix_are_rejected(self):
        s = scheduler()
        s.model.run(T0+MINUTE)
        with self.assertRaisesRegex(ValueError, 'ownership'):
            s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        s = scheduler()
        with self.assertRaisesRegex(ValueError, 'immutable'):
            s.advance(T0, prefix=prefix(T0, price="1001"))

    def test_futures_cash_equalization_preserves_125_percent_buffer(self):
        s = scheduler(spot_cash="100", futures_cash="500", hedged=True)
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        self.assertIsNone(s.model.transfer)
        self.assertEqual(s.model.futures_cash, D("500"))
        self.assertIsNone(s.model.plan)

    def test_insufficient_capacity_rejects_whole_risk_leg_then_freezes_new_retry(self):
        s = scheduler(spot_cash="100", futures_cash="500", hedged=True, volume="1")
        s.queue_funding(T0+timedelta(seconds=15), rate="-.5", mark="1000")
        opening(s, 1)
        s.advance(T0+MINUTE, prefix=prefix(T0+MINUTE))
        self.assertEqual(s.model.short_btc, D(".4"))
        rejected = [row for row in s.model.journal if row['event'] == 'leg_rejected']
        self.assertEqual(rejected[0]['reason'], 'capacity')
        self.assertEqual(s.bindings[rejected[0]['number']]['capacities'], ('0.01', '0.01'))
        self.assertGreater(s.model.plan.number, rejected[0]['number'])
        self.assertEqual(s.bindings[s.model.plan.number]['prefix_end'], (T0+MINUTE).isoformat())
        self.assertEqual(s.model.plan.legs[0].capacity, D("1"))

    def test_mismatched_transfer_confirmation_does_not_advance_money_or_clock(self):
        s = scheduler(spot_cash="600", futures_cash="400")
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE))
        bad = TransferConfirmation(T0+7*MINUTE, T0+7*MINUTE, "spot", "101")
        with self.assertRaisesRegex(ValueError, 'does not match'):
            s.advance(T0+7*MINUTE, prefix=prefix(T0+7*MINUTE), confirmation=bad)
        self.assertEqual(s.model.now, T0+2*MINUTE)
        self.assertEqual(s.model.futures_cash, D("400"))

    def test_external_F1_opening_breach_is_latched_before_pending_reduction(self):
        m = CarryModel(start=T0, spot_rule=TradingRule('.001','.001','10'),
            futures_rule=TradingRule('.001','.001','10'), fees=FeeScenario('.001','.0005','.0002'),
            spot_cash='0', futures_cash='600')
        m.spot_btc = m.short_btc = D('.5')
        m.entry_vwap = D('1000'); m.spot_cost = D('500')
        m.peak = m.daily_reference = D('1100')
        s = SyntheticCarryScheduler(m)
        s.queue_opening(T0, spot='1000'); s.advance(T0, prefix=prefix(T0))
        number, second_leg = m.plan.number, m.plan.legs[1]
        self.assertEqual(m.plan.legs[0].quantity, D('.060'))
        opening(s, 1, price='1110')
        s.advance(T0+MINUTE, prefix=prefix(T0+MINUTE))
        self.assertEqual(m.short_btc, D('.440'))
        self.assertTrue({'gross_over_100_percent','futures_wallet_below_1x'} <= m.failures)
        self.assertTrue(m.paused)
        self.assertEqual((m.plan.number, m.plan.index, m.plan.legs[1]), (number, 1, second_leg))
        evidence = [r for r in m.journal if r['event']=='risk_observation'
                    and r['observation']=='execution_opening_before_events'][-1]
        self.assertEqual(tuple(D(evidence[k]) for k in ('nav','gross','futures_equity','short_mark_notional')),
                         (D('1100'),D('1110'),D('545'),D('555')))
        first_fill = next(i for i,r in enumerate(m.journal) if r['event']=='leg_filled')
        self.assertLess(m.journal.index(evidence), first_fill)
        opening(s, 2, price='1110')
        s.advance(T0+2*MINUTE, prefix=prefix(T0+2*MINUTE, price='1110'))
        fills = [r for r in m.journal if r['event']=='leg_filled']
        self.assertEqual([r['number'] for r in fills[:2]], [number,number])
        self.assertEqual([r['side'] for r in fills[:2]], ['short_close','spot_sell'])
        self.assertTrue(m.paused)
        self.assertEqual(m.plan.kind, 'risk_exit')  # The restored bounds do not cancel the rest of the exit.

    def test_external_F2_completed_close_marks_real_wallet_and_daily_stop(self):
        s = scheduler(spot_cash='100', futures_cash='500', hedged=True)
        at = T0+MINUTE
        p = prefix(at)
        p = CompletedPrefix(CompletedPrices(at, at, '1000','1100','1100'), p.spot_minutes,p.futures_minutes)
        s.advance(at, prefix=p)
        self.assertEqual((s.model.mark_price,s.model.nav), (D('1100'),D('960')))
        self.assertTrue(s.model.paused)
        self.assertEqual(s.model.plan.kind, 'risk_exit')
        close = [r for r in s.model.journal if r['event']=='completed_close'][-1]
        self.assertEqual(close['closed_at'],at.isoformat())
        self.assertEqual(close['available_at'],at.isoformat())
        self.assertEqual(close['processed_at'],at.isoformat())

    def test_midnight_final_close_precedes_day_end_new_opening_and_funding(self):
        s = scheduler(spot_cash='100', futures_cash='500', hedged=True)
        midnight = T0+timedelta(days=1)
        s.queue_day_end(midnight-timedelta(microseconds=1))
        s.queue_opening(midnight,spot='1000',future='1050',mark='1050')
        s.queue_funding(midnight,rate='.01',mark='1100')
        p = prefix(midnight)
        p = CompletedPrefix(CompletedPrices(midnight,midnight,'1000','1100','1100'),p.spot_minutes,p.futures_minutes)
        s.advance(midnight,prefix=p)
        self.assertEqual(s.model.daily_reference,D('960'))
        self.assertEqual(s.model.nav,D('964.4'))
        self.assertTrue(s.model.paused)
        rows = [r for r in s.model.journal if r['time']==midnight.isoformat()]
        events = [r['event'] for r in rows]
        self.assertLess(events.index('completed_close'), events.index('day_end'))
        self.assertLess(events.index('day_end'),events.index('funding'))
        day_end = next(r for r in rows if r['event']=='day_end')
        self.assertEqual((day_end['day'],D(day_end['reference_nav'])),('2001-01-01',D('960')))
        close_risk = next(r for r in rows if r['event']=='risk_observation' and r['observation']=='completed_minute_close')
        self.assertEqual(D(close_risk['daily_reference']),D('1000'))

    def test_midnight_missing_final_close_blocks_entire_group_before_funding(self):
        s = scheduler(spot_cash='100',futures_cash='500',hedged=True)
        midnight=T0+timedelta(days=1)
        s.queue_day_end(midnight)
        s.queue_funding(midnight,rate='.01',mark='1100')
        result=s.advance(midnight)
        self.assertEqual(result['status'],'blocked')
        self.assertIn('completed_final_minute',result['reason'])
        self.assertEqual(s.model.now,T0)
        self.assertEqual(s.model.daily_reference,D('1000'))
        self.assertEqual(s.model.funding_cash,0)
        self.assertFalse(any(r['event']=='day_end' for r in s.model.journal))

    def test_final_microsecond_cannot_claim_last_minute_is_complete(self):
        s=scheduler()
        end=T0+timedelta(days=1)-timedelta(microseconds=1)
        s.queue_day_end(end)
        result=s.advance(end)
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(result['reason'],'final_minute_not_complete_before_next_utc_boundary')
        self.assertEqual(s.model.now,T0)

    def test_old_close_cannot_overwrite_processed_opening_or_funding(self):
        for source in ('opening','funding'):
            s=scheduler(spot_cash='100',futures_cash='500',hedged=True)
            at=T0+MINUTE
            if source=='opening': s.queue_opening(at,spot='1000',future='1010',mark='1010')
            else: s.queue_funding(at,rate='.001',mark='1010')
            s.advance(at)
            before=s.model.nav
            late=at+timedelta(milliseconds=15)
            with self.assertRaisesRegex(ValueError,'cannot overwrite newer'):
                s.advance(late,prefix=prefix(at,received_at=late))
            self.assertEqual(s.model.now,at)
            self.assertEqual((s.model.mark_price,s.model.nav),(D('1010'),before))

    def test_late_close_without_intervening_event_preserves_all_three_clocks(self):
        s=scheduler()
        end=T0+MINUTE
        received=end+timedelta(milliseconds=15)
        s.advance(received,prefix=prefix(end,price='1010',received_at=received))
        record=[r for r in s.model.journal if r['event']=='completed_close'][-1]
        self.assertEqual(record['closed_at'],end.isoformat())
        self.assertEqual(record['available_at'],received.isoformat())
        self.assertEqual(record['processed_at'],received.isoformat())
        self.assertEqual(s.model.now,received)

    def test_late_close_cannot_pass_already_queued_boundary_funding(self):
        s=scheduler()
        end=T0+MINUTE
        s.queue_funding(end,rate='.001',mark='1010')
        with self.assertRaisesRegex(ValueError,'crosses a queued'):
            s.advance(end+timedelta(milliseconds=15),prefix=prefix(end,received_at=end+timedelta(milliseconds=15)))
        self.assertEqual(s.model.now,T0)

    def test_year_end_processing_uses_only_prior_year_final_bar(self):
        # Synthetic clock: processing crosses the year, but no new-year opening/funding is supplied.
        s=scheduler()
        boundary=datetime(2002,1,1,tzinfo=timezone.utc)
        s.queue_day_end(boundary)
        s.advance(boundary,prefix=prefix(boundary))
        end=[r for r in s.model.journal if r['event']=='day_end'][-1]
        self.assertEqual(end['day'],'2001-12-31')
        self.assertEqual(s.model.now,boundary)
        self.assertEqual(s.model.daily_reference,D('1000'))
        self.assertFalse(any(r['event']=='funding' for r in s.model.journal))

    def test_initial_missing_twenty_minutes_cancels_day_without_late_entry(self):
        s=scheduler(initial_prefix=False)
        at=T0+2*MINUTE
        good=prefix(at)
        with self.assertRaisesRegex(ValueError,'Twenty complete consecutive'):
            CompletedPrefix(good.prices,good.spot_minutes[1:],good.futures_minutes)
        s.advance(at)
        self.assertIsNone(s.model.plan)
        self.assertTrue(any(r['event']=='daily_opportunity_cancelled' for r in s.journal))
        s.advance(T0+3*MINUTE,prefix=prefix(T0+3*MINUTE))
        self.assertIsNone(s.model.plan)
        tomorrow=T0+timedelta(days=1,minutes=2)
        s.advance(tomorrow,prefix=prefix(tomorrow))
        self.assertIsNotNone(s.model.plan)


if __name__ == '__main__':
    unittest.main()
