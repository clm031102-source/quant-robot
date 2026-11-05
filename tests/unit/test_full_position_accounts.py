"""Full NAV risk and control tests on synthetic bars only."""
import unittest
from quant_robot.paper.annual_allocation import AllocationConfig,run_allocation_account
from quant_robot.paper.comparative_allocation import full_nav_policy_template,run_comparison
from quant_robot.research.full_position_accounts import audit_terminal_rights
from tests.unit.test_annual_allocation_account import fixture,change,cycle,A,G,cash_action


class FullPositionAccountTests(unittest.TestCase):
    def source(self,count=34):
        days,bars=fixture(count,(A,),price=5)
        for row in bars:row['volume']='10000000'
        return days,bars

    def run_account(self,days,bars,**kwargs):
        return run_allocation_account(bars,sessions=days,assets=(A,),actions=(),
            cycles=[cycle(days),cycle(days,28,32,'two')],
            config=AllocationConfig(max_position_fraction=1,max_position_cny=10000,
                slippage_bps=0,execution_price_field='open',**kwargs))

    def test_full_nav_appreciation_is_not_fixed_cap_breach(self):
        days,bars=self.source()
        for d in days[21:]:change(bars,d,price=6)
        result=self.run_account(days,bars)
        self.assertEqual(result['fills'][0]['quantity'],1900)
        self.assertGreater(result['metrics']['ending_cash'],10000)
        self.assertFalse(result['risk']['breaches'])
        self.assertFalse(any(f['reason']=='position_trim' for f in result['fills']))
        self.assertTrue(all(r['cash']>=0 for r in result['equity_curve']))

    def test_gap_cancels_whole_order_and_fee_lots_fit_cash(self):
        days,bars=self.source()
        change(bars,days[20],price=6)
        result=self.run_account(days,bars)
        self.assertFalse(any(f['date']==days[20] for f in result['fills']))
        self.assertTrue(any(e['reason']=='entry_budget_or_cash' for e in result['events']))
        self.assertTrue(all(f['quantity']%100==0 for f in result['fills']))

    def test_loss_halts_next_entries_permanently(self):
        days,bars=self.source()
        for d in days[21:]:change(bars,d,price=4.9)
        result=self.run_account(days,bars)
        self.assertTrue(result['risk']['new_entries_halted'])
        self.assertEqual([f['side'] for f in result['fills']],['buy','sell'])
        self.assertEqual(result['fills'][1]['date'],days[22])
        self.assertGreater(result['metrics']['maximum_daily_loss_cny'],60)

    def test_full_mode_rejects_multiple_assets(self):
        days,bars=fixture()
        with self.assertRaisesRegex(ValueError,'single asset'):
            run_allocation_account(bars,sessions=days,assets=(A,G),cycles=[cycle(days)],actions=(),
                config=AllocationConfig(max_position_fraction=1))

    def test_nine_cases_and_terminal_recorded_rights_audited(self):
        days,bars=self.source()
        policy=full_nav_policy_template(study_id='synthetic',first_session=days[20],
            terminal_session=days[-1],later_start=days[27])
        event=cash_action(days,record=32,ex=33,pay=33)
        result=run_comparison(bars,sessions=days,asset=A,strategy_cycles=[cycle(days,20,33)],
            actions=[event],policy=policy)
        self.assertEqual(len(result['comparisons']),9)
        self.assertEqual(sum(len(v) for v in result['accounts'].values()),27)
        for roles in result['accounts'].values():
            for account in roles.values():
                account['corporate_action_journal']=[e for e in account['corporate_action_journal'] if e['kind']!='cash_paid_after_fills']
        audit_terminal_rights(result,[event])
        self.assertFalse(result['comparisons']['min5_slip10']['accounts']['strategy']['terminal_settled'])
