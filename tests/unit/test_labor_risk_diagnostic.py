import copy
import math
import unittest
from quant_robot.research.labor_risk_diagnostic import event_intervals, summarize


class LaborRiskDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.sources = [
            dict(observation_month='2018-12', declared_release_date='2019-01-03', rate_tenths_pct=50),
            dict(observation_month='2019-02', declared_release_date='2019-03-01', rate_tenths_pct=51),
            dict(observation_month='2019-12', declared_release_date='2020-01-03', rate_tenths_pct=52),
            dict(observation_month='2020-02', declared_release_date='2020-03-01', rate_tenths_pct=51),
        ]
        self.sessions = ['2020-01-02', '2020-01-03', '2020-01-06', '2020-02-28', '2020-03-02']

    def test_release_day_excluded_and_exact_prior_year_used(self):
        rows = event_intervals(self.sources, self.sessions)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['entry_date'], '2020-01-06')
        self.assertEqual(rows[0]['exit_date'], '2020-03-02')
        self.assertEqual(rows[0]['sessions'], 2)
        self.assertEqual(rows[0]['selected'], 1)
        self.assertEqual(rows[0]['contrast_tenths_pct'], 2)

    def test_tie_is_cash_without_signed_tolerance(self):
        self.sources[2]['rate_tenths_pct'] = 50
        self.assertEqual(event_intervals(self.sources, self.sessions)[0]['selected'], 0)

    def test_missing_reference_duplicate_future_month_and_boolean_rejected(self):
        variants = [
            self.sources[1:],
            self.sources + [copy.deepcopy(self.sources[0])],
            [{**x, 'observation_month':'2020-03'} if i==3 else x for i,x in enumerate(self.sources)],
            [{**x, 'rate_tenths_pct':True} if i==2 else x for i,x in enumerate(self.sources)],
        ]
        for rows in variants:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                event_intervals(rows, self.sessions)

    def test_calendar_order_and_duplicate_rejected(self):
        for days in [self.sessions[::-1],self.sessions+[self.sessions[-1]]]:
            with self.assertRaises(ValueError): event_intervals(self.sources, days)

    def fixture(self):
        return [dict(entry_date=('2022' if i<12 else '2023')+f'-{i%12+1:02}-03',
            selected=i%2, sessions=10 if i%2 else 30,
            return_value=math.expm1(.001*(10 if i%2 else 30))) for i in range(24)]

    def test_duration_matching_cancels_identical_daily_growth(self):
        r = summarize(self.fixture())
        self.assertAlmostEqual(r['full']['D_daily_log'], 0.0, places=15)
        self.assertAlmostEqual(r['full']['selected_session_fraction'], .25)
        self.assertFalse(r['gross_screen_passed'])

    def test_arithmetic_mean_and_positive_frequency_are_interval_metrics(self):
        rows = self.fixture()
        for row in rows: row['return_value'] = .02 if row['selected'] else -.01
        result = summarize(rows)
        self.assertEqual(result['full']['selected_intervals'],12)
        self.assertAlmostEqual(result['full']['selected_mean_gross'],.02)
        self.assertEqual(result['full']['selected_positive_fraction'],1)
        self.assertEqual(result, summarize(rows))
        self.assertFalse(result['net_positive_EV_verified'])

    def test_constant_cash_is_undefined_and_fails(self):
        rows=self.fixture()
        for row in rows: row['selected']=0
        result=summarize(rows)
        self.assertIsNone(result['full']['selected_mean_gross'])
        self.assertFalse(result['gross_screen_passed'])

    def test_invalid_return_or_transition_count_rejected(self):
        for value,n in [(float('nan'),1),(-1,1),(.1,0),(.1,True)]:
            rows=self.fixture(); rows[0].update(return_value=value,sessions=n)
            with self.assertRaises(ValueError):summarize(rows)

    def test_complete_synthetic_join_filters_other_assets_and_counts_cash_once(self):
        from datetime import date
        import io
        import json
        from unittest.mock import patch
        import pandas as pd
        from quant_robot.research.labor_risk_diagnostic import calculate
        from quant_robot.research.monthly_diagnostic_registration import sha256
        sessions = pd.bdate_range('2020-01-02', '2024-06-28').date.tolist()
        sources = []
        snapshots = {'calendar': b'synthetic', 'calendar_manifest': b'synthetic'}
        for year in range(2019, 2025):
            for month in ([1, 3, 4, 5, 6] if year == 2024 else [1, *range(3, 13)]):
                raw = f'synthetic release {year}-{month}'.encode()
                snapshots[f'release_{len(sources)}'] = raw
                sources.append(dict(declared_release_date=f'{year}-{month:02}-17',
                    observation_month=f'{year-1}-12' if month == 1 else f'{year}-{month-1:02}',
                    rate_tenths_pct=50+year%2, raw_sha256=sha256(raw)))
        snapshots['source_rows'] = json.dumps({'rows': sources}).encode()
        for year in range(2020, 2025):
            rows = [dict(date=d, asset_id=a, market='CN_ETF', currency='CNY', open=p)
                for d in sessions if d.year == year
                for a,p in [('CN_ETF_XSHG_510300',10.), ('CN_ETF_XSHG_510050',999.)]]
            stream = io.BytesIO(); pd.DataFrame(rows).to_parquet(stream, index=False)
            snapshots[f'bars_{year}'] = stream.getvalue()
        actions = dict(schema_version=3, source_ref='synthetic', coverage_start='2020-01-02',
            coverage_end='2024-06-28', asset_ids=['CN_ETF_XSHG_510300'], events=[dict(
                event_id='synthetic', asset_id='CN_ETF_XSHG_510300', kind='cash_dividend',
                announced_date='2023-01-09', record_date='2023-01-17', ex_date='2023-01-18',
                pay_date='2023-01-20', cash_per_share=.1, cash_amount_basis='gross')])
        snapshots['actions'] = json.dumps(actions).encode()
        with patch('quant_robot.data.cn_calendar_snapshot.calendar_rows_from_snapshot',
                return_value=[(d,True) for d in sessions]):
            result = calculate(snapshots)
        self.assertEqual(result['ETF_open_values_decoded'], 49)
        self.assertEqual(len(result['observations']), 48)
        cash_rows = [r for r in result['observations'] if r['return_value']]
        self.assertEqual(len(cash_rows), 1)
        self.assertEqual(cash_rows[0]['exit_date'], '2023-01-18')
        self.assertAlmostEqual(cash_rows[0]['return_value'], .01)
        self.assertFalse(result['net_account_run'])
        snapshots['release_0'] = b'altered'
        with patch('pandas.read_parquet', side_effect=AssertionError('early price read')):
            with self.assertRaisesRegex(ValueError, 'pinned original'):
                calculate(snapshots)
