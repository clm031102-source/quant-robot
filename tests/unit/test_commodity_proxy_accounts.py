"""Invented prices only: fixed batch, comparison and statistical accounting."""
from copy import deepcopy
from datetime import date, timedelta
import math
import unittest

from quant_robot.research import commodity_proxy_accounts as study


def synthetic_inputs():
    sessions = []
    day, end = date(2019, 12, 30), date(2024, 6, 28)
    while day <= end:
        if day.weekday() < 5:
            sessions.append(day.isoformat())
        day += timedelta(days=1)
    lifecycle = [dict(ts_code=code, fut_code='M', exchange='DCE', list_date='20180101',
        delist_date=expiry, last_ddate=expiry, per_unit=10, trade_unit='吨', quote_unit='人民币元/吨')
        for code, expiry in [('M2701.DCE', '20270115'), ('M2705.DCE', '20270515')]]
    settlements = [dict(ts_code=row['ts_code'], trade_date=day.replace('-', ''), settle=value)
        for day in sessions for row, value in zip(lifecycle, (3100, 3000), strict=True)]
    dates = [day for day in sessions if any(a <= day <= b for a, b in study.WINDOWS.values())]
    bars = [dict(asset_id=study.ASSET, date=day, open=5, high=5, low=5, close=5,
                 volume=1000000, suspended=None, limit_up=None, limit_down=None) for day in dates]
    return dict(sessions=sessions, lifecycle=lifecycle, settlements=settlements, bars=bars, actions=[])


class CommodityAccountsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calls = []
        cls.saved = []
        cls.result = study.calculate(**synthetic_inputs(),
            guard=lambda phase, identity: cls.calls.append((phase, identity)),
            account_sink=lambda identity, account: cls.saved.append(identity))

    def test_all36_accounts_have_identical_rules_and_matched_controls(self):
        result = self.result
        self.assertEqual((result['account_count'], result['cash_benchmark_count']), (36, 2))
        self.assertEqual(len(self.calls), 72)
        self.assertEqual(len(self.saved), 36)
        for index, identity in enumerate(self.saved):
            self.assertEqual(self.calls[2*index:2*index+2], [('before', identity), ('after', identity)])
        for window in study.WINDOWS:
            for minimum, slip in study.FEES:
                suffix = f'min{minimum}_slip{slip}'
                curve = result['accounts'][f'{window}/curve/{suffix}']
                holding = result['accounts'][f'{window}/holding/{suffix}']
                self.assertEqual(curve['equity_curve'], holding['equity_curve'])
                self.assertEqual(curve['metrics']['initial_cash'], 10000)
                self.assertTrue(all(row['equity'] == 10000 for row in curve['equity_curve'][:20]))
                self.assertTrue(curve['risk']['terminal_settled'])
                self.assertEqual(curve['positions'], {})
                self.assertGreater(curve['unknown_execution_flag_rows'], 0)
                self.assertFalse(curve['executable'])

    def test_no_cost_cherry_pick_or_synthetic_qualification(self):
        assessment = self.result['assessment']
        self.assertFalse(assessment['financial_conditions_supported'])
        self.assertFalse(assessment['checks']['later_primary_exceeds_matched_holding'])
        self.assertFalse(assessment['qualification_granted'])
        self.assertEqual(self.result['bootstrap']['fifth_percentile_mean_daily_log_excess'], 0)
        self.assertEqual(self.result['real_forward_days_added'], 0)
        for summary in self.result['account_summaries'].values():
            self.assertEqual(summary['roundtrips']['count'], summary['actual_buy_fills'])
            self.assertFalse(summary['roundtrips']['minimum_30_observation_met'])

    def test_control_drawdown_and_unsettled_terminal_are_named_comparison_failures(self):
        accounts = deepcopy(self.result['accounts'])
        identity = 'later/holding/min10_slip30'
        accounts[identity]['metrics']['maximum_drawdown'] = .40001
        accounts[identity]['risk']['terminal_settled'] = False
        result = study.support_assessment(accounts, self.result['bootstrap'])
        self.assertEqual(set(result['account_comparability_failures']), {identity})
        self.assertEqual(len(result['account_comparability_failures'][identity]), 2)
        self.assertFalse(result['financial_conditions_supported'])
        accounts.pop(identity)
        with self.assertRaisesRegex(ValueError, 'All36'):
            study.support_assessment(accounts, self.result['bootstrap'])

    def test_guard_failure_stops_without_producing_or_restarting_account(self):
        seen = []
        def changed(phase, identity):
            seen.append((phase, identity))
            raise ValueError('frozen input changed')
        with self.assertRaisesRegex(ValueError, 'frozen input changed'):
            study.calculate(**synthetic_inputs(), guard=changed,
                account_sink=lambda *args: self.fail('No result before successful guard'))
        self.assertEqual(len(seen), 1)

    def test_unrequested_asset_and_outside_window_bar_rejected(self):
        for field, value in [('asset_id', 'OTHER'), ('date', '2026-01-01')]:
            inputs = synthetic_inputs()
            inputs['bars'][0][field] = value
            with self.assertRaises(ValueError):
                study.calculate(**inputs)

    def test_roundtrip_requires_full_actual_quantity_and_correct_attempt(self):
        fills = [dict(cycle_id='a', side='buy', quantity=300, date='2020-02-01'),
                 dict(cycle_id='a', side='sell', quantity=100, date='2020-02-02')]
        self.assertEqual(study.completed_roundtrips(fills)['count'], 0)
        fills.append(dict(cycle_id='a', side='sell', quantity=200, date='2020-02-03'))
        self.assertEqual(study.completed_roundtrips(fills)['count'], 1)
        fills.append(dict(cycle_id='a', side='sell', quantity=100, date='2020-02-04'))
        with self.assertRaises(ValueError):
            study.completed_roundtrips(fills)

    def test_year_slices_use_prior_real_NAV_without_reset(self):
        rows = [dict(date='2020-12-30', equity=11000), dict(date='2020-12-31', equity=9000),
                dict(date='2021-01-04', equity=9500), dict(date='2021-01-05', equity=9900)]
        annual = study.annual_decomposition(rows)
        self.assertEqual(annual['2021']['starting_NAV'], 9000)
        self.assertEqual(sum(row['pnl_cny'] for row in annual.values()), -100)

    def test_bootstrap_constant_paired_growth_and_exact_calendar(self):
        strategy = [dict(date=str(i), equity=10000*math.exp(.001*(i+1))) for i in range(41)]
        control = [dict(date=str(i), equity=10000) for i in range(41)]
        result = study.paired_bootstrap(strategy, control)
        self.assertAlmostEqual(result['mean_daily_log_excess'], .001)
        self.assertAlmostEqual(result['fifth_percentile_mean_daily_log_excess'], .001)
        self.assertEqual(result, study.paired_bootstrap(strategy, control))
        control[0]['date'] = 'changed'
        with self.assertRaises(ValueError):
            study.paired_bootstrap(strategy, control)


if __name__ == '__main__':
    unittest.main()
