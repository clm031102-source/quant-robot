from datetime import date, timedelta
import math
import unittest

from quant_robot.research.electricity_activity_diagnostic import event_intervals, describe, summarize


def weekdays(start, end):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    return [(first+timedelta(days=i)).isoformat() for i in range((last-first).days+1)
            if (first+timedelta(days=i)).weekday() < 5]


def history():
    return [dict(reference_month=f'{y}-{m:02}', availability_date=f'{y+(m==12)}-{m%12+1:02}-10',
                 growth_percent='10') for y in range(2013, 2016) for m in range(1, 13)]


class ElectricityEventsTests(unittest.TestCase):
    def setUp(self):
        self.days = weekdays('2013-01-01', '2017-06-01')
        self.current = dict(reference_month='2016-01', availability_date='2016-02-10', growth_percent='9')

    def run_rows(self, sources, start='2016-02-10', end='2016-06-01'):
        return event_intervals(sources, self.days, start=start, terminal=end)

    def test_strict_next_session_median_and_sixty_two_day_expiration(self):
        rows = self.run_rows(history()+[self.current])
        self.assertEqual([r['entry_date'] for r in rows], ['2016-02-10','2016-02-11','2016-04-13'])
        self.assertEqual([r['state'] for r in rows], [None,1,None])
        self.assertEqual(rows[1]['median_growth_percent'], '10')
        self.assertEqual(rows[1]['prior_valid_months'], 36)
        self.assertEqual(sum(r['sessions'] for r in rows), self.days.index('2016-06-01')-self.days.index('2016-02-10'))

    def test_exact_even_median_tie_and_insufficient_history(self):
        sources = history()
        for i,r in enumerate(sources): r['growth_percent'] = '0' if i < 18 else '2'
        rows = self.run_rows(sources+[{**self.current,'growth_percent':'1'}])
        row = next(r for r in rows if r['entry_date']=='2016-02-11')
        self.assertEqual(row['median_growth_percent'],'1')
        self.assertEqual(row['state'],0)
        rows = self.run_rows(sources[1:]+[self.current])
        self.assertTrue(all(r['state'] is None for r in rows))

    def test_late_old_month_neither_recomputes_state_nor_refreshes_expiry(self):
        sources = history()[1:]+[{**self.current,'growth_percent':'10'},
            dict(reference_month='2016-02', availability_date='2016-03-10',growth_percent='1')]
        late = dict(reference_month='2013-01',availability_date='2016-04-01',growth_percent='1000')
        expected = self.run_rows(sources)
        self.assertEqual(self.run_rows(sources+[late]),expected)
        self.assertIn('2016-05-12',[r['entry_date'] for r in expected])

    def test_new_latest_release_wins_on_expiration_day_and_preserves_episode(self):
        fresh = dict(reference_month='2016-03',availability_date='2016-04-12',growth_percent='1')
        rows = self.run_rows(history()+[self.current,fresh])
        r = next(r for r in rows if r['entry_date']=='2016-04-13')
        self.assertEqual(r['state'],1)
        self.assertEqual(r['reference_month'],'2016-03')
        self.assertEqual(r['episode_id'],next(r for r in rows if r['entry_date']=='2016-02-11')['episode_id'])

    def test_same_open_installs_all_history_then_uses_latest_month(self):
        a = dict(reference_month='2016-02',availability_date='2016-03-12',growth_percent='2')
        b = dict(reference_month='2016-01',availability_date='2016-03-13',growth_percent='0')
        rows = self.run_rows(history()+[a,b])
        r = next(r for r in rows if r['entry_date']=='2016-03-14')
        self.assertEqual(r['reference_month'],'2016-02')
        self.assertEqual(r['prior_valid_months'],37)
        self.assertEqual(r['median_growth_percent'],'10')
        self.assertEqual(self.run_rows(history()+[b,a]),rows)

    def test_duplicate_future_month_nonfinite_and_unordered_calendar_rejected(self):
        sources=history()+[self.current]
        for bad in [sources+[self.current],sources+[{**self.current,'reference_month':'2017-01'}],
                    history()+[{**self.current,'growth_percent':'NaN'}],
                    history()+[{**self.current,'growth_percent':True}]]:
            with self.assertRaises(ValueError):self.run_rows(bad)
        with self.assertRaises(ValueError):event_intervals(sources,self.days[::-1])


