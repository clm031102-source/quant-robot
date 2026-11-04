"""Synthetic-only checks for the frozen GPRT account and statistical rules."""
from copy import deepcopy
from datetime import date, timedelta
import unittest
from unittest.mock import patch

import numpy as np

from quant_robot.research import geopolitical_account as account


def invented_calendar():
    day = date(2022, 1, 1); end = date(2025, 12, 31); result = []
    while day <= end:
        if day.weekday() < 5:
            result.append(day.isoformat())
        day += timedelta(days=1)
    return result


def source_states():
    ranges = [('202203', '202207'), ('202210', '202211'), ('202311', '202402'),
              ('202405', '202405'), ('202412', '202412'), ('202503', '202509'),
              ('202511', '202511')]
    return [dict(month=m, state=int(any(a <= m <= b for a, b in ranges))) for m in account.MONTHS]


def invented_bars(plan):
    return [dict(asset_id=account.ASSET, date=d, open='4.9', close='4.9', high='4.91',
                 low='4.89', volume='10000000') for d in plan['sessions']]


class GeopoliticalAccountTests(unittest.TestCase):
    def setUp(self):
        self.states = source_states()
        self.plan = account.make_plan(invented_calendar(), self.states)

    def test_seven_episodes_and_four_new_later_without_counting_carry_in(self):
        cycles = self.plan['strategy_cycles']
        self.assertEqual(len(cycles), 7)
        self.assertEqual(sum(c['new_later_episode'] for c in cycles), 4)
        carry = next(c for c in cycles if c['source_episode_start'] == '202311')
        self.assertEqual(carry['exit_date'], '2024-03-15')
        self.assertFalse(carry['new_later_episode'])
        self.assertEqual(self.plan['sessions'].index(cycles[0]['entry_date']), 20)

    def test_weekend_decision_waits_until_next_calendar_open(self):
        cycle = next(c for c in self.plan['strategy_cycles'] if c['cycle_id'] == 'gprt_202503')
        self.assertEqual(cycle['entry_date'], '2025-03-17')

    def test_fixed_1000_original_policy_not_later_800_buffer(self):
        policy = self.plan['comparison_policy']
        self.assertEqual(policy['schema_version'], 1)
        self.assertEqual(policy['common']['all_in_entry_budget_CNY'], 1000)
        self.assertNotIn('position_buffer', policy)

    def test_252_session_exit_never_reenters_same_long_source_episode(self):
        states = [dict(month=m, state=1) for m in account.MONTHS]
        plan = account.make_plan(invented_calendar(), states)
        self.assertEqual(len(plan['strategy_cycles']), 1)
        cycle = plan['strategy_cycles'][0]
        self.assertEqual(plan['sessions'].index(cycle['exit_date']) - 20, 252)

    def test_final_episode_exits_in_2025_and_no_2026_calendar_is_accepted(self):
        states = [dict(month=m, state=int(m == '202512')) for m in account.MONTHS]
        plan = account.make_plan(invented_calendar(), states)
        self.assertEqual(plan['strategy_cycles'][0]['exit_date'], '2025-12-31')
        with self.assertRaisesRegex(ValueError, '2025'):
            account.make_plan(invented_calendar() + ['2026-01-02'], states)

    def test_missing_unknown_and_nonbinary_states_are_not_silently_selected(self):
        with self.assertRaisesRegex(ValueError, '46'):
            account.make_plan(invented_calendar(), self.states[:-1])
        for value in (True, '1', 2):
            states = deepcopy(self.states); states[0]['state'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                account.make_plan(invented_calendar(), states)
        states = deepcopy(self.states); states[0]['state'] = None
        plan = account.make_plan(invented_calendar(), states)
        self.assertEqual(plan['strategy_cycles'][0]['source_episode_start'], '202204')

    def test_all_27_real_engine_accounts_and_reconciled_primary_fees(self):
        with patch.object(account.comparative_allocation, 'run_comparison',
                          wraps=account.comparative_allocation.run_comparison) as runner:
            result = account.calculate(bars=invented_bars(self.plan), actions=[],
                                       plan=self.plan, cadence_rows=self.states)
        runner.assert_called_once()
        self.assertEqual(sum(len(v) for v in result['comparison']['accounts'].values()), 27)
        self.assertEqual(result['completed_full_episodes'], 7)
        self.assertEqual(result['completed_new_later_episodes'], 4)
        self.assertLess(result['primary_summary']['net_PnL_CNY'], 0)
        self.assertAlmostEqual(sum(result['monthly_PnL_CNY'].values()), result['primary_summary']['net_PnL_CNY'])
        self.assertFalse(result['checks']['majority_full_episodes_profitable'])
        self.assertFalse(result['checks']['monthly_interval_lower_positive'])
        self.assertFalse(result['conditional_screen_passed'])
        self.assertFalse(result['paper_promotion_allowed'])
        self.assertEqual(result['new_forward_days'], 0)

    def test_changed_policy_or_cycle_is_rejected_before_comparison(self):
        for key in ('comparison_policy', 'strategy_cycles'):
            plan = deepcopy(self.plan)
            if key == 'comparison_policy':
                plan[key]['primary']['minimum_commission_CNY'] = 0
            else:
                plan[key][0]['exit_date'] = plan['sessions'][-1]
            with patch.object(account.comparative_allocation, 'run_comparison') as runner:
                with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'plan changed'):
                    account.calculate(bars=[], actions=[], plan=plan, cadence_rows=self.states)
                runner.assert_not_called()

    def test_recorded_terminal_right_blocks_control_settlement_even_before_ex_date(self):
        action = dict(event_id='synthetic_future_ex', asset_id=account.ASSET,
            record_date='2025-12-30', ex_date='2026-01-02', pay_date='2026-01-05',
            cash_per_unit='.5', share_multiplier='1')
        result = account.calculate(bars=invented_bars(self.plan), actions=[action],
                                   plan=self.plan, cadence_rows=self.states)
        holding = result['comparison']['accounts']['min5_slip10']['holding']
        self.assertTrue(holding['risk']['terminal_settled'])  # old engine lacks pre-ex rights
        self.assertEqual(holding['terminal_entitlement_audit']['unpaid_rights'],
                         [dict(event_id='synthetic_future_ex', unpaid_CNY=100)])
        self.assertFalse(result['checks']['primary_controls_terminal_settled'])
        self.assertFalse(result['cost_summaries']['min5_slip10']['accounts']['holding']['terminal_settled'])

    def test_monthly_series_keeps_zero_months_and_later_carry_contribution(self):
        curve = []
        for d in self.plan['sessions']:
            equity = 10000 if d < '2023-11-15' else 10010 if d < '2024-01-02' else 10013
            curve.append(dict(date=d, equity=equity))
        months = account.monthly_contributions(curve, self.plan['sessions'])
        self.assertEqual(len(months), 46)
        self.assertEqual(months['202203'], 0)
        self.assertEqual(months['202311'], 10)
        self.assertEqual(months['202401'], 3)
        self.assertEqual(sum(months.values()), 13)
        curve[0]['equity'] = 10001
        with self.assertRaisesRegex(ValueError, 'warmup'):
            account.monthly_contributions(curve, self.plan['sessions'])

    def test_block_bootstrap_matches_independent_loop_and_truncates_last_block(self):
        values = list(range(-23, 23)); rng = np.random.default_rng(20260922)
        starts = rng.integers(0, 46, size=(5000, 8)); means = []
        for row in starts:
            draw = [values[(int(start)+offset) % 46] for start in row for offset in range(6)][:46]
            means.append(sum(draw)/46)
        expected = np.quantile(means, [.025, .975], method='linear')
        result = account.block_interval(values)
        self.assertEqual(result['lower_95_CNY'], expected[0])
        self.assertEqual(result['upper_95_CNY'], expected[1])
        self.assertEqual(result['seed'], 20260922)
        self.assertEqual(account.block_interval([2]*46)['lower_95_CNY'], 2)
        self.assertEqual(account.block_interval([0]*46)['lower_95_CNY'], 0)
        for values in ([1]*45, [1]*47, [float('nan')]*46):
            with self.assertRaises(ValueError):
                account.block_interval(values)


if __name__ == '__main__':
    unittest.main()
