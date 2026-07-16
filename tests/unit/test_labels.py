import unittest

import pandas as pd

from quant_robot.research.labels import (
    filter_market_calendar_aligned_forward_returns,
    make_forward_returns,
)


class LabelTests(unittest.TestCase):
    def test_forward_returns_respect_execution_lag(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 5,
                "market": ["US"] * 5,
                "date": pd.date_range("2024-01-01", periods=5).date,
                "adj_close": [100.0, 110.0, 121.0, 133.1, 146.41],
            }
        )

        labels = make_forward_returns(bars, horizons=(1,), execution_lag=1)
        first = labels[labels["date"] == pd.Timestamp("2024-01-01").date()].iloc[0]

        self.assertAlmostEqual(first["forward_return"], 0.10)
        self.assertEqual(first["entry_date"], pd.Timestamp("2024-01-02").date())
        self.assertEqual(first["exit_date"], pd.Timestamp("2024-01-03").date())

    def test_forward_returns_drop_rows_without_future_exit(self):
        bars = pd.DataFrame(
            {
                "asset_id": ["A"] * 3,
                "market": ["US"] * 3,
                "date": pd.date_range("2024-01-01", periods=3).date,
                "adj_close": [100.0, 110.0, 121.0],
            }
        )

        labels = make_forward_returns(bars, horizons=(1,), execution_lag=1)

        self.assertEqual(set(labels["date"]), {pd.Timestamp("2024-01-01").date()})

    def test_market_calendar_alignment_drops_compressed_asset_horizons(self):
        dates = pd.date_range("2024-01-01", periods=6).date
        bars = pd.DataFrame(
            [
                *[
                    {
                        "asset_id": "B",
                        "market": "US",
                        "date": signal_date,
                        "adj_close": 100.0 + index,
                    }
                    for index, signal_date in enumerate(dates)
                ],
                *[
                    {
                        "asset_id": "A",
                        "market": "US",
                        "date": signal_date,
                        "adj_close": 100.0 + index,
                    }
                    for index, signal_date in enumerate(dates)
                    if signal_date != dates[1]
                ],
            ]
        )
        labels = make_forward_returns(bars, horizons=(1,), execution_lag=1)

        aligned = filter_market_calendar_aligned_forward_returns(labels, bars)

        compressed = aligned[
            aligned["asset_id"].eq("A")
            & pd.to_datetime(aligned["date"]).eq(pd.Timestamp(dates[0]))
        ]
        complete = aligned[
            aligned["asset_id"].eq("B")
            & pd.to_datetime(aligned["date"]).eq(pd.Timestamp(dates[0]))
        ]
        self.assertTrue(compressed.empty)
        self.assertEqual(len(complete), 1)
        self.assertEqual(pd.Timestamp(complete.iloc[0]["entry_date"]), pd.Timestamp(dates[1]))
        self.assertEqual(pd.Timestamp(complete.iloc[0]["exit_date"]), pd.Timestamp(dates[2]))


if __name__ == "__main__":
    unittest.main()
