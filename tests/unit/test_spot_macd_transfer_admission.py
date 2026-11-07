"""Artificial temporary projects; actual guard never admits artificial sources."""
from contextlib import ExitStack
from datetime import datetime, timezone
from decimal import getcontext, setcontext, ROUND_DOWN
import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.research import spot_macd_transfer_admission as a
from quant_robot.research import pm_startup_gate as pm


class FixedDatetime(datetime):
    @classmethod
    def now(cls,tz=None): return cls(2026,11,7,4,30,tzinfo=timezone.utc)


class ArtificialPackage:
    """Explicit test-injected source-nature allowance; no production admission."""
    def __init__(self,payloads=None):
        self.stack=ExitStack(); self.root=Path(self.stack.enter_context(TemporaryDirectory()))
        repo=Path(__file__).resolve().parents[2]
        subprocess.run(['git','init','--quiet','--initial-branch='+a.BRANCH],cwd=self.root,check=True,capture_output=True)
        self.config=json.loads((repo/a.PM_INPUTS['pm_policy']).read_bytes())
        self.family=json.loads((repo/a.PM_INPUTS['family_scheduler']).read_bytes())
        self.workstations=json.loads((repo/a.PM_INPUTS['workstations']).read_bytes())
        for r in self.config['required_reading']: self.write(r['path'],b'artificial protocol text only\n')
        for p in a.IMPLEMENTATION: self.write(p,(repo/p).read_bytes())
        for k,v in [('pm_policy',self.config),('family_scheduler',self.family),('workstations',self.workstations)]:
            self.write(a.PM_INPUTS[k],a.canonical(v))
        self.write(a.PM_INPUTS['campaign'],a.canonical(dict(campaign_id='quant_manager_72h_20261106',status='active',
            task_branch=a.BRANCH,machine='office_desktop',started_at='2026-11-06T16:21:39Z',delivery_deadline='2026-11-09T16:21:39Z',
            finite_preregistered_studies_required=True,old_consumed_scopes_remain_closed=True,
            holdout_unsealing_authorized=False,live_boundary_allowed=False)))
        payloads=dict(payloads or {}); daily=[]; monthly=[]
        ranges=[('2018-01-01','2018-01-01'),('2018-01-02','2018-12-31')]+[(f'{y}-01-01',f'{y}-12-31') for y in range(2019,2024)]+[('2024-01-01','2024-01-01')]
        for i,(first,last) in enumerate(ranges):
            role=f'daily_{i}'; receipt=role+'_receipt'
            daily.append(dict(role=role,receipt_role=receipt,first=first,last=last,received_at_path=['completed_at'],receipt_clock_kind='source_capture_completed_at'))
            payloads.setdefault(role,b'{}'); payloads.setdefault(receipt,a.canonical(dict(artificial=True,completed_at='2025-02-01T00:00:00Z')))
        for y in range(2019,2025):
            for m in range(1,13):
                if (y,m)>(2024,1): break
                month=f'{y}-{m:02}'; role='minute_'+month
                monthly.append(dict(month=month,zip_role=role,checksum_role=role+'_checksum',receipt_role=role+'_receipt',
                    received_at_path=['completed_at'],receipt_clock_kind='source_capture_completed_at'))
                for key,default in [(role,b'not a market archive'),(role+'_checksum',b'artificial'),(role+'_receipt',a.canonical(dict(artificial=True,completed_at='2025-02-01T00:00:00Z')))]:
                    payloads.setdefault(key,default)
        for role in a.CORE_ROLES: payloads.setdefault(role,a.canonical(dict(artificial=True,role=role)))
        rows=[]
        for role,raw in sorted(payloads.items()):
            path='data/artificial/'+role+'.bin'; self.write(path,raw)
            rows.append(dict(role=role,path=path,sha256=a.digest(raw),bytes=len(raw)))
        method=next(r['sha256'] for r in rows if r['role']=='method')
        self.manifest=dict(artifact_type='spot_macd_transfer_input_manifest_v1',method_sha256=method,policy=a.POLICY,
            source_nature='artificial_protocol_fixture',study_number=999999,input_count=len(rows),inputs=rows,daily_sources=daily,minute_sources=monthly)
        self.write(a.MANIFEST,a.canonical(self.manifest))
        self.stack.enter_context(patch.object(a,'METHOD_SHA',method))
        self.stack.enter_context(patch.object(a,'MANIFEST_SHA',a.file_digest(self.root/a.MANIFEST)))
        self.stack.enter_context(patch.object(a,'datetime',FixedDatetime))
        self.original_manifest_validator=a._manifest_inputs
        # The only source-authority bypass is visible here, confined to a temp
        # project and an artificial marker. The real validator rejects it.
        self.stack.enter_context(patch.object(a,'_manifest_inputs',side_effect=lambda r,m:self.original_manifest_validator(r,m,allow_artificial=True)))
        runtime=a.runtime_environment
        self.stack.enter_context(patch.object(a,'runtime_environment',side_effect=lambda:{**runtime(),'python':'3.12.13',
            'dependencies':{'numpy':'2.4.6','pandas':'3.0.3'}}))
        self.packet=a.build_registration(self.root); self.write(a.REGISTRATION,a.canonical(self.packet))
        for path,reviewer in ((a.REVIEW,'quant_manager_72h'),(a.ROOT_REVIEW,'root')):
            self.write(path,a.canonical(dict(status='accepted_for_one_conditional_spot_transfer',reviewer=reviewer,
                registration_sha256=self.packet['registration_sha256'],financial_execution_authorized=True,qualified=False,real_forward_days_added=0,
                artificial_test_injected=True)))
        self.write(a.COMPARISON,a.canonical(dict(status='accepted_fixed_spot_comparison',reviewer='root',
            registration_sha256=self.packet['registration_sha256'],method_sha256=a.METHOD_SHA,policy=a.POLICY,
            inputs_sha256=a.digest(a.canonical(self.packet['inputs'])),implementation_sha256=a.digest(a.canonical(self.packet['implementation'])),
            environment_sha256=a.digest(a.canonical(self.packet['environment'])),holding_control_tested=True,
            holding_policy=a.POLICY['holding_policy'],uninterrupted_passive_holding_tested=False,
            comparison_purpose=a.POLICY['comparison_purpose'],alpha_or_promotion_eligible=False)))
        self.write(a.ADMISSION,a.canonical(dict(artifact_type='spot_macd_transfer_admission_v1',status='authorized_once',
            registration=self.ref(a.REGISTRATION),review=self.ref(a.REVIEW),root_review=self.ref(a.ROOT_REVIEW),comparison=self.ref(a.COMPARISON),policy=a.POLICY)))

    def close(self): self.stack.close()
    def write(self,path,raw):
        target=self.root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    def ref(self,path): return dict(path=path,sha256=a.file_digest(self.root/path))
    def gate(self):
        gate=pm.build_quant_pm_startup_gate(gate_config=self.config,workstations_config=self.workstations,family_config=self.family,
            repo_root=self.root,machine='office_desktop',task='factor_review',branch=a.BRANCH,current_branch=a.BRANCH)
        gate['generated_at']=FixedDatetime.now().isoformat(); return gate
    def execute(self):
        return a.execute_once(self.root,expected_registration_sha256=self.packet['registration_sha256'],gate_supplier=self.gate)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=ArtificialPackage(); self.addCleanup(self.f.close)

    def test_real_PM_scope_comparison_and_artificial_source_rejection(self):
        with self.assertRaises(ValueError): self.f.original_manifest_validator(self.f.root,self.f.manifest)
        gate=self.f.gate()
        self.assertEqual(gate['status'],'ready',gate['blockers']);self.assertEqual(gate['mode'],a.MODE)
        self.assertTrue(gate['safety']['spot_macd_transfer_allowed']);self.assertFalse(gate['safety']['factor_batch_allowed'])
        self.assertEqual(gate['account_comparison']['strategy_accounts'],9)
        self.assertFalse(gate['account_comparison']['uninterrupted_passive_holding_tested'])
        self.assertFalse(gate['account_comparison']['alpha_or_promotion_eligible'])

    def test_noncampaign_scope_has_no_path_reads(self):
        with patch.object(Path,'exists',side_effect=AssertionError('exists')),patch.object(Path,'read_bytes',side_effect=AssertionError('read')):
            self.assertIsNone(a.scope('factor_review',{}, {},root=self.f.root,branch='codex/unrelated'))

    def test_verifier_code_and_direct_tests_are_frozen_before_claim(self):
        for name in ('src/quant_robot/research/spot_macd_transfer_verification.py',
                     'tests/unit/test_spot_macd_transfer_verification.py'):
            with self.subTest(name=name):
                self.assertIn(name,a.IMPLEMENTATION)
                path=self.f.root/name;raw=path.read_bytes();path.write_bytes(raw+b'\n# artificial drift\n')
                try:
                    with self.assertRaisesRegex(ValueError,'Bound file changed'):self.f.execute()
                finally:path.write_bytes(raw)
                self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_orphan_normalized_input_or_missing_review_blocks_before_claim(self):
        self.f.write(a.DIRECTORY+'/decoded_input.json',b'artificial orphan')
        with patch('quant_robot.research.spot_macd_transfer_historical.run_claimed_diagnostic') as run:
            with self.assertRaisesRegex(ValueError,'reserved or consumed'): self.f.execute()
            run.assert_not_called()
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())
        (self.f.root/a.DIRECTORY/'decoded_input.json').unlink();(self.f.root/a.ROOT_REVIEW).unlink()
        with self.assertRaises(OSError):self.f.execute()

    def test_full_context_source_and_expiration_are_guarded(self):
        saved=getcontext().copy()
        try:
            getcontext().rounding=ROUND_DOWN
            with self.assertRaisesRegex(ValueError,'numeric runtime'):self.f.execute()
        finally:setcontext(saved)
        class Expired(FixedDatetime):
            @classmethod
            def now(cls,tz=None):return cls(2026,11,10,tzinfo=timezone.utc)
        with patch.object(a,'datetime',Expired),self.assertRaisesRegex(ValueError,'Active fixed campaign'):self.f.execute()
        self.f.write(self.f.packet['inputs']['daily_0']['path'],b'changed original')
        with self.assertRaisesRegex(ValueError,'Source size|Bound file'):self.f.execute()
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_claim_precedes_decode_failed_attempt_is_not_resumed_or_called_real(self):
        def fail(claim):
            self.assertTrue((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())
            self.assertFalse((self.f.root/a.DIRECTORY/'financial_decode_started.json').exists())
            claim.begin_financial_decode();raise ValueError('artificial parse failure')
        with patch('quant_robot.research.spot_macd_transfer_historical.run_claimed_diagnostic',side_effect=fail) as run:
            with self.assertRaisesRegex(ValueError,'artificial parse'):self.f.execute()
            with self.assertRaisesRegex(ValueError,'reserved or consumed'):self.f.execute()
            self.assertEqual(run.call_count,1)
        out=json.loads((self.f.root/a.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(out['status'],'failed_consumed');self.assertTrue(out['numerical_decode_started'])
        for k in ('financial_decode_started','historical_returns_computed','research_study_consumed'):self.assertFalse(out[k])
        self.assertIsNone(out['study_number'])

    def test_after_claim_branch_change_cannot_get_reauthorized(self):
        def fail(claim):
            self.assertIsNone(a.scope('factor_review',self.f.family,{'blockers':['insufficient_active_research_families'],
                'summary':{'primary_budget_share':0,'active_primary_families':0}},root=self.f.root,branch=a.BRANCH))
            subprocess.run(['git','symbolic-ref','HEAD','refs/heads/codex/changed'],cwd=self.f.root,check=True,capture_output=True)
            claim.guard('before','changed')
        with patch('quant_robot.research.spot_macd_transfer_historical.run_claimed_diagnostic',side_effect=fail):
            with self.assertRaisesRegex(ValueError,'branch changed'):self.f.execute()


if __name__=='__main__':unittest.main()
