from copy import deepcopy
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import json
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research import us_monthly_rotation_inputs as M


def artificial_sources():
    day = date(2004,12,1); dates = []
    while day <= date(2024,12,31):
        if day.weekday() < 5: dates.append(day)
        day += timedelta(days=1)
    stamps = [int(datetime(d.year,d.month,d.day,9,30,tzinfo=ZoneInfo('America/New_York')).timestamp()) for d in dates]
    split_time = int(datetime(2005,6,9,9,30,tzinfo=ZoneInfo('America/New_York')).timestamp())
    event_time = int(datetime(2006,1,3,9,30,tzinfo=ZoneInfo('America/New_York')).timestamp())
    sources = {}
    for s in M.ASSETS:
        events = {'dividends':{str(event_time):{'date':event_time,'amount':'0.10'}}}
        if s == 'EFA': events['splits'] = {str(split_time):{'date':split_time,'numerator':3.0,'denominator':1.0,'splitRatio':'3:1'}}
        row = {'meta':{'symbol':s,'currency':'USD','exchangeTimezoneName':'America/New_York','instrumentType':'ETF','regularMarketPrice':'SEALED'},
               'timestamp':stamps[:], 'indicators':{'quote':[{k:['100' if k=='volume' else {'open':'10','close':'10','high':'11','low':'9'}[k]]*len(dates) for k in ('open','high','low','close','volume')}],
               'adjclose':[{'adjclose':['10']*len(dates)}]},'events':events}
        sources[s] = {'chart':{'result':[row],'error':None}}
    return sources


def artificial_monthly_metadata(objects):
    objects = deepcopy(objects)
    for obj in objects.values():
        row = obj['chart']['result'][0]
        row['meta']['dataGranularity'] = '1mo'
        buckets = sorted({datetime.fromtimestamp(t, M.NY).strftime('%Y-%m') for t in row['timestamp']})
        row['timestamp'] = [int(datetime.fromisoformat(m+'-01').replace(tzinfo=M.NY).timestamp()) for m in buckets]
        events = row.get('events', {}).get('splits', {})
        row['events']['splits'] = {str(int(datetime.fromtimestamp(e['date'], M.NY).replace(day=1,hour=0,minute=0,second=0).timestamp())):e for e in events.values()}
    return objects


class USInputsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.objects = artificial_sources()

    def load(self, changed=None, split_changed=None, **kwargs):
        objects = changed or deepcopy(self.objects)
        split_objects = artificial_monthly_metadata(split_changed or self.objects)
        raw = {s:json.dumps(v).encode() for s,v in objects.items()}
        splits = {s:json.dumps(v).encode() for s,v in split_objects.items()}
        return M.normalize_saved_sources(raw, split_raw_by_symbol=splits,
            method_sha256=M.METHOD_SHA256, provenance={'source':'invented_weekdays_and_values'}, test_values=True,
            before_numeric_decode=kwargs.pop('before_numeric_decode', lambda: {'artificial_marker':True}), **kwargs)

    def test_artificial_identity_and_terminal_sealed_values(self):
        obj = deepcopy(self.objects)
        for s in M.ASSETS:
            r = obj[s]['chart']['result'][0]
            for k in ('high','low','close','volume'): r['indicators']['quote'][0][k][-1] = 'UNREADABLE_TERMINAL'
            r['indicators']['adjclose'][0]['adjclose'][-1] = 'UNREADABLE_TERMINAL'
            # A warmup distribution amount must not be converted into the account.
            t = r['timestamp'][5]; r['events']['dividends'][str(t)]={'date':t,'amount':'WARMUP_OPAQUE'}
        result = self.load(obj)
        self.assertEqual(result['evidence_kind'],'artificial_values_true_calendar')
        self.assertEqual(result['first_decision_date'],'2005-12-30')
        self.assertFalse(result['provenance']['constructed_from_market_data'])
        self.assertEqual(len(result['dividends']),4)
        self.assertTrue(result['days'][-1]['terminal_open_only'])
        self.assertIsNone(result['days'][-1]['prices']['SPY']['close'])
        self.assertNotIn('SEALED', json.dumps(result))

    def test_date_sets_null_lengths_and_units_fail_closed(self):
        for kind in ('missing_date','null','length','currency','timezone','symbol','field'):
            with self.subTest(kind=kind):
                obj = deepcopy(self.objects); row = obj['EFA']['chart']['result'][0]
                if kind == 'missing_date':
                    row['timestamp'].pop(30)
                    for values in row['indicators']['quote'][0].values(): values.pop(30)
                    row['indicators']['adjclose'][0]['adjclose'].pop(30)
                elif kind == 'null': row['indicators']['quote'][0]['close'][30]=None
                elif kind == 'length': row['indicators']['quote'][0]['open'].pop()
                elif kind == 'field': del row['indicators']['quote'][0]['volume']
                else: row['meta'][{'timezone':'exchangeTimezoneName'}.get(kind,kind)]='WRONG'
                with self.assertRaises(ValueError): self.load(obj)

    def test_split_chain_and_capital_gains_fail_closed(self):
        for kind in ('missing_split','extra_split','capital_gains','full_history_split'):
            with self.subTest(kind=kind):
                obj=deepcopy(self.objects); full=deepcopy(self.objects)
                if kind=='missing_split': obj['EFA']['chart']['result'][0]['events']['splits']={}
                elif kind=='capital_gains': obj['SPY']['chart']['result'][0]['events']['capitalGains']={'unexpected':{}}
                else:
                    target=full if kind=='full_history_split' else obj
                    target['SPY']['chart']['result'][0]['events']['splits']=deepcopy(obj['EFA']['chart']['result'][0]['events']['splits'])
                with self.assertRaises(ValueError): self.load(obj,full)

    def test_ny_event_dates_and_numeric_contract(self):
        self.assertEqual(M._day(str(int(datetime(2006,1,4,0,30,tzinfo=ZoneInfo('UTC')).timestamp()))),'2006-01-03')
        for value in (None,True,1.2,'NaN','Infinity','-1'):
            with self.subTest(value=value), self.assertRaises(ValueError): M._number(value)
        self.assertEqual(M._number('0',volume=True),'0')
        self.assertEqual(M._number('1e1'),'1E+1')
        with self.assertRaises(ValueError): M._opaque(b'{"x":1,"x":2}')
        with self.assertRaises(ValueError): M._opaque(b'{"x":NaN}')

    def test_outer_marker_required_before_any_number(self):
        raw={s:json.dumps(v).encode() for s,v in self.objects.items()}
        with patch.object(M,'_number',side_effect=AssertionError('decoded_before_marker')) as number:
            with self.assertRaisesRegex(ValueError,'outer_registration'):
                M.normalize_saved_sources(raw,split_raw_by_symbol=raw,method_sha256=M.METHOD_SHA256,provenance={},before_numeric_decode=lambda:None)
            number.assert_not_called()

    def test_callback_once_after_structure_before_numeric_and_same_bytes(self):
        count=[]
        real=M._number
        def checked(token,**kwargs):
            self.assertEqual(count,['marker'])
            return real(token,**kwargs)
        with patch.object(M,'_number',side_effect=checked):
            fixture=self.load(before_numeric_decode=lambda:count.append('marker'))
        self.assertEqual(count,['marker'])
        evidence=fixture['provenance']['split_event_metadata']['EFA']
        self.assertEqual(evidence['monthly_metadata'][0]['source_key'],'1117598400')
        self.assertEqual(evidence['monthly_metadata'][0]['event_timestamp'],'1118323800')
        self.assertEqual(evidence['daily'][0]['source_key'],'1118323800')
        obj=deepcopy(self.objects);obj['GLD']['chart']['result'][0]['meta']['currency']='CNY'
        with self.assertRaises(ValueError): self.load(obj,before_numeric_decode=lambda:self.fail('marker_before_identity'))

    def test_monthly_split_real_shape_with_opaque_prices_reaches_marker_only(self):
        daily=deepcopy(self.objects);monthly=artificial_monthly_metadata(self.objects)
        for obj in monthly.values():
            row=obj['chart']['result'][0]
            row['indicators']={'quote':[{'close':['OPAQUE_PRICE_NOT_DECODED']} ]}
            row['meta']['regularMarketPrice']='OPAQUE_CURRENT_QUOTE'
        event=monthly['EFA']['chart']['result'][0]['events']['splits']
        self.assertEqual(event,{'1117598400':{'date':1118323800,'numerator':3.0,'denominator':1.0,'splitRatio':'3:1'}})
        raw={s:json.dumps(v).encode() for s,v in daily.items()}
        splits={s:json.dumps(v).encode() for s,v in monthly.items()}
        calls=[]
        def marker():
            calls.append('marker');raise RuntimeError('artificial_stop_before_financial_decode')
        with patch.object(M,'_number',side_effect=AssertionError('numeric_decode_forbidden')) as number:
            with self.assertRaisesRegex(RuntimeError,'artificial_stop_before_financial_decode'):
                M.normalize_saved_sources(raw,split_raw_by_symbol=splits,method_sha256=M.METHOD_SHA256,
                    provenance={},test_values=True,before_numeric_decode=marker)
            number.assert_not_called()
        self.assertEqual(calls,['marker'])

    def test_split_bucket_invalid_or_daily_mismatch_rejected_before_marker(self):
        for kind in ('wrong_month','not_month_start','missing_bucket','duplicate_bucket','wrong_interval','daily_mismatch'):
            with self.subTest(kind=kind):
                daily=deepcopy(self.objects);monthly=artificial_monthly_metadata(self.objects)
                row=monthly['EFA']['chart']['result'][0];old='1117598400'
                if kind in ('wrong_month','not_month_start'):
                    new='1114920000' if kind=='wrong_month' else '1117684800'
                    row['events']['splits'][new]=row['events']['splits'].pop(old)
                elif kind=='missing_bucket':row['timestamp'].remove(int(old))
                elif kind=='duplicate_bucket':row['timestamp'].append(int(old))
                elif kind=='wrong_interval':row['meta']['dataGranularity']='1d'
                else:
                    splits=daily['EFA']['chart']['result'][0]['events']['splits']
                    splits[old]=splits.pop('1118323800')
                with patch.object(M,'_number',side_effect=AssertionError('numeric_decode_forbidden')) as number:
                    with self.assertRaises(ValueError):
                        M.normalize_saved_sources({s:json.dumps(v).encode() for s,v in daily.items()},
                            split_raw_by_symbol={s:json.dumps(v).encode() for s,v in monthly.items()},
                            method_sha256=M.METHOD_SHA256,provenance={},test_values=True,
                            before_numeric_decode=lambda:self.fail('invalid_structure_reached_marker'))
                    number.assert_not_called()

    def test_bound_manifest_interface_retains_bytes_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            def save(name,value):
                data=value if isinstance(value,bytes) else json.dumps(value).encode()
                (root/name).write_bytes(data)
                return {'path':name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
            method=save('method.json',{'artificial_method':True})
            manifest={'schema':'us_monthly_rotation_sources_v1','method':method,'charts':{},'split_metadata':{},
                      'split_projection':save('split_projection.json',{}),'remaining_source_outcome':save('outcome.json',{})}
            for s in M.ASSETS:
                raw=save(s+'.raw',self.objects[s])
                manifest['charts'][s]={'raw':raw,'receipt':save(s+'.receipt',{'HTTP_status':200,'raw':raw,'raw_complete':True}),
                                       'projection':save(s+'.projection',{})}
                split=save(s+'.split',self.objects[s])
                manifest['split_metadata'][s]={'raw':split,'receipt':save(s+'.split_receipt',{'status':200,'error':None,'raw_sha256':split['sha256']})}
            original=(root/'SPY.raw').read_bytes()
            def inspect_bound(raw,**kwargs):
                (root/'SPY.raw').write_bytes(b'changed-after-read')
                self.assertEqual(raw['SPY'],original)
                self.assertTrue(callable(kwargs['before_numeric_decode']))
                return {'artificial_interface_only':True}
            with patch.object(M,'METHOD_SHA256',method['sha256']),patch.object(M,'normalize_saved_sources',side_effect=inspect_bound):
                self.assertEqual(M.load_inputs(root,manifest,method_sha256=method['sha256'],registration_sha256='a'*64,
                    before_numeric_decode=lambda:self.fail('mock_adapter_does_not_decode')),{'artificial_interface_only':True})
                with self.assertRaisesRegex(ValueError,'source_bytes_mismatch'):
                    M.load_inputs(root,manifest,method_sha256=method['sha256'],registration_sha256='a'*64,
                                  before_numeric_decode=lambda:self.fail('must_not_decode_drift'))


if __name__ == '__main__': unittest.main()
