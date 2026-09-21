import unittest
from datetime import date
import pandas as pd

from quant_robot.research.option_activity_diagnostic import monthly_rows, summarize


class OptionActivityDiagnosticTests(unittest.TestCase):
    def fixture(self):
        days = [date(2020, m, d) for m in range(1, 6) for d in (2, 3, 6)]
        counts = [dict(date=str(d), CALL_VOLUME=20 if d.month == 1 else 10,
            PUT_VOLUME=10, LEAVES_CALL_QTY=10, LEAVES_PUT_QTY=10) for d in days]
        levels = pd.Series([100.0 + i for i in range(len(days))], index=days)
        return days, counts, levels

    def test_previous_complete_month_second_session_and_no_terminal_outcome(self):
        days, counts, levels = self.fixture()
        rows = monthly_rows(counts, levels, days)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]['feature_month'], '2020-01')
        self.assertEqual(rows[0]['entry_date'], '2020-02-03')
        self.assertEqual(rows[0]['exit_date'], '2020-03-03')
        self.assertGreater(rows[0]['score'], 0)
        self.assertAlmostEqual(rows[0]['total_return'], 107 / 104 - 1)
        self.assertEqual(rows[1]['selected'], 0)

    def test_missing_duplicate_zero_nonfinite_and_negative_counts_fail(self):
        days, counts, levels = self.fixture()
        for mutated in (counts[:-1], counts + [counts[0]]):
            with self.assertRaises(ValueError): monthly_rows(mutated, levels, days)
        for value in (0, -1, float('nan'), True):
            mutated = [dict(r) for r in counts]
            mutated[0]['LEAVES_CALL_QTY'] = value
            with self.assertRaises(ValueError): monthly_rows(mutated, levels, days)

    def test_same_month_counts_do_not_change_previous_signal(self):
        days, counts, levels = self.fixture()
        original = monthly_rows(counts, levels, days)
        for r in counts:
            if r['date'].startswith('2020-02'): r['CALL_VOLUME'] *= 100
        changed = monthly_rows(counts, levels, days)
        self.assertEqual(original[0], changed[0])
        self.assertNotEqual(original[1]['score'], changed[1]['score'])

    def test_bootstrap_deterministic_and_negative_relation_rejected(self):
        rows = [dict(score=float(i-10), total_return=(10-i)/100,
                     selected=int(i>10), entry_date=f'2023-{i%12+1:02d}-03') for i in range(24)]
        a = summarize(rows, replications=100, seed=19)
        self.assertEqual(a, summarize(rows, replications=100, seed=19))
        self.assertAlmostEqual(a['spearman'], -1)
        self.assertFalse(a['gross_screen_passed'])
        self.assertFalse(a['formal_positive_ev_verified'])

    def test_single_signal_state_cannot_pass(self):
        rows = [dict(score=float(i+1), total_return=i/100, selected=1,
                     entry_date=f'2023-{i%12+1:02d}-03') for i in range(24)]
        self.assertFalse(summarize(rows, replications=100)['gross_screen_passed'])


if __name__ == '__main__': unittest.main()
