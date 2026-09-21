"""Offline compatibility for the observed API envelope; no market fixtures."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import json
import unittest
from unittest.mock import patch

from quant_robot.data.sources import tushare_moneyflow_observation as collector
from tests.unit import test_moneyflow_receipt_asof as fixtures
from tests.unit.test_tushare_moneyflow_observation import payload


def mixed(day="20250102", value=12.5):
    body = payload(day, value)
    body["data"]["items"].append(["920163.BJ", day, 4.0])
    body["data"].update(count=0, has_more=False)
    return body


class MoneyflowReceiptVersionTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.MoneyflowReceiptAsOfTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def parse(self, body):
        return collector.parse_moneyflow_payload(body, trade_date="20250102", receipt_schema_version=2)

    def legacy_capture(self, body):
        with (patch.object(collector, "CAPTURE_COMMON", collector.COMMON, create=True),
              patch.object(collector, "CAPTURE_SCHEMA_VERSION", 1, create=True)):
            return self.fixture.capture(body)

    def test_v2_preserves_count_without_assigning_row_count_semantics(self):
        for count in [0, 3, 9000]:
            body = mixed(); body["data"]["count"] = count
            result = self.parse(body)
            self.assertEqual(result["receipt_schema_version"], 2)
            self.assertEqual(result["rows"], 3)
            self.assertEqual(result["eligible_source_rows"], 2)
            self.assertEqual(result["excluded_bj_source_rows"], 1)
            self.assertEqual(result["provider_count"], count)
            self.assertFalse(result["provider_count_semantics_verified"])
            self.assertEqual(result["provider_count_matches_response_rows"], count == 3)
            self.assertEqual(result["status"], "observed_unqualified")

    def test_v1_count_and_universe_rules_are_unchanged(self):
        body = payload(); body["data"]["count"] = 0
        with self.assertRaisesRegex(ValueError, "count"):
            collector.parse_moneyflow_payload(body, trade_date="20250102")
        body = mixed(); body["data"]["count"] = 3
        with self.assertRaisesRegex(ValueError, "Shanghai or Shenzhen"):
            collector.parse_moneyflow_payload(body, trade_date="20250102")

    def test_v2_invalid_count_types_and_negative_values_still_rejected(self):
        for count in [True, -1, "3", 3.0, None]:
            with self.subTest(count=count):
                body = mixed(); body["data"]["count"] = count
                with self.assertRaises(ValueError):
                    self.parse(body)

    def test_v2_excluded_values_still_contribute_to_source_fingerprint(self):
        body = mixed(); changed = deepcopy(body)
        changed["data"]["items"][-1][-1] = 5.0
        self.assertNotEqual(self.parse(body)["content_sha256"], self.parse(changed)["content_sha256"])

    def test_v2_unknown_identities_dates_duplicates_and_nonfinite_rejected(self):
        for symbol in ["510300.SH", "200001.SZ", "600584.HK", "838163.BJ", "921163.BJ"]:
            body = mixed(); body["data"]["items"][-1][0] = symbol
            with self.subTest(symbol=symbol), self.assertRaises(ValueError):
                self.parse(body)
        for change in [lambda b: b["data"]["items"][-1].__setitem__(1, "20250101"),
                       lambda b: b["data"]["items"].append(b["data"]["items"][-1]),
                       lambda b: b["data"]["items"][-1].__setitem__(2, float("inf")),
                       lambda b: b["data"]["items"][-1].__setitem__(2, "4")]:
            body = mixed(); change(body)
            with self.assertRaises(ValueError):
                self.parse(body)

    def test_v2_empty_projection_nulls_and_has_more_remain_incomplete(self):
        for change in [lambda b: b["data"].update(items=[b["data"]["items"][-1]]),
                       lambda b: b["data"]["items"][0].__setitem__(2, None),
                       lambda b: b["data"].update(has_more=True)]:
            body = mixed(); change(body)
            self.assertEqual(self.parse(body)["status"], "incomplete_unqualified")

    def test_v2_total_row_budget_applies_before_universe_exclusion(self):
        body = payload()
        body["data"]["items"] = [[f"{600000+i}.SH", "20250102", 1] for i in range(5999)]
        body["data"]["items"].append(["920163.BJ", "20250102", 1])
        result = self.parse(body)
        self.assertTrue(result["row_limit_reached"])
        self.assertEqual(result["status"], "incomplete_unqualified")
        body["data"]["items"].append(["920164.BJ", "20250102", 1])
        with self.assertRaises(ValueError):
            self.parse(body)

    def test_new_capture_writes_consistent_v2_packet_claim_and_record(self):
        result = self.fixture.capture(mixed())
        self.assertEqual(result["status"], "observed_unqualified")
        claim = json.loads(self.fixture.packets[0].with_name("claim.json").read_bytes())
        record = json.loads(self.fixture.record_path(self.fixture.packets[0]).read_bytes())
        self.assertEqual([x["receipt_schema_version"] for x in [result, claim, record]], [2, 2, 2])
        self.assertEqual(record["excluded_bj_source_rows"], 1)
        self.assertEqual(len(self.fixture.session.calls), 1)

    def test_v2_reader_projects_only_requested_sh_sz_stocks(self):
        self.fixture.capture(mixed())
        result = self.fixture.review()
        self.assertTrue(result["source_selection_complete"])
        self.assertEqual(result["observed_numeric_cells"], 2)
        self.assertEqual({c["symbol"] for c in result["cells"]}, {"600584.SH", "000063.SZ"})
        self.assertFalse(result["research_admission_granted"])
        manifest = self.fixture.manifest(); manifest["symbols"] = ["920163.BJ"]
        with self.assertRaises(ValueError):
            self.fixture.review(manifest)

    def test_legacy_accepted_and_rejected_receipts_keep_their_version(self):
        self.legacy_capture(payload())
        self.assertTrue(self.fixture.review()["source_selection_complete"])
        self.fixture.now += timedelta(days=1)
        result = self.legacy_capture(mixed("20250103"))
        self.assertEqual(result["status"], "source_review_required")
        manifest = self.fixture.manifest(as_of="2025-01-03T11:15:00+00:00")
        manifest["trade_dates"] = ["20250103"]
        reviewed = self.fixture.review(manifest)
        self.assertEqual(reviewed["observed_numeric_cells"], 0)
        self.assertEqual(reviewed["failed_visible_requests"], 1)

    def test_v2_revision_can_link_to_valid_v1_original(self):
        self.legacy_capture(payload())
        self.fixture.now += timedelta(days=1)
        result = self.fixture.capture(mixed("20250103"), mixed(value=21))
        self.assertEqual(result["requests_started"], 2)
        reviewed = self.fixture.review(self.fixture.manifest(as_of="2025-01-03T11:15:00+00:00"))
        self.assertTrue(reviewed["source_selection_complete"])
        self.assertEqual(Decimal(self.fixture.value(reviewed)["net_mf_amount"]), Decimal(21))

    def test_mixed_record_and_packet_versions_rejected(self):
        self.fixture.capture(payload())
        self.fixture.rewrite_record(self.fixture.packets[0], "current", lambda r: r.update(receipt_schema_version=1))
        with self.assertRaises(ValueError):
            self.fixture.review()

    def test_v2_never_retries_or_relabels_existing_rejected_v1_day(self):
        self.legacy_capture(mixed())
        path = self.fixture.packets[0]
        original = path.read_bytes()
        result = self.fixture.capture()
        self.assertEqual(result["status"], "already_attempted")
        self.assertEqual(result["receipt_schema_version"], 1)
        self.assertEqual(result["previous_status"], "source_review_required")
        self.assertEqual(path.read_bytes(), original)
        self.assertEqual(len(self.fixture.session.calls), 1)

    def test_malformed_previous_packet_does_not_prevent_current_capture(self):
        self.fixture.capture(payload())
        self.fixture.packets[0].write_text('[]', encoding="utf-8")
        self.fixture.now += timedelta(days=1)
        result = self.fixture.capture(mixed("20250103"))
        self.assertEqual(result["requests_started"], 1)
        self.assertEqual(result["prior_review_status"], "archive_integrity_failed")
        self.assertEqual(result["status"], "source_review_required")
        self.assertEqual(len(self.fixture.session.calls), 2)

    def test_unsupported_or_boolean_parser_versions_rejected(self):
        for version in [0, 3, True, "2"]:
            with self.subTest(version=version), self.assertRaises(ValueError):
                collector.parse_moneyflow_payload(payload(), trade_date="20250102", receipt_schema_version=version)


if __name__ == "__main__":
    unittest.main()
