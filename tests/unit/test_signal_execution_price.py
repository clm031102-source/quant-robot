import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.portfolio.rebalance import build_rebalance_plan
from quant_robot.signals.pipeline import (
    SignalPipelineConfig, generate_signal_snapshot,
    generate_signal_snapshot_from_factors, write_signal_snapshot,
)


class SignalExecutionPriceTests(unittest.TestCase):
    def setUp(self):
        self.config = SignalPipelineConfig(market='CN_ETF', factor_name='synthetic',
            top_n=1, as_of_date='2024-01-08')
        self.bars = pd.DataFrame([
            {'date': date, 'asset_id': 'SYNTHETIC_ETF', 'market': 'CN_ETF',
             'close': close, 'adj_close': 2.0, 'source': 'fixture'}
            for date, close in [('2024-01-05', 3.0), ('2024-01-08', 4.0), ('2024-01-09', 9.0)]
        ])
        self.factors = pd.DataFrame([{'date': '2024-01-08', 'asset_id': 'SYNTHETIC_ETF',
            'market': 'CN_ETF', 'factor_name': 'synthetic', 'factor_value': 1.0}])

    def snapshot(self, bars=None):
        return generate_signal_snapshot_from_factors(
            self.bars if bars is None else bars, self.factors, self.config, validate=False)

    def test_raw_quote_survives_serialization_and_drives_quantity_estimate(self):
        result = self.snapshot()
        with tempfile.TemporaryDirectory() as tmp:
            write_signal_snapshot(result, Path(tmp))
            targets = pd.read_csv(Path(tmp) / 'targets.csv')
        plan = build_rebalance_plan(targets, pd.DataFrame(columns=['asset_id', 'quantity']),
            targets[['asset_id', 'latest_price']], portfolio_value=1000.0)
        self.assertEqual(targets.iloc[0]['latest_price'], 4.0)
        self.assertEqual(plan.iloc[0]['estimated_quantity_delta'], 250.0)
        self.assertFalse(plan.iloc[0]['executable'])
        self.assertFalse(result['input_provenance']['source_quality_verified'])

    def test_research_adjustment_changes_do_not_change_execution_reference(self):
        changed = self.bars.copy()
        changed['adj_close'] = 0.5
        self.assertEqual(self.snapshot()['targets'], self.snapshot(changed)['targets'])

    def test_invalid_latest_raw_quote_cannot_use_adjusted_or_older_quote(self):
        for value in [0.0, -1.0, float('nan'), float('inf'), float('-inf'), None, pd.NA, 'unavailable']:
            with self.subTest(value=value):
                changed = self.bars.copy()
                changed['close'] = changed['close'].astype(object)
                changed.loc[changed['date'].eq('2024-01-08'), 'close'] = value
                with self.assertRaisesRegex(ValueError, 'raw close'):
                    self.snapshot(changed)

    def test_missing_raw_close_has_no_adjusted_fallback(self):
        with self.assertRaisesRegex(ValueError, 'raw close'):
            self.snapshot(self.bars.drop(columns='close'))

    def test_technical_entrypoint_keeps_factor_basis_separate_from_quote(self):
        bars = load_demo_market_bars()
        config = SignalPipelineConfig(market='CN_ETF', factor_name='momentum_2',
            factor_windows=(2,), top_n=1, as_of_date='2024-01-08')
        original = generate_signal_snapshot(bars, config)
        changed = bars.copy()
        for column in ['open', 'high', 'low', 'close']:
            changed[column] *= 2.0
        result = generate_signal_snapshot(changed, config)
        self.assertEqual(result['targets'][0]['factor_value'], original['targets'][0]['factor_value'])
        self.assertEqual(result['targets'][0]['latest_price'], original['targets'][0]['latest_price'] * 2.0)


if __name__ == '__main__':
    unittest.main()
