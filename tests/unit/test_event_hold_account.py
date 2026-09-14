"""Scheduled exits, risk delays and cash rights on synthetic prices only."""
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from scripts.run_cn_etf_research_price_basis_drill import ASSET_ID, _bars
from quant_robot.paper.event_hold import EventHoldConfig, ScheduledEntry, run_event_hold_account


class EventHoldAccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'actions.json'
        self.dates = [date(2024, 1, 2) + timedelta(days=i) for i in range(7)]
        self.dataset = {'schema_version': 3, 'source_ref': 'synthetic fixture',
            'coverage_start': str(self.dates[0]), 'coverage_end': str(self.dates[-1]),
            'asset_ids': [ASSET_ID], 'events': []}
        self.save()
        self.config = EventHoldConfig(asset_id=ASSET_ID, corporate_actions_path=self.path,
            hold_transitions=2, slippage_bps=0, market_impact_bps=0)

    def save(self):
        self.path.write_text(json.dumps(self.dataset), encoding='utf-8')

    def bars(self, prices):
        template = _bars([5] * 6).iloc[[0]]
        frame = pd.concat([template] * len(prices), ignore_index=True)
        frame['date'] = self.dates
        frame['timestamp'] = pd.to_datetime(self.dates)
        for field in ('open', 'high', 'low', 'close', 'adj_close'):
            frame[field] = prices
        return frame.assign(volume=1_000_000, amount=5_000_000)

    def entry(self, index=1, name='a'):
        return ScheduledEntry(name, self.dates[index - 1], self.dates[index])

    def run_case(self, prices=None, entries=None, **kwargs):
        return run_event_hold_account(self.bars(prices or [4] * 7),
            replace(self.config, **kwargs), entries=entries or [self.entry()], sessions=self.dates)

    def test_fixed_horizon_counts_close_transitions_and_both_minimum_fees(self):
        result = self.run_case()
        self.assertEqual([x['execution_date'] for x in result['fills']],
                         [str(self.dates[1]), str(self.dates[3])])
        self.assertEqual([x['quantity'] for x in result['fills']], [200, 200])
        self.assertEqual(result['metrics']['ending_cash'], 9990)
        self.assertEqual(result['metrics']['fees_paid'], 10)
        self.assertEqual(result['metrics']['completed_round_trips'], 1)
        self.assertFalse(result['executable'])
        self.assertFalse(result['research_admission_verified'])

    def test_entry_uses_prior_close_whole_lots_and_never_increases_after_price_drop(self):
        result = self.run_case([4, 3, 3, 3, 3, 3, 3])
        self.assertEqual(result['fills'][0]['quantity'], 200)
        self.assertEqual(result['fills'][0]['notional'], 600)
        blocked = self.run_case([4, 6, 4, 4, 4, 4, 4])
        self.assertEqual(blocked['fills'], [])
        self.assertIn('entry_position_limit', [x['reason'] for x in blocked['execution_events']])

    def test_overlap_and_same_day_exit_do_not_create_extra_buys(self):
        result = self.run_case(entries=[self.entry(1), self.entry(2, 'b'), self.entry(3, 'c'), self.entry(4, 'd')])
        self.assertEqual([x['execution_date'] for x in result['fills'] if x['side'] == 'buy'],
                         [str(self.dates[1]), str(self.dates[4])])
        self.assertEqual(result['metrics']['completed_round_trips'], 2)

    def test_risk_breach_exits_next_session_and_stops_later_entries(self):
        result = self.run_case([4, 4, 3.5, 3.4, 3.4, 3.4, 3.4],
            entries=[self.entry(), self.entry(3, 'b')], hold_transitions=3)
        self.assertEqual(len(result['fills']), 2)
        self.assertEqual(result['fills'][-1]['execution_date'], str(self.dates[3]))
        self.assertEqual(result['fills'][-1]['exit_reason'], 'risk_exit')
        self.assertTrue(result['risk']['new_entries_halted'])
        self.assertEqual(result['risk']['breaches'][0]['date'], str(self.dates[2]))

    def test_blocked_exit_retries_but_blocked_entry_does_not(self):
        bars = self.bars([4] * 7)
        bars['suspended'] = [False, False, False, True, False, False, False]
        result = run_event_hold_account(bars, self.config, entries=[self.entry()], sessions=self.dates)
        self.assertEqual(result['fills'][-1]['execution_date'], str(self.dates[4]))
        self.assertEqual(result['fills'][-1]['exit_reason'], 'scheduled_exit')
        bars['suspended'] = [False, True, False, False, False, False, False]
        result = run_event_hold_account(bars, self.config, entries=[self.entry()], sessions=self.dates)
        self.assertEqual(result['fills'], [])

    def test_terminal_blocked_exit_is_marked_unresolved_without_invented_fill(self):
        bars = self.bars([4] * 7)
        bars['suspended'] = [False, False, False, True, True, True, True]
        result = run_event_hold_account(bars, self.config, entries=[self.entry()], sessions=self.dates)
        self.assertEqual(len(result['fills']), 1)
        self.assertFalse(result['risk']['terminal_settled'])
        self.assertEqual(result['metrics']['completed_round_trips'], 0)
        self.assertEqual(result['positions'][0]['quantity'], 200)

    def test_cash_dividend_survives_sale_and_is_not_double_counted_at_payment(self):
        self.dataset['events'] = [{'event_id': 'div', 'asset_id': ASSET_ID, 'kind': 'cash_dividend',
            'announced_date': str(self.dates[0]), 'record_date': str(self.dates[1]),
            'ex_date': str(self.dates[2]), 'pay_date': str(self.dates[5]),
            'cash_per_share': .5, 'cash_amount_basis': 'net'}]
        self.save()
        result = self.run_case([4, 4, 3.5, 3.5, 3.5, 3.5, 3.5])
        self.assertEqual(result['equity_curve'][3]['dividend_receivable'], 100)
        self.assertEqual(result['equity_curve'][5]['cash_before_close'], 9890)
        self.assertEqual(result['metrics']['ending_cash'], 9990)
        self.assertEqual(result['risk']['breaches'], [])

    def test_gross_requires_explicit_research_assumption_and_preserves_original(self):
        event = {'event_id': 'div', 'asset_id': ASSET_ID, 'kind': 'cash_dividend',
            'announced_date': str(self.dates[0]), 'record_date': str(self.dates[1]),
            'ex_date': str(self.dates[2]), 'pay_date': str(self.dates[5]),
            'cash_per_share': .5, 'cash_amount_basis': 'gross'}
        self.dataset['events'] = [event]
        self.save()
        raw = self.path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'net cash'):
            self.run_case()
        result = self.run_case([4, 4, 3.5, 3.5, 3.5, 3.5, 3.5],
            cash_amount_policy='gross_announcement_assumption')
        self.assertEqual(result['metrics']['ending_cash'], 9990)
        self.assertEqual(result['accounting']['cash_amount_basis'], 'gross_announcement_assumption')
        self.assertFalse(result['accounting']['net_cash_verified'])
        self.assertEqual(self.path.read_bytes(), raw)

    def test_conversion_adjusts_sale_units_and_waits_for_tradability(self):
        self.dataset['events'] = [{'event_id': 'split', 'asset_id': ASSET_ID, 'kind': 'share_split',
            'announced_date': str(self.dates[0]), 'ex_date': str(self.dates[3]),
            'tradable_date': str(self.dates[4]), 'share_ratio': 2, 'share_rounding': 'reject_fractional'}]
        self.save()
        result = self.run_case([4, 4, 4, 2, 2, 2, 2])
        self.assertEqual(result['fills'][-1]['quantity'], 400)
        self.assertEqual(result['fills'][-1]['execution_date'], str(self.dates[4]))
        self.assertEqual(result['metrics']['ending_cash'], 9990)

    def test_capacity_is_checked_for_scheduled_sale(self):
        bars = self.bars([4] * 7)
        bars.loc[3, 'amount'] = 100
        result = run_event_hold_account(bars, self.config, entries=[self.entry()], sessions=self.dates)
        self.assertEqual(result['fills'][-1]['execution_date'], str(self.dates[4]))
        self.assertIn('capacity_limit_exceeded', [x['reason'] for x in result['execution_events']])

    def test_invalid_schedule_calendar_numbers_and_missing_horizon_rejected(self):
        for changes in [{'hold_transitions': True}, {'hold_transitions': 0},
                {'slippage_bps': float('nan')}, {'minimum_commission': -1},
                {'cash_amount_policy': 'guess'}, {'max_participation_rate': 2}]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_case(**changes)
        for entries in [[self.entry(), self.entry()], [self.entry(6)],
                [ScheduledEntry('x', self.dates[1], self.dates[1])]]:
            with self.subTest(entries=entries), self.assertRaises(ValueError):
                self.run_case(entries=entries)
        with self.assertRaises(ValueError):
            run_event_hold_account(self.bars([4] * 7).iloc[:-1], self.config,
                entries=[self.entry()], sessions=self.dates)

    def test_fee_cent_rounding_can_reduce_quantity_without_negative_cash(self):
        result = self.run_case(initial_cash=800.459, commission_bps=5.7, minimum_commission=0)
        self.assertEqual(result['fills'][0]['quantity'], 100)
        self.assertEqual(result['metrics']['fees_paid'], .46)
        self.assertTrue(all(row['cash'] >= 0 for row in result['equity_curve']))
        self.assertAlmostEqual(result['metrics']['ending_cash'], 799.999)

    def test_position_appreciation_triggers_later_exit_and_empty_schedule_is_cash(self):
        result = self.run_case([4, 4, 5.1, 5, 5, 5, 5], hold_transitions=4)
        self.assertEqual(result['risk']['breaches'][0]['reason'], 'position_limit')
        self.assertEqual(result['fills'][-1]['execution_date'], str(self.dates[3]))
        empty = run_event_hold_account(self.bars([4] * 7), self.config, entries=[], sessions=self.dates)
        self.assertEqual(empty['metrics']['ending_cash'], 10000)
        self.assertEqual(empty['fills'], [])

    def test_gross_policy_refuses_net_or_mixed_dividend_bases(self):
        self.dataset['events'] = [{'event_id': 'div', 'asset_id': ASSET_ID, 'kind': 'cash_dividend',
            'announced_date': str(self.dates[0]), 'record_date': str(self.dates[1]),
            'ex_date': str(self.dates[2]), 'pay_date': str(self.dates[5]),
            'cash_per_share': .5, 'cash_amount_basis': 'net'}]
        self.save()
        with self.assertRaisesRegex(ValueError, 'explicit gross'):
            self.run_case(cash_amount_policy='gross_announcement_assumption')


if __name__ == '__main__':
    unittest.main()
