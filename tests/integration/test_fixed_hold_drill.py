import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from quant_robot.data.fixtures import load_demo_market_bars


class FixedHoldDrillTests(unittest.TestCase):
    def test_existing_paper_cli_accepts_fixed_hold_entries_and_saves_comparison(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars = load_demo_market_bars()
            bars = bars[bars.market.eq('CN_ETF')]
            actions = root / 'actions.json'
            actions.write_text(json.dumps({'schema_version': 1, 'source_ref': 'synthetic fixture only',
                'coverage_start': str(bars.date.min()), 'coverage_end': str(bars.date.max()),
                'asset_ids': sorted(set(bars.asset_id)), 'events': []}), encoding='utf-8')
            entries = root / 'entries.json'
            entries.write_text(json.dumps({'schema_version': 1, 'entries': [
                {'asset_id': 'CN_ETF_XSHG_510300', 'quantity': 100, 'limit_price': 10}]}), encoding='utf-8')
            output = root / 'result'
            command = [sys.executable, 'scripts/run_paper_simulation.py', '--source', 'fixture',
                '--market', 'CN_ETF', '--initial-cash', '10000', '--commission-bps', '5',
                '--minimum-commission', '5', '--slippage-bps', '0', '--max-participation-rate', '.01',
                '--max-asset-weight', '.1', '--max-gross-exposure', '.1',
                '--corporate-actions', str(actions), '--fixed-hold-benchmark', str(entries),
                '--output-dir', str(output)]
            environment = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
            completed = subprocess.run(command, text=True, capture_output=True, env=environment, timeout=60)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            result = json.loads((output / 'manifest.json').read_text())
            baseline = json.loads((output / 'fixed_hold_benchmark.json').read_text())
            self.assertEqual(result['request']['execution_economics'], baseline['request']['execution_economics'])
            self.assertEqual(result['request']['fixed_hold_benchmark_sha256'], hashlib.sha256(entries.read_bytes()).hexdigest())
            self.assertEqual(result['account_comparison'], json.loads((output/'account_comparison.json').read_text()))
            self.assertFalse(result['account_comparison']['research_admission_verified'])

    def test_public_fixed_hold_process_persists_comparable_cash_accounts(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'drill'
            command = [sys.executable, 'scripts/run_cn_etf_fixed_hold_drill.py', '--output-dir', str(output)]
            environment = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
            completed = subprocess.run(command, text=True, capture_output=True, env=environment, timeout=60)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(report['status'], 'passed')
            self.assertEqual(report['market_data_requests'], 0)
            self.assertEqual(report['new_forward_paper_days'], 0)
            self.assertFalse(report['executable'])
            self.assertTrue(all(report['checks'].values()))
            self.assertAlmostEqual(report['comparison']['relative_return'], .005)
            self.assertFalse(report['comparison']['risk_adjusted_alpha_verified'])
            for relative, digest in report['files'].items():
                self.assertEqual(hashlib.sha256((output / relative).read_bytes()).hexdigest(), digest)
            left = json.loads((output / 'cash_distribution_account.json').read_text())
            right = json.loads((output / 'flat_price_account.json').read_text())
            self.assertEqual(left['metrics']['ending_equity'], 10045)
            self.assertEqual(right['metrics']['ending_equity'], 9995)
            self.assertEqual(left['request']['execution_economics'], right['request']['execution_economics'])
            # A second invocation must preserve the already observed artifacts.
            digest = hashlib.sha256((output / 'report.json').read_bytes()).hexdigest()
            repeated = subprocess.run(command, text=True, capture_output=True, env=environment, timeout=60)
            self.assertNotEqual(repeated.returncode, 0)
            self.assertEqual(hashlib.sha256((output / 'report.json').read_bytes()).hexdigest(), digest)


if __name__ == '__main__':
    unittest.main()
