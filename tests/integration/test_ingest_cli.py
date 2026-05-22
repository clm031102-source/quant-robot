import json
import tempfile
import unittest
from pathlib import Path

from scripts.ingest_data import run_ingest


class IngestCliTests(unittest.TestCase):
    def test_fixture_ingest_writes_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_ingest(source="fixture", market="CN", output_dir=Path(tmp))

            report_path = Path(tmp) / "quality_report.json"
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(result["market"], "CN")
            self.assertEqual(report["markets"], ["CN"])
            self.assertGreater(report["rows"], 0)

    def test_tushare_fixture_ingest_writes_manifest_and_processed_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_ingest(source="tushare-fixture", market="CN", output_dir=Path(tmp))

            self.assertEqual(result["source"], "tushare")
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "quality_report.json").exists())
            self.assertGreater(result["processed_rows"], 0)


if __name__ == "__main__":
    unittest.main()
