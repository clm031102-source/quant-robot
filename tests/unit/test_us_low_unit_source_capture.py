import importlib.util
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("low_unit_capture", ROOT / "scripts/capture_us_low_unit_allocation_sources.py")
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class TestLowUnitSourceCapture(unittest.TestCase):
    def test_fixed_four_requests_and_distinct_source_windows(self):
        self.assertEqual([r["role"] for r in M.REQUESTS], ["SPYM_daily", "SPYM_actions", "GLDM_daily", "GLDM_actions"])
        for r in M.REQUESTS:
            self.assertIn("period1=1606798800", r["url"])
            self.assertIn("period2=1767243600&interval=1d" if r["kind"] == "daily" else "period2=1794114000&interval=1mo", r["url"])

    def test_claim_prevents_second_network_attempt(self):
        with TemporaryDirectory() as temp:
            directory = Path(temp)
            M.H.save(directory / "capture_claim.json", {"already": "consumed"})
            with patch.object(M, "admit", return_value=({"requests": list(M.REQUESTS)}, {})), patch.object(M.urllib.request, "build_opener") as opener:
                with self.assertRaises(FileExistsError):
                    M.capture(directory)
                opener.assert_not_called()

    def test_transport_failure_has_no_retry_or_second_request(self):
        with TemporaryDirectory() as temp:
            with patch.object(M, "admit", return_value=({"requests": list(M.REQUESTS)}, {})), patch.object(M.urllib.request, "build_opener") as opener:
                opener.return_value.open.side_effect = OSError("synthetic transport failure")
                with self.assertRaisesRegex(OSError, "synthetic transport"):
                    M.capture(Path(temp))
                self.assertEqual(opener.return_value.open.call_count, 1)
                self.assertEqual(M.H.load(Path(temp) / "capture_failure.json")["status"], "failed_no_retry")

    def test_all_four_bodies_remain_opaque(self):
        with TemporaryDirectory() as temp:
            with patch.object(M, "admit", return_value=({"requests": list(M.REQUESTS)}, {})), patch.object(M.urllib.request, "build_opener") as opener:
                response = opener.return_value.open.return_value.__enter__.return_value
                response.status = 200
                response.headers.get.side_effect = lambda key, default=None: "application/json" if key == "Content-Type" else default
                response.read.return_value = b'{"unparsed_price":NaN}'
                outcome = M.H.load(M.capture(Path(temp))["path"])
                self.assertEqual(opener.return_value.open.call_count, 4)
                self.assertFalse(outcome["financial_decode_allowed"])
                for refs in outcome["sources"].values():
                    self.assertEqual(M.H.bound(refs["raw"]), b'{"unparsed_price":NaN}')
                    self.assertEqual(M.H.load(refs["receipt"]["path"])["numeric_conversions"], 0)


if __name__ == "__main__":
    unittest.main()
