"""Synthetic checks of the global drawdown pause and unchanged equity peak."""
from copy import deepcopy
from decimal import Decimal
import unittest

from quant_robot.paper.daily_recovery import DailyRecovery, RECOVERY_40
from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account
from quant_robot.paper.comparative_allocation import dd40_policy_template, run_comparison
from tests.unit.test_annual_allocation_account import A, fixture, change, cycle


class DrawdownReentryTests(unittest.TestCase):
    def source(self):
        days, bars = fixture(50, (A,), price=5)
        for row in bars:
            row['volume'] = '10000000'
        for day in days[21:]:
            change(bars, day, price=2.8)
        return days, bars

    def account(self, days, bars, cycles):
        return run_allocation_account(bars, sessions=days, assets=(A,), cycles=cycles,
            actions=(), config=AllocationConfig(max_position_cny=10000,
                max_position_fraction=1, max_drawdown=.4,
                execution_price_field='open', slippage_bps=0), daily_recovery=RECOVERY_40)

    def test_cash_below_global_line_can_resume_then_exposure_retriggers(self):
        days, bars = self.source()
        account = self.account(days, bars, [cycle(days,20,24,'first'),
            cycle(days,26,27,'cooling'), cycle(days,28,32,'new'), cycle(days,35,40,'third')])
        buys = [f for f in account['fills'] if f['side']=='buy']
        self.assertEqual([f['date'] for f in buys], [days[20],days[28],days[35]])
        self.assertEqual([f['date'] for f in account['fills'] if f['side']=='sell'],
                         [days[22],days[29],days[36]])
        self.assertFalse(account['risk']['new_entries_halted'])
        self.assertGreater(account['metrics']['maximum_drawdown'],.4)
        journal = account['daily_recovery_journal']
        self.assertEqual([e['date'] for e in journal if e['kind']=='flat_cooldown_started'],
                         [days[22],days[29],days[36]])
        for row in account['equity_curve'][21:]:
            self.assertAlmostEqual(row['drawdown'],1-row['equity']/10000)
            self.assertLess(row['equity'],6000)

    def test_exit_constraints_delay_cooling(self):
        days, bars = self.source()
        for day in days[22:25]:
            change(bars,day,suspended=True)
        account = self.account(days,bars,[cycle(days,20,24,'first'),
            cycle(days,28,30,'blocked'),cycle(days,31,35,'new')])
        self.assertEqual([f['date'] for f in account['fills'] if f['side']=='buy'],
                         [days[20],days[31]])
        self.assertEqual(account['fills'][1]['date'],days[25])

    def test_exact_line_and_cash_only_days_do_not_reset_clock(self):
        recovery = DailyRecovery(RECOVERY_40)
        def close(i,dd,exposed):
            recovery.after_close(i,str(i),previous=Decimal(6000),equity=Decimal(6000),
                positions={},drawdown=Decimal(dd),had_exposure=exposed)
        close(0,'.399999',True)
        self.assertFalse(recovery.paused)
        close(1,'.4',True)
        self.assertTrue(recovery.paused)
        for i in range(2,7):
            close(i,'.4',False)
            recovery.before_open(i,str(i),positions={},permanently_halted=False)
            self.assertTrue(recovery.paused)
        recovery.before_open(7,'7',positions={},permanently_halted=False)
        self.assertFalse(recovery.paused)
        self.assertEqual(sum(e['kind']=='global_drawdown_pause' for e in recovery.journal),1)

    def test_all_controls_share_policy_and_changed_threshold_rejected(self):
        days,bars=self.source()
        policy=dd40_policy_template(study_id='synthetic',first_session=days[20],
            later_start=days[30],terminal_session=days[-1])
        result=run_comparison(bars,sessions=days,asset=A,strategy_cycles=[cycle(days)],
            actions=(),policy=policy)
        self.assertEqual(sum(map(len,result['accounts'].values())),27)
        for accounts in result['accounts'].values():
            for role in ('strategy','holding','cash'):
                self.assertEqual(accounts[role]['config']['max_drawdown'],.4)
                self.assertEqual(accounts[role]['config'],accounts['strategy']['config'])
        bad=deepcopy(policy);bad['common']['paper_drawdown_limit']=.41
        with self.assertRaises(ValueError):
            run_comparison(bars,sessions=days,asset=A,strategy_cycles=[],actions=(),policy=bad)
