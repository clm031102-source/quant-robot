import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.processed_bars import load_processed_bars


class ProcessedBarsDateBoundaryTests(unittest.TestCase):
    def test_end_date_skips_later_year_partitions_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = DatasetStore(root)
            store.write_frame(
                pd.DataFrame(
                    [
                        {
                            "date": "2024-06-28",
                            "asset_id": "CN_ETF_XSHG_510300",
                            "market": "CN_ETF",
                            "adj_close": 1.0,
                        }
                    ]
                ),
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )
            sealed = store.partition_path(
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2026"},
            )
            sealed.mkdir(parents=True)
            (sealed / "_format.json").write_text(
                json.dumps({"format": "sealed", "file": "do-not-read"}),
                encoding="utf-8",
            )

            observed = load_processed_bars(root, "CN_ETF", end_date="2024-12-31")

            self.assertEqual(len(observed), 1)
            self.assertEqual(pd.Timestamp(observed.iloc[0]["date"]), pd.Timestamp("2024-06-28"))

    def test_end_date_filters_rows_inside_the_last_allowed_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = DatasetStore(root)
            store.write_frame(
                pd.DataFrame(
                    [
                        {
                            "date": "2024-06-28",
                            "asset_id": "CN_ETF_XSHG_510300",
                            "market": "CN_ETF",
                            "adj_close": 1.0,
                        },
                        {
                            "date": "2024-12-31",
                            "asset_id": "CN_ETF_XSHG_510300",
                            "market": "CN_ETF",
                            "adj_close": 1.1,
                        },
                    ]
                ),
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )

            observed = load_processed_bars(root, "CN_ETF", end_date="2024-06-28")

            self.assertEqual(len(observed), 1)
            self.assertEqual(pd.Timestamp(observed.iloc[0]["date"]), pd.Timestamp("2024-06-28"))

    def test_start_date_skips_earlier_partitions_before_reading(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = DatasetStore(root)
            sealed = store.partition_path(
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2020"},
            )
            sealed.mkdir(parents=True)
            (sealed / "_format.json").write_text(
                json.dumps({"format": "sealed", "file": "do-not-read"}),
                encoding="utf-8",
            )
            store.write_frame(
                pd.DataFrame(
                    [
                        {
                            "date": "2024-01-02",
                            "asset_id": "CN_ETF_XSHG_510300",
                            "market": "CN_ETF",
                            "adj_close": 1.0,
                        }
                    ]
                ),
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )

            observed = load_processed_bars(root, "CN_ETF", start_date="2024-01-01")

            self.assertEqual(len(observed), 1)
            self.assertEqual(pd.Timestamp(observed.iloc[0]["date"]), pd.Timestamp("2024-01-02"))

    def test_bounded_read_rejects_unparseable_year_partition(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = DatasetStore(root)
            partition = store.partition_path(
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "unknown"},
            )
            partition.mkdir(parents=True)

            with self.assertRaisesRegex(ValueError, "Invalid processed-bar year partition"):
                load_processed_bars(root, "CN_ETF", end_date="2024-12-31")

    def test_bounded_read_requires_a_date_column(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = DatasetStore(root)
            store.write_frame(
                pd.DataFrame(
                    [
                        {
                            "asset_id": "CN_ETF_XSHG_510300",
                            "market": "CN_ETF",
                            "adj_close": 1.0,
                        }
                    ]
                ),
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )

            with self.assertRaisesRegex(ValueError, "date or timestamp column"):
                load_processed_bars(root, "CN_ETF", end_date="2024-12-31")


if __name__ == "__main__":
    unittest.main()
