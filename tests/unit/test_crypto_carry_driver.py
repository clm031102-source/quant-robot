"""Only artificial 2001 values; no files, requests, historical return fixtures."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import timedelta
from decimal import Decimal as D
import unittest

from quant_robot.research.crypto_carry_driver import (
    DEMO_START, DAY, MINUTE, PRIMARY_FEES, YEAR_END, audit_dataset, fabricated_fixture, run_synthetic_driver,
)
from quant_robot.research.crypto_carry_model import CarryModel, Leg, TradingRule
from quant_robot.research.crypto_carry_policy import CompletedPrices, VolumeMinute, plan_target
from quant_robot.research.crypto_carry_scheduler import CompletedPrefix, SyntheticCarryScheduler


def model(*, audit=False):
    return CarryModel(start=DEMO_START,spot_rule=TradingRule('.001','.001','10'),
        futures_rule=TradingRule('.001','.001','10'),fees=PRIMARY_FEES,audit_event_states=audit)


def completed(at,received=None):
    received=received or at
    prices=CompletedPrices(at,at,'1000','1000','1000')
    rows=tuple(VolumeMinute(at-(19-i)*MINUTE,received,'100') for i in range(20))
    return CompletedPrefix(prices,rows,rows)


class CryptoCarryDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=fabricated_fixture()
        cls.result=run_synthetic_driver(cls.data)

    def test_full_primary_two_days_continuous_wallet_real_synthetic_cash_events(self):
        r=self.result
        self.assertEqual(r['status'],'completed_synthetic_exercise')
        self.assertTrue(r['economic_exercise_complete'])
        self.assertEqual((r['processed_minutes'],r['fill_count'],r['confirmed_transfer_count']),(2880,4,3))
        self.assertEqual(r['envelope_status_counts'],{'verified_within_envelope':2880})
        self.assertTrue(r['funding_event_coverage_complete'])
        self.assertEqual([D(row['reference_nav']) for row in r['daily_nav']],
                         [D('998.90089962'),D('997.72399924')])
        self.assertEqual(D(r['kernel']['funding_cash']),D('.3192'))
        self.assertFalse(r['terminal']['terminal_unsettled'])
        self.assertFalse(r['qualified'])
        self.assertEqual(r['real_forward'],0)

    def test_exact_event_and_terminal_order_are_preserved(self):
        r=self.result
        fills=[row for row in r['kernel_journal'] if row['event']=='leg_filled']
        self.assertEqual([row['time'] for row in fills],[(DEMO_START+8*MINUTE).isoformat(),
            (DEMO_START+9*MINUTE).isoformat(),(DEMO_START+DAY+timedelta(hours=22,minutes=1)).isoformat(),
            (DEMO_START+DAY+timedelta(hours=22,minutes=2)).isoformat()])
        funding=[row for row in r['kernel_journal'] if row['event']=='funding']
        self.assertEqual(D(funding[1]['quantity_before']),0)
        self.assertEqual(D(funding[2]['quantity_before']),D('.399'))
        self.assertIn('.015000',funding[2]['time'])
        midnight=DEMO_START+DAY
        end=next(i for i,row in enumerate(r['kernel_journal']) if row['event']=='day_end')
        next_funding=next(i for i,row in enumerate(r['kernel_journal']) if row['event']=='funding' and row['time']==midnight.isoformat())
        self.assertLess(end,next_funding)

    def test_missing_minute_or_final_bar_blocks_before_account_creation(self):
        for target in (DEMO_START+10*MINUTE,self.data.end-MINUTE):
            bars=tuple(bar for bar in self.data.bars if not(bar.market=='mark' and bar.candle.start==target))
            result=run_synthetic_driver(replace(self.data,bars=bars))
            self.assertEqual(result['status'],'blocked_input_coverage')
            self.assertFalse(result['account_created'])

    def test_duplicate_wrong_units_extra_range_and_nonfinite_fields_block(self):
        bar=self.data.bars[0]
        cases=[replace(self.data,bars=self.data.bars+(bar,)),
            replace(self.data,bars=(replace(bar,price_unit='USD'),)+self.data.bars[1:]),
            replace(self.data,bars=(replace(bar,volume_btc=D('NaN')),)+self.data.bars[1:]),
            replace(self.data,end=self.data.end+DAY)]
        for case in cases:
            self.assertEqual(audit_dataset(case)['status'],'blocked')

    def test_missing_funding_event_rate_or_mark_never_becomes_zero(self):
        for field in ('rate','mark'):
            event=replace(self.data.funding[0],**{field:None})
            result=run_synthetic_driver(replace(self.data,funding=(event,)+self.data.funding[1:]))
            self.assertFalse(result['account_created'])
            self.assertIn('missing_funding_rate_or_mark',result['reason'])
        self.assertEqual(audit_dataset(replace(self.data,funding=self.data.funding[:-1]))['status'],'blocked')

    def test_missing_or_mismatched_confirmation_blocks_without_credit(self):
        for receipts in (self.data.confirmations[1:],
                         (replace(self.data.confirmations[0],amount=D('99')),)+self.data.confirmations[1:]):
            result=run_synthetic_driver(replace(self.data,confirmations=receipts))
            self.assertEqual(result['status'],'blocked_execution')
            self.assertEqual(result['confirmed_transfer_count'],0)
            self.assertEqual(D(result['kernel']['futures_cash']),D('400'))
            self.assertEqual(D(result['kernel']['in_transit']),D('100'))

    def test_no_warmup_cancels_first_day_then_enters_only_next_fixed_schedule(self):
        result=run_synthetic_driver(fabricated_fixture(warmup=False))
        self.assertTrue(result['economic_exercise_complete'])
        fills=[row for row in result['kernel_journal'] if row['event']=='leg_filled']
        self.assertEqual(fills[0]['time'],(DEMO_START+DAY+8*MINUTE).isoformat())
        self.assertEqual(D(result['daily_nav'][0]['reference_nav']),D('1000'))
        closes=[row for row in result['kernel_journal'] if row['event']=='completed_close']
        self.assertEqual(closes[0]['closed_at'],(DEMO_START+MINUTE).isoformat())
        self.assertEqual(len(closes),2880)

    def test_unknown_ohlc_path_is_not_claimed_as_liquidation_or_confirmed_breach(self):
        at=DEMO_START+10*MINUTE
        bars=tuple(replace(bar,candle=replace(bar.candle,high=D('1400'),low=D('600')))
                   if bar.candle.start==at and bar.market in {'spot','mark'} else bar for bar in self.data.bars)
        result=run_synthetic_driver(replace(self.data,bars=bars))
        self.assertTrue(result['economic_exercise_complete'])
        self.assertEqual(result['status'],'completed_with_unresolved_path')
        self.assertEqual(result['envelope_status_counts'].get('confirmed_breach',0),0)
        self.assertEqual(result['kernel']['failures'],[])
        self.assertTrue(result['no_actual_liquidation_inferred_from_envelope'])

    def test_known_cash_shock_has_confirmed_breach_before_missing_later_ack_blocks(self):
        events=tuple(replace(event,rate=D('-.5')) if event.at==DEMO_START+timedelta(hours=8) else event
                     for event in self.data.funding)
        result=run_synthetic_driver(replace(self.data,funding=events))
        self.assertGreater(result['envelope_status_counts'].get('confirmed_breach',0),0)
        self.assertIn('futures_wallet_below_1x',result['kernel']['failures'])
        self.assertFalse(result['economic_exercise_complete'])

    def test_missing_synchronous_event_spot_never_reuses_old_opening_as_known_point(self):
        when=DEMO_START+9*MINUTE+timedelta(milliseconds=15)
        events=tuple(replace(event,synchronous_spot=None) if event.at==when else event for event in self.data.funding)
        result=run_synthetic_driver(replace(self.data,funding=events))
        minute=next(row for row in result['envelopes'] if row['start']==(DEMO_START+9*MINUTE).isoformat())
        self.assertFalse(any(point['at']==when for point in minute['known_points']))

    def test_zero_fill_zero_interest_cannot_be_complete_exercise(self):
        bars=tuple(replace(bar,volume_btc=D('0')) if bar.market!='mark' else bar for bar in self.data.bars)
        data=replace(self.data,bars=bars,spot_cash=D('500'),futures_cash=D('500'),confirmations=())
        result=run_synthetic_driver(data)
        self.assertEqual(result['status'],'incomplete_economic_exercise')
        self.assertEqual(result['fill_count'],0)
        self.assertFalse(result['economic_exercise_complete'])
        self.assertTrue(result['funding_event_coverage_complete'])

    def test_year_final_minute_processed_without_new_year_price_or_funding(self):
        data=fabricated_fixture(start=YEAR_END-2*DAY)
        self.assertTrue(all(bar.candle.start.year==2001 for bar in data.bars))
        self.assertTrue(all(event.at.year==2001 for event in data.funding))
        result=run_synthetic_driver(data)
        self.assertTrue(result['economic_exercise_complete'])
        self.assertEqual(result['final_processing_at'],YEAR_END.isoformat())
        self.assertFalse(result['next_interval_opening_or_funding_consumed'])
        self.assertEqual(result['daily_nav'][-1]['day'],'2001-12-31')

    def test_trace_switch_does_not_change_economic_outputs_or_journal(self):
        models=[]
        for audit in (False,True):
            m=model(audit=audit)
            m.queue_quote(DEMO_START,spot='1000'); m.run(DEMO_START)
            m.request_transfer('spot','100')
            m.run(DEMO_START+5*MINUTE)
            m.register_plan((Leg('spot_buy','.02'),Leg('short_open','.019')))
            m.queue_funding(DEMO_START+7*MINUTE+timedelta(milliseconds=15),rate='.0001',mark='1000')
            m.run(DEMO_START+7*MINUTE+timedelta(milliseconds=15)); models.append(m)
        self.assertEqual(models[0].snapshot(),models[1].snapshot())
        self.assertEqual(models[0].journal,models[1].journal)
        self.assertEqual(models[0].audit_states_since(),(0,()))
        _,trace=models[1].audit_states_since()
        self.assertTrue(trace)
        with self.assertRaises(FrozenInstanceError): trace[0].spot_cash=D('0')

    def test_planning_clone_economics_and_pending_mutable_state_are_independent(self):
        m=model(audit=True)
        m.queue_quote(DEMO_START,spot='1000'); m.run(DEMO_START)
        p=completed(DEMO_START)
        kwargs=dict(decision_at=DEMO_START,prices=p.prices,spot_minutes=p.spot_minutes,futures_minutes=p.futures_minutes)
        self.assertEqual(plan_target(deepcopy(m),**kwargs),plan_target(m.planning_copy(),**kwargs))
        m.request_transfer('spot','100')
        clone=m.planning_copy()
        self.assertEqual(clone.snapshot(),m.snapshot())
        self.assertEqual(clone.journal,[])
        self.assertEqual(clone.audit_states_since(),(0,()))
        clone.transfer.confirmed=False
        self.assertTrue(m.transfer.confirmed)
        m.run(DEMO_START+5*MINUTE)
        m.register_plan((Leg('spot_buy','.02'),Leg('short_open','.019')))
        clone=m.planning_copy(); clone.plan.index=1
        self.assertEqual(m.plan.index,0)

    def test_price_only_then_late_capacity_prefix_never_requeues_or_catches_up(self):
        s=SyntheticCarryScheduler(model())
        s.queue_opening(DEMO_START,spot='1000')
        s.advance(DEMO_START,completed_prices=completed(DEMO_START).prices)
        at=DEMO_START+2*MINUTE
        s.advance(at,completed_prices=completed(at).prices)
        before=sum(row['event']=='completed_close' for row in s.model.journal)
        late=at+timedelta(milliseconds=15)
        s.advance(late,prefix=completed(at,late))
        self.assertEqual(sum(row['event']=='completed_close' for row in s.model.journal),before)
        self.assertIsNone(s.model.plan)
        bad=completed(at,late)
        with self.assertRaisesRegex(ValueError,'immutable'):
            s.advance(late,prefix=replace(bad,prices=replace(bad.prices,mark=D('1001'))))

    def test_price_only_midnight_settles_without_capacity_but_cannot_bind_new_risk(self):
        s=SyntheticCarryScheduler(model())
        s.queue_opening(DEMO_START,spot='1000')
        s.advance(DEMO_START,completed_prices=completed(DEMO_START).prices)
        midnight=DEMO_START+DAY
        s.queue_day_end(midnight)
        s.advance(midnight,completed_prices=completed(midnight).prices)
        self.assertEqual(s.model.daily_reference,D('1000'))
        self.assertIsNone(s.model.plan)
        # A separate known-loss fixture has no capacity evidence at its trigger.
        m=model(); m.spot_cash=D('100'); m.spot_btc=m.short_btc=D('.4'); m.entry_vwap=D('1000')
        s=SyntheticCarryScheduler(m); s.queue_opening(DEMO_START,spot='1000')
        s.advance(DEMO_START,completed_prices=completed(DEMO_START).prices)
        at=DEMO_START+MINUTE
        s.advance(at,completed_prices=CompletedPrices(at,at,'1000','1100','1100'))
        self.assertIsNotNone(s.bindings[m.plan.number]['blocked_reason'])
        s.queue_opening(at+MINUTE,spot='1000',future='1100',mark='1100')
        result=s.advance(at+MINUTE,prefix=completed(at+MINUTE))
        self.assertEqual(result['status'],'blocked')
        self.assertEqual(m.short_btc,D('.4'))

    def terminal_fixture(self):
        m=model(); m.spot_cash=D('50'); m.futures_cash=D('550')
        m.spot_btc=m.short_btc=D('.4'); m.entry_vwap=D('1000'); m.spot_cost=D('400')
        m.peak=m.daily_reference=D('1000')
        s=SyntheticCarryScheduler(m); s.queue_opening(DEMO_START,spot='1000')
        s.advance(DEMO_START,prefix=completed(DEMO_START))
        return s

    def at_price(self, at, price):
        p=completed(at)
        return replace(p,prices=CompletedPrices(at,at,price,price,price))

    def test_terminal_intent_prevents_same_boundary_new_90_percent_reduction(self):
        s=self.terminal_fixture(); at=DEMO_START+timedelta(hours=22)
        s.queue_opening(at,spot='1126')
        s.advance(at,prefix=self.at_price(at,'1126'),terminal_intent=True)
        self.assertEqual(s.model.plan.kind,'terminal_exit')
        self.assertEqual([leg.quantity for leg in s.model.plan.legs],[D('.4'),D('.4')])
        self.assertFalse(s.model.paused)
        self.assertEqual(s.model.failures,set())
        self.assertFalse(any(row['event']=='policy_decision' and row['time']==at.isoformat() for row in s.journal))
        self.assertIsNone(s.model.transfer)

    def test_terminal_preserves_already_filled_reduction_leg_then_exits_remaining(self):
        s=self.terminal_fixture(); end=DEMO_START+timedelta(hours=22)
        before=end-2*MINUTE
        s.queue_opening(before,spot='1126'); s.advance(before,prefix=self.at_price(before,'1126'))
        number=s.model.plan.number; second=s.model.plan.legs[1]
        self.assertLess(s.model.plan.legs[0].quantity,D('.4'))
        s.queue_opening(end-MINUTE,spot='1126')
        s.advance(end-MINUTE,prefix=self.at_price(end-MINUTE,'1126'))
        self.assertEqual((s.model.plan.number,s.model.plan.index,s.model.plan.legs[1]),(number,1,second))
        self.assertEqual(s.model.plan.kind,'rebalance')
        s.queue_opening(end,spot='1126'); s.advance(end,prefix=self.at_price(end,'1126'),terminal_intent=True)
        fills=[row for row in s.model.journal if row['event']=='leg_filled']
        self.assertEqual([row['number'] for row in fills],[number,number])
        self.assertEqual(D(fills[-1]['quantity']),second.quantity)
        self.assertGreater(s.model.plan.number,number)
        self.assertEqual(s.model.plan.kind,'terminal_exit')
        self.assertEqual(s.model.plan.legs[0].quantity,s.model.short_btc)
        self.assertIsNone(s.model.transfer)

    def test_known_midminute_spot_updates_kernel_stop_and_matches_trace_known_point(self):
        at=DEMO_START+9*MINUTE+timedelta(milliseconds=15)
        events=tuple(replace(event,synchronous_spot=D('900')) if event.at==at else event for event in self.data.funding)
        bars=tuple(replace(bar,candle=replace(bar.candle,low=D('900')))
                   if bar.market=='spot' and bar.candle.start==at.replace(second=0,microsecond=0) else bar
                   for bar in self.data.bars)
        result=run_synthetic_driver(replace(self.data,bars=bars,funding=events))
        hit=next(row for row in result['kernel_journal'] if row['event']=='risk_observation'
                 and row['time']==at.isoformat() and row['observation']=='funding_event_mark_before_cash')
        self.assertIn('daily_loss_2_percent',hit['reasons'])
        self.assertTrue(result['kernel']['paused'])
        states=[row for row in result['event_states'] if at.replace(second=0,microsecond=0)<=row['at']<DEMO_START+10*MINUTE
                and row['event'] not in {'completed_close','day_end'}]
        index=next(i for i,row in enumerate(states) if row['at']==at and row['stage']=='mark_before_cash')
        state=states[index]
        minute=next(row for row in result['envelopes'] if row['start']==(DEMO_START+9*MINUTE).isoformat())
        point=next(point for point in minute['known_points'] if point['at']==at and point['state_index']==index)
        self.assertEqual((point['spot'],point['mark']),(D('900'),D('1000')))
        actual_nav=state['spot_cash']+state['spot_btc']*point['spot']+state['futures_cash']+state['short_btc']*(state['entry_vwap']-point['mark'])+state['in_transit']
        self.assertEqual(actual_nav,D(hit['nav']))
        self.assertEqual(state['spot_price'],point['spot'])
        self.assertEqual(state['future_price'],D('1000'))

    def test_synchronous_spot_preserves_funding_before_short_entry_and_none_is_unknown(self):
        for known in (True,False):
            m=model(audit=True)
            m.queue_quote(DEMO_START,spot='1000'); m.run(DEMO_START)
            m.register_plan((Leg('spot_buy','.02'),Leg('short_open','.019')))
            at=DEMO_START+2*MINUTE
            m.queue_funding(at,rate='.01',mark='1000',synchronous_spot='1100' if known else None)
            m.queue_funding(at+timedelta(milliseconds=15),rate='.01',mark='1000',synchronous_spot='1100' if known else None)
            m.run(at+timedelta(milliseconds=15))
            events=[row for row in m.journal if row['event']=='funding']
            self.assertEqual([D(row['quantity_before']) for row in events],[D('0'),D('.019')])
            self.assertEqual(m.future_price,D('1000'))
            self.assertEqual(m.spot_price,D('1100') if known else D('1000'))
            self.assertEqual(events[-1]['spot_observation'],'explicit_synchronous' if known else 'unobserved_last_known_valuation')


if __name__=='__main__': unittest.main()
