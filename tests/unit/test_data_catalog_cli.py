import json
import unittest

from scripts.show_data_catalog import render_catalog


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


if __name__ == "__main__":
    unittest.main()
