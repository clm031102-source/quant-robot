from copy import deepcopy
from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research import us_fixed_allocation_2025_inputs as M


def invented_sources():
    def stamps(start,end):
        days=[];d=date.fromisoformat(start)
        while d<=date.fromisoformat(end):
            if d.weekday()<5:days.append(int(datetime(d.year,d.month,d.day,9,30,tzinfo=ZoneInfo('America/New_York')).timestamp()))
            d+=timedelta(days=1)
        return days
    def row(symbol,times):
        return {'chart':{'error':None,'result':[{'meta':{'symbol':symbol,'currency':'USD','exchangeTimezoneName':'America/New_York','instrumentType':'ETF','dataGranularity':'1d','regularMarketPrice':'SEALED'},
            'timestamp':times,'indicators':{'quote':[{k:[v]*len(times) for k,v in [('open','10'),('high','11'),('low','9'),('close','10'),('volume','100000')]}],
                'adjclose':[{'adjclose':['NEVER_DECODE_ADJUSTED']*len(times)}]},'events':{}}]}}
    new={s:row(s,stamps('2025-01-01','2025-12-31')) for s in M.ASSETS}
    warm={s:row(s,stamps('2024-11-29','2024-12-31')) for s in M.ASSETS}
    split={}
    for s in M.ASSETS:
        r=warm[s]['chart']['result'][0]
        for values in r['indicators']['quote'][0].values():values[0]='OPAQUE_OLD_NOT_DECEMBER'
        t=r['timestamp'][2];r['events']['dividends']={str(t):{'date':t,'amount':'OPAQUE_WARMUP_DIVIDEND'}}
        n=new[s]['chart']['result'][0]
        for k,v in n['indicators']['quote'][0].items():
            if k!='open':v[-1]='OPAQUE_TERMINAL'
        t=n['timestamp'][2];n['events']['dividends']={str(t):{'date':t,'amount':'0.10'}}
        sp=row(s,[1117598400]);sp['chart']['result'][0]['meta']['dataGranularity']='1mo'
        sp['chart']['result'][0]['indicators']='OPAQUE_FULL_HISTORY_PRICES'
        if s=='EFA':sp['chart']['result'][0]['events']['splits']={'1117598400':{'date':1118323800,'numerator':3.0,'denominator':1.0,'splitRatio':'3:1'}}
        split[s]=sp
    return new,warm,split


def encode(objects):return {k:json.dumps(v).encode() for k,v in objects.items()}


class FixedInputsTests(unittest.TestCase):
    def load(self,new,warm,split,callback=lambda:None):
        return M.normalize_saved_sources(encode(new),warmup_raw_by_symbol=encode(warm),split_raw_by_symbol=encode(split),
            method_sha256=M.METHOD_SHA256,provenance={},test_values=True,before_numeric_decode=callback)

    def test_exact_selection_opaque_exclusions_and_marker(self):
        sources=invented_sources();calls=[];number=M.old._number
        def check(value,**kwargs):
            self.assertEqual(calls,['marker']);return number(value,**kwargs)
        with patch.object(M.old,'_number',side_effect=check):f=self.load(*sources,callback=lambda:calls.append('marker'))
        self.assertEqual(calls,['marker']);self.assertEqual(f['schema'],'us_fixed_allocation_2025_fixture_v1')
        self.assertEqual(f['evidence_kind'],'artificial_values_true_calendar')
        self.assertTrue(f['provenance']['holding_window_splits_absent']);self.assertEqual(len(f['dividends']),4)
        self.assertTrue(all(d['prices'][s]['adj_close'] is None for d in f['days'] for s in M.ASSETS))
        self.assertEqual(f['days'][0]['date'],'2024-12-02');self.assertEqual(f['days'][-1]['prices']['SPY']['open'],'10')
        self.assertIsNone(f['days'][-1]['prices']['SPY']['volume']);self.assertNotIn('OPAQUE',json.dumps(f))

    def test_metadata_failures_before_marker(self):
        for case in ('missing_date','split','capital_gain','wrong_unit','out_of_window','month_bucket'):
            with self.subTest(case=case):
                new,warm,split=invented_sources();r=new['EFA']['chart']['result'][0]
                if case=='missing_date':
                    r['timestamp'].pop(4)
                    for values in r['indicators']['quote'][0].values():values.pop(4)
                elif case=='split':r['events']['splits']={'1':{'date':1}}
                elif case=='capital_gain':r['events']['capitalGains']={'1':{'date':1}}
                elif case=='wrong_unit':r['meta']['currency']='CNY'
                elif case=='out_of_window':r['timestamp'][-1]=1767277800
                else:split['EFA']['chart']['result'][0]['timestamp']=[]
                with patch.object(M.old,'_number',side_effect=AssertionError('number_called')) as number:
                    with self.assertRaises(ValueError):self.load(new,warm,split,lambda:self.fail('marker_called'))
                    number.assert_not_called()

    def test_required_null_fails_after_durable_callback(self):
        new,warm,split=invented_sources();new['SPY']['chart']['result'][0]['indicators']['quote'][0]['open'][0]=None
        calls=[]
        with self.assertRaisesRegex(ValueError,'required_numeric_token'):self.load(new,warm,split,lambda:calls.append('marker'))
        self.assertEqual(calls,['marker'])

    def test_bound_manifest_retains_same_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            def save(name,value):
                b=json.dumps(value).encode();(root/name).write_bytes(b)
                return {'path':name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
            method=save('method',{'artificial':True});manifest={'schema':'us_fixed_allocation_2025_sources_v1','method':method,'session_metadata':{},
                'source_outcome':save('outcome',{}),'split_projection':save('splits_projection',{})}
            for group in ('charts_2025','warmup_charts','split_metadata'):
                manifest[group]={}
                for s in M.ASSETS:
                    raw=save(group+s,{'opaque_artificial':True});receipt=save(group+s+'receipt',{'HTTP_status':200,'raw':raw,'raw_complete':True,'error':None})
                    entry={'raw':raw,'receipt':receipt}
                    if group!='split_metadata':entry['projection']=save(group+s+'projection',{})
                    manifest[group][s]=entry
            original=(root/'charts_2025SPY').read_bytes()
            def inspect(raw,**kwargs):
                (root/'charts_2025SPY').write_bytes(b'mutated_later');self.assertEqual(raw['SPY'],original)
                self.assertEqual(kwargs['session_metadata'],{});return {'artificial_metadata_only':True}
            with patch.object(M,'METHOD_SHA256',method['sha256']),patch.object(M,'normalize_saved_sources',side_effect=inspect):
                self.assertEqual(M.load_inputs(root,manifest,method_sha256=method['sha256'],registration_sha256='a'*64,
                    before_numeric_decode=lambda:self.fail('no_normalization')),{'artificial_metadata_only':True})
                with self.assertRaisesRegex(ValueError,'source_hash'):
                    M.load_inputs(root,manifest,method_sha256=method['sha256'],registration_sha256='a'*64,before_numeric_decode=lambda:None)


if __name__=='__main__':unittest.main()
