"""Finite artificial capture -> source -> G1; no real requests or PM process."""
from copy import deepcopy
import json
import os
from pathlib import Path
from time import perf_counter
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_synthetic_capture_observe as pipeline
from quant_robot.ops import paper_prospective_transport as v1
from quant_robot.ops import paper_prospective_transport_v2 as v2
from quant_robot.ops import tushare_live_transport as archive
from quant_robot.ops import tushare_daily_receipt as parser
from tests.unit import test_frozen_candidate_deferred as fixtures
from tests.unit import test_paper_source_connection as source_fixtures
from tests.unit import test_paper_prospective_transport as v1_fixtures
from tests.unit import test_paper_prospective_transport_v2 as v2_fixtures


class SyntheticCaptureObserveTests(TestCase):
    probes=[]

    def fixture(self,deferred=True):
        case=source_fixtures.SourceConnectionTests();f=fixtures.G1Fixture(case,deferred=deferred)
        self.addCleanup(case.doCleanups);return f

    def ready(self):
        f=self.fixture();packet=f.packet(21);f.activate();f.decide(21)
        now=f.f.days[21]+'T08:02:00Z'
        context=dict(machine='office_desktop',task='factor_review',branch='codex/artificial-capture-proof')
        scope=pipeline.prepare_synthetic_scope(f.journal,evidence_root=f.root,context=context,now=now)['result']
        f.f.save('capture_scope.json',scope)
        spec=json.loads((f.root/packet['source_proof']['specification']['path']).read_bytes())
        del spec['evidence']['price'];f.f.save('capture_template.json',spec)
        body=json.dumps(dict(code=0,msg=None,data=dict(fields=list(parser.FIELDS),
            items=[['510300.SH',f.f.days[21].replace('-',''),20.3,21,20,20.3,1000,2030]]))).encode()
        return dict(f=f,packet=packet,scope=scope,now=now,template=f.ref('capture_template.json'),
            response=pipeline.SyntheticResponse(body),folder=f.root/v1.ARCHIVE/'mock_requests'/v1.request_identity(scope))

    def operation(self,case):return sessions.EvidenceOperation(case['f'].root,policy=sessions.G1_SYNTHETIC_POLICY)

    def call(self,case,operation=None):
        return pipeline.capture_observe_synthetic(case['f'].root/'capture_scope.json',evidence_root=case['f'].root,
            expected_scope_sha256=forward.digest(case['scope']),template_ref=case['template'],
            response=case['response'],now=case['now'],operation=operation)

    def meter(self,label,operation,counts,elapsed,**details):
        actual=operation.measurements()
        self.assertEqual(counts['opens'],actual['open_attempts'])
        self.assertEqual(counts['reads'],actual['read_calls'])
        self.assertEqual(counts['bytes'],actual['io_bytes_returned'])
        self.probes.append(dict(label=label,seconds=elapsed,external=dict(counts),internal=actual,**details))

    def test_complete_five_stages_one_mock_request_account_parity_and_full_meter(self):
        case=self.ready();f=case['f'];old=self.fixture(False)
        packet=old.packet(21);old.activate();old.decide(21)
        expected=old.observe(21,packet)['payload']['account']
        operation=self.operation(case);raw_account=forward.run_allocation_account;runs=[];guards=[]
        raw_check=forward._SyntheticG1Action.check_guard
        def guard(owner,**kwargs):guards.append(owner.guard);return raw_check(owner,**kwargs)
        def account(*args,**kwargs):
            state=operation.measurements();self.assertEqual(state['stages_started'],3)
            self.assertEqual([row['state'] for row in state['stages']],['committed','committed','open'])
            self.assertEqual(len(list(f.journal.glob('[0-9]*.json'))),3)
            runs.append(True);return raw_account(*args,**kwargs)
        stack,counts=fixtures.content_meter();start=perf_counter()
        with patch.object(forward,'run_allocation_account',side_effect=account), \
             patch.object(forward._SyntheticG1Action,'check_guard',new=guard), \
             patch.object(archive,'_existing_token',side_effect=AssertionError('real credentials')), \
             patch.object(archive,'_new_session',side_effect=AssertionError('real network')), \
             patch.object(archive,'_fresh_gate',side_effect=AssertionError('real PM gate')),stack:
            result=self.call(case,operation)
        self.meter('complete_one_day',operation,counts,perf_counter()-start,
            account_calls=len(runs),unique_guards=len(set(guards)),account_equal=True,
            mocked_requests=result['mocked_requests_started'],mock_tokens=result['mock_token_calls'])
        self.assertEqual(result['result']['payload']['account'],expected)
        self.assertEqual(result['measurements']['stages_started'],5)
        self.assertTrue(all(row['state']=='committed' for row in result['measurements']['stages']))
        self.assertEqual(len(runs),1);self.assertEqual(len(set(guards)),1)
        self.assertEqual(result['mocked_requests_started'],1);self.assertEqual(result['mock_token_calls'],1)
        self.assertTrue(result['complete_synthetic_capture_observe_io_measured'])
        self.assertFalse(result['complete_capture_io_measured']);self.assertFalse(result['real_pm_gate_measured'])
        self.assertEqual(result['real_forward_days_added'],0);self.assertFalse(result['production_admission'])
        self.assertFalse((f.journal/'.writer.lock').exists())
        self.assertLessEqual(result['measurements']['io_bytes_returned'],sessions.G1_SYNTHETIC_POLICY.operation_io_bytes)
        self.assertLessEqual(result['measurements']['open_attempts'],sessions.G1_SYNTHETIC_POLICY.operation_opens)
        for row in result['measurements']['stages']:
            self.assertLessEqual(row['io_bytes_returned'],sessions.G1_SYNTHETIC_POLICY.stage_io_bytes)
            self.assertLessEqual(row['open_attempts'],sessions.G1_SYNTHETIC_POLICY.stage_opens)
        # Legacy inverse-conflict checks are outside the new root I/O meter.
        def forbidden(*args,**kwargs):raise AssertionError('legacy transport attempted a consumed request')
        hooks=dict(clock=lambda:forward._instant(case['now']),monotonic=lambda:0.,gate=forbidden,token=forbidden,session=forbidden)
        old1=v1.capture_prospective_source(f.root/'capture_scope.json',repo_root=f.root,execute=True,
            expected_scope_sha256=forward.digest(case['scope']),mock_hooks=hooks)
        old2=v2.capture_synthetic(f.root/'capture_scope.json',repo_root=f.root,
            expected_scope_sha256=forward.digest(case['scope']),mock_hooks=hooks)
        self.assertEqual(old1['status'],'recovery_review_required');self.assertEqual(old2['status'],'recovery_review_required')
        self.assertEqual(self.inspect(case,'existing_after_complete_capture')['status'],'already_consumed')
        (case['folder']/'response.entity.json').write_bytes(b'corrupt original response')
        self.assertEqual(self.inspect(case,'existing_corrupt_original')['status'],'recovery_review_required')
        before=operation.measurements()['open_attempts']
        with self.assertRaisesRegex(ValueError,'stage_budget_exceeded'):operation.stage()
        self.assertEqual(operation.measurements()['open_attempts'],before)

    def assert_failed(self,case,operation,*,body=False,durable=False):
        self.assertEqual(operation.measurements()['state'],'failed')
        self.assertTrue((case['f'].journal/'.writer.lock').is_file())
        self.assertEqual((case['f'].journal/'00000003.json').exists(),body)
        self.assertEqual((case['f'].journal/'00000004.json').exists(),durable)
        before=operation.measurements()['open_attempts']
        with self.assertRaisesRegex(ValueError,'operation_not_open'):self.call(case,operation)
        self.assertEqual(operation.measurements()['open_attempts'],before)

    def inspect(self,case,label):
        operation=self.operation(case);stack,counts=fixtures.content_meter();start=perf_counter()
        with patch.object(pipeline,'_fixed_token',side_effect=AssertionError('consumed identity token')), \
             patch.object(pipeline._Session,'post',side_effect=AssertionError('consumed identity request')), \
             patch.object(forward,'run_allocation_account',side_effect=AssertionError('consumed identity account')),stack:
            result=self.call(case,operation)
        self.meter(label,operation,counts,perf_counter()-start)
        self.assertFalse(result['automatic_retry_allowed']);self.assertTrue(result['receipt_success_not_assumed'])
        self.assertEqual(result['mocked_requests_started'],0);self.assertEqual(result['mock_token_calls'],0)
        self.assertEqual(result['measurements']['stages_started'],1)
        operation.close();return result

    def test_preclaim_source_and_guard_changes_start_zero_mock_requests(self):
        for timing in ('P1_source','P2_source','P1_guard'):
            with self.subTest(timing=timing):
                case=self.ready();operation=self.operation(case)
                path=case['f'].root/'qualification_fixture.json';raw=path.read_bytes()
                gate=pipeline._fixed_gate;claim=v2._claim
                def change_gate(*args,**kwargs):
                    result=gate(*args,**kwargs)
                    if timing=='P1_source':path.write_bytes(raw+b' ')
                    if timing=='P1_guard':(case['f'].journal/'.writer.lock').write_bytes(b'foreign owner')
                    return result
                def change_claim(*args,**kwargs):
                    if timing=='P2_source':path.write_bytes(raw+b' ')
                    return claim(*args,**kwargs)
                stack,counts=fixtures.content_meter();start=perf_counter()
                with patch.object(pipeline,'_fixed_gate',side_effect=change_gate),patch.object(v2,'_claim',side_effect=change_claim), \
                     patch.object(pipeline,'_fixed_token',side_effect=AssertionError('preclaim token')), \
                     patch.object(pipeline._Session,'post',side_effect=AssertionError('preclaim request')),stack:
                    with self.assertRaises(ValueError):self.call(case,operation)
                self.meter(timing,operation,counts,perf_counter()-start,mocked_requests=0,mock_tokens=0)
                self.assert_failed(case,operation)
                if timing=='P1_guard':self.assertEqual((case['f'].journal/'.writer.lock').read_bytes(),b'foreign owner')

    def test_post_request_source_change_has_no_observation_and_no_retry(self):
        case=self.ready();operation=self.operation(case);capture=archive._capture_once;calls=[]
        path=case['f'].root/'qualification_fixture.json';raw=path.read_bytes()
        def changed(*args,**kwargs):
            result=capture(*args,**kwargs);calls.append(True);path.write_bytes(raw+b' ');return result
        stack,counts=fixtures.content_meter();start=perf_counter()
        with patch.object(archive,'_capture_once',side_effect=changed),stack:
            with self.assertRaisesRegex(ValueError,'original_changed_at_final_read'):self.call(case,operation)
        self.meter('P3_post_request_source_failure',operation,counts,perf_counter()-start)
        self.assertEqual(len(calls),1);self.assert_failed(case,operation)
        receipt=json.loads((case['folder']/'receipt.json').read_bytes())
        self.assertEqual(receipt['mocked_requests_started'],1)
        self.assertEqual(self.inspect(case,'existing_after_P3_failure')['status'],'already_consumed')
        self.assertTrue((case['f'].journal/'.writer.lock').exists())

    def test_rejected_artificial_response_consumes_once_without_account(self):
        case=self.ready();case['response']=pipeline.SyntheticResponse(b'{"code":1,"msg":"artificial rejection"}')
        operation=self.operation(case);stack,counts=fixtures.content_meter();start=perf_counter()
        with patch.object(forward,'run_allocation_account',side_effect=AssertionError('rejected response account')),stack:
            with self.assertRaisesRegex(ValueError,'response rejected'):self.call(case,operation)
        self.meter('rejected_response',operation,counts,perf_counter()-start)
        self.assert_failed(case,operation)
        self.assertEqual(self.inspect(case,'existing_rejected_response')['status'],'already_consumed')

    def test_P4_source_failure_and_P5_deadline_preserve_guard(self):
        for stage_number in (4,5):
            with self.subTest(stage=stage_number):
                case=self.ready();operation=self.operation(case)
                path=case['f'].root/'qualification_fixture.json';raw=path.read_bytes()
                append=forward._append;begin=forward._SyntheticG1Action._begin;clock=forward._clock;late=[]
                def published(*args,**kwargs):
                    result=append(*args,**kwargs)
                    if stage_number==4 and result['kind']=='observation':path.write_bytes(raw+b' ')
                    return result
                def started(owner,phase):
                    result=begin(owner,phase)
                    if stage_number==5 and owner.operation.measurements()['stages_started']==5:late.append(True)
                    return result
                def now(value=None):return clock(case['f'].f.days[22]+'T01:15:00Z' if late else value)
                stack,counts=fixtures.content_meter();start=perf_counter()
                with patch.object(forward,'_append',side_effect=published), \
                     patch.object(forward._SyntheticG1Action,'_begin',new=started),patch.object(forward,'_clock',side_effect=now),stack:
                    with self.assertRaises(ValueError):self.call(case,operation)
                self.meter(f'P{stage_number}_late_failure',operation,counts,perf_counter()-start)
                self.assertEqual(operation.measurements()['stages_started'],stage_number)
                self.assert_failed(case,operation,body=True)
                self.inspect(case,f'existing_after_P{stage_number}_failure')

    def test_P5_final_guard_read_failure_counts_attempt_and_keeps_publications(self):
        case=self.ready();operation=self.operation(case);raw_open=os.open;guard_opens=[]
        lock=(case['f'].journal/'.writer.lock').resolve()
        def fail(path,flags,*args,**kwargs):
            if operation.measurements()['stages_started']==5 and Path(path).resolve()==lock:
                guard_opens.append(True)
                if len(guard_opens)==4:raise OSError('P5 final guard open failure')
            return raw_open(path,flags,*args,**kwargs)
        with patch.object(os,'open',side_effect=fail):
            stack,counts=fixtures.content_meter();start=perf_counter()
            with stack:
                with self.assertRaisesRegex(OSError,'P5 final guard open failure'):self.call(case,operation)
        self.meter('P5_final_guard_open_failure',operation,counts,perf_counter()-start)
        self.assertEqual(len(guard_opens),4);self.assert_failed(case,operation,body=True,durable=True)
        self.inspect(case,'existing_after_P5_final_guard_failure')

    def test_existing_partial_and_corrupt_archives_are_metered_and_not_retried(self):
        case=self.ready();case['folder'].mkdir(parents=True)
        self.assertEqual(self.inspect(case,'existing_empty_reservation')['status'],'recovery_review_required')
        (case['folder']/'claim.json').write_text('{"partial":true}',encoding='utf-8')
        self.assertEqual(self.inspect(case,'existing_partial_claim')['status'],'recovery_review_required')
        (case['folder']/'receipt.json').write_bytes(b'{broken')
        self.assertEqual(self.inspect(case,'existing_corrupt_receipt')['status'],'recovery_review_required')
        self.assertEqual((case['folder']/'receipt.json').read_bytes(),b'{broken')
        self.assertFalse((case['f'].journal/'.writer.lock').exists())

    def test_v1_v2_consumed_identity_and_branch_change_cannot_retry(self):
        for version in (1,2):
            with self.subTest(version=version):
                original=v1_fixtures.ProspectiveTransportTests() if version==1 else v2_fixtures.ProspectiveV2Tests()
                original.setUp();self.addCleanup(original.doCleanups)
                first=original.collect();self.assertEqual(first['status'],'source_observed_unqualified')
                c=original if version==1 else original.case
                case=dict(f=type('FixtureView',(),dict(root=c.root))(),scope=c.scope,now=c.stamp(),
                    template=dict(path='unused.json',sha256='0'*64),response=pipeline.SyntheticResponse(b'{}'))
                # The early existing branch reads the frozen scope before any G1 owner exists.
                (c.root/'capture_scope.json').write_text(json.dumps(c.scope),encoding='utf-8')
                self.assertEqual(self.inspect(case,f'existing_v{version}')['status'],'already_consumed')
                case['scope']=deepcopy(c.scope);case['scope']['context']['branch']='codex/renamed-artificial-topic'
                (c.root/'capture_scope.json').write_text(json.dumps(case['scope']),encoding='utf-8')
                self.assertEqual(self.inspect(case,f'existing_v{version}_renamed')['status'],'already_consumed')
                self.assertEqual(c.token_reads,1);self.assertEqual(len(c.session.calls),1)

    def test_wrong_policy_rejected_before_any_content_read(self):
        case=self.ready();operation=sessions.EvidenceOperation(case['f'].root)
        stack,counts=fixtures.content_meter()
        with stack:
            with self.assertRaisesRegex(ValueError,'Exact five-stage'):self.call(case,operation)
        self.assertEqual(counts['opens'],0);self.assertEqual(operation.measurements()['open_attempts'],0)
        self.assertFalse(case['folder'].exists());self.assertFalse((case['f'].journal/'.writer.lock').exists())
        self.assertEqual(sessions.SYNTHETIC_POLICY.stages,4)

