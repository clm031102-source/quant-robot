"""Artificial temporary repositories; no retained financial original is decoded."""
from __future__ import annotations

from contextlib import ExitStack
from decimal import getcontext, ROUND_DOWN
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from quant_robot.research import crypto_charge_monthly_admission as a
from quant_robot.research import pm_startup_gate as pm
from tests.unit.test_crypto_monthly_admission import PreparedFixture as LegacyFixture, FixedDatetime


class PreparedFixture:
    """Own independent new approval; the artificial old19 is already consumed."""
    def __init__(self,source_payloads=None):
        self.legacy=LegacyFixture(source_payloads)
        self.stack=ExitStack(); self.stack.callback(self.legacy.close)
        self.root=self.legacy.root
        self.config,self.family,self.workstations=self.legacy.config,self.legacy.family,self.legacy.workstations
        repo=Path(__file__).resolve().parents[2]
        for path in a.IMPLEMENTATION: self.write(path,(repo/path).read_bytes())
        old=self.legacy.packet
        preserve={
            'legacy_registration':old,
            'legacy_claim':{'registration_sha256':old['registration_sha256']},
            'legacy_outcome':{'registration_sha256':old['registration_sha256'],'status':'failed_consumed','financial_decode_started':True},
            'legacy_decode_marker':{'registration_sha256':old['registration_sha256'],'study_number':19},
            'legacy_D_archive_receipt':{'all_source_archive_restore_hashes_match':True,
                'source_files':{name:ref['sha256'] for name,ref in old['implementation'].items()}},
        }
        copies={}
        names={'prechange_model':'crypto_carry_model.py','prechange_scheduler':'crypto_carry_scheduler.py',
               'prechange_driver':'crypto_carry_driver.py','prechange_monthly':'crypto_monthly_diagnostic.py'}
        for role,name in names.items():
            source='src/quant_robot/research/'+name
            body=(self.root/source).read_bytes()
            self.write(a.EXTRA_INPUTS[role],body)
            copies[name]={'source':source,'sha256':a.digest(body),'bytes':len(body)}
        preserve['prechange_runtime_manifest']={'files':copies}
        for role,path in a.EXTRA_INPUTS.items():
            if role in names or role=='legacy_input_manifest': continue
            self.write(path,a.canonical(preserve.get(role,{'invented_metadata':True,'role':role})))
        legacy_manifest=json.loads((self.root/a.EXTRA_INPUTS['legacy_input_manifest']).read_bytes())
        rows=list(legacy_manifest['inputs'])
        for role,path in a.EXTRA_INPUTS.items():
            target=self.root/path
            rows.append({'role':role,'path':str(target),'sha256':a.file_digest(target),'bytes':target.stat().st_size})
        method=a.file_digest(self.root/a.EXTRA_INPUTS['new_monthly_method'])
        manifest={'artifact_type':'conditional_crypto_charge_monthly_input_manifest_v1','method_sha256':method,
                  'input_count':len(rows),'inputs':rows}
        self.write(a.MANIFEST,a.canonical(manifest))
        self.stack.enter_context(patch.object(a,'METHOD_SHA',method))
        self.stack.enter_context(patch.object(a,'MANIFEST_SHA',a.file_digest(self.root/a.MANIFEST)))
        self.stack.enter_context(patch.object(a,'LEGACY_MANIFEST_SHA',a.file_digest(self.root/a.EXTRA_INPUTS['legacy_input_manifest'])))
        self.stack.enter_context(patch.object(a,'datetime',FixedDatetime))
        runtime=a.runtime_environment
        self.stack.enter_context(patch.object(a,'runtime_environment',side_effect=lambda:{**runtime(),'python':'3.12.13'}))
        self.packet=a.build_registration(self.root)
        self.write(a.REGISTRATION,a.canonical(self.packet))
        for path,reviewer in ((a.REVIEW,'quant_manager_72h'),(a.ROOT_REVIEW,'root')):
            self.write(path,a.canonical({'status':'accepted_for_one_conditional_crypto_charge_month',
                'reviewer':reviewer,'registration_sha256':self.packet['registration_sha256'],
                'financial_execution_authorized':True,'qualified':False,'real_forward_days_added':0}))
        self.approval={'artifact_type':'crypto_charge_monthly_conditional_admission_v1','status':'authorized_once',
            'registration':self.ref(a.REGISTRATION),'review':self.ref(a.REVIEW),'root_review':self.ref(a.ROOT_REVIEW),
            'policy':a.POLICY}
        self.write(a.ADMISSION,a.canonical(self.approval))

    def close(self): self.stack.close()
    def write(self,path,body):
        target=self.root/path; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(body)
    def ref(self,path): return {'path':path,'sha256':a.file_digest(self.root/path)}
    def gate(self):
        gate=pm.build_quant_pm_startup_gate(gate_config=self.config,workstations_config=self.workstations,
            family_config=self.family,repo_root=self.root,machine='office_desktop',task='factor_review',
            branch=a.BRANCH,current_branch=a.BRANCH)
        gate['generated_at']=FixedDatetime.now().isoformat()
        return gate
    def execute(self):
        return a.execute(self.root,expected_registration_sha256=self.packet['registration_sha256'],gate_supplier=self.gate)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.f=PreparedFixture(); self.addCleanup(self.f.close)

    def test_real_new_pm_route_with_old_consumed_scope_and_no_decode(self):
        with patch('quant_robot.research.crypto_charge_monthly_historical.load_claimed_month') as decoder:
            gate=self.f.gate()
            self.assertEqual(gate['status'],'ready',gate['blockers'])
            self.assertEqual(gate['mode'],a.MODE)
            self.assertTrue(gate['safety']['crypto_charge_monthly_allowed'])
            self.assertFalse(gate['safety']['crypto_monthly_10_account_allowed'])
            self.assertFalse(gate['account_comparison']['holding_control_tested'])
            self.assertFalse(gate['account_comparison']['alpha_or_promotion_eligible'])
            self.assertEqual(gate['safety']['crypto_charge_monthly_scope']['policy']['consumed_study_number'],20)
            decoder.assert_not_called()

    def test_old_admission_and_old_failure_do_not_open_missing_new_admission(self):
        (self.f.root/a.ADMISSION).unlink()
        with self.assertRaises(OSError): self.f.execute()
        self.assertNotEqual(self.f.gate()['mode'],a.MODE)
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_preserved_original28_cannot_be_replaced_even_with_new_file_hash(self):
        manifest=json.loads((self.f.root/a.MANIFEST).read_bytes())
        row=next(r for r in manifest['inputs'] if r['role']=='funding_raw_MCP')
        self.f.write('data/fabricated/replacement.json',b'{}')
        row.update(path=str(self.f.root/'data/fabricated/replacement.json'),sha256=a.digest(b'{}'),bytes=2)
        with self.assertRaisesRegex(ValueError,'Original28 source reference'):
            a._manifest_inputs(self.f.root,manifest)

    def test_old_registration_does_not_revalidate_old_current_code_hashes(self):
        # Current new PM implementation legitimately differs from old-record
        # code; its historical pins are checked against the retained receipt.
        self.assertNotIn('crypto_charge_monthly_admission.py',str(self.f.legacy.packet['implementation']))
        self.assertEqual(a.validate_registration(self.f.packet,self.f.root),self.f.packet)

    def test_corrupted_old_failure_or_backup_chain_is_rejected(self):
        pins=self.f.packet['inputs']
        for role,obj in (
            ('legacy_outcome',{'registration_sha256':'0'*64,'status':'failed_consumed','financial_decode_started':True}),
            ('legacy_D_archive_receipt',{'all_source_archive_restore_hashes_match':False,'source_files':{}})):
            with self.subTest(role=role):
                changed=dict(pins)
                original=(self.f.root/pins[role]['path']).read_bytes()
                self.f.write(pins[role]['path'],a.canonical(obj)); changed[role]=self.f.ref(pins[role]['path'])
                with self.assertRaises(ValueError): a._validate_predecessor(self.f.root,changed)
                self.f.write(pins[role]['path'],original)

    def test_changed_source_or_decimal_context_blocks_before_claim(self):
        context=getcontext(); saved=context.copy()
        try:
            context.rounding=ROUND_DOWN
            with self.assertRaisesRegex(ValueError,'environment'): self.f.execute()
        finally: __import__('decimal').setcontext(saved)
        target=self.f.root/self.f.packet['inputs']['spot_1m_zip']['path']
        with target.open('ab') as stream: stream.write(b'changed')
        with self.assertRaises(ValueError): self.f.execute()
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())

    def test_wrong_scope_or_expired_campaign_blocks(self):
        packet=json.loads(a.canonical(self.f.packet)); packet['policy']['funding_mode']='event_mark_legacy'
        packet['registration_sha256']=a.digest(a.canonical({k:v for k,v in packet.items() if k!='registration_sha256'}))
        with self.assertRaisesRegex(ValueError,'fixed-month'): a.validate_registration(packet,self.f.root)
        class Expired(FixedDatetime):
            @classmethod
            def now(cls,tz=None): return cls(2026,11,10,tzinfo=__import__('datetime').timezone.utc)
        with patch.object(a,'datetime',Expired),self.assertRaisesRegex(ValueError,'Active campaign'):
            self.f.execute()

    def test_claim_precedes_decode_and_failure_is_consumed_without_resume(self):
        seen=[]
        def fail(claim):
            self.assertTrue((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())
            self.assertFalse((self.f.root/a.DIRECTORY/'financial_decode_started.json').exists())
            claim.begin_financial_decode()
            self.assertTrue((self.f.root/a.DIRECTORY/'financial_decode_started.json').exists())
            seen.append(claim); raise ValueError('invented_failure_after_decode_marker')
        with patch('quant_robot.research.crypto_charge_monthly_historical.run_claimed_month',side_effect=fail) as worker:
            with self.assertRaisesRegex(ValueError,'invented_failure'): self.f.execute()
            with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()
            self.assertEqual(worker.call_count,1)
        outcome=json.loads((self.f.root/a.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(outcome['study_number'],20); self.assertTrue(outcome['research_study_consumed'])
        with self.assertRaisesRegex(ValueError,'not opened'): seen[0].read('spot_1m_zip')

    def test_failure_before_decode_retains_claim_without_counting_new_study(self):
        with patch.object(a._Claim,'guard',side_effect=ValueError('invented_pre_decode_guard_failure')):
            with self.assertRaisesRegex(ValueError,'pre_decode'): self.f.execute()
        outcome=json.loads((self.f.root/a.DIRECTORY/'outcome.json').read_bytes())
        self.assertFalse(outcome['financial_decode_started']); self.assertFalse(outcome['research_study_consumed'])
        self.assertNotIn('study_number',outcome)
        with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()

    def test_source_preparation_failure_after_first_guard_does_not_count_study20(self):
        def preparation(claim):
            claim.guard('before','source_decode')
            self.assertTrue(claim.read('time_projection_result'))
            raise ValueError('invented_metadata_failure_before_parser')
        with patch('quant_robot.research.crypto_charge_monthly_historical.run_claimed_month',side_effect=preparation):
            with self.assertRaisesRegex(ValueError,'metadata_failure'): self.f.execute()
        outcome=json.loads((self.f.root/a.DIRECTORY/'outcome.json').read_bytes())
        self.assertFalse(outcome['financial_decode_started']); self.assertFalse(outcome['research_study_consumed'])
        self.assertFalse((self.f.root/a.DIRECTORY/'financial_decode_started.json').exists())
        with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()

    def test_partial_claim_and_missing_root_review_are_closed(self):
        self.f.write(a.DIRECTORY+'/attempt_claim.json',b'{')
        with self.assertRaisesRegex(ValueError,'consumed'): self.f.execute()
        (self.f.root/a.ROOT_REVIEW).unlink()
        with self.assertRaises(OSError): self.f.execute()

    def test_gate_cannot_open_ordinary_holdout_or_live_or_use_legacy_mode(self):
        for key in ('factor_batch_allowed','final_holdout_allowed','live_boundary_allowed'):
            def gate():
                value=self.f.gate(); value['safety'][key]=True; return value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'Fresh exact'):
                a.execute(self.f.root,expected_registration_sha256=self.f.packet['registration_sha256'],gate_supplier=gate)
        self.assertFalse((self.f.root/a.DIRECTORY/'attempt_claim.json').exists())


if __name__=='__main__': unittest.main()
