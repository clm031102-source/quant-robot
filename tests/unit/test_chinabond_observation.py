"""Synthetic public-page observations; no network or market outcomes."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.data.sources import chinabond_observation as subject


def page(day="2025-01-02", government="1.20", credit="1.80"):
    names = ["ChinaBond Government Bond Yield Curve",
             "ChinaBond Financial Bond of Commercial Bank Yield Curve (AAA)",
             "ChinaBond CP&Note Yield Curve (AAA)"]
    head = f"<th>{day}(%)</th>" + "".join(
        f"<th>{x}</th>" for x in ["3月", "6月", "1年", "3年", "5年", "7年", "10年", "30年"])
    rows = [f"<tr>{head}</tr>"]
    for name, value in zip(names, [government, "1.50", credit]):
        cells = [name, "1", "1", value, "1", "1", "1", "1", ""]
        rows.append("<tr>" + "".join(f"<td>{x}</td>" for x in cells) + "</tr>")
    return ("<html><div id='gjqxData'><table>" + "".join(rows)
            + "</table></div></html>").encode()


class Response:
    status_code = 200
    headers = {"Date": "Thu, 02 Jan 2025 10:10:00 GMT"}

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, size):
        yield self.body


class Session:
    def __init__(self, body):
        self.response = Response(body)
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class ChinaBondObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2025, 1, 2, 10, 10, tzinfo=timezone.utc)
        self.session = Session(page())

    def capture(self, *, execute=True, gate=None):
        with patch.object(subject, "_utc_now", return_value=self.now), \
                patch.object(subject, "_new_session", return_value=self.session):
            return subject.capture_current_observation(
                repo_root=self.root, execute=execute,
                run_gate=gate or (lambda path: {"status": "ready", "blockers": [],
                                               "primary_market": "CN_ETF"}))

    def test_current_capture_keeps_source_clock_raw_and_two_unqualified_values(self):
        result = self.capture()
        self.assertEqual(result["status"], "observed_unqualified")
        record = json.loads(Path(result["record_path"]).read_text())
        self.assertEqual(record["observation_date"], "2025-01-02")
        self.assertEqual(record["observed_at"], self.now.isoformat())
        self.assertIsNone(record["source_published_at"])
        self.assertEqual(record["yields_percent"], {"government": "1.20", "aaa_cp_note": "1.80"})
        self.assertFalse(record["research_admission_granted"])
        self.assertFalse(record["historical_vintage_verified"])
        self.assertEqual(Path(result["raw_path"]).read_bytes(), page())
        self.assertEqual(self.session.calls[0][0], subject.SOURCE_URL)
        self.assertFalse(self.session.calls[0][1]["allow_redirects"])
        self.assertFalse(self.session.trust_env)

    def test_preview_and_early_day_do_not_touch_gate_network_or_archive(self):
        for preview, hour in [(True, 10), (False, 1)]:
            with self.subTest(preview=preview):
                self.now = self.now.replace(hour=hour)
                with patch.object(subject, "_new_session") as network:
                    result = self.capture(execute=not preview,
                        gate=lambda path: self.fail("gate must not run"))
                self.assertIn(result["status"], {"preview", "not_due"})
                self.assertEqual(self.session.calls, [])
                self.assertFalse((self.root / "data").exists())

    def test_gate_rejection_prevents_request_and_daily_claim(self):
        result = self.capture(gate=lambda path: {"status": "ready", "blockers": ["blocked"],
                                               "primary_market": "CN_ETF"})
        self.assertEqual(result["status"], "gate_blocked")
        self.assertFalse(self.session.calls)
        self.assertFalse(list(self.root.rglob("claim.json")))

    def test_second_run_cannot_redownload_or_overwrite_first_record(self):
        first = self.capture()
        before = Path(first["record_path"]).read_bytes()
        self.session.response.body = page(credit="9.99")
        second = self.capture()
        self.assertEqual(second["status"], "already_attempted")
        self.assertEqual(len(self.session.calls), 1)
        self.assertEqual(Path(first["record_path"]).read_bytes(), before)

    def test_stale_observation_and_later_changed_value_remain_separate_versions(self):
        first = self.capture()
        self.now = self.now.replace(day=3)
        self.session.response.body = page(credit="1.90")
        second = self.capture()
        self.assertEqual(second["status"], "stale_observation_unqualified")
        a = json.loads(Path(first["record_path"]).read_text())
        b = json.loads(Path(second["record_path"]).read_text())
        self.assertEqual(a["yields_percent"]["aaa_cp_note"], "1.80")
        self.assertEqual(b["yields_percent"]["aaa_cp_note"], "1.90")
        self.assertLess(a["observed_at"], b["observed_at"])
        self.assertNotEqual(a["raw_sha256"], b["raw_sha256"])

    def test_malformed_or_future_source_retained_without_admission_or_retry(self):
        variations = [page(credit=""), page(credit="NaN"), page(day="2025-01-03"),
                      page().replace(b"1\xe5\xb9\xb4", b"2\xe5\xb9\xb4"),
                      page() + page(), page().replace(b"AAA)", b"AA+)")]
        for body in variations:
            with self.subTest(body=body[:30]), tempfile.TemporaryDirectory() as temp:
                self.root = Path(temp)
                self.session = Session(body)
                result = self.capture()
                self.assertEqual(result["status"], "source_rejected")
                self.assertFalse(result["research_admission_granted"])
                self.assertEqual(Path(result["raw_path"]).read_bytes(), body)
                self.assertEqual(self.capture()["status"], "already_attempted")
                self.assertEqual(len(self.session.calls), 1)

    def test_oversize_and_http_failure_consume_attempt_without_source_success(self):
        for code, body in [(302, b"redirect"), (503, b"failed"), (200, b"x" * 1_000_001)]:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as temp:
                self.root = Path(temp)
                self.session = Session(body)
                self.session.response.status_code = code
                result = self.capture()
                self.assertEqual(result["status"], "source_rejected")
                self.assertEqual(self.capture()["status"], "already_attempted")
                self.assertEqual(len(self.session.calls), 1)

    def test_interrupted_claim_does_not_turn_into_an_implicit_retry(self):
        first = self.capture()
        Path(first["record_path"]).unlink()
        result = self.capture()
        self.assertEqual(result["status"], "attempt_incomplete")
        self.assertEqual(len(self.session.calls), 1)

    def test_changed_archived_body_requires_review_without_new_request(self):
        first = self.capture()
        Path(first["raw_path"]).write_bytes(page(credit="9.99"))
        self.assertEqual(self.capture()["status"], "archive_integrity_failed")
        self.assertEqual(len(self.session.calls), 1)

    def test_negative_yield_is_preserved_in_percent_units(self):
        self.session.response.body = page(government="-0.25")
        result = self.capture()
        record = json.loads(Path(result["record_path"]).read_text())
        self.assertEqual(record["yields_percent"]["government"], "-0.25")


if __name__ == "__main__":
    unittest.main()
