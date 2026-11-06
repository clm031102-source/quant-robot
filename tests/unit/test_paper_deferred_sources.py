"""Synthetic top-level five-component + warmup reader integration, no network."""
from contextlib import ExitStack
from copy import deepcopy
import builtins
import io
import json
import os
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops import paper_warmup_bundle as warmup
from quant_robot.ops import paper_prospective_transport_v2 as v2
from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import tushare_live_transport as legacy
from tests.unit import test_paper_warmup_bundle as fixtures


class DeferredSourcesTests(TestCase):
    def setUp(self):
        self.fixture=fixtures.PaperWarmupBundleTests();self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups);self.fixture.make_prefix(21)
        self.root=self.fixture.root.resolve();self.configure()

    def configure(self):
        f=self.fixture
        # Input authoring is outside the measured read-only reconstruction.
        with connection.SyntheticSourceVerification(self.root) as authoring:
            contract=authoring.source_contract('synthetic-deferred-fixtures')
        self.contract=contract
        spec=deepcopy(f.spec)
        spec['implementation_binding']=contract['originals_binding']['runtime']['assembler_binding']
        self.warmup_spec=spec
        self.warmup_ref=f.save('deferred/warmup_spec.json',spec)
        self.schedule_ref=f.save('deferred/schedule.json',f.calendar['sessions'])
        self.manifest=dict(asset_id=spec['asset_id'],first_session=spec['first_session'],
            strategy=dict(components=spec['components']),source_contract=contract)
        self.manifest_ref=f.save('deferred/manifest.json',self.manifest)
        self.daily_ref,self.acquired=self.make_daily(len(f.spec['sessions']))

    def make_daily(self,index,*,price=None):
        f=self.fixture;day=f.days[index];received=day+'T08:00:00Z'
        actions=deepcopy(f.actions);actions['coverage_end']=day
        bar=dict(asset_id=f.spec['asset_id'],date=day,open='20.3',high='20.4',low='20.2',
                 close='20.3',volume='100000',amount='2030000')
        execution=dict(asset_id=f.spec['asset_id'],session_date=day,suspended=False,
                       limit_regime='bounded',up_limit='40',down_limit='1')
        def item(kind,facts):
            return f.evidence(kind,facts,label=f'deferred/{day}/{kind}',received=received,requested=received)
        spec=dict(artifact_type=daily.SPEC_TYPE,asset_id=f.spec['asset_id'],session_date=day,
            window_start=f.days[0],evidence=dict(calendar=f.spec['evidence']['calendar'],
                identity=f.spec['evidence']['identity'],actions=item('actions',actions),
                execution=item('execution',execution),price=price or item('price',dict(bar=bar))))
        return f.save(f'deferred/{day}/spec.json',spec),day+'T08:01:00Z'

    def proof(self,ref):
        return dict(artifact_type=connection.PROOF_TYPE,evidence_root=str(self.root),specification=ref)

    def prepare_pair(self,verification):
        first=verification.prepare_warmup_input(self.manifest_ref,self.proof(self.warmup_ref),
            schedule_ref=self.schedule_ref,now=daily._instant(self.fixture.as_of))
        second=verification.prepare_daily_input(self.manifest_ref,self.proof(self.daily_ref),
            schedule_ref=self.schedule_ref,acquired_at=self.acquired,now=daily._instant(self.acquired))
        return first,second

    def meter(self):
        """External hook observes all content opens/bytes, forbids buffered bypass."""
        stack=ExitStack();counts=dict(opens=0,bytes=0,reads=0)
        opened,read=os.open,os.read
        def counted_open(*args,**kwargs):counts['opens']+=1;return opened(*args,**kwargs)
        def counted_read(*args,**kwargs):
            counts['reads']+=1;raw=read(*args,**kwargs);counts['bytes']+=len(raw);return raw
        stack.enter_context(patch.object(os,'open',side_effect=counted_open))
        stack.enter_context(patch.object(os,'read',side_effect=counted_read))
        stack.enter_context(patch.object(builtins,'open',side_effect=AssertionError('unmetered builtin open')))
        stack.enter_context(patch.object(io,'open',side_effect=AssertionError('unmetered io.open')))
        for owner,name in ((daily,'_adapter_binding'),(warmup,'runtime_binding'),
                           (connection,'runtime_binding'),(forward,'_active'),(legacy,'_read')):
            stack.enter_context(patch.object(owner,name,side_effect=AssertionError('unmetered legacy helper')))
        return stack,counts

    def test_full_five_component_and_warmup_one_stage_no_unmetered_content_reads(self):
        stack,counts=self.meter()
        with stack,connection.SyntheticSourceVerification(self.root) as verification:
            first,second=self.prepare_pair(verification)
            with self.assertRaisesRegex(ValueError,'not_finalized'):first.result()
            with self.assertRaisesRegex(ValueError,'not_finalized'):second.result()
            committed=verification.commit()
        warm,daily_result=committed.result(first),committed.result(second)
        self.assertEqual(len(warm['bars']),21)
        self.assertEqual(daily_result['bar']['date'],self.fixture.days[21])
        self.assertEqual(warm['evidence_class'],'synthetic_only')
        self.assertFalse(daily_result['production_admission'])
        measure=verification.operation.measurements();self.assertEqual(measure['stages_started'],1)
        self.assertEqual(measure['stages'][0]['children'],51)
        self.assertEqual(counts,dict(opens=measure['open_attempts'],bytes=measure['io_bytes_returned'],reads=measure['read_calls']))
        self.assertEqual(set(row['opens'] for row in measure['stages'][0]['per_path'].values()),{2})
        self.assertEqual(sum(p.lineage=='recorded_observation' for p in connection.PROFILES.values()),0)

    def test_verify_methods_are_pending_and_rebuild_every_original(self):
        with connection.SyntheticSourceVerification(self.root) as first:
            a,b=self.prepare_pair(first);done=first.commit();warm,packet=done.result(a),done.result(b)
        with connection.SyntheticSourceVerification(self.root) as second:
            wa=second.verify_warmup_input(self.manifest_ref,warm,schedule_ref=self.schedule_ref,
                now=daily._instant(self.fixture.as_of))
            da=second.verify_daily_input(self.manifest_ref,packet,schedule_ref=self.schedule_ref,
                now=daily._instant(self.acquired))
            with self.assertRaisesRegex(ValueError,'not_finalized'):da.result()
            final=second.commit()
        self.assertEqual(final.result(wa),warm);self.assertEqual(final.result(da),packet)
        edited=deepcopy(packet);edited['bar']['close']='20.31'
        with connection.SyntheticSourceVerification(self.root) as rejected:
            with self.assertRaisesRegex(ValueError,'differs from rebuilt'):
                rejected.verify_daily_input(self.manifest_ref,edited,schedule_ref=self.schedule_ref,
                    now=daily._instant(self.acquired))
            self.assertEqual(rejected.operation.measurements()['state'],'failed')

    def test_final_check_covers_spec_manifest_warmup_and_daily_action_originals(self):
        paths=[self.warmup_ref['path'],self.manifest_ref['path'],
            self.fixture.spec['sessions'][0]['price']['receipt']['path'].replace('receipt','original'),
            f'deferred/{self.fixture.days[21]}/actions/original.json']
        for name in paths:
            path=self.root/name;raw=path.read_bytes()
            with self.subTest(name=name):
                with connection.SyntheticSourceVerification(self.root) as verification:
                    self.prepare_pair(verification);path.write_bytes(raw+b' ')
                    with self.assertRaisesRegex(ValueError,'original_changed_at_final_read'):verification.commit()
                    self.assertEqual(verification.operation.measurements()['state'],'failed')
            path.write_bytes(raw)

    def test_transitive_code_change_at_final_read_poisoned_without_editing_code(self):
        original=sessions.EvidenceOperation._read;seen={}
        def change_on_second(op,stage,path,limit,label):
            raw=original(op,stage,path,limit,label);seen[label]=seen.get(label,0)+1
            if label=='@code/src/quant_robot/ops/frozen_cash_actions.py' and seen[label]==2:return raw+b' '
            return raw
        with patch.object(sessions.EvidenceOperation,'_read',new=change_on_second):
            with connection.SyntheticSourceVerification(self.root) as verification:
                self.prepare_pair(verification)
                with self.assertRaisesRegex(ValueError,'implementation_changed_at_final_read'):verification.commit()

    def test_unreleased_parsers_and_recorded_profiles_are_rejected(self):
        spec=json.loads((self.root/self.daily_ref['path']).read_bytes())
        spec['evidence']['calendar']['adapter_id']='published_calendar_from_JSON'
        ref=self.fixture.save('deferred/unsupported.json',spec)
        for proof,recorded in ((self.proof(ref),False),(self.proof(self.daily_ref),True)):
            with connection.SyntheticSourceVerification(self.root) as verification:
                with self.assertRaises(ValueError):
                    verification.prepare_daily_input(self.manifest_ref,proof,schedule_ref=self.schedule_ref,
                        acquired_at=self.acquired,now=daily._instant(self.acquired),require_recorded=recorded)
                with self.assertRaises(ValueError):verification.commit()
        with self.assertRaisesRegex(ValueError,'reviewed code profile required'):
            connection.runtime_binding(connection.DEFERRED_PROFILE_ID)

    def test_later_component_failure_never_releases_an_earlier_successful_ticket(self):
        wrong={**self.daily_ref,'sha256':'0'*64}
        with connection.SyntheticSourceVerification(self.root) as verification:
            ticket=verification.prepare_warmup_input(self.manifest_ref,self.proof(self.warmup_ref),
                schedule_ref=self.schedule_ref,now=daily._instant(self.fixture.as_of))
            with self.assertRaises(ValueError):
                verification.prepare_daily_input(self.manifest_ref,self.proof(wrong),schedule_ref=self.schedule_ref,
                    acquired_at=self.acquired,now=daily._instant(self.acquired))
            with self.assertRaises(ValueError):verification.commit()
            with self.assertRaises(ValueError):ticket.result()

    def test_invalid_verify_argument_poisoned_after_valid_warmup(self):
        with connection.SyntheticSourceVerification(self.root) as verification:
            verification.prepare_warmup_input(self.manifest_ref,self.proof(self.warmup_ref),
                schedule_ref=self.schedule_ref,now=daily._instant(self.fixture.as_of))
            with self.assertRaisesRegex(ValueError,'packet object'):
                verification.verify_daily_input(self.manifest_ref,None,schedule_ref=self.schedule_ref,
                    now=daily._instant(self.acquired))
            with self.assertRaises(ValueError):verification.commit()

    def test_deferred_component_and_warmup_ledger_keep_their_separate_limits(self):
        refs=[self.fixture.save(f'budget/{i}.json',dict(i=i)) for i in range(129)]
        with sessions.EvidenceOperation(self.root).stage() as stage:
            assembly=daily._DeferredAssembly(stage);context=assembly.context('actions')
            for ref in refs[:128]:context.read_bytes(ref)
            with self.assertRaisesRegex(ValueError,'ordinary_file_budget_exceeded'):context.read_bytes(refs[128])
            self.assertEqual(stage.measurements()['state'],'failed')
        # A reduced ledger probe tests the actual integrated call site; the
        # shipped 8192/64 MB constants and session policy are not enlarged.
        spec=deepcopy(self.warmup_spec)
        with sessions.EvidenceOperation(self.root).stage() as stage:
            with patch.object(warmup,'MAX_PREFIX_DOCUMENTS',4):
                with self.assertRaisesRegex(ValueError,'prefix_document_budget_exceeded'):
                    warmup.prepare_warmup_bundle(spec,session=stage)
            self.assertEqual(stage.measurements()['state'],'failed')
        with sessions.EvidenceOperation(self.root).stage() as stage:
            with patch.object(warmup,'MAX_PREFIX_BYTES',64):
                with self.assertRaisesRegex(ValueError,'prefix_byte_budget_exceeded'):
                    warmup.prepare_warmup_bundle(spec,session=stage)
            self.assertEqual(stage.measurements()['state'],'failed')
        self.assertEqual((warmup.MAX_PREFIX_DOCUMENTS,warmup.MAX_PREFIX_BYTES),(8192,64_000_000))

    def test_catalog_selection_and_child_ceiling_stop_before_extra_reads(self):
        with sessions.EvidenceOperation(self.root).stage() as stage:
            before=stage.measurements()['open_attempts']
            with self.assertRaisesRegex(ValueError,'code_owned_catalog'):
                stage.bind_implementation({'catalog_id':sessions.SOURCE_CATALOG})
            self.assertEqual(stage.measurements()['open_attempts'],before)
        with sessions.EvidenceOperation(self.root).stage() as stage:
            for i in range(2500):stage.new_child('bounded')
            before=stage.measurements()['open_attempts']
            with self.assertRaisesRegex(ValueError,'child_budget_exceeded'):stage.new_child('overflow')
            self.assertEqual(stage.measurements()['open_attempts'],before)

    def test_public_prefix_view_rejects_unregistered_tail_and_closed_stage(self):
        from tests.unit.test_paper_evidence_session import EvidenceSessionTests
        f=EvidenceSessionTests();f.root=self.root
        raws,events=f.chain(3);descriptor=f.descriptor(raws,events,2)
        with sessions.EvidenceOperation(self.root).stage() as stage:
            child=stage.child('prefix');view=child.prefix_view(descriptor)
            self.assertEqual(view.originals()[1]['raw'].encode(),raws[1])
            child.propose({'synthetic':True});stage.commit()
        with self.assertRaisesRegex(ValueError,'session_not_open'):view.originals()
        with sessions.EvidenceOperation(self.root).stage() as stage:
            view=stage.child('prefix').prefix_view(descriptor)
            with self.assertRaisesRegex(ValueError,'outside_registered_range'):
                view.read_bytes(dict(path='journal/00000002.json',sha256=events[2]['sha256']))
            self.assertEqual(stage.measurements()['state'],'failed')


