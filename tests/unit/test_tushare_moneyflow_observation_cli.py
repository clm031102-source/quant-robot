import contextlib
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import capture_tushare_moneyflow_observation as cli
from quant_robot.data.sources import tushare_moneyflow_observation as source
from tests.unit.test_tushare_moneyflow_observation import Session, Response, TOKEN, payload


class MoneyflowObservationCliTests(unittest.TestCase):
    def invoke(self, args):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = cli.main(args)
        return code, json.loads(output.getvalue())

    def test_preview_actual_entrypoint_receipt_and_duplicate_share_one_request(self):
        with tempfile.TemporaryDirectory() as temp:
            session = Session([Response(payload())])
            args = ["--machine", "office_desktop", "--branch", "codex/factor-review-test"]
            with patch.object(Path, "cwd", return_value=Path(temp)), \
                    patch.object(source, "_utc_now", return_value=datetime(2025, 1, 2, 11, 10, tzinfo=timezone.utc)), \
                    patch.object(source, "_new_session", return_value=session) as network, \
                    patch.object(cli, "require_env_secret", return_value=TOKEN) as secret, \
                    patch.object(cli, "run_quant_pm_startup_gate", return_value={
                        "status": "ready", "primary_market": "CN_ETF", "blockers": []}) as gate:
                code, result = self.invoke(args)
                self.assertEqual((code, result["status"]), (0, "preview"))
                gate.assert_not_called(); network.assert_not_called(); secret.assert_not_called()
                for expected in ["observed_unqualified", "already_attempted"]:
                    code, result = self.invoke([*args, "--execute"])
                    self.assertEqual((code, result["status"]), (0, expected))
                self.assertEqual(len(session.calls), 1)
                self.assertEqual(gate.call_count, 1)
                self.assertEqual(gate.call_args.kwargs["task"], "factor_review")
                self.assertEqual(secret.call_count, 1)

    def test_empty_source_and_repeated_failed_day_keep_failure_exit(self):
        with tempfile.TemporaryDirectory() as temp:
            p = payload(); p["data"]["items"] = []
            args = ["--machine", "office_desktop", "--branch", "codex/factor-review-test", "--execute"]
            with patch.object(Path, "cwd", return_value=Path(temp)), \
                    patch.object(source, "_utc_now", return_value=datetime(2025, 1, 2, 11, 10, tzinfo=timezone.utc)), \
                    patch.object(source, "_new_session", return_value=Session([Response(p)])), \
                    patch.object(cli, "require_env_secret", return_value=TOKEN), \
                    patch.object(cli, "run_quant_pm_startup_gate", return_value={
                        "status": "ready", "primary_market": "CN_ETF", "blockers": []}):
                self.assertEqual(self.invoke(args)[0], 1)
                self.assertEqual(self.invoke(args)[0], 1)

    def test_cli_has_no_historical_date_override(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            cli.main(["--machine", "office_desktop", "--branch", "codex/factor-review-test", "--date", "20240329"])
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
