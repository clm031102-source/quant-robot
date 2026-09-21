"""Synthetic source boundaries; no real credit spreads or financial labels."""
import unittest

from quant_robot.data.sources.chinabond_credit_history import (
    CORPORATE, GOVERNMENT, pair_months, parse_credit_history,
)


def row(day, value, curve):
    return dict(date=day, yield_1y_percent=value, curve=curve)


def page(cells):
    headers = ['Yield Curve Name', 'Date', '3M', '6M', '1Y', '3Y', '5Y', '7Y', '10Y', '30Y']
    rows = [headers] + [[CORPORATE, day, '', '', value, '', '', '', '', ''] for day, value in cells]
    return ('<div id="gjqxData"><table>' + ''.join('<tr>' + ''.join('<td>'+v+'</td>' for v in r)+'</tr>' for r in rows) + '</table></div>').encode()


class CreditHistoryTests(unittest.TestCase):
    def parse(self, raw):
        return parse_credit_history(raw, start='2020-01-01', end='2020-01-31')

    def test_one_year_projection_preserves_weekend_negative_and_missing_values(self):
        result = self.parse(page([('2020-01-04', '-0.25'), ('2020-01-03', '--')]))
        self.assertEqual([r['date'] for r in result], ['2020-01-03', '2020-01-04'])
        self.assertIsNone(result[0]['yield_1y_percent'])
        self.assertEqual(result[1]['yield_1y_percent'], '-0.25')

    def test_wrong_curve_projection_header_and_malformed_table_rejected(self):
        good = page([('2020-01-03', '3')])
        for raw in [good.replace(CORPORATE.encode(), GOVERNMENT.encode()),
                    good.replace(b'<td>10Y</td>', b'<td>20Y</td>'),
                    good.replace(b'<td></td>', b'<td>3</td>', 1), good+good,
                    good[:-6], good.replace(b'<table>', b'<table><table>')]:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                self.parse(raw)

    def test_invalid_yields_and_duplicate_or_outside_dates_rejected(self):
        for values in [[('2020-01-03', 'NaN')], [('2020-01-03', '3%')],
                       [('2019-12-31', '3')], [('2020-01-3', '3')],
                       [('2020-01-03', '3'), ('2020-01-03', '3')]]:
            with self.subTest(values=values), self.assertRaises(ValueError):
                self.parse(page(values))

    def test_request_size_range_and_empty_rejected(self):
        for raw in [b'x'*1_000_001, page([])]:
            with self.assertRaises(ValueError): self.parse(raw)
        with self.assertRaises(ValueError):
            parse_credit_history(page([('2020-01-03', '3')]), start='2018-01-01', end='2020-01-31')

    def test_missing_corporate_last_date_never_selects_earlier_common_date(self):
        gov = [row('2020-01-30', '2', GOVERNMENT), row('2020-01-31', '2', GOVERNMENT)]
        corp = [row('2020-01-30', '3', CORPORATE)]
        result = pair_months(gov, corp, first='2020-01', last='2020-02')
        self.assertEqual(result[0]['observation_date'], '2020-01-31')
        self.assertEqual(result[0]['reason'], 'same_date_corporate_observation_missing')
        self.assertEqual(result[1]['reason'], 'government_month_missing')

    def test_seven_day_limit_and_same_date_weekend_are_preserved(self):
        for day, status in [('2020-01-24', 'conditional'), ('2020-01-23', 'unknown'), ('2020-01-25', 'conditional')]:
            result = pair_months([row(day, '2', GOVERNMENT)], [row(day, '3', CORPORATE)], first='2020-01', last='2020-01')
            self.assertEqual(result[0]['status'], status)

    def test_missing_yield_never_fills_from_an_earlier_date(self):
        for gv, cv, reason in [(None, '3', 'government_one_year_missing'), ('2', None, 'corporate_one_year_missing')]:
            result = pair_months([row('2020-01-31', gv, GOVERNMENT)], [row('2020-01-31', cv, CORPORATE)], first='2020-01', last='2020-01')
            self.assertEqual(result[0]['reason'], reason)

    def test_cross_response_duplicate_wrong_population_and_out_of_range_rejected(self):
        gov, corp = [row('2020-01-31', '2', GOVERNMENT)], [row('2020-01-31', '3', CORPORATE)]
        for g,c in [(gov+gov,corp),(gov,corp+corp),(corp,corp),(gov,[row('2019-12-31','3',CORPORATE)])]:
            with self.assertRaises(ValueError): pair_months(g,c,first='2020-01',last='2020-01')

    def test_month_pairing_requires_normalized_missing_but_not_other_tenors(self):
        gov = [dict(row('2020-01-31', '2', GOVERNMENT), yield_10y_percent=None)]
        corp = [row('2020-01-31', '3', CORPORATE)]
        self.assertEqual(pair_months(gov,corp,first='2020-01',last='2020-01')[0]['status'], 'conditional')
        for missing in ['', '-', '--']:
            with self.assertRaisesRegex(ValueError, 'normalized'):
                pair_months(gov,[row('2020-01-31',missing,CORPORATE)],first='2020-01',last='2020-01')


if __name__ == '__main__':
    unittest.main()
