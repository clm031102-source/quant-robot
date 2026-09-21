import itertools
import io
import json
import unittest
from datetime import date
from unittest.mock import patch
import numpy as np
import pandas as pd
from quant_robot.research.disclosed_flow_diagnostic import performance_bounds, open_return, summarize, calculate


class DisclosedFlowDiagnosticTests(unittest.TestCase):
    def test_bounds_equal_exhaustive_unknown_completions(self):
        for states in ([1,None,0,None], [None,None], [1,1,0], [0,0]):
            y=np.array([.07,-.03,.11,-.09][:len(states)])
            observed=[]
            for completion in itertools.product([0,1],repeat=states.count(None)):
                it=iter(completion); z=np.array([next(it) if s is None else s for s in states])
                observed.append((float(np.mean(z*(y-y.mean()))), y[z==1]))
            actual=performance_bounds(states,y)
            np.testing.assert_allclose(actual['D'],[min(r[0] for r in observed),max(r[0] for r in observed)],atol=1e-15)
            selected=[r[1] for r in observed if len(r[1])]
            if selected:
                np.testing.assert_allclose(actual['selected_mean'],[min(a.mean() for a in selected),max(a.mean() for a in selected)])
                np.testing.assert_allclose(actual['selected_win_rate'],[min((a>0).mean() for a in selected),max((a>0).mean() for a in selected)])
            else: self.assertIsNone(actual['selected_mean'])
            self.assertEqual(actual['empty_selection_possible'],any(len(r[1])==0 for r in observed))

    def test_cash_rights_use_record_date_and_not_payment_or_entry_ex_date(self):
        event={'kind':'cash_dividend','record_date':'2022-01-31','ex_date':'2022-02-01','cash_per_share':.2,'cash_amount_basis':'gross'}
        self.assertAlmostEqual(open_return('2022-01-03','2022-02-01',10,9.8,[event]),0)
        self.assertAlmostEqual(open_return('2022-02-01','2022-03-01',9.8,9.8,[event]),0)
        self.assertAlmostEqual(open_return('2022-01-31','2022-02-01',10,9.8,[event]),0)
        with self.assertRaises(ValueError):open_return('2022-01-03','2022-02-01',0,10,[event])
        with self.assertRaises(ValueError):open_return('2022-01-03','2022-02-01',10,10,[dict(event,kind='split')])

    def test_validation_no_cash_imputation_and_no_constant_signal_qualification(self):
        for states,y in [([True],[.1]),([2],[.1]),([None],[float('nan')]),([0],[])]:
            with self.assertRaises(ValueError):performance_bounds(states,y)
        rows=[{'decision_date':f'{2021+i//12}-{1+i%12:02d}-01','state':None,'return':.01} for i in range(38)]
        result=summarize(rows)
        self.assertFalse(result['gross_screen_passed'])
        self.assertEqual(result['full']['unknown_months'],38)
        self.assertEqual(result['full']['selected_count'],[0,38])
        self.assertTrue(result['full']['empty_selection_possible'])

    def test_full_synthetic_join_filters_assets_preserves_calendar_and_flow_segments(self):
        days=[d for d in pd.bdate_range('2020-01-02','2024-06-28').date if str(d) not in ('2024-05-01','2024-05-02','2024-05-03')]
        anchors=sorted({str(d)[:7]:str(d) for d in reversed(days) if '2021-04'<=str(d)[:7]<='2024-06'}.values())
        periods=['2020-12-31','2021-06-30','2021-12-31','2022-06-30','2022-12-31','2023-06-30','2023-12-31']
        pubs=['2021-03-31','2021-08-28','2022-03-31','2022-08-30','2023-03-31','2023-08-31','2024-03-30']
        def encoded(x):return json.dumps(x).encode()
        def parquet(rows):
            b=io.BytesIO();pd.DataFrame(rows).to_parquet(b,index=False);return b.getvalue()
        snapshots={'calendar':b'','calendar_manifest':b''}; records=[]
        for i,(period,pub) in enumerate(zip(periods,pubs,strict=True)):
            record=dict(symbol='510300.SH',period_end=period,publication_date=pub,reported_scope='all_stocks',source_sha256='a'*64,
                equity_total_cny='10.00',holdings=[dict(ordinal=1,symbol='600000.SH',quantity=1,fair_value_cny='10.00',reported_nav_weight_percent='100.00')])
            snapshots[f'holdings_{i}']=encoded(record);records.append(record)
        inputs=[];flows=[[] for _ in range(7)]
        for i,y in enumerate([2021,2022,2023,2023,2024,2023,2024]):
            inputs.append(dict(path=f'synthetic_{i}/year={y}/part.parquet',segment_start='2023-07-03' if i==3 else '0001-01-01',segment_end='2023-06-30' if i==2 else '9999-12-31'))
        fields=['date','symbol','asset_id','market','source','ingested_at','net_mf_amount']; months=[]; coverage=[]
        for k,(entry,exit_day) in enumerate(zip(anchors,anchors[1:])):
            prior=str(date.fromordinal(date.fromisoformat(entry).replace(day=1).toordinal()-1))[:7]
            sessions=[str(d) for d in days if str(d)[:7]==prior]
            latest=max((r for r in records if r['publication_date']<entry),key=lambda r:r['period_end'])
            months.append(dict(decision_date=entry,exit_date=exit_day,source_month=prior,sessions=sessions,period_end=latest['period_end'],symbols=['600000.SH']))
            coverage.append(dict(decision_date=entry,missing_cells=[],unknown_weighted_numerator=0,full_denominator=1000*len(sessions)))
            for day in sessions:
                i=0 if day[:4]=='2021' else 1 if day[:4]=='2022' else 4 if day[:4]=='2024' else 2 if day<='2023-06-30' else 3
                flows[i].append(dict(date=date.fromisoformat(day),symbol='600000.SH',asset_id='CN_XSHG_600000',market='CN',source='tushare_moneyflow',ingested_at='synthetic',net_mf_amount=10. if k%2 else -10.))
        for i,rows in enumerate(flows):
            snapshots[f'flow_{i}']=parquet(rows or [dict(date=date(2023,1,3),symbol='600001.SH',asset_id='CN_XSHG_600001',market='CN',source='tushare_moneyflow',ingested_at='synthetic',net_mf_amount=999.)])
        for y in range(2021,2025):
            snapshots[f'bars_{y}']=parquet([dict(date=date.fromisoformat(d),asset_id='CN_ETF_XSHG_510300',market='CN_ETF',currency='CNY',open=100.+i) for i,d in enumerate(anchors) if d[:4]==str(y)])
        snapshots['coverage_scope']=encoded(dict(months=months,inputs=inputs,fields=fields))
        snapshots['coverage_result']=encoded(dict(months=coverage))
        snapshots['actions']=encoded(dict(schema_version=3,source_ref='synthetic',coverage_start='2020-01-02',coverage_end='2024-06-28',asset_ids=['CN_ETF_XSHG_510300'],events=[]))
        with patch('quant_robot.data.cn_calendar_snapshot.calendar_rows_from_snapshot',return_value=[(d,True) for d in days]):result=calculate(snapshots)
        self.assertEqual(len(result['observations']),38)
        self.assertEqual(result['diagnostic']['full']['selected_count'],[19,19])
        self.assertEqual(result['diagnostic']['full']['unknown_months'],0)
        self.assertEqual(result['ETF_open_values_decoded'],39)
        self.assertFalse(result['net_account_run'])


if __name__=='__main__':unittest.main()
