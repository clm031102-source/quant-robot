"""Actual synthetic G1 root calls; unchanged account engine, no capture/network."""
from contextlib import ExitStack
from copy import deepcopy
import builtins
import io
import json
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import paper_evidence_session as sessions
from tests.unit import test_paper_source_connection as source_fixtures


class G1Fixture:
    def __init__(self,case,*,deferred):
        self.case=case;self.case.setUp();self.f=case.fixture;self.root=case.root.resolve()
        self.deferred=deferred;self.manifest=deepcopy(case.manifest);self.journal=case.journal
        if deferred:self.freeze_deferred()

    def ref(self,name):
        return dict(path=name,sha256=forward.sha256((self.root/name).read_bytes()).hexdigest())

    def freeze_deferred(self):
        operation=sessions.EvidenceOperation(self.root,policy=sessions.G1_SYNTHETIC_POLICY)
        with connection.SyntheticSourceVerification(self.root,operation=operation) as author:
            self.manifest['source_contract']=author.source_contract('synthetic-originals')
        spec=deepcopy(self.f.spec)
        spec['implementation_binding']=self.manifest['source_contract']['originals_binding']['runtime']['assembler_binding']
        self.f.save('warmup_spec.json',spec)
        self.f.save('manifest.json',self.manifest)
        operation=sessions.EvidenceOperation(self.root,policy=sessions.G1_SYNTHETIC_POLICY)
        with connection.SyntheticSourceVerification(self.root,operation=operation) as checking:
            ticket=checking.prepare_warmup_input(self.ref('manifest.json'),connection.proof_reference(self.root,'warmup_spec.json'),
                schedule_ref=self.ref('calendar.json'),now=forward._instant(self.case.activation_at))
            payload=checking.commit().result(ticket)
        self.manifest['warmup']=self.case.absolute_save('warmup.json',payload)
        manifest_ref=self.case.absolute_save('manifest.json',self.manifest)
        qualification=deepcopy(self.case.qualification);qualification['manifest_sha256']=manifest_ref['sha256']
        self.case.absolute_save('qualification.json',qualification)

    def packet(self,index):
        day=self.f.days[index];received=day+'T08:00:00Z';acquired=day+'T08:01:00Z'
        actions=deepcopy(self.f.actions);actions['coverage_end']=day
        price=str(20.3+(index-21)*.1)
        bar=dict(asset_id=self.manifest['asset_id'],date=day,open=price,close=price,high='21',low='20',volume='100000',amount='2030000')
        execution=dict(asset_id=self.manifest['asset_id'],session_date=day,suspended=False,
                       limit_regime='bounded',up_limit='40',down_limit='1')
        def item(kind,facts):return self.f.evidence(kind,facts,label=f'{day}/{kind}',requested=received,received=received)
        spec=dict(artifact_type=daily.SPEC_TYPE,asset_id=self.manifest['asset_id'],session_date=day,
            window_start=self.f.days[0],evidence=dict(calendar=self.f.spec['evidence']['calendar'],
                identity=self.f.spec['evidence']['identity'],actions=item('actions',actions),
                price=item('price',dict(bar=bar)),execution=item('execution',execution)))
        name=f'{day}/spec.json';self.f.save(name,spec);proof=connection.proof_reference(self.root,name)
        if not self.deferred:
            return connection.build_daily_input(self.manifest,proof,schedule=self.case.schedule,
                acquired_at=acquired,now=forward._instant(acquired))
        operation=sessions.EvidenceOperation(self.root,policy=sessions.G1_SYNTHETIC_POLICY)
        with connection.SyntheticSourceVerification(self.root,operation=operation) as checking:
            ticket=checking.prepare_daily_input(self.ref('manifest.json'),proof,schedule_ref=self.ref('calendar.json'),
                acquired_at=acquired,now=forward._instant(acquired))
            return checking.commit().result(ticket)

    def activate(self,**kwargs):
        if not self.deferred:return self.case.activate()
        return forward.activate_synthetic_deferred(self.journal,self.root/'manifest.json',self.root/'qualification.json',
            evidence_root=self.root,now=self.case.activation_at,**kwargs)

    def decide(self,index,**kwargs):
        now=self.f.days[index]+'T01:00:00Z'
        if not self.deferred:return forward.decide(self.journal,now=now)
        return forward.decide_synthetic_deferred(self.journal,evidence_root=self.root,now=now,**kwargs)

    def observe(self,index,packet,**kwargs):
        now=self.f.days[index]+'T08:02:00Z'
        if not self.deferred:return forward.observe(self.journal,packet,now=now)
        return forward.observe_synthetic_deferred(self.journal,packet,evidence_root=self.root,now=now,**kwargs)


