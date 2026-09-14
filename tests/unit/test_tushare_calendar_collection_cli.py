import json
from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.data.cn_trading_calendar import build_cn_trading_calendar
from quant_robot.data.sources.tushare_mapping import map_tushare_trade_cal
from scripts import collect_tushare_source_scope as cli
from tests.unit.test_tushare_calendar_source import FIELDS, PARAMS, ROWS, payload
from tests.unit import test_tushare_source_collection_cli as fixtures
from tests.unit.test_tushare_source_http import Response, Session


class TushareCalendarCollectionCliTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.TushareSourceCollectionCliTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        scope = self.fixture.fixture.scope
        scope["requests"] = [{"api_name": "trade_cal", "fields": FIELDS, "max_rows": 3,
                              "params": {**PARAMS, "exchange": exchange}}
                             for exchange in ("SSE", "SZSE")]
        self.fixture.path.write_text(json.dumps(scope), encoding="utf-8")
        self.args = self.fixture.args

    def execute(self, responses):
        with patch.object(cli, "run_quant_pm_startup_gate", return_value=self.fixture.fixture.gate) as gate, \
                patch.object(cli, "require_env_secret", return_value="private-test-token") as secret, \
                patch("quant_robot.data.sources.tushare_http._new_session", side_effect=responses) as network:
            code, preview = self.fixture.invoke(self.args)
            self.assertEqual(code, 0)
            gate.assert_not_called()
            secret.assert_not_called()
            network.assert_not_called()
            args = [*self.args, "--execute", "--expected-scope-sha256", preview["scope_sha256"]]
            code, result = self.fixture.invoke(args)
            repeat_code, repeated = self.fixture.invoke(args)
            self.assertEqual(repeat_code, 1)
            self.assertEqual(repeated["status"], "rejected")
        return code, result, network.call_count

    def test_two_exchange_sources_survive_cli_and_existing_calendar_builder(self):
        szse = [["SZSE", *row[1:]] for row in ROWS]
        code, result, calls = self.execute([Session(Response(payload(ROWS))), Session(Response(payload(szse)))])
        self.assertEqual(code, 0)
        self.assertEqual(calls, 2)
        self.assertEqual(result["status"], "collected_unqualified")
        self.assertFalse(result["research_admission_granted"])
        self.assertFalse(result["source_audit_verified"])
        self.assertIn("tushare_calendar_contract.py", result["implementation_sha256"])
        frames = {}
        for i, exchange in enumerate(("SSE", "SZSE"), 1):
            attempt = json.loads((Path(result["output_dir"]) / f"request_{i:03}.json").read_text())
            saved = json.loads((Path(result["output_dir"]) / attempt["canonical_payload_file"]).read_text())
            data = saved["data"]
            frames[exchange] = pd.DataFrame(data["items"], columns=data["fields"])
            self.assertEqual(len(frames[exchange]), 3)
            self.assertNotIn("private-test-token", json.dumps(attempt))
            frames[exchange] = map_tushare_trade_cal(frames[exchange], open_only=True)
        calendar, manifest = build_cn_trading_calendar(frames, start_date="2024-01-05", end_date="2024-01-07")
        self.assertEqual(calendar.date.tolist(), ["2024-01-05"])
        self.assertEqual(manifest["summary"]["exchange_session_rows"], {"SSE": 1, "SZSE": 1})

    def test_partial_calendar_stops_remaining_requests_and_preserves_attempt(self):
        code, result, calls = self.execute([Session(Response(payload(ROWS[:1])))])
        self.assertEqual(code, 1)
        self.assertEqual(calls, 1)
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["research_admission_granted"])
        attempt = json.loads((Path(result["output_dir"]) / "request_001.json").read_text())
        self.assertEqual(attempt["transport"]["failure_kind"], "response_scope")
        self.assertFalse((Path(result["output_dir"]) / "request_002.json").exists())


if __name__ == "__main__":
    unittest.main()
