"""Invented metadata only: no prices, source reads or network."""
from copy import deepcopy
from datetime import date,datetime,timedelta
import hashlib
import json
import unittest
from unittest.mock import patch
from quant_robot.ops import us_allocation_source_contract as C


def artificial_metadata(purpose='warmup'):
    ref={'path':'artificial-only','sha256':'a'*64,'bytes':1}
    authorities={kind:{'kind':kind,'definition_ref':deepcopy(ref)} for kind in
        ('provider_daily_completed','exchange_official_open','exchange_security_status','provider_publication_clock','corporate_action_coverage')}
    sessions=[];d=date(2026,10,9)
    while d<=date(2026,11,9):
        if d.weekday()<5:
            row={'date':d.isoformat()}
            for k,h,m in [('open_at',9,30),('close_at',16,0)]:
                row[k]=datetime(d.year,d.month,d.day,h,m,tzinfo=C.NY).astimezone(C.timezone.utc).isoformat()
            sessions.append(row)
        d+=timedelta(days=1)
    target='2026-11-09' if purpose in ('warmup','open') else '2026-11-06'
    i=next(i for i,s in enumerate(sessions) if s['date']==target);row=sessions[i]
    opened=C._instant(row['open_at']);closed=C._instant(row['close_at'])
    received=(opened+timedelta(minutes=2) if purpose=='open' else closed+timedelta(minutes=15))
    if purpose=='warmup':received=C._instant(sessions[i-1]['close_at'])+timedelta(minutes=10)
    dates=[s['date'] for s in sessions[max(0,i-20):i]]
    packet={'schema':'us_allocation_source_evidence_v1','purpose':purpose,'symbols':list(C.ASSETS),'session_date':target,
        'calendar_ref':deepcopy(ref),'source_ref':deepcopy(ref),'received_at':received.isoformat(),'records':{},'warmup_dates':dates,
        'previous_observed_session_date':sessions[i-1]['date'],'previous_committed_decision_at':(opened-timedelta(hours=1)).isoformat(),
        'previous_committed_decision_ref':deepcopy(ref)}
    for symbol in C.ASSETS:
        kind='exchange_official_open' if purpose=='open' else 'provider_daily_completed'
        packet['records'][symbol]={'currency':'USD','timezone':'America/New_York','source_ref':deepcopy(ref),
            'source_authority':kind,'definition_ref':deepcopy(ref),'complete':True,'received_at':received.isoformat(),
            'observation_kind':'official_open' if purpose=='open' else 'completed_daily','dates':dates,'session_complete':[True]*20,
            'effective_at':row['open_at'] if purpose=='open' else None,'provider_available_at':(opened+timedelta(minutes=1)).isoformat() if purpose=='open' else None,
            'publication_authority':'provider_publication_clock','publication_definition_ref':deepcopy(ref),
            'execution':dict(suspended=False,buy_blocked=False,sell_blocked=False) if purpose=='open' else dict(suspended=None,buy_blocked=None,sell_blocked=None),
            'execution_authority':'exchange_security_status','execution_definition_ref':deepcopy(ref),
            'execution_effective_at':row['open_at'],'execution_received_at':received.isoformat(),
            'provider_bar_interval':'1d','provider_trading_date':target,'provider_bucket_timestamp':str(int(opened.timestamp())),
            'finality':'provider_snapshot_finality_unknown',
            'session_open_at':row['open_at'],'session_close_at':row['close_at'],
            'units':{'prices':'USD_per_share','volume':'shares','dividend':'USD_per_share'},
            'corporate_actions':{'authority':'corporate_action_coverage','definition_ref':deepcopy(ref),'coverage_complete':True,
                'coverage_basis':'provider_query_snapshot_only',
                'units':'USD_per_share','splits_absent':True,'capital_gains_absent':True,'coverage_dates':dates if purpose=='warmup' else [target],
                'known_at':(opened-timedelta(hours=1)).isoformat(),'split_ratio_unit':'new_shares_per_old_share'}}
    return packet,{'source_ref':deepcopy(ref),'sessions':sessions},authorities


