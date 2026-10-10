"""Prospective controls are mandatory before any synthetic market calculation."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from quant_robot.paper import comparative_allocation as comparison
from tests.unit.test_annual_allocation_account import A, cash_action, change, cycle, fixture


class ComparativeAllocationTests(unittest.TestCase):
    def setUp(self):
        self.days,self.bars=fixture(35,(A,))
        self.policy=comparison.policy_template(study_id='synthetic_only',first_session=self.days[20],
            terminal_session=self.days[-1],later_start=self.days[27])

    def run_case(self,**kwargs):
        return comparison.run_comparison(self.bars,sessions=self.days,asset=A,
            strategy_cycles=[cycle(self.days)],actions=kwargs.pop('actions',[]),policy=kwargs.pop('policy',self.policy),**kwargs)

    def test_missing_holding_cash_or_maxholding_renewal_rejected_before_prices(self):
        variants=[]
        for role in ('holding','cash'):
            policy=deepcopy(self.policy);del policy['controls'][role];variants.append(policy)
        policy=deepcopy(self.policy);del policy['controls']['holding']['renewal'];variants.append(policy)
        for policy in variants:
            with self.subTest(policy=policy),patch.object(comparison,'run_allocation_account') as engine:
                with self.assertRaises(ValueError):self.run_case(policy=policy)
                engine.assert_not_called()

    def test_no_fee_scenario_selection_or_risk_loosening(self):
        for field,value in [('cost_cases',self.policy['cost_cases'][:1]),('primary',dict(minimum_commission_CNY=0,slippage_bps_each=0)),
                            ('common',dict(self.policy['common'],marked_position_limit_CNY=1100))]:
            policy=deepcopy(self.policy);policy[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.run_case(policy=policy)

    def test_all_nine_cases_run_three_accounts_with_same_dates_and_costs(self):
        result=self.run_case()
        self.assertEqual(len(result['accounts']),9)
        for key,accounts in result['accounts'].items():
            self.assertEqual(set(accounts),{'strategy','holding','cash'})
            self.assertEqual(accounts['cash']['metrics']['pnl_cny'],0)
            self.assertEqual(accounts['cash']['fills'],[])
            for account in accounts.values():
                self.assertEqual([r['date'] for r in account['equity_curve']],self.days)
                self.assertEqual(account['config'],accounts['strategy']['config'])
            self.assertTrue(result['comparisons'][key]['calendar_and_cost_identity'])
        self.assertFalse(result['net_positive_EV_verified'])

    def test_same_rule_produces_identical_candidate_and_holding_accounts(self):
        cycles=comparison.holding_cycles(self.days,self.policy)
        result=comparison.run_comparison(self.bars,sessions=self.days,asset=A,strategy_cycles=cycles,actions=[],policy=self.policy)
        for item in result['comparisons'].values():
            self.assertEqual(item['strategy_minus_holding_CNY'],0)

    def test_holding_renewal_has_no_same_day_roundtrip_or_price_selection(self):
        days,_=fixture(600,(A,));policy=comparison.policy_template(study_id='synthetic_long',
            first_session=days[19],terminal_session=days[-1],later_start=days[300])
        cycles=comparison.holding_cycles(days,policy)
        self.assertEqual([(days.index(c['entry_date']),days.index(c['exit_date'])) for c in cycles],[(20,272),(273,525),(526,599)])

    def test_holding_budget_gap_skips_cycle_without_catchup(self):
        change(self.bars,self.days[20],price=5.1)
        result=self.run_case()
        holding=result['accounts']['min5_slip10']['holding']
        self.assertEqual(holding['fills'],[])
        self.assertEqual(holding['events'][0]['reason'],'entry_budget_or_cash')

    def test_dividend_entitlement_counts_even_after_exdate_exit_and_cash_waits(self):
        action=cash_action(self.days,record=21,ex=22,pay=29,cash='.1')
        result=comparison.run_comparison(self.bars,sessions=self.days,asset=A,
            strategy_cycles=[cycle(self.days,20,22)],actions=[action],policy=self.policy)
        primary=result['comparisons']['min5_slip0']['accounts']
        self.assertEqual(primary['strategy']['net_PnL_CNY'],10)
        self.assertEqual(primary['strategy']['completed_episode_win_fraction'],1)
        self.assertEqual(primary['cash']['net_PnL_CNY'],0)
        curve=result['accounts']['min5_slip0']['strategy']['equity_curve']
        self.assertEqual(curve[22]['dividend_receivable'],20)
        self.assertEqual(curve[22]['cash'],9990)
        self.assertEqual(curve[29]['cash'],10010)

    def test_unpaid_dividend_cannot_pass_terminal_settlement(self):
        action={**cash_action(self.days),'pay_date':'2021-01-01'}
        result=self.run_case(actions=[action])
        self.assertFalse(result['comparisons']['min5_slip0']['accounts']['strategy']['terminal_settled'])

    def test_empty_strategy_still_has_both_controls_and_no_win_rate(self):
        result=comparison.run_comparison(self.bars,sessions=self.days,asset=A,strategy_cycles=[],actions=[],policy=self.policy)
        primary=result['comparisons']['min5_slip10']
        self.assertIsNone(primary['accounts']['strategy']['completed_episode_win_fraction'])
        self.assertEqual(primary['accounts']['strategy']['net_PnL_CNY'],0)
        self.assertLess(primary['accounts']['holding']['net_PnL_CNY'],0)

    def test_common_terminal_cannot_silently_drop_tail(self):
        policy=deepcopy(self.policy);policy['window']['terminal_session']=self.days[-2]
        with self.assertRaisesRegex(ValueError,'common terminal'):self.run_case(policy=policy)

    def test_unfilled_holding_exit_skips_fixed_renewal_without_catchup(self):
        days,bars=fixture(278,(A,))
        for index in (272,273):change(bars,days[index],volume=0)
        policy=comparison.policy_template(study_id='synthetic_exit_delay',first_session=days[20],
            terminal_session=days[-1],later_start=days[200])
        result=comparison.run_comparison(bars,sessions=days,asset=A,strategy_cycles=[],actions=[],policy=policy)
        holding=result['accounts']['min5_slip10']['holding']
        buys=[r for r in holding['fills'] if r['side']=='buy']
        self.assertEqual(len(buys),1)
        self.assertEqual(holding['fills'][-1]['date'],days[274])
        self.assertTrue(any(r['date']==days[273] and r['reason']=='occupied_at_session_start' for r in holding['events']))
        self.assertTrue(any(r['reason']=='holding_limit' for r in holding['risk']['breaches']))

    def test_holding_stop_survives_later_scheduled_renewal(self):
        days,bars=fixture(278,(A,))
        change(bars,days[21],price=3)
        policy=comparison.policy_template(study_id='synthetic_stop',first_session=days[20],
            terminal_session=days[-1],later_start=days[200])
        result=comparison.run_comparison(bars,sessions=days,asset=A,strategy_cycles=[],actions=[],policy=policy)
        holding=result['accounts']['min5_slip10']['holding']
        self.assertEqual(len([r for r in holding['fills'] if r['side']=='buy']),1)
        self.assertTrue(holding['risk']['new_entries_halted'])
        self.assertTrue(any(r['date']==days[273] and r['reason']=='risk_halted' for r in holding['events']))
