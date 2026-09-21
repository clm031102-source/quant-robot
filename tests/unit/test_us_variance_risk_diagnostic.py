from datetime import date, timedelta
import math
import unittest
import io
import json
from unittest.mock import patch
import pandas as pd
from quant_robot.research.us_variance_risk_diagnostic import quarterly_anchors, variance_signal, summarize


class USVarianceRiskDiagnosticTests(unittest.TestCase):
    def test_realized_month_uses_previous_session_and_percent_units(self):
        days=['2012-11-30','2012-12-03','2012-12-04']
        spx={days[0]:100.0,days[1]:101.0,days[2]:99.0}
        result=variance_signal('2012-12',days,spx,{'2012-12-04':20.0,'2012-12-05':99.0})
        expected=math.fsum([(100*math.log(101/100))**2,(100*math.log(99/101))**2])
        self.assertAlmostEqual(result['realized_variance_pct2'],expected)
        self.assertAlmostEqual(result['gap_pct2'],400/12-expected)
        self.assertEqual(result['observation_date'],'2012-12-04')
        self.assertEqual(result['selected'],1)

    def test_missing_calendar_session_or_seed_or_vix_is_blocker(self):
        days=['2012-11-30','2012-12-03','2012-12-04']
        for spx,vix in [({d:100 for d in days[:-1]},{days[-1]:20}),({d:100 for d in days[1:]},{days[-1]:20}),({d:100 for d in days},{})]:
            with self.subTest(spx=spx,vix=vix),self.assertRaises(ValueError):
                variance_signal('2012-12',days,spx,vix)

    def test_negative_gap_stays_cash(self):
        days=['2012-11-30','2012-12-03']
        row=variance_signal('2012-12',days,{days[0]:100,days[1]:50},{days[1]:20})
        self.assertLess(row['gap_pct2'],0)
        self.assertEqual(row['selected'],0)

    def test_anchors_use_second_cn_session_with_all_45_fixed_intervals(self):
        start=date(2013,1,1);end=date(2024,4,10)
        days=[(start+timedelta(days=i)).isoformat() for i in range((end-start).days+1) if (start+timedelta(days=i)).weekday()<5]
        anchors=quarterly_anchors(days)
        self.assertEqual(len(anchors),46)
        self.assertEqual(anchors[0]['decision_date'],'2013-01-01')
        self.assertEqual(anchors[0]['entry_date'],'2013-01-02')
        self.assertEqual(anchors[0]['observation_month'],'2012-12')
        self.assertEqual(anchors[-1]['entry_date'],'2024-04-02')
        with self.assertRaises(ValueError):quarterly_anchors(days+[days[-1]])
        with self.assertRaises(ValueError):quarterly_anchors(days[:-10])

    def test_summary_matches_scalar_exposure_effect_and_run_count(self):
        rows=[]
        for i in range(45):
            z=int(i%3!=1)
            rows.append(dict(entry_date=f'{2013+i//4}-{1+3*(i%4):02}-02',selected=z,return_value=.03 if z else -.01,sessions=60+i%4))
        result=summarize(rows)
        n=sum(r['sessions'] for r in rows);f=sum(r['selected']*r['sessions'] for r in rows)/n
        expected=sum((r['selected']-f)*math.log1p(r['return_value']) for r in rows)/n
        self.assertAlmostEqual(result['full']['D_daily_log'],expected)
        self.assertEqual(result['full']['selected_runs'],16)
        self.assertEqual(result['later_2020_onward']['intervals'],17)
        self.assertTrue(result['gross_screen_passed'])
        self.assertFalse(result['net_positive_EV_verified'])
        rows[0]['return_value']=-1
        with self.assertRaises(ValueError):summarize(rows)

    def test_one_persistent_state_is_insufficient_even_with_positive_gross(self):
        rows=[dict(entry_date=f'{2013+i//4}-{1+3*(i%4):02}-02',selected=1,return_value=.03,sessions=61) for i in range(45)]
        result=summarize(rows)
        self.assertEqual(result['full']['selected_runs'],1)
        self.assertFalse(result['gross_screen_passed'])
        self.assertEqual(result['bootstrap_D_daily_log_2_5_97_5'],[0,0])

    def test_complete_synthetic_source_join_filters_holdout_and_counts_cash_once(self):
        from quant_robot.research.us_variance_risk_diagnostic import calculate, us_sources
        sessions=pd.bdate_range('2013-01-01','2024-06-28').date.tolist()
        us_days=pd.date_range('2012-11-01','2023-12-31').date.tolist()
        opened=[d for d in us_days if d.weekday()<5]
        calendar=[];previous=date(2012,10,31)
        for d in us_days:
            calendar.append([d.strftime('%Y%m%d'),int(d.weekday()<5),previous.strftime('%Y%m%d')])
            if d.weekday()<5:previous=d
        def provider(fields,items):return json.dumps(dict(code=0,data=dict(fields=fields,items=items))).encode()
        snapshots={'US_calendar':provider(['cal_date','is_open','pretrade_date'],calendar),
            'SPX':provider(['ts_code','trade_date','open','high','low','close'],[['SPX',d.strftime('%Y%m%d'),100,100,100,100] for d in opened]),
            'VIX':('DATE,OPEN,HIGH,LOW,CLOSE\n'+''.join(d.strftime('%m/%d/%Y')+',20,20,20,20\n' for d in opened)+'01/05/2026,FORBIDDEN,FORBIDDEN,FORBIDDEN,FORBIDDEN\n').encode()}
        snapshots['early_price']=json.dumps(dict(code='510300',kline=[[int(d.strftime('%Y%m%d')),10,10,10,10] for d in sessions if d.year<2020])).encode()
        for y in range(2020,2025):
            rows=[dict(date=d,asset_id='CN_ETF_XSHG_510300',market='CN_ETF',currency='CNY',open=10.) for d in sessions if d.year==y]
            rows.append(dict(date=date(2026,1,5),asset_id='CN_ETF_XSHG_510300',market='CN_ETF',currency='CNY',open=9999.))
            stream=io.BytesIO();pd.DataFrame(rows).to_parquet(stream,index=False);snapshots[f'bars_{y}']=stream.getvalue()
        events=[]
        for y in range(2014,2025):
            record=next(d for d in sessions if d>=date(y,1,15));ex=sessions[sessions.index(record)+1]
            events.append(dict(asset_id='CN_ETF_XSHG_510300',kind='cash_dividend',cash_amount_basis='gross',record_date=str(record),ex_date=str(ex),cash_per_share=.1))
        snapshots['actions']=json.dumps({'events':events[7:]}).encode()
        snapshots['early_actions']=json.dumps({'events':[{**r,'cash_per_unit':str(r['cash_per_share'])} for r in events[:7]]}).encode()
        with patch('quant_robot.research.us_variance_risk_diagnostic.cn_sessions',return_value=[str(d) for d in sessions]):
            result=calculate(snapshots)
        self.assertEqual(len(result['observations']),45)
        self.assertEqual(result['ETF_open_values_used'],46)
        self.assertEqual(sum(r['return_value']>0 for r in result['observations']),11)
        self.assertTrue(all(abs(r['return_value']-.01)<1e-12 for r in result['observations'] if r['return_value']))
        self.assertTrue(all(r['assumed_source_to_decision_hours']>0 for r in result['observations']))
        self.assertFalse(result['diagnostic']['gross_screen_passed'])
        broken=json.loads(snapshots['SPX']);broken['data']['items'].pop(20)
        snapshots['SPX']=json.dumps(broken).encode()
        with self.assertRaisesRegex(ValueError,'exact US session coverage'):us_sources(snapshots)
