"""Bounded source transport contracts with in-memory network and fake credentials."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from io import StringIO
import json
import multiprocessing
from pathlib import Path
import socket
from tempfile import TemporaryDirectory
import threading
import time
import unittest
from unittest.mock import patch

from quant_robot.ops import tushare_live_transport as live
from quant_robot.ops import tushare_daily_receipt as raw_parser
from scripts import capture_tushare_scoped_source as cli


TOKEN='synthetic-credential-never-read-from-host'


def _slow_drip_worker(connection):
    """Real local socket bytes arrive fast enough to evade a per-read timeout."""
    reader,writer=socket.socketpair()
    reader.settimeout(.5)
    def drip():
        for _ in range(300):
            writer.sendall(b'x')
            time.sleep(.02)
        writer.close()
    threading.Thread(target=drip,daemon=True).start()
    connection.send({'event':'slow_fixture_read_started'})
    with reader.makefile('rb') as stream:
        result=stream.read(8192)  # About six seconds without a total deadline.
    connection.send({'result':result})
    reader.close();connection.close()


def payload(day='20250102',symbol='510300.SH'):
    return json.dumps(dict(code=0,msg=None,data=dict(fields=list(raw_parser.FIELDS),
        items=[[symbol,day,4.1,4.2,4.0,4.15,12345.67,98765.432]]))).encode()


class Response:
    def __init__(self,raw,*,url=raw_parser.SOURCE_URL,status=200,date='Thu, 02 Jan 2025 07:00:01 GMT'):
        self.raw,self.url,self.status_code=raw,url,status
        self.headers={'Date':date} if date is not None else {}
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def iter_content(self,chunk_size):
        yield self.raw[:15]
        yield self.raw[15:]


class Session:
    def __init__(self,response):self.response,self.calls=response,[]
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def post(self,url,**kwargs):
        self.calls.append((url,kwargs))
        if isinstance(self.response,Exception):raise self.response
        return self.response


class ScopedTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.day='20250102'
        self.now=datetime(2025,1,2,7,0,1,tzinfo=timezone.utc)
        self.token_reads=0
        self.scope_path=self.root/'scope.json'
        self.make_scope()

    def make_scope(self,day=None,*,observation_time='07:00:00',observed_time='07:00:01'):
        if day is not None:
            self.day=day
            self.now=datetime.strptime(day,'%Y%m%d').replace(hour=7,second=1,tzinfo=timezone.utc)
        self.now=datetime.fromisoformat(self.now.date().isoformat()+'T'+observed_time+'+00:00')
        date=self.now.date().isoformat()
        evidence={}
        for role in live.EVIDENCE_ROLES:
            path=self.root/(role+'.md')
            path.write_text('SYNTHETIC_ONLY review metadata: '+role,encoding='utf-8')
            evidence[role]=dict(path=path.name,sha256=live._sha(path.read_bytes()))
        self.scope=dict(artifact_type=live.SCOPE_TYPE,scope_id='synthetic-source-observation',
            purpose='source_observation_only',market='CN_ETF',request=dict(ts_code='510300.SH',trade_date=self.day),
            session=dict(date=date,open_at=date+'T01:15:00Z',close_at=date+'T07:00:00Z',
                         daily_observation_not_before=date+'T'+observation_time+'Z',
                         timezone='Asia/Shanghai',exchange='XSHG'),
            valid_from=date+'T07:00:00Z',valid_until=date+'T08:00:00Z',request_budget=1,retry_budget=0,
            transport_limits=dict(max_response_bytes=65536,connect_seconds=3,read_seconds=3,total_seconds=10),
            holdout=deepcopy(live.HOLDOUT),context=dict(machine='office_desktop',task='factor_review',
            branch='codex/factor-review-synthetic'),review_evidence=evidence,
            implementation_binding=live.implementation_binding())
        self.save_scope()

    def save_scope(self):
        self.scope_path.write_text(json.dumps(self.scope),encoding='utf-8')

    def gate(self,*args):
        return dict(status='ready',primary_market='CN_ETF',blockers=[],generated_at=self.now.isoformat(),
                    selected={**self.scope['context'],'current_branch':self.scope['context']['branch']},
                    required_reading=[dict(path='synthetic.md',status='read',sha256='a'*64)],
                    reading_summary=dict(required=1,read=1,missing=0),
                    safety=dict(final_holdout_allowed=False,live_boundary_allowed=False))

    def hooks(self,response=None):
        self.session=Session(response or Response(payload(self.day)))
        ticks=iter(i/10 for i in range(100))
        def token():
            self.token_reads+=1
            # Scope, gate, evidence and claim must all be committed before any secret provider.
            folder=self.folder()
            for name in ('scope.json','gate.json','claim.json'):
                self.assertTrue((folder/name).is_file())
            self.assertFalse(list(folder.glob('.pending-*')))
            return TOKEN
        return dict(clock=lambda:self.now,monotonic=lambda:next(ticks),gate=self.gate,
                    token=token,session=lambda:self.session)

    def folder(self):
        identity=raw_parser.request_identity(**self.scope['request'])
        return self.root/live.ARCHIVE/'mock_requests'/live._digest(identity)

    def collect(self,response=None,*,hooks=None,execute=True,expected=None):
        return live.capture_scoped_source(self.scope_path,repo_root=self.root,execute=execute,
            expected_scope_sha256=live._digest(self.scope) if expected is None else expected,
            mock_hooks=hooks or self.hooks(response))

    def receipt(self,result):return live.verify_scoped_source_receipt(result['receipt_path'])

    def test_source_observation_succeeds_without_candidate_and_never_reads_host_secret(self):
        with patch.object(live,'_existing_token',side_effect=AssertionError('host credential read')), \
                patch.object(live,'_new_session',side_effect=AssertionError('real network factory')):
            result=self.collect()
        self.assertEqual(result['status'],'source_observed_unqualified')
        receipt=self.receipt(result)
        self.assertEqual(receipt['artifact_type'],live.RECEIPT_TYPE)
        self.assertEqual(receipt['evidence_class'],'mock_transport_contract_test')
        self.assertEqual(receipt['normalized_bar']['volume'],'1234567')
        self.assertEqual(receipt['network_requests_started'],0)
        self.assertEqual(receipt['mocked_requests_started'],1)
        self.assertEqual(receipt['strategy_forward_days_added'],0)
        self.assertFalse(receipt['candidate_qualification_granted'])
        self.assertIsNone(receipt['provider_generated_at'])
        self.assertIsNone(receipt['provider_available_at'])
        self.assertEqual(receipt['availability_upper_bound']['at'],receipt['received_at'])
        self.assertEqual(self.token_reads,1)
        url,call=self.session.calls[0]
        self.assertEqual(url,'https://api.tushare.pro')
        self.assertEqual(call['json']['params'],self.scope['request'])
        self.assertTrue(call['verify']);self.assertFalse(call['allow_redirects'])
        self.assertEqual(call['timeout'],(3,3))
        self.assertFalse(self.session.trust_env)
        self.assertEqual(self.session.proxies,{})
        for path in self.folder().iterdir():
            self.assertNotIn(TOKEN,path.read_text(encoding='utf-8'))

    def test_legal_future_scope_is_not_a_permanent_false_gate(self):
        # Deliberately supplied synthetic future session, not an exchange calendar
        # or a permission to request future/2026 prices. No time is inferred by production code.
        self.make_scope('20270105',observation_time='07:30:00',observed_time='07:31:00')
        response=Response(payload(self.day),date='Tue, 05 Jan 2027 07:31:00 GMT')
        result=self.collect(response)
        self.assertEqual(result['status'],'source_observed_unqualified')
        self.assertEqual(self.receipt(result)['normalized_bar']['date'],'2027-01-05')
        self.assertFalse(self.scope['holdout']['allow_2026_prices'])

    def test_auction_close_does_not_replace_final_daily_observation_boundary(self):
        self.make_scope('20270105',observation_time='07:30:00',observed_time='07:01:00')
        with self.assertRaisesRegex(ValueError,'closed_frozen_session'):
            self.collect()
        self.assertEqual(self.token_reads,0);self.assertFalse(self.session.calls)

    def test_preview_is_read_only_and_execution_needs_exact_hash(self):
        preview=self.collect(execute=False)
        self.assertEqual(preview['status'],'preview')
        self.assertFalse(preview['candidate_qualification_required'])
        self.assertEqual(self.token_reads,0);self.assertFalse(self.folder().exists())
        with self.assertRaisesRegex(ValueError,'exact_frozen_scope_hash'):
            self.collect(expected='0'*64)
        self.assertEqual(self.token_reads,0);self.assertFalse(self.session.calls)

    def test_holdout_wrong_purpose_multi_request_and_budget_fail_before_credentials(self):
        original=deepcopy(self.scope)
        variants=[]
        for key,value in [('purpose','strategy_search'),('request_budget',2),('retry_budget',1)]:
            changed=deepcopy(original);changed[key]=value;variants.append(changed)
        changed=deepcopy(original);changed['holdout']['allow_2026_prices']=True;variants.append(changed)
        changed=deepcopy(original);changed['holdout']['allow_2026_prices']=0;variants.append(changed)
        changed=deepcopy(original);changed['request']['ts_code']='510300.SH,518880.SH';variants.append(changed)
        changed=deepcopy(original);changed['transport_limits']['max_response_bytes']=65537;variants.append(changed)
        for variant in variants:
            self.scope=variant;self.save_scope()
            with self.assertRaises(ValueError):self.collect()
            self.assertEqual(self.token_reads,0);self.assertFalse(self.session.calls)
        self.make_scope('20261106')
        with self.assertRaisesRegex(ValueError,'2026_price_holdout_closed'):self.collect()

    def test_expiry_not_closed_evidence_change_and_runtime_change_fail_closed(self):
        original=deepcopy(self.scope)
        self.scope['valid_until']=self.scope['valid_from'];self.save_scope()
        with self.assertRaises(ValueError):self.collect()
        self.scope=deepcopy(original);self.scope['session']['close_at']=self.now.date().isoformat()+'T07:10:00Z';self.save_scope()
        with self.assertRaises(ValueError):self.collect()
        self.scope=deepcopy(original);self.scope['implementation_binding']['python']='different';self.save_scope()
        with self.assertRaisesRegex(ValueError,'implementation_or_environment_changed'):self.collect()
        self.scope=original;self.save_scope();(self.root/'calendar.md').write_text('changed')
        with self.assertRaisesRegex(ValueError,'evidence_hash_changed'):self.collect()
        self.assertEqual(self.token_reads,0)

    def test_fresh_full_gate_required_before_claim_or_token(self):
        for kind in ('blocked','stale','branch','reading','holdout'):
            hooks=self.hooks();gate=self.gate()
            if kind=='blocked':gate['status']='blocked'
            elif kind=='stale':gate['generated_at']=(self.now-timedelta(minutes=5)).isoformat()
            elif kind=='branch':gate['selected']['current_branch']='main'
            elif kind=='reading':gate['reading_summary']['missing']=1
            else:gate['safety']['final_holdout_allowed']=True
            hooks['gate']=lambda *args,value=gate:value
            with self.assertRaises(ValueError):self.collect(hooks=hooks)
            self.assertEqual(self.token_reads,0);self.assertFalse(self.folder().exists())

    def test_network_failure_consumes_claim_without_retry_or_secret_echo(self):
        result=self.collect(OSError('network error contains '+TOKEN))
        self.assertEqual(result['status'],'source_rejected')
        receipt=self.receipt(result)
        self.assertEqual(receipt['http_attempts_started'],1)
        self.assertEqual(receipt['failure_code'],'transport_or_validation_failed_redacted')
        again=self.collect()
        self.assertEqual(again['status'],'already_consumed')
        self.assertFalse(self.session.calls);self.assertEqual(self.token_reads,1)
        self.assertNotIn(TOKEN,Path(result['receipt_path']).read_text())

    def test_same_request_under_renamed_scope_is_still_consumed(self):
        first=self.collect()
        self.scope['scope_id']='different-label';self.save_scope()
        second=self.collect()
        self.assertEqual(second['status'],'already_consumed')
        self.assertEqual(first['receipt_path'],second['receipt_path'])
        self.assertFalse(self.session.calls)

    def test_hostile_response_endpoint_date_schema_and_credentials_never_form_price_input(self):
        responses=[Response(payload(),url='https://example.com'),Response(payload(),status=302),
                   Response(payload('20260102')),Response(payload(symbol='518880.SH')),
                   Response(b'{"code":0,"data":{"fields":[],"items":[]}}'),
                   Response(('{"code":1,"msg":"'+TOKEN+'"}').encode()),
                   Response(('{"code":1,"msg":"'+''.join('\\u%04x'%ord(c) for c in TOKEN)+'"}').encode())]
        for index,response in enumerate(responses):
            with self.subTest(index=index):
                # Each temporary repository owns an independent purely mocked scope.
                original_root=self.root
                self.root=original_root/str(index);self.root.mkdir();self.scope_path=self.root/'scope.json';self.make_scope()
                result=self.collect(response)
                self.assertEqual(result['status'],'source_rejected')
                self.assertIsNone(self.receipt(result)['raw_response'])
                self.assertFalse((self.folder()/'response.entity.json').exists())
                self.root=original_root;self.scope_path=self.root/'scope.json'

    def test_response_size_and_total_time_budget_are_enforced(self):
        result=self.collect(Response(b'x'*65537))
        self.assertEqual(self.receipt(result)['failure_code'],'response_byte_budget_exceeded')
        self.root=self.root/'time';self.root.mkdir();self.scope_path=self.root/'scope.json';self.make_scope()
        hooks=self.hooks();ticks=iter((0,0,1,11));hooks['monotonic']=lambda:next(ticks)
        result=self.collect(hooks=hooks)
        self.assertEqual(self.receipt(result)['failure_code'],'monotonic_request_deadline_exceeded')
        self.assertEqual(len(self.session.calls),1)

    def test_atomic_claim_failure_preserves_pending_and_never_reads_credential(self):
        with patch.object(live.os,'link',side_effect=OSError('disk unavailable')):
            result=self.collect()
        self.assertEqual(result['status'],'recovery_review_required')
        self.assertTrue(result['pending_files'])
        self.assertIn('claim.json',result['missing_files'])
        self.assertEqual(self.token_reads,0);self.assertFalse(self.session.calls)
        again=self.collect()
        self.assertEqual(again['status'],'recovery_review_required')
        self.assertFalse(self.session.calls)

    def test_receipt_publication_failure_never_reports_success_or_retries(self):
        publish=live._publish
        def fail_receipt(path,raw):
            if path.name=='receipt.json':raise live.ArchiveWriteError('disk')
            return publish(path,raw)
        with patch.object(live,'_publish',side_effect=fail_receipt):result=self.collect()
        self.assertEqual(result['status'],'recovery_review_required')
        self.assertTrue((self.folder()/'response.entity.json').is_file())
        self.assertIn('receipt.json',result['missing_files'])
        again=self.collect();self.assertEqual(again['status'],'recovery_review_required')
        self.assertFalse(self.session.calls);self.assertEqual(self.token_reads,1)

    def test_original_scope_mapping_clock_and_mock_class_are_bound(self):
        result=self.collect();path=Path(result['receipt_path'])
        original=json.loads(path.read_text())
        for field in ('mapping','clock','qualification','class','missing_raw','attempt_count'):
            receipt=deepcopy(original)
            if field=='mapping':receipt['normalized_bar']['amount']='1'
            elif field=='clock':receipt['availability_upper_bound']['at']='2025-01-02T06:00:00Z'
            elif field=='qualification':receipt['candidate_qualification_granted']=True
            elif field=='class':receipt['evidence_class']='live_source_observation'
            elif field=='missing_raw':receipt['raw_response']=None
            else:receipt['http_attempts_started']=2;receipt['mocked_requests_started']=2
            receipt.pop('sha256');receipt['sha256']=live._digest(receipt)
            path.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):live.verify_scoped_source_receipt(path)
        path.write_text(json.dumps(original))
        self.assertEqual(live.verify_scoped_source_receipt(path)['sha256'],original['sha256'])

    def test_archived_binding_is_not_current_implementation_equivalence(self):
        result=self.collect()
        with patch.object(live,'implementation_binding',return_value={'changed':'future version'}):
            receipt=live.verify_scoped_source_receipt(result['receipt_path'])
        self.assertEqual(receipt['status'],'source_observed_unqualified')
        self.assertEqual(receipt['implementation_binding'],self.scope['implementation_binding'])

    def test_mock_archive_does_not_consume_real_transport_request_slot(self):
        result=self.collect()
        identity=live._digest(raw_parser.request_identity(**self.scope['request']))
        self.assertTrue(Path(result['receipt_path']).parent.resolve().is_relative_to((self.root/live.ARCHIVE/'mock_requests').resolve()))
        self.assertFalse((self.root/live.ARCHIVE/'requests'/identity).exists())

    def test_real_slow_socket_drip_is_terminated_at_total_deadline(self):
        before={child.pid for child in multiprocessing.active_children()}
        started=time.monotonic()
        with self.assertRaisesRegex(ValueError,'isolated_transport_deadline_exceeded') as caught:
            live._bounded_worker(_slow_drip_worker,(),1.5)
        self.assertIn('slow_fixture_read_started',caught.exception.worker_events)
        self.assertLess(time.monotonic()-started,3)
        self.assertEqual({child.pid for child in multiprocessing.active_children()},before)

    def test_claim_clock_regression_prevents_request_dispatch(self):
        for index,point in enumerate(('credential','request')):
            if index:
                self.root=self.root/'request_clock';self.root.mkdir();self.scope_path=self.root/'scope.json';self.make_scope()
            self.token_reads=0
            hooks=self.hooks()
            sequence=[self.now]*(4 if point=='credential' else 5)+[self.now-timedelta(seconds=1)]
            clocks=iter(sequence);hooks['clock']=lambda:next(clocks)
            result=self.collect(hooks=hooks)
            self.assertEqual(result['status'],'source_rejected')
            receipt=self.receipt(result)
            self.assertEqual(receipt['http_attempts_started'],0)
            self.assertFalse(self.session.calls)
            self.assertEqual(self.token_reads,0 if point=='credential' else 1)

    def test_archived_claim_after_request_is_rejected_even_with_rehashed_files(self):
        result=self.collect()
        receipt_path=Path(result['receipt_path'])
        receipt=json.loads(receipt_path.read_text())
        claim_path=receipt_path.parent/'claim.json'
        claim=json.loads(claim_path.read_text())
        claim['claimed_at']=raw_parser._stamp(self.now+timedelta(seconds=1))
        claim_path.write_bytes(live._canonical(claim)+b'\n')
        receipt['claim_ref']['sha256']=live._sha(claim_path.read_bytes())
        receipt.pop('sha256');receipt['sha256']=live._digest(receipt)
        receipt_path.write_bytes(live._canonical(receipt)+b'\n')
        with self.assertRaisesRegex(ValueError,'claim_must_precede_request_inside_scope'):
            live.verify_scoped_source_receipt(receipt_path)

    def test_missing_scope_CLI_status_does_not_read_credentials_or_run_transport(self):
        with patch.object(live,'_existing_token',side_effect=AssertionError('credential read')), \
                patch.object(live,'_new_session',side_effect=AssertionError('network')):
            output=StringIO()
            with redirect_stdout(output):code=cli.main(['status'])
        self.assertEqual(code,0)
        result=json.loads(output.getvalue())
        self.assertTrue(result['source_observation_supported'])
        self.assertEqual(result['network_requests_started'],0)
        self.assertTrue(result['holdout_2026_prices_closed'])


if __name__=='__main__':unittest.main()
