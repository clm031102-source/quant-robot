"""One artificial day: source preparation and G1 account share an open stage."""
from copy import deepcopy
from pathlib import Path
import os
from time import perf_counter
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import tushare_live_transport as transport
from tests.unit import test_frozen_candidate_deferred as fixtures
from tests.unit import test_paper_source_connection as source_fixtures


class P3PrivateHandoffTests(TestCase):
    probes=[]

    def fixture(self,deferred=True):
        case=source_fixtures.SourceConnectionTests()
        fixture=fixtures.G1Fixture(case,deferred=deferred)
        self.addCleanup(case.doCleanups)
        return fixture

    def ready(self):
        fixture=self.fixture();packet=fixture.packet(21)
        fixture.activate();fixture.decide(21)
        return fixture,packet

    def operation(self,fixture):
        return sessions.EvidenceOperation(fixture.root,policy=sessions.G1_SYNTHETIC_POLICY)

    def call(self,fixture,packet,operation):
        return forward._observe_synthetic_deferred_from_proof(fixture.journal,packet['source_proof'],
            evidence_root=fixture.root,acquired_at=packet['acquired_at'],
            now=fixture.f.days[21]+'T08:02:00Z',operation=operation)

    def blocked(self,fixture,operation):
        self.assertEqual(operation.measurements()['state'],'failed')
        self.assertTrue((fixture.journal/'.writer.lock').is_file())
        self.assertFalse((fixture.journal/'00000003.json').exists())
        self.assertFalse((fixture.journal/'00000004.json').exists())
        with self.assertRaisesRegex(ValueError,'operation_not_open'):operation.stage()

    def record_meter(self,label,operation,counts,seconds):
        measured=operation.measurements()
        self.assertEqual(counts['opens'],measured['open_attempts'])
        self.assertEqual(counts['reads'],measured['read_calls'])
        self.assertEqual(counts['bytes'],measured['io_bytes_returned'])
        self.probes.append(dict(label=label,seconds=seconds,external=dict(counts),internal=measured,
            complete_capture_io_measured=False,real_pm_gate_measured=False))

    def test_one_day_same_stage_without_source_commit_account_parity_and_full_meter(self):
        fixture,packet=self.ready()
        old=self.fixture(False);old_packet=old.packet(21);old.activate();old.decide(21)
        expected=old.observe(21,old_packet)['payload']['account']
        operation=self.operation(fixture);trace=[];owners=[]
        raw_handoff=daily._DeferredAssembly._handoff_g1
        raw_account=forward.run_allocation_account
        def handoff(assembly,owner,*args,**kwargs):
            owners.append(owner);return raw_handoff(assembly,owner,*args,**kwargs)
        def account(*args,**kwargs):
            owner=owners[-1];state=operation.measurements()
            self.assertIs(owner.stage,operation._active)
            self.assertIs(owner.source.stage,owner.stage)
            self.assertEqual(state['stages_started'],1)
            self.assertEqual(state['stages'][0]['state'],'open')
            self.assertEqual(owner.boundary_records,[])
            self.assertTrue(owner._source_handoff['consumed'])
            trace.append(dict(stages_started=state['stages_started'],commits_before_account=0,stage_state='open'))
            return raw_account(*args,**kwargs)
        stack,counts=fixtures.content_meter();started=perf_counter()
        with patch.object(daily._DeferredAssembly,'_handoff_g1',new=handoff), \
             patch.object(forward,'run_allocation_account',side_effect=account), \
             patch.object(transport,'_existing_token',side_effect=AssertionError('credentials forbidden')), \
             patch.object(transport,'_new_session',side_effect=AssertionError('network forbidden')),stack:
            result=self.call(fixture,packet,operation)
        self.record_meter('successful_one_day_root',operation,counts,perf_counter()-started)
        self.probes[-1].update(account_trace=trace,account_equal=True,
            account_sha256=forward.digest(expected),journal_events=5,real_forward_days=0)
        self.assertEqual(len(trace),1)
        self.assertEqual(result['result']['payload']['account'],expected)
        self.assertEqual(result['measurements']['stages_started'],3)
        self.assertEqual(len(result['source_boundaries']),3)
        self.assertTrue(all(stage['state']=='committed' for stage in result['measurements']['stages']))
        self.assertFalse(result['complete_capture_io_measured'])
        self.assertFalse(result['production_admission'])
        self.assertEqual(result['real_forward_days_added'],0)
        self.assertFalse((fixture.journal/'.writer.lock').exists())
        self.assertEqual(len(list(fixture.journal.glob('[0-9]*.json'))),5)
        self.assertGreater(counts['confirmation_flushes'],0)
        self.assertIn('ops/paper_g1_handoff.py',forward.CODE_FILES)
        for stage in result['measurements']['stages']:
            self.assertGreaterEqual(stage['per_path']['@code/src/quant_robot/ops/paper_g1_handoff.py']['reads'],2)
        operation.close()

    def test_wrong_handoff_identity_fails_before_account_or_publication(self):
        fixture,packet=self.ready();original=daily._DeferredAssembly._handoff_g1
        for field in ('journal','decision_sha256','session_date','source_id'):
            operation=self.operation(fixture)
            def wrong(assembly,owner,*args,**kwargs):
                kwargs['identity']=deepcopy(kwargs['identity']);kwargs['identity'][field]='wrong'
                return original(assembly,owner,*args,**kwargs)
            with self.subTest(field=field),patch.object(daily._DeferredAssembly,'_handoff_g1',new=wrong), \
                 patch.object(forward,'run_allocation_account',side_effect=AssertionError('unbound account')):
                with self.assertRaisesRegex(ValueError,'handoff identity'):self.call(fixture,packet,operation)
                self.blocked(fixture,operation)
            # Explicit fixture repair only; the root never automatically clears a failed guard.
            (fixture.journal/'.writer.lock').unlink()

    def test_foreign_or_closed_stage_cannot_handoff(self):
        fixture,packet=self.ready();original=daily._DeferredAssembly._handoff_g1
        foreign=self.operation(fixture);foreign_assembly=daily._DeferredAssembly(foreign.stage())
        for mode in ('foreign','closed'):
            operation=self.operation(fixture)
            def wrong(assembly,owner,*args,**kwargs):
                if mode=='foreign':assembly=foreign_assembly
                else:assembly.stage.abort()
                return original(assembly,owner,*args,**kwargs)
            with self.subTest(mode=mode),patch.object(daily._DeferredAssembly,'_handoff_g1',new=wrong), \
                 patch.object(forward,'run_allocation_account',side_effect=AssertionError('foreign stage account')):
                with self.assertRaisesRegex(ValueError,'Same open G1 source stage'):self.call(fixture,packet,operation)
                self.blocked(fixture,operation)
            (fixture.journal/'.writer.lock').unlink()
        self.assertEqual(foreign.measurements()['state'],'failed')

    def test_changed_source_input_identity_fails_before_account(self):
        fixture,packet=self.ready();operation=self.operation(fixture)
        original=daily._DeferredAssembly._handoff_g1
        def wrong(assembly,owner,source,*args,**kwargs):
            source.manifest['asset_id']='CN_ETF_XSHG_510500'
            return original(assembly,owner,source,*args,**kwargs)
        with patch.object(daily._DeferredAssembly,'_handoff_g1',new=wrong), \
             patch.object(forward,'run_allocation_account',side_effect=AssertionError('changed input account')):
            with self.assertRaisesRegex(ValueError,'original-bound G1 source input'):self.call(fixture,packet,operation)
        self.blocked(fixture,operation)

    def test_second_consumption_rejected_without_account_or_observation(self):
        fixture,packet=self.ready();operation=self.operation(fixture);edge={}
        original=forward._consume_source_handoff
        def capture(owner,assembly,identity,value,**kwargs):
            edge.update(owner=owner,assembly=assembly,identity=identity,packet=value,kwargs=kwargs)
            return original(owner,assembly,identity,value,**kwargs)
        def duplicate(*args,**kwargs):
            return original(edge['owner'],edge['assembly'],edge['identity'],edge['packet'],**edge['kwargs'])
        with patch.object(forward,'_consume_source_handoff',side_effect=capture), \
             patch.object(forward,'observe',side_effect=duplicate), \
             patch.object(forward,'run_allocation_account',side_effect=AssertionError('duplicate account')):
            with self.assertRaisesRegex(ValueError,'Unused G1 source handoff'):self.call(fixture,packet,operation)
        self.blocked(fixture,operation)

    def test_packet_change_during_private_edge_rejected_before_account(self):
        fixture,packet=self.ready();operation=self.operation(fixture)
        original=forward._consume_source_handoff
        def change(owner,assembly,identity,value,**kwargs):
            value=deepcopy(value);value['bar']['close']='20.4'
            return original(owner,assembly,identity,value,**kwargs)
        with patch.object(forward,'_consume_source_handoff',side_effect=change), \
             patch.object(forward,'run_allocation_account',side_effect=AssertionError('altered packet account')):
            with self.assertRaisesRegex(ValueError,'prepared G1 packet obligation'):self.call(fixture,packet,operation)
        self.blocked(fixture,operation)

    def test_raw_source_changed_at_handoff_or_after_account_blocks_observation(self):
        fixture,packet=self.ready();path=fixture.root/(fixture.f.days[21]+'/price/original.json')
        raw=path.read_bytes();consume=forward._consume_source_handoff;account=forward.run_allocation_account
        for timing in ('handoff','after_account'):
            operation=self.operation(fixture);runs=[]
            def handoff(*args,**kwargs):
                if timing=='handoff':path.write_bytes(raw+b' ')
                return consume(*args,**kwargs)
            def calculate(*args,**kwargs):
                result=account(*args,**kwargs);runs.append(True)
                if timing=='after_account':path.write_bytes(raw+b' ')
                return result
            stack,counts=fixtures.content_meter();started=perf_counter()
            with self.subTest(timing=timing),patch.object(forward,'_consume_source_handoff',side_effect=handoff), \
                 patch.object(forward,'run_allocation_account',side_effect=calculate),stack:
                with self.assertRaisesRegex(ValueError,'original_changed_at_final_read'):self.call(fixture,packet,operation)
            self.record_meter('source_mutation_'+timing,operation,counts,perf_counter()-started)
            self.assertEqual(len(runs),1);self.blocked(fixture,operation)
            path.write_bytes(raw);(fixture.journal/'.writer.lock').unlink()

    def test_final_content_open_failure_is_charged_and_cannot_retry(self):
        fixture,packet=self.ready();operation=self.operation(fixture)
        path=fixture.root/(fixture.f.days[21]+'/price/original.json');finished=[]
        raw_open=os.open;account=forward.run_allocation_account
        def calculate(*args,**kwargs):
            result=account(*args,**kwargs);finished.append(True);return result
        def failed(path_arg,flags,*args,**kwargs):
            if finished and Path(path_arg).resolve()==path.resolve():raise OSError('injected final content open failure')
            return raw_open(path_arg,flags,*args,**kwargs)
        with patch.object(os,'open',side_effect=failed):
            stack,counts=fixtures.content_meter();started=perf_counter()
            with patch.object(forward,'run_allocation_account',side_effect=calculate),stack:
                with self.assertRaisesRegex(OSError,'injected final content open'):self.call(fixture,packet,operation)
        self.record_meter('final_content_open_failure',operation,counts,perf_counter()-started)
        self.assertEqual(counts['opens'],counts['reads']+1)
        self.blocked(fixture,operation)

    def test_handoff_implementation_final_read_change_blocks_before_publication(self):
        fixture,packet=self.ready();operation=self.operation(fixture)
        original=sessions.EvidenceOperation._read;seen=[]
        def changed(current,stage,path,limit,label,**kwargs):
            raw=original(current,stage,path,limit,label,**kwargs)
            if label=='@code/src/quant_robot/ops/paper_g1_handoff.py':
                seen.append(True)
                if len(seen)==2:return raw+b' '
            return raw
        with patch.object(sessions.EvidenceOperation,'_read',new=changed):
            with self.assertRaisesRegex(ValueError,'implementation_changed_at_final_read'):
                self.call(fixture,packet,operation)
        self.assertEqual(len(seen),2)
        self.blocked(fixture,operation)
