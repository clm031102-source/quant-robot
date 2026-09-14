import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research.month_start_diagnostic_execution import preflight_registration, execute_registration
from quant_robot.research.month_start_diagnostic_registration import DIRECTORY
from tests.unit.month_start_diagnostic_fixtures import execution_fixture


class MonthStartExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); self.root = Path(temporary.name)
        self.packet, self.scheduler, self.gate, _ = execution_fixture(self.root)

    def arguments(self, **changes):
        self.gate['generated_at'] = datetime.now(timezone.utc).isoformat()
        result = dict(root=self.root, registration_path=DIRECTORY+'/registration.json',
            scheduler=self.scheduler, gate_supplier=lambda: self.gate, environment={'python': 'fixture'})
        return result | changes

    def test_preflight_claims_nothing_and_computes_no_signal_or_price(self):
        with patch('pandas.read_parquet', side_effect=AssertionError('no price decoding')), \
                patch('quant_robot.research.month_start_diagnostic_inputs.month_start_diagnostic', side_effect=AssertionError('no signal')):
            prepared = preflight_registration(**self.arguments())
        self.assertEqual(len(prepared.snapshots), 11)
        self.assertFalse((self.root/self.packet['ledger_path']).exists())

    def test_claim_precedes_signal_and_price_decoding(self):
        from quant_robot.research.month_start_diagnostic_inputs import month_start_diagnostic
        import pandas as pd
        read_parquet = pd.read_parquet
        def checked(*args, **kwargs):
            self.assertTrue((self.root/self.packet['ledger_path']).is_file())
            return month_start_diagnostic(*args, **kwargs)
        def checked_decode(*args, **kwargs):
            self.assertTrue((self.root/self.packet['ledger_path']).is_file())
            return read_parquet(*args, **kwargs)
        with patch('quant_robot.research.month_start_diagnostic_inputs.month_start_diagnostic', side_effect=checked), \
                patch('pandas.read_parquet', side_effect=checked_decode):
            result = execute_registration(**self.arguments())
        self.assertEqual(result['diagnostic']['cycle_count'], 53)
        self.assertFalse(result['formal_positive_ev_verified'])
        with self.assertRaisesRegex(ValueError, 'claimed'): execute_registration(**self.arguments())

    def test_stale_wrong_scope_or_expanded_gate_fails_before_claim(self):
        for change in ({'generated_at': '2000-01-01T00:00:00+00:00'},
                {'mode': 'single_monthly_diagnostic_only'}, {'status': 'blocked'}):
            gate = copy.deepcopy(self.gate); gate.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                execute_registration(**self.arguments(gate_supplier=lambda: gate))
        self.gate['safety']['monthly_diagnostic_allowed'] = True
        with self.assertRaises(ValueError): execute_registration(**self.arguments())
        self.assertFalse((self.root/self.packet['ledger_path']).exists())

    def test_decode_failure_consumes_attempt_and_records_failure(self):
        with patch('pandas.read_parquet', side_effect=ValueError('injected decode failure')):
            with self.assertRaises(ValueError): execute_registration(**self.arguments())
        result = json.loads((self.root/DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(result['status'], 'failed'); self.assertEqual(result['failure_kind'], 'ValueError')
        with self.assertRaisesRegex(ValueError, 'claimed'): execute_registration(**self.arguments())

    def test_interruption_is_retained_without_automatic_retry(self):
        def interrupt(_): raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt): execute_registration(**self.arguments(), on_claim=interrupt)
        self.assertEqual(json.loads((self.root/DIRECTORY/'outcome.json').read_bytes())['status'], 'interrupted')
        with self.assertRaisesRegex(ValueError, 'claimed'): execute_registration(**self.arguments())

    def test_changed_original_after_claim_cannot_change_verified_snapshot(self):
        def replace_original(_):
            (self.root/self.packet['inputs']['actions']['path']).write_bytes(b'corrupt after verified read')
        result = execute_registration(**self.arguments(), on_claim=replace_original)
        self.assertEqual(result['diagnostic']['cycle_count'], 53)
        self.assertEqual(result['analytical_price_evidence']['applied_events'], 0)

    def test_prior_result_without_claim_cannot_be_overwritten(self):
        output = self.root/DIRECTORY/'result.json'; output.write_bytes(b'prior result')
        with self.assertRaisesRegex(ValueError, 'claimed'): execute_registration(**self.arguments())
        self.assertEqual(output.read_bytes(), b'prior result')


if __name__ == '__main__': unittest.main()
