import tempfile
import unittest
from pathlib import Path

from quant_robot.data.ingest.manifest import IngestManifest


class IngestManifestTests(unittest.TestCase):
    def test_manifest_records_completed_partitions_and_reloads(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            manifest = IngestManifest(path)
            manifest.mark_completed("daily:20240102", rows=2)
            manifest.save()

            reloaded = IngestManifest(path)

            self.assertTrue(reloaded.is_completed("daily:20240102"))
            self.assertEqual(reloaded.data["completed"]["daily:20240102"]["rows"], 2)

    def test_manifest_records_failed_partitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = IngestManifest(Path(tmp) / "manifest.json")

            manifest.mark_failed("daily:20240103", "network")

            self.assertEqual(manifest.data["failed"]["daily:20240103"], "network")


if __name__ == "__main__":
    unittest.main()
