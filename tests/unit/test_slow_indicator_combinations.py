"""Synthetic-only causality, risk and same-budget controls for the new proposal."""
from copy import deepcopy
import unittest
import pandas as pd
from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account
from quant_robot.paper.position_buffer import BUFFER
from quant_robot.paper.comparative_allocation import buffered_policy_template, run_comparison
from quant_robot.research.slow_indicator_combinations import slow_features, separated_cycles
from tests.unit.test_annual_allocation_account import A, fixture, change, cycle
from tests.unit import test_indicator_combinations as indicator_fixtures


class BufferedExecutionTests(unittest.TestCase):
    def setUp(self):
        self.days, self.bars = fixture(38, (A,), price=2.6)
        self.config = AllocationConfig(execution_price_field='open', slippage_bps=0)

    def run_account(self, **kwargs):
        return run_allocation_account(self.bars, sessions=self.days, assets=(A,),
            cycles=kwargs.pop('cycles', [cycle(self.days,20,30)]), actions=[],
            config=kwargs.pop('config', self.config),
            position_buffer=kwargs.pop('position_buffer', BUFFER), **kwargs)

    def test_buffer_sizes_whole_lots_with_entry_fee(self):
        result=self.run_account()
        entry=result['fills'][0]
        self.assertEqual(entry['quantity'],300)
        self.assertEqual(entry['notional']+entry['fee'],785)
        self.assertEqual(result['config']['max_position_cny'],1000)
        self.assertEqual(result['position_buffer'],BUFFER)

    def test_gap_over_budget_cancels_whole_order_without_resize(self):
        change(self.bars,self.days[20],price=2.7)
        result=self.run_account()
        self.assertEqual(result['fills'],[])
        self.assertTrue(any(e['reason']=='entry_budget_or_cash' for e in result['events']))

    def test_early_trim_uses_next_open_and_preserves_lots_without_topup(self):
        for day in self.days[21:]:
            change(self.bars,day,price=3.1)
        result=self.run_account()
        trim=next(f for f in result['fills'] if f['reason']=='position_trim')
        self.assertEqual((trim['date'],trim['quantity']),(self.days[22],100))
        self.assertEqual(result['equity_curve'][21]['position_values'][A]['market_value'],930)
        self.assertEqual(result['equity_curve'][22]['position_values'][A]['market_value'],620)
        self.assertEqual(len([f for f in result['fills'] if f['side']=='buy']),1)
        self.assertEqual(result['risk']['breaches'],[])

    def test_repeated_trims_keep_currency_target_separate_from_share_quantity(self):
        for day in self.days[21:]:
            change(self.bars,day,price=3.1 if day<self.days[23] else 4.6)
        result=self.run_account()
        trims=[f for f in result['fills'] if f['reason']=='position_trim']
        self.assertEqual([(f['date'],f['quantity']) for f in trims],
                         [(self.days[22],100),(self.days[24],100)])
        self.assertEqual(result['equity_curve'][24]['position_values'][A]['market_value'],460)
        self.assertEqual(result['risk']['breaches'],[])

    def test_failed_trim_is_refreshed_not_carried_after_value_recovers(self):
        change(self.bars,self.days[21],price=3.1)
        for day in self.days[22:]:
            change(self.bars,day,price=3)
        change(self.bars,self.days[22],limit_down=True)
        result=self.run_account()
        self.assertFalse(any(f['reason']=='position_trim' for f in result['fills']))
        self.assertTrue(any(e.get('order_reason')=='position_trim' for e in result['events']))
        self.assertEqual(result['risk']['breaches'],[])

    def test_unfillable_trim_and_gap_remain_failure_and_stop_future_entries(self):
        for day in self.days[21:]:
            change(self.bars,day,price=3.1 if day<self.days[23] else 3.5)
        for index in (22,23):
            change(self.bars,self.days[index],limit_down=True)
        result=self.run_account(cycles=[cycle(self.days,20,27),cycle(self.days,29,35,'two')])
        breaches=result['risk']['breaches']
        self.assertTrue(any(b['reason']=='position_limit' and b['market_value']==1050 for b in breaches))
        self.assertTrue(result['risk']['new_entries_halted'])
        self.assertTrue(any(e['reason']=='risk_halted' and e['date']==self.days[29] for e in result['events']))
        self.assertEqual(len([f for f in result['fills'] if f['side']=='buy']),1)
        self.assertTrue(any(f['reason']=='account_risk_exit' and f['date']==self.days[24] for f in result['fills']))

    def test_daily_loss_stop_still_applies_and_no_restart(self):
        for day in self.days[21:]:
            change(self.bars,day,price=2.39)
        result=self.run_account(cycles=[cycle(self.days,20,27),cycle(self.days,29,35,'two')])
        self.assertTrue(any(b['reason']=='daily_loss_limit' for b in result['risk']['breaches']))
        self.assertEqual(len([f for f in result['fills'] if f['side']=='buy']),1)

    def test_opening_gap_is_retained_after_planned_trim_full_exit_or_block(self):
        for action in ('trim', 'full_exit', 'blocked_trim'):
            with self.subTest(action=action):
                self.days, self.bars = fixture(38, (A,), price=2.6)
                change(self.bars, self.days[21], price=3.1)
                change(self.bars, self.days[22], price=3.1)
                row = next(r for r in self.bars if r['date'] == self.days[22])
                row.update(open=3.35, high=3.35, low=3.1)
                if action == 'blocked_trim':
                    row['limit_down'] = True
                exit_index = 22 if action == 'full_exit' else 27
                result = self.run_account(cycles=[cycle(self.days,20,exit_index),
                                                 cycle(self.days,29,35,'two')])
                opening = [b for b in result['risk']['breaches'] if b.get('phase') == 'before_fills']
                self.assertEqual(opening[0]['market_value'],1005)
                self.assertEqual(opening[0]['quantity'],300)
                self.assertEqual(opening[0]['price_basis'],'raw_open')
                self.assertFalse(result['risk']['within_all_observed_limits'])
                self.assertTrue(result['risk']['new_entries_halted'])
                self.assertEqual(len([f for f in result['fills'] if f['side']=='buy']),1)
                self.assertTrue(any(e['reason']=='risk_halted' and e['date']==self.days[29]
                                    for e in result['events']))
                sells = [f for f in result['fills'] if f['side']=='sell']
                if action == 'full_exit':
                    self.assertEqual((sells[0]['date'],sells[0]['quantity'],sells[0]['reason']),
                                     (self.days[22],300,'scheduled_exit'))
                elif action == 'trim':
                    self.assertEqual((sells[0]['date'],sells[0]['quantity'],sells[0]['reason']),
                                     (self.days[22],100,'position_trim'))
                    self.assertEqual((sells[1]['date'],sells[1]['reason']),
                                     (self.days[23],'account_risk_exit'))
                else:
                    self.assertEqual((sells[0]['date'],sells[0]['quantity'],sells[0]['reason']),
                                     (self.days[23],300,'account_risk_exit'))

    def test_invalid_or_looser_buffer_is_rejected(self):
        for policy in ({},dict(BUFFER,trim_trigger_cny=1000),dict(BUFFER,topup=True)):
            with self.subTest(policy=policy),self.assertRaises(ValueError):
                self.run_account(position_buffer=policy)
        with self.assertRaises(ValueError):
            self.run_account(config=AllocationConfig(execution_price_field='open',max_position_cny=1100))
        with self.assertRaises(ValueError):
            self.run_account(config=AllocationConfig(execution_price_field='close'))

    def test_default_engine_result_remains_legacy_policy(self):
        for day in self.days:
            change(self.bars,day,price=2.4)
        a=self.run_account(position_buffer=None)
        b=run_allocation_account(self.bars,sessions=self.days,assets=(A,),
            cycles=[cycle(self.days,20,30)],actions=[],config=self.config)
        self.assertEqual(a,b)
        self.assertNotIn('position_buffer',a)
        self.assertGreater(a['fills'][0]['quantity'],self.run_account()['fills'][0]['quantity'])

    def test_all_27_accounts_share_buffer_costs_and_continuous_calendar(self):
        policy=buffered_policy_template(study_id='synthetic_only',first_session=self.days[20],
            terminal_session=self.days[-1],later_start=self.days[27])
        result=run_comparison(self.bars,sessions=self.days,asset=A,
            strategy_cycles=[cycle(self.days,20,37)],actions=[],policy=policy)
        self.assertEqual(len(result['accounts']),9)
        for group in result['accounts'].values():
            self.assertEqual(set(group),{'strategy','holding','cash'})
            self.assertEqual(group['strategy']['equity_curve'],group['holding']['equity_curve'])
            for role in ('strategy','holding'):
                self.assertEqual(group[role]['metrics']['pnl_cny'],group['strategy']['metrics']['pnl_cny'])
            for account in group.values():
                self.assertEqual(account['position_buffer'],BUFFER)
                self.assertEqual(account['config'],group['strategy']['config'])
                self.assertEqual([r['date'] for r in account['equity_curve']],self.days)
            self.assertEqual(group['cash']['fills'],[])
        self.assertFalse(result['paper_promotion_allowed'])

    def test_v2_missing_buffer_and_legacy_disguise_fail_before_accounts(self):
        policy=buffered_policy_template(study_id='synthetic_only',first_session=self.days[20],
            terminal_session=self.days[-1],later_start=self.days[27])
        for invalid in (dict(policy,position_buffer=None),dict(policy,schema_version=1)):
            with self.subTest(policy=invalid),self.assertRaises(ValueError):
                run_comparison([],sessions=self.days,asset=A,strategy_cycles=[],actions=[],policy=invalid)


