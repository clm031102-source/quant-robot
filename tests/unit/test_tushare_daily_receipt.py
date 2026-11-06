"""Synthetic HTTP entity fixtures only; never requests credentials or market data."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.data.sources.tushare_mapping import map_tushare_daily
from quant_robot.ops import tushare_daily_receipt as subject
from scripts import capture_tushare_paper_daily as cli


TOKEN = 'synthetic-offline-credential-123456'
START = '2020-01-02T07:00:01Z'
RECEIVED = '2020-01-02T07:00:03Z'
HTTP_DATE = 'Thu, 02 Jan 2020 07:00:02 GMT'


def payload():
    return {'code':0, 'msg':None, 'data': {'fields':list(subject.FIELDS),
            'items':[['510300.SH','20200102',4.111,4.222,4.001,4.125,12345.67,98765.432]],
            'count':-999}}


def body():
    value = payload()
    value['data'].pop('count')
    return json.dumps(value, separators=(',', ':')).encode('utf-8')


class Response:
    def __init__(self, raw=None, *, status=200, url=subject.SOURCE_URL, date=HTTP_DATE):
        self.raw = body() if raw is None else raw
        self.status_code, self.url = status, url
        self.headers = {'Date':date} if date is not None else {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, chunk_size):
        yield self.raw[:20]
        yield self.raw[20:]


class Transport:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url,kwargs))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class DailyReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def capture(self, response=None, *, archive=None, times=(START,RECEIVED), **kwargs):
        self.transport = Transport(response or Response())
        clock = iter(times)
        return subject.capture_synthetic_receipt(archive or self.root, ts_code='510300.SH',
            trade_date='20200102', token=TOKEN, transport=self.transport,
            clock=lambda: next(clock), **kwargs)

    def read(self, result):
        return subject.verify_receipt(result['receipt_path'])

    def test_raw_bytes_request_and_time_receipt_without_publication_claim(self):
        raw = body()
        result = self.capture(Response(raw))
        self.assertEqual(result['status'], 'captured_synthetic')
        receipt = self.read(result)
        self.assertEqual((Path(result['receipt_path']).parent/'response.entity.json').read_bytes(),raw)
        self.assertEqual(receipt['request_started_at'],'2020-01-02T07:00:01.000000Z')
        self.assertEqual(receipt['received_at'],'2020-01-02T07:00:03.000000Z')
        self.assertEqual(receipt['http_clock']['http_date'],HTTP_DATE)
        self.assertIsNone(receipt['provider_generated_at'])
        self.assertIsNone(receipt['provider_available_at'])
        self.assertFalse(receipt['real_forward_eligible'])
        self.assertFalse(receipt['source_quality_verified'])
        self.assertFalse(receipt['live_capture_enabled'])
        self.assertEqual(receipt['evidence_class'],'synthetic_only')
        self.assertEqual(receipt['availability_upper_bound']['at'],receipt['received_at'])
        url, request = self.transport.calls[0]
        self.assertEqual(url,subject.SOURCE_URL)
        self.assertEqual(request['json']['api_name'],'fund_daily')
        self.assertEqual(request['json']['params'],{'ts_code':'510300.SH','trade_date':'20200102'})
        self.assertEqual(request['json']['fields'],','.join(subject.FIELDS))
        self.assertTrue(request['verify'])
        self.assertFalse(request['allow_redirects'])
        self.assertFalse(self.transport.trust_env)
        for file in self.root.rglob('*'):
            if file.is_file():
                self.assertNotIn(TOKEN,file.read_text(encoding='utf-8'))

    def test_exact_unit_scaling_matches_existing_mapping_without_inventing_flags(self):
        parsed = subject.parse_fund_daily_body(body(),ts_code='510300.SH',trade_date='20200102')
        bar = parsed['bar']
        self.assertEqual(bar['volume'],'1234567')
        self.assertEqual(bar['amount'],'98765432')
        self.assertEqual(bar['open'],'4.111')
        value = json.loads(body())
        mapped = map_tushare_daily(pd.DataFrame(value['data']['items'],columns=value['data']['fields'])).iloc[0]
        self.assertEqual(float(bar['volume']),mapped['volume'])
        self.assertEqual(float(bar['amount']),mapped['amount'])
        self.assertFalse(parsed['corporate_actions_complete'])
        self.assertIsNone(parsed['corporate_actions'])
        self.assertFalse(parsed['execution_constraints_complete'])
        self.assertFalse(parsed['asset_membership_verified'])
        for flag in ('suspended','limit_up','limit_down'):
            self.assertIsNone(bar[flag])

    def test_long_decimal_is_exact_and_exponent_expansion_is_bounded(self):
        raw=body().replace(b'12345.67',b'0.12345678901234567890123456789')
        parsed=subject.parse_fund_daily_body(raw,ts_code='510300.SH',trade_date='20200102')
        self.assertEqual(parsed['bar']['volume'],'12.345678901234567890123456789')
        raw=body().replace(b'12345.67',b'1e100000000')
        with self.assertRaisesRegex(ValueError,'precision_budget'):
            subject.parse_fund_daily_body(raw,ts_code='510300.SH',trade_date='20200102')

    def test_field_order_is_mapped_by_name_and_count_is_unverified_metadata(self):
        value = json.loads(body())
        value['data']['fields'].reverse()
        value['data']['items'][0].reverse()
        value['data']['count']=777
        parsed = subject.parse_fund_daily_body(json.dumps(value).encode(),ts_code='510300.SH',trade_date='20200102')
        self.assertEqual(parsed['bar']['volume'],'1234567')
        self.assertEqual(parsed['provider_count'],777)
        self.assertFalse(parsed['provider_count_semantics_verified'])

    def test_missing_stale_or_invalid_HTTP_Date_never_becomes_publication_time(self):
        for index, date in enumerate((None,'Thu, 02 Jan 2020 06:59:00 GMT','not a date')):
            result = self.capture(Response(date=date),archive=self.root/str(index))
            receipt = self.read(result)
            self.assertEqual(receipt['status'], 'capture_rejected' if date=='not a date'
                              else 'captured_synthetic_clock_review_required')
            self.assertIsNone(receipt['provider_available_at'])
            self.assertFalse(receipt['real_forward_eligible'])

    def test_changed_symbol_date_rows_fields_and_bad_amount_are_rejected(self):
        variants=[]
        for field,value in [('ts_code','518880.SH'),('trade_date','20200103'),('amount',None),('amount',-1),('vol',True)]:
            changed=json.loads(body())
            changed['data']['items'][0][changed['data']['fields'].index(field)]=value
            variants.append(changed)
        missing=json.loads(body());missing['data']['fields'].pop();missing['data']['items'][0].pop();variants.append(missing)
        extra=json.loads(body());extra['data']['items'].append(extra['data']['items'][0]);variants.append(extra)
        empty=json.loads(body());empty['data']['items']=[];variants.append(empty)
        for index,variant in enumerate(variants):
            result=self.capture(Response(json.dumps(variant).encode()),archive=self.root/str(index))
            receipt=self.read(result)
            self.assertEqual(receipt['status'],'capture_rejected')
            self.assertIsNone(receipt['parsed'])
            self.assertIsNotNone(receipt['response_body'])

    def test_duplicate_keys_nan_and_secret_echo_are_not_archived(self):
        escaped=''.join('\\u%04x'%ord(char) for char in TOKEN)
        rows=[b'{"code":0,"code":1}',body().replace(b'4.111',b'NaN'),
              ('{"code":1,"msg":"'+TOKEN+'"}').encode(),
              ('{"code":1,"msg":"'+escaped+'"}').encode()]
        for index,raw in enumerate(rows):
            result=self.capture(Response(raw),archive=self.root/str(index))
            receipt=self.read(result)
            self.assertEqual(receipt['status'],'capture_rejected')
            self.assertIsNone(receipt['response_body'])
            self.assertFalse((Path(result['receipt_path']).parent/'response.entity.json').exists())
            self.assertNotIn(TOKEN,Path(result['receipt_path']).read_text())

    def test_transport_exception_is_redacted_and_not_retried(self):
        for index, error in enumerate((RuntimeError('request token='+TOKEN),subject.ReceiptError(TOKEN))):
            result=self.capture(error,archive=self.root/str(index))
            receipt=self.read(result)
            self.assertEqual(receipt['failure_code'],'transport_or_unclassified_failure_redacted')
            self.assertNotIn(TOKEN,Path(result['receipt_path']).read_text())
            self.assertEqual(len(self.transport.calls),1)

    def test_unparseable_header_never_persists_disguised_credential_text(self):
        escaped='\\u0073'+TOKEN[1:]
        result=self.capture(Response(date=escaped))
        receipt=self.read(result)
        self.assertEqual(receipt['http_clock']['status'],'unparseable')
        self.assertIsNone(receipt['http_clock']['http_date'])
        self.assertNotIn(escaped,Path(result['receipt_path']).read_text())
        self.assertNotIn(TOKEN,Path(result['receipt_path']).read_text())

    def test_no_live_or_multi_symbol_request_can_reach_transport(self):
        transport=Transport(Response())
        for kwargs in ({'synthetic_only':False},{'ts_code':'510300.SH,518880.SH'},
                       {'trade_date':'20200102,20200103'}):
            inputs=dict(ts_code='510300.SH',trade_date='20200102',token=TOKEN,
                        transport=transport,clock=lambda:START)
            inputs.update(kwargs)
            with self.assertRaises(ValueError):
                subject.capture_synthetic_receipt(self.root,**inputs)
        self.assertFalse(transport.calls)
        self.assertFalse(list(self.root.iterdir()))

    def test_redirect_host_change_http_failure_size_and_clock_regression_reject(self):
        responses=[Response(status=302),Response(url='http://api.tushare.pro'),
                   Response(url='https://example.com'),Response(b'x'*(subject.MAX_BYTES+1))]
        for index,response in enumerate(responses):
            result=self.capture(response,archive=self.root/str(index))
            self.assertEqual(self.read(result)['status'],'capture_rejected')
        result=self.capture(archive=self.root/'clock',times=(RECEIVED,START))
        self.assertEqual(self.read(result)['failure_code'],'host_clock_regressed')

    def test_one_attempt_is_immutable_and_incomplete_attempt_is_not_retried(self):
        first=self.capture()
        receipt_path=Path(first['receipt_path'])
        before={p:p.read_bytes() for p in receipt_path.parent.iterdir()}
        replay=self.capture()
        self.assertEqual(replay['status'],'already_captured')
        self.assertFalse(self.transport.calls)
        for path,raw in before.items():self.assertEqual(path.read_bytes(),raw)
        receipt_path.unlink()
        replay=self.capture()
        self.assertEqual(replay['status'],'attempt_incomplete')
        self.assertFalse(self.transport.calls)

    def test_tampered_raw_or_mapping_or_receipt_class_fails_validation(self):
        for index,part in enumerate(('raw','mapping','class','quality')):
            result=self.capture(archive=self.root/str(index))
            path=Path(result['receipt_path'])
            if part=='raw':
                (path.parent/'response.entity.json').write_bytes(b'changed')
            else:
                receipt=json.loads(path.read_text())
                if part=='mapping':receipt['parsed']['bar']['amount']='1'
                elif part=='class':receipt['evidence_class']='real_forward'
                else:receipt['source_quality_verified']=True
                receipt.pop('sha256')
                receipt['sha256']=subject._sha(subject._canonical(receipt))
                path.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):subject.verify_receipt(path)

    def test_success_cannot_lose_original_bytes_or_rewrite_clock_relationships(self):
        for index,part in enumerate(('missing_raw','missing_received','missing_clock','byte_count',
                                     'available_bound','http_clock')):
            result=self.capture(archive=self.root/str(index))
            path=Path(result['receipt_path'])
            receipt=json.loads(path.read_text())
            if part=='missing_raw':
                receipt['response_body']=None
                (path.parent/'response.entity.json').unlink()
            elif part=='missing_received':receipt['received_at']=None
            elif part=='missing_clock':receipt['http_clock']=None
            elif part=='byte_count':receipt['response_bytes']+=1
            elif part=='available_bound':receipt['availability_upper_bound']['at']=START
            else:receipt['http_clock']['http_date_utc']='2020-01-02T08:00:00.000000Z'
            receipt.pop('sha256')
            receipt['sha256']=subject._sha(subject._canonical(receipt))
            path.write_text(json.dumps(receipt))
            with self.assertRaises(ValueError):subject.verify_receipt(path)

    def test_cli_live_is_closed_without_credentials_or_input_reads(self):
        with patch.object(cli,'capture_synthetic_receipt',side_effect=AssertionError('capture called')), \
                patch.object(Path,'read_bytes',side_effect=AssertionError('source file read')):
            output=StringIO()
            with redirect_stdout(output):code=cli.main(['capture-live'])
        result=json.loads(output.getvalue())
        self.assertEqual(code,2)
        self.assertEqual(result['network_requests'],0)
        self.assertFalse(result['credentials_read'])
        self.assertEqual(result['reason'],'live_transport_not_implemented_or_reviewed')

    def test_cli_fixture_roundtrip_keeps_mode_synthetic_and_inspects_bound_bytes(self):
        raw_path=self.root/'synthetic.response.json'
        raw_path.write_bytes(body())
        output=StringIO()
        with redirect_stdout(output):
            code=cli.main(['capture-fixture','--body',str(raw_path),'--archive',str(self.root/'archive'),
                '--ts-code','510300.SH','--trade-date','20200102','--started-at',START,
                '--received-at',RECEIVED,'--http-date',HTTP_DATE])
        result=json.loads(output.getvalue())
        self.assertEqual(code,0)
        self.assertEqual(result['status'],'captured_synthetic')
        output=StringIO()
        with redirect_stdout(output):code=cli.main(['inspect','--receipt',result['receipt_path']])
        self.assertEqual(code,0)
        self.assertEqual(json.loads(output.getvalue())['evidence_class'],'synthetic_only')


if __name__=='__main__':
    unittest.main()
