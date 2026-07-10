import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    def test_failed_manifest_save_preserves_previous_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            manifest = IngestManifest(path)
            manifest.mark_completed("daily:20240102", rows=2)
            manifest.save()
            original = path.read_text(encoding="utf-8")
            manifest.mark_completed("daily:20240103", rows=3)

            original_write_text = Path.write_text

            def partial_then_fail(target, text, *args, **kwargs):
                original_write_text(target, "{", encoding="utf-8")
                raise OSError("simulated manifest failure")

            with patch.object(Path, "write_text", autospec=True, side_effect=partial_then_fail):
                with self.assertRaisesRegex(OSError, "simulated manifest failure"):
                    manifest.save()

            self.assertEqual(path.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
