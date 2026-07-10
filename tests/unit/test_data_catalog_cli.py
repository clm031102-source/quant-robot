import json
import tempfile
import unittest
from pathlib import Path

from scripts.show_data_catalog import render_catalog, run_data_catalog_cli


class DataCatalogCliTests(unittest.TestCase):
    def test_render_catalog_can_emit_summary_without_dataset_rows(self):
        catalog = {
            "root": "data",
            "total_files": 2,
            "total_bytes": 42,
            "total_rows": 3,
            "datasets": [{"path": "a.csv"}, {"path": "b.csv"}],
        }

        rendered = json.loads(render_catalog(catalog, summary_only=True))

        self.assertEqual(rendered["root"], "data")
        self.assertEqual(rendered["total_files"], 2)
        self.assertNotIn("datasets", rendered)

    def test_summary_only_cli_does_not_count_csv_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "processed" / "candidate_source"
            path.mkdir(parents=True)
            (path / "bad.csv").write_bytes(b"\xff\xfe\x00not-a-readable-csv")

            rendered = json.loads(run_data_catalog_cli(root=root, summary_only=True))

        self.assertEqual(rendered["total_files"], 1)
        self.assertIsNone(rendered["total_rows"])
        self.assertNotIn("datasets", rendered)


if __name__ == "__main__":
    unittest.main()
