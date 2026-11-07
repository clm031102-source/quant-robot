"""Artificial HTTP objects/processes only; no credentials or external requests."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import http.client
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from quant_robot.ops import tushare_fund_daily_batch as B
from quant_robot.ops import tushare_fund_daily_wire as W
try:
    from .test_tushare_fund_daily_wire import artificial_manifest, body
except ImportError:  # Direct unit-directory discovery.
    from test_tushare_fund_daily_wire import artificial_manifest, body


TOKEN = "ARTIFICIAL_CREDENTIAL_NOT_REAL"


def report(raw, *, error=None, status=200):
    return {"body": raw, "error": error, "body_complete": True,
            "received_bytes": len(raw), "received_bytes_lower_bound": len(raw),
            "attempts_started": 1, "attempts_started_lower_bound": 1,
            "worker_exit_confirmed": True, "http_status": status, "headers": {},
            "request_started_at": B._now(), "headers_received_at": B._now(),
            "body_completed_at": B._now(), "failed_at": None}


def slow_worker(connection, request, token):
    connection.send({"event": "start", "at": B._now()})
    connection.send({"event": "bytes", "count": 17})
    time.sleep(10)


def artificial_worker(connection, request, token):
    connection.send({"event": "start", "at": B._now()})
    connection.send({"event": "bytes", "count": 2})
    connection.send({"result": report(b"{}")})
    connection.close()


class FakeResponse:
    def __init__(self, raw=b"{}", *, length=True, status=200, headers=None, partial=None):
        self.raw, self.offset, self.status = raw, 0, status
        self.length = len(raw) if length else None
        self.headers = headers or [("Content-Type", "application/json")]
        self.read_sizes, self.partial = [], partial

    def getheaders(self):
        return self.headers

    def read1(self, size):
        self.read_sizes.append(size)
        if self.partial is not None:
            raise http.client.IncompleteRead(self.partial, 10)
        value = self.raw[self.offset:self.offset+size]
        self.offset += len(value)
        if self.length is not None:
            self.length -= len(value)
        return value


class FakeConnection:
    def __init__(self, response):
        self.response, self.calls, self.closed = response, [], False

    def request(self, *args, **kwargs):
        self.calls.append((args, kwargs))

    def getresponse(self):
        return self.response

    def close(self):
        self.closed = True


class BatchCaptureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest, self.sessions = artificial_manifest()
        self.calls, self.token_reads = [], 0

    def token(self):
        self.token_reads += 1
        return TOKEN

    def transport(self, request, token, seconds):
        self.calls.append(request["id"])
        self.assertEqual(token, TOKEN)
        self.assertLessEqual(seconds, 40)
        return report(body(request["expected_trade_dates"], symbol=request["params"]["ts_code"]))

    def run_artificial(self, transport=None, refs=()):
        return B.capture_synthetic(self.manifest, self.sessions, self.root/"capture",
                                   transport=transport or self.transport, token_loader=self.token, bound_refs=refs)

    def test_save_anchors_supplied_bytes_and_detects_pre_verification_mutation(self):
        original_bound = B._bound
        path = self.root/'saved.raw'
        def altered(ref):
            Path(ref['path']).write_bytes(b'evil')
            return original_bound(ref)
        with patch.object(B, '_bound', altered), self.assertRaisesRegex(B.BatchError, 'bound_artifact_changed'):
            B._save(path, b'good', raw=True)
        good = B._save(self.root/'unchanged.raw', b'good', raw=True)
        self.assertEqual(good['sha256'], sha256(b'good').hexdigest())

    def test_complete_24_once_source_roles_and_opaque_originals(self):
        outcome = self.run_artificial()
        self.assertEqual(outcome["status"], "completed_structure_only")
        self.assertEqual(outcome["HTTP_attempts_started"], 24)
        self.assertEqual(outcome["reserved_body_bytes_upper_bound"], 6291456)
        self.assertEqual(self.token_reads, 1)
        index = json.loads(Path(outcome["source_index"]["path"]).read_bytes())
        self.assertEqual(index["identity_rows"], 4908)
        self.assertEqual(index["evidence_class"], "synthetic_only_not_source_evidence")
        self.assertFalse(index["numerical_quality_verified"])
        raw = Path(index["roles"][0]["raw"]["path"]).read_bytes()
        self.assertIn(b"1e999999999", raw)
        self.assertNotIn("1e999999999", json.dumps(outcome))
        with self.assertRaises(FileExistsError):
            self.run_artificial()
        self.assertEqual(len(self.calls), 24)
        self.assertEqual(self.token_reads, 1)

    def test_first_provider_error_preserved_without_message_in_receipts(self):
        raw = b'{"code":2002,"msg":"private provider diagnostic 65432"}'
        outcome = self.run_artificial(lambda *a: report(raw))
        self.assertEqual(outcome["error"], "provider_envelope_rejected")
        self.assertEqual(outcome["HTTP_attempts_started"], 1)
        self.assertIsNone(outcome["source_index"])
        self.assertEqual(Path(outcome["request_receipts"][0]["raw"]["path"]).read_bytes(), raw)
        self.assertNotIn("65432", json.dumps(outcome))

    def test_escaped_secret_and_partial_non_JSON_are_never_persisted(self):
        escaped = "".join("\\u%04x" % ord(char) for char in TOKEN)
        for raw in (('{"msg":"'+escaped+'"}').encode(), b'{"truncated":"'+TOKEN.encode()[:7]):
            with self.subTest(raw_length=len(raw)), tempfile.TemporaryDirectory() as temp:
                outcome = B.capture_synthetic(self.manifest, self.sessions, temp,
                    transport=lambda *a: report(raw), token_loader=self.token)
                self.assertEqual(outcome["status"], "failed_consumed")
                self.assertIsNone(outcome["request_receipts"][0]["raw"])
                self.assertFalse(list(Path(temp).rglob("response.entity.json")))
                self.assertNotIn(TOKEN, json.dumps(outcome))
                self.assertEqual(outcome["body_bytes_received"], len(raw))

    def test_partial_safe_JSON_retained_but_transport_failure_cannot_make_index(self):
        outcome = self.run_artificial(lambda *a: report(b'{"code":0}', error="incomplete_HTTP_body"))
        self.assertEqual(outcome["error"], "incomplete_HTTP_body")
        self.assertIsNotNone(outcome["request_receipts"][0]["raw"])
        self.assertIsNone(outcome["source_index"])

    def test_missing_date_stops_remaining_requests_and_keeps_original(self):
        def missing(request, token, seconds):
            return report(body(request["expected_trade_dates"][:-1]))
        outcome = self.run_artificial(missing)
        self.assertEqual(outcome["error"], "response_date_set_mismatch")
        self.assertEqual(len(outcome["request_receipts"]), 1)
        receipt = json.loads(Path(outcome["request_receipts"][0]["receipt"]["path"]).read_bytes())
        self.assertEqual(len(receipt["identity_findings"]["missing_dates"]), 1)

    def test_prior_original_drift_stops_before_next_HTTP(self):
        original_save = B._save
        def tamper(path, value, **kwargs):
            ref = original_save(path, value, **kwargs)
            if Path(path).name == "receipt.json":
                Path(value["raw"]["path"]).write_bytes(b'{"changed":true}')
            return ref
        with patch.object(B, "_save", tamper):
            outcome = self.run_artificial()
        self.assertEqual(outcome["error"], "bound_artifact_changed")
        self.assertEqual(len(self.calls), 1)
        self.assertIsNone(outcome["source_index"])

    def test_context_drift_after_response_stops_next_request(self):
        calls = []
        def context():
            calls.append(1)
            if len(calls) == 3:
                raise B.BatchError("branch_or_HEAD_changed")
        outcome = B._capture(self.manifest, self.root/"capture", [], self.token, self.transport,
                             evidence_class="synthetic_only_not_source_evidence", check_context=context)
        self.assertEqual(outcome["error"], "branch_or_HEAD_changed")
        self.assertEqual(len(self.calls), 1)

    def test_unknown_worker_and_raised_transport_counts_are_not_zero_claims(self):
        unknown = {**report(b""), "body": None, "received_bytes": None,
                   "received_bytes_lower_bound": 17, "attempts_started": None,
                   "worker_exit_confirmed": False, "error": "worker_termination_unconfirmed"}
        outcome = self.run_artificial(lambda *a: unknown)
        self.assertIsNone(outcome["body_bytes_received"])
        self.assertIsNone(outcome["HTTP_attempts_started"])
        self.assertEqual(outcome["body_bytes_received_lower_bound"], 17)
        self.assertEqual(outcome["reserved_body_bytes_upper_bound"], 262144)
        with tempfile.TemporaryDirectory() as temp:
            def failed(*a):
                raise OSError(TOKEN)
            outcome = B.capture_synthetic(self.manifest, self.sessions, temp, transport=failed, token_loader=self.token)
        self.assertIsNone(outcome["body_bytes_received"])
        self.assertIsNone(outcome["HTTP_attempts_started"])
        self.assertEqual(len(outcome["request_claims"]), 1)
        self.assertNotIn(TOKEN, json.dumps(outcome))

    def test_bad_binding_and_missing_token_consume_no_HTTP(self):
        source = self.root/"bound.json"
        source.write_bytes(b"{}")
        ref = B.reference(source)
        source.write_bytes(b"[]")
        outcome = self.run_artificial(refs=[ref])
        self.assertEqual(outcome["error"], "bound_artifact_changed")
        self.assertEqual(self.token_reads, 0)
        self.assertEqual(self.calls, [])
        with tempfile.TemporaryDirectory() as temp:
            outcome = B.capture_synthetic(self.manifest, self.sessions, temp,
                      transport=self.transport, token_loader=lambda: None)
        self.assertEqual(outcome["error"], "credential_unavailable")
        self.assertEqual(outcome["HTTP_attempts_started"], 0)

    def test_public_preview_cannot_call_token_gate_or_transport(self):
        scope = {"root_review_path": "unused"}
        with patch.object(B, "_scope", return_value=(scope, self.manifest, self.root, [])), \
             patch.object(B, "_fresh_gate", side_effect=AssertionError("gate called")), \
             patch.object(B, "_isolated", side_effect=AssertionError("network called")), \
             patch.dict(B.os.environ, {}, clear=True):
            outcome = B.capture("unused", repo_root=self.root, expected_scope_sha256="unused")
        self.assertEqual(outcome["status"], "preview")
        self.assertFalse(outcome["credentials_read"])
        with self.assertRaises(TypeError):
            B.capture("unused", repo_root=self.root, expected_scope_sha256="unused", transport=self.transport)

    def exchange(self, response):
        connection = FakeConnection(response)
        events = []
        result = B._exchange(self.manifest["requests"][0], TOKEN, events.append, lambda *a, **k: connection)
        self.assertTrue(connection.closed)
        self.assertEqual(len(connection.calls), 1)
        self.assertEqual(connection.calls[0][0], ("POST", "/"))
        self.assertEqual(connection.calls[0][1]["headers"]["Accept-Encoding"], "identity")
        return result, events

    def test_HTTP_error_bytes_count_and_headers_are_safely_projected(self):
        raw = b'{"code":451,"msg":"denied"}'
        response = FakeResponse(raw, status=451, headers=[("Set-Cookie", TOKEN), ("Authorization", TOKEN),
                                 ("Date", "Sat, 07 Nov 2026 08:00:00 GMT"), ("X-Request-ID", TOKEN)])
        result, events = self.exchange(response)
        self.assertEqual(result["error"], "HTTP_status_rejected")
        self.assertEqual(result["received_bytes"], len(raw))
        self.assertEqual(result["body"], raw)
        self.assertEqual(set(result["headers"]), {"date"})
        self.assertNotIn(TOKEN, json.dumps(result["headers"]))
        self.assertEqual(events[-1]["count"], len(raw))

    def test_body_cap_no_extra_probe_declared_completion_vs_unknown_EOF(self):
        for known in (True, False):
            with self.subTest(content_length=known):
                response = FakeResponse(b"x"*B.LIMITS["response_bytes"], length=known)
                result, _ = self.exchange(response)
                self.assertEqual(result["received_bytes"], B.LIMITS["response_bytes"])
                self.assertEqual(sum(response.read_sizes), B.LIMITS["response_bytes"])
                self.assertEqual(result["error"], None if known else "response_cap_without_EOF")
        result, _ = self.exchange(FakeResponse(b"x"*(B.LIMITS["response_bytes"]+1)))
        self.assertEqual(result["error"], "response_cap_without_EOF")

    def test_incomplete_partial_count_and_unsupported_encoding(self):
        result, _ = self.exchange(FakeResponse(partial=b"12345"))
        self.assertEqual(result["received_bytes"], 5)
        self.assertEqual(result["error"], "incomplete_HTTP_body")
        response = FakeResponse(b"compressed", headers=[("Content-Encoding", "gzip")])
        result, _ = self.exchange(response)
        self.assertEqual(result["error"], "unsupported_content_encoding")
        self.assertEqual(response.read_sizes, [])
        self.assertEqual(result["received_bytes"], 0)

    def test_ambiguous_framing_stops_without_reading_body(self):
        for headers in ([('Content-Length', '2'), ('Content-Length', '3')],
                        [('Content-Length', '2'), ('Transfer-Encoding', 'chunked')]):
            response = FakeResponse(headers=headers)
            result, _ = self.exchange(response)
            self.assertEqual(result["error"], "ambiguous_HTTP_framing")
            self.assertEqual(response.read_sizes, [])

    def test_scope_preview_and_review_bind_exact_scope_without_circular_hash(self):
        for filename in B.CODE_FILES:
            path = self.root/filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('# artificial code only\n')
        manifest = B._save(self.root/'manifest.json', self.manifest)
        sessions = B._save(self.root/'sessions.json', self.sessions)
        now = datetime.now(timezone.utc)
        scope = {"artifact_type": "constant_mix_fund_daily_batch_scope_v1", "purpose": "source_structure_only",
                 "limits": B.LIMITS, "allow_2026_prices": False, "implementation": B.implementation(self.root),
                 "context": {"machine": "office_desktop", "task": "factor_review", "branch": "codex/artificial"},
                 "head": "artificial_HEAD", "valid_from": (now-timedelta(minutes=1)).isoformat(),
                 "valid_until": (now+timedelta(hours=1)).isoformat(), "manifest": manifest, "sessions": sessions,
                 "bindings": [], "capture_directory": str(self.root/'data/reports/capture'),
                 "root_review_path": str(self.root/'root_review.json')}
        scope_ref = B._save(self.root/'scope.json', scope)
        B._save(self.root/'root_review.json', {"status": "accepted_exact_constant_mix_source_capture",
            "scope_sha256": "wrong_scope_digest", "manifest_sha256": manifest['sha256'],
            "implementation": scope['implementation']})
        def fake_git(root, *args):
            return 'codex/artificial' if args[0] == 'branch' else 'artificial_HEAD'
        with patch.object(B, '_git', fake_git), patch.object(B, '_fresh_gate', side_effect=AssertionError('gate called')):
            preview = B.capture(scope_ref['path'], repo_root=self.root, expected_scope_sha256=scope_ref['sha256'])
            self.assertEqual(preview['status'], 'preview')
            with self.assertRaisesRegex(B.BatchError, 'exact_root_review_required'):
                B.capture(scope_ref['path'], repo_root=self.root, expected_scope_sha256=scope_ref['sha256'], execute=True)
        self.assertFalse((self.root/'data/reports/capture/claim.json').exists())

    def test_fresh_gate_normalized_hash_is_checked_and_raw_bytes_pinned(self):
        context = {"machine": "office_desktop", "task": "factor_review", "branch": "codex/artificial"}
        document = self.root/'protocol.md'
        document.write_bytes(b'first\r\nsecond\r\n')
        normalized = b'first\nsecond\n'
        gate = {"status": "ready", "primary_market": "CN_ETF", "blockers": [],
                "selected": {**context, "current_branch": context['branch']}, "generated_at": B._now(),
                "reading_summary": {"required": 1, "read": 1, "missing": 0},
                "required_reading": [{"path": "protocol.md", "status": "read", "bytes": len(normalized),
                                      "sha256": sha256(normalized).hexdigest()}],
                "safety": {"final_holdout_allowed": False, "live_boundary_allowed": False}}
        def fake_run(command, **kwargs):
            B._save(Path(command[-1])/'quant_pm_startup_gate_pack.json', gate)
            class Result:
                returncode = 0
            return Result()
        with patch.object(B.subprocess, 'run', fake_run):
            refs = B._fresh_gate(self.root, context, self.root/'capture')
        self.assertEqual(refs[-1], B.reference(document))
        self.assertNotEqual(refs[-1]['sha256'], gate['required_reading'][0]['sha256'])
        document.write_bytes(b'changed')
        with self.assertRaisesRegex(B.BatchError, 'bound_artifact_changed'):
            B._verify(refs)

    def test_unconfirmed_process_stop_is_explicit(self):
        class Unstoppable:
            def join(self, **kwargs): pass
            def is_alive(self): return True
            def terminate(self): pass
            def kill(self): pass
        self.assertFalse(B._stop(Unstoppable(), True, time.monotonic()))
        class StopRaises(Unstoppable):
            def terminate(self): raise OSError(TOKEN)
        self.assertFalse(B._stop(StopRaises(), True, time.monotonic()))

    def test_process_success_and_slow_process_deadline_are_confirmed(self):
        result = B._isolated({}, TOKEN, 5, worker=artificial_worker)
        self.assertTrue(result["worker_exit_confirmed"])
        self.assertEqual(result["body"], b"{}")
        started = time.monotonic()
        result = B._isolated({}, TOKEN, .2, worker=slow_worker)
        self.assertLess(time.monotonic()-started, 3)
        self.assertTrue(result["worker_exit_confirmed"])
        self.assertIsNone(result["received_bytes"])
        self.assertEqual(result["error"], "worker_wall_deadline")
        self.assertIsNone(result["body"])


if __name__ == "__main__":
    unittest.main()
