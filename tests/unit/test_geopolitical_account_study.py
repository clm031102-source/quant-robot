"""Synthetic admission checks; never execute retained market accounts."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research import geopolitical_account_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, runtime_environment, sha256
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate
from tests.unit.test_geopolitical_account import invented_calendar,source_states
from quant_robot.research.geopolitical_account import make_plan

REPO=Path(__file__).resolve().parents[2]


class AccountAdmissionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.inputs={};code={}
        def put_path(path,raw):
            target=self.root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            return dict(path=path,sha256=sha256(raw))
        for path in study.IMPLEMENTATION:
            code[path]=put_path(path,b'# synthetic current implementation')
        for role,path in study.EXTRA_PATHS.items():
            self.inputs[role]=put_path(path,b'{}')
        self.inputs['executed_source_pm_gate']=put_path(study.EXTRA_PATHS['executed_source_pm_gate'],b'# synthetic original source gate')
        names=['proposal','method','account_plan','cadence_result','scope.json','source_outcome.json','bars','actions','sessions']
        names += [f'opaque_{i}' for i in range(60-len(names))]
        originals={}
        def put(role,value):
            path=f'data/synthetic/{role}.json'
            originals[role]=put_path(path,canonical(value));self.inputs['review_'+role]=originals[role]
        for role in names:put(role,{})
        plan=make_plan(invented_calendar(),source_states())
        put('account_plan',plan);put('cadence_result',dict(rows=source_states()));put('actions',dict(events=[]))
        for role,value in [('sessions',plan['sessions']),('strategy_cycles',plan['strategy_cycles'])]:
            self.inputs[role]=put_path(study.EXTRA_PATHS[role],canonical(value))
        self.inputs['comparison_policy']=put_path(study.EXTRA_PATHS['comparison_policy'],
            canonical(dict(plan['comparison_policy'],strategy_cycles=self.inputs['strategy_cycles'])))
        put('method',dict(account_plan=originals['account_plan']))
        source_code=deepcopy(code)
        source_code={k:v for k,v in source_code.items() if k in study.SOURCE_CODE}
        gate_path='src/quant_robot/research/pm_startup_gate.py'
        source_code[gate_path]=dict(path=gate_path,sha256=self.inputs['executed_source_pm_gate']['sha256'])
        put('scope.json',dict(code_files=source_code))
        put('source_outcome.json',dict(status='raw_sources_retained_review_pending',requests=6,
            market_outcomes_computed=False,scope_sha256=originals['scope.json']['sha256']))
        review=dict(inputs=originals,status='conditional_account_inputs_prepared_no_outcomes',
                    market_outcomes_computed=False,account_executed=False,bar_rows=944,calendar_sessions=944)
        self.inputs['input_review']=put_path(study.EXTRA_PATHS['input_review'],canonical(review))
        execution=dict(stage=study.STAGE,max_executions=1,account_count=27,method_changes_allowed=False,
            input_review=self.inputs['input_review'],method=originals['method'],
            independent_source_review=self.inputs['independent_source_review'],paper_promotion_allowed=False,
            final_holdout_allowed=False,live_boundary_allowed=False)
        self.inputs['execution_proposal']=put_path(study.EXTRA_PATHS['execution_proposal'],canonical(execution))
        fixed=patch.object(study,'FROZEN',{role:self.inputs[role] for role in study.FROZEN})
        fixed.start();self.addCleanup(fixed.stop)
        self.packet=study.build_registration(inputs=self.inputs,code_files=code,branch=study.BRANCH,environment=runtime_environment())
        raw=canonical(self.packet);put_path(study.REGISTRATION,raw)
        self.family=json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.family[study.DECISION]=study.admission(self.packet,raw)
        self.gate_config=json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        self.workstations=json.loads((REPO/'configs/workstations.json').read_bytes())
        for row in self.gate_config['required_reading']:put_path(row['path'],b'fixture')

    def gate(self):
        return build_quant_pm_startup_gate(gate_config=self.gate_config,workstations_config=self.workstations,
            repo_root=self.root,machine='office_desktop',task='factor_batch',branch=study.BRANCH,
            current_branch=study.BRANCH,family_config=self.family)

    def test_dedicated_preflight_has_no_account_outcomes_or_general_permissions(self):
        gate=self.gate();self.assertEqual(gate['status'],'ready',gate['blockers'])
        self.assertEqual(gate['mode'],study.MODE)
        self.assertTrue(gate['safety']['geopolitical_account_allowed'])
        self.assertFalse(gate['safety']['factor_batch_allowed'])
        self.assertEqual(gate['safety']['factor_batch_scope'],{})
        self.assertEqual(gate['next_actions'][0]['action'],'run_registered_geopolitical_account_once')
        with patch.object(study,'calculate') as calculate:
            study.preflight(self.root,self.family,self.gate);calculate.assert_not_called()
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_missing_inputs_expanded_authority_and_wrong_branch_rejected(self):
        missing=dict(self.inputs);missing.pop('review_bars')
        with self.assertRaises(ValueError):
            study.build_registration(inputs=missing,code_files=self.packet['code_files'],branch=study.BRANCH,environment=runtime_environment())
        self.family[study.DECISION]['promotion_allowed']=True
        self.assertEqual(self.gate()['status'],'blocked')
        self.family[study.DECISION]=study.admission(self.packet,canonical(self.packet))
        gate=self.gate();gate['selected']['current_branch']='main'
        with self.assertRaises(ValueError):study.preflight(self.root,self.family,lambda:gate)

    def test_input_or_current_implementation_change_fails_before_claim(self):
        for pin in (self.inputs['review_bars'],next(iter(self.packet['code_files'].values()))):
            target=self.root/pin['path'];old=target.read_bytes();target.write_bytes(b'changed')
            with patch.object(study,'calculate') as calc,self.assertRaisesRegex(ValueError,'Pinned file changed'):
                study.execute(self.root,self.family,self.gate)
            calc.assert_not_called();self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())
            target.write_bytes(old)

    def test_prepared_economic_code_and_original_gate_are_bound_separately(self):
        snapshots={k:(self.root/v['path']).read_bytes() for k,v in self.inputs.items()}
        packet=deepcopy(self.packet)
        packet['code_files']['src/quant_robot/research/geopolitical_account.py']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Prepared economic'):
            study.source_chain(packet,snapshots)
        packet=deepcopy(self.packet);packet['inputs']['executed_source_pm_gate']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'Prepared economic'):
            study.source_chain(packet,snapshots)

    def test_stale_gate_runtime_drift_and_multiple_scopes_block(self):
        gate=self.gate();gate['generated_at']=(datetime.now(timezone.utc)-timedelta(seconds=31)).isoformat()
        with self.assertRaises(ValueError):study.preflight(self.root,self.family,lambda:gate)
        with patch.object(study,'runtime_environment',return_value={}):
            with self.assertRaises(ValueError):study.preflight(self.root,self.family,self.gate)
        with patch('quant_robot.research.pm_startup_gate.geopolitical_cadence_scope',return_value=dict(mode='single_geopolitical_cadence_only',scope={})):
            gate=self.gate()
        self.assertIn('multiple_dedicated_diagnostics_authorized',gate['blockers'])
        self.assertFalse(gate['safety']['geopolitical_account_allowed'])

    def test_claim_precedes_calculation_and_failed_attempt_cannot_repeat(self):
        def fail(**kwargs):
            self.assertTrue((self.root/study.DIRECTORY/'attempt_claim.json').exists())
            raise ValueError('synthetic after-claim failure')
        with patch.object(study,'calculate',side_effect=fail):
            with self.assertRaisesRegex(ValueError,'after-claim'):study.execute(self.root,self.family,self.gate)
        self.assertTrue((self.root/study.DIRECTORY/'attempt_claim.json').exists())
        outcome=json.loads((self.root/study.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(outcome['status'],'failed_consumed')
        with self.assertRaisesRegex(ValueError,'consumed'):
            study.execute(self.root,self.family,self.gate)
        self.assertEqual(self.gate()['status'],'blocked')

    def test_success_and_bad_comparison_cannot_bypass_exclusive_registration(self):
        with patch.object(study,'calculate',return_value=dict(synthetic_only=True)):
            self.assertTrue(study.execute(self.root,self.family,self.gate)['synthetic_only'])
        with self.assertRaisesRegex(ValueError,'consumed'):
            study.execute(self.root,self.family,self.gate)

    def test_missing_or_changed_comparison_blocks_pm_gate_before_outcomes(self):
        target=self.root/self.inputs['comparison_policy']['path'];target.write_bytes(b'{}')
        gate=self.gate()
        self.assertIn('account_comparison_specification_missing_or_invalid',gate['blockers'])
        self.assertFalse(gate['safety']['geopolitical_account_allowed'])


if __name__=='__main__':unittest.main()
