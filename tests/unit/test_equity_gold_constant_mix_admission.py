import copy
import json
import sys
import unittest
from datetime import datetime, timezone
from decimal import getcontext, ROUND_DOWN, InvalidOperation
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from quant_robot.research import equity_gold_constant_mix_admission as a


class FixedAdmissionTime(datetime):
    @classmethod
    def now(cls,tz=None):
        value=datetime(2026,11,7,9,30,tzinfo=timezone.utc)
        return value if tz is None else value.astimezone(tz)


class ExpiredAdmissionTime(datetime):
    @classmethod
    def now(cls,tz=None):
        value=datetime(2026,11,9,16,21,39,tzinfo=timezone.utc)
        return value if tz is None else value.astimezone(tz)


class AdmissionTests(unittest.TestCase):
    def test_wrong_task_branch_before_any_path_read(self):
        with mock.patch.object(a,'resolve_path',side_effect=AssertionError('path access')):
            self.assertIsNone(a.scope('project_sync',{}, {},root='unread',branch=a.BRANCH))
            self.assertIsNone(a.scope('factor_review',{}, {},root='unread',branch='codex/pm-review'))
    def test_no_final_manifest_pin_closes_fingerprint(self):
        with mock.patch.object(a,'MANIFEST_SHA',None),\
             mock.patch.object(a,'read_bound',side_effect=AssertionError('source read')):
            with self.assertRaisesRegex(ValueError,'not frozen'):a.build_registration('unread')
    def test_snapshot_residue_blocks_before_attempt(self):
        with TemporaryDirectory() as td:
            target=Path(td)/a.DIRECTORY/'decoded_input.json';target.parent.mkdir(parents=True);target.write_text('{}')
            with self.assertRaisesRegex(ValueError,'consumed'):a.require_unused(td)
            self.assertFalse((target.parent/'attempt_claim.json').exists())
    def test_full_context_binding_and_ambient_flags_exclusion(self):
        ctx=getcontext();before=ctx.copy();base=a.runtime_environment()
        try:
            ctx.flags[InvalidOperation]=not ctx.flags[InvalidOperation]
            self.assertEqual(base,a.runtime_environment())
            ctx.rounding=ROUND_DOWN
            self.assertNotEqual(base,a.runtime_environment())
            ctx.rounding=before.rounding;ctx.traps[InvalidOperation]=not ctx.traps[InvalidOperation]
            self.assertNotEqual(base,a.runtime_environment())
        finally:
            from decimal import setcontext
            setcontext(before)
    def test_canonical_unicode_matches_kernel_definition_without_import(self):
        self.assertEqual(a.canonical({'x':'份'}),'{"x":"份"}'.encode())
    def test_exact_path_hash_and_no_outside_root(self):
        with TemporaryDirectory() as td:
            p=Path(td)/'a.json';p.write_bytes(b'{}')
            a.read_bound(td,dict(path='a.json',sha256=a.file_digest(p)))
            for path in ('../a.json',str(p.resolve())):
                with self.assertRaises(ValueError):a.read_bound(td,dict(path=path,sha256=a.file_digest(p)))
            p.write_bytes(b'[]')
            with self.assertRaisesRegex(ValueError,'Frozen file'):a.read_bound(td,dict(path='a.json',sha256=a.digest(b'{}')))
    @mock.patch.object(a,'datetime',FixedAdmissionTime)
    def test_attempt_failure_vs_decode_failure_and_no_resume(self):
        for enter_parser in (False,True):
            with self.subTest(enter_parser=enter_parser),TemporaryDirectory() as td:
                root=Path(td).resolve();conf=root/a.ADMISSION;conf.parent.mkdir(parents=True);conf.write_bytes(b'{}')
                packet=dict(registration_sha256='c'*64,policy=dict(a.POLICY,study_number=999));approval={}
                def admit(root,**kwargs):
                    if kwargs.get('require_unused',True):a.require_unused(root)
                    return packet,approval
                gate=dict(generated_at=FixedAdmissionTime.now(timezone.utc).isoformat(),status='ready',blockers=[],mode=a.MODE,
                    primary_market='CN_ETF',selected=dict(machine='office_desktop',task='factor_review',branch=a.BRANCH,current_branch=a.BRANCH),
                    safety=dict(constant_mix_allowed=True,constant_mix_scope=a._scope(packet,root),
                                factor_batch_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False))
                def fail(claim):
                    self.assertTrue((root/a.DIRECTORY/'attempt_claim.json').exists())
                    if enter_parser:claim.begin_financial_decode()
                    raise ValueError('artificial transport/parser failure')
                with mock.patch.object(a,'admitted_packet',side_effect=admit),mock.patch.object(a._Claim,'guard'),\
                     mock.patch('quant_robot.research.equity_gold_constant_mix_historical.run_claimed_diagnostic',side_effect=fail):
                    with self.assertRaises(ValueError):a.execute(root,expected_registration_sha256='c'*64,gate_supplier=lambda:gate)
                    with self.assertRaisesRegex(ValueError,'consumed'):a.execute(root,expected_registration_sha256='c'*64,gate_supplier=lambda:gate)
                outcome=json.loads((root/a.DIRECTORY/'outcome.json').read_bytes())
                self.assertEqual(outcome['financial_decode_started'],enter_parser)
                self.assertEqual(outcome['research_study_consumed'],enter_parser)
                self.assertEqual(outcome['status'],'failed_consumed')
                self.assertFalse(outcome['historical_returns_computed'])
    @mock.patch.object(a,'datetime',FixedAdmissionTime)
    @mock.patch.object(a.platform,'python_version',return_value='3.12.13')
    def test_pure_hash_registration_admission_scope_and_environment_recheck(self,_python_version):
        # A temporary metadata-only packet: no market raw, no parser, no claim.
        with TemporaryDirectory() as td:
            root=Path(td).resolve()
            def put(path,value):
                file=root/path;file.parent.mkdir(parents=True,exist_ok=True)
                file.write_bytes((json.dumps(value)+'\n').encode())
                return dict(path=path,sha256=a.file_digest(file),bytes=file.stat().st_size)
            rows=[]
            for role in sorted(a.CORE_ROLES):
                value=dict(test_metadata_only=True,role=role)
                if role=='relocations':value=dict(artifact_type='constant_mix_exact_source_relocations_v1',mappings=[])
                rows.append(dict(role=role,**put('inputs/'+role+'.json',value)))
            pins={r['role']:r for r in rows}
            for role,path in a.PM_INPUTS.items():
                value={}
                if role=='campaign':value=dict(campaign_id='quant_manager_72h_20261106',status='active',task_branch=a.BRANCH,
                    machine='office_desktop',started_at='2026-11-06T16:21:39Z',delivery_deadline='2026-11-09T16:21:39Z',
                    finite_preregistered_studies_required=True,old_consumed_scopes_remain_closed=True,
                    holdout_unsealing_authorized=False,live_boundary_allowed=False)
                put(path,value)
            put('code.py',dict(test_code_fingerprint_only=True))
            manifest=dict(artifact_type='constant_mix_historical_input_manifest_v1',method_sha256=pins['method']['sha256'],
                exit_fee_addendum_sha256=pins['exit_fee_addendum']['sha256'],source_nature=a.SOURCE,
                input_count=len(rows),inputs=rows,study_number=999)
            ref=put(a.MANIFEST,manifest)
            def short(ref):return {k:ref[k] for k in ('path','sha256')}
            with mock.patch.multiple(a,MANIFEST_SHA=ref['sha256'],METHOD_SHA=pins['method']['sha256'],
                    EXIT_FEE_SHA=pins['exit_fee_addendum']['sha256'],CODE_FILES=('code.py',)):
                packet=a.build_registration(root);registration=put(a.REGISTRATION,packet)
                refs={}
                for key,reviewer,path in (('review','quant_manager_72h',a.REVIEW),('root_review','root',a.ROOT_REVIEW)):
                    refs[key]=short(put(path,dict(status='accepted_for_one_conditional_constant_mix',reviewer=reviewer,
                        registration_sha256=packet['registration_sha256'],qualified=False,real_forward_days_added=0,
                        financial_execution_authorized=True,test_metadata_only=True)))
                comparison=put(a.COMPARISON,dict(artifact_type='constant_mix_comparison_review_v1',status='accepted_specification_only',
                    registration_sha256=packet['registration_sha256'],strategy_accounts=9,drift_controls=9,cash_controls=9,
                    same_actual_initial_basket_required=True,comparison_purpose=a.POLICY['comparison_purpose'],
                    alpha_or_promotion_eligible=False,qualified=False))
                put(a.ADMISSION,dict(artifact_type='constant_mix_admission_v1',status='authorized_once',
                    registration=short(registration),**refs,comparison=short(comparison),policy=packet['policy']))
                accepted,_=a.admitted_packet(root);self.assertEqual(accepted,packet)
                scope=a.scope('factor_review',{},dict(blockers=['insufficient_active_research_families'],
                    summary=dict(primary_budget_share=0,active_primary_families=0)),root=root,branch=a.BRANCH)
                self.assertEqual(scope['mode'],a.MODE)
                self.assertEqual(a.review_comparison(root,scope['scope'])['status'],'passed_specification_only')
                self.assertFalse((root/a.DIRECTORY/'attempt_claim.json').exists())
                with mock.patch.object(a,'datetime',ExpiredAdmissionTime):
                    with self.assertRaisesRegex(ValueError,'Active campaign'):
                        a.admitted_packet(root)
                self.assertFalse((root/a.DIRECTORY/'attempt_claim.json').exists())
                with mock.patch.object(a.platform,'python_version',return_value='3.13.0'):
                    with self.assertRaisesRegex(ValueError,'environment'):
                        a.validate_registration(packet,root)
                context=getcontext();old=context.rounding
                try:
                    context.rounding=ROUND_DOWN
                    with self.assertRaisesRegex(ValueError,'environment'):a.validate_registration(packet,root)
                finally:context.rounding=old
                (root/pins['actions']['path']).write_bytes(b'{}')
                with self.assertRaisesRegex(ValueError,'size changed'):a.validate_registration(packet,root)

    def test_production_claim_cannot_be_fabricated_from_test_label(self):
        with self.assertRaisesRegex(ValueError,'durable'):a._Claim(None,None,None,None,object())

    @mock.patch.object(a,'datetime',FixedAdmissionTime)
    def test_final_result_anchors_prewrite_bytes_and_rejects_same_length_mutation(self):
        for mutate in (False,True):
            with self.subTest(mutate=mutate),TemporaryDirectory() as td:
                root=Path(td).resolve();conf=root/a.ADMISSION
                conf.parent.mkdir(parents=True);conf.write_bytes(b'{}')
                packet=dict(registration_sha256='c'*64,policy=dict(a.POLICY,study_number=999))
                def admit(root,**kwargs):
                    if kwargs.get('require_unused',True):a.require_unused(root)
                    return packet,{}
                gate=dict(generated_at=FixedAdmissionTime.now(timezone.utc).isoformat(),status='ready',
                    blockers=[],mode=a.MODE,primary_market='CN_ETF',
                    selected=dict(machine='office_desktop',task='factor_review',branch=a.BRANCH,current_branch=a.BRANCH),
                    safety=dict(constant_mix_allowed=True,constant_mix_scope=a._scope(packet,root),
                        factor_batch_allowed=False,final_holdout_allowed=False,live_boundary_allowed=False))
                # Only the outer publication route is exercised. These values,
                # production-shaped identity and claim are explicit test injection.
                intended=dict(artifact_type='conditional_historical_constant_mix_matrix_v1',
                    registration_sha256='c'*64,source_nature=a.SOURCE,qualified=False,real_forward=0,
                    historical_returns_computed=True,test_injected_values=False,
                    artificial_test_marker='10000',unicode_marker='份')
                expected=a._persisted_json_bytes(intended)
                writer=a.write_exclusive_json
                def write(path,value):
                    writer(path,value)
                    if mutate and path.name=='result.json':
                        raw=path.read_bytes();changed=raw.replace(b'10000',b'00000')
                        self.assertEqual(len(raw),len(changed));self.assertNotEqual(raw,changed)
                        path.write_bytes(changed)
                def artificial_run(claim):
                    self.assertTrue((root/a.DIRECTORY/'attempt_claim.json').exists())
                    claim.begin_financial_decode()
                    return intended
                with mock.patch.object(a,'admitted_packet',side_effect=admit),\
                     mock.patch.object(a._Claim,'guard'),mock.patch.object(a,'_final_artifacts'),\
                     mock.patch.object(a,'write_exclusive_json',side_effect=write),\
                     mock.patch('quant_robot.research.equity_gold_constant_mix_historical.run_claimed_diagnostic',side_effect=artificial_run):
                    if mutate:
                        with self.assertRaisesRegex(ValueError,'pre-write intended bytes'):
                            a.execute(root,expected_registration_sha256='c'*64,gate_supplier=lambda:gate)
                    else:
                        result=a.execute(root,expected_registration_sha256='c'*64,gate_supplier=lambda:gate)
                        self.assertEqual(result['result_sha256'],a.digest(expected))
                outcome=json.loads((root/a.DIRECTORY/'outcome.json').read_bytes())
                self.assertTrue(outcome['research_study_consumed'])
                self.assertEqual(outcome['status'],'failed_consumed' if mutate else 'completed_conditional_accounts')
                if mutate:
                    self.assertNotIn('result_sha256',outcome)
                    self.assertNotEqual((root/a.DIRECTORY/'result.json').read_bytes(),expected)
                else:
                    self.assertEqual((root/a.DIRECTORY/'result.json').read_bytes(),expected)
                    self.assertEqual(outcome['result_sha256'],a.digest(expected))


if __name__=='__main__':unittest.main()
