"""Offline source receipts and revision checks, without ETF outcomes."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.data.sources import tushare_moneyflow_observation as subject


TOKEN = "synthetic-secret-for-offline-test"


def payload(day="20250102", value=12.5):
    return {"code": 0, "msg": None, "data": {"fields": subject.FIELDS,
            "items": [["600584.SH", day, value], ["000063.SZ", day, -2.0]]}}


class Response:
    def __init__(self, body, status=200):
        self.body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.status_code = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, chunk_size):
        yield self.body


class Session:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


class MoneyflowObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2025, 1, 2, 11, 10, tzinfo=timezone.utc)
        self.session = Session([Response(payload())])

    def capture(self, execute=True, gate=None, get_token=None):
        with patch.object(subject, "_utc_now", return_value=self.now), \
                patch.object(subject, "_new_session", return_value=self.session):
            return subject.capture_moneyflow_observation(repo_root=self.root, execute=execute,
                run_gate=gate or (lambda _: {"status": "ready", "primary_market": "CN_ETF", "blockers": []}),
                get_token=get_token or (lambda: TOKEN))

    def record(self, result, kind="current"):
        entry = next(r for r in result["records"] if r["kind"] == kind)
        return json.loads(Path(entry["record_path"]).read_text())

    def test_first_receipt_keeps_entity_body_and_actual_clock_without_admission(self):
        result = self.capture()
        self.assertEqual(result["status"], "observed_unqualified")
        record = self.record(result)
        self.assertEqual(record["observed_at"], self.now.isoformat())
        self.assertIsNone(record["source_published_at"])
        self.assertEqual(record["trade_date"], "20250102")
        self.assertEqual(record["rows"], 2)
        self.assertFalse(record["research_admission_granted"])
        self.assertFalse(record["universe_coverage_verified"])
        self.assertEqual(Path(record["raw_path"]).read_bytes(), Response(payload()).body)
        url, call = self.session.calls[0]
        self.assertEqual(url, subject.SOURCE_URL)
        self.assertEqual(call["json"]["api_name"], "moneyflow")
        self.assertEqual(call["json"]["params"], {"trade_date": "20250102"})
        self.assertFalse(call["allow_redirects"])
        self.assertTrue(call["verify"])
        self.assertFalse(self.session.trust_env)
        for path in self.root.rglob("*.json"):
            self.assertNotIn(TOKEN, path.read_text())

    def test_preview_early_weekend_and_naive_clock_never_request_or_read_token(self):
        for execute, instant in [(False, self.now), (True, self.now.replace(hour=10)),
                                  (True, self.now.replace(day=4))]:
            self.now = instant
            result = self.capture(execute=execute, get_token=lambda: self.fail("token read"),
                                  gate=lambda _: self.fail("gate called"))
            self.assertIn(result["status"], {"preview", "not_due"})
        self.now = self.now.replace(tzinfo=None)
        with self.assertRaises(ValueError):
            self.capture()
        self.assertFalse(self.session.calls)
        self.assertFalse(list(self.root.iterdir()))

    def test_gate_failure_and_missing_credential_never_request(self):
        result = self.capture(gate=lambda _: {"status": "blocked", "primary_market": "CN_ETF", "blockers": ["x"]})
        self.assertEqual(result["status"], "gate_blocked")
        self.assertFalse(self.session.calls)
        self.now += timedelta(days=1)
        result = self.capture(get_token=lambda: "")
        self.assertEqual(result["status"], "credential_missing")
        self.assertFalse(self.session.calls)

    def test_same_day_attempt_is_immutable_and_interruption_is_not_retry(self):
        first = self.capture()
        before = {p: p.read_bytes() for p in self.root.rglob("*.json")}
        self.assertEqual(self.capture()["status"], "already_attempted")
        self.assertEqual(len(self.session.calls), 1)
        for p, raw in before.items():
            self.assertEqual(p.read_bytes(), raw)
        Path(first["result_path"]).unlink()
        self.assertEqual(self.capture()["status"], "attempt_incomplete")
        self.assertEqual(len(self.session.calls), 1)

    def test_changed_value_is_later_version_and_original_is_unchanged(self):
        first = self.capture()
        original = self.record(first)
        original_bytes = Path(original["raw_path"]).read_bytes()
        self.now += timedelta(days=1)
        self.session.responses.extend([Response(payload("20250103")), Response(payload(value=99.0))])
        second = self.capture()
        revision = self.record(second, "revision")
        self.assertEqual(len(self.session.calls), 3)
        self.assertTrue(revision["content_changed_since_original"])
        self.assertEqual(revision["original_raw_sha256"], original["raw_sha256"])
        self.assertGreater(revision["observed_at"], original["observed_at"])
        self.assertEqual(Path(original["raw_path"]).read_bytes(), original_bytes)
        self.assertFalse(revision["historical_vintage_verified"])
        self.assertEqual(self.capture()["status"], "already_attempted")

    def test_field_order_change_does_not_count_as_value_revision(self):
        self.capture()
        self.now += timedelta(days=1)
        changed = payload()
        changed["data"]["fields"] = list(reversed(subject.FIELDS))
        changed["data"]["items"] = [list(reversed(r)) for r in changed["data"]["items"]]
        self.session.responses.extend([Response(payload("20250103")), Response(changed)])
        revision = self.record(self.capture(), "revision")
        self.assertFalse(revision["content_changed_since_original"])
        self.assertNotEqual(revision["raw_sha256"], revision["original_raw_sha256"])

    def test_failed_revision_is_consumed_once_and_cannot_rewrite_original(self):
        first = self.capture()
        original_hash = self.record(first)["raw_sha256"]
        self.now += timedelta(days=1)
        self.session.responses.extend([Response(payload("20250103")), RuntimeError(TOKEN)])
        second = self.capture()
        self.assertEqual(second["status"], "source_review_required")
        self.assertEqual(self.record(second, "revision")["status"], "source_rejected")
        self.now += timedelta(days=3)
        self.session.responses.extend([Response(payload("20250106")), Response(payload("20250103"))])
        third = self.capture()
        self.assertEqual(self.record(third, "revision")["trade_date"], "20250103")
        self.assertEqual(self.record(first)["raw_sha256"], original_hash)

    def test_tampered_prior_body_blocks_recheck_but_not_new_day_source_capture(self):
        first = self.capture()
        Path(self.record(first)["raw_path"]).write_bytes(b"changed")
        self.assertEqual(self.capture()["status"], "archive_integrity_failed")
        self.now += timedelta(days=1)
        self.session.responses.append(Response(payload("20250103")))
        second = self.capture()
        self.assertEqual(len(self.session.calls), 2)
        self.assertEqual(second["prior_review_status"], "archive_integrity_failed")
        self.assertEqual([r["kind"] for r in second["records"]], ["current"])

    def test_no_history_backfill_after_seven_day_gap(self):
        self.capture()
        self.now += timedelta(days=8)
        self.session.responses.append(Response(payload("20250110")))
        second = self.capture()
        self.assertEqual(len(self.session.calls), 2)
        self.assertEqual([r["kind"] for r in second["records"]], ["current"])

    def test_empty_null_and_page_limit_are_unqualified_not_zero_or_complete(self):
        variants = []
        empty = payload(); empty["data"]["items"] = []; variants.append(empty)
        null = payload(value=None); variants.append(null)
        page = payload(); page["data"]["has_more"] = True; variants.append(page)
        for body in variants:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temp:
                self.root = Path(temp); self.session = Session([Response(body)])
                result = self.capture()
                self.assertEqual(result["status"], "source_review_required")
                record = self.record(result)
                self.assertFalse(record["universe_coverage_verified"])
                self.assertEqual(Path(record["raw_path"]).read_bytes(), Response(body).body)
                self.assertEqual(self.capture()["status"], "already_attempted")

    def test_scope_and_numeric_identity_errors_preserve_safe_body_and_stop(self):
        wrong_day = payload("20250101")
        duplicate = payload(); duplicate["data"]["items"].append(duplicate["data"]["items"][0])
        wrong_asset = payload(); wrong_asset["data"]["items"][0][0] = "510300.SH"
        boolean = payload(value=True)
        for body in [wrong_day, duplicate, wrong_asset, boolean]:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temp:
                self.root = Path(temp); self.session = Session([Response(body)])
                result = self.capture()
                record = self.record(result)
                self.assertEqual(record["status"], "source_rejected")
                self.assertEqual(Path(record["raw_path"]).read_bytes(), Response(body).body)
                self.assertEqual(len(self.session.calls), 1)

    def test_secret_echo_invalid_json_http_oversize_and_timeout_never_leak_or_retry(self):
        echo = payload(); echo["msg"] = TOKEN
        escaped = json.dumps(echo).replace(TOKEN, "".join("\\u%04x" % ord(c) for c in TOKEN)).encode()
        responses = [Response(echo), Response(escaped), Response(b"not JSON " + TOKEN.encode()),
                     Response(b"redirect", 302), Response(b"x" * (subject.MAX_BYTES + 1)), RuntimeError(TOKEN)]
        for response in responses:
            with self.subTest(response=type(response)), tempfile.TemporaryDirectory() as temp:
                self.root = Path(temp); self.session = Session([response])
                result = self.capture()
                self.assertEqual(result["status"], "source_review_required")
                self.assertEqual(self.capture()["status"], "already_attempted")
                self.assertEqual(len(self.session.calls), 1)
                self.assertFalse(list(self.root.rglob("*.response.json")))
                for p in self.root.rglob("*.json"):
                    self.assertNotIn(TOKEN, p.read_text())

    def test_payload_parser_rejects_limit_count_mismatch_and_nonfinite(self):
        for edit in [lambda d: d["data"].update(count=3), lambda d: d["data"].update(count=True),
                     lambda d: d["data"]["items"][0].__setitem__(2, float("inf"))]:
            p = payload(); edit(p)
            with self.assertRaises(ValueError):
                subject.parse_moneyflow_payload(p, trade_date="20250102")

    def test_exact_decimal_revision_is_not_lost_in_binary_float_rounding(self):
        self.session = Session([Response(Response(payload()).body.replace(b"12.5", b"12.0000000000000000"))])
        self.capture()
        self.now += timedelta(days=1)
        changed = Response(payload()).body.replace(b"12.5", b"12.0000000000000001")
        self.session.responses.extend([Response(payload("20250103")), Response(changed)])
        self.assertTrue(self.record(self.capture(), "revision")["content_changed_since_original"])

    def test_equivalent_numeric_spelling_is_not_a_value_revision(self):
        self.session = Session([Response(payload(value=12))])
        self.capture()
        self.now += timedelta(days=1)
        self.session.responses.extend([Response(payload("20250103")), Response(payload(value=12.0))])
        self.assertFalse(self.record(self.capture(), "revision")["content_changed_since_original"])

    def test_exact_provider_row_limit_remains_incomplete(self):
        p = payload()
        p["data"]["items"] = [[f"{600000 + i}.SH", "20250102", 1.0] for i in range(6000)]
        self.session = Session([Response(p)])
        result = self.capture()
        self.assertEqual(result["status"], "source_review_required")
        self.assertTrue(self.record(result)["row_limit_reached"])

    def test_backwards_receipt_clock_consumes_attempt_without_archiving_body(self):
        times = [self.now, self.now + timedelta(seconds=1), self.now,
                 self.now + timedelta(seconds=2), self.now + timedelta(seconds=3)]
        with patch.object(subject, "_utc_now", side_effect=times), \
                patch.object(subject, "_new_session", return_value=self.session):
            result = subject.capture_moneyflow_observation(repo_root=self.root, execute=True,
                run_gate=lambda _: {"status": "ready", "primary_market": "CN_ETF", "blockers": []},
                get_token=lambda: TOKEN)
        self.assertEqual(result["status"], "source_review_required")
        self.assertFalse(self.record(result)["raw_retained"])
        self.assertEqual(len(self.session.calls), 1)

    def test_late_arrival_after_empty_or_null_receipt_is_a_new_version_not_backfill(self):
        for first_payload in [payload(value=None), {"code": 0, "data": {"fields": subject.FIELDS, "items": []}}]:
            with self.subTest(initial=first_payload), tempfile.TemporaryDirectory() as temp:
                self.root = Path(temp)
                self.now = datetime(2025, 1, 2, 11, 10, tzinfo=timezone.utc)
                self.session = Session([Response(first_payload)])
                first = self.capture()
                original = self.record(first)
                self.assertEqual(original["status"], "incomplete_unqualified")
                before = Path(first["result_path"]).read_bytes()
                self.now += timedelta(days=1)
                self.session.responses.extend([Response(payload("20250103")), Response(payload())])
                revision = self.record(self.capture(), "revision")
                self.assertTrue(revision["content_changed_since_original"])
                self.assertGreater(revision["observed_at"], original["observed_at"])
                self.assertEqual(Path(first["result_path"]).read_bytes(), before)
                self.assertEqual(self.record(first)["status"], "incomplete_unqualified")


if __name__ == "__main__":
    unittest.main()
