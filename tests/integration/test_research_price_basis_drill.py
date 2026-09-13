import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import pandas as pd


class ResearchPriceBasisDrillTests(unittest.TestCase):
    def test_fixed_drill_exports_distinct_analytical_and_account_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'drill'
            environment = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
            completed = subprocess.run([sys.executable, 'scripts/run_cn_etf_research_price_basis_drill.py',
                '--output-dir', str(output)], text=True, capture_output=True, env=environment, timeout=60)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(report['status'], 'passed')
            self.assertEqual(len(report['cases']), 3)
            self.assertEqual(report['market_data_requests'], 0)
            self.assertFalse(report['executable'])
            self.assertFalse(report['source_audit_verified'])
            for case in report['cases'].values():
                self.assertTrue(all(case['checks'].values()))
                for relative, expected_hash in case['files'].items():
                    self.assertEqual(hashlib.sha256((output / relative).read_bytes()).hexdigest(), expected_hash)
            account = pd.read_csv(output / 'dividend_reinvestment_gap' / 'account_comparison.csv')
            self.assertEqual(account.iloc[3]['account_equity'], 1900)
            self.assertEqual(account.iloc[3]['theoretical_index_value'], 2000)
            self.assertEqual(account.iloc[3]['cash_after_close'], 0)
            self.assertEqual(account.iloc[4]['cash_before_close'], 0)
            self.assertEqual(account.iloc[4]['cash_after_close'], 100)


if __name__ == '__main__':
    unittest.main()
