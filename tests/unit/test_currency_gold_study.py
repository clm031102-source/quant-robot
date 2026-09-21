"""Admission tests use synthetic source files and a mocked calculator only."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research import currency_gold_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, runtime_environment, sha256
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate

REPO = Path(__file__).resolve().parents[2]


class CurrencyGoldGrossAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.inputs = {}

        def put(role, content, path=None):
            path = path or 'data/'+role+'.json'
            target = self.root/path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            self.inputs[role] = dict(path=path, sha256=sha256(content))

        for role in study.ROLES-{'source_review'}:
            put(role,b'{}')
        put('cadence_result',canonical(dict(screen={'passed':True},returns_computed=False)))
        put('cadence_outcome',canonical(dict(status='completed',result_sha256=self.inputs['cadence_result']['sha256'])))
        put('cadence_verification',canonical(dict(status='passed',result_sha256=self.inputs['cadence_result']['sha256'],
            registration_sha256=self.inputs['cadence_registration']['sha256'],pins=[dict(path=f'original/{i}',
                sha256=self.inputs[f'cadence_authority_{i}']['sha256']) for i in range(189)])))
        put('market_registration',canonical(dict(inputs={role[7:]:item for role,item in self.inputs.items() if role.startswith('market_') and role!='market_registration'})))
        put('source_review',canonical(dict(fixed=self.inputs.copy(),returns_calculated=False,net_account_allowed=False)),study.REVIEW)
        fixed=patch.object(study,'REVIEW_SHA256',self.inputs['source_review']['sha256'])
        fixed.start();self.addCleanup(fixed.stop)
        code = {}
        for name in study.IMPLEMENTATION:
            target = self.root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b'# synthetic')
            code[name] = dict(path=name, sha256=sha256(target.read_bytes()))
        self.packet = study.build_registration(inputs=self.inputs, code_files=code,
            branch='codex/factor-review-synthetic', environment=runtime_environment())
        raw = canonical(self.packet)
        target = self.root/study.REGISTRATION
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        self.family = json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.family[study.DECISION] = study.admission(self.packet, raw)
        self.gate_config = json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        self.workstations = json.loads((REPO/'configs/workstations.json').read_bytes())
        for row in self.gate_config['required_reading']:
            target = self.root/row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text('fixture')

    def gate(self):
        return build_quant_pm_startup_gate(gate_config=self.gate_config,
            workstations_config=self.workstations, repo_root=self.root, machine='office_desktop',
            task='factor_batch', branch=self.packet['branch'], current_branch=self.packet['branch'],
            family_config=self.family)

    def test_gate_allows_only_exact_gross_and_preflight_does_not_calculate(self):
        gate = self.gate()
        self.assertEqual(gate['status'], 'ready', gate['blockers'])
        self.assertEqual(gate['mode'], study.MODE)
        self.assertTrue(gate['safety']['currency_gold_diagnostic_allowed'])
        self.assertFalse(gate['safety']['factor_batch_allowed'])
        self.assertEqual(gate['safety']['factor_batch_scope'], {})
        self.assertFalse(gate['safety']['final_holdout_allowed'])
        with patch.object(study, 'calculate') as calculate:
            study.preflight(self.root, self.family, self.gate)
            calculate.assert_not_called()
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_unregistered_role_is_rejected(self):
        inputs = dict(self.inputs, bars_2020=dict(path='data/price.parquet', sha256='0'*64))
        with self.assertRaisesRegex(ValueError, 'Exact study inputs'):
            study.build_registration(inputs=inputs, code_files=self.packet['code_files'],
                branch=self.packet['branch'], environment=self.packet['environment'])

    def test_source_mutation_fails_before_claim_or_calculation(self):
        (self.root/self.inputs['cadence_authority_0']['path']).write_bytes(b'changed')
        with patch.object(study, 'calculate') as calculate:
            with self.assertRaisesRegex(ValueError, 'Pinned file changed'):
                study.execute(self.root, self.family, self.gate)
            calculate.assert_not_called()
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_admission_cannot_expand_to_account(self):
        self.family[study.DECISION]['net_account_allowed'] = True
        self.assertEqual(self.gate()['status'], 'blocked')
        with self.assertRaises(ValueError):
            study.preflight(self.root, self.family, self.gate)

    def test_stale_gate_is_rejected(self):
        gate = self.gate()
        gate['generated_at'] = (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
        with self.assertRaisesRegex(ValueError, 'Fresh exact'):
            study.preflight(self.root, self.family, lambda: gate)

    def test_claim_precedes_calculation_and_failed_attempt_is_consumed(self):
        def fail(_):
            self.assertTrue((self.root/study.DIRECTORY/'attempt_claim.json').exists())
            raise ValueError('synthetic calculation failure')
        with patch.object(study, 'calculate', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'synthetic calculation failure'):
                study.execute(self.root, self.family, self.gate)
        self.assertEqual(self.gate()['status'], 'blocked')
        with self.assertRaisesRegex(ValueError, 'consumed'):
            study.execute(self.root, self.family, self.gate)
        terminal = json.loads((self.root/study.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(terminal['status'], 'failed_consumed')

    def test_success_cannot_be_repeated(self):
        with patch.object(study, 'calculate', return_value={'synthetic': True}):
            self.assertTrue(study.execute(self.root, self.family, self.gate)['synthetic'])
        self.assertEqual(self.gate()['status'], 'blocked')
        with self.assertRaisesRegex(ValueError, 'consumed'):
            study.execute(self.root, self.family, self.gate)

    def test_multiple_dedicated_scopes_fail_closed(self):
        with patch('quant_robot.research.pm_startup_gate.enterprise_cadence_scope',
                   return_value=dict(mode='single_enterprise_cadence_only', scope={})):
            gate = self.gate()
        self.assertEqual(gate['status'], 'blocked')
        self.assertIn('multiple_dedicated_diagnostics_authorized', gate['blockers'])
        self.assertFalse(gate['safety']['currency_gold_diagnostic_allowed'])
        self.assertFalse(gate['safety']['factor_batch_allowed'])

