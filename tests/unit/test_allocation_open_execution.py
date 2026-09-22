"""Open fills retain previous-close sizing and current-close risk observations."""
import unittest

from quant_robot.paper.annual_allocation import AllocationConfig, run_allocation_account
from tests.unit.test_annual_allocation_account import A, change, cycle, fixture


def run(days, bars, **kwargs):
    return run_allocation_account(bars, sessions=days, assets=(A,), actions=[],
        cycles=[cycle(days)], config=AllocationConfig(execution_price_field='open',slippage_bps=0,**kwargs))


class OpenExecutionTests(unittest.TestCase):
    def test_open_fill_and_close_mark_are_distinct(self):
        days,bars=fixture(26,(A,))
        change(bars,days[20],open='3.8',low='3.8',high='4',close='4')
        result=run(days,bars)
        buy=result['fills'][0]
        self.assertEqual((buy['quantity'],buy['price']),(200,3.8))
        self.assertEqual(result['equity_curve'][20]['equity'],10035)
        self.assertEqual(result['equity_curve'][20]['position_values'][A]['price'],4)

    def test_open_gap_cancels_without_resizing_even_when_close_fits(self):
        days,bars=fixture(26,(A,))
        change(bars,days[20],open='5.1',high='5.1',low='4',close='4')
        result=run(days,bars)
        self.assertEqual(result['fills'],[])
        self.assertEqual(result['events'][0]['reason'],'entry_budget_or_cash')

    def test_breach_at_close_exits_at_next_open_not_breach_price(self):
        days,bars=fixture(26,(A,))
        change(bars,days[21],open='4',high='4',close='3.5',low='3.5')
        change(bars,days[22],open='3',low='3',close='3.8',high='3.8')
        result=run(days,bars)
        sale=result['fills'][1]
        self.assertEqual((sale['date'],sale['price'],sale['reason']),(days[22],3,'account_risk_exit'))
        self.assertTrue(result['risk']['new_entries_halted'])

    def test_previous_close_still_controls_quantity(self):
        days,bars=fixture(26,(A,))
        change(bars,days[19],open='2',low='2',close='4',high='4')
        result=run(days,bars)
        self.assertEqual(result['fills'][0]['quantity'],200)

    def test_close_trim_runs_at_following_open(self):
        days,bars=fixture(26,(A,),price=3.3)
        change(bars,days[21],open='3.3',low='3.3',close='3.4',high='3.4')
        change(bars,days[22],open='3.35',low='3.3',close='3.3',high='3.35')
        result=run(days,bars)
        trim=result['fills'][1]
        self.assertEqual((trim['quantity'],trim['price'],trim['reason']),(100,3.35,'position_trim'))
        self.assertFalse(result['risk']['within_all_observed_limits'])

    def test_unsupported_execution_basis_rejected(self):
        days,bars=fixture(26,(A,))
        with self.assertRaisesRegex(ValueError,'execution basis'):
            run_allocation_account(bars,sessions=days,assets=(A,),cycles=[cycle(days)],actions=[],
                config=AllocationConfig(execution_price_field='vwap'))
