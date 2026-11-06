"""Synthetic execution cases for a new opt-in; old default semantics stay fixed."""
from dataclasses import replace
from datetime import date,timedelta
import unittest

from quant_robot.paper.annual_allocation import AllocationConfig,run_allocation_account
from quant_robot.paper.daily_entry_policy import NAV90_DAILY_RETRY,cycles_from_daily_targets
from quant_robot.paper.daily_recovery import RECOVERY_40,RECOVERY_40_DAILY_RETRY


class DailyEntryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.days=[(date(2000,1,1)+timedelta(days=i)).isoformat() for i in range(310)]
        self.bars=[dict(asset_id='SYNTHETIC',date=day,open=5,high=5,low=5,close=5,
            volume=1000000,suspended=False,limit_up=False,limit_down=False) for day in self.days]
        self.config=AllocationConfig(initial_cash=10000,max_position_cny=10000,
            max_position_fraction=1,max_drawdown=.4,execution_price_field='open',
            commission_bps=0,minimum_commission=0,slippage_bps=0)

    def run_account(self,*,stop=45,config=None,cycles=None,**options):
        return run_allocation_account(self.bars[:stop],sessions=self.days[:stop],assets=['SYNTHETIC'],
            cycles=cycles or [dict(cycle_id='fixed_episode',entry_date=self.days[20],exit_date=self.days[stop-1])],
            actions=[],config=config or self.config,daily_recovery=options.pop('daily_recovery',RECOVERY_40_DAILY_RETRY),
            entry_policy=options.pop('entry_policy',NAV90_DAILY_RETRY),**options)

    def test_ninety_percent_budget_includes_fee_and_does_not_rebalance(self):
        for i in range(21,44):
            for key in ('open','high','low','close'):self.bars[i][key]=5+(i-20)*.001
        account=self.run_account(config=replace(self.config,commission_bps=5,minimum_commission=5))
        buys=[fill for fill in account['fills'] if fill['side']=='buy']
        self.assertEqual(len(buys),1)
        self.assertEqual(buys[0]['quantity'],1700)
        self.assertEqual(buys[0]['precommitted_entry_budget'],9000)
        self.assertLessEqual(buys[0]['notional']+buys[0]['fee'],9000)
        self.assertFalse(account['entry_policy']['daily_rebalance'])
        self.assertTrue(all(row['equity']==10000 for row in account['equity_curve'][:20]))

    def test_gap_cannot_spend_reserved_cash_and_can_retry_next_day(self):
        for row in self.bars[20:]:
            for key in ('open','high','low','close'):row[key]=5.1
        account=self.run_account()
        rejection=next(event for event in account['events'] if event['date']==self.days[20])
        self.assertEqual(rejection['reason'],'entry_budget_or_cash')
        self.assertEqual(rejection['requested_quantity'],1800)
        self.assertLess(1800*5.1,10000)  # Cash suffices, the frozen 9000 budget does not.
        buy=next(fill for fill in account['fills'] if fill['side']=='buy')
        self.assertEqual((buy['date'],buy['quantity']),(self.days[21],1700))
        planned=next(cycle for cycle in account['cycles'] if cycle['cycle_id']==buy['cycle_id'])
        self.assertEqual((planned['entry_date'],planned['entry_index']),(self.days[21],21))

    def test_current_capacity_rejection_never_resizes_and_retries(self):
        self.bars[20]['volume']=100
        account=self.run_account()
        event=next(event for event in account['events'] if event['date']==self.days[20])
        self.assertEqual((event['reason'],event['requested_quantity']),('entry_current_capacity',1800))
        self.assertFalse(any(fill['date']==self.days[20] for fill in account['fills']))
        self.assertEqual(account['fills'][0]['date'],self.days[21])
        self.assertIn('not_known_at_open',account['entry_policy']['current_day_volume_gate'])

    def test_known_execution_rejection_retries_only_while_episode_is_desired(self):
        self.bars[20]['suspended']=True
        account=self.run_account()
        self.assertEqual(account['events'][0]['reason'],'known_execution_constraint')
        self.assertEqual(account['fills'][0]['date'],self.days[21])
        no_buy=self.run_account(cycles=[dict(cycle_id='one_attempt_episode',entry_date=self.days[20],exit_date=self.days[21])])
        self.assertEqual(no_buy['fills'],[])

    def test_hold_limit_exit_does_not_reenter_same_open_and_new_entry_restarts_clock(self):
        account=self.run_account(stop=300)
        fills=account['fills']
        self.assertEqual([(row['date'],row['side']) for row in fills],
            [(self.days[20],'buy'),(self.days[272],'sell'),(self.days[273],'buy'),(self.days[299],'sell')])
        self.assertEqual(fills[1]['reason'],'max_holding_exit')
        self.assertNotEqual(fills[0]['cycle_id'],fills[2]['cycle_id'])
        self.assertEqual(fills[0]['episode_id'],fills[2]['episode_id'])
        self.assertFalse(account['daily_recovery_journal'])

    def test_daily_risk_uses_five_complete_flat_sessions_then_current_daily_signal(self):
        for row in self.bars[22:]:
            for key in ('open','high','low','close'):row[key]=4
        account=self.run_account()
        fills=account['fills']
        self.assertEqual([(row['date'],row['side']) for row in fills[:3]],
            [(self.days[20],'buy'),(self.days[23],'sell'),(self.days[29],'buy')])
        self.assertEqual(account['config']['daily_recovery'],RECOVERY_40_DAILY_RETRY)
        self.assertEqual(account['equity_curve'][29]['drawdown'],.18)
        self.assertEqual(account['metrics']['maximum_drawdown'],.18)

    def test_blocked_terminal_exit_keeps_inventory_and_fails_terminal_settlement(self):
        self.bars[44]['limit_down']=True
        account=self.run_account()
        self.assertTrue(account['positions'])
        self.assertFalse(account['risk']['terminal_settled'])
        self.assertEqual(account['fills'][-1]['side'],'buy')
        self.assertTrue(any(row['date']==self.days[44] and row['reason']=='known_execution_constraint'
                            for row in account['events']))

    def test_new_entry_and_resume_contracts_must_be_explicit_together(self):
        for options in (dict(daily_recovery=RECOVERY_40),dict(entry_policy=None),
                        dict(entry_policy='unregistered_retry'),dict(config=replace(self.config,execution_price_field='close')),
                        dict(config=replace(self.config,max_holding_sessions=251))):
            with self.subTest(options=options),self.assertRaises(ValueError):self.run_account(**options)
        original=self.run_account(entry_policy=None,daily_recovery=RECOVERY_40)
        self.assertNotIn('entry_policy',original)
        self.assertEqual(original['fills'][0]['quantity'],2000)
        self.assertNotIn('precommitted_entry_budget',original['fills'][0])

    def test_fixed_daily_targets_exit_on_unknown_and_force_terminal_exit_without_extra_lag(self):
        sessions=self.days[:45]
        targets=[dict(execution_date=day,known=True,desired=True) for day in sessions]
        targets[23].update(known=False,desired=False)
        cycles=cycles_from_daily_targets(targets,sessions,episode_prefix='fixed')
        self.assertEqual([(row['entry_date'],row['exit_date']) for row in cycles],
                         [(sessions[20],sessions[23]),(sessions[24],sessions[-1])])
        account=self.run_account(cycles=cycles)
        self.assertEqual([(row['date'],row['side']) for row in account['fills']],
                         [(sessions[20],'buy'),(sessions[23],'sell'),(sessions[24],'buy'),(sessions[-1],'sell')])
        targets[23]['desired']=True
        with self.assertRaisesRegex(ValueError,'known-state'):
            cycles_from_daily_targets(targets,sessions,episode_prefix='fixed')

    def test_all_unknown_targets_stay_cash_for_the_entire_report_window(self):
        sessions=self.days[:45]
        targets=[dict(execution_date=day,known=False,desired=False) for day in sessions]
        cycles=cycles_from_daily_targets(targets,sessions,episode_prefix='missing')
        self.assertEqual(cycles,[])
        account=run_allocation_account(self.bars[:45],sessions=sessions,assets=['SYNTHETIC'],
            cycles=cycles,actions=[],config=self.config,daily_recovery=RECOVERY_40_DAILY_RETRY,
            entry_policy=NAV90_DAILY_RETRY)
        self.assertEqual(account['fills'],[])
        self.assertEqual(account['metrics']['ending_cash'],10000)
