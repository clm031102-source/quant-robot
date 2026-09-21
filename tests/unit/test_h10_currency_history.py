"""Synthetic archived H.10 schema and timing tests."""
from datetime import date, timedelta
import unittest

from quant_robot.data.sources.h10_currency_history import parse_release, endpoint_snapshot, quarter_requests


def page(values=('6.1','6.2','ND','6.3','6.4'),country='CHINA, P.R.',currency='YUAN',
         headers=('Dec. 23','Dec. 24','Dec. 25','Dec. 26','Dec. 27'),release='December 30, 2013'):
    header='<tr>'+''.join('<th>'+x+'</th>' for x in ('COUNTRY','CURRENCY',*headers))+'</tr>'
    row='<tr>'+''.join('<td>'+x+'</td>' for x in (country,currency,*values))+'</tr>'
    return ('Release Date: '+release+' Rates in currency units per U.S. dollar except as noted'
        +'<table class="statistics">'+header+row+'</table>').encode()


class H10CurrencyTests(unittest.TestCase):
    def test_exact_units_dates_and_ND_are_preserved(self):
        rows=parse_release(page(),release_date='2013-12-30')
        self.assertEqual(len(rows),5)
        self.assertEqual(rows[0],dict(date='2013-12-23',cny_per_usd='6.1'))
        self.assertIsNone(rows[2]['cny_per_usd'])

    def test_published_memo_rows_with_omitted_opening_tr_are_accepted(self):
        memo=b'<th colspan="8">Memo:</th></tr><th>UNITED STATES</th><td>DOLLAR</td></tr>'
        raw=page().replace(b'</table>',memo+b'</table>')
        self.assertEqual(parse_release(raw,release_date='2013-12-30'),
                         parse_release(page(),release_date='2013-12-30'))

    def test_2017_publication_table_class_requires_exact_H10title(self):
        raw=page().replace(b'class="statistics"',
            b'class="pubtables" title="Foreign Exchange Rates -- H.10 Weekly"')
        self.assertEqual(parse_release(raw,release_date='2013-12-30'),
                         parse_release(page(),release_date='2013-12-30'))
        with self.assertRaises(ValueError):
            parse_release(raw.replace(b' -- H.10 Weekly',b' other table'),release_date='2013-12-30')

    def test_last_valid_quote_can_precede_missing_Friday(self):
        result=endpoint_snapshot(page(values=('6.1','6.2','ND','6.3','ND')),
            release_date='2013-12-30',quarter_end='2013-12-31')
        self.assertEqual(result['observation_date'],'2013-12-26')
        self.assertEqual(result['age_calendar_days'],5)
        self.assertEqual(result['cny_per_usd'],'6.3')

    def test_release_on_quarter_end_is_excluded(self):
        with self.assertRaises(ValueError):
            endpoint_snapshot(page(),release_date='2013-12-31',quarter_end='2013-12-31')

    def test_source_age_strictly_above14is_unknown(self):
        data=page(headers=('Dec. 09','Dec. 10','Dec. 11','Dec. 12','Dec. 13'),release='December 16, 2013')
        result=endpoint_snapshot(data,release_date='2013-12-16',quarter_end='2013-12-31')
        self.assertEqual(result['status'],'unknown')
        self.assertEqual(result['reason'],'quote_older_than14days')
        self.assertIsNone(result['cny_per_usd'])

    def test_all_ND_remains_unknown(self):
        result=endpoint_snapshot(page(values=('ND',)*5),release_date='2013-12-30',quarter_end='2013-12-31')
        self.assertEqual(result['reason'],'no_valid_quote')
        self.assertIsNone(result['observation_date'])

    def test_new_year_observations_belong_to_prior_year(self):
        data=page(headers=('Dec. 28','Dec. 29','Dec. 30','Dec. 31','Jan. 01'),release='January 4, 2021')
        rows=parse_release(data,release_date='2021-01-04')
        self.assertEqual(rows[0]['date'],'2020-12-28')
        self.assertEqual(rows[-1]['date'],'2021-01-01')

    def test_wrong_units_starred_currency_and_release_rejected(self):
        for data in [page(country='*CHINA, P.R.'),page(currency='DOLLAR'),
                     page(release='December 31, 2013'),page().replace(b'per U.S. dollar',b'per Yuan')]:
            with self.assertRaises(ValueError):
                parse_release(data,release_date='2013-12-30')

    def test_nonfinite_nonpositive_and_unknown_missing_tokens_rejected(self):
        for value in ['NaN','Infinity','0','-1','','.','NA']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                parse_release(page(values=('6','6',value,'6','6')),release_date='2013-12-30')

    def test_duplicate_china_row_or_incomplete_table_rejected(self):
        data=page()
        row=data[data.index(b'<tr><td>'):data.index(b'</table>')]
        for raw in [data.replace(b'</table>',row+b'</table>'),data.replace(b'</table>',b'')]:
            with self.assertRaises(ValueError):
                parse_release(raw,release_date='2013-12-30')

    def test_bad_week_or_future_observation_rejected(self):
        for headers in [('Dec. 23',)*5,('Dec. 30','Dec. 31','Jan. 01','Jan. 02','Jan. 03')]:
            with self.assertRaises(ValueError):
                parse_release(page(headers=headers),release_date='2013-12-30')

    def test_catalogue_selects_latest_strictly_before_each_endpoint(self):
        catalogue=[]
        for year in range(2013,2024):
            start=date(year,1,1)
            days=[start+timedelta(days=n) for n in range((date(year+1,1,1)-start).days)]
            catalogue.append(dict(yearValue=year,Months=[dict(Dates=[day.strftime('%Y%m%d')
                for day in days if day.weekday()==0])]))
        rows=quarter_requests(catalogue)
        self.assertEqual(len(rows),41)
        self.assertEqual(rows[0]['quarter_end'],'2013-09-30')
        self.assertEqual(rows[0]['release_date'],'2013-09-23')
        self.assertEqual(rows[-1]['release_date'],'2023-09-25')
        catalogue[0]['Months'][0]['Dates'].append('20130107')
        with self.assertRaises(ValueError):
            quarter_requests(catalogue)