def content_meter():
    stack=ExitStack();counts=dict(opens=0,reads=0,bytes=0,confirmation_flushes=0)
    raw_open,raw_read=os.open,os.read;builtin_open,io_open=builtins.open,io.open
    def open_count(path,flags,*args,**kwargs):
        if not flags&getattr(os,'O_DIRECTORY',0):counts['opens']+=1
        return raw_open(path,flags,*args,**kwargs)
    def read_count(*args,**kwargs):
        counts['reads']+=1;raw=raw_read(*args,**kwargs);counts['bytes']+=len(raw);return raw
    def writes_only(original):
        def call(path,mode='r',*args,**kwargs):
            if 'r' in mode or '+' in mode:raise AssertionError('unmetered buffered content read')
            return original(path,mode,*args,**kwargs)
        return call
    stack.enter_context(patch.object(os,'open',side_effect=open_count))
    stack.enter_context(patch.object(os,'read',side_effect=read_count))
    stack.enter_context(patch.object(builtins,'open',side_effect=writes_only(builtin_open)))
    stack.enter_context(patch.object(io,'open',side_effect=writes_only(io_open)))
    original=sessions.EvidenceOperation._read
    def confirmations(operation,stage,path,limit,label,**kwargs):
        if kwargs.get('flush'):counts['confirmation_flushes']+=1
        return original(operation,stage,path,limit,label,**kwargs)
    stack.enter_context(patch.object(sessions.EvidenceOperation,'_read',new=confirmations))
    return stack,counts


