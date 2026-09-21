import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.config.secrets import SecretMissingError
from quant_robot.data.sources.tushare_collection import collect_source, validate_scope
from tests.unit.test_tushare_source_http import Response, Session


class TushareSourceCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = self.root / "review.md"
        self.evidence.write_text("Fixed source review; no outcome admission.", encoding="utf-8")
        self.scope = {
            "schema_version": 1, "scope_id": "source-review-1",
            "purpose": "source_qualification", "primary_market": "CN_ETF",
            "max_date": "20241231", "trust_env": False,
            "max_response_bytes": 10000, "connect_timeout": 10, "read_timeout": 20,
            "review_evidence": [{"path": "review.md", "sha256": hashlib.sha256(self.evidence.read_bytes()).hexdigest()}],
            "requests": [{"api_name": "fund_adj", "fields": "ts_code,trade_date,adj_factor",
                "max_rows": 3, "params": {"ts_code": "510300.SH", "trade_date": "20240118"}}],
        }
        self.gate = {"status": "ready", "primary_market": "CN_ETF", "blockers": []}
        self.response = Response({"code": 0, "data": {
            "fields": ["ts_code", "trade_date", "adj_factor"],
            "items": [["510300.SH", "20240118", 1.2]],
        }})

    def collect(self, scope=None, **kwargs):
        return collect_source(scope or self.scope, repo_root=self.root,
            run_gate=lambda path: self.gate, get_token=lambda: "private-test-token", **kwargs)

    def test_preview_validates_all_requests_without_gate_credentials_or_network(self):
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            result = collect_source(self.scope, repo_root=self.root,
                run_gate=lambda path: self.fail("preview gate"), get_token=lambda: self.fail("preview secret"))
        self.assertEqual(result["status"], "preview")
        self.assertFalse((self.root / "data").exists())
        network.assert_not_called()

    def test_changed_evidence_future_scope_and_duplicate_requests_fail_before_network(self):
        invalid = []
        for change in ({"max_date": "20260101"}, {"purpose": "factor_mining"}, {"token": "must-not-be-accepted"}):
            scope = copy.deepcopy(self.scope)
            scope.update(change)
            invalid.append(scope)
        scope = copy.deepcopy(self.scope)
        scope["requests"].append(copy.deepcopy(scope["requests"][0]))
        scope["requests"][1]["fields"] = "adj_factor,trade_date,ts_code"
        invalid.append(scope)
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            for scope in invalid:
                with self.subTest(scope=scope), self.assertRaises(ValueError):
                    validate_scope(scope, repo_root=self.root)
            self.evidence.write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "evidence"):
                validate_scope(self.scope, repo_root=self.root)
        network.assert_not_called()

    def test_execute_requires_exact_frozen_hash_and_fresh_gate_before_credentials(self):
        validated = validate_scope(self.scope, repo_root=self.root)
        with self.assertRaisesRegex(ValueError, "scope.*hash"):
            self.collect(execute=True, expected_scope_sha256="0" * 64)
        self.gate = {"status": "blocked", "primary_market": "CN_ETF", "blockers": ["not_ready"]}
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            result = collect_source(self.scope, repo_root=self.root, execute=True,
                expected_scope_sha256=validated["scope_sha256"], run_gate=lambda path: self.gate,
                get_token=lambda: self.fail("blocked gate read secret"))
        self.assertEqual(result["status"], "gate_blocked")
        self.assertEqual(result["requests_started"], 0)
        self.assertTrue((Path(result["output_dir"]) / "gate.json").exists())
        network.assert_not_called()

    def test_claim_and_started_record_exist_before_network_and_restart_cannot_repeat(self):
        validated = validate_scope(self.scope, repo_root=self.root)
        session = Session(self.response)
        def new_session():
            claims = list((self.root / "data/reports/tushare_source_collections/claims").glob("*.json"))
            self.assertEqual(len(claims), 1)
            claim = json.loads(claims[0].read_text(encoding="utf-8"))
            started = json.loads(Path(claim["attempt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(started["status"], "started")
            return session
        with patch("quant_robot.data.sources.tushare_http._new_session", side_effect=new_session):
            result = self.collect(execute=True, expected_scope_sha256=validated["scope_sha256"])
            with self.assertRaisesRegex(ValueError, "already"):
                self.collect(execute=True, expected_scope_sha256=validated["scope_sha256"])
        self.assertEqual(result["status"], "collected_unqualified")
        self.assertFalse(result["source_audit_verified"])
        self.assertEqual(len(session.calls), 1)
        attempt = json.loads((Path(result["output_dir"]) / "request_001.json").read_text())
        self.assertEqual(attempt["transport"]["response_sha256"], hashlib.sha256(self.response.raw).hexdigest())
        payload_path = Path(result["output_dir"]) / attempt["canonical_payload_file"]
        self.assertEqual(attempt["canonical_payload_sha256"], hashlib.sha256(payload_path.read_bytes()).hexdigest())

    def test_renamed_scope_changed_budget_and_field_order_cannot_repeat_consumed_request(self):
        validated = validate_scope(self.scope, repo_root=self.root)
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(self.response)) as network:
            self.collect(execute=True, expected_scope_sha256=validated["scope_sha256"])
            renamed = copy.deepcopy(self.scope)
            renamed["scope_id"] = "renamed"
            renamed["requests"][0]["max_rows"] = 10
            renamed["requests"][0]["fields"] = "adj_factor,trade_date,ts_code"
            sha = validate_scope(renamed, repo_root=self.root)["scope_sha256"]
            with self.assertRaisesRegex(ValueError, "already"):
                self.collect(renamed, execute=True, expected_scope_sha256=sha)
        self.assertEqual(network.call_count, 1)

    def test_permission_failure_is_retained_stops_batch_and_redacts_secret(self):
        self.scope["requests"].append({"api_name": "fund_adj", "fields": "ts_code,trade_date,adj_factor",
            "max_rows": 3, "params": {"ts_code": "510300.SH", "trade_date": "20240119"}})
        sha = validate_scope(self.scope, repo_root=self.root)["scope_sha256"]
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(Response({
                "code": 40203, "msg": "denied private-test-token"}))) as network:
            result = self.collect(execute=True, expected_scope_sha256=sha)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["requests_started"], 1)
        self.assertEqual(result["requests_not_started"], 1)
        self.assertEqual(network.call_count, 1)
        texts = "\n".join(p.read_text(encoding="utf-8") for p in Path(result["output_dir"]).glob("*.json"))
        self.assertIn("40203", texts)
        self.assertNotIn("private-test-token", texts)

    def test_validated_payload_preserves_nulls_integer_types_and_duplicate_rows(self):
        request = self.scope["requests"][0]
        request.update(api_name="fund_div", fields="ts_code,ann_date,cash_div,net_ex_date",
            params={"ann_date": "20240111"})
        payload = {"code": 0, "data": {"fields": request["fields"].split(","), "items": [
            ["510300.SH", "20240111", 1, None], ["510300.SH", "20240111", 0.5, "20240118"],
            ["510300.SH", "20240111", 1, None],
        ]}}
        sha = validate_scope(self.scope, repo_root=self.root)["scope_sha256"]
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(Response(payload))):
            result = self.collect(execute=True, expected_scope_sha256=sha)
        saved = json.loads((Path(result["output_dir"]) / "response_001.json").read_text())
        self.assertEqual(saved, payload)
        self.assertIs(type(saved["data"]["items"][0][2]), int)

    def test_interrupt_keeps_durable_claim_and_does_not_allow_restart(self):
        sha = validate_scope(self.scope, repo_root=self.root)["scope_sha256"]
        with patch("quant_robot.data.sources.tushare_http._new_session", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.collect(execute=True, expected_scope_sha256=sha)
        with self.assertRaisesRegex(ValueError, "already"):
            self.collect(execute=True, expected_scope_sha256=sha)

    def test_missing_existing_credential_is_recorded_without_consuming_requests(self):
        sha = validate_scope(self.scope, repo_root=self.root)["scope_sha256"]
        def missing_token():
            raise SecretMissingError("Required environment secret is missing: TUSHARE_TOKEN")
        with patch("quant_robot.data.sources.tushare_http._new_session") as network:
            result = collect_source(self.scope, repo_root=self.root, execute=True,
                expected_scope_sha256=sha, run_gate=lambda path: self.gate, get_token=missing_token)
        self.assertEqual(result["status"], "credential_missing")
        self.assertEqual(result["requests_started"], 0)
        self.assertEqual(list((self.root / "data/reports/tushare_source_collections/claims").glob("*.json")), [])
        network.assert_not_called()

    def test_ambiguous_json_stops_batch_without_persisting_a_successful_projection(self):
        second = copy.deepcopy(self.scope["requests"][0])
        second["params"]["ts_code"] = "510500.SH"
        self.scope["requests"].append(second)
        sha = validate_scope(self.scope, repo_root=self.root)["scope_sha256"]
        raw = self.response.raw[:-2] + b',"has_more":true,"has_more":false}}'
        session = Session(Response(raw=raw))
        with patch("quant_robot.data.sources.tushare_http._new_session", return_value=session):
            result = self.collect(execute=True, expected_scope_sha256=sha)
            with self.assertRaisesRegex(ValueError, "already"):
                self.collect(execute=True, expected_scope_sha256=sha)
        output = Path(result["output_dir"])
        attempt = json.loads((output / "request_001.json").read_text())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["requests_started"], 1)
        self.assertEqual(result["requests_not_started"], 1)
        self.assertEqual(result["responses_received"], 0)
        self.assertEqual(attempt["transport"]["failure_kind"], "response_schema")
        self.assertEqual(attempt["transport"]["response_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertNotIn("canonical_payload_file", attempt)
        self.assertFalse((output / "response_001.json").exists())
        self.assertFalse((output / "request_002.json").exists())
        self.assertEqual(len(session.calls), 1)


if __name__ == "__main__":
    unittest.main()
