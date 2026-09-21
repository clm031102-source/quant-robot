import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from scripts import collect_tushare_source_scope as cli
from tests.unit import test_tushare_source_collection as fixtures
from tests.unit.test_tushare_source_http import Response, Session


class TushareSourceCollectionCliTests(unittest.TestCase):
    def setUp(self):
        # Reuse fixture construction without inheriting/re-running its test cases.
        self.fixture = fixtures.TushareSourceCollectionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.path = self.root / "scope.json"
        self.path.write_text(json.dumps(self.fixture.scope), encoding="utf-8")
        self.args = ["--scope", str(self.path), "--machine", "office_desktop", "--branch", "codex/factor-review-test"]

    def invoke(self, args):
        stdout = io.StringIO()
        with patch.object(Path, "cwd", return_value=self.root), contextlib.redirect_stdout(stdout):
            code = cli.main(args)
        return code, json.loads(stdout.getvalue())

    def test_preview_then_execute_runs_fresh_gate_and_retains_canonical_response(self):
        with patch.object(cli, "run_quant_pm_startup_gate", return_value=self.fixture.gate) as gate, \
                patch.object(cli, "require_env_secret", return_value="private-test-token") as secret, \
                patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(self.fixture.response)) as network:
            code, preview = self.invoke(self.args)
            self.assertEqual(code, 0)
            gate.assert_not_called()
            secret.assert_not_called()
            network.assert_not_called()
            code, result = self.invoke([*self.args, "--execute", "--expected-scope-sha256", preview["scope_sha256"]])
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "collected_unqualified")
        self.assertEqual(gate.call_count, 1)
        self.assertEqual(gate.call_args.kwargs["task"], "factor_review")
        self.assertEqual(gate.call_args.kwargs["machine"], "office_desktop")
        secret.assert_called_once_with("TUSHARE_TOKEN")
        self.assertEqual(network.call_count, 1)
        self.assertTrue((Path(result["output_dir"]) / "invocation.json").is_file())

    def test_empty_source_returns_nonzero_and_is_not_promoted_as_no_events(self):
        _, preview = self.invoke(self.args)
        empty = Response({"code": 0, "data": {"fields": ["ts_code", "trade_date", "adj_factor"], "items": []}})
        with patch.object(cli, "run_quant_pm_startup_gate", return_value=self.fixture.gate), \
                patch.object(cli, "require_env_secret", return_value="private-test-token"), \
                patch("quant_robot.data.sources.tushare_http._new_session", return_value=Session(empty)):
            code, result = self.invoke([*self.args, "--execute", "--expected-scope-sha256", preview["scope_sha256"]])
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "collected_with_empty_unqualified")
        self.assertFalse(result["research_admission_granted"])

    def test_gate_blocked_despite_normal_return_never_reads_credential_or_network(self):
        _, preview = self.invoke(self.args)
        with patch.object(cli, "run_quant_pm_startup_gate", return_value={"status": "blocked"}), \
                patch.object(cli, "require_env_secret") as secret, \
                patch("quant_robot.data.sources.tushare_http._new_session") as network:
            code, result = self.invoke([*self.args, "--execute", "--expected-scope-sha256", preview["scope_sha256"]])
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "gate_blocked")
        secret.assert_not_called()
        network.assert_not_called()

    def test_malformed_scope_is_nonzero_without_echoing_arbitrary_secret_text(self):
        for text in ('{"private-test-token": ', self.path.read_text().replace('"max_date":', '"max_date":"20260101","max_date":')):
            with self.subTest(text=text):
                self.path.write_text(text, encoding="utf-8")
                code, result = self.invoke(self.args)
                self.assertEqual(code, 1)
                self.assertNotIn("private-test-token", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
