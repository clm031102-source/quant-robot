import json
import threading
import unittest
from contextlib import ExitStack
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

from quant_robot.gui import research_service as service
from quant_robot.gui.app import create_gui_handler
from quant_robot.ops.daily_trade_advisory import build_daily_trade_advisory_pack


class GuiDemoAdvisoryIsolationTests(unittest.TestCase):
    def forbid_ambient_reads(self, stack):
        readers = {}
        for name in (
            "build_factor_leaderboard_snapshot",
            "_server_pre_live_evidence_snapshot",
            "_read_optional_json",
            "load_processed_bars",
        ):
            readers[name] = stack.enter_context(patch.object(
                service, name, side_effect=AssertionError(f"ambient read: {name}")
            ))
        return readers

    def assert_demo_only(self, result):
        self.assertEqual(result["data_mode"], "demo_fixture")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["leaderboard_summary"]["report_files_scanned"], 0)
        self.assertTrue(result["selected_candidates"])
        self.assertTrue(all(row["fallback_baseline"] for row in result["selected_candidates"]))
        self.assertFalse(result["daily_ops_handoff"]["artifact_present"])
        self.assertFalse(result["daily_ops_handoff"]["summary"]["daily_ops_paper_trading_allowed"])
        self.assertTrue(result["summary"]["manual_trade_plan_blocked"])
        self.assertFalse(result["summary"]["live_trading_allowed"])
        rehearsal = result["daily_same_parameter_paper_rehearsal"]
        self.assertTrue(rehearsal["recommended_requests"])
        for request in rehearsal["recommended_requests"]:
            self.assertEqual(request["source"], "demo_fixture")
            query = parse_qs(urlparse(request["request_url"]).query)
            self.assertEqual(query["source"], ["demo_fixture"])
            self.assertEqual(query["same_parameter_lock_id"], [rehearsal["lock_id"]])
        handoff = result["daily_signal_execution_bridge"]["paper_simulation_handoff"]
        self.assertEqual(handoff["recommended_request"]["source"], "demo_fixture")

    def test_request_locks_distinguish_demo_and_processed_sources(self):
        candidate = {"case_id": "fixture", "factor_name": "momentum_2", "market": "CN_ETF"}
        locks = []
        for source in ("demo_fixture", "processed-bars"):
            result = build_daily_trade_advisory_pack([candidate], [], source=source)
            locks.append(result["daily_same_parameter_paper_rehearsal"]["lock_id"])
        self.assertNotEqual(*locks)

    def test_default_demo_aliases_never_read_workstation_reports_or_ledger(self):
        for source in ("demo_fixture", "fixture", " DEMO-FIXTURE "):
            with self.subTest(source=source), ExitStack() as stack:
                readers = self.forbid_ambient_reads(stack)
                result = service.build_daily_trade_advisory_snapshot(
                    source=source, market="CN_ETF", configs_root="unread-config-root",
                    data_root="unread-market-data-root", risk_profile_id="conservative_10dd",
                )
                self.assert_demo_only(result)
                for reader in readers.values():
                    reader.assert_not_called()

    def test_http_demo_does_not_accept_report_path_overrides(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_gui_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with ExitStack() as stack:
                readers = self.forbid_ambient_reads(stack)
                record = stack.enter_context(patch("quant_robot.gui.app._record_operation"))
                query = urlencode({
                    "source": "fixture", "market": "CN_ETF",
                    "reports_root": "unread-private-reports",
                    "configs_root": "unread-private-configs",
                    "data_root": "unread-private-bars",
                })
                with urlopen(f"http://127.0.0.1:{server.server_port}/api/trade/daily-advisory?{query}", timeout=10) as response:
                    result = json.load(response)
                self.assert_demo_only(result)
                for reader in readers.values():
                    reader.assert_not_called()
                self.assertEqual(record.call_args.kwargs["request"]["source"], "demo_fixture")
                request = result["daily_same_parameter_paper_rehearsal"]["recommended_requests"][0]
                with urlopen(f"http://127.0.0.1:{server.server_port}{request['request_url']}", timeout=10) as response:
                    paper = json.load(response)
                self.assertEqual(paper["data_source"], "demo_fixture")
                readers["load_processed_bars"].assert_not_called()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


if __name__ == "__main__":
    unittest.main()
