import unittest

from quant_robot.research.equity_gold_diagnostic import annual_contributions, block_interval, position_episodes, financial_screen


class EquityGoldDiagnosticTests(unittest.TestCase):
    def test_continuous_year_deltas_include_terminal_fee_in_last_year(self):
        curve = [{'date': f'{year}-12-31', 'equity': 10000+5*(year-2013)} for year in range(2014,2024)]
        curve += [{'date': '2024-01-02', 'equity': 10047}]
        values, terminal = annual_contributions(curve)
        self.assertEqual(list(values.values()), [5]*9+[2])
        self.assertEqual(terminal, -3)
        self.assertEqual(sum(values.values()), 47)

    def test_circular_two_year_blocks_preserve_alternating_dependence(self):
        self.assertEqual(block_interval([1,-1]*5), [0,0])
        self.assertEqual(block_interval([3]*10), [3,3])

    def test_position_episode_combines_partial_sales_fees_and_earned_cash(self):
        result = {'fills': [
            dict(date='2014-01-03',asset_id='A',cycle_id='2014',side='buy',quantity=200,notional=800,fee=5),
            dict(date='2014-01-24',asset_id='A',cycle_id='2014',side='sell',quantity=100,notional=410,fee=5),
            dict(date='2015-01-05',asset_id='A',cycle_id='2014',side='sell',quantity=100,notional=420,fee=5)],
            'corporate_action_journal': [dict(date='2014-01-20',kind='record_entitlement',event_id='d',quantity=200)]}
        actions = [dict(event_id='d',asset_id='A',cash_per_unit='.1')]
        rows = position_episodes(result, actions)
        self.assertEqual(rows[0]['net_PnL_CNY'], 35)
        self.assertEqual(rows[0]['fees_CNY'], 15)
        self.assertTrue(rows[0]['completed'])

    def test_open_position_is_not_a_completed_profitable_trade(self):
        result = {'fills':[dict(date='2014-01-03',asset_id='A',cycle_id='2014',side='buy',quantity=200,notional=800,fee=5)],
                  'corporate_action_journal':[]}
        row = position_episodes(result, [])[0]
        self.assertFalse(row['completed'])
        self.assertIsNone(row['net_PnL_CNY'])

    def test_financial_pass_does_not_override_risk_or_certify_EV(self):
        summary = dict(annual_contributions_CNY={str(y):3 for y in range(2014,2024)},full_net_PnL_CNY=30,
                       later_net_contribution_CNY=12,positive_years=10,paired_entry_cycles=[str(y) for y in range(2014,2024)],
                       terminal_settled=True,risk_within_all_observed_limits=False)
        decision = financial_screen(summary)
        self.assertTrue(decision['conditional_financial_screen_passed'])
        self.assertFalse(decision['risk_within_all_observed_limits'])
        self.assertFalse(decision['net_positive_EV_verified'])
        self.assertFalse(decision['paper_promotion_allowed'])
