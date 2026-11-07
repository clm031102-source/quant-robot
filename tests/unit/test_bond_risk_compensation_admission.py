"""Temporary invented repositories; no real financial input or admission."""
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import getcontext, Inexact, ROUND_DOWN
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.paper import bond_risk_compensation as kernel
from quant_robot.research import bond_risk_compensation_admission as a
from quant_robot.research import pm_startup_gate as pm


class FixedDatetime(datetime):
    @classmethod
    def now(cls,tz=None): return cls(2026,11,7,3,0,tzinfo=timezone.utc)


class PreparedFixture:
    def __init__(self,payloads=None):
        self.stack=ExitStack(); self.root=Path(self.stack.enter_context(TemporaryDirectory()))
        repo=Path(__file__).resolve().parents[2]
        subprocess.run(['git','init','--quiet','--initial-branch='+a.BRANCH],cwd=self.root,check=True,capture_output=True)
        self.config=json.loads((repo/a.PM_INPUTS['pm_policy']).read_bytes())
        self.family=json.loads((repo/a.PM_INPUTS['family_scheduler']).read_bytes())
        self.workstations=json.loads((repo/a.PM_INPUTS['workstations']).read_bytes())
        for row in self.config['required_reading']: self.write(row['path'],b'invented protocol text only\n')
        for name in a.IMPLEMENTATION: self.write(name,(repo/name).read_bytes())
        for role,value in [('pm_policy',self.config),('family_scheduler',self.family),('workstations',self.workstations)]:
            self.write(a.PM_INPUTS[role],a.canonical(value))
        self.write(a.PM_INPUTS['campaign'],a.canonical(dict(campaign_id='quant_manager_72h_20261106',status='active',
            machine='office_desktop',task_branch=a.BRANCH,started_at='2026-11-06T16:21:39Z',
            delivery_deadline='2026-11-09T16:21:39Z',finite_preregistered_studies_required=True,
            old_consumed_scopes_remain_closed=True,holdout_unsealing_authorized=False,live_boundary_allowed=False)))
        rows=[]; payloads=payloads or {}
        for role in sorted(a.CORE_ROLES|set(payloads)):
            default=a.BAR_PATH.format(role[-4:]) if role.startswith('bars_') else f'data/invented/{role}.json'
            path,body=payloads.get(role,(default,a.canonical({'invented':True,'role':role})))
            self.write(path,body)
            rows.append(dict(role=role,path=str(self.root/path),sha256=a.digest(body),bytes=len(body)))
        method=next(r['sha256'] for r in rows if r['role']=='method')
        split=next(r['sha256'] for r in rows if r['role']=='split_contract')
        self.write(a.MANIFEST,a.canonical(dict(artifact_type='bond_risk_compensation_input_manifest_v1',
            method_sha256=method,split_contract_sha256=split,input_count=len(rows),inputs=rows)))
        self.stack.enter_context(patch.object(a,'METHOD_SHA',method))
        self.stack.enter_context(patch.object(a,'SPLIT_CONTRACT_SHA',split))
        self.stack.enter_context(patch.object(a,'MANIFEST_SHA',a.file_digest(self.root/a.MANIFEST)))
        self.stack.enter_context(patch.object(a,'datetime',FixedDatetime))
        # Other CI Python versions may exercise only the synthetic verifier.
        # Its remaining context, dependency and executable hashes remain real.
        runtime=a.runtime_environment
        self.stack.enter_context(patch.object(a,'runtime_environment',side_effect=lambda:{**runtime(),'python':'3.12.13'}))
        self.packet=a.build_registration(self.root)
        self.write(a.REGISTRATION,a.canonical(self.packet))
        for path,reviewer in ((a.REVIEW,'quant_manager_72h'),(a.ROOT_REVIEW,'root')):
            self.write(path,a.canonical(dict(status='accepted_for_one_conditional_bond_risk_compensation',
                reviewer=reviewer,registration_sha256=self.packet['registration_sha256'],
                qualified=False,real_forward_days_added=0,financial_execution_authorized=True)))
        self.write(a.ADMISSION,a.canonical(dict(artifact_type='bond_risk_compensation_admission_v1',status='authorized_once',
            registration=self.ref(a.REGISTRATION),review=self.ref(a.REVIEW),root_review=self.ref(a.ROOT_REVIEW),policy=a.POLICY)))

    def close(self): self.stack.close()
    def write(self,path,raw):
        target=self.root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    def ref(self,path): return {'path':path,'sha256':a.file_digest(self.root/path)}
    def gate(self):
        gate=pm.build_quant_pm_startup_gate(gate_config=self.config,workstations_config=self.workstations,
            family_config=self.family,repo_root=self.root,machine='office_desktop',task='factor_review',
            branch=a.BRANCH,current_branch=a.BRANCH)
        gate['generated_at']=FixedDatetime.now().isoformat(); return gate
    def execute(self):
        return a.execute(self.root,expected_registration_sha256=self.packet['registration_sha256'],gate_supplier=self.gate)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=PreparedFixture(); self.addCleanup(self.f.close)

    def test_actual_PM_scope_and_comparison_are_not_mocked(self):
        with patch('quant_robot.research.bond_risk_compensation_historical.load_claimed_inputs') as loader:
            gate=self.f.gate()
            self.assertEqual(gate['status'],'ready',gate['blockers'])
            self.assertEqual(gate['mode'],a.MODE)
            self.assertTrue(gate['safety']['bond_risk_compensation_allowed'])
            self.assertFalse(gate['safety']['factor_batch_allowed'])
            self.assertEqual(gate['account_comparison']['additional_nontrading_references'],1)
            self.assertFalse(gate['account_comparison']['holding_control_tested'])
            self.assertFalse(gate['account_comparison']['alpha_or_promotion_eligible'])
            loader.assert_not_called()

    def test_missing_approval_or_changed_original_blocks_before_claim(self):
        (self.f.root/a.ROOT_REVIEW).unlink()
        with self.assertRaises(OSError): self.f.execute()
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_orphan_decoded_input_blocks_before_claim_and_parser(self):
        folder=self.f.root/a.DIRECTORY
        self.f.write(a.DIRECTORY+'/decoded_input.json',b'{"invented_orphan":true}')
        with patch('quant_robot.research.bond_risk_compensation_historical.run_claimed_diagnostic') as runner,patch(
                'quant_robot.research.bond_risk_compensation_historical.load_claimed_inputs') as loader:
            with self.assertRaisesRegex(ValueError,'reserved or consumed'): self.f.execute()
            runner.assert_not_called(); loader.assert_not_called()
        self.assertFalse((folder/'attempt_claim.json').exists())
        self.assertFalse((folder/'financial_decode_started.json').exists())
        self.assertEqual((folder/'decoded_input.json').read_bytes(),b'{"invented_orphan":true}')

    def test_scope_policy_and_environment_cannot_expand(self):
        packet=json.loads(a.canonical(self.f.packet)); packet['policy']['end']='2026-12-31'
        packet['registration_sha256']=a.digest(a.canonical({k:v for k,v in packet.items() if k!='registration_sha256'}))
        with self.assertRaises(ValueError): a.validate_registration(packet,self.f.root)
        saved=getcontext().copy()
        try:
            getcontext().rounding=ROUND_DOWN
            with self.assertRaisesRegex(ValueError,'environment'): self.f.execute()
        finally: __import__('decimal').setcontext(saved)
        old=kernel.CONTEXT.traps[Inexact]
        try:
            kernel.CONTEXT.traps[Inexact]=not old
            with self.assertRaisesRegex(ValueError,'environment'): self.f.execute()
        finally: kernel.CONTEXT.traps[Inexact]=old
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_source_change_or_expiration_blocks_before_decode(self):
        class Expired(FixedDatetime):
            @classmethod
            def now(cls,tz=None): return cls(2026,11,10,tzinfo=timezone.utc)
        with patch.object(a,'datetime',Expired),self.assertRaisesRegex(ValueError,'Active campaign'):
            self.f.execute()
        ref=self.f.packet['inputs']['bars_2020'];self.f.write(ref['path'],b'changed')
        with self.assertRaisesRegex(ValueError,'Source size|Frozen file'): self.f.execute()
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_claim_then_marker_then_failure_consumes_once(self):
        seen=[]
        def worker(claim):
            self.assertTrue((self.f.root/a.DIRECTORY/'attempt_claim.json').is_file())
            self.assertFalse((self.f.root/a.DIRECTORY/'financial_decode_started.json').exists())
            claim.begin_financial_decode()
            self.assertTrue((self.f.root/a.DIRECTORY/'financial_decode_started.json').is_file())
            seen.append(claim); raise ValueError('invented numerical failure')
        with patch('quant_robot.research.bond_risk_compensation_historical.run_claimed_diagnostic',side_effect=worker) as run:
            with self.assertRaisesRegex(ValueError,'invented numerical'): self.f.execute()
            with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()
            self.assertEqual(run.call_count,1)
        outcome=json.loads((self.f.root/a.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(outcome['study_number'],21);self.assertTrue(outcome['research_study_consumed'])
        with self.assertRaises(ValueError): seen[0].read('calendar')

    def test_failure_before_parser_reserves_attempt_not_new_financial_study(self):
        with patch('quant_robot.research.bond_risk_compensation_historical.run_claimed_diagnostic',side_effect=ValueError('before parser')):
            with self.assertRaisesRegex(ValueError,'before parser'): self.f.execute()
        outcome=json.loads((self.f.root/a.DIRECTORY/'outcome.json').read_bytes())
        self.assertFalse(outcome['research_study_consumed']);self.assertNotIn('study_number',outcome)
        with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()

    def test_branch_change_after_claim_blocks_and_no_scope_reauthorization(self):
        def worker(claim):
            self.assertIsNone(a.scope('factor_review',self.f.family,
                {'blockers':['insufficient_active_research_families'],'summary':{'primary_budget_share':0,'active_primary_families':0}},root=self.f.root,branch=a.BRANCH))
            subprocess.run(['git','symbolic-ref','HEAD','refs/heads/codex/other'],cwd=self.f.root,check=True)
            claim.guard('before','changed_branch')
        with patch('quant_robot.research.bond_risk_compensation_historical.run_claimed_diagnostic',side_effect=worker):
            with self.assertRaisesRegex(ValueError,'branch changed'): self.f.execute()

    def test_completed_account_original_mutation_blocks_final_publication(self):
        def worker(claim):
            claim.begin_financial_decode(); accounts={}
            for identity in [f'M{m}_S{s}' for m,s in a.POLICY['cost_cases']]+['CASH']:
                path=a.DIRECTORY+'/accounts/'+identity+'/complete.json'
                self.f.write(path,b'{"invented":true}')
                accounts[identity]=self.f.ref(path)
            path=a.DIRECTORY+'/reference/complete.json'; self.f.write(path,b'{"invented_reference":true}')
            reference=self.f.ref(path)
            self.f.write(accounts['M0_S0']['path'],b'{"changed_after_capture":true}')
            return dict(artifact_type='conditional_bond_risk_compensation_result_v1',
                registration_sha256=claim.packet['registration_sha256'],qualified=False,real_forward=0,
                historical_returns_computed=True,accounts=accounts,strategy_accounts=9,cash_controls=1,
                additional_nontrading_references=1,reference=reference,study_number=21,
                holding_control_tested=False,alpha_or_promotion_eligible=False)
        with patch('quant_robot.research.bond_risk_compensation_historical.run_claimed_diagnostic',side_effect=worker):
            with self.assertRaisesRegex(ValueError,'Frozen file changed'): self.f.execute()
        self.assertFalse((self.f.root/a.DIRECTORY/'result.json').exists())
        self.assertEqual(json.loads((self.f.root/a.DIRECTORY/'outcome.json').read_bytes())['status'],'failed_consumed')

    def _invented_complete_result(self,fixture,claim):
        claim.begin_financial_decode(); accounts={}
        for identity in [f'M{m}_S{s}' for m,s in a.POLICY['cost_cases']]+['CASH']:
            path=a.DIRECTORY+'/accounts/'+identity+'/complete.json'
            fixture.write(path,b'{"invented":true}'); accounts[identity]=fixture.ref(path)
        path=a.DIRECTORY+'/reference/complete.json'; fixture.write(path,b'{"invented_reference":true}')
        reference=fixture.ref(path)
        snapshot={'fixture':{'invented_value':'91'},'provenance':{'all_values_invented':True}}
        path=a.DIRECTORY+'/decoded_input.json'
        a.write_exclusive_json(fixture.root/path,snapshot)
        canonical_sha=a.digest(a.canonical(snapshot))
        return dict(artifact_type='conditional_bond_risk_compensation_result_v1',
            registration_sha256=claim.packet['registration_sha256'],qualified=False,real_forward=0,
            historical_returns_computed=True,accounts=accounts,strategy_accounts=9,cash_controls=1,
            additional_nontrading_references=1,reference=reference,study_number=21,
            holding_control_tested=False,alpha_or_promotion_eligible=False,
            decoded_input_sha256=canonical_sha,
            decoded_input_artifact={**fixture.ref(path),'canonical_sha256':canonical_sha})

    def test_persisted_decoded_input_is_bound_by_file_and_canonical_digests(self):
        def worker(claim): return self._invented_complete_result(self.f,claim)
        with patch('quant_robot.research.bond_risk_compensation_historical.run_claimed_diagnostic',side_effect=worker):
            self.assertEqual(self.f.execute()['status'],'completed')
        result=json.loads((self.f.root/a.DIRECTORY/'result.json').read_bytes())
        artifact=result['decoded_input_artifact']
        raw=(self.f.root/artifact['path']).read_bytes()
        self.assertEqual(a.digest(raw),artifact['sha256'])
        self.assertEqual(a.digest(a.canonical(json.loads(raw))),result['decoded_input_sha256'])

    def test_decoded_input_mutation_or_forged_ref_blocks_final_publication(self):
        for problem in ('changed_bytes','rehashed_changed_content','missing_file','wrong_path'):
            fixture=PreparedFixture()
            try:
                def worker(claim):
                    result=self._invented_complete_result(fixture,claim)
                    artifact=result['decoded_input_artifact']; path=fixture.root/artifact['path']
                    if problem=='missing_file': path.unlink()
                    elif problem=='wrong_path': artifact['path']=a.DIRECTORY+'/reference/complete.json'
                    else:
                        snapshot=json.loads(path.read_bytes()); snapshot['fixture']['invented_value']='92'
                        path.write_bytes(a.canonical(snapshot))
                        if problem=='rehashed_changed_content': artifact['sha256']=a.file_digest(path)
                    return result
                with self.subTest(problem=problem),patch(
                        'quant_robot.research.bond_risk_compensation_historical.run_claimed_diagnostic',side_effect=worker):
                    with self.assertRaises((ValueError,OSError)): fixture.execute()
                self.assertFalse((fixture.root/a.DIRECTORY/'result.json').exists())
                outcome=json.loads((fixture.root/a.DIRECTORY/'outcome.json').read_bytes())
                self.assertEqual(outcome['status'],'failed_consumed'); self.assertTrue(outcome['research_study_consumed'])
            finally: fixture.close()


if __name__=='__main__': unittest.main()
