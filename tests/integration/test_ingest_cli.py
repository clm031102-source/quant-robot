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


if __name__ == "__main__":
    unittest.main()
