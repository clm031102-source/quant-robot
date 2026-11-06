"""Fabricated temporary repositories only; no retained market original is decoded."""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import getcontext, ROUND_DOWN
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.research import crypto_monthly_admission as a
from quant_robot.research import pm_startup_gate as pm


class FixedDatetime(datetime):
    @classmethod
    def now(cls,tz=None):
        return cls(2026,11,7,0,0,tzinfo=timezone.utc)


class PreparedFixture:
    """A fully pinned artificial repository, using actual PM scope/comparison code."""
    def __init__(self,source_payloads=None):
        self.stack=ExitStack(); self.root=Path(self.stack.enter_context(TemporaryDirectory()))
        repo=Path(__file__).resolve().parents[2]
        self.config=json.loads((repo/a.PM_INPUTS['pm_policy']).read_bytes())
        self.family=json.loads((repo/a.PM_INPUTS['family_scheduler']).read_bytes())
        self.workstations=json.loads((repo/a.PM_INPUTS['workstations']).read_bytes())
        for row in self.config['required_reading']: self.write(row['path'],b'fabricated protocol only\n')
        for name in a.IMPLEMENTATION: self.write(name,(repo/name).read_bytes())
        for role,value in (('pm_policy',self.config),('family_scheduler',self.family),('workstations',self.workstations)):
            self.write(a.PM_INPUTS[role],a.canonical(value))
        campaign={'campaign_id':'quant_manager_72h_20261106','status':'active','machine':'office_desktop',
            'task_branch':a.BRANCH,'started_at':'2026-11-06T16:21:39Z','delivery_deadline':'2026-11-09T16:21:39Z',
            'finite_preregistered_studies_required':True,'old_consumed_scopes_remain_closed':True,
            'holdout_unsealing_authorized':False,'live_boundary_allowed':False}
        self.write(a.CAMPAIGN,a.canonical(campaign))
        rows=[]
        for role in sorted(a.SOURCE_ROLES):
            payload=(source_payloads or {}).get(role)
            if payload is None: path,body=f'data/fabricated/{role}.json',a.canonical({'fabricated':True,'role':role})
            else: path,body=payload
            self.write(path,body)
            rows.append({'role':role,'path':str(self.root/path),'sha256':a.digest(body),'bytes':len(body)})
        method=next(row['sha256'] for row in rows if row['role']=='monthly_method')
        manifest={'artifact_type':'conditional_crypto_monthly_input_preparation_manifest_v1','method_sha256':method,
                  'input_count':28,'inputs':rows}
        self.write(a.MANIFEST,a.canonical(manifest))
        self.stack.enter_context(patch.object(a,'METHOD_SHA',method))
        self.stack.enter_context(patch.object(a,'MANIFEST_SHA',a.file_digest(self.root/a.MANIFEST)))
        self.stack.enter_context(patch.object(a,'datetime',FixedDatetime))
        # CI may have another Python; synthetic guard fixtures bind its actual
        # context/dependencies/executable, with only the required version label
        # mocked. Production never patches this verifier.
        runtime=a.runtime_environment
        self.stack.enter_context(patch.object(a,'runtime_environment',side_effect=lambda:{**runtime(),'python':'3.12.13'}))
        self.packet=a.build_registration(self.root)
        self.write(a.REGISTRATION,a.canonical(self.packet))
        for path,reviewer in ((a.REVIEW,'quant_manager_72h'),(a.ROOT_REVIEW,'root')):
            self.write(path,a.canonical({'status':'accepted_for_one_conditional_crypto_month',
                'reviewer':reviewer,'registration_sha256':self.packet['registration_sha256'],
                'financial_execution_authorized':True,'qualified':False,'real_forward_days_added':0}))
        self.approval={'artifact_type':'crypto_monthly_conditional_admission_v1','status':'authorized_once',
            'registration':self.ref(a.REGISTRATION),'review':self.ref(a.REVIEW),'root_review':self.ref(a.ROOT_REVIEW),
            'policy':a.POLICY}
        self.write(a.ADMISSION,a.canonical(self.approval))

    def close(self): self.stack.close()
    def write(self,path,body):
        target=self.root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(body)
    def ref(self,path): return {'path':path,'sha256':a.file_digest(self.root/path)}
    def gate(self):
        result=pm.build_quant_pm_startup_gate(gate_config=self.config,workstations_config=self.workstations,
            family_config=self.family,repo_root=self.root,machine='office_desktop',task='factor_review',
            branch=a.BRANCH,current_branch=a.BRANCH)
        result['generated_at']=FixedDatetime.now().isoformat()
        return result
    def execute(self):
        return a.execute(self.root,expected_registration_sha256=self.packet['registration_sha256'],gate_supplier=self.gate)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=PreparedFixture(); self.addCleanup(self.f.close)

    def test_real_pm_scope_comparison_without_mocked_new_scope(self):
        with patch('quant_robot.research.crypto_monthly_historical.load_claimed_month') as decode:
            gate=self.f.gate()
            self.assertEqual(gate['status'],'ready',gate['blockers'])
            self.assertEqual(gate['mode'],a.MODE)
            self.assertTrue(gate['safety']['crypto_monthly_10_account_allowed'])
            self.assertFalse(gate['account_comparison']['holding_control_tested'])
            self.assertFalse(gate['account_comparison']['alpha_or_promotion_eligible'])
            decode.assert_not_called()
            self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_decimal_rounding_or_trap_mutation_blocks_before_claim(self):
        context=getcontext(); saved=context.copy()
        try:
            context.rounding=ROUND_DOWN
            with self.assertRaisesRegex(ValueError,'environment'): self.f.execute()
            context.rounding=saved.rounding
            from decimal import Inexact
            context.traps[Inexact]=not saved.traps[Inexact]
            with self.assertRaisesRegex(ValueError,'environment'): self.f.execute()
        finally:
            __import__('decimal').setcontext(saved)
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_decimal_flags_do_not_change_frozen_environment(self):
        before=a.runtime_environment(); getcontext().flags[__import__('decimal').Inexact]=True
        self.assertEqual(a.runtime_environment(),before)

    def test_input_mutation_blocks_before_financial_decode(self):
        path=self.f.packet['inputs']['spot_1m_zip']['path']
        with (self.f.root/path).open('ab') as stream: stream.write(b'changed')
        with patch('quant_robot.research.crypto_monthly_historical.run_claimed_month') as worker:
            with self.assertRaises(ValueError): self.f.execute()
            worker.assert_not_called()
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_method_and_scope_policy_cannot_expand(self):
        packet=json.loads(a.canonical(self.f.packet)); packet['policy']['end_exclusive']='2026-02-01T00:00:00+00:00'
        packet['registration_sha256']=a.digest(a.canonical({k:v for k,v in packet.items() if k!='registration_sha256'}))
        with self.assertRaisesRegex(ValueError,'fixed-month'): a.validate_registration(packet,self.f.root)

    def test_missing_root_review_cannot_be_replaced_by_method_permission(self):
        (self.f.root/a.ROOT_REVIEW).unlink()
        with self.assertRaises(OSError): self.f.execute()

    def test_consumed_on_failure_and_no_retry(self):
        def worker(claim):
            self.assertTrue((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())
            self.assertTrue((self.f.root/a.DIRECTORY/'financial_decode_started.json').exists())
            raise ValueError('artificial parser failure')
        with patch('quant_robot.research.crypto_monthly_historical.run_claimed_month',side_effect=worker) as run:
            with self.assertRaisesRegex(ValueError,'artificial parser'): self.f.execute()
            with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()
            self.assertEqual(run.call_count,1)
        outcome=json.loads((self.f.root/a.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(outcome['status'],'failed_consumed')
        self.assertTrue(outcome['financial_decode_started'])

    def test_partial_claim_alone_is_consumed(self):
        self.f.write(a.DIRECTORY+'/attempt_claim.json',b'{')
        with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()

    def test_closed_claim_rejects_all_reads(self):
        saved=[]
        def worker(claim): saved.append(claim); raise RuntimeError('test stop')
        with patch('quant_robot.research.crypto_monthly_historical.run_claimed_month',side_effect=worker):
            with self.assertRaises(RuntimeError): self.f.execute()
        with self.assertRaisesRegex(ValueError,'not opened'): saved[0].read('spot_1m_zip')
        with self.assertRaisesRegex(ValueError,'closed'): saved[0].guard('after','test')

    def test_fresh_gate_cannot_open_holdout(self):
        def gate():
            packet=self.f.gate(); packet['safety']['final_holdout_allowed']=True; return packet
        with self.assertRaisesRegex(ValueError,'Fresh exact'):
            a.execute(self.f.root,expected_registration_sha256=self.f.packet['registration_sha256'],gate_supplier=gate)
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())


if __name__=='__main__': unittest.main()
