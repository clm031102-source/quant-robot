import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore


class DatasetStoreTests(unittest.TestCase):
    def test_write_frame_uses_stable_partition_path_and_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DatasetStore(tmp)
            frame = pd.DataFrame({"symbol": ["000001.SZ"], "date": ["2024-01-02"], "close": [10.5]})

            written = store.write_frame(frame, "raw/tushare/daily", {"trade_date": "20240102"})

            self.assertTrue(written.exists())
            self.assertTrue(store.exists("raw/tushare/daily", {"trade_date": "20240102"}))
            self.assertIn("trade_date=20240102", written.as_posix())

    def test_read_frame_reads_csv_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DatasetStore(tmp)
            frame = pd.DataFrame({"symbol": ["000001.SZ"], "close": [10.5]})
            store.write_frame(frame, "processed/bars", {"market": "CN", "year": "2024"})

            result = store.read_frame("processed/bars", {"market": "CN", "year": "2024"})

            self.assertEqual(result.loc[0, "symbol"], "000001.SZ")

    def test_write_frame_removes_stale_alternate_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DatasetStore(tmp)
            partitions = {"market": "CN", "year": "2024"}
            with patch("quant_robot.storage.dataset_store._has_parquet_engine", return_value=False):
                csv_path = store.write_frame(
                    pd.DataFrame({"symbol": ["OLD"], "close": [1.0]}),
                    "processed/bars",
                    partitions,
                )
            with patch("quant_robot.storage.dataset_store._has_parquet_engine", return_value=True):
                parquet_path = store.write_frame(
                    pd.DataFrame({"symbol": ["NEW"], "close": [2.0]}),
                    "processed/bars",
                    partitions,
                )

            self.assertTrue(parquet_path.exists())
            self.assertFalse(csv_path.exists())
            self.assertEqual(store.read_frame("processed/bars", partitions).loc[0, "symbol"], "NEW")

    def test_failed_write_does_not_replace_existing_partition(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DatasetStore(tmp)
            partitions = {"market": "CN", "year": "2024"}
            existing = store.write_frame(
                pd.DataFrame({"symbol": ["OLD"], "close": [1.0]}),
                "processed/bars",
                partitions,
            )
            original = existing.read_bytes()

            def corrupt_then_fail(_frame, path, *args, **kwargs):
                Path(path).write_bytes(b"partial")
                raise OSError("simulated write failure")

            target = "pandas.DataFrame.to_parquet" if existing.suffix == ".parquet" else "pandas.DataFrame.to_csv"
            with patch(target, autospec=True, side_effect=corrupt_then_fail):
                with self.assertRaisesRegex(OSError, "simulated write failure"):
                    store.write_frame(
                        pd.DataFrame({"symbol": ["NEW"], "close": [2.0]}),
                        "processed/bars",
                        partitions,
                    )

            self.assertEqual(existing.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
