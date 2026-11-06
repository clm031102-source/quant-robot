"""Artificial capture, archived authority, once-claim and recovery boundaries."""
from copy import deepcopy
from contextlib import redirect_stdout
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from quant_robot.ops import frozen_candidate_forward as forward
from quant_robot.ops import paper_prospective_scope as scopes
from quant_robot.ops import paper_prospective_transport as capture
from quant_robot.ops import paper_source_bundle as bundles
from quant_robot.ops import tushare_live_transport as legacy
from tests.unit import test_paper_source_connection as connection_fixture
from tests.unit.test_tushare_live_transport import Response, Session, TOKEN, payload
from scripts import capture_tushare_prospective_source as cli


class ProspectiveTransportTests(TestCase):
    def setUp(self):
        self.case=connection_fixture.SourceConnectionTests();self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root=self.case.root.resolve();self.case.activate()
        self.day=self.case.fixture.days[21]
        forward.decide(self.case.journal,now=self.day+'T01:00:00Z')
        self.now=datetime.fromisoformat(self.day+'T07:31:00+00:00')
        self.context=dict(machine='office_desktop',task='factor_review',branch='codex/factor-review-test')
        self.scope=scopes.prepare_scope(self.case.journal,repo_root=self.root,
            context=self.context,now=self.stamp())
        self.scope_path=self.root/'prospective_scope.json';self.save_scope()
        self.token_reads=0;self.gate_calls=0
        self.session=Session(Response(payload(self.day.replace('-','')),date=None))

    def stamp(self):return self.now.isoformat().replace('+00:00','Z')

    def save_scope(self):self.scope_path.write_text(json.dumps(self.scope),encoding='utf-8')

    def gate(self,*args):
        self.gate_calls+=1
        return dict(status='ready',primary_market='CN_ETF',blockers=[],generated_at=self.stamp(),
            selected={**self.scope['context'],'current_branch':self.scope['context']['branch']},
            required_reading=[dict(path='artificial.md',status='read',sha256='a'*64)],
            reading_summary=dict(required=1,read=1,missing=0),
            safety=dict(final_holdout_allowed=False,live_boundary_allowed=False))

    def folder(self):
        return self.root/capture.ARCHIVE/'mock_requests'/capture.request_identity(self.scope)

    def hooks(self):
        ticks=iter(i/100 for i in range(1000))
        def token():
            self.token_reads+=1
            self.assertFalse((self.case.journal/'.writer.lock').exists())
            self.assertTrue((self.folder()/'claim.json').is_file())
            self.assertFalse(list(self.folder().glob('.pending-*')))
            return TOKEN
        return dict(clock=lambda:self.now,monotonic=lambda:next(ticks),gate=self.gate,
                    token=token,session=lambda:self.session)

    def collect(self,**kwargs):
        with (patch.object(legacy,'_existing_token',side_effect=AssertionError('host secret')),
              patch.object(legacy,'_new_session',side_effect=AssertionError('real network'))):
            return capture.capture_prospective_source(self.scope_path,repo_root=self.root,
                execute=kwargs.pop('execute',True),expected_scope_sha256=kwargs.pop('expected',forward.digest(self.scope)),
                mock_hooks=kwargs.pop('mock_hooks',self.hooks()),**kwargs)

    def test_mock_capture_retains_originals_and_one_durable_claim(self):
        seen=[];original=scopes.validate_execution
        def checked(*args,**kwargs):
            if kwargs.get('_guard') is not None:
                seen.append((self.case.journal/'.writer.lock').is_file())
            return original(*args,**kwargs)
        with patch.object(scopes,'validate_execution',side_effect=checked):
            result=self.collect()
        self.assertEqual(result['status'],'source_observed_unqualified')
        self.assertTrue(seen and all(seen))
        receipt=capture.verify_prospective_receipt(result['receipt_path'])
        self.assertEqual(receipt['evidence_class'],'mock_transport_contract_test')
        self.assertEqual(receipt['normalized_bar']['volume'],'1234567')
        self.assertEqual(receipt['network_requests_started'],0)
        self.assertEqual(receipt['mocked_requests_started'],1)
        self.assertEqual(self.token_reads,1);self.assertEqual(len(self.session.calls),1)
        self.assertFalse(receipt['candidate_qualification_granted'])
        self.assertEqual(receipt['strategy_forward_days_added'],0)
        for path in self.folder().iterdir():
            self.assertNotIn(TOKEN.encode(),path.read_bytes())
        output=StringIO()
        with redirect_stdout(output):
            code=cli.main(['--repo-root',str(self.root),'inspect','--receipt',result['receipt_path']])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(output.getvalue())['network_requests_started'],0)

    def test_preview_and_wrong_hash_never_claim_or_read_credentials(self):
        result=self.collect(execute=False)
        self.assertEqual(result['status'],'preview')
        self.assertFalse(self.folder().exists());self.assertEqual(self.gate_calls,0)
        with self.assertRaisesRegex(ValueError,'frozen_scope_hash'):
            self.collect(expected='0'*64)
        self.assertEqual(self.token_reads,0);self.assertFalse(self.session.calls)

    def test_context_change_cannot_reset_once_claim(self):
        first=self.collect()
        self.scope=scopes.prepare_scope(self.case.journal,repo_root=self.root,
            context={**self.context,'branch':'codex/renamed-topic'},now=self.stamp())
        self.save_scope();again=self.collect()
        self.assertEqual(again['status'],'already_consumed')
        self.assertEqual(first['receipt_path'],again['receipt_path'])
        self.assertEqual(self.token_reads,1);self.assertEqual(len(self.session.calls),1)

    def test_source_failure_consumes_once_and_redacts_error(self):
        self.session=Session(OSError('failure '+TOKEN))
        result=self.collect()
        self.assertEqual(result['status'],'source_rejected')
        receipt=capture.verify_prospective_receipt(result['receipt_path'])
        self.assertEqual(receipt['http_attempts_started'],1)
        self.assertEqual(self.collect()['status'],'already_consumed')
        self.assertEqual(self.token_reads,1)
        self.assertNotIn(TOKEN,Path(result['receipt_path']).read_text())

    def test_gate_failure_and_writer_race_prevent_claim_and_secret(self):
        hooks=self.hooks();gate=self.gate();gate['status']='blocked'
        hooks['gate']=lambda *args:gate
        with self.assertRaises(ValueError):self.collect(mock_hooks=hooks)
        self.assertFalse(self.folder().exists());self.assertEqual(self.token_reads,0)
        hooks=self.hooks()
        def writer_during_gate(*args):
            (self.case.journal/'.writer.lock').write_text('foreign writer',encoding='utf-8')
            return self.gate()
        hooks['gate']=writer_during_gate
        with self.assertRaises(ValueError):self.collect(mock_hooks=hooks)
        self.assertFalse(self.folder().exists());self.assertEqual(self.token_reads,0)
        self.assertEqual((self.case.journal/'.writer.lock').read_text(),'foreign writer')

    def test_incomplete_claim_is_preserved_and_never_retried(self):
        original=legacy._confirm_references
        def fail_after_claim(folder,refs):
            if (folder/'claim.json').exists():raise OSError('artificial fsync failure')
            return original(folder,refs)
        with patch.object(legacy,'_confirm_references',side_effect=fail_after_claim):
            result=self.collect()
        self.assertEqual(result['status'],'recovery_review_required')
        self.assertTrue((self.folder()/'claim.json').exists())
        self.assertEqual(self.collect()['status'],'recovery_review_required')
        self.assertEqual(self.token_reads,0);self.assertFalse(self.session.calls)

    def test_verifier_allows_append_only_journal_and_never_calls_active(self):
        result=self.collect()
        forward.observe(self.case.journal,self.case.daily_packet(),now=self.day+'T08:02:00Z')
        with patch.object(forward,'_active',side_effect=AssertionError('recursive source verification')):
            verified=capture.verify_prospective_receipt(result['receipt_path'])
        self.assertEqual(verified['status'],'source_observed_unqualified')
        self.assertEqual(self.collect()['status'],'already_consumed')
        self.assertEqual(self.token_reads,1)

    def test_changed_original_prefix_or_archive_blocks_verification(self):
        result=self.collect();path=self.case.journal/'00000001.json'
        raw=path.read_bytes();path.write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):capture.verify_prospective_receipt(result['receipt_path'])
        path.write_bytes(raw)
        (self.folder()/'response.entity.json').write_text('{}',encoding='utf-8')
        with self.assertRaises(ValueError):capture.verify_prospective_receipt(result['receipt_path'])

    def test_source_adapter_binds_archived_prefix_and_preserves_synthetic(self):
        result=self.collect();path=Path(result['receipt_path'])
        context=bundles.EvidenceContext(self.root,component='price')
        evidence=capture.price_adapter().parse(context,dict(
            path=path.relative_to(self.root).as_posix(),sha256=legacy._sha(path.read_bytes())))
        self.assertEqual(evidence.evidence_class,'synthetic_only')
        self.assertGreater(len(context.references),8)
        self.assertEqual(evidence.facts['bar']['date'],self.day)
        context.recheck()

    def test_source_adapter_rechecks_every_current_prefix_original_and_allows_append(self):
        result=self.collect();path=Path(result['receipt_path'])
        context=bundles.EvidenceContext(self.root,component='price')
        with patch.object(forward,'_active',side_effect=AssertionError('recursive source verification')):
            capture.price_adapter().parse(context,dict(
                path=path.relative_to(self.root).as_posix(),sha256=legacy._sha(path.read_bytes())))
        prefix=[self.case.journal/f'{i:08d}.json' for i in range(self.scope['journal_binding']['prefix_length'])]
        for original in prefix:
            key=original.resolve().relative_to(self.root).as_posix()
            self.assertIn(key,context.references)
            before=original.read_bytes();original.write_text('{}',encoding='utf-8')
            try:
                with self.assertRaises(bundles.BundleError):context.recheck()
            finally:original.write_bytes(before)
        before_keys=set(context.references)
        forward.observe(self.case.journal,self.case.daily_packet(),now=self.day+'T08:02:00Z')
        context.recheck()
        self.assertEqual(set(context.references),before_keys)

    def test_source_adapter_preserves_exact_existing_file_and_byte_budgets(self):
        result=self.collect();path=Path(result['receipt_path'])
        ref=dict(path=path.relative_to(self.root).as_posix(),sha256=legacy._sha(path.read_bytes()))
        adapter=capture.price_adapter()
        baseline=bundles.EvidenceContext(self.root,component='price');adapter.parse(baseline,ref)
        self.assertEqual(bundles.MAX_DOCUMENTS,128)
        self.assertEqual(bundles.MAX_TOTAL_BYTES,16_000_000)
        self.assertEqual(bundles.MAX_DOCUMENT_BYTES,2_000_000)
        count=bundles.MAX_DOCUMENTS-len(baseline.references)
        padding=[]
        for index in range(count+1):
            item=self.root/f'readset-padding-{index}.bin';item.write_bytes(b'x')
            padding.append(dict(path=item.name,sha256=legacy._sha(b'x')))
        exact=bundles.EvidenceContext(self.root,component='price')
        for item in padding[:count]:exact.read_bytes(item)
        adapter.parse(exact,ref);self.assertEqual(len(exact.references),128);exact.recheck()
        overflow=bundles.EvidenceContext(self.root,component='price')
        for item in padding:overflow.read_bytes(item)
        with self.assertRaisesRegex(bundles.BundleError,'evidence_budget_exceeded'):adapter.parse(overflow,ref)
        # Use real fixed limits, without patching or expanding shared constants.
        remaining=bundles.MAX_TOTAL_BYTES-baseline.total_bytes;byte_padding=[]
        while remaining:
            raw=b'z'*min(remaining,bundles.MAX_DOCUMENT_BYTES)
            item=self.root/f'byte-padding-{len(byte_padding)}.bin';item.write_bytes(raw)
            byte_padding.append(dict(path=item.name,sha256=legacy._sha(raw)));remaining-=len(raw)
        exact_bytes=bundles.EvidenceContext(self.root,component='price')
        for item in byte_padding:exact_bytes.read_bytes(item)
        adapter.parse(exact_bytes,ref);self.assertEqual(exact_bytes.total_bytes,16_000_000)
        overflow_bytes=bundles.EvidenceContext(self.root,component='price')
        for item in byte_padding:overflow_bytes.read_bytes(item)
        overflow_bytes.read_bytes(padding[0])
        with self.assertRaisesRegex(bundles.BundleError,'evidence_budget_exceeded'):adapter.parse(overflow_bytes,ref)

    def test_production_cannot_use_synthetic_journal_or_mock_scope(self):
        with (patch.object(legacy,'_existing_token',side_effect=AssertionError('host secret')),
              patch.object(legacy,'_new_session',side_effect=AssertionError('real network'))):
            with self.assertRaises(ValueError):
                capture.capture_prospective_source(self.scope_path,repo_root=self.root,
                    execute=True,expected_scope_sha256=forward.digest(self.scope))
        self.assertFalse((self.root/capture.ARCHIVE/'requests').exists())

    def test_legacy_holdout_unchanged_and_no_json_policy_bypass(self):
        before=deepcopy(legacy.HOLDOUT)
        self.scope['policy']['sealed_research_partitions_opened']=True;self.save_scope()
        with self.assertRaises(ValueError):self.collect()
        self.assertEqual(legacy.HOLDOUT,before);self.assertFalse(legacy.HOLDOUT['allow_2026_prices'])
        self.assertEqual(self.token_reads,0)

    def test_claim_guard_cannot_be_reused_after_exit_or_hide_foreign_lock(self):
        with scopes.protected_execution(self.scope,repo_root=self.root,now=self.stamp(),synthetic=True) as refresh:
            self.assertEqual(refresh(now=self.stamp())['request_identity'],capture.request_identity(self.scope))
        with self.assertRaisesRegex(ValueError,'exclusion changed'):refresh(now=self.stamp())
        lock=self.case.journal/'.writer.lock'
        with self.assertRaisesRegex(ValueError,'exclusion changed'):
            with scopes.protected_execution(self.scope,repo_root=self.root,now=self.stamp(),synthetic=True):
                lock.write_text('replacement-owned-elsewhere',encoding='utf-8')
        self.assertEqual(lock.read_text(),'replacement-owned-elsewhere')

    def test_capture_archive_budget_failure_occurs_before_credential(self):
        with patch.object(capture,'MAX_ARCHIVE_BASE_BYTES',100):result=self.collect()
        self.assertEqual(result['status'],'recovery_review_required')
        self.assertEqual(self.token_reads,0);self.assertFalse(self.session.calls)

    def test_body_wrong_day_does_not_become_input(self):
        self.session=Session(Response(payload('20190102'),date=None))
        result=self.collect()
        self.assertEqual(result['status'],'source_rejected')
        self.assertFalse((self.folder()/'response.entity.json').exists())
        self.assertEqual(capture.verify_prospective_receipt(result['receipt_path'])['network_requests_started'],0)

    def test_expiry_after_claim_prevents_credential_and_consumes_identity(self):
        original=legacy._confirm_references
        def expire_after_persistence(folder,refs):
            original(folder,refs)
            if (folder/'claim.json').exists():self.now=capture.parser._utc(self.scope['valid_until'])
        with patch.object(legacy,'_confirm_references',side_effect=expire_after_persistence):
            result=self.collect()
        self.assertEqual(result['status'],'source_rejected')
        receipt=capture.verify_prospective_receipt(result['receipt_path'])
        self.assertEqual(receipt['failure_code'],'scope_expired_before_credential_read')
        self.assertEqual(receipt['http_attempts_started'],0)
        self.assertEqual(self.collect()['status'],'already_consumed')
        self.assertEqual(self.token_reads,0);self.assertFalse(self.session.calls)

    def test_receipt_publication_failure_preserves_raw_response_without_retry(self):
        original=legacy._publish_json
        def fail_receipt(path,value):
            if path.name=='receipt.json':raise legacy.ArchiveWriteError('artificial receipt failure')
            return original(path,value)
        with patch.object(legacy,'_publish_json',side_effect=fail_receipt):result=self.collect()
        self.assertEqual(result['status'],'recovery_review_required')
        self.assertTrue((self.folder()/'response.entity.json').is_file())
        self.assertFalse((self.folder()/'receipt.json').exists())
        self.assertEqual(self.collect()['status'],'recovery_review_required')
        self.assertEqual(self.token_reads,1);self.assertEqual(len(self.session.calls),1)

    def test_archived_prefix_decompression_and_total_bytes_are_bounded(self):
        result=self.collect()
        with patch.object(capture,'MAX_CHUNK_DECODED_BYTES',1):
            with self.assertRaisesRegex(ValueError,'decompression budget'):
                capture.verify_prospective_receipt(result['receipt_path'])
        with patch.object(capture,'MAX_ARCHIVE_BASE_BYTES',100):
            with self.assertRaisesRegex(ValueError,'archive budget'):
                capture.verify_prospective_receipt(result['receipt_path'])

    def test_raw_body_change_during_verification_is_detected(self):
        result=self.collect();original=capture.parser.parse_fund_daily_body
        def mutate_after_parse(*args,**kwargs):
            parsed=original(*args,**kwargs)
            (self.folder()/'response.entity.json').write_text('{}',encoding='utf-8')
            return parsed
        with patch.object(capture.parser,'parse_fund_daily_body',side_effect=mutate_after_parse):
            with self.assertRaises(ValueError):capture.verify_prospective_receipt(result['receipt_path'])

    def test_status_cli_and_capture_reject_without_production_profile(self):
        output=StringIO()
        with redirect_stdout(output):code=cli.main(['status'])
        self.assertEqual(code,0);self.assertEqual(json.loads(output.getvalue())['production_profiles'],0)
        output=StringIO()
        with (redirect_stdout(output),patch.object(legacy,'_existing_token',side_effect=AssertionError('host secret'))):
            code=cli.main(['--repo-root',str(self.root),'capture','--scope',str(self.scope_path),
                          '--scope-sha256',forward.digest(self.scope)])
        self.assertEqual(code,2);self.assertEqual(json.loads(output.getvalue())['status'],'blocked')
