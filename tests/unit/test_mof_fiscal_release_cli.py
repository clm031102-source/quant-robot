from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import review_mof_fiscal_release as cli
from tests.unit.test_mof_fiscal_release import document


class MofFiscalReleaseCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'release.html'
        self.source.write_bytes(document())
        self.output = self.root / 'review'
        self.digest = hashlib.sha256(self.source.read_bytes()).hexdigest()
        self.args = ['--input', str(self.source), '--source-sha256', self.digest,
                     '--year', '2024', '--month', '5', '--output-dir', str(self.output),
                     '--machine', 'office_desktop', '--branch', 'codex/factor-review-fixture']
        self.gate = {'status': 'ready', 'primary_market': 'CN_ETF', 'blockers': []}

    def invoke(self, args=None):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = cli.main(self.args if args is None else args)
        return code, json.loads(stdout.getvalue())

    def test_real_file_cli_retains_gate_source_and_implementation_identities(self):
        with patch.object(cli, 'run_quant_pm_startup_gate', return_value=self.gate) as gate:
            code, result = self.invoke()
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'parsed_source_not_admitted')
        self.assertEqual(result['observation']['source_sha256'], self.digest)
        self.assertEqual(result['observation']['assumed_available_civil_day'], '2024-06-25')
        self.assertFalse(result['observation']['research_admission_granted'])
        self.assertIn('mof_fiscal_release.py', result['implementation_sha256'])
        self.assertIn('review_mof_fiscal_release.py', result['implementation_sha256'])
        self.assertEqual(json.loads((self.output / 'result.json').read_text()), result)
        self.assertEqual(json.loads((self.output / 'gate.json').read_text()), self.gate)
        self.assertEqual(gate.call_args.kwargs['task'], 'factor_review')
        self.assertEqual(gate.call_args.kwargs['machine'], 'office_desktop')

    def test_source_hash_mismatch_rejects_before_gate_or_output_creation(self):
        self.source.write_bytes(document(national='121'))
        with patch.object(cli, 'run_quant_pm_startup_gate') as gate:
            code, result = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result['status'], 'rejected')
        gate.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_gate_blockers_prevent_source_interpretation(self):
        blocked = {**self.gate, 'blockers': ['research_context_missing']}
        with patch.object(cli, 'run_quant_pm_startup_gate', return_value=blocked), \
                patch.object(cli, 'parse_mof_monthly_expenditure') as parser:
            code, result = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result['status'], 'gate_blocked')
        parser.assert_not_called()
        self.assertFalse(result['research_admission_granted'])

    def test_period_failure_is_retained_after_gate_without_observation(self):
        args = list(self.args)
        args[args.index('--month') + 1] = '4'
        with patch.object(cli, 'run_quant_pm_startup_gate', return_value=self.gate):
            code, result = self.invoke(args)
        self.assertEqual(code, 1)
        self.assertEqual(result['status'], 'rejected')
        self.assertNotIn('observation', result)
        self.assertEqual(json.loads((self.output / 'result.json').read_text()), result)

    def test_existing_output_is_not_overwritten_or_reused(self):
        self.output.mkdir()
        marker = self.output / 'prior.json'
        marker.write_text('preserve')
        with patch.object(cli, 'run_quant_pm_startup_gate') as gate:
            code, result = self.invoke()
        self.assertEqual(code, 1)
        self.assertEqual(result['status'], 'rejected')
        self.assertEqual(marker.read_text(), 'preserve')
        gate.assert_not_called()

    def test_gb2312_cli_binds_original_source_instead_of_transcoded_hash(self):
        raw = document().decode().replace('UTF-8', 'gb2312').encode('gb2312')
        self.source.write_bytes(raw)
        args = list(self.args)
        args[args.index('--source-sha256') + 1] = hashlib.sha256(raw).hexdigest()
        with patch.object(cli, 'run_quant_pm_startup_gate', return_value=self.gate):
            code, result = self.invoke(args)
        self.assertEqual(code, 0)
        self.assertEqual(result['observation']['source_encoding'], 'gb2312')
        self.assertEqual(result['observation']['source_sha256'], hashlib.sha256(raw).hexdigest())


if __name__ == '__main__':
    unittest.main()
