import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tests.unit.test_us_sector_momentum_screen import artificial_sources, method

PATH = Path(__file__).resolve().parents[2] / "scripts/run_us_sector_momentum_screen.py"
SPEC = importlib.util.spec_from_file_location("sector_controller_test", PATH)
C = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(C)


class SectorControllerTests(unittest.TestCase):
    def test_source_claim_blocks_second_capture_before_network(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            C.write(directory / "capture_claim.json", {"already": True})
            with patch.object(C, "admit", return_value=({}, {})), patch.object(C.urllib.request, "build_opener") as opener:
                with self.assertRaises(FileExistsError):
                    C.capture(directory)
                opener.assert_not_called()

    def test_numeric_claim_blocks_second_price_read(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            outcome = {"sources": {}}
            C.write(directory / "capture_outcome.json", outcome)
            C.write(directory / "numeric_claim.json", {"already": True})
            packet = {"source_structure": {}, "capture_outcome": C.pin(directory / "capture_outcome.json"), "source_files": {}}
            real_read = C.read
            with patch.object(C, "admit", return_value=(packet, {})), patch.object(C, "bound"), \
                 patch.object(C, "saved_sources", return_value=artificial_sources()), \
                 patch.object(C, "read", side_effect=lambda p: method() if str(p).endswith(C.METHOD) else real_read(p)), \
                 patch.object(C.M, "source_qa") as qa:
                with self.assertRaises(FileExistsError):
                    C.run(directory)
                qa.assert_not_called()

    def test_failed_qa_consumes_scope_without_factor_screen(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            C.write(directory / "capture_outcome.json", {"sources": {}})
            packet = {"source_structure": {}, "capture_outcome": C.pin(directory / "capture_outcome.json"), "source_files": {}}
            real_read = C.read
            with patch.object(C, "admit", return_value=(packet, {})), patch.object(C, "bound"), patch.object(C, "validate_packet"), \
                 patch.object(C, "saved_sources", return_value=artificial_sources()), \
                 patch.object(C, "read", side_effect=lambda p: method() if str(p).endswith(C.METHOD) else real_read(p)), \
                 patch.object(C.M, "screen") as screen:
                C.run(directory)
                screen.assert_not_called()
            self.assertTrue((directory / "numeric_claim.json").exists())
            self.assertTrue((directory / "financial_decode_started.json").exists())
            result = json.loads((directory / "outcome.json").read_text())
            self.assertEqual(result["status"], "source_qa_failed_closed")
            self.assertEqual(result["candidate_screens"], 0)

    def test_pin_detects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "source.json"
            p.write_bytes(b"original")
            ref = C.pin(p)
            p.write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "bound_file_changed"):
                C.bound(ref)

    def test_missing_reviews_cannot_create_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            C.write(directory / "capture_registration.json", {"stage": "capture"})
            with patch.object(C, "validate_packet"), patch.object(C.urllib.request, "build_opener") as opener:
                with self.assertRaises(FileNotFoundError):
                    C.capture(directory)
                opener.assert_not_called()
            self.assertFalse((directory / "capture_claim.json").exists())


if __name__ == "__main__":
    unittest.main()
