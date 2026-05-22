import importlib.util
import tempfile
import unittest

import pandas as pd

from quant_robot.storage.parquet_store import ParquetStore
from quant_robot.storage.paths import bars_partition_path


class StorageTests(unittest.TestCase):
    def test_bars_partition_path_uses_frequency_market_and_year(self):
        path = bars_partition_path("data/processed", frequency="1d", market="US", year=2024)

        self.assertEqual(path.as_posix(), "data/processed/bars/frequency=1d/market=US/year=2024")

    @unittest.skipIf(importlib.util.find_spec("pyarrow") is None, "pyarrow not installed")
    def test_parquet_store_round_trips_dataframe(self):
        with tempfile.TemporaryDirectory() as tmp:
            frame = pd.DataFrame({"asset_id": ["US_XNAS_AAPL"], "market": ["US"], "year": [2024], "value": [1.0]})
            store = ParquetStore(tmp)

            store.write_dataset(frame, "sample")
            result = store.read_dataset("sample")

            self.assertEqual(result.loc[0, "asset_id"], "US_XNAS_AAPL")


if __name__ == "__main__":
    unittest.main()
