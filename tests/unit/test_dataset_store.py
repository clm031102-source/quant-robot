import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
