"""Synthetic curve history; no network, signals or ETF returns."""
import unittest

from quant_robot.data.sources.chinabond_history import monthly_inputs, parse_history


def page(rows, headers=None):
    headers = headers or ['Yield Curve Name', 'Date', '3M', '6M', '1Y',
                          '3Y', '5Y', '7Y', '10Y', '30Y']
    cells = [headers] + [
        ['ChinaBond Government Bond Yield Curve', day, '1', '1', y1,
         '2', '2', '2', y10, '3'] for day, y1, y10 in rows]
    return ('<div id="gjqxData"><table>' + ''.join(
        '<tr>' + ''.join('<td>' + x + '</td>' for x in row) + '</tr>'
        for row in cells) + '</table></div>').encode()


class ChinaBondHistoryTests(unittest.TestCase):
    def parse(self, rows, **kwargs):
        return parse_history(page(rows), start='2011-12-01', end='2011-12-31', **kwargs)

    def test_weekend_curve_observation_survives_month_end_selection(self):
        rows = self.parse([('2011-12-30', '2.7', '3.4'), ('2011-12-31', '2.8', '3.5')])
        result = monthly_inputs(rows, first='2011-12', last='2012-01')
        self.assertEqual(result[0]['observation_date'], '2011-12-31')
        self.assertEqual(result[0]['yield_1y_percent'], '2.8')
        self.assertEqual(result[0]['status'], 'conditional')
        self.assertEqual(result[1]['status'], 'unknown')
        self.assertEqual(result[1]['reason'], 'no_observation')

    def test_missing_latest_tenor_never_falls_back_or_joins_dates(self):
        rows = self.parse([('2011-12-30', '2.7', '3.4'), ('2011-12-31', '--', '3.5')])
        result = monthly_inputs(rows, first='2011-12', last='2011-12')[0]
        self.assertEqual(result['observation_date'], '2011-12-31')
        self.assertEqual(result['status'], 'unknown')
        self.assertEqual(result['reason'], 'required_tenor_missing')

    def test_age_limit_includes_seven_but_excludes_eight_calendar_days(self):
        for day, expected in [('2011-12-24', 'conditional'), ('2011-12-23', 'unknown')]:
            with self.subTest(day=day):
                result = monthly_inputs(self.parse([(day, '2', '3')]),
                                        first='2011-12', last='2011-12')[0]
                self.assertEqual(result['status'], expected)

    def test_duplicate_dates_rejected_within_and_between_responses(self):
        row = ('2011-12-30', '2', '3')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.parse([row, row])
        rows = self.parse([row])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            monthly_inputs(rows + rows, first='2011-12', last='2011-12')

    def test_wrong_curve_header_and_extra_region_rejected(self):
        raw = page([('2011-12-30', '2', '3')])
        for changed in [raw.replace(b'Government Bond', b'Corporate Bond'),
                        raw.replace(b'<td>10Y</td>', b'<td>20Y</td>'), raw + raw]:
            with self.subTest(changed=changed[:40]):
                with self.assertRaises(ValueError):
                    parse_history(changed, start='2011-12-01', end='2011-12-31')

    def test_dates_must_be_iso_unique_and_within_request(self):
        for day in ['2011-11-30', '2011-12-32', '2011-12-1']:
            with self.subTest(day=day):
                with self.assertRaises(ValueError):
                    self.parse([(day, '2', '3')])

    def test_nonfinite_or_unrecognized_yield_rejected(self):
        for value in ['NaN', 'Infinity', 'oops', '2%']:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.parse([('2011-12-31', value, '3')])

    def test_size_empty_and_row_limits_rejected(self):
        with self.assertRaises(ValueError):
            parse_history(b'x' * 1_000_001, start='2011-12-01', end='2011-12-31')
        with self.assertRaises(ValueError):
            self.parse([])
        with self.assertRaises(ValueError):
            self.parse([('2011-12-30', '2', '3'), ('2011-12-31', '2', '3')], max_rows=1)

    def test_partial_or_nested_table_rejected(self):
        raw = page([('2011-12-31', '2', '3')])
        for changed in [raw[:-6], raw.replace(b'<table>', b'<table><table>')]:
            with self.assertRaises(ValueError):
                parse_history(changed, start='2011-12-01', end='2011-12-31')

    def test_leap_month_and_outside_month_range(self):
        rows = parse_history(page([('2012-02-29', '2', '3')]),
                             start='2012-02-01', end='2012-02-29')
        result = monthly_inputs(rows, first='2012-02', last='2012-02')[0]
        self.assertEqual(result['age_calendar_days'], 0)
        with self.assertRaises(ValueError):
            monthly_inputs(rows, first='2011-12', last='2012-01')


if __name__ == '__main__':
    unittest.main()
