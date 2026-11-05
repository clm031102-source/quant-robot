"""Synthetic lifecycle checks for the separately authorized recovery policy."""
from copy import deepcopy
from decimal import Decimal
import unittest
from quant_robot.paper.daily_recovery import DailyRecovery, RECOVERY
from quant_robot.paper.annual_allocation import AllocationConfig,run_allocation_account
from quant_robot.paper.comparative_allocation import recovery_policy_template,run_comparison
from tests.unit.test_annual_allocation_account import A,fixture,change,cycle


class DailyRecoveryTests(unittest.TestCase):
    def source(self,count=45):
        days,bars=fixture(count,(A,),price=5)
        for r in bars:r['volume']='10000000'
        return days,bars

    def account(self,days,bars,cycles):
        return run_allocation_account(bars,sessions=days,assets=(A,),cycles=cycles,actions=(),
            config=AllocationConfig(max_position_cny=10000,max_position_fraction=1,
                execution_price_field='open',slippage_bps=0),daily_recovery=RECOVERY)

    def test_five_complete_sessions_after_flat_and_only_new_cycle(self):
        days,bars=self.source()
        for d in days[21:]:change(bars,d,price=4.85)
        # Day21 loses285; day22 exits; days23..27 complete cooling;28 may enter.
        a=self.account(days,bars,[cycle(days,20,24,'first'),cycle(days,26,27,'blocked'),cycle(days,28,32,'new')])
        self.assertEqual([f['date'] for f in a['fills'] if f['side']=='buy'],[days[20],days[28]])
        self.assertEqual(a['fills'][1]['date'],days[22])
        self.assertEqual(a['fills'][1]['reason'],'daily_loss_pause_exit')
        self.assertTrue(any(e['reason']=='daily_risk_pause' for e in a['events']))
        self.assertFalse(a['risk']['new_entries_halted'])
        self.assertFalse(a['risk']['breaches'])
        self.assertLess(a['equity_curve'][28]['equity'],10000)
        self.assertIsNone(a['config']['max_daily_loss_cny'])

    def test_delayed_exit_does_not_start_cooldown_until_flat(self):
        days,bars=self.source()
        for d in days[21:]:change(bars,d,price=4.85)
        for d in days[22:25]:change(bars,d,suspended=True)
        a=self.account(days,bars,[cycle(days,20,24,'first'),cycle(days,28,30,'blocked'),cycle(days,31,35,'new')])
        self.assertEqual(a['fills'][1]['date'],days[25])
        self.assertEqual([f['date'] for f in a['fills'] if f['side']=='buy'],[days[20],days[31]])

    def test_drawdown_halt_never_recovers_or_resets_peak(self):
        days,bars=self.source()
        for d in days[21:]:change(bars,d,price=4.5)
        a=self.account(days,bars,[cycle(days,20,24,'first'),cycle(days,35,40,'new')])
        self.assertTrue(a['risk']['new_entries_halted'])
        self.assertEqual(len([f for f in a['fills'] if f['side']=='buy']),1)
        self.assertGreater(a['metrics']['maximum_drawdown'],.08)
        self.assertFalse(any(e['kind'].startswith('eligible') for e in a['daily_recovery_journal']))

    def test_threshold_uses_previous_nav_and_trigger_resets_flat_counter(self):
        r=DailyRecovery(RECOVERY)
        r.after_close(10,'d10',previous=Decimal(12000),equity=Decimal(11760),positions={})
        self.assertEqual(r.journal[0]['threshold'],Decimal(240))
        r.after_close(14,'d14',previous=Decimal(10000),equity=Decimal(9800),positions={})
        r.before_open(16,'d16',positions={},permanently_halted=False)
        self.assertTrue(r.paused)
        r.before_open(20,'d20',positions={},permanently_halted=False)
        self.assertFalse(r.paused)

    def test_controls_use_identical_recovery_policy(self):
        days,bars=self.source()
        p=recovery_policy_template(study_id='synthetic',first_session=days[20],later_start=days[30],terminal_session=days[-1])
        a=run_comparison(bars,sessions=days,asset=A,strategy_cycles=[cycle(days)],actions=(),policy=p)
        self.assertEqual(sum(len(v) for v in a['accounts'].values()),27)
        for roles in a['accounts'].values():
            self.assertEqual(roles['strategy']['config'],roles['holding']['config'])
            self.assertEqual(roles['strategy']['config'],roles['cash']['config'])
        changed=deepcopy(p);changed['daily_recovery']['complete_flat_sessions']=4
        with self.assertRaisesRegex(ValueError,'recovery'):
            run_comparison(bars,sessions=days,asset=A,strategy_cycles=[],actions=(),policy=changed)
