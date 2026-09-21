"""Synthetic timing, missing-state, cash-entitlement and inference cases."""
from datetime import date, timedelta
from decimal import Decimal
import io
import json
import math
import unittest
from unittest.mock import patch
import pandas as pd
from quant_robot.research import term_structure_diagnostic as subject


def months():
    result=[]
    for i in range(142):
        number=2011*12+11+i; year,month=divmod(number,12); month+=1
        result.append(dict(month=f'{year:04}-{month:02}',status='conditional',
            yield_1y_percent='2',yield_10y_percent=str(Decimal('2')+Decimal(i)/100)))
    return result


def sample_rows():
    return [dict(entry_date=f'{2013+i//4}-{1+3*(i%4):02}-02',
        state=int(i%3!=1),return_value=.03 if i%3!=1 else -.01,sessions=60+i%4,
        episode_id=None) for i in range(44)]


class TermStructureDiagnosticTests(unittest.TestCase):
    def test_median_excludes_current_and_strict_equality_is_cash(self):
        data=months(); data[12]['yield_10y_percent']='2.055'
        signal=subject.signal('2012-12',{r['month']:r for r in data})
        self.assertEqual(signal['prior12_median_percentage_points'],'0.055')
        self.assertEqual(signal['state'],0)
        data[12]['yield_10y_percent']='2.0550001'
        self.assertEqual(subject.signal('2012-12',{r['month']:r for r in data})['state'],1)

    def test_missing_older_month_not_skipped_and_future_not_used(self):
        data={r['month']:r for r in months()}
        before=subject.signal('2012-12',data)
        data['2013-01']['yield_10y_percent']='99999'
        self.assertEqual(subject.signal('2012-12',data),before)
        del data['2011-12']
        result=subject.signal('2012-12',data)
        self.assertIsNone(result['state'])
        self.assertEqual(result['unknown_months'],['2011-12'])

    def test_unknown_january_propagates_to_four_quarter_windows(self):
        data={r['month']:r for r in months()}; data['2020-01']['status']='unknown'
        unknown=[m for m in data if int(m[5:]) in (3,6,9,12) and m>='2012-12'
                 and subject.signal(m,data)['state'] is None]
        self.assertEqual(unknown,['2020-03','2020-06','2020-09','2020-12'])

    def test_finite_values_required_for_conditional_month(self):
        data={r['month']:r for r in months()}; data['2012-12']['yield_10y_percent']='NaN'
        with self.assertRaises(ValueError): subject.signal('2012-12',data)

    def test_anchors_use_first_session_and_exact_terminal(self):
        days=[str(d) for d in pd.bdate_range('2013-01-01','2024-01-10').date]
        result=subject.quarterly_anchors(days)
        self.assertEqual(len(result),45)
        self.assertEqual(result[0],dict(entry_date='2013-01-01',observation_month='2012-12',quarter_end='2012-12-31'))
        self.assertEqual(result[-1]['entry_date'],'2024-01-01')
        with self.assertRaises(ValueError): subject.quarterly_anchors(days+days[-1:])
        with self.assertRaises(ValueError): subject.quarterly_anchors([d for d in days if not d.startswith('2016-04')])

    def test_effect_unknown_denominator_and_carry_in_episode(self):
        rows=sample_rows(); rows[2]['state']=None
        subject.mark_episodes(rows)
        result=subject.summarize(rows)
        n=sum(r['sessions'] for r in rows)
        fraction=sum(r['sessions'] for r in rows if r['state']==1)/n
        effect=sum(((r['state']==1)-fraction)*math.log1p(r['return_value']) for r in rows)/n
        self.assertAlmostEqual(result['full']['D_daily_log'],effect)
        self.assertEqual(result['full']['unknown_intervals'],1)
        self.assertEqual(result['later_2020_onward']['intervals'],16)
        self.assertFalse(result['net_positive_EV_verified'])
        rows[27]['state']=rows[28]['state']=1; subject.mark_episodes(rows)
        self.assertTrue(subject.summarize(rows)['later_carry_in_episode'])

    def test_one_persistent_state_is_not_many_independent_episodes(self):
        rows=sample_rows()
        for r in rows:r['state']=1
        subject.mark_episodes(rows); result=subject.summarize(rows)
        self.assertEqual(result['full']['selected_episodes'],1)
        self.assertFalse(result['gross_screen_passed'])
        self.assertEqual(result['bootstrap_D_daily_log_2_5_97_5'],[0,0])

    def test_invalid_quarter_count_state_duration_or_return_rejected(self):
        rows=sample_rows(); subject.mark_episodes(rows)
        with self.assertRaises(ValueError):subject.summarize(rows[:-1])
        for field,value in [('state',2),('sessions',0),('return_value',-1),('return_value',float('nan'))]:
            changed=[dict(r) for r in rows];changed[0][field]=value
            with self.assertRaises(ValueError):subject.summarize(changed)

    def test_synthetic_complete_join_counts_cash_and_ignores_2026_rows(self):
        sessions=pd.bdate_range('2013-01-01','2024-06-28').date.tolist()
        snapshots={'source_rows':json.dumps({'months':months()}).encode(),
            'early_price':json.dumps(dict(code='510300',kline=[[int(d.strftime('%Y%m%d')),10,10,10,10] for d in sessions if d.year<2020])).encode()}
        for year in range(2020,2025):
            rows=[dict(date=d,asset_id='CN_ETF_XSHG_510300',market='CN_ETF',currency='CNY',open=10.) for d in sessions if d.year==year]
            rows.append(dict(date=date(2026,1,5),asset_id='CN_ETF_XSHG_510300',market='CN_ETF',currency='CNY',open=9999.))
            stream=io.BytesIO();pd.DataFrame(rows).to_parquet(stream,index=False);snapshots[f'bars_{year}']=stream.getvalue()
        events=[]
        for year in range(2014,2025):
            record=next(d for d in sessions if d>=date(year,1,15)); ex=sessions[sessions.index(record)+1]
            events.append(dict(asset_id='CN_ETF_XSHG_510300',kind='cash_dividend',cash_amount_basis='gross',
                record_date=str(record),ex_date=str(ex),cash_per_share=.1))
        snapshots['actions']=json.dumps({'events':events[7:]}).encode()
        snapshots['early_actions']=json.dumps({'events':[{**r,'cash_per_unit':str(r['cash_per_share'])} for r in events[:7]]}).encode()
        with patch.object(subject,'cn_sessions',return_value=[str(d) for d in sessions]):
            result=subject.calculate(snapshots)
        self.assertEqual(len(result['observations']),44)
        self.assertEqual(result['ETF_open_values_used'],45)
        self.assertEqual(sum(r['return_value']>0 for r in result['observations']),10)
        self.assertTrue(all(abs(r['return_value']-.01)<1e-12 for r in result['observations'] if r['return_value']))
        self.assertFalse(result['diagnostic']['gross_screen_passed'])
        self.assertTrue(all(r['entry_date']>r['quarter_end'] for r in result['observations']))


if __name__=='__main__':unittest.main()
