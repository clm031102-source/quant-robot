from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.data import moneyflow_receipt_asof as reader
from quant_robot.data.sources import tushare_moneyflow_observation as collector
from tests.unit.test_tushare_moneyflow_observation import Response, Session, TOKEN, payload


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class MoneyflowReceiptAsOfTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.now = datetime(2025, 1, 2, 11, 10, tzinfo=timezone.utc)
        self.session = Session([])
        self.packets = []

    def capture(self, *responses):
        self.session.responses.extend(Response(p) if not isinstance(p, BaseException) else p for p in responses)
        with patch.object(collector, "_utc_now", return_value=self.now), \
                patch.object(collector, "_new_session", return_value=self.session):
            result = collector.capture_moneyflow_observation(repo_root=self.root, execute=True,
                run_gate=lambda _: {"status": "ready", "primary_market": "CN_ETF", "blockers": []},
                get_token=lambda: TOKEN)
        self.packets.append(Path(result["result_path"]))
        return result

    def manifest(self, as_of="2025-01-02T11:15:00+00:00", packets=None):
        return {"schema_version": 1, "purpose": "moneyflow_asof_source_review", "as_of": as_of,
                "trade_dates": ["20250102"], "symbols": ["600584.SH", "000063.SZ"],
                "receipts": [{"path": str(p.relative_to(self.root)), "sha256": sha(p)}
                             for p in (self.packets if packets is None else packets)]}

    def review(self, manifest=None):
        return reader.read_moneyflow_asof(manifest or self.manifest(), repo_root=self.root)

    def value(self, result, symbol="600584.SH"):
        return next(c for c in result["cells"] if c["symbol"] == symbol)

    def record_path(self, packet, kind="current"):
        d = json.loads(packet.read_bytes())
        return Path(next(r["record_path"] for r in d["records"] if r["kind"] == kind))

    def rewrite_record(self, packet, kind, change):
        d = json.loads(packet.read_bytes()); p = self.record_path(packet, kind)
        r = json.loads(p.read_bytes()); change(r); p.write_text(json.dumps(r), encoding="utf-8")
        next(e for e in d["records"] if e["kind"] == kind)["record_sha256"] = sha(p)
        packet.write_text(json.dumps(d), encoding="utf-8")

    def test_visible_values_keep_units_and_no_admission(self):
        self.capture(payload(value=0.0))
        result = self.review()
        self.assertEqual(Decimal(self.value(result)["net_mf_amount"]), Decimal(0))
        self.assertEqual(self.value(result)["state"], "observed_numeric")
        self.assertEqual(result["amount_unit"], "CNY_10000")
        self.assertFalse(result["research_admission_granted"])
        self.assertFalse(result["historical_vintage_verified"])
        self.assertEqual(result["observed_numeric_cells"], 2)

    def test_before_receipt_is_unknown_and_future_body_is_never_opened(self):
        self.capture(payload())
        original_read = reader._read
        def guarded(path, limit):
            self.assertFalse(str(path).endswith(".response.json"), "future values were read")
            return original_read(path, limit)
        with patch.object(reader, "_read", side_effect=guarded):
            result = self.review(self.manifest("2025-01-02T11:09:59+00:00"))
        self.assertIsNone(self.value(result)["net_mf_amount"])
        self.assertEqual(self.value(result)["state"], "no_visible_version")

    def test_later_correction_never_changes_earlier_cutoff(self):
        self.capture(payload(value=10))
        self.now += timedelta(days=1)
        self.capture(payload("20250103"), payload(value=20))
        old = self.review()
        later = self.review(self.manifest("2025-01-03T11:15:00+00:00"))
        self.assertEqual(Decimal(self.value(old)["net_mf_amount"]), Decimal(10))
        self.assertEqual(Decimal(self.value(later)["net_mf_amount"]), Decimal(20))

    def test_empty_and_null_late_arrival_do_not_fill_earlier_missing_state(self):
        p = payload(value=None)
        self.capture(p)
        self.now += timedelta(days=1)
        self.capture(payload("20250103"), payload(value=12))
        self.assertEqual(self.value(self.review())["state"], "explicit_null")
        self.assertIsNone(self.value(self.review())["net_mf_amount"])
        self.assertEqual(self.value(self.review(self.manifest("2025-01-03T11:15:00+00:00")))["state"], "observed_numeric")

    def test_latest_whole_response_does_not_stitch_old_values_for_omitted_stock(self):
        self.capture(payload(value=10))
        self.now += timedelta(days=1)
        partial = payload(value=20); partial["data"]["items"] = partial["data"]["items"][:1]
        self.capture(payload("20250103"), partial)
        result = self.review(self.manifest("2025-01-03T11:15:00+00:00"))
        self.assertEqual(self.value(result, "000063.SZ")["state"], "absent_from_response")
        self.assertIsNone(self.value(result, "000063.SZ")["net_mf_amount"])

    def test_new_empty_version_supersedes_prior_numeric_response(self):
        self.capture(payload(value=10))
        self.now += timedelta(days=1)
        empty = payload(); empty["data"]["items"] = []
        self.capture(payload("20250103"), empty)
        result = self.review(self.manifest("2025-01-03T11:15:00+00:00"))
        self.assertEqual(result["observed_numeric_cells"], 0)
        self.assertEqual(self.value(result)["state"], "absent_from_response")

    def test_failed_check_retains_last_known_version_with_explicit_failure(self):
        self.capture(payload(value=10))
        self.now += timedelta(days=1)
        self.capture(payload("20250103"), RuntimeError("synthetic failure"))
        result = self.review(self.manifest("2025-01-03T11:15:00+00:00"))
        self.assertEqual(Decimal(self.value(result)["net_mf_amount"]), Decimal(10))
        self.assertEqual(result["failed_visible_requests"], 1)

    def test_missing_original_revision_link_is_rejected_without_implicit_discovery(self):
        self.capture(payload())
        self.now += timedelta(days=1)
        self.capture(payload("20250103"), payload(value=99))
        with self.assertRaises(ValueError):
            self.review(self.manifest("2025-01-03T11:15:00+00:00", packets=[self.packets[1]]))

    def test_future_tampered_body_does_not_pollute_old_cutoff_but_later_fails(self):
        self.capture(payload())
        self.now += timedelta(days=1)
        self.capture(payload("20250103"), payload(value=99))
        r = json.loads(self.record_path(self.packets[1], "revision").read_bytes())
        Path(r["raw_path"]).write_bytes(b"tampered future body")
        self.assertEqual(Decimal(self.value(self.review())["net_mf_amount"]), Decimal("12.5"))
        with self.assertRaises(ValueError):
            self.review(self.manifest("2025-01-03T11:15:00+00:00"))

    def test_tampered_claim_record_body_and_packet_are_rejected(self):
        self.capture(payload())
        manifest = self.manifest()
        folder = self.packets[0].parent
        for name in ["claim.json", "current.json", "current.response.json", "completion.json"]:
            p = folder / name; saved = p.read_bytes(); p.write_bytes(saved + b" ")
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.review(manifest)
            p.write_bytes(saved)

    def test_bad_timezone_scope_and_unsupported_receipt_version_rejected(self):
        self.capture(payload())
        for change in [lambda m: m.update(as_of="2025-01-02T11:15:00"),
                       lambda m: m["symbols"].append("600584.SH"),
                       lambda m: m.update(symbols=["510300.SH"]),
                       lambda m: m["receipts"].append(m["receipts"][0]),
                       lambda m: m.update(trade_dates=["20250103"]),
                       lambda m: m.update(purpose="factor_generation")]:
            m = self.manifest(); change(m)
            with self.assertRaises(ValueError):
                self.review(m)
        d = json.loads(self.packets[0].read_bytes()); d["receipt_schema_version"] = 2
        self.packets[0].write_text(json.dumps(d), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.review()

    def test_record_completion_clock_must_follow_receipt_and_precede_packet(self):
        self.capture(payload())
        self.rewrite_record(self.packets[0], "current", lambda r: r.update(finished_at="2025-01-02T11:09:59+00:00"))
        with self.assertRaises(ValueError):
            self.review()

    def test_recomputed_source_summary_must_match_recorded_digest(self):
        self.capture(payload())
        self.rewrite_record(self.packets[0], "current", lambda r: r.update(content_sha256="0" * 64))
        with self.assertRaises(ValueError):
            self.review()

    def test_archive_scope_rejects_paths_outside_fixed_source_directory(self):
        self.capture(payload())
        alternate = self.root / "copied.json"; alternate.write_bytes(self.packets[0].read_bytes())
        m = self.manifest(packets=[alternate])
        with self.assertRaises(ValueError):
            self.review(m)

    def same_clock_versions(self, revised_value):
        self.capture(payload(value=10))
        self.now += timedelta(days=1)
        instant = self.now.isoformat()
        self.rewrite_record(self.packets[0], "current", lambda r: r.update(observed_at=instant, finished_at=instant))
        packet = json.loads(self.packets[0].read_bytes()); packet["finished_at"] = instant
        self.packets[0].write_text(json.dumps(packet), encoding="utf-8")
        self.capture(payload("20250103"), payload(value=revised_value))
        return self.review(self.manifest("2025-01-03T11:15:00+00:00"))

    def test_conflicting_same_receipt_clock_remains_unknown(self):
        result = self.same_clock_versions(20)
        self.assertEqual(self.value(result)["state"], "conflicting_receipt_time")
        self.assertIsNone(self.value(result)["net_mf_amount"])

    def test_equivalent_same_receipt_clock_keeps_evidence_for_both(self):
        result = self.same_clock_versions(10.0)
        self.assertEqual(Decimal(self.value(result)["net_mf_amount"]), Decimal(10))
        self.assertEqual(result["selected_versions"][0]["equivalent_latest_receipts"], 2)

    def test_page_incompleteness_cannot_be_hidden_by_present_requested_symbols(self):
        p = payload(); p["data"]["has_more"] = True
        self.capture(p)
        result = self.review()
        self.assertEqual(result["observed_numeric_cells"], 2)
        self.assertFalse(result["source_selection_complete"])
        self.assertIn("source_response_incomplete", result["source_review_blockers"])

    def test_failed_check_is_not_reported_as_complete_source_selection(self):
        self.capture(payload())
        self.now += timedelta(days=1)
        self.capture(payload("20250103"), RuntimeError("synthetic failure"))
        result = self.review(self.manifest("2025-01-03T11:15:00+00:00"))
        self.assertEqual(result["observed_numeric_cells"], 2)
        self.assertFalse(result["source_selection_complete"])
        self.assertIn("visible_source_request_failed", result["source_review_blockers"])

    def test_revision_claim_fingerprint_is_part_of_source_chain(self):
        self.capture(payload())
        self.now += timedelta(days=1)
        self.capture(payload("20250103"), payload(value=20))
        r = json.loads(self.record_path(self.packets[1], "revision").read_bytes())
        p = Path(r["revision_claim_path"]); p.write_bytes(p.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            self.review(self.manifest("2025-01-03T11:15:00+00:00"))

    def test_same_clock_conflicting_completeness_is_not_silently_resolved(self):
        p = payload(value=10); p["data"]["has_more"] = True
        self.capture(p)
        self.now += timedelta(days=1)
        instant = self.now.isoformat()
        self.rewrite_record(self.packets[0], "current", lambda r: r.update(observed_at=instant, finished_at=instant))
        packet = json.loads(self.packets[0].read_bytes()); packet["finished_at"] = instant
        self.packets[0].write_text(json.dumps(packet), encoding="utf-8")
        self.capture(payload("20250103"), payload(value=10))
        result = self.review(self.manifest("2025-01-03T11:15:00+00:00"))
        self.assertFalse(result["source_selection_complete"])
        self.assertEqual(self.value(result)["state"], "conflicting_receipt_time")

    def test_packet_with_unaccounted_request_cannot_hide_a_missing_revision_receipt(self):
        self.capture(payload())
        self.now += timedelta(days=1)
        self.capture(payload("20250103"), payload(value=20))
        packet = json.loads(self.packets[1].read_bytes())
        packet["records"] = [e for e in packet["records"] if e["kind"] == "current"]
        self.packets[1].write_text(json.dumps(packet), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.review(self.manifest("2025-01-03T11:15:00+00:00"))


if __name__ == "__main__":
    unittest.main()
