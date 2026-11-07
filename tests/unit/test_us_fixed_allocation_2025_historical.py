"""Artificial controller evidence only; no actual sources, market values or strategy run."""
from __future__ import annotations
import json,tempfile,unittest
from datetime import datetime,timedelta,timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import ExitStack
from quant_robot.research import us_fixed_allocation_2025_historical as h

class USFixed2025HistoricalTests(unittest.TestCase):
    def test_exclusive_prewrite_anchor_unicode_and_postwrite_mutation(self):
        with tempfile.TemporaryDirectory() as d:
            r=h._persist(d,'data/good.json',{'text':'人工中文'})
            self.assertEqual(h._read(d,r),h.persisted_bytes({'text':'人工中文'}))
            with self.assertRaises(FileExistsError):h._persist(d,'data/good.json',{})
            original=h.U.write_exclusive_json
            def drift(p,x):
                original(p,x);p.write_bytes(p.read_bytes().replace(b'10',b'11'))
            with patch.object(h.U,'write_exclusive_json',side_effect=drift):
                with self.assertRaisesRegex(ValueError,'persisted_bytes_changed'):
                    h._persist(d,'data/bad.json',{'number':10})

    def packet(self):
        return {'registration_sha256':'a'*64,'policy':{'study_number':27},
                'input_manifest':{'path':'data/source_manifest.json','sha256':h.digest(b'{}')}}

    def admission_setup(self,root):
        p=self.packet();folder=root/h.DIRECTORY;folder.mkdir(parents=True)
        h.U.write_exclusive_json(folder/'registration.json',p)
        refs={}
        for name,reviewer in (('manager_review','quant_manager_72h'),('root_review','root')):
            x=dict(status='accepted_for_one_conditional_us_fixed_allocation_2025',reviewer=reviewer,
                   registration_sha256='a'*64,method_sha256=h.METHOD_SHA,qualified=False)
            h.U.write_exclusive_json(folder/(name+'.json'),x)
            refs[name]=h.U.file_digest(folder/(name+'.json'))
        t=datetime(2026,11,7,tzinfo=timezone.utc)
        release=dict(status='authorized_one_us_fixed_allocation_2025',registration_sha256='a'*64,
            manager_review_sha256=refs['manager_review'],root_review_sha256=refs['root_review'],
            max_executions=1,not_before=(t-timedelta(seconds=1)).isoformat(),expires_at=(t+timedelta(minutes=15)).isoformat())
        h.U.write_exclusive_json(folder/'release.json',release)
        return p,t

    def test_exact_two_review_release_expiry_and_consumed_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p,t=self.admission_setup(root)
            with patch.object(h,'validate_registration',return_value=p),patch.object(h,'_branch',return_value=h.BRANCH),patch.object(h,'now',return_value=t):
                got,refs=h.admitted(root)
                self.assertEqual(got,p);self.assertEqual(set(refs),{'manager_review','root_review','registration','release'})
                h.U.write_exclusive_json(root/h.DIRECTORY/'attempt_claim.json',{'artificial':True})
                with self.assertRaisesRegex(ValueError,'attempt_already_reserved'):h.admitted(root)
            (root/h.DIRECTORY/'attempt_claim.json').unlink()
            with patch.object(h,'validate_registration',return_value=p),patch.object(h,'_branch',return_value=h.BRANCH),patch.object(h,'now',return_value=t+timedelta(hours=1)):
                with self.assertRaisesRegex(ValueError,'exact_fresh_release'):h.admitted(root)

    def test_manager_root_roles_not_interchangeable(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p,t=self.admission_setup(root)
            file=root/h.DIRECTORY/'manager_review.json'
            x=json.loads(file.read_bytes());x['reviewer']='root';file.write_text(json.dumps(x))
            with patch.object(h,'validate_registration',return_value=p),patch.object(h,'_branch',return_value=h.BRANCH),patch.object(h,'now',return_value=t):
                with self.assertRaisesRegex(ValueError,'independent_review'):h.admitted(root)

    def test_gate_raw_and_normalized_hashes_and_future_or_stale_clock(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);raw=b'a\r\nb\r\n';(root/'protocol.md').write_bytes(raw)
            p={'protocols':{'protocol.md':{'path':'protocol.md','sha256':h.digest(raw)}}}
            t=datetime(2026,11,7,tzinfo=timezone.utc)
            gate={'status':'ready','selected':dict(machine='office_desktop',task='factor_review',current_branch=h.BRANCH,branch=h.BRANCH),
                  'generated_at':t.isoformat(),'required_reading':[{'path':'protocol.md','sha256':h.digest(b'a\nb\n')}],
                  'live_boundary_allowed':False}
            with patch.object(h,'now',return_value=t):
                h._gate(root,p,gate)
                for dt in (timedelta(seconds=1),timedelta(seconds=-121)):
                    gate['generated_at']=(t+dt).isoformat()
                    with self.assertRaisesRegex(ValueError,'fresh_PM'):h._gate(root,p,gate)
                gate['generated_at']=t.isoformat();gate['live_boundary_allowed']=True
                with self.assertRaisesRegex(ValueError,'PM_old_permissions_closed'):h._gate(root,p,gate)

    def test_numeric_marker_classification_and_no_rerun_after_failure(self):
        for decode in (False,True):
            with self.subTest(decode=decode),tempfile.TemporaryDirectory() as d:
                root=Path(d);p=self.packet()
                (root/'data').mkdir();(root/'data/source_manifest.json').write_bytes(b'{}')
                def loader(*args,**kwargs):
                    if decode:
                        marker=kwargs['before_numeric_decode']()
                        self.assertTrue(h.resolve_path(root,marker['path']).exists())
                    raise ValueError('artificial_pipeline_failure')
                with ExitStack() as stack:
                    stack.enter_context(patch.object(h,'admitted',return_value=(p,{})))
                    stack.enter_context(patch.object(h,'validate_registration',return_value=p))
                    stack.enter_context(patch.object(h,'_branch',return_value=h.BRANCH))
                    stack.enter_context(patch.object(h,'_gate'))
                    stack.enter_context(patch.object(h,'_financial_modules',return_value=(object(),SimpleNamespace(load_inputs=loader))))
                    with self.assertRaisesRegex(ValueError,'artificial_pipeline_failure'):
                        h.execute(root,expected_registration_sha256='a'*64,gate_supplier=lambda:{'artificial_gate':True})
                outcome=json.loads((root/h.DIRECTORY/'outcome.json').read_bytes())
                self.assertEqual(outcome['financial_decode_started'],decode)
                self.assertEqual(outcome['status'],'failed_consumed' if decode else 'failed_before_numeric_decode')
                self.assertEqual((root/h.DIRECTORY/'financial_decode_started.json').exists(),decode)
                with self.assertRaisesRegex(ValueError,'attempt_already_reserved'):h.require_unused(root)

    def test_module_origin_is_this_checkout(self):
        root=Path(__file__).resolve().parents[2]
        M,I=h._financial_modules(root)
        self.assertEqual(Path(M.__file__).resolve(),root/h.NEW_FILES[0])
        self.assertEqual(Path(I.__file__).resolve(),root/h.NEW_FILES[1])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'financial_module_origin'):h._financial_modules(d)

    def test_artificial_dependency_stubs_complete_3_manifest_without_strategy(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.packet()
            (root/'data').mkdir();(root/'data/source_manifest.json').write_bytes(b'{}')
            fixture={'schema':'artificial_controller_stub','provenance':{'constructed_from_market_data':False}}
            def loader(*args,**kw):
                kw['before_numeric_decode']();return fixture
            def run(prepared,role,*,context):
                minimum,slip={'primary':('1.00',10),'stress':('2.50',30),'cash':('0.35',0)}[role]
                return {'role':role,'policy':'cash' if role=='cash' else 'fixed_quarters',
                    'minimum_commission':minimum,'slippage_bps':slip,
                    'summary':{'artificial_dependency_stub':True},'annual_contributions':{'2025':'0'}}
            model=SimpleNamespace(_ExecutionContext=lambda *a:object(),digest=lambda x:h.digest(h.canonical(x)),
                prepare=lambda *a,**k:object(),run_prepared=run)
            with ExitStack() as stack:
                stack.enter_context(patch.object(h,'admitted',return_value=(p,{})))
                stack.enter_context(patch.object(h,'validate_registration',return_value=p))
                stack.enter_context(patch.object(h,'_branch',return_value=h.BRANCH))
                stack.enter_context(patch.object(h,'_gate'))
                stack.enter_context(patch.object(h,'_financial_modules',return_value=(model,SimpleNamespace(load_inputs=loader))))
                result=h.execute(root,expected_registration_sha256='a'*64,gate_supplier=lambda:{'artificial_gate':True})
            self.assertEqual(set(result['accounts']),{'primary','stress','cash'})
            cash=json.loads(h._read(root,result['accounts']['cash']['artifact']))
            self.assertEqual((cash['minimum_commission'],cash['slippage_bps']),('0.35',0))
            self.assertEqual(json.loads((root/h.DIRECTORY/'decoded_input.json').read_bytes()),fixture)
            for key,row in result['accounts'].items():
                self.assertEqual(json.loads(h._read(root,row['completion']))['account_id'],key)
                self.assertIn('summary',json.loads(h._read(root,row['artifact'])))
            outcome=json.loads((root/h.DIRECTORY/'outcome.json').read_bytes())
            self.assertEqual(outcome['result']['sha256'],h.U.file_digest(root/h.DIRECTORY/'result.json'))
            with self.assertRaises(ValueError):h.require_unused(root)

    def test_unfrozen_manifest_stops_before_reading_sources(self):
        with tempfile.TemporaryDirectory() as d,patch.object(h,'MANIFEST_SHA',None):
            with self.assertRaisesRegex(ValueError,'final_manifest_not_frozen'):h._inputs(Path(d))

if __name__=='__main__':unittest.main()

