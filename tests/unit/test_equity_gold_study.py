from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research import equity_gold_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, runtime_environment
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate

REPO = Path(__file__).resolve().parents[2]


class EquityGoldStudyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.inputs = {}
        def put(role, content, path=None):
            path = path or 'data/'+role+'.json'; target = self.root/path
            target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
            self.inputs[role] = dict(path=path,sha256=sha256(content))
        for role in ['bars','sessions','actions','cycles','config_account_method','config_execution_clarification','current_research_account',
                     *[f'fixture_{i}' for i in range(133)]]:
            put(role,b'{}')
        base = self.inputs.copy()
        put('input_review',canonical(dict(status='conditional_account_inputs_prepared_no_outcomes',
            inputs=base,market_outcomes_computed=False,account_executed=False)))
        put('input_binding',canonical(dict(source_review=self.inputs['input_review'],inputs=base,original_root=self.root.as_posix())))
        proposal = json.loads((REPO/study.PROPOSAL).read_bytes())
        for key, role in [('source_review','input_review'),('input_binding','input_binding'),
                          ('financial_method','config_account_method'),('execution_clarification','config_execution_clarification')]:
            proposal[key] = self.inputs[role]
        raw = canonical(proposal)
        override = patch.object(study,'PROPOSAL_SHA256',sha256(raw));override.start();self.addCleanup(override.stop)
        put('proposal',raw,study.PROPOSAL)
        code = {}
        for name in study.IMPLEMENTATION:
            p = self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'# fixture')
            code[name] = dict(path=name,sha256=sha256(p.read_bytes()))
        self.packet = study.build_registration(inputs=self.inputs,code_files=code,
            branch='codex/factor-review-synthetic',environment=runtime_environment())
        raw = canonical(self.packet);target=self.root/study.REGISTRATION;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        self.family=json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.family[study.DECISION]=study.admission(self.packet,raw)
        self.gate_config=json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        # Preserve the consumed study's historical protocol in its lifecycle fixtures.
        self.gate_config.pop('account_comparison_protocol', None)
        self.workstations=json.loads((REPO/'configs/workstations.json').read_bytes())
        for row in self.gate_config['required_reading']:
            p=self.root/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')

    def gate(self):
        return build_quant_pm_startup_gate(gate_config=self.gate_config,workstations_config=self.workstations,
            repo_root=self.root,machine='office_desktop',task='factor_batch',branch=self.packet['branch'],
            current_branch=self.packet['branch'],family_config=self.family)

    def test_only_exact_conditional_account_opens_and_preflight_never_calculates(self):
        gate=self.gate();self.assertEqual(gate['status'],'ready',gate['blockers'])
        self.assertTrue(gate['safety']['equity_gold_account_allowed'])
        for flag in ['factor_batch_allowed','final_holdout_allowed','live_boundary_allowed']:
            self.assertFalse(gate['safety'][flag])
        self.assertEqual(gate['safety']['factor_batch_scope'],{})
        with patch.object(study,'calculate',side_effect=AssertionError('early account calculation')):
            study.preflight(self.root,self.family,self.gate)
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_changed_source_fails_before_claim(self):
        (self.root/self.inputs['bars']['path']).write_bytes(b'changed')
        with patch.object(study,'calculate') as calculate:
            with self.assertRaisesRegex(ValueError,'Pinned file changed'):
                study.execute(self.root,self.family,self.gate)
            calculate.assert_not_called()
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_registration_cannot_rebind_a_different_source_manifest(self):
        new=b'{"different":true}'
        (self.root/self.inputs['input_binding']['path']).write_bytes(new)
        self.packet['inputs']['input_binding']['sha256']=sha256(new)
        self.packet=study.build_registration(**{k:self.packet[k] for k in ('inputs','code_files','branch','environment')})
        raw=canonical(self.packet);(self.root/study.REGISTRATION).write_bytes(raw)
        self.family[study.DECISION]=study.admission(self.packet,raw)
        with self.assertRaisesRegex(ValueError,'Frozen source identity'):
            study.execute(self.root,self.family,self.gate)

    def test_broader_admission_and_stale_gate_are_rejected(self):
        gate=self.gate();gate['generated_at']=(datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'Fresh exact'):
            study.preflight(self.root,self.family,lambda:gate)
        self.family[study.DECISION]['general_factor_batch_allowed']=True
        self.assertEqual(self.gate()['status'],'blocked')

    def test_exclusive_claim_precedes_failure_and_never_reopens(self):
        def fail(_):
            self.assertTrue((self.root/study.DIRECTORY/'attempt_claim.json').exists())
            raise ValueError('synthetic failure')
        with patch.object(study,'calculate',side_effect=fail):
            with self.assertRaisesRegex(ValueError,'synthetic failure'):
                study.execute(self.root,self.family,self.gate)
        self.assertEqual(json.loads((self.root/study.DIRECTORY/'outcome.json').read_bytes())['status'],'failed_consumed')
        self.assertEqual(self.gate()['status'],'blocked')
        with self.assertRaisesRegex(ValueError,'consumed'):
            study.execute(self.root,self.family,self.gate)

    def test_completed_result_is_immutable_and_replay_is_rejected(self):
        with patch.object(study,'calculate',return_value={'synthetic':True}):
            study.execute(self.root,self.family,self.gate)
        original=(self.root/study.DIRECTORY/'result.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'consumed'):
            study.execute(self.root,self.family,self.gate)
        self.assertEqual((self.root/study.DIRECTORY/'result.json').read_bytes(),original)
        self.assertEqual(self.gate()['status'],'blocked')