class SlowSignalTests(unittest.TestCase):
    def states(self):
        days=pd.bdate_range('2014-01-01',periods=145).strftime('%Y-%m-%d').tolist()
        return days,[False]*len(days),[False]*len(days)

    def test_macd_off_does_not_exit_and_trend_exit_runs_daily(self):
        days,entries,exits=self.states()
        entries[119]=True
        exits[122]=True  # Not an entry decision day.
        result=separated_cycles(days,entries,exits,first=days[120])
        self.assertEqual([(c['entry_date'],c['exit_date']) for c in result],[(days[120],days[123])])

    def test_no_same_open_roundtrip_and_terminal_entry(self):
        days,entries,exits=self.states()
        entries[:]=[True]*len(days)
        exits[124]=True
        result=separated_cycles(days,entries,exits,first=days[120])
        self.assertEqual([(c['entry_date'],c['exit_date']) for c in result],[(days[120],days[125]),(days[130],days[-1])])
        entries[:]=[False]*len(days); entries[-2]=True
        self.assertEqual(separated_cycles(days,entries,exits,first=days[120]),[])

    def test_unknown_information_exits_without_dropping_calendar(self):
        days,entries,exits=self.states()
        entries[119]=True;entries[121]=pd.NA
        result=separated_cycles(days,entries,exits,first=days[120])
        self.assertEqual(result[0]['exit_date'],days[122])

    def test_future_changes_do_not_alter_earlier_features(self):
        bars=indicator_fixtures.IndicatorCombinationsTests().rows()
        original=slow_features(bars,[])
        changed=deepcopy(bars)
        for row in changed[300:]:
            row['close']=str(float(row['close'])*4);row['amount']='1'
        revised=slow_features(changed,[])
        pd.testing.assert_frame_equal(original.iloc[:300],revised.iloc[:300])
        self.assertTrue(original.iloc[:119]['slow_macd'].isna().all())
        expected=((original.signal_price<original.sma120)&(original.signal_price.shift(1)<original.sma120.shift(1)))
        pd.testing.assert_series_equal(original.trend_exit.iloc[120:].astype(bool),expected.iloc[120:],check_names=False)


if __name__=='__main__': unittest.main()
