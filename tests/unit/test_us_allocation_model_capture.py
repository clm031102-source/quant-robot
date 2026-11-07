"""Artificial HTTP objects / invented source values; never network or accounts."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from email.message import Message
from http.client import IncompleteRead
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError
from urllib.request import Request

from quant_robot.ops import us_allocation_model_capture as T
from quant_robot.ops import us_allocation_source_contract as C


class Response:
    def __init__(self, body=b'{}', *, code=200, length=None, fault=None):
        self.code=code; self.body=io.BytesIO(body); self.closed=False; self.reads=0
        self.headers=Message(); self.headers['Content-Type']='application/json'
        self.headers['Content-Length']=str(len(body) if length is None else length)
        self.headers['Set-Cookie']='MUST_NOT_RETAIN_COOKIE'; self.fault=fault
    def read(self,n):
        self.reads+=1
        if self.fault is not None and self.reads>1:raise self.fault
        return self.body.read(n)
    def close(self):self.closed=True


def artificial_calendar():
    ref=dict(path='invented-calendar',sha256='a'*64,bytes=1)
    sessions=[]; current=date(2004,1,2)
    while len(sessions)<24:
        if current.weekday()<5:
            row=dict(date=current.isoformat())
            for field,hour,minute in [('open_at',9,30),('close_at',16,0)]:
                row[field]=datetime(current.year,current.month,current.day,hour,minute,tzinfo=C.NY).astimezone(timezone.utc).isoformat()
            sessions.append(row)
        current+=timedelta(days=1)
    authorities={kind:dict(kind=kind,definition_ref=deepcopy(ref)) for kind in
                 ('provider_daily_completed','corporate_action_coverage')}
    return dict(source_ref=ref,sessions=sessions),authorities


def artificial_body(symbol, dates):
    stamps=[int(datetime.fromisoformat(d+'T09:30:00').replace(tzinfo=C.NY).timestamp()) for d in dates]
    row=dict(meta=dict(symbol=symbol,currency='USD',exchangeTimezoneName='America/New_York',
        instrumentType='ETF',dataGranularity='1d',regularMarketPrice='NEVER_CONVERT_QUOTE'),timestamp=stamps,
        indicators=dict(quote=[{field:[value]*len(dates) for field,value in
            [('open','10'),('close','10'),('volume','10000'),('high','NEVER_CONVERT_HIGH'),('low','NEVER_CONVERT_LOW')]}],
            adjclose=[dict(adjclose=['NEVER_CONVERT_ADJUSTED']*len(dates))]),
        events=dict(dividends={str(stamps[0]):dict(date=stamps[0],amount='NEVER_CONVERT_WARMUP_DIVIDEND')}))
    return json.dumps(dict(chart=dict(error=None,result=[row]))).encode()


class CaptureTests(unittest.TestCase):
    def fetch(self, root, response, *, cap=T.CAP, name='spy', opened=None):
        url=T.expected_url('SPY','2004-01-01','2004-01-03'); prefix=Path(root)/name
        def start(req,timeout):
            self.assertTrue(prefix.with_name(name+'_request.json').exists())
            self.assertTrue(prefix.with_name(name+'_attempt.json').exists())
            self.assertEqual(req.get_method(),'GET');self.assertEqual(req.get_header('Accept-encoding'),'identity')
            self.assertLessEqual(timeout,20)
            if opened is not None:opened.append(True)
            if isinstance(response,Exception):raise response
            return response
        with patch.object(T,'build_opener',return_value=Mock(open=start)) as factory:
            result=T.fetch_one(url,prefix,max_body_bytes=cap)
        self.assertEqual(len(factory.call_args.args),1)
        self.assertIsInstance(factory.call_args.args[0],T._NoRedirect)
        self.assertEqual(factory.call_args.kwargs,{})
        return result

    def test_one_attempt_exact_bytes_headers_and_duplicate_reservation(self):
        with tempfile.TemporaryDirectory() as root:
            original='{"artificial":"换行\\n🙂"}'.encode(); response=Response(original); opened=[]
            raw,ref,receipt,receipt_ref=self.fetch(root,response,opened=opened)
            self.assertEqual(raw,original);self.assertEqual(T._bound(ref),original)
            self.assertEqual(json.loads(T._bound(receipt_ref)),receipt);self.assertEqual(opened,[True])
            self.assertEqual(receipt['HTTP_attempts_started'],1);self.assertTrue(receipt['raw_complete'])
            self.assertNotIn('Set-Cookie',receipt['headers']);self.assertIsNone(receipt['error']);self.assertTrue(response.closed)
            self.assertFalse(receipt['independent_worker_used']);self.assertFalse(receipt['independent_wall_timeout'])
            request=json.loads(T._bound(receipt['request']))
            self.assertFalse(request['application_credentials_added'])
            self.assertEqual(request['proxy_configuration'],'urllib_default_environment_or_system_not_inspected')
            self.assertNotIn('credentials_used',request)
            clocks=[C._instant(receipt[k]) for k in ('request_started_at','headers_received_at','body_completed_at','retained_at')]
            self.assertEqual(clocks,sorted(clocks))
            with patch.object(T,'build_opener',side_effect=AssertionError('must_not_dispatch')):
                with self.assertRaisesRegex(ValueError,'already_reserved_no_retry'):
                    T.fetch_one(receipt['url'],Path(root)/'spy')

    def test_partial_timeout_HTTP_failure_and_byte_probe_are_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            cases=[('cap',Response(b'123456'),4,b'12345','body_cap_exceeded',False),
                   ('length',Response(b'1234',length=9),20,b'1234','content_length_mismatch',False),
                   ('timeout',Response(b'1234',fault=TimeoutError()),20,b'1234','socket_timeout',False),
                   ('partial',Response(b'1234',fault=IncompleteRead(b'56',10)),20,b'123456','incomplete_HTTP_body',False),
                   ('http',Response(b'OPAQUE_ERROR_BODY',code=503),50,b'OPAQUE_ERROR_BODY','HTTP_error',True)]
            for name,response,cap,expected,error,complete in cases:
                with self.subTest(case=name):
                    raw,ref,receipt,_=self.fetch(root,response,cap=cap,name=name)
                    self.assertEqual(raw,expected);self.assertEqual(T._bound(ref),expected)
                    self.assertEqual(receipt['error'],error);self.assertEqual(receipt['raw_complete'],complete)
                    self.assertEqual(receipt['HTTP_attempts_started'],1)
                    self.assertEqual(receipt['bytes_received'],len(expected));self.assertEqual(receipt['bytes_retained'],len(expected))
                    self.assertIsNotNone(receipt['failed_at']);self.assertLessEqual(len(raw),cap+1)
            self.assertEqual(json.loads((Path(root)/'cap_receipt.json').read_bytes())['oversize_detection_bytes'],1)

    def test_redirect_never_followed_and_pre_dispatch_failure_is_zero(self):
        url=T.expected_url('SPY','2004-01-01','2004-01-03')
        with tempfile.TemporaryDirectory() as root:
            headers=Message();headers['Location']='https://unapproved.invalid/next';headers['Content-Length']='3'
            error=HTTPError(url,302,'redirect',headers,io.BytesIO(b'RAW'))
            raw,_,receipt,_=self.fetch(root,error)
            self.assertEqual(raw,b'RAW');self.assertEqual(receipt['error'],'redirect_blocked')
            self.assertEqual(receipt['HTTP_status'],302);self.assertEqual(receipt['HTTP_attempts_started'],1)
            self.assertIsNone(T._NoRedirect().redirect_request(Request(url),None,302,'',headers,headers['Location']))
            with patch.object(T,'build_opener',side_effect=OSError('SECRET_ERROR_TEXT')):
                _,ref,receipt,_=T.fetch_one(url,Path(root)/'before')
            self.assertIsNone(ref);self.assertEqual(receipt['HTTP_attempts_started'],0)
            self.assertIsNone(receipt['attempt']);self.assertNotIn('SECRET',json.dumps(receipt))
            with patch.object(T,'build_opener',side_effect=AssertionError('expired_must_not_dispatch')):
                _,_,expired,_=T.fetch_one(url,Path(root)/'expired',deadline_at='2000-01-01T00:00:00Z')
            self.assertEqual(expired['HTTP_attempts_started'],0);self.assertEqual(expired['error'],'deadline')
            raw,ref,receipt,_=self.fetch(root,URLError('SECRET_ERROR_TEXT'),name='during')
            self.assertEqual(raw,b'');self.assertIsNone(ref);self.assertEqual(receipt['HTTP_attempts_started'],1)
            self.assertEqual(receipt['error'],'transport_error');self.assertNotIn('SECRET',json.dumps(receipt))

    def test_interrupted_call_has_only_intent_and_partial_not_final_count(self):
        with tempfile.TemporaryDirectory() as root:
            response=Response(b'PARTIAL',fault=KeyboardInterrupt())
            with self.assertRaises(KeyboardInterrupt):self.fetch(root,response)
            self.assertTrue((Path(root)/'spy_request.json').exists())
            intent=json.loads((Path(root)/'spy_attempt.json').read_bytes())
            self.assertFalse(intent['actual_dispatch_confirmed'])
            self.assertEqual((Path(root)/'spy_raw.body').read_bytes(),b'PARTIAL')
            self.assertFalse((Path(root)/'spy_receipt.json').exists())

    def bundle(self,root,*,warmup=True,missing=False):
        schedule,authorities=artificial_calendar();target=schedule['sessions'][20]['date']
        wanted=[x['date'] for x in schedule['sessions'][:20]] if warmup else [target]
        key='warmup' if warmup else target
        # Artificial responses and artificial clock, never actual 2026 values.
        now=C._instant(schedule['sessions'][19 if warmup else 20]['close_at'])+timedelta(minutes=16)
        scope=dict(operation_dates=[target],requests={key:dict(urls={})});captured={}
        for symbol in C.ASSETS:
            end=(date.fromisoformat(wanted[-1])+timedelta(days=1)).isoformat()
            url=T.expected_url(symbol,wanted[0],end);scope['requests'][key]['urls'][symbol]=url
            body=artificial_body(symbol,wanted[:-1] if missing and symbol=='GLD' else wanted)
            with patch.object(T,'build_opener',return_value=Mock(open=Mock(return_value=Response(body)))),patch.object(T,'_now',return_value=now):
                captured[symbol]=T.fetch_one(url,Path(root)/symbol)
        manifest=dict(schedule=schedule,authorities=authorities)
        batch_ref=T._save(Path(root)/'sources.json',{s:dict(raw=x[1],receipt=x[3]) for s,x in captured.items()})
        prior=dict(prior_session_date=schedule['sessions'][19]['date'],prior_committed_ref=deepcopy(schedule['source_ref']),
                   prior_committed_at=(C._instant(schedule['sessions'][20]['open_at'])-timedelta(hours=1)).isoformat())
        return scope,manifest,key,captured,batch_ref,prior

    def test_four_sources_bind_batch_and_build_metadata_without_numeric_conversion(self):
        for warmup in (True,False):
            with self.subTest(warmup=warmup),tempfile.TemporaryDirectory() as root:
                scope,manifest,key,captured,batch_ref,prior=self.bundle(root,warmup=warmup)
                with patch.object(C,'_number',side_effect=AssertionError('numeric_decoder_must_not_run')):
                    packet=T.build_source_packet(scope,manifest,key,captured,batch_ref,**prior)
                self.assertEqual(packet['source_ref'],batch_ref)
                self.assertTrue(C.assess_source_metadata(packet,manifest['schedule'],authorities=manifest['authorities'])['requirements_met'])
                self.assertNotIn('NEVER_CONVERT',json.dumps(packet));self.assertNotIn('amount',json.dumps(packet))
                for symbol in C.ASSETS:
                    self.assertEqual(packet['records'][symbol]['source_ref'],captured[symbol][1])
                    self.assertEqual(packet['records'][symbol]['execution'],dict(suspended=None,buy_blocked=None,sell_blocked=None))
                if warmup:self.assertEqual(len(packet['warmup_dates']),20)
                else:
                    self.assertEqual(packet['previous_committed_decision_ref'],prior['prior_committed_ref'])
                    self.assertIsNone(packet['records']['SPY']['provider_available_at'])

    def test_missing_day_or_changed_batch_or_receipt_is_rejected(self):
        for failure in ('missing_day','batch_changed','receipt_changed','request_changed','prior_unknown'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as root:
                scope,manifest,key,captured,batch_ref,prior=self.bundle(root,warmup=failure!='prior_unknown',missing=failure=='missing_day')
                if failure=='batch_changed':Path(batch_ref['path']).write_bytes(b'{}')
                if failure=='receipt_changed':captured['SPY'][2]['HTTP_status']=201
                if failure=='request_changed':Path(captured['SPY'][2]['request']['path']).write_bytes(b'{}')
                if failure=='prior_unknown':prior['prior_session_date']=None
                with patch.object(C,'_number',side_effect=AssertionError('numeric_decoder_must_not_run')):
                    with self.assertRaises(ValueError):T.build_source_packet(scope,manifest,key,captured,batch_ref,**prior)


if __name__=='__main__':unittest.main()
