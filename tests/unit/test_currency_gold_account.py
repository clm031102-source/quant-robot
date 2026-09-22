import unittest
from quant_robot.research.currency_gold_account import episode_cycles, financial_screen


class CurrencyGoldAccountTests(unittest.TestCase):
    def test_contiguous_quarters_form_one_opportunity_and_unknown_splits(self):
        sessions=[f'2020-01-{d:02d}' for d in range(1,32)]
        rows=[dict(state=s,episode_id=e,entry_date=sessions[i],exit_date=sessions[i+1])
              for i,s,e in [(20,1,1),(21,1,1),(22,None,None),(23,1,2)]]
        cycles,omitted=episode_cycles(rows,sessions)
        self.assertEqual(len(cycles),2)
        self.assertEqual(cycles[0]['entry_date'],sessions[20])
        self.assertEqual(cycles[0]['exit_date'],sessions[22])
        self.assertEqual(cycles[0]['selected_quarters'],2)
        self.assertEqual(omitted,[])

    def test_missing_warmup_is_cancelled_not_shifted(self):
        sessions=[f'2020-01-{d:02d}' for d in range(1,32)]
        rows=[dict(state=1,episode_id=1,entry_date=sessions[19],exit_date=sessions[23])]
        cycles,omitted=episode_cycles(rows,sessions)
        self.assertEqual(cycles,[])
        self.assertEqual(omitted[0]['entry_date'],sessions[19])

    def summary(self):
        return dict(terminal_settled=True,full_net_PnL_CNY=100,later_net_contribution_CNY=40,
            annual_contributions_CNY={str(y):10 for y in range(2014,2024)},
            risk_within_all_observed_limits=True,
            position_episodes=[dict(completed=True,entry_date=f'{y}-01-02',net_PnL_CNY=10)
                               for y in [2014,2016,2018,2020,2021,2023]])

    def test_positive_net_statistics_and_risk_are_both_required(self):
        summary=self.summary();account={'metrics':{'maximum_drawdown':.01}}
        self.assertTrue(financial_screen(summary,account)['conditional_account_screen_passed'])
        summary['risk_within_all_observed_limits']=False
        self.assertFalse(financial_screen(summary,account)['conditional_account_screen_passed'])

    def test_quarter_count_cannot_replace_completed_trade_count(self):
        summary=self.summary();summary['position_episodes']=summary['position_episodes'][-3:]
        result=financial_screen(summary,{'metrics':{'maximum_drawdown':0}})
        self.assertFalse(result['checks']['full_completed_episodes'])

    def test_flat_or_half_wins_are_not_majority(self):
        summary=self.summary()
        for row in summary['position_episodes'][::2]:row['net_PnL_CNY']=0
        result=financial_screen(summary,{'metrics':{'maximum_drawdown':0}})
        self.assertFalse(result['checks']['full_net_win_majority'])

    def test_later_count_uses_entry_date_and_excludes_carry_in(self):
        summary=self.summary();summary['position_episodes'][-3]['entry_date']='2019-12-31'
        result=financial_screen(summary,{'metrics':{'maximum_drawdown':0}})
        self.assertEqual(result['later_new_completed_episodes'],2)
        self.assertFalse(result['checks']['later_new_completed_episodes'])
