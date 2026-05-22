import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.catalog import build_storage_catalog


class StorageCatalogTests(unittest.TestCase):
    def test_catalog_summarizes_local_dataset_files_and_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "processed" / "bars" / "frequency=1d" / "market=CN" / "year=2024"
            path.mkdir(parents=True)
            (path / "part-00000.csv").write_text("asset_id,date\nA,2024-01-02\nB,2024-01-03\n", encoding="utf-8")

            catalog = build_storage_catalog(root)

            self.assertEqual(catalog["root"], str(root))
            self.assertEqual(catalog["total_files"], 1)
            self.assertEqual(catalog["total_rows"], 2)
            dataset = catalog["datasets"][0]
            self.assertEqual(dataset["dataset"], "processed/bars")
            self.assertEqual(dataset["partitions"]["market"], "CN")


if __name__ == "__main__":
    unittest.main()