class ElectricityStatisticsTests(unittest.TestCase):
    def fixture(self):
        rows=[]
        for i in range(24):
            state=[1,1,0,None][i%4]; n=7 if i%2 else 19
            rows.append(dict(entry_date=f'{2019+i//12}-{i%12+1:02}-01',exit_date='2024-01-02',
                state=state,episode_id=i//4+1 if state==1 else None,sessions=n,
                return_value=math.expm1(.001*n)))
        return rows

    def test_unknown_cash_remains_in_unconditional_denominator(self):
        r=describe(self.fixture())
        self.assertEqual(r['unknown_intervals'],6)
        self.assertEqual(r['known_unselected_intervals'],6)
        self.assertEqual(r['selected_episodes'],6)
        self.assertAlmostEqual(r['selected_session_fraction'],.5)
        self.assertAlmostEqual(r['D_daily_log'],0,places=15)

    def test_episode_count_does_not_count_repeated_selected_releases(self):
        rows=self.fixture()
        for i,r in enumerate(rows):
            r['state']=1 if i<12 else 0;r['episode_id']=1 if i<12 else None
        result=summarize(rows,rows[12:])
        self.assertEqual(result['full']['selected_intervals'],12)
        self.assertEqual(result['full']['selected_episodes'],1)
        self.assertFalse(result['checks']['full_episodes'])
        self.assertFalse(result['gross_screen_passed'])

    def test_bootstrap_recomputes_joint_duration_exposure_and_linear_percentiles(self):
        import numpy as np
        rows=self.fixture()
        for i,r in enumerate(rows):r['return_value']=(.03 if r['state']==1 else -.02)+(i%3)*.001
        actual=summarize(rows,rows[12:])
        rng=np.random.default_rng(20260922); count=len(rows)
        starts=rng.integers(0,count,size=(5000,2)); effects=[]
        for pair in starts:
            sample=[rows[(int(a)+j)%count] for a in pair for j in range(12)]
            duration=sum(r['sessions'] for r in sample)
            exposure=sum(r['sessions'] for r in sample if r['state']==1)/duration
            effects.append(sum(((r['state']==1)-exposure)*math.log1p(r['return_value']) for r in sample)/duration)
        expected=np.quantile(effects,[.025,.975],method='linear')
        np.testing.assert_allclose(actual['bootstrap_D_daily_log_2_5_97_5'],expected,rtol=1e-12,atol=1e-15)
        self.assertFalse(actual['net_positive_EV_verified'])

    def test_invalid_outcomes_and_boolean_duration_rejected(self):
        for value,n in [(float('nan'),1),(-1,1),(.1,0),(.1,True)]:
            rows=self.fixture();rows[0].update(return_value=value,sessions=n)
            with self.assertRaises(ValueError):summarize(rows,rows[12:])

    def test_slice_clips_crossing_interval_without_changing_episode_identity(self):
        from quant_robot.research.electricity_activity_diagnostic import clip_later
        days=weekdays('2020-12-01','2021-02-01')
        row=dict(entry_date='2020-12-15',exit_date='2021-01-15',state=1,episode_id=7,sessions=23)
        actual=clip_later([row],days)
        self.assertEqual(actual[0]['entry_date'],'2021-01-01')  # Synthetic calendar, no holidays.
        self.assertEqual(actual[0]['sessions'],10)
        self.assertEqual(actual[0]['episode_id'],7)
        self.assertTrue(actual[0]['left_clipped'])
        self.assertEqual(row['entry_date'],'2020-12-15')

    def test_synthetic_price_join_cash_entitlement_and_asset_filter(self):
        import io
        import json
        from unittest.mock import patch
        import pandas as pd
        from quant_robot.research.electricity_activity_diagnostic import calculate
        days=weekdays('2013-01-01','2024-06-28')
        sources=[dict(reference_month=f'{y}-{m:02}',availability_date=f'{y}-{m+1:02}-15',
                      growth_percent=str((y+m)%7))
                 for y in range(2013,2024) for m in range(2,12)
                 if f'{y}-{m:02}' not in {'2022-11','2023-05'}]
        snapshots={'source_rows':json.dumps({'rows':sources}).encode(),
            'early_price':json.dumps({'code':'510300','kline':[[d.replace('-',''),10] for d in days if d<'2020-01-01']}).encode()}
        for year in range(2020,2025):
            bars=[dict(date=date.fromisoformat(d),asset_id=a,market='CN_ETF',currency='CNY',open=p)
                  for d in days if d.startswith(str(year))
                  for a,p in [('CN_ETF_XSHG_510300',10.),('CN_ETF_XSHG_510050',999.)]]
            stream=io.BytesIO();pd.DataFrame(bars).to_parquet(stream,index=False)
            snapshots[f'bars_{year}']=stream.getvalue()
        early=[];recent=[]
        for year,month in [(y,1) for y in range(2014,2020)]+[(2019,12)]+[(y,1) for y in range(2021,2025)]:
            record=next(d for d in days if d>=f'{year}-{month:02}-15');ex=days[days.index(record)+1]
            item=dict(asset_id='CN_ETF_XSHG_510300',record_date=record,ex_date=ex)
            if year<2020:early.append({**item,'cash_per_unit':.1})
            else:recent.append({**item,'cash_per_share':.1,'kind':'cash_dividend','cash_amount_basis':'gross'})
        snapshots['actions']=json.dumps({'events':recent}).encode()
        snapshots['early_actions']=json.dumps({'events':early}).encode()
        with patch('quant_robot.research.us_variance_risk_diagnostic.cn_sessions',return_value=days):
            result=calculate(snapshots)
        rows=result['observations']
        self.assertEqual(rows[0]['entry_date'],'2017-01-02')
        self.assertEqual(rows[-1]['exit_date'],'2024-01-02')
        self.assertEqual(sum(r['sessions'] for r in rows),days.index('2024-01-02')-days.index('2017-01-02'))
        self.assertAlmostEqual(sum(r['return_value'] for r in rows),.07)
        self.assertAlmostEqual(sum(r['return_value'] for r in result['later_observations']),.03)
        self.assertFalse(result['net_account_run'])


if __name__=='__main__':unittest.main()
