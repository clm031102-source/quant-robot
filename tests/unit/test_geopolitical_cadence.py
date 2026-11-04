import unittest

from quant_robot.research.geopolitical_cadence import MONTHS, screen, window_state


def window(month, target=1):
    end = int(month[:4]) * 12 + int(month[4:]) - 1
    rows = [dict(month=f"{(n - 1) // 12:04d}-{(n - 1) % 12 + 1:02d}", GPRT="1")
            for n in range(end - 12, end + 1)]
    rows[-1]["GPRT"] = str(target)
    return rows


def series(selected):
    return [dict(month=m, window=window(m, 2 if i in selected else 1)) for i, m in enumerate(MONTHS)]


class GeopoliticalCadenceTests(unittest.TestCase):
    def test_strict_median_uses_only_previous_twelve_values(self):
        rows = window("202204")
        for i in range(12):
            rows[i]["GPRT"] = str(i)
        rows[-1]["GPRT"] = "5.5"
        self.assertEqual(window_state("202204", rows)["state"], 0)
        rows[-1]["GPRT"] = "5.500000000001"
        result = window_state("202204", rows)
        self.assertEqual(result["state"], 1)
        self.assertEqual(result["median_prior_12"], "5.5")

    def test_unknown_is_not_known_cash_and_breaks_an_episode(self):
        rows = series(range(46))
        rows[10]["window"] = []
        result = screen(rows)
        self.assertEqual(result["full"]["unknown_months"], 1)
        self.assertEqual(result["full"]["known_cash_months"], 0)
        self.assertEqual(result["full"]["new_source_episodes"], 2)
        self.assertFalse(result["passed"])

    def test_one_long_holding_is_not_many_independent_episodes(self):
        result = screen(series(range(46)))
        self.assertEqual(result["full"]["selected_months"], 46)
        self.assertEqual(result["full"]["new_source_episodes"], 1)
        self.assertEqual(result["later"]["new_source_episodes"], 0)
        self.assertFalse(result["passed"])

    def test_six_separate_full_and_three_later_episodes_meet_fixed_minima(self):
        selected = {i for start in (0, 6, 12, 22, 30, 38) for i in range(start, start + 4)}
        result = screen(series(selected))
        self.assertEqual(result["full"]["selected_months"], 24)
        self.assertEqual(result["later"]["selected_months"], 12)
        self.assertEqual(result["full"]["new_source_episodes"], 6)
        self.assertEqual(result["later"]["new_source_episodes"], 3)
        self.assertTrue(result["passed"])
        self.assertFalse(result["financial_execution_allowed"])

    def test_later_carry_in_does_not_count_as_new(self):
        selected = {i for start in (0, 6, 12, 20, 30, 38) for i in range(start, start + 4)}
        result = screen(series(selected))
        self.assertEqual(result["full"]["new_source_episodes"], 6)
        self.assertEqual(result["later"]["new_source_episodes"], 2)
        self.assertTrue(result["rows"][22]["later_carry_in"])
        self.assertFalse(result["checks"]["new_source_episodes_later"])
        self.assertFalse(result["passed"])

    def test_failed_source_requirements_remain_unknown(self):
        for value in (None, True, "NaN", "Infinity", "-1"):
            rows = window("202204")
            rows[-1]["GPRT"] = value
            with self.subTest(value=value):
                self.assertIsNone(window_state("202204", rows)["state"])
        rows = window("202204")
        rows[-1]["month"] = "2022-04"
        self.assertIsNone(window_state("202204", rows)["state"])

    def test_missing_duplicate_or_reordered_decision_months_are_rejected(self):
        rows = series(set())
        for invalid in (rows[:-1], rows[::-1], [rows[1], *rows[1:]]):
            with self.assertRaises(ValueError):
                screen(invalid)


if __name__ == "__main__":
    unittest.main()
