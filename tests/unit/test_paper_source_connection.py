"""Artificial original-to-journal integration; never a strategy qualification."""
from copy import deepcopy
from dataclasses import asdict
from datetime import timedelta
import json
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_source_connection as connection
from quant_robot.ops import paper_source_bundle as daily
from quant_robot.ops import paper_warmup_bundle as warmup
from quant_robot.paper.annual_allocation import AllocationConfig
from quant_robot.paper.daily_recovery import RECOVERY_40
from tests.unit import test_paper_warmup_bundle as warmup_fixtures


class SourceConnectionTests(TestCase):
    def setUp(self):
        self.fixture = warmup_fixtures.PaperWarmupBundleTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.make_prefix(21)
        self.root = self.fixture.root
        self.schedule = self.fixture.calendar['sessions']
        self.manifest = dict(artifact_type=forward.MANIFEST_TYPE, candidate_id='SYNTHETIC_ONLY',
            asset_id=self.fixture.spec['asset_id'], first_session=self.fixture.days[21],
            runtime_binding=forward.runtime_binding(), daily_recovery=RECOVERY_40,
            account_config=asdict(AllocationConfig(max_position_cny=10000,
                max_position_fraction=1, max_drawdown=.4, execution_price_field='open')),
            strategy=dict(adapter='existing_predicate_and_v1', components=['sma20_trend'], cadence=1),
            source_contract=connection.source_contract('synthetic-originals'))
        self.journal = self.root/'journal'
        self.activation_at = self.fixture.as_of
        self.freeze()

    def absolute_save(self, name, value):
        self.fixture.save(name, value)
        return forward.file_reference(self.root/name)

    def freeze(self):
        self.fixture.bind(adapters=connection.PROFILES[connection.PROFILE_ID].adapters,
                          adapter_dependencies=connection.PROFILES[connection.PROFILE_ID].dependencies)
        self.fixture.save('warmup_spec.json', self.fixture.spec)
        proof = connection.proof_reference(self.root, 'warmup_spec.json')
        payload = connection.build_warmup_input(self.manifest, proof, schedule=self.schedule,
                                               now=forward._instant(self.activation_at))
        self.manifest['calendar'] = self.absolute_save('calendar.json', self.schedule)
        self.manifest['warmup'] = self.absolute_save('warmup.json', payload)
        manifest_ref = self.absolute_save('manifest.json', self.manifest)
        self.qualification = dict(artifact_type=forward.QUALIFICATION_TYPE,
            manifest_sha256=manifest_ref['sha256'], verdict='qualified',
            review_role='independent_qualification_review', evidence_class='synthetic_test_only',
            issued_at=self.activation_at, gates={name:True for name in forward.GATES},
            supporting_evidence=[self.absolute_save('qualification_fixture.json', {'synthetic_only':True})])
        self.absolute_save('qualification.json', self.qualification)

    def activate(self):
        return forward.activate(self.journal, self.root/'manifest.json', self.root/'qualification.json',
                                mode='synthetic', now=self.activation_at)

    def daily_packet(self):
        fixture = self.fixture
        day = fixture.days[21]
        received, acquired = day+'T08:00:00Z', day+'T08:01:00Z'
        fixture.actions['coverage_end'] = day
        bar = dict(asset_id=self.manifest['asset_id'], date=day, open='20.3', high='20.4',
                   low='20.2', close='20.3', volume='100000', amount='2030000')
        execution = dict(asset_id=self.manifest['asset_id'], session_date=day,
                         suspended=False, limit_regime='bounded', up_limit='40', down_limit='1')
        def item(kind, facts):
            return fixture.evidence(kind, facts, label='daily_'+kind,
                                    requested=received, received=received)
        spec = dict(artifact_type=daily.SPEC_TYPE, asset_id=self.manifest['asset_id'],
            session_date=day, window_start=fixture.days[0], evidence=dict(
                calendar=fixture.spec['evidence']['calendar'],
                identity=fixture.spec['evidence']['identity'],
                actions=item('actions',fixture.actions), price=item('price',{'bar':bar}),
                execution=item('execution',execution)))
        fixture.save('daily_spec.json',spec)
        return connection.build_daily_input(self.manifest,
            connection.proof_reference(self.root,'daily_spec.json'), schedule=self.schedule,
            acquired_at=acquired, now=forward._instant(acquired))

    def test_originals_to_activation_decision_observation_and_restart(self):
        self.activate()
        day = self.fixture.days[21]
        forward.decide(self.journal,now=day+'T01:00:00Z')
        packet = self.daily_packet()
        observed = forward.observe(self.journal,packet,now=day+'T08:02:00Z')
        self.assertFalse(observed['payload']['real_forward_day'])
        status = forward.status(self.journal)
        self.assertEqual(status['real_forward_days'],0)
        self.assertEqual(status['source_adapter_status'],'bound_originals_synthetic')
        self.assertEqual(forward.observe(self.journal,packet,now=day+'T08:03:00Z'), observed)
        next_day = self.fixture.days[22]
        self.assertEqual(forward.decide(self.journal,now=next_day+'T01:00:00Z')['payload']['session_date'],next_day)

    def test_manual_packet_edit_and_original_mutation_fail_closed(self):
        self.activate()
        day = self.fixture.days[21]
        forward.decide(self.journal,now=day+'T01:00:00Z')
        packet = self.daily_packet()
        edited = deepcopy(packet); edited['bar']['close']='20.31'
        with self.assertRaisesRegex(ValueError,'differs from rebuilt'):
            forward.observe(self.journal,edited,now=day+'T08:02:00Z')
        forward.observe(self.journal,packet,now=day+'T08:02:00Z')
        (self.root/'daily_price/original.json').write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'evidence_hash_mismatch'):
            forward.status(self.journal)

    def test_fixture_cannot_be_promoted_by_qualification_or_manifest_flags(self):
        self.qualification['evidence_class']='reviewed_research'
        self.absolute_save('qualification.json',self.qualification)
        with self.assertRaisesRegex(ValueError,'synthetic profile cannot certify forward'):
            forward.activate(self.journal,self.root/'manifest.json',self.root/'qualification.json')
        self.assertFalse(self.journal.exists())
        with self.assertRaisesRegex(ValueError,'reviewed code profile required'):
            connection.runtime_binding('claimed_production_source')

    def test_current_asof_notice_survives_activation_and_first_observation(self):
        f = self.fixture
        self.activation_at=f.days[21]+'T01:00:00Z'; f.spec['as_of']=self.activation_at
        event=dict(event_id='synthetic-new-cash',asset_id=self.manifest['asset_id'],
            kind='cash_dividend',announced_date=f.days[21],record_date=f.days[21],
            ex_date=f.days[22],pay_date=f.days[23],cash_amount='1',per_units='10',
            share_multiplier='1',cash_basis='net')
        f.actions['coverage_end']=f.days[21]
        f.actions['pages'][0].update(total_records=1,records=[dict(event_id=event['event_id'],kind='cash_dividend')])
        f.actions['notices']=[event]
        f.spec['evidence']['actions']=f.evidence('actions',f.actions,label='new_cash',
            requested=f.days[21]+'T00:50:00Z',received=f.days[21]+'T00:51:00Z')
        self.freeze();self.activate()
        decision=forward.decide(self.journal,now=f.days[21]+'T01:01:00Z')
        self.assertTrue(decision['payload']['known'])
        result=forward.observe(self.journal,self.daily_packet(),now=f.days[21]+'T08:02:00Z')
        self.assertEqual(result['payload']['packet']['corporate_actions'][0]['announced_date'],f.days[21])

    def test_changed_profile_parameters_and_candidate_components_rejected(self):
        manifest=deepcopy(self.manifest)
        manifest['source_contract']['originals_binding']['runtime']['lineage']='recorded_observation'
        with self.assertRaisesRegex(ValueError,'parameters changed'):
            connection.validate_contract(manifest)
        manifest=deepcopy(self.manifest);manifest['strategy']['components']=['cmf20_positive']
        payload=json.loads((self.root/'warmup.json').read_bytes())
        with self.assertRaisesRegex(ValueError,'differs from frozen candidate'):
            connection.verify_warmup_input(manifest,self.schedule,payload,
                                           now=forward._instant(self.activation_at))

    def test_validation_finishing_after_deadline_does_not_append_observation(self):
        self.activate();day=self.fixture.days[21]
        forward.decide(self.journal,now=day+'T01:00:00Z')
        packet=self.daily_packet()
        early=day+'T08:02:00Z';late=self.fixture.days[22]+'T08:00:01Z'
        # The first clock verifies the old prefix, second imports the new packet,
        # and the final clock must account for time spent validating/replaying.
        clocks=[(forward._instant(value),value) for value in (early,early,late)]
        with patch.object(forward,'_clock',side_effect=clocks):
            with self.assertRaisesRegex(ValueError,'crossed the receipt deadline'):
                forward.observe(self.journal,packet,now=early)
        self.assertEqual(len([e for e in forward._journal(self.journal) if e['kind']=='observation']),0)

    def test_decision_published_after_cutoff_cannot_use_earlier_calculation_stamp(self):
        self.activate();day=self.fixture.days[21]
        early,late=day+'T01:14:59Z',day+'T01:15:01Z'
        clocks=[(forward._instant(value),value) for value in (early,early,early,late)]
        with patch.object(forward,'_clock',side_effect=clocks):
            with self.assertRaisesRegex(ValueError,'durability confirmation missed'):
                forward.decide(self.journal,now=early)
        events=forward._journal(self.journal)
        self.assertEqual(len([e for e in events if e['kind']=='decision']),1)
        self.assertFalse(any(e['kind']=='decision_durability' for e in events))
        with self.assertRaisesRegex(ValueError,'durability confirmation missed'):
            forward.decide(self.journal,now=late)
        with self.assertRaisesRegex(ValueError,'Durable pre-open decision'):
            forward.observe(self.journal,self.daily_packet(),now=day+'T08:02:00Z')

    def test_final_observation_clock_cannot_precede_received_inputs(self):
        self.activate();day=self.fixture.days[21]
        forward.decide(self.journal,now=day+'T01:00:00Z');packet=self.daily_packet()
        moments=[day+'T08:02:00Z',day+'T08:02:00Z',day+'T07:59:00Z']
        with patch.object(forward,'_clock',side_effect=[(forward._instant(t),t) for t in moments]):
            with self.assertRaisesRegex(ValueError,'calculation clock regressed'):
                forward.observe(self.journal,packet,now=moments[0])
        self.assertFalse(any(e['kind']=='observation' for e in forward._journal(self.journal)))

    def test_empty_daily_action_index_cannot_cover_after_actual_receipt(self):
        self.daily_packet();day=self.fixture.days[21]
        spec=json.loads((self.root/'daily_spec.json').read_bytes())
        earlier=self.fixture.days[20]+'T08:00:00Z'
        self.fixture.replace_receipt(spec['evidence']['actions'],
            request_started_at=earlier,received_at=earlier)
        self.fixture.save('daily_spec.json',spec)
        with self.assertRaisesRegex(ValueError,'action_coverage_after_receipt_date'):
            connection.build_daily_input(self.manifest,connection.proof_reference(self.root,'daily_spec.json'),
                schedule=self.schedule,acquired_at=day+'T08:01:00Z',now=forward._instant(day+'T08:02:00Z'))

    def test_original_mutation_during_account_work_cannot_publish_success(self):
        self.activate();day=self.fixture.days[21]
        forward.decide(self.journal,now=day+'T01:00:00Z');packet=self.daily_packet()
        calculate=forward.run_allocation_account
        def mutate(*args,**kwargs):
            result=calculate(*args,**kwargs)
            (self.root/'daily_price/original.json').write_text('{}',encoding='utf-8')
            return result
        with patch.object(forward,'run_allocation_account',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'evidence_hash_mismatch'):
                forward.observe(self.journal,packet,now=day+'T08:02:00Z')
        self.assertFalse(any(e['kind']=='observation' for e in forward._journal(self.journal)))

    def test_late_observation_publication_is_retained_unconfirmed_and_unusable(self):
        self.activate();day=self.fixture.days[21]
        forward.decide(self.journal,now=day+'T01:00:00Z');packet=self.daily_packet()
        deadline=forward._instant(day+'T07:30:00Z')+timedelta(days=1)
        early=(deadline-timedelta(seconds=1)).isoformat().replace('+00:00','Z')
        late=(deadline+timedelta(seconds=1)).isoformat().replace('+00:00','Z')
        physical={'now':early};append=forward._append
        def clock(now=None):return forward._instant(physical['now']),physical['now']
        def delayed(*args,**kwargs):
            if args[2]=='observation':physical['now']=late
            return append(*args,**kwargs)
        with patch.object(forward,'_clock',side_effect=clock),patch.object(forward,'_append',side_effect=delayed):
            with self.assertRaisesRegex(ValueError,'durability confirmation crossed'):
                forward.observe(self.journal,packet,now=early)
        events=forward._journal(self.journal)
        self.assertEqual(len([e for e in events if e['kind']=='observation']),1)
        self.assertFalse(any(e['kind']=='observation_durability' for e in events))
        status=forward.status(self.journal)
        self.assertEqual(status['reason'],'observation_durability_unconfirmed')
        self.assertTrue(status['recovery_required'])
        self.assertEqual(status['real_forward_days'],0)
        self.assertEqual(status['paper_fills'],0)
        with self.assertRaisesRegex(ValueError,'Unconfirmed observation'):
            forward.decide(self.journal,now=self.fixture.days[22]+'T01:00:00Z')
        with self.assertRaisesRegex(ValueError,'durability confirmation crossed'):
            forward.observe(self.journal,packet,now=late)
        self.assertEqual(events,forward._journal(self.journal))

    def test_warmup_mutation_during_signal_work_blocks_activation_or_decision(self):
        feature=forward.feature_frame
        original=self.root/self.fixture.days[0]/'price/original.json'
        raw=original.read_bytes()
        def mutate(*args,**kwargs):
            result=feature(*args,**kwargs);original.write_text('{}',encoding='utf-8');return result
        with patch.object(forward,'feature_frame',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'evidence_hash_mismatch'):self.activate()
        self.assertFalse(self.journal.exists())
        original.write_bytes(raw);self.activate()
        with patch.object(forward,'feature_frame',side_effect=mutate):
            with self.assertRaisesRegex(ValueError,'evidence_hash_mismatch'):
                forward.decide(self.journal,now=self.fixture.days[21]+'T01:00:00Z')
        self.assertFalse(any(e['kind']=='decision' for e in forward._journal(self.journal)))