def artificial_raws(purpose='warmup'):
    packet,schedule,authorities=artificial_metadata(purpose);raws={}
    dates=packet['warmup_dates'] if purpose=='warmup' else [packet['session_date']]
    for symbol in C.ASSETS:
        stamps=[int(datetime.fromisoformat(d+'T09:30:00').replace(tzinfo=C.NY).timestamp()) for d in dates]
        quote={field:[value]*len(dates) for field,value in [('open','10' if purpose=='daily_model' else 'OPAQUE_OPEN'),
            ('close','10'),('volume','10000'),('high','OPAQUE_HIGH'),('low','OPAQUE_LOW')]}
        row={'meta':{'symbol':symbol,'currency':'USD','exchangeTimezoneName':'America/New_York','instrumentType':'ETF','dataGranularity':'1d','regularMarketPrice':'OPAQUE_CURRENT'},
            'timestamp':stamps,'indicators':{'quote':[quote],'adjclose':[{'adjclose':['OPAQUE_ADJUSTED']*len(dates)}]},
            'events':{'dividends':{str(stamps[0]):{'date':stamps[0],'amount':'OPAQUE_WARM_DIVIDEND' if purpose=='warmup' else '.10'}}}}
        # Provider numerical strings use standard JSON-number lexical form.
        if purpose=='daily_model':row['events']['dividends'][str(stamps[0])]['amount']='0.10'
        raw=json.dumps({'chart':{'error':None,'result':[row]}}).encode();raws[symbol]=raw
        packet['records'][symbol]['source_ref']={'path':'artificial/'+symbol,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
    return raws,packet,schedule,authorities


def artificial_context(packet):
    return C._SourceDecodeContext(packet['purpose'],C._digest(packet),C._digest({s:packet['records'][s]['source_ref'] for s in C.ASSETS}),
                                  'b'*64,'artificial_source_values',True)


class SourceContractTests(unittest.TestCase):
    def test_describe_reads_only_bound_identity_time_and_schema(self):
        raws,p,s,a=artificial_raws('daily_model');ref=p['records']['SPY']['source_ref']
        with patch.object(C,'_number',side_effect=AssertionError('numeric_called')):
            result=C.describe_yahoo_source(raws['SPY'],ref,symbol='SPY')
        self.assertEqual(result['dates'],['2026-11-06']);self.assertEqual(result['rows'],1)
        self.assertEqual(result['provider_bucket_timestamps'],[p['records']['SPY']['provider_bucket_timestamp']])
        self.assertEqual(result['event_counts']['dividends'],1);self.assertNotIn('OPAQUE',json.dumps(result))
        with self.assertRaisesRegex(ValueError,'source_bytes_hash'):C.describe_yahoo_source(raws['SPY']+b' ',ref,symbol='SPY')

    def test_bound_raws_callback_then_only_allowlisted_values_same_bytes(self):
        raws,p,s,a=artificial_raws();context=artificial_context(p);called=[];number=C._number
        def callback():
            called.append(True);raws['SPY']=b'changed_mapping_after_metadata'
            p['records']['SPY']['execution']['suspended']=False
            return {'artificial_marker':True}
        def checked(token,**kwargs):
            self.assertEqual(called,[True]);return number(token,**kwargs)
        with patch.object(C,'_number',side_effect=checked):
            result=C.normalize_yahoo_sources(raws,p,s,authorities=a,context=context,before_numeric_decode=callback)
        self.assertEqual(len(result['days']),20);self.assertEqual(result['dividends'],[])
        self.assertEqual(result['days'][0]['prices']['SPY'],{'close':'10','volume':'10000'})
        self.assertEqual(result['evidence_kind'],'artificial_source_values');self.assertEqual(result['real_forward'],0)
        self.assertIsNone(result['source_metadata']['records']['SPY']['execution']['suspended'])
        self.assertNotIn('OPAQUE',json.dumps(result));self.assertFalse(result['adjusted_close_decoded'])

    def test_raw_missing_dates_bad_hash_late_and_unknown_actions_pre_marker(self):
        for case in ('missing_day','bad_hash','late','split','unknown_CG','capital_gain','null'):
            with self.subTest(case=case):
                raws,p,s,a=artificial_raws('daily_model');obj=json.loads(raws['SPY']);row=obj['chart']['result'][0]
                if case=='missing_day':row['timestamp']=[]
                elif case=='bad_hash':raws['SPY']=b'changed'
                elif case=='late':p['received_at']='2026-11-09T14:30:00Z'
                elif case=='split':row['events']['splits']={'unapproved':{}}
                elif case=='unknown_CG':row['events']['capitalGains']=None
                elif case=='capital_gain':row['events']['capitalGains']={'unapproved':{}}
                else:row['indicators']['quote'][0]['close'][0]=None
                if case not in ('bad_hash','late'):
                    raws['SPY']=json.dumps(obj).encode();p['records']['SPY']['source_ref'].update(sha256=hashlib.sha256(raws['SPY']).hexdigest(),bytes=len(raws['SPY']))
                with patch.object(C,'_number',side_effect=AssertionError('numeric_called')) as number:
                    with self.assertRaises(ValueError):
                        C.normalize_yahoo_sources(raws,p,s,authorities=a,context=artificial_context(p),before_numeric_decode=lambda:self.fail('marker_called'))
                    number.assert_not_called()

    def test_daily_allowed_values_and_identity_are_preserved(self):
        raws,p,s,a=artificial_raws('daily_model');calls=[]
        result=C.normalize_yahoo_sources(raws,p,s,authorities=a,context=artificial_context(p),before_numeric_decode=lambda:calls.append('marker'))
        self.assertEqual(calls,['marker']);self.assertEqual(result['days'][0]['prices']['SPY'],{'open':'10','close':'10','volume':'10000'})
        self.assertEqual(len(result['dividends']),4);self.assertEqual(result['dividends'][0]['amount_per_share'],'0.10')
        self.assertIsNone(result['source_metadata']['records']['SPY']['provider_available_at'])
        self.assertTrue(all(v is None for v in result['source_metadata']['records']['SPY']['execution'].values()))
        with self.assertRaises(ValueError):C._SourceDecodeContext('daily_model','a'*64,'b'*64,'c'*64,'conditional_provider_observation',True)

    def test_basic_ISO_date_is_not_accepted_as_canonical_calendar(self):
        p,s,a=artificial_metadata('open')
        last=deepcopy(s['sessions'][-1]);last['date']='20261109';s['sessions']=[last];p['session_date']='20261109'
        result=C.assess_source_metadata(p,s,authorities=a)
        self.assertFalse(result['requirements_met']);self.assertIn('canonical_session_date',result['missing'])

    def test_exact20_completed_dates_not20_successes(self):
        p,s,a=artificial_metadata();r=C.assess_source_metadata(p,s,authorities=a)
        self.assertTrue(r['requirements_met']);self.assertEqual(r['warmup_session_count'],20)
        self.assertFalse(r['paper_fills_allowed']);self.assertFalse(r['authority_content_authenticated'])
        for case in ('gap','incomplete','wrong_reference','before_close'):
            with self.subTest(case=case):
                q=deepcopy(p);row=q['records']['SPY']
                if case=='gap':row['dates']=row['dates'][:-1]+['2026-11-09']
                elif case=='incomplete':row['session_complete'][-1]=False
                elif case=='wrong_reference':row['definition_ref']['sha256']='b'*64
                else:row['received_at']='2026-11-06T20:59:00Z'
                self.assertFalse(C.assess_source_metadata(q,s,authorities=a)['requirements_met'])

    def test_minute_bucket_is_not_official_open_or_permission(self):
        p,s,a=artificial_metadata('open');self.assertTrue(C.assess_source_metadata(p,s,authorities=a)['requirements_met'])
        for case in ('bar','missing_status','late','publication_unknown','borrowed_authority'):
            with self.subTest(case=case):
                q=deepcopy(p);row=q['records']['SPY']
                if case=='bar':row['observation_kind']='minute_bar'
                elif case=='missing_status':row['execution']['suspended']=None
                elif case=='late':q['received_at']='2026-11-09T14:36:00Z'
                elif case=='publication_unknown':row['provider_available_at']=None
                else:row['execution_authority']='provider_daily_completed'
                result=C.assess_source_metadata(q,s,authorities=a)
                self.assertEqual(result['status'],'unfilled_source_unproven');self.assertFalse(result['paper_fills_allowed'])

    def test_daily_model_keeps_unknowns_and_cannot_backdate_decision(self):
        p,s,a=artificial_metadata('daily_model');result=C.assess_source_metadata(p,s,authorities=a)
        self.assertEqual(result['status'],'conditional_daily_model_metadata_valid')
        self.assertEqual(result['real_forward'],0);self.assertFalse(result['paper_fills_allowed'])
        for case in ('early','backfill','late_decision','fake_effective','fake_permission','bad_bucket','wrong_day'):
            with self.subTest(case=case):
                q=deepcopy(p);row=q['records']['SPY']
                if case=='early':row['received_at']=row['session_close_at']
                elif case=='backfill':q['previous_observed_session_date']='2026-11-04'
                elif case=='late_decision':q['previous_committed_decision_at']=row['session_open_at']
                elif case=='fake_effective':row['effective_at']=row['session_open_at']
                elif case=='fake_permission':row['execution']['buy_blocked']=False
                elif case=='bad_bucket':row['provider_bucket_timestamp']='not_a_timestamp'
                else:q['received_at']='2026-11-09T14:30:00Z'
                self.assertFalse(C.assess_source_metadata(q,s,authorities=a)['requirements_met'])

    def test_reference_clocks_use_NY_dst_and_bound_early_close(self):
        p,s,a=artificial_metadata('daily_model')
        row=next(x for x in s['sessions'] if x['date']==p['session_date']);row['close_at']='2026-11-06T18:00:00Z'
        # This is an invented early-close authority; not a claim Nov6 really closed early.
        for record in p['records'].values():record['session_close_at']=row['close_at']
        self.assertTrue(C.assess_source_metadata(p,s,authorities=a)['requirements_met'])
        row['open_at']='2026-11-06T13:30:00Z'
        self.assertFalse(C.assess_source_metadata(p,s,authorities=a)['requirements_met'])


if __name__=='__main__':unittest.main()
