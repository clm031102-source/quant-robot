import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.paper.corporate_actions import CorporateActionLedger
from quant_robot.research.labels import make_forward_returns
from quant_robot.research.price_basis import build_cash_action_research_prices


ASSET = 'CN_ETF_XSHG_510300'
SESSIONS = [date.fromisoformat(value) for value in
            ['2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05', '2024-01-08', '2024-01-09']]


def dividend(**changes):
    return {'event_id': 'fixture-dividend', 'asset_id': ASSET, 'kind': 'cash_dividend',
            'announced_date': '2024-01-02', 'record_date': '2024-01-03',
            'ex_date': '2024-01-04', 'pay_date': '2024-01-08', 'net_cash_per_share': 1.0, **changes}


def split(**changes):
    return {'event_id': 'fixture-split', 'asset_id': ASSET, 'kind': 'share_split',
            'announced_date': '2024-01-02', 'ex_date': '2024-01-04',
            'tradable_date': '2024-01-04', 'share_ratio': 2.0, **changes}


def fixture_bars(prices):
    bars = load_demo_market_bars()
    bars = bars[bars.asset_id.eq(ASSET)].head(len(prices)).copy().reset_index(drop=True)
    bars['date'] = SESSIONS[:len(prices)]
    bars['timestamp'] = pd.to_datetime(bars['date']).dt.tz_localize('Asia/Shanghai').dt.tz_convert('UTC')
    for name in ['open', 'high', 'low', 'close', 'adj_close']:
        bars[name] = [float(value) for value in prices]
    bars['adjusted'] = False
    bars['ingested_at'] = pd.Timestamp('2024-02-01', tz='UTC')
    return bars


def write_actions(root, events, *, version=1, **changes):
    path = Path(root) / 'actions.json'
    path.write_text(json.dumps({'schema_version': version, 'source_ref': 'synthetic fixture',
        'coverage_start': str(SESSIONS[0]), 'coverage_end': str(SESSIONS[-1]),
        'asset_ids': [ASSET], 'events': events, **changes}), encoding='utf-8')
    return path


