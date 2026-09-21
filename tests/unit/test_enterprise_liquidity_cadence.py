"""Synthetic timing tests; no real market outcome inputs."""
from datetime import date, timedelta
import unittest

from quant_robot.research.enterprise_liquidity_cadence import (
    event_intervals, later_intervals, describe, screen_counts,
)


def sessions(start, end):
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    return [(a + timedelta(days=n)).isoformat() for n in range((b-a).days+1)
            if (a + timedelta(days=n)).weekday() < 5]


def report(quarter, day, level):
    return dict(quarter=quarter, available_date=day, index_percent=level)


class EnterpriseCadenceTests(unittest.TestCase):
    def test_release_is_used_only_at_next_open_and_equal_level_is_cash(self):
        days = sessions('2020-01-02', '2020-01-10')
        sources = [report('2018Q4', '2018-12-20', '50'),
                   report('2019Q4', '2019-12-20', '51'),
                   report('2019Q1', '2019-03-20', '49'),
                   report('2020Q1', '2020-01-03', '49')]
        rows = event_intervals(sources, days, start='2020-01-01', terminal='2020-01-10')
        self.assertEqual([(r['entry_date'], r['exit_date'], r['state']) for r in rows],
                         [('2020-01-02', '2020-01-06', 1), ('2020-01-06', '2020-01-10', 0)])
        self.assertEqual(sum(r['sessions'] for r in rows), len(days)-1)

    def test_same_open_installs_older_comparison_before_latest_decision(self):
        days = sessions('2020-01-02', '2020-01-10')
        sources = [report('2019Q1', '2020-01-04', '50'),
                   report('2020Q1', '2020-01-05', '51')]
        rows = event_intervals(list(reversed(sources)), days, start='2020-01-01',
                              terminal='2020-01-10')
        self.assertEqual([(r['entry_date'], r['state']) for r in rows],
                         [('2020-01-02', None), ('2020-01-06', 1)])

    def test_late_older_report_does_not_retroactively_recompute_current_state(self):
        days = sessions('2020-01-02', '2020-01-15')
        sources = [report('2020Q1', '2020-01-03', '51'),
                   report('2019Q1', '2020-01-07', '50'),
                   report('2019Q2', '2019-06-20', '48'),
                   report('2020Q2', '2020-01-10', '49')]
        rows = event_intervals(sources, days, start='2020-01-01', terminal='2020-01-15')
        self.assertEqual([(r['entry_date'], r['state']) for r in rows],
                         [('2020-01-02', None), ('2020-01-06', None), ('2020-01-13', 1)])
        self.assertEqual(rows[1]['reason'], 'comparison_missing')

    def test_expiration_is_strictly_after_124_calendar_days(self):
        days = sessions('2020-01-02', '2020-05-08')
        sources = [report('2018Q4', '2018-12-20', '50'),
                   report('2019Q4', '2019-12-31', '51')]
        rows = event_intervals(sources, days, start='2020-01-01', terminal='2020-05-08')
        self.assertEqual([(r['entry_date'], r['state']) for r in rows],
                         [('2020-01-02', 1), ('2020-05-04', None)])
        self.assertEqual(rows[-1]['reason'], 'expired')

    def test_new_report_at_expiration_open_preserves_selected_episode(self):
        days = sessions('2020-01-02', '2020-05-08')
        sources = [report('2018Q4', '2018-12-20', '50'),
                   report('2019Q4', '2019-12-31', '51'),
                   report('2019Q1', '2019-03-20', '50'),
                   report('2020Q1', '2020-05-03', '52')]
        rows = event_intervals(sources, days, start='2020-01-01', terminal='2020-05-08')
        self.assertEqual([r['state'] for r in rows], [1, 1])
        self.assertEqual(rows[1]['entry_date'], '2020-05-04')
        self.assertEqual(describe(rows)['selected_episodes'], 1)
        self.assertTrue(all(r['sessions'] > 0 for r in rows))

    def test_terminal_and_after_cutoff_releases_make_no_extra_interval(self):
        # This synthetic calendar explicitly closes New Year's Day.
        days = [d for d in sessions('2023-12-20', '2024-01-02') if d != '2024-01-01']
        sources = [report('2022Q2', '2022-06-20', '50'),
                   report('2023Q2', '2023-12-19', '51'),
                   report('2023Q3', '2024-03-22', '99'),
                   report('2023Q4', '2023-12-31', '99')]
        rows = event_intervals(sources, days, start='2023-12-20', terminal='2024-01-02')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['quarter'], '2023Q2')

    def test_clipped_later_carry_in_is_not_a_new_episode(self):
        days = sessions('2019-12-20', '2020-01-15')
        sources = [report('2018Q4', '2018-12-19', '50'),
                   report('2019Q4', '2019-12-19', '51'),
                   report('2019Q1', '2019-03-20', '50'),
                   report('2020Q1', '2020-01-07', '52')]
        rows = event_intervals(sources, days, start='2019-12-20', terminal='2020-01-15')
        later = later_intervals(rows, days, boundary='2020-01-01')
        self.assertEqual(later[0]['entry_date'], '2020-01-01')
        self.assertEqual(later[0]['original_entry_date'], '2019-12-20')
        self.assertEqual(later[0]['sessions'],
                         days.index('2020-01-08')-days.index('2020-01-01'))
        desc = describe(later)
        self.assertEqual((desc['selected_intervals'], desc['selected_episodes'],
                          desc['new_selected_episodes'], desc['carry_in_episodes']), (2, 1, 0, 1))
        self.assertFalse(screen_counts(rows, later)['passed'])

    def test_unknown_state_interrupts_selected_episodes_and_stays_in_counts(self):
        days = sessions('2020-01-02', '2020-01-15')
        sources = [report('2018Q4', '2018-12-20', '50'), report('2019Q4', '2019-12-20', '51'),
                   report('2020Q1', '2020-01-03', None), report('2019Q2', '2019-06-20', '48'),
                   report('2020Q2', '2020-01-10', '49')]
        rows = event_intervals(sources, days, start='2020-01-01', terminal='2020-01-15')
        desc = describe(rows)
        self.assertEqual((desc['selected_intervals'], desc['unknown_intervals'],
                          desc['selected_episodes']), (2, 1, 2))
        self.assertEqual(desc['total_sessions'], len(days)-1)
        self.assertGreater(desc['unknown_sessions'], 0)

    def test_initial_report_can_already_be_expired(self):
        days = sessions('2020-01-02', '2020-01-10')
        rows = event_intervals([report('2019Q2', '2019-06-20', '51')], days,
                               start='2020-01-01', terminal='2020-01-10')
        self.assertEqual(rows[0]['reason'], 'expired')
        self.assertIsNone(rows[0]['state'])

    def test_invalid_calendar_duplicate_report_and_nonfinite_level_rejected(self):
        days = sessions('2020-01-02', '2020-01-10')
        src = report('2019Q4', '2019-12-20', '51')
        for sources, calendar in [([src, src], days), ([src], days[::-1]),
                                  ([report('2019Q4', '2019-12-20', 'NaN')], days),
                                  ([report('2019Q4', '2019-12-20', '101')], days)]:
            with self.subTest(sources=sources, calendar=calendar), self.assertRaises(ValueError):
                event_intervals(sources, calendar, start='2020-01-01', terminal='2020-01-10')
