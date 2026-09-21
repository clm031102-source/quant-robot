import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.paper.simulator import write_paper_simulation_artifacts
from scripts.run_paper_simulation import run_simulation


class PaperFixedHoldAttachmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        bars = load_demo_market_bars()
        bars = bars[bars.market.eq('CN_ETF')]
        self.actions = self.root / 'actions.json'
        self.actions.write_text(json.dumps({'schema_version': 1, 'source_ref': 'fixture only',
            'coverage_start': str(bars.date.min()), 'coverage_end': str(bars.date.max()),
            'asset_ids': sorted(set(bars.asset_id)), 'events': []}), encoding='utf-8')
        self.entries = self.root / 'entries.json'
        self.entries.write_text(json.dumps({'schema_version': 1, 'entries': [
            {'asset_id': 'CN_ETF_XSHG_510300', 'quantity': 100, 'limit_price': 10}]}), encoding='utf-8')

    def run_case(self, **changes):
        kwargs = {'source': 'fixture', 'market': 'CN_ETF', 'initial_cash': 10000,
            'commission_bps': 5, 'minimum_commission': 5, 'slippage_bps': 0,
            'max_participation_rate': .01, 'max_asset_weight': .1, 'max_gross_exposure': .1,
            'corporate_actions_path': self.actions, 'fixed_hold_benchmark_path': self.entries}
        return run_simulation(**{**kwargs, **changes})

    def test_actual_paper_pipeline_persists_inherited_economics_and_comparison(self):
        output = self.root / 'output'
        result = self.run_case(output_dir=output)
        baseline = result['fixed_hold_benchmark']
        self.assertEqual(result['request']['execution_economics'], baseline['request']['execution_economics'])
        self.assertEqual([x['date'] for x in result['equity_curve']], [x['date'] for x in baseline['equity_curve']])
        self.assertEqual(result['request']['fixed_hold_benchmark_sha256'], hashlib.sha256(self.entries.read_bytes()).hexdigest())
        manifest = json.loads((output / 'manifest.json').read_text())
        saved = json.loads((output / 'account_comparison.json').read_text())
        self.assertEqual(saved, manifest['account_comparison'])
        self.assertEqual(saved, result['account_comparison'])
        self.assertEqual(json.loads((output / 'fixed_hold_benchmark.json').read_text()), baseline)
        self.assertTrue((output / 'fixed_hold_benchmark_curve.csv').exists())
        self.assertFalse(saved['risk_adjusted_alpha_verified'])
        previous = (output / 'manifest.json').read_bytes()
        with self.assertRaises(FileExistsError):
            write_paper_simulation_artifacts(result, output)
        without = {key: value for key, value in result.items() if key not in ('fixed_hold_benchmark', 'account_comparison')}
        with self.assertRaises(FileExistsError):
            write_paper_simulation_artifacts(without, output)
        self.assertEqual((output / 'manifest.json').read_bytes(), previous)

    def test_market_admission_remains_before_data_or_benchmark_file_reads(self):
        with patch('scripts.run_paper_simulation._load_bars', side_effect=AssertionError('must not load')):
            with self.assertRaisesRegex(ValueError, 'CN_ETF'):
                self.run_case(source='processed-bars', fixed_hold_benchmark_path=self.root/'missing.json')

    def test_attachment_requires_explicit_capacity_actions_and_cash_only_start(self):
        for change in [{'max_participation_rate': None}, {'corporate_actions_path': None},
                       {'positions_csv': self.root/'missing_positions.csv'}, {'market': 'US'}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.run_case(**change)

    def test_benchmark_spec_rejects_fee_override_or_ambiguous_entries(self):
        for spec in [{'schema_version': 1, 'entries': [], 'initial_cash': 20000},
                     {'schema_version': 1, 'entries': [{'asset_id': 'CN_ETF_XSHG_510300', 'quantity': 100, 'limit_price': 10, 'broker': 'example'}]},
                     {'schema_version': True, 'entries': []}]:
            self.entries.write_text(json.dumps(spec), encoding='utf-8')
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                self.run_case()


if __name__ == '__main__':
    unittest.main()