class DeferredG1Tests(TestCase):
    def fixture(self,deferred=True):
        case=source_fixtures.SourceConnectionTests();f=G1Fixture(case,deferred=deferred)
        self.addCleanup(case.doCleanups);return f

    def test_two_observations_status_rebuild_exact_account_parity_and_complete_root_meter(self):
        new=self.fixture();old=self.fixture(False)
        packets={i:(new.packet(i),old.packet(i)) for i in (21,22)}
        old.activate()
        legacy=[]
        for index in (21,22):old.decide(index);legacy.append(old.observe(index,packets[index][1]))
        stack,counts=content_meter()
        with stack:
            results=[new.activate()];observations=[]
            for index in (21,22):
                results.append(new.decide(index));result=new.observe(index,packets[index][0])
                results.append(result);observations.append(result['result'])
            restarted=forward.status_synthetic_deferred(new.journal,evidence_root=new.root);results.append(restarted)
        for actual,expected in zip(observations,legacy):
            self.assertEqual(actual['payload']['account'],expected['payload']['account'])
            self.assertFalse(actual['payload']['real_forward_day'])
        self.assertEqual([item['measurements']['stages_started'] for item in results],[2,2,3,2,3,1])
        self.assertEqual(restarted['result']['real_forward_days'],0)
        self.assertFalse(restarted['result']['recovery_required'])
        self.assertEqual(counts['opens'],sum(r['measurements']['open_attempts'] for r in results))
        self.assertEqual(counts['bytes'],sum(r['measurements']['io_bytes_returned'] for r in results))
        self.assertEqual(counts['reads'],sum(r['measurements']['read_calls'] for r in results))
        self.assertGreater(counts['confirmation_flushes'],0)
        self.assertFalse((new.journal/'.writer.lock').exists())

    def ready(self):
        f=self.fixture();packet=f.packet(21);f.activate();f.decide(21);return f,packet

    def operation(self,f):return sessions.EvidenceOperation(f.root,policy=sessions.G1_SYNTHETIC_POLICY)

    def test_account_completed_but_actual_original_mutation_prevents_observation(self):
        f,packet=self.ready();original=forward.run_allocation_account
        for name in ('qualification_fixture.json','calendar.json','warmup_spec.json',
                     f.f.days[0]+'/price/original.json'):
            path=f.root/name;raw=path.read_bytes();operation=self.operation(f)
            def changed(*args,**kwargs):
                account=original(*args,**kwargs);path.write_bytes(raw+b' ');return account
            with self.subTest(name=name),patch.object(forward,'run_allocation_account',side_effect=changed):
                with self.assertRaisesRegex(ValueError,'original_changed_at_final_read'):
                    f.observe(21,packet,operation=operation)
                self.assertEqual(operation.measurements()['state'],'failed')
                self.assertFalse((f.journal/'00000003.json').exists())
                self.assertTrue((f.journal/'.writer.lock').exists())
            # Explicit fixture-only repair between independent fault cases.
            path.write_bytes(raw);(f.journal/'.writer.lock').unlink()

    def test_postflush_source_failure_preserves_body_then_explicit_timely_recovery(self):
        f,packet=self.ready();path=f.root/(f.f.days[21]+'/price/original.json');raw=path.read_bytes()
        original=forward._confirm_durable_event;operation=self.operation(f)
        def changed(directory,event,**kwargs):
            result=original(directory,event,**kwargs)
            if event['kind']=='observation':path.write_bytes(raw+b' ')
            return result
        with patch.object(forward,'_confirm_durable_event',side_effect=changed):
            with self.assertRaises(ValueError):f.observe(21,packet,operation=operation)
        self.assertEqual(operation.measurements()['state'],'failed')
        self.assertTrue((f.journal/'00000003.json').exists())
        self.assertFalse((f.journal/'00000004.json').exists())
        self.assertTrue((f.journal/'.writer.lock').exists())
        path.write_bytes(raw)
        blocked=forward.status_synthetic_deferred(f.journal,evidence_root=f.root)['result']
        self.assertEqual(blocked['status'],'blocked');self.assertEqual(blocked['real_forward_days'],0)
        # Simulates an explicit operator inspection/repair, never auto cleanup.
        (f.journal/'.writer.lock').unlink()
        with patch.object(forward,'run_allocation_account',side_effect=AssertionError('recovery must not replace account')):
            recovered=f.observe(21,packet)
        self.assertEqual(recovered['measurements']['stages_started'],2)
        self.assertEqual(recovered['result']['sequence'],3)
        self.assertTrue((f.journal/'00000004.json').exists())
        again=f.observe(21,packet)
        self.assertEqual(again['result'],recovered['result'])
        self.assertEqual(len(list(f.journal.glob('[0-9]'*8+'.json'))),5)

    def test_postflush_deadline_cannot_be_backfilled_on_late_recovery(self):
        f,packet=self.ready();original=forward._confirm_durable_event;real_clock=forward._clock
        late=f.f.days[22]+'T01:15:00Z';state={'late':False}
        def flushed(directory,event,**kwargs):
            result=original(directory,event,**kwargs)
            if event['kind']=='observation':state['late']=True
            return result
        def clock(now=None):return real_clock(late if state['late'] else now)
        with patch.object(forward,'_confirm_durable_event',side_effect=flushed),patch.object(forward,'_clock',side_effect=clock):
            with self.assertRaisesRegex(ValueError,'receipt deadline'):f.observe(21,packet)
        self.assertFalse((f.journal/'00000004.json').exists())
        (f.journal/'.writer.lock').unlink()  # Explicit artificial recovery inspection.
        with self.assertRaises(ValueError):
            forward.observe_synthetic_deferred(f.journal,packet,evidence_root=f.root,now=late)
        self.assertFalse((f.journal/'00000004.json').exists())

    def test_foreign_lock_replacement_is_preserved_and_active_head_append_is_detected(self):
        f,packet=self.ready();original=forward.run_allocation_account;foreign=b'{"foreign":true}'
        def replace(*args,**kwargs):
            result=original(*args,**kwargs);(f.journal/'.writer.lock').write_bytes(foreign);return result
        with patch.object(forward,'run_allocation_account',side_effect=replace):
            with self.assertRaisesRegex(ValueError,'writer_guard_ownership_changed'):f.observe(21,packet)
        self.assertEqual((f.journal/'.writer.lock').read_bytes(),foreign)
        with self.assertRaises(FileExistsError):f.observe(21,packet)
        self.assertEqual((f.journal/'.writer.lock').read_bytes(),foreign)
        (f.journal/'.writer.lock').unlink()  # Explicit fixture-only removal.
        def append(*args,**kwargs):
            result=original(*args,**kwargs)
            # Even a raw self-consistent extra event cannot silently extend the active head.
            previous=json.loads((f.journal/'00000002.json').read_bytes())['sha256']
            event=dict(artifact_type=forward.EVENT_TYPE,sequence=3,kind='decision',previous_sha256=previous,
                received_at=f.f.days[21]+'T08:02:00Z',payload={'synthetic_only':True})
            event['sha256']=forward.digest(event);(f.journal/'00000003.json').write_bytes(forward.canonical(event))
            return result
        with patch.object(forward,'run_allocation_account',side_effect=append):
            with self.assertRaisesRegex(ValueError,'active_journal_head_changed'):f.observe(21,packet)

    def test_account_code_final_read_change_blocks_without_editing_financial_file(self):
        f,packet=self.ready();original=sessions.EvidenceOperation._read;seen={}
        def changed(operation,stage,path,limit,label,**kwargs):
            raw=original(operation,stage,path,limit,label,**kwargs)
            seen[label]=seen.get(label,0)+1
            if label=='@code/src/quant_robot/paper/annual_allocation.py' and seen[label]==2:return raw+b' '
            return raw
        with patch.object(sessions.EvidenceOperation,'_read',new=changed):
            with self.assertRaisesRegex(ValueError,'implementation_changed_at_final_read'):f.observe(21,packet)
        self.assertFalse((f.journal/'00000003.json').exists())

    def test_publication_head_is_checked_before_releasing_owned_lock(self):
        f=self.fixture();f.activate();original=forward._append
        def append(*args,**kwargs):
            result=original(*args,**kwargs)
            if result['kind']=='decision_durability':
                (f.journal/'00000099.json').write_bytes(b'{}')
            return result
        with patch.object(forward,'_append',side_effect=append):
            with self.assertRaisesRegex(ValueError,'current_journal_gap_or_event_budget|publication_journal_head_changed'):
                f.decide(21)
        self.assertTrue((f.journal/'.writer.lock').exists())

    def test_confirmation_read_failure_is_charged_and_no_budget_restart(self):
        f,packet=self.ready();operation=self.operation(f);original=sessions.EvidenceOperation._read
        def failed(op,stage,path,limit,label,**kwargs):
            raw=original(op,stage,path,limit,label,**kwargs)
            if kwargs.get('flush') and str(path).endswith('00000003.json'):
                raise OSError('artificial post-read persistence failure')
            return raw
        with patch.object(sessions.EvidenceOperation,'_read',new=failed):
            with self.assertRaises(OSError):f.observe(21,packet,operation=operation)
        measure=operation.measurements();self.assertEqual(measure['state'],'failed')
        row=measure['stages'][-1]['per_path']['journal/00000003.json']
        self.assertGreater(row['bytes'],0);self.assertGreaterEqual(row['opens'],2)
        before=measure['open_attempts']
        with self.assertRaises(ValueError):operation.stage()
        self.assertEqual(operation.measurements()['open_attempts'],before)
        self.assertTrue((f.journal/'.writer.lock').exists())

    def test_final_publication_commit_failure_keeps_recovery_lock(self):
        for fault in ('original_change','read_error','code_change'):
            with self.subTest(fault=fault):
                f,packet=self.ready();operation=self.operation(f)
                original=sessions.EvidenceOperation._read;nonflush={};fired=[]
                def fail_final(op,stage,path,limit,label,**kwargs):
                    key=(id(stage),label)
                    if not kwargs.get('flush'):nonflush[key]=nonflush.get(key,0)+1
                    final_event=(label=='journal/00000004.json' and not kwargs.get('flush') and nonflush.get(key)==2)
                    final_code=(len(op._stages)==3 and label=='@code/src/quant_robot/paper/annual_allocation.py' and nonflush.get(key)==2)
                    if fault=='original_change' and final_event:
                        path.write_bytes(path.read_bytes()+b' ');fired.append(True)
                    raw=original(op,stage,path,limit,label,**kwargs)
                    if fault=='read_error' and final_event:
                        fired.append(True);raise OSError('final publication read failed')
                    if fault=='code_change' and final_code:
                        fired.append(True);return raw+b' '
                    return raw
                with patch.object(sessions.EvidenceOperation,'_read',new=fail_final):
                    with self.assertRaises((ValueError,OSError)):f.observe(21,packet,operation=operation)
                self.assertTrue(fired);self.assertEqual(operation.measurements()['state'],'failed')
                self.assertTrue((f.journal/'.writer.lock').exists())
                self.assertTrue((f.journal/'00000004.json').exists())

    def test_postcommit_cleanup_error_or_replacement_does_not_report_success(self):
        for fault in ('unlink_error','replacement'):
            with self.subTest(fault=fault):
                f,packet=self.ready();operation=self.operation(f);foreign=b'{"replacement_after_commit":true}'
                if fault=='unlink_error':
                    unlink=Path.unlink
                    def fail_unlink(path,*args,**kwargs):
                        if path.name=='.writer.lock' and path.parent.resolve()==f.journal.resolve():
                            raise OSError('cleanup failed')
                        return unlink(path,*args,**kwargs)
                    hook=patch.object(Path,'unlink',new=fail_unlink)
                else:
                    commit=sessions.VerificationSession.commit
                    def replace_after(stage):
                        result=commit(stage)
                        if len(stage._operation._stages)==3:(f.journal/'.writer.lock').write_bytes(foreign)
                        return result
                    hook=patch.object(sessions.VerificationSession,'commit',new=replace_after)
                with hook:
                    with self.assertRaises((ValueError,OSError)):f.observe(21,packet,operation=operation)
                self.assertEqual(operation.measurements()['state'],'failed')
                self.assertTrue((f.journal/'.writer.lock').exists())
                if fault=='replacement':self.assertEqual((f.journal/'.writer.lock').read_bytes(),foreign)

    def test_exact_five_stage_policy_sixth_hard_stop_and_invalid_packet_poison(self):
        from dataclasses import asdict,replace
        self.assertEqual(sessions.SYNTHETIC_POLICY.stages,4)
        old,new=asdict(sessions.SYNTHETIC_POLICY),asdict(sessions.G1_SYNTHETIC_POLICY)
        self.assertEqual({k:v for k,v in old.items() if k not in ('stages','policy_id')},
                         {k:v for k,v in new.items() if k not in ('stages','policy_id')})
        f=self.fixture();ref=f.ref('qualification_fixture.json')
        for invalid in (replace(sessions.G1_SYNTHETIC_POLICY),asdict(sessions.G1_SYNTHETIC_POLICY)):
            with self.assertRaisesRegex(ValueError,'code_owned_policy'):
                sessions.EvidenceOperation(f.root,policy=invalid)
        operation=self.operation(f)
        for _ in range(5):
            with operation.stage() as stage:
                child=stage.child('probe');child.read_bytes(ref);child.propose({'synthetic_only':True});stage.commit()
        before=operation.measurements()['open_attempts']
        with self.assertRaisesRegex(ValueError,'stage_budget'):operation.stage()
        self.assertEqual(operation.measurements()['open_attempts'],before)
        operation=self.operation(f)
        with self.assertRaisesRegex(ValueError,'packet object'):
            forward.observe_synthetic_deferred(f.journal,None,evidence_root=f.root,operation=operation)
        self.assertEqual(operation.measurements()['state'],'failed')

    def test_borrowed_source_cannot_commit_or_open_nested_operation(self):
        f=self.fixture();operation=self.operation(f)
        with operation.stage() as stage:
            borrowed=connection.SyntheticSourceVerification.from_stage(stage)
            with self.assertRaisesRegex(ValueError,'Only the root'):borrowed.commit()
            with self.assertRaisesRegex(ValueError,'Borrowed'):borrowed.__enter__()
            stage.abort()

    def test_legacy_or_unbound_profile_cannot_enter_new_g1_by_synthetic_label(self):
        old=self.fixture(False)
        with patch.object(forward,'run_allocation_account',side_effect=AssertionError('unadmitted account')):
            with self.assertRaisesRegex(ValueError,'five-stage original-bound'):
                forward.activate_synthetic_deferred(old.journal,old.root/'manifest.json',old.root/'qualification.json',
                    evidence_root=old.root,now=old.case.activation_at)
        self.assertFalse((old.journal/'00000000.json').exists())

    def test_old_four_stage_v2_capture_binding_is_not_reinterpreted_by_five_stage_sources(self):
        from tests.unit import test_paper_prospective_transport_v2 as v2_fixtures
        capture=v2_fixtures.ProspectiveV2Tests();capture.setUp();self.addCleanup(capture.doCleanups)
        observed=capture.collect();self.assertEqual(observed['status'],'source_observed_unqualified')
        capture.case.case.daily_packet()
        spec=json.loads((capture.root/'daily_spec.json').read_bytes())
        spec['evidence']['price']=dict(adapter_id='synthetic_prospective_fund_daily_v2',receipt=observed['receipt_ref'])
        operation=sessions.EvidenceOperation(capture.root,policy=sessions.G1_SYNTHETIC_POLICY)
        with operation.stage() as stage:
            with self.assertRaisesRegex(ValueError,'deferred_bundle_incomplete'):
                daily.prepare_source_bundle(spec,session=stage,decision_at=capture.case.day+'T08:01:00Z')
        self.assertEqual(operation.measurements()['state'],'failed')
        self.assertEqual(capture.case.token_reads,1);self.assertEqual(len(capture.case.session.calls),1)
