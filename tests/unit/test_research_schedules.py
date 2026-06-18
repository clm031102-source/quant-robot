import unittest
from datetime import date

from quant_robot.research.schedules import rebalance_phase_dates


class ResearchScheduleTests(unittest.TestCase):
    def test_rebalance_phase_dates_selects_sorted_unique_dates_by_offset(self) -> None:
        dates = [
            date(2024, 1, 8),
            date(2024, 1, 2),
            date(2024, 1, 3),
            date(2024, 1, 2),
            date(2024, 1, 4),
            date(2024, 1, 5),
            date(2024, 1, 9),
            date(2024, 1, 10),
        ]

        selected = rebalance_phase_dates(dates, interval=3, offset=1)

        self.assertEqual(selected, [date(2024, 1, 3), date(2024, 1, 8)])

    def test_rebalance_phase_dates_rejects_invalid_offset(self) -> None:
        with self.assertRaisesRegex(ValueError, "offset"):
            rebalance_phase_dates([date(2024, 1, 2)], interval=5, offset=5)


if __name__ == "__main__":
    unittest.main()
