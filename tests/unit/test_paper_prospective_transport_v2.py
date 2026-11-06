"""Isolated v2 integration with artificial sources; no production registration."""
from copy import deepcopy
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import paper_prospective_transport_v2 as v2
from quant_robot.ops import paper_evidence_session as sessions
from quant_robot.ops import paper_prospective_transport as v1
from quant_robot.ops import paper_prospective_scope as scopes
from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import tushare_live_transport as archive
from quant_robot.ops import paper_source_connection as connection
from tests.unit import test_paper_prospective_transport as fixtures


class ProspectiveV2Tests(TestCase):
    def setUp(self):
        self.case=fixtures.ProspectiveTransportTests();self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root=self.case.root

    def collect(self,**kwargs):
        with (patch.object(archive,'_existing_token',side_effect=AssertionError('real credential')),
              patch.object(archive,'_new_session',side_effect=AssertionError('real network')),
              patch.object(archive,'_bounded_worker',side_effect=AssertionError('production transport'))):
            return v2.capture_synthetic(self.case.scope_path,repo_root=self.root,
                expected_scope_sha256=kwargs.pop('expected',forward.digest(self.case.scope)),
                mock_hooks=kwargs.pop('mock_hooks',self.case.hooks()),**kwargs)

    def verify(self,result):return v2.verify_receipt(result['receipt_ref'],evidence_root=self.root)

    def save_json(self,path,value):
        raw=archive._canonical(value)+b'\n';path.write_bytes(raw)
        return dict(path=path.name,sha256=archive._sha(raw))

    def file_ref(self,path):
        return dict(path=path.resolve().relative_to(self.root).as_posix(),sha256=archive._sha(path.read_bytes()))

    def test_v2_mock_capture_has_no_copied_prefix_and_independent_deferred_price(self):
        result=self.collect()
        self.assertEqual(result['status'],'source_observed_unqualified',result)
        folder=self.case.folder();authority=json.loads((folder/'authority.json').read_bytes())
        self.assertEqual(authority['prefix_dependency']['prefix_length'],3)
        self.assertFalse(list(folder.glob('prefix*')))
        verified=self.verify(result)['receipt']
        self.assertEqual(verified['normalized_bar']['volume'],'1234567')
        self.assertEqual(verified['network_requests_started'],0)
        self.assertEqual(verified['mocked_requests_started'],1)
        self.assertEqual(result['isolated_v2_measurements']['stages_started'],3)
        self.assertFalse(result['complete_capture_io_measured'])
        with v2.V2Verification(self.root) as checking:
            ticket=v2.price_adapter().prepare(checking,result['receipt_ref'])
            with self.assertRaisesRegex(ValueError,'not_finalized'):ticket.result()
            committed=checking.commit()
        evidence=committed.price(ticket)
        self.assertEqual(evidence.evidence_class,'synthetic_only')
        self.assertEqual(evidence.facts['bar']['date'],self.case.day)
        self.assertFalse(evidence.implementation_binding['production_admission'])

    def test_existing_v1_success_is_consumed_by_v2_without_a_second_request(self):
        first=self.case.collect();self.assertEqual(first['status'],'source_observed_unqualified')
        result=self.collect();self.assertEqual(result['status'],'already_consumed')
        self.assertEqual(result['receipt_path'],first['receipt_path'])
        self.assertEqual(self.case.token_reads,1);self.assertEqual(len(self.case.session.calls),1)

    def test_v2_identity_survives_branch_change_and_v1_cannot_retry_it(self):
        first=self.collect();self.assertEqual(first['status'],'source_observed_unqualified')
        v1_retry=self.case.collect()
        self.assertEqual(v1_retry['status'],'recovery_review_required')
        self.case.scope=scopes.prepare_scope(self.case.case.journal,repo_root=self.root,
            context={**self.case.context,'branch':'codex/different-label'},now=self.case.stamp())
        self.case.save_scope()
        self.assertEqual(self.collect()['status'],'already_consumed')
        self.assertEqual(self.case.token_reads,1);self.assertEqual(len(self.case.session.calls),1)

    def test_no_implicit_hooks_or_production_profile_and_wrong_scope_hash_is_inert(self):
        for hooks in (None,{}, {'clock':lambda:self.case.now}):
            with self.assertRaises(ValueError):self.collect(mock_hooks=hooks)
        with self.assertRaises(ValueError):self.collect(expected='0'*64)
        self.assertFalse(self.case.folder().exists());self.assertEqual(self.case.token_reads,0)
        self.assertEqual(sum(profile.lineage=='recorded_observation' for profile in connection.PROFILES.values()),0)
        self.assertFalse(isinstance(v2.price_adapter(),v1.sources.SourceAdapter))

    def test_deferred_final_read_detects_current_prefix_and_ordinary_archive_edits(self):
        result=self.collect();folder=self.case.folder()
        for path in (self.case.case.journal/'00000001.json',folder/'response.entity.json',folder/'manifest.original'):
            original=path.read_bytes()
            with self.subTest(path=path.name):
                with self.assertRaisesRegex(ValueError,'original_changed_at_final_read'):
                    with v2.V2Verification(self.root) as checking:
                        ticket=checking.prepare_price(result['receipt_ref'])
                        path.write_bytes(original+b' ');checking.commit()
                path.write_bytes(original)
                with self.assertRaises(ValueError):ticket.result()

    def test_claim_persistence_then_raw_prefix_edit_stops_before_mock_token(self):
        original=archive._confirm_references
        def mutate_after_persist(folder,refs):
            original(folder,refs)
            if (folder/'claim.json').exists() and not (folder/'receipt.json').exists():
                path=self.case.case.journal/'00000001.json';path.write_bytes(path.read_bytes()+b' ')
        with patch.object(archive,'_confirm_references',side_effect=mutate_after_persist):result=self.collect()
        self.assertEqual(result['status'],'recovery_review_required')
        self.assertTrue((self.case.folder()/'claim.json').is_file())
        self.assertEqual(self.case.token_reads,0);self.assertFalse(self.case.session.calls)
        self.assertEqual(self.collect()['status'],'recovery_review_required')
        self.assertEqual(self.case.collect()['status'],'recovery_review_required')
        self.assertEqual(self.case.token_reads,0)

    def test_batch_verification_merges_prefix_and_has_no_legacy_content_reads(self):
        result=self.collect()
        with (patch.object(forward,'_active',side_effect=AssertionError('recursive active')),
              patch.object(archive,'_read',side_effect=AssertionError('unmetered legacy read'))):
            with v2.V2Verification(self.root) as checking:
                first=checking.prepare_price(result['receipt_ref'])
                second=checking.prepare_price(result['receipt_ref'])
                committed=checking.commit()
        self.assertEqual(committed.price(first),committed.price(second))
        stats=checking.operation.measurements()['stages'][0]
        self.assertTrue(all(row['opens']==2 for row in stats['per_path'].values()))
        self.assertEqual(stats['prefix_events'],3)

    def test_appended_tail_is_not_recursively_consumed_by_historical_receipt(self):
        result=self.collect();journal=self.case.case.journal
        previous=json.loads((journal/'00000002.json').read_bytes())
        event=dict(artifact_type=forward.EVENT_TYPE,sequence=3,kind='observation',
            previous_sha256=previous['sha256'],received_at=self.case.day+'T08:02:00Z',
            payload=dict(synthetic_only=True,not_a_business_admission=True))
        event['sha256']=forward.digest(event)
        self.save_json(journal/'00000003.json',event)
        with patch.object(forward,'_active',side_effect=AssertionError('recursive active')):verified=self.verify(result)
        self.assertEqual(verified['receipt']['status'],'source_observed_unqualified')
        # Only the captured prefix is validated; the appended payload itself is
        # not asserted to satisfy the full observation business contract.
        paths=verified['measurements']['stages'][0]['per_path']
        self.assertNotIn('journal/00000003.json',paths)

    def test_rehashed_policy_claim_cannot_expand_reviewed_limits(self):
        result=self.collect();folder=self.case.folder()
        receipt=json.loads((folder/'receipt.json').read_bytes());claim=json.loads((folder/'claim.json').read_bytes())
        altered=deepcopy(receipt['capture_binding']);altered['session']['policy']['ordinary_files']=999999
        claim['capture_binding']=altered;receipt['capture_binding']=altered
        receipt['claim_ref']=self.save_json(folder/'claim.json',claim)
        receipt.pop('sha256');receipt['sha256']=forward.digest(receipt)
        self.save_json(folder/'receipt.json',receipt)
        with self.assertRaisesRegex(ValueError,'exact_capture_and_consumer_binding'):
            v2.verify_receipt(self.file_ref(folder/'receipt.json'),evidence_root=self.root)

    def test_self_consistent_raw_prefix_still_requires_preopen_durability_semantics(self):
        result=self.collect();folder=self.case.folder();journal=self.case.case.journal
        event=json.loads((journal/'00000002.json').read_bytes())
        event['received_at']=self.case.day+'T07:30:00Z';event.pop('sha256');event['sha256']=forward.digest(event)
        self.save_json(journal/'00000002.json',event)
        scope=json.loads((folder/'scope.json').read_bytes())
        scope['journal_binding']['prefix_sha256']=event['sha256']
        scope['journal_binding']['durability_sha256']=event['sha256']
        scope_ref=self.save_json(folder/'scope.json',scope)
        authority=json.loads((folder/'authority.json').read_bytes());desc=authority['prefix_dependency']
        raw_root=sessions.raw_prefix_seed(scope['journal'],desc['activation_sha256']);total=0
        for index in range(desc['prefix_length']):
            raw=(journal/f'{index:08d}.json').read_bytes();total+=len(raw)
            raw_root=sessions.raw_prefix_step(raw_root,index,raw)
        desc.update(prefix_canonical_tail_sha256=event['sha256'],prefix_raw_commitment=raw_root,total_original_bytes=total)
        receipt=json.loads((folder/'receipt.json').read_bytes());claim=json.loads((folder/'claim.json').read_bytes())
        refs=receipt['evidence_refs'];refs['authority']=self.save_json(folder/'authority.json',authority)
        for value in (receipt,claim):
            value['scope_ref']=scope_ref;value['scope_sha256']=forward.digest(scope);value['evidence_refs']=refs
        receipt['claim_ref']=self.save_json(folder/'claim.json',claim)
        receipt.pop('sha256');receipt['sha256']=forward.digest(receipt)
        self.save_json(folder/'receipt.json',receipt)
        with self.assertRaisesRegex(ValueError,'pre-open decision durability'):
            v2.verify_receipt(self.file_ref(folder/'receipt.json'),evidence_root=self.root)
