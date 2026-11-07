"""Explicitly artificial 518880 framework; no host secret, HTTP or market input."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import inspect
import json
import os
import shutil
from pathlib import Path
from time import perf_counter
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_recorded_518880_profile as profile
from quant_robot.ops import paper_recorded_sources as sources
from quant_robot.ops import paper_recorded_capture_observe as pipeline
from quant_robot.ops import paper_prospective_recorded_transport as transport
from quant_robot.ops import paper_prospective_transport as v1
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import tushare_live_transport as archive
from quant_robot.ops import tushare_daily_receipt as parser
from tests.unit import test_paper_source_connection as source_fixtures
from tests.unit import test_paper_warmup_bundle as warmup_fixtures
from tests.unit import test_frozen_candidate_deferred as legacy_fixtures
from tests.unit import test_paper_actual_pm_gate as actual_fixtures
from tests.unit import test_tushare_live_transport as scoped_fixtures
from tests.unit import test_paper_prospective_transport as v1_fixtures
from tests.unit import test_paper_prospective_transport_v2 as v2_fixtures
from quant_robot.ops import paper_actual_pm_gate as actual_pm


class FrameworkFixture:
    def __init__(self, test):
        self.case=source_fixtures.SourceConnectionTests()
        with patch.object(warmup_fixtures,'ASSET',profile.ASSET_ID):self.case.setUp()
        test.addCleanup(self.case.doCleanups)
        self.f=self.case.fixture;self.root=self.case.root.resolve();self.journal=self.case.journal
        self.manifest=deepcopy(self.case.manifest)
        operation=self.operation();stage=operation.stage()
        author=sources.RecordedSourceVerification.from_stage(stage,_offline=True)
        self.manifest['source_contract']=author.source_contract('offline-518880')
        operation.close()
        spec=deepcopy(self.f.spec)
        spec['implementation_binding']=self.manifest['source_contract']['originals_binding']['runtime']['assembler_binding']
        self.f.save('warmup_spec.json',spec);self.f.save('manifest.json',self.manifest)
        payload=self.prepare('warmup','warmup_spec.json',self.case.activation_at)
        self.manifest['warmup']=self.case.absolute_save('warmup.json',payload)
        manifest_ref=self.case.absolute_save('manifest.json',self.manifest)
        qualification=deepcopy(self.case.qualification);qualification['manifest_sha256']=manifest_ref['sha256']
        self.case.absolute_save('qualification.json',qualification)

    def ref(self,name):return dict(path=name,sha256=forward.sha256((self.root/name).read_bytes()).hexdigest())
    def operation(self):return sessions.EvidenceOperation(self.root,policy=sessions.G1_RECORDED_POLICY)

    def prepare(self,kind,name,now):
        operation=self.operation();stage=operation.stage()
        author=sources.RecordedSourceVerification.from_stage(stage,_offline=True)
        method=author.prepare_daily_input if kind=='daily' else author.prepare_warmup_input
        kwargs=dict(schedule_ref=self.ref('calendar.json'),now=forward._instant(now))
        if kind=='daily':kwargs['acquired_at']=now
        ticket=method(self.ref('manifest.json'),connection.proof_reference(self.root,name),**kwargs)
        result=stage.commit().result(ticket);operation.close();return result

    def packet(self,index=21):
        day=self.f.days[index];received=day+'T08:00:00Z';acquired=day+'T08:01:00Z'
        actions=deepcopy(self.f.actions);actions['coverage_end']=day
        bar=dict(asset_id=profile.ASSET_ID,date=day,open='20.3',close='20.3',high='21',low='20',volume='100000',amount='2030000')
        execution=dict(asset_id=profile.ASSET_ID,session_date=day,suspended=False,limit_regime='bounded',up_limit='40',down_limit='1')
        def item(kind,facts):return self.f.evidence(kind,facts,label=f'{day}/{kind}',requested=received,received=received)
        spec=dict(artifact_type=daily.SPEC_TYPE,asset_id=profile.ASSET_ID,session_date=day,window_start=self.f.days[0],
            evidence=dict(calendar=self.f.spec['evidence']['calendar'],identity=self.f.spec['evidence']['identity'],
                actions=item('actions',actions),price=item('price',dict(bar=bar)),execution=item('execution',execution)))
        name=f'{day}/spec.json';self.f.save(name,spec);return self.prepare('daily',name,acquired)

    def activate(self):
        return pipeline._offline_journal_action('activate',self.journal,evidence_root=self.root,
            now=self.case.activation_at,manifest_path=self.root/'manifest.json',qualification_path=self.root/'qualification.json')

    def decide(self,index=21):
        return pipeline._offline_journal_action('decide',self.journal,evidence_root=self.root,now=self.f.days[index]+'T01:00:00Z')

    def ready(self):
        packet=self.packet();self.activate();self.decide()
        now=self.f.days[21]+'T08:02:00Z'
        scope=pipeline._prepare_offline_scope(self.journal,evidence_root=self.root,
            context=dict(machine='office_desktop',task='factor_review',branch='codex/artificial-recorded-framework'),now=now)['result']
        self.f.save('scope.json',scope)
        template=json.loads((self.root/packet['source_proof']['specification']['path']).read_bytes())
        del template['evidence']['price'];self.f.save('template.json',template)
        body=json.dumps(dict(code=0,msg=None,data=dict(fields=list(parser.FIELDS),
            items=[['518880.SH',self.f.days[21].replace('-',''),20.3,21,20,20.3,1000,2030]]))).encode()
        return dict(f=self,scope=scope,now=now,template=self.ref('template.json'),response=pipeline._OfflineResponse(body),
            folder=self.root/v1.ARCHIVE/'mock_requests'/v1.request_identity(scope))


class RecordedConnectionTests(TestCase):
    probes=[]

    def ready(self):return FrameworkFixture(self).ready()

    def operation(self,case):return case['f'].operation()

    def meter(self,label,operation,counts,elapsed,**details):
        actual=operation.measurements()
        self.assertEqual(counts['opens'],actual['open_attempts'])
        self.assertEqual(counts['reads'],actual['read_calls'])
        self.assertEqual(counts['bytes'],actual['io_bytes_returned'])
        self.probes.append(dict(label=label,seconds=elapsed,external=dict(counts),internal=actual,**details))

    def assert_failed(self,case,operation,*,body=False,durable=False):
        self.assertEqual(operation.measurements()['state'],'failed')
        self.assertTrue((case['f'].journal/'.writer.lock').is_file())
        self.assertEqual((case['f'].journal/'00000003.json').exists(),body)
        self.assertEqual((case['f'].journal/'00000004.json').exists(),durable)
        before=operation.measurements()['open_attempts']
        with self.assertRaisesRegex(ValueError,'operation_not_open'):self.call(case,operation)
        self.assertEqual(operation.measurements()['open_attempts'],before)

    def inspect(self,case,label):
        operation=self.operation(case)
        with patch.object(pipeline,'_fixed_token',side_effect=AssertionError('consumed token')), \
             patch.object(pipeline._Session,'post',side_effect=AssertionError('consumed request')), \
             patch.object(forward,'run_allocation_account',side_effect=AssertionError('consumed account')):
            result=self.measured(label,case,operation)
        self.assertFalse(result['automatic_retry_allowed'])
        self.assertTrue(result['receipt_success_not_assumed'])
        self.assertEqual(result['mocked_requests_started'],0)
        self.assertEqual(result['measurements']['stages_started'],1)
        operation.close();return result

    def call(self,case,operation=None):
        return pipeline._capture_observe_offline(case['f'].root/'scope.json',evidence_root=case['f'].root,
            expected_scope_sha256=forward.digest(case['scope']),template_ref=case['template'],
            response=case['response'],now=case['now'],operation=operation)

    def measured(self,label,case,operation):
        stack,counts=legacy_fixtures.content_meter();started=perf_counter()
        try:
            with stack:return self.call(case,operation)
        finally:
            actual=operation.measurements()
            self.assertEqual(counts['opens'],actual['open_attempts'])
            self.assertEqual(counts['reads'],actual['read_calls'])
            self.assertEqual(counts['bytes'],actual['io_bytes_returned'])
            self.probes.append(dict(label=label,seconds=perf_counter()-started,external=dict(counts),internal=actual))

    def test_production_entry_has_no_injection_and_missing_facts_touch_nothing(self):
        self.assertEqual(tuple(inspect.signature(pipeline.capture_observe_recorded).parameters),
                         ('scope_path','evidence_root','expected_scope_sha256','template_ref'))
        with patch.object(archive,'_existing_token',side_effect=AssertionError('host secret')), \
             patch.object(archive,'_bounded_worker',side_effect=AssertionError('worker')), \
             patch.object(Path,'open',side_effect=AssertionError('file read')):
            with self.assertRaisesRegex(ValueError,'profile_unavailable'):
                pipeline.capture_observe_recorded('absent',evidence_root='absent',expected_scope_sha256='0'*64,template_ref={})
        self.assertFalse(profile.readiness()['registered']);self.assertFalse(profile.RECORDED_PROFILES)
        with self.assertRaisesRegex(ValueError,'profile_unavailable'):connection._profile(profile.PROFILE_ID,require_recorded=True)

    def test_five_stage_offline_capture_matches_original_account_and_meter(self):
        case=self.ready();operation=case['f'].operation()
        old_case=source_fixtures.SourceConnectionTests()
        with patch.object(warmup_fixtures,'ASSET',profile.ASSET_ID):old=legacy_fixtures.G1Fixture(old_case,deferred=False)
        self.addCleanup(old_case.doCleanups)
        packet=old.packet(21);old.activate();old.decide(21)
        expected=old.observe(21,packet)['payload']['account']
        with patch.object(archive,'_existing_token',side_effect=AssertionError('host secret')), \
             patch.object(archive,'_bounded_worker',side_effect=AssertionError('real worker')):
            result=self.measured('five_stage_offline_success',case,operation)
        self.assertEqual(result['result']['payload']['account'],expected)
        self.assertEqual([r['state'] for r in result['measurements']['stages']],['committed']*5)
        self.assertEqual(result['mocked_requests_started'],1)
        self.assertEqual(result['mock_token_calls'],1)
        self.assertEqual(result['real_forward_days_added'],0)
        self.assertFalse(result['production_admission'])
        self.assertFalse((case['f'].journal/'.writer.lock').exists())

    def test_recorded_admission_rejects_offline_profile(self):
        f=FrameworkFixture(self);operation=f.operation();stage=operation.stage()
        with self.assertRaisesRegex(ValueError,'profile_unavailable'):
            sources.RecordedSourceVerification.from_stage(stage)
        self.assertEqual(operation.measurements()['state'],'failed')
        operation=f.operation();stage=operation.stage()
        author=sources.RecordedSourceVerification.from_stage(stage,_offline=True)
        with self.assertRaisesRegex(ValueError,'cannot_certify_recorded'):
            author.prepare_warmup_input(f.ref('manifest.json'),connection.proof_reference(f.root,'warmup_spec.json'),
                schedule_ref=f.ref('calendar.json'),now=forward._instant(f.case.activation_at),require_recorded=True)
        self.assertEqual(operation.measurements()['state'],'failed')

    def test_old_registry_and_numeric_limits_are_unchanged(self):
        from dataclasses import asdict
        before=asdict(sessions.G1_SYNTHETIC_POLICY);after=asdict(sessions.G1_RECORDED_POLICY)
        before.pop('policy_id');after.pop('policy_id');self.assertEqual(before,after)
        self.assertNotIn(profile.PROFILE_ID,connection.PROFILES)
        self.assertNotIn(profile.OFFLINE_PROFILE_ID,connection.PROFILES)
        self.assertNotIn('synthetic_recorded_connection_price_v1',daily.SYNTHETIC_DEFERRED_ADAPTERS)

    def test_actual_pm_uses_real_branch_and_clocks_with_offline_new_policy(self):
        git=shutil.which('git')
        if git is None:self.skipTest('Git executable unavailable')
        # Only benign fixed environment entries, never a host environment snapshot.
        environment=dict(PATH=str(Path(git).parent)+os.pathsep+os.defpath,PATHEXT='.COM;.EXE;.BAT;.CMD',
                         SYSTEMROOT='C:\\Windows',SystemRoot='C:\\Windows',WINDIR='C:\\Windows')
        with patch.object(os,'environ',environment):
            try:identity=actual_pm._git_identity()
            except ValueError as exc:
                if str(exc) in ('actual_pm_independent_worktree_required','actual_pm_git_command_failed'):
                    self.skipTest('Actual-PM integration requires its isolated engineering branch')
                raise
            now=datetime.now(timezone.utc);day=(now+timedelta(hours=8)).date()
            while day.weekday()>=5 or now<datetime.combine(day,datetime.min.time(),timezone.utc)+timedelta(hours=8,minutes=2):
                day-=timedelta(days=1)
            observable=datetime.combine(day,datetime.min.time(),timezone.utc)+timedelta(hours=7,minutes=30)
            if not observable<=now<observable+timedelta(days=1):
                self.skipTest('Actual UTC outside weekday-only artificial fixture window')
            anchor=day
            for _ in range(21):
                anchor-=timedelta(days=1)
                while anchor.weekday()>=5:anchor-=timedelta(days=1)
            def fixture_date(*args):return anchor if args==(2020,1,2) else date(*args)
            with patch.object(warmup_fixtures,'date',side_effect=fixture_date):case=self.ready()
            f=case['f']
            case['scope']=pipeline._prepare_offline_scope(f.journal,evidence_root=f.root,
                context=dict(machine='office_desktop',task='factor_review',branch=identity['branch']),now=forward._clock()[1])['result']
            f.f.save('scope.json',case['scope']);operation=f.operation()
            stack,counts=actual_fixtures.content_meter();started=perf_counter()
            with patch.object(archive,'_existing_token',side_effect=AssertionError('host credential')), \
                    patch.object(archive,'_bounded_worker',side_effect=AssertionError('real worker')),stack:
                result=pipeline._capture_observe_offline(f.root/'scope.json',evidence_root=f.root,
                    expected_scope_sha256=forward.digest(case['scope']),template_ref=case['template'],
                    response=case['response'],now=None,operation=operation,_actual_pm=True)
            self.meter('actual_pm_offline_new_policy',operation,counts,perf_counter()-started,
                       actual_pm=operation._pm_role().summary(),minimal_artificial_process_environment=True)
        self.assertTrue(result['actual_pm_executed']);self.assertEqual(result['actual_pm_calls'],1)
        self.assertEqual(len(result['git_checks']),10)
        self.assertEqual(result['actual_credentials'],0);self.assertEqual(result['real_network_requests'],0)
        self.assertEqual(result['mocked_requests_started'],1);self.assertEqual(result['real_forward_days_added'],0)


    def test_preclaim_source_and_guard_changes_start_zero_mock_requests(self):
        for timing in ('P1_source','P2_source','P1_guard'):
            with self.subTest(timing=timing):
                case=self.ready();operation=self.operation(case)
                path=case['f'].root/'qualification_fixture.json';raw=path.read_bytes()
                gate=pipeline._fixed_gate;claim=transport._claim
                def change_gate(*args,**kwargs):
                    result=gate(*args,**kwargs)
                    if timing=='P1_source':path.write_bytes(raw+b' ')
                    if timing=='P1_guard':(case['f'].journal/'.writer.lock').write_bytes(b'foreign owner')
                    return result
                def change_claim(*args,**kwargs):
                    if timing=='P2_source':path.write_bytes(raw+b' ')
                    return claim(*args,**kwargs)
                stack,counts=legacy_fixtures.content_meter();start=perf_counter()
                with patch.object(pipeline,'_fixed_gate',side_effect=change_gate),patch.object(transport,'_claim',side_effect=change_claim), \
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
        stack,counts=legacy_fixtures.content_meter();start=perf_counter()
        with patch.object(archive,'_capture_once',side_effect=changed),stack:
            with self.assertRaisesRegex(ValueError,'original_changed_at_final_read'):self.call(case,operation)
        self.meter('P3_post_request_source_failure',operation,counts,perf_counter()-start)
        self.assertEqual(len(calls),1);self.assert_failed(case,operation)
        receipt=json.loads((case['folder']/'receipt.json').read_bytes())
        self.assertEqual(receipt['mocked_requests_started'],1)
        self.assertEqual(self.inspect(case,'existing_after_P3_failure')['status'],'already_consumed')
        self.assertTrue((case['f'].journal/'.writer.lock').exists())


    def test_rejected_artificial_response_consumes_once_without_account(self):
        case=self.ready();case['response']=pipeline._OfflineResponse(b'{"code":1,"msg":"artificial rejection"}')
        operation=self.operation(case);stack,counts=legacy_fixtures.content_meter();start=perf_counter()
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
                append=forward._append;begin=pipeline._RecordedG1Action._begin;clock=forward._clock;late=[]
                def published(*args,**kwargs):
                    result=append(*args,**kwargs)
                    if stage_number==4 and result['kind']=='observation':path.write_bytes(raw+b' ')
                    return result
                def started(owner,phase):
                    result=begin(owner,phase)
                    if stage_number==5 and owner.operation.measurements()['stages_started']==5:late.append(True)
                    return result
                def now(value=None):return clock(case['f'].f.days[22]+'T01:15:00Z' if late else value)
                stack,counts=legacy_fixtures.content_meter();start=perf_counter()
                with patch.object(forward,'_append',side_effect=published), \
                     patch.object(pipeline._RecordedG1Action,'_begin',new=started),patch.object(forward,'_clock',side_effect=now),stack:
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
            stack,counts=legacy_fixtures.content_meter();start=perf_counter()
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


    def test_wrong_policy_rejected_before_any_content_read(self):
        case=self.ready();operation=sessions.EvidenceOperation(case['f'].root)
        stack,counts=legacy_fixtures.content_meter()
        with stack:
            with self.assertRaisesRegex(ValueError,'Exact five-stage'):self.call(case,operation)
        self.assertEqual(counts['opens'],0);self.assertEqual(operation.measurements()['open_attempts'],0)
        self.assertFalse(case['folder'].exists());self.assertFalse((case['f'].journal/'.writer.lock').exists())
        self.assertEqual(sessions.SYNTHETIC_POLICY.stages,4)

    def test_each_missing_metadata_component_blocks_before_claim(self):
        for component in ('calendar','identity','actions','execution'):
            with self.subTest(component=component):
                case=self.ready();f=case['f'];operation=f.operation()
                template=json.loads((f.root/'template.json').read_bytes())
                del template['evidence'][component];f.f.save('template.json',template)
                case['template']=f.ref('template.json')
                before=sorted(p.name for p in f.journal.glob('*.json'))
                with patch.object(pipeline,'_fixed_token',side_effect=AssertionError('missing metadata token')), \
                     patch.object(pipeline._Session,'post',side_effect=AssertionError('missing metadata request')):
                    with self.assertRaisesRegex(ValueError,'four-component'):
                        self.measured('missing_'+component,case,operation)
                self.assertEqual(operation.measurements()['stages_started'],1)
                self.assertFalse(case['folder'].exists())
                self.assertEqual(sorted(p.name for p in f.journal.glob('*.json')),before)
                self.assert_failed(case,operation)

    def test_no_preopen_decision_or_durability_cannot_prepare_scope(self):
        for decision in (False,True):
            with self.subTest(decision=decision):
                f=FrameworkFixture(self);f.activate()
                if decision:
                    f.decide();(f.journal/'00000002.json').unlink()
                with patch.object(pipeline,'_fixed_token',side_effect=AssertionError('decision token')), \
                     patch.object(pipeline._Session,'post',side_effect=AssertionError('decision request')):
                    with self.assertRaises(ValueError):
                        pipeline._prepare_offline_scope(f.journal,evidence_root=f.root,
                            context=dict(machine='office_desktop',task='factor_review',branch='codex/artificial'),
                            now=f.f.days[21]+'T08:02:00Z')
                self.assertFalse((f.root/v1.ARCHIVE).exists())

    def test_missing_token_and_secret_bearing_exception_consume_without_retry(self):
        for value in ('',' ',RuntimeError('artificial-private-secret-123456')):
            with self.subTest(kind=type(value).__name__,blank=not isinstance(value,Exception)):
                case=self.ready();operation=self.operation(case)
                token_patch=(dict(side_effect=value) if isinstance(value,Exception) else dict(return_value=value))
                with patch.object(pipeline,'_fixed_token',**token_patch) as token, \
                     patch.object(pipeline._Session,'post',side_effect=AssertionError('missing token HTTP')):
                    with self.assertRaisesRegex(ValueError,'response rejected'):
                        self.measured('missing_token_or_redacted_exception',case,operation)
                self.assertEqual(token.call_count,1);self.assertTrue((case['folder']/'claim.json').is_file())
                receipt=json.loads((case['folder']/'receipt.json').read_bytes())
                self.assertEqual(receipt['http_attempts_started'],0)
                for path in case['folder'].iterdir():
                    self.assertNotIn(b'artificial-private-secret-123456',path.read_bytes())
                self.assert_failed(case,operation);self.inspect(case,'consumed_missing_token')

    def test_claim_receipt_and_body_publication_failures_never_retry(self):
        for target in ('claim.json','receipt.json','observation'):
            with self.subTest(target=target):
                case=self.ready();operation=self.operation(case)
                publish=archive._publish_json;append=forward._append
                def fail_publish(path,*args,**kwargs):
                    if Path(path).name==target:raise archive.ArchiveWriteError('artificial publication failure')
                    return publish(path,*args,**kwargs)
                def fail_append(directory,events,kind,*args,**kwargs):
                    if target=='observation' and kind=='observation':
                        raise OSError('artificial body failure')
                    return append(directory,events,kind,*args,**kwargs)
                with patch.object(archive,'_publish_json',side_effect=fail_publish), \
                     patch.object(forward,'_append',side_effect=fail_append):
                    with self.assertRaises((OSError,ValueError)):
                        self.measured('publication_failure_'+target,case,operation)
                self.assert_failed(case,operation)
                if target!='claim.json':self.assertTrue((case['folder']/'response.entity.json').is_file())
                inspected=self.inspect(case,'consumed_publication_failure_'+target)
                if target!='observation':self.assertEqual(inspected['status'],'recovery_review_required')

    def test_success_return_lost_and_renamed_scope_do_not_repeat_account(self):
        case=self.ready();operation=self.operation(case)
        self.measured('success_before_lost_return',case,operation)
        journal={p.name:p.read_bytes() for p in case['f'].journal.glob('*.json')}
        case['scope']=deepcopy(case['scope'])
        case['scope']['context']['branch']='codex/renamed-artificial-topic'
        case['f'].f.save('scope.json',case['scope'])
        self.assertEqual(self.inspect(case,'completed_renamed_scope')['status'],'already_consumed')
        self.assertEqual({p.name:p.read_bytes() for p in case['f'].journal.glob('*.json')},journal)

    def test_five_stage_policy_refuses_sixth_stage_before_reads(self):
        f=FrameworkFixture(self);operation=f.operation();reference=f.ref('calendar.json')
        stack,counts=legacy_fixtures.content_meter();started=perf_counter()
        with stack:
            for _ in range(5):
                stage=operation.stage();child=stage.child('price');child.read_bytes(reference)
                child.propose(dict(artificial=True));stage.commit()
            before=operation.measurements()['open_attempts']
            with self.assertRaisesRegex(ValueError,'operation_stage_budget_exceeded'):operation.stage()
        self.assertEqual(operation.measurements()['open_attempts'],before)
        self.meter('sixth_stage_rejected',operation,counts,perf_counter()-started)

    def test_artificial_20240628_518880_source_only_has_no_forward_authority(self):
        case=scoped_fixtures.ScopedTransportTests();case.setUp();self.addCleanup(case.doCleanups)
        case.make_scope('20240628');case.scope['request']['ts_code']='518880.SH';case.save_scope()
        response=scoped_fixtures.Response(scoped_fixtures.payload('20240628','518880.SH'),
                                         date='Fri, 28 Jun 2024 07:00:01 GMT')
        with patch.object(archive,'_existing_token',side_effect=AssertionError('host secret')), \
             patch.object(archive,'_bounded_worker',side_effect=AssertionError('real worker')), \
             patch.object(forward,'run_allocation_account',side_effect=AssertionError('source-only account')):
            result=case.collect(response);receipt=case.receipt(result)
        self.assertEqual(result['status'],'source_observed_unqualified')
        self.assertEqual(receipt['request']['params'],dict(ts_code='518880.SH',trade_date='20240628'))
        self.assertEqual(receipt['received_at'],'2024-06-28T07:00:01.000000Z')
        self.assertFalse(receipt['candidate_qualification_granted']);self.assertEqual(receipt['strategy_forward_days_added'],0)
        self.assertEqual(receipt['network_requests_started'],0);self.assertEqual(receipt['mocked_requests_started'],1)

    def test_handoff_rejects_foreign_owner_identity_packet_and_reuse(self):
        case=self.ready();operation=self.operation(case);consume=pipeline._consume_handoff;checks=[]
        def checked(owner,assembly,identity,packet,**kwargs):
            with self.assertRaisesRegex(ValueError,'owner'):
                consume(object(),assembly,identity,packet,**kwargs)
            changed=deepcopy(identity);changed['source_id']='other-artificial-source'
            with self.assertRaisesRegex(ValueError,'identity'):
                consume(owner,assembly,changed,packet,**kwargs)
            other=sources._RecordedAssembly(owner.stage,_offline=True)
            with self.assertRaisesRegex(ValueError,'obligation'):
                consume(owner,other,identity,packet,**kwargs)
            changed=deepcopy(packet);changed['bar']['asset_id']='CN_ETF_XSHG_510300'
            with self.assertRaisesRegex(ValueError,'obligation'):
                consume(owner,assembly,identity,changed,**kwargs)
            result=consume(owner,assembly,identity,packet,**kwargs)
            with self.assertRaises(ValueError):consume(owner,assembly,identity,packet,**kwargs)
            checks.append(True);return result
        with patch.object(pipeline,'_consume_handoff',side_effect=checked), \
             patch.object(forward,'run_allocation_account',wraps=forward.run_allocation_account) as account:
            self.measured('handoff_foreign_and_reuse_rejected',case,operation)
        self.assertEqual(checks,[True]);self.assertEqual(account.call_count,1)

    def test_prior_v1_v2_identity_is_consumed_across_branch_and_format(self):
        for version in (1,2):
            with self.subTest(version=version):
                original=v1_fixtures.ProspectiveTransportTests() if version==1 else v2_fixtures.ProspectiveV2Tests()
                with patch.object(warmup_fixtures,'ASSET',profile.ASSET_ID):original.setUp()
                self.addCleanup(original.doCleanups);prior=original if version==1 else original.case
                prior.session=scoped_fixtures.Session(scoped_fixtures.Response(
                    scoped_fixtures.payload(prior.day.replace('-',''),'518880.SH'),date=None))
                self.assertEqual(original.collect()['status'],'source_observed_unqualified')
                fixture=type('ExistingFixture',(),{'root':prior.root,
                    'operation':lambda self:sessions.EvidenceOperation(self.root,policy=sessions.G1_RECORDED_POLICY)})()
                case=dict(f=fixture,scope=prior.scope,now=prior.stamp(),template=dict(path='unused.json',sha256='0'*64),
                          response=pipeline._OfflineResponse(b'{}'))
                for renamed in (False,True):
                    if renamed:
                        case['scope']=deepcopy(case['scope']);case['scope']['context']['branch']='codex/renamed-artificial'
                    (prior.root/'scope.json').write_text(json.dumps(case['scope']),encoding='utf-8')
                    result=self.inspect(case,f'prior_v{version}_renamed_{renamed}')
                    self.assertTrue(result['request_reservation_consumed'])
                self.assertEqual(prior.token_reads,1);self.assertEqual(len(prior.session.calls),1)