class ResearchPriceBasisTests(unittest.TestCase):
    def build(self, prices, events, **kwargs):
        bars = fixture_bars(prices)
        with tempfile.TemporaryDirectory() as tmp:
            path = write_actions(tmp, events, **kwargs)
            return build_cash_action_research_prices(bars, path, sessions=SESSIONS[:len(prices)])

    def test_cash_dividend_removes_mechanical_factor_and_label_loss(self):
        raw = fixture_bars([10, 10, 9, 9])
        result = self.build([10, 10, 9, 9], [dividend()])
        self.assertEqual(result.bars['adj_close'].tolist(), [10.0] * 4)
        self.assertEqual(result.bars['close'].tolist(), raw['close'].tolist())
        raw_factor = compute_basic_factors(raw, windows=(1,), factor_names=('momentum_1',))
        fixed_factor = compute_basic_factors(result.bars, windows=(1,), factor_names=('momentum_1',))
        self.assertAlmostEqual(raw_factor.iloc[2]['factor_value'], -0.1)
        self.assertAlmostEqual(fixed_factor.iloc[2]['factor_value'], 0.0)
        self.assertAlmostEqual(make_forward_returns(raw, horizons=(1,), execution_lag=1).iloc[0]['forward_return'], -0.1)
        self.assertAlmostEqual(make_forward_returns(result.bars, horizons=(1,), execution_lag=1).iloc[0]['forward_return'], 0.0)

    def test_ex_close_reinvestment_differs_from_ex_reference_adjustment(self):
        result = self.build([10, 10, 10, 20], [dividend()])
        self.assertEqual(result.bars['adj_close'].tolist(), [10.0, 10.0, 11.0, 22.0])
        # A different convention, close / (previous close - dividend), is not this model.
        self.assertNotAlmostEqual(result.bars.iloc[2]['adj_close'], 10 * 10 / 9)

    def test_theoretical_reinvestment_is_not_spendable_account_cash(self):
        bars = fixture_bars([10, 10, 9, 18, 18, 18])
        with tempfile.TemporaryDirectory() as tmp:
            path = write_actions(tmp, [dividend()])
            result = build_cash_action_research_prices(bars, path, sessions=SESSIONS)
            positions = {ASSET: 100.0}
            ledger = CorporateActionLedger(path, {ASSET}, SESSIONS, positions)
            cash = 0.0
            observations = []
            for session, price in zip(SESSIONS, bars['close']):
                received, _ = ledger.before_session(session, positions, [])
                cash += received
                before_close_cash = cash
                cash += ledger.after_session(session, positions)
                observations.append((cash, ledger.receivable, 100 * price + cash + ledger.receivable, before_close_cash))
        self.assertEqual(observations[2][:3], (0.0, 100.0, 1000.0))
        self.assertEqual(observations[3][:3], (0.0, 100.0, 1900.0))
        self.assertEqual(observations[4], (100.0, 0.0, 1900.0, 0.0))
        self.assertEqual(result.bars.iloc[3]['adj_close'], 20.0)
        self.assertFalse(result.evidence['source_audit_verified'])
        self.assertFalse(result.evidence['account_cash_or_tradability_verified'])

    def test_split_preserves_analytical_units_without_holder_rounding_profit(self):
        result = self.build([10, 10, 5, 5], [split()])
        self.assertEqual(result.bars['adj_close'].tolist(), [10.0] * 4)
        rounded = self.build([10, 10, 20, 20],
            [split(share_ratio=0.5, share_rounding='ceil_per_holder')], version=2)
        self.assertEqual(rounded.bars['adj_close'].tolist(), [10.0] * 4)
        self.assertEqual(rounded.evidence['holder_rounding'], 'not_applied_to_theoretical_index')

    def test_future_events_and_prices_do_not_rewrite_earlier_levels(self):
        prefix = self.build([10, 10, 9, 9], [dividend()])
        future = dividend(event_id='later', announced_date='2024-01-05', record_date='2024-01-08',
                          ex_date='2024-01-09', pay_date='2024-01-10', net_cash_per_share=2.0)
        extended = self.build([10, 10, 9, 9, 9, 7], [dividend(), future])
        self.assertEqual(prefix.bars['adj_close'].tolist(), extended.bars.head(4)['adj_close'].tolist())
        self.assertEqual(prefix.bars['adj_close'].tolist(), self.build([10, 10, 9, 9], [dividend(), future]).bars['adj_close'].tolist())

    def test_declared_empty_history_and_input_frame_are_preserved(self):
        bars = fixture_bars([10, 11, 12])
        original = bars.copy(deep=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = write_actions(tmp, [])
            result = build_cash_action_research_prices(bars, path, sessions=SESSIONS[:3])
        pd.testing.assert_frame_equal(bars, original)
        self.assertEqual(result.bars['adj_close'].tolist(), [10.0, 11.0, 12.0])
        self.assertFalse(result.evidence['source_audit_verified'])

    def test_invalid_or_incomplete_price_calendars_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_actions(tmp, [dividend()])
            bars = fixture_bars([10, 10, 9, 9])
            cases = [bars.drop(index=2), pd.concat([bars, bars.iloc[[1]]]), bars.drop(columns='close')]
            for value in [0.0, -1.0, float('nan'), float('inf')]:
                changed = bars.copy()
                changed.loc[2, 'close'] = value
                cases.append(changed)
            for changed in cases:
                with self.subTest(rows=len(changed)), self.assertRaises(ValueError):
                    build_cash_action_research_prices(changed, path, sessions=SESSIONS[:4])

    def test_calendar_duplicate_unsorted_and_date_coverage_are_rejected(self):
        bars = fixture_bars([10, 10, 9, 9])
        with tempfile.TemporaryDirectory() as tmp:
            path = write_actions(tmp, [dividend()])
            for sessions in [[], SESSIONS[:3], list(reversed(SESSIONS[:4])), SESSIONS[:4] + [SESSIONS[3]]]:
                with self.subTest(sessions=sessions), self.assertRaises(ValueError):
                    build_cash_action_research_prices(bars, path, sessions=sessions)

    def test_ambiguous_or_unknown_events_and_incomplete_coverage_are_rejected(self):
        cases = [([dividend(), dividend(event_id='duplicate-economic')], {}),
                 ([dividend(), split()], {}),
                 ([dividend(kind='rights_issue')], {}),
                 ([dividend(announced_date='2024-01-05')], {}),
                 ([dividend(record_date='2024-01-02')], {}),
                 ([dividend()], {'coverage_start': '2024-01-03'}),
                 ([dividend()], {'asset_ids': []})]
        for events, changes in cases:
            with self.subTest(events=events, changes=changes), self.assertRaises(ValueError):
                self.build([10, 10, 9, 9], events, **changes)

    def test_evidence_binds_actual_inputs_and_does_not_certify_sources(self):
        first = self.build([10, 10, 9, 9], [dividend()])
        second = self.build([10, 10, 9, 9], [dividend(net_cash_per_share=0.5)])
        self.assertEqual(first.evidence['input_bars_sha256'], second.evidence['input_bars_sha256'])
        self.assertNotEqual(first.evidence['action_file_sha256'], second.evidence['action_file_sha256'])
        self.assertNotEqual(first.evidence['output_bars_sha256'], second.evidence['output_bars_sha256'])
        self.assertFalse(first.evidence['research_admission_verified'])

    def test_multiple_assets_are_independent_after_unsorted_input(self):
        first = fixture_bars([10, 10, 9, 9])
        other = fixture_bars([20, 20, 20, 20])
        other['asset_id'] = 'CN_ETF_XSHE_159915'
        other['symbol'] = '159915.SZ'
        bars = pd.concat([other, first]).iloc[::-1].reset_index(drop=True)
        with tempfile.TemporaryDirectory() as tmp:
            path = write_actions(tmp, [dividend()], asset_ids=[ASSET, 'CN_ETF_XSHE_159915'])
            result = build_cash_action_research_prices(bars, path, sessions=SESSIONS[:4])
        self.assertEqual(result.bars[result.bars.asset_id.eq(ASSET)]['adj_close'].tolist(), [10.0] * 4)
        self.assertEqual(result.bars[result.bars.asset_id.ne(ASSET)]['adj_close'].tolist(), [20.0] * 4)

    def test_index_starting_on_ex_date_does_not_invent_pre_window_income(self):
        bars = fixture_bars([10, 10, 9, 9]).iloc[2:].copy()
        with tempfile.TemporaryDirectory() as tmp:
            path = write_actions(tmp, [dividend()])
            result = build_cash_action_research_prices(bars, path, sessions=SESSIONS[2:4])
        self.assertEqual(result.bars['adj_close'].tolist(), [9.0, 9.0])
        self.assertEqual(result.evidence['applied_events'], 0)

    def test_ex_date_absent_from_calendar_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'ex-date'):
            self.build([10] * 6, [dividend(record_date='2024-01-05', ex_date='2024-01-06')])

    def test_wrong_currency_and_unsupported_market_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_actions(tmp, [])
            for column, value in [('currency', 'USD'), ('market', 'CN')]:
                changed = fixture_bars([10, 10, 10])
                changed[column] = value
                with self.subTest(column=column), self.assertRaisesRegex(ValueError, 'CN_ETF'):
                    build_cash_action_research_prices(changed, path, sessions=SESSIONS[:3])

    def test_nonrepresentable_input_and_daily_ratio_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = write_actions(tmp, [])
            for prices in [['1e-999', '10'], ['10', '1e999'], ['1e-300', '1e300']]:
                bars = fixture_bars([10, 10])
                bars['close'] = prices
                with self.subTest(prices=prices), self.assertRaises(ValueError):
                    build_cash_action_research_prices(bars, path, sessions=SESSIONS[:2])


if __name__ == '__main__':
    unittest.main()
