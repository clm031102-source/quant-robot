"""Synthetic accounting comparisons; no market or broker calls."""
import copy
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_cn_etf_research_price_basis_drill import ASSET_ID, DATES, _actions, _bars
from quant_robot.paper.fixed_hold import FixedHoldConfig, FixedHoldEntry, run_fixed_hold_benchmark
from quant_robot.paper.account_comparison import compare_cash_accounts


class FixedHoldBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.actions = Path(self.temp.name) / 'actions.json'
        self.actions.write_text(json.dumps(_actions('cash_dividend')), encoding='utf-8')
        self.config = FixedHoldConfig(entries=(FixedHoldEntry(ASSET_ID, 100, 10),),
            initial_cash=10000, commission_bps=5, minimum_commission=5,
            slippage_bps=0, market_impact_bps=0, max_participation_rate=.01,
            corporate_actions_path=self.actions)

    def run_case(self, prices=None, **changes):
        bars = _bars(prices or [10, 10, 9, 9.5, 9.5, 9.5])
        return run_fixed_hold_benchmark(bars, replace(self.config, **changes), sessions=DATES)

    def test_entry_is_paid_from_total_capital_without_factor_generation(self):
        with patch('quant_robot.paper.simulator._compute_factors', side_effect=AssertionError('no factors')):
            result = self.run_case()
        self.assertEqual(result['equity_curve'][0]['equity'], 10000)
        self.assertEqual(result['equity_curve'][1]['cash'], 8995)
        self.assertEqual(result['metrics']['ending_equity'], 10045)
        self.assertAlmostEqual(result['metrics']['total_return'], .0045)
        self.assertEqual(len(result['fills']), 1)
        self.assertEqual(result['fills'][0]['quantity'], 100)
        self.assertEqual(result['fills'][0]['execution_date'], str(DATES[1]))
        self.assertFalse(result['executable'])
        self.assertFalse(result['accounting']['source_audit_verified'])

    def test_dividend_is_receivable_before_payment_and_not_reinvested(self):
        result = self.run_case()
        rows = result['equity_curve']
        self.assertEqual(rows[2]['cash'], 8995)
        self.assertEqual(rows[2]['dividend_receivable'], 100)
        self.assertEqual(rows[4]['cash_before_close'], 8995)
        self.assertEqual(rows[4]['cash'], 9095)
        self.assertEqual(rows[3]['equity'], rows[4]['equity'])
        self.assertEqual(result['positions'], [{'asset_id': ASSET_ID, 'quantity': 100.0}])

    def test_shared_cash_and_minimum_fees_can_reduce_second_order_by_one_lot(self):
        other = 'CN_ETF_XSHE_159915'
        first = _bars([5] * 6).assign(volume=100000, amount=500000)
        second = first.assign(asset_id=other, symbol='159915.SZ', exchange='XSHE', calendar='XSHE')
        bars = pd.concat([first, second], ignore_index=True)
        dataset = _actions('cash_dividend')
        dataset.update(asset_ids=[ASSET_ID, other], events=[])
        self.actions.write_text(json.dumps(dataset), encoding='utf-8')
        config = replace(self.config, initial_cash=2000,
                         entries=(FixedHoldEntry(ASSET_ID, 200, 5), FixedHoldEntry(other, 200, 5)))
        result = run_fixed_hold_benchmark(bars, config, sessions=DATES)
        self.assertEqual([row['quantity'] for row in result['fills']], [200, 100])
        self.assertEqual(result['metrics']['ending_cash'], 490)
        self.assertEqual(result['metrics']['ending_equity'], 1990)
        self.assertTrue(any(row['reason'] == 'cash_limited_partial_entry' for row in result['execution_events']))

    def test_price_ceiling_failure_is_not_retried_on_a_later_cheaper_day(self):
        result = self.run_case([10, 10.5, 9, 9, 9, 9])
        self.assertEqual(result['fills'], [])
        self.assertEqual(result['metrics']['ending_equity'], 10000)
        self.assertIn('entry_price_above_limit', [x['reason'] for x in result['execution_events']])

    def test_capacity_rejection_has_distinct_reason(self):
        result = self.run_case([5] * 6, entries=(FixedHoldEntry(ASSET_ID, 200, 5),))
        self.assertEqual(result['fills'], [])
        self.assertIn('capacity_limit_exceeded', [x['reason'] for x in result['execution_events']])
        self.assertFalse(result['risk']['entry_fully_filled'])

    def test_suspended_entry_remains_cash_without_later_retry(self):
        bars = _bars([10] * 6)
        bars['suspended'] = [False, True, False, False, False, False]
        result = run_fixed_hold_benchmark(bars, self.config, sessions=DATES)
        self.assertEqual(result['fills'], [])
        self.assertIn('suspended', [x['reason'] for x in result['execution_events']])

    def test_share_conversion_uses_existing_ledger(self):
        self.actions.write_text(json.dumps(_actions('share_split')), encoding='utf-8')
        result = self.run_case([10, 10, 5, 5, 5, 5])
        self.assertEqual(result['positions'][0]['quantity'], 200)
        self.assertEqual(result['metrics']['ending_equity'], 9995)

    def test_entry_position_cap_and_daily_cost_stop_are_enforced(self):
        with self.assertRaisesRegex(ValueError, 'position limit'):
            self.run_case(entries=(FixedHoldEntry(ASSET_ID, 200, 10),))
        result = self.run_case(minimum_commission=60)
        self.assertEqual(result['fills'], [])
        self.assertIn('entry_daily_loss_limit', [x['reason'] for x in result['execution_events']])

    def test_later_risk_breach_is_reported_without_invented_exit_fill(self):
        result = self.run_case([10, 10, 9, 8, 8, 8])
        self.assertEqual(len(result['fills']), 1)
        self.assertFalse(result['risk']['compatible_with_declared_limits'])
        self.assertIn('daily_loss_limit', [x['reason'] for x in result['risk']['breaches']])
        self.assertEqual(result['metrics']['ending_equity'], 9895)

    def test_explicit_calendar_missing_duplicate_and_intraday_dates_rejected(self):
        bars = _bars([10] * 6)
        for modified, sessions in [(bars.iloc[:-1], DATES),
                (pd.concat([bars, bars.iloc[[0]]], ignore_index=True), DATES),
                (bars, DATES[::-1]), (bars, [pd.Timestamp(DATES[0]) + pd.Timedelta(hours=1), *DATES[1:]])]:
            with self.subTest(rows=len(modified), sessions=sessions), self.assertRaises(ValueError):
                run_fixed_hold_benchmark(modified, self.config, sessions=sessions)

    def test_invalid_config_numbers_and_lots_rejected(self):
        cases = [{'initial_cash': float('nan')}, {'initial_cash': '10000'}, {'commission_bps': True},
                 {'minimum_commission': -1}, {'slippage_bps': 10000},
                 {'max_participation_rate': 0}, {'max_drawdown': 1},
                 {'entries': ()}, {'entries': (FixedHoldEntry(ASSET_ID, 150, 10),)},
                 {'entries': (FixedHoldEntry(ASSET_ID, True, 10),)},
                 {'entries': (FixedHoldEntry(ASSET_ID, 100, float('inf')),)},
                 {'entries': self.config.entries * 2}, {'corporate_actions_path': None}]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.run_case(**kwargs)

    def test_gross_dividend_and_wrong_currency_rejected(self):
        bars = _bars([10] * 6)
        with self.assertRaisesRegex(ValueError, 'CNY'):
            run_fixed_hold_benchmark(bars.assign(currency='USD'), self.config, sessions=DATES)
        dataset = _actions('cash_dividend')
        dataset['schema_version'] = 3
        event = dataset['events'][0]
        event['cash_per_share'] = event.pop('net_cash_per_share')
        event['cash_amount_basis'] = 'gross'
        self.actions.write_text(json.dumps(dataset), encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'net cash'):
            self.run_case()

    def test_adj_close_is_not_used_for_fills_and_actual_inputs_are_fingerprinted(self):
        bars = _bars([10, 10, 9, 9.5, 9.5, 9.5])
        original = run_fixed_hold_benchmark(bars, self.config, sessions=DATES)
        changed = run_fixed_hold_benchmark(bars.assign(adj_close=100), self.config, sessions=DATES)
        self.assertEqual(original['metrics'], changed['metrics'])
        self.assertNotEqual(original['input_provenance']['bars']['content_sha256'],
                            changed['input_provenance']['bars']['content_sha256'])

    def test_comparison_checks_shared_calendar_capital_fees_and_not_theoretical_curves(self):
        account = self.run_case()
        comparison = compare_cash_accounts(account, account)
        self.assertEqual(comparison['relative_return'], 0)
        self.assertFalse(comparison['risk_adjusted_alpha_verified'])
        mutations = [lambda r: r['equity_curve'].pop(),
                     lambda r: r['equity_curve'][0].update(equity=11000),
                     lambda r: r['request']['execution_economics'].update(minimum_commission=0),
                     lambda r: r.update(equity_curve=[{'date': str(DATES[0]), 'benchmark_equity': 1}])]
        for mutate in mutations:
            other = copy.deepcopy(account)
            mutate(other)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                compare_cash_accounts(account, other)

    def test_comparison_rejects_invalid_equity_and_inconsistent_period_returns(self):
        account = self.run_case()
        for change in [{'equity': float('nan')}, {'equity': 0}, {'period_return': .5},
                       {'date': str(DATES[0])}]:
            other = copy.deepcopy(account)
            other['equity_curve'][2].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                compare_cash_accounts(account, other)

    def test_comparison_binds_outer_economics_opening_cash_and_declared_sessions(self):
        account = self.run_case()
        mutations = [lambda r: r['request'].update(minimum_commission=0),
                     lambda r: r['equity_curve'][0].update(cash=9000),
                     lambda r: r['request'].update(cash_annual_return=.02),
                     lambda r: r['request']['sessions'].pop(),
                     lambda r: r['equity_curve'][2].update(cash=12000)]
        for mutate in mutations:
            other = copy.deepcopy(account)
            mutate(other)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                compare_cash_accounts(account, other)


if __name__ == '__main__':
    unittest.main()
