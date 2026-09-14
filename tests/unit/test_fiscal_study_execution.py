import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research.fiscal_study_registration import DIRECTORY, expected_admission
from quant_robot.research.fiscal_study_execution import preflight_registration, execute_registration
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256
from tests.unit.test_fiscal_study_registration import fixture


class FiscalExecutionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name); self.packet=fixture(self.root)
        self.scope=expected_admission(self.packet,sha256(canonical(self.packet)))
        self.scheduler={'fiscal_event_account_decision':self.scope}
        self.gate={'generated_at':datetime.now(timezone.utc).isoformat(),'status':'ready',
            'mode':'single_fiscal_event_account_only','primary_market':'CN_ETF','blockers':[],
            'selected':{'machine':'office_desktop','task':'factor_batch','branch':self.packet['branch'],
                        'current_branch':self.packet['branch']},
            'safety':{'fiscal_event_account_allowed':True,'fiscal_event_account_scope':self.scope,
                'factor_batch_scope':{}, **{key:False for key in ('factor_batch_allowed','monthly_diagnostic_allowed',
                    'household_diagnostic_allowed','month_start_diagnostic_allowed','final_holdout_allowed','live_boundary_allowed')}}}

    def arguments(self, **changes):
        return dict(root=self.root,scheduler=self.scheduler,gate_supplier=lambda:self.gate,
                    environment={'python':'fixture'}) | changes

    def test_preflight_never_claims_or_calls_calculation(self):
        with patch('pandas.read_parquet',side_effect=AssertionError('no decoding')):
            prepared=preflight_registration(**self.arguments())
        self.assertEqual(prepared.registration,self.packet)
        self.assertFalse((self.root/DIRECTORY/'attempt_claim.json').exists())

    def test_claim_precedes_calculation_and_original_mutation_does_not_change_snapshot(self):
        path='data/reports/fixture_source.json'; original=(self.root/path).read_bytes()
        def calculate(packet,snapshots):
            self.assertTrue((self.root/DIRECTORY/'attempt_claim.json').exists())
            self.assertEqual(snapshots[path],original)
            return {'stage':packet['stage'],'fixture_result':True}
        with patch('quant_robot.research.fiscal_study_inputs.calculate_from_snapshots',side_effect=calculate):
            execute_registration(**self.arguments(),on_claim=lambda _: (self.root/path).write_bytes(b'changed'))
        self.assertEqual(json.loads((self.root/DIRECTORY/'outcome.json').read_bytes())['status'],'completed')
        with self.assertRaisesRegex(ValueError,'claimed'): execute_registration(**self.arguments())

    def test_failed_or_interrupted_attempt_cannot_be_retried(self):
        with patch('quant_robot.research.fiscal_study_inputs.calculate_from_snapshots',side_effect=ValueError('injected')):
            with self.assertRaises(ValueError): execute_registration(**self.arguments())
        self.assertEqual(json.loads((self.root/DIRECTORY/'outcome.json').read_bytes())['status'],'failed')
        with self.assertRaisesRegex(ValueError,'claimed'): execute_registration(**self.arguments())

    def test_stale_or_expanded_gate_fails_before_claim(self):
        for change in ({'generated_at':'2000-01-01T00:00:00+00:00'}, {'mode':'family_rotation_review_only'},
                {'safety':{**self.gate['safety'],'factor_batch_allowed':True}},
                {'safety':{**self.gate['safety'],'live_boundary_allowed':True}}):
            gate=copy.deepcopy(self.gate);gate.update(change)
            with self.subTest(change=change),self.assertRaises(ValueError):
                execute_registration(**self.arguments(gate_supplier=lambda:gate))
        self.assertFalse((self.root/DIRECTORY/'attempt_claim.json').exists())

    def test_interrupt_is_recorded_and_real_cli_rejects_fixture_registration(self):
        from scripts.run_cn_etf_fiscal_study import run
        with patch('subprocess.check_output',return_value=self.packet['branch']):
            with self.assertRaisesRegex(ValueError,'Real CLI'):
                run(self.root,action='execute')
        def interrupt(_):raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):execute_registration(**self.arguments(),on_claim=interrupt)
        self.assertEqual(json.loads((self.root/DIRECTORY/'outcome.json').read_bytes())['status'],'interrupted')
        with self.assertRaisesRegex(ValueError,'claimed'):execute_registration(**self.arguments())


if __name__=='__main__':unittest.main()
