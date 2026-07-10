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

    def test_summary_catalog_can_skip_dataset_rows_and_row_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "reports" / "large_source_audit"
            path.mkdir(parents=True)
            (path / "bad.csv").write_bytes(b"\xff\xfe\x00not-a-readable-csv")

            catalog = build_storage_catalog(root, include_datasets=False, count_rows=False)

            self.assertEqual(catalog["total_files"], 1)
            self.assertGreater(catalog["total_bytes"], 0)
            self.assertIsNone(catalog["total_rows"])
            self.assertNotIn("datasets", catalog)

    def test_rows_are_unknown_when_dataset_details_are_omitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "processed" / "bars"
            path.mkdir(parents=True)
            (path / "part.csv").write_text("asset_id,date\nA,2024-01-02\n", encoding="utf-8")

            catalog = build_storage_catalog(root, include_datasets=False)

            self.assertEqual(catalog["total_files"], 1)
            self.assertIsNone(catalog["total_rows"])


if __name__ == "__main__":
    unittest.main()
