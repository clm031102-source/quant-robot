import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class CnEtfPcfVendorRequestTests(unittest.TestCase):
    def test_vendor_request_matches_delivery_contract(self):
        request = json.loads(
            (
                ROOT / "configs" / "cn_etf_pcf_vendor_request_20260728.json"
            ).read_text(encoding="utf-8")
        )
        contract = json.loads(
            (ROOT / "configs" / "cn_etf_pcf_delivery_contract.json").read_text(
                encoding="utf-8"
            )
        )

        scope = request["requested_scope"]
        frozen = contract["frozen_delivery_scope"]
        self.assertEqual(scope["target_universe_sha256"], frozen["target_universe_sha256"])
        self.assertEqual(scope["target_etfs"], frozen["target_etfs"])
        self.assertEqual(scope["official_sessions"], frozen["official_sessions"])
        self.assertEqual(scope["expected_etf_sessions"], frozen["expected_etf_sessions"])
        self.assertEqual(
            scope["expected_sse_etf_sessions"],
            frozen["expected_sse_etf_sessions"],
        )
        self.assertEqual(
            scope["expected_szse_etf_sessions"],
            frozen["expected_szse_etf_sessions"],
        )
        self.assertEqual(
            scope["expected_etf_sessions"],
            scope["expected_sse_etf_sessions"]
            + scope["expected_szse_etf_sessions"],
        )
        self.assertEqual(
            request["acceptance"]["required_etf_session_coverage_ratio"],
            1.0,
        )
        self.assertFalse(request["acceptance"]["duplicate_keys_allowed"])
        self.assertFalse(request["acceptance"]["final_holdout_rows_allowed"])


if __name__ == "__main__":
    unittest.main()
