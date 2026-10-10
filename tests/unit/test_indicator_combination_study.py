"""Synthetic admission/lifecycle tests; no retained market outcomes are read."""
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.paper.comparative_allocation import policy_template
from quant_robot.research import indicator_combination_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, runtime_environment, sha256
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate

REPO = Path(__file__).resolve().parents[2]
BRANCH = 'codex/factor-batch-indicator-combinations-20261010'


class IndicatorAdmissionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.inputs = {role:self.put('data/'+role+'.json',b'{}') for role in study.ROLES}
        days = [str(date(2014,1,1)+timedelta(days=i)) for i in range(40)]
        self.inputs['sessions'] = self.put('data/sessions.json',canonical(days))
        self.inputs['proposal'] = self.put(study.PROPOSAL,canonical(dict(study_id=study.STUDY,
            max_executions=1,hypothesis_count=16,new_data_requests=0,final_holdout_allowed=False)))
        self.inputs['strategy_cycles'] = self.put('data/cycles.json',canonical(dict(
            kind='prospective_decision_calendar_and_frozen_rules',
            proposal=self.inputs['proposal'],sessions=self.inputs['sessions'])))
        policy = policy_template(study_id=study.STUDY,first_session=days[20],terminal_session=days[-1],later_start=days[30])
        policy['strategy_cycles'] = self.inputs['strategy_cycles']
        self.inputs['comparison_policy'] = self.put('data/policy.json',canonical(policy))
        fixture_hashes = patch.object(study,'SOURCE_HASHES',{k:self.inputs[k]['sha256'] for k in study.SOURCE_HASHES})
        fixture_hashes.start();self.addCleanup(fixture_hashes.stop)
        code = {path:self.put(path,b'# synthetic implementation') for path in study.IMPLEMENTATION}
        self.packet = study.build_registration(inputs=self.inputs,code_files=code,branch=BRANCH,
            workspace=self.root,environment=runtime_environment())
        raw = canonical(self.packet);self.put(study.REGISTRATION,raw)
        self.family = json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.family[study.DECISION] = study.admission(self.packet,raw)
        self.config = json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        for item in self.config['required_reading']:
            self.put(item['path'],b'fixture')
        self.workstations = json.loads((REPO/'configs/workstations.json').read_bytes())

    def put(self,path,raw):
        target = self.root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
        return dict(path=path,sha256=sha256(raw))

    def gate(self,branch=BRANCH):
        return build_quant_pm_startup_gate(gate_config=self.config,workstations_config=self.workstations,
            repo_root=self.root,machine='office_desktop',task='factor_batch',branch=branch,
            current_branch=branch,family_config=self.family)

    def test_complete_gate_scopes_account_without_computing_signals(self):
        gate = self.gate()
        self.assertEqual(gate['status'],'ready',gate['blockers'])
        self.assertEqual(gate['mode'],study.MODE)
        self.assertEqual(gate['account_comparison']['status'],'passed_specification_only')
        for key in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed','portfolio_grid_allowed','walk_forward_allowed'):
            self.assertIs(gate['safety'][key],False)
        self.assertEqual(gate['safety']['factor_batch_scope'],{})
        with patch.object(study,'calculate') as calculate:
            study.preflight(self.root,self.family,self.gate)
            calculate.assert_not_called()

    def test_wrong_branch_and_expanded_admission_are_blocked(self):
        self.assertEqual(self.gate('codex/factor-batch-other')['status'],'blocked')
        self.family[study.DECISION]['general_factor_batch_allowed'] = True
        self.assertEqual(self.gate()['status'],'blocked')

    def test_comparator_protocol_required(self):
        self.config.pop('account_comparison_protocol')
        gate = self.gate()
        self.assertEqual(gate['status'],'blocked')
        self.assertIn('account_comparison_protocol_invalid',gate['blockers'])
        self.assertFalse(gate['safety']['indicator_combination_account_allowed'])

    def test_input_mutation_fails_without_consuming_attempt(self):
        self.put(self.inputs['bars']['path'],b'changed')
        with patch.object(study,'calculate') as calculate:
            with self.assertRaisesRegex(ValueError,'Pinned file changed'):
                study.execute(self.root,self.family,self.gate)
            calculate.assert_not_called()
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_claim_precedes_computation_and_failed_attempt_remains_consumed(self):
        def fail(*args,**kwargs):
            self.assertTrue((self.root/study.DIRECTORY/'attempt_claim.json').exists())
            raise ValueError('synthetic failure')
        with patch.object(study,'calculate',side_effect=fail):
            with self.assertRaisesRegex(ValueError,'synthetic failure'):
                study.execute(self.root,self.family,self.gate)
        self.assertEqual(self.gate()['status'],'blocked')
        with self.assertRaisesRegex(ValueError,'consumed'):
            study.execute(self.root,self.family,self.gate)
        self.assertEqual(json.loads((self.root/study.DIRECTORY/'outcome.json').read_bytes())['status'],'failed_consumed')

    def test_completed_attempt_cannot_repeat(self):
        with patch.object(study,'calculate',return_value=dict(synthetic=True)):
            self.assertTrue(study.execute(self.root,self.family,self.gate)['synthetic'])
        with self.assertRaisesRegex(ValueError,'consumed'):
            study.execute(self.root,self.family,self.gate)

    def test_stale_gate_rejected(self):
        gate = self.gate();gate['generated_at'] = '2000-01-01T00:00:00+00:00'
        with self.assertRaisesRegex(ValueError,'Fresh restricted'):
            study.preflight(self.root,self.family,lambda:gate)

    def test_conflicting_dedicated_admission_is_blocked(self):
        with patch('quant_robot.research.pm_startup_gate.enterprise_cadence_scope',
                   return_value=dict(mode='single_enterprise_cadence_only',scope={})):
            gate = self.gate()
        self.assertIn('multiple_dedicated_diagnostics_authorized',gate['blockers'])
        self.assertFalse(gate['safety']['indicator_combination_account_allowed'])