class DeferredProspectivePriceTests(TestCase):
    def test_v2_price_shares_the_top_level_five_component_and_warmup_stage(self):
        from tests.unit.test_paper_prospective_transport_v2 import ProspectiveV2Tests
        capture=ProspectiveV2Tests();capture.setUp();self.addCleanup(capture.doCleanups)
        observed=capture.collect();self.assertEqual(observed['status'],'source_observed_unqualified')
        f=DeferredSourcesTests();f.fixture=capture.case.case.fixture;f.root=capture.root;f.configure()
        f.daily_ref,f.acquired=f.make_daily(21,price=dict(adapter_id='synthetic_prospective_fund_daily_v2',
                                                       receipt=observed['receipt_ref']))
        stack,counts=f.meter()
        with stack,connection.SyntheticSourceVerification(f.root) as verification:
            a,b=f.prepare_pair(verification);committed=verification.commit()
        self.assertEqual(committed.result(b)['bar']['volume'],'1234567')
        measure=verification.operation.measurements();self.assertEqual(measure['stages_started'],1)
        self.assertEqual(measure['stages'][0]['children'],51)
        self.assertEqual(measure['stages'][0]['prefix_events'],3)
        self.assertEqual(counts['bytes'],measure['io_bytes_returned'])
        self.assertEqual(set(row['opens'] for row in measure['stages'][0]['per_path'].values()),{2})
        self.assertEqual(capture.case.token_reads,1);self.assertEqual(len(capture.case.session.calls),1)
