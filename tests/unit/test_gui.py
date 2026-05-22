import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from quant_robot.gui.app import create_gui_handler
from quant_robot.gui.research_service import build_gui_snapshot, run_demo_research


class GuiSnapshotTests(unittest.TestCase):
    def test_snapshot_marks_demo_data_and_includes_required_sections(self):
        snapshot = build_gui_snapshot()

        self.assertEqual(snapshot["data_mode"], "demo_fixture")
        self.assertFalse(snapshot["risk"]["account_connected"])
        self.assertEqual({market["market"] for market in snapshot["markets"]}, {"CN", "HK", "US", "CRYPTO"})
        self.assertIn("research", snapshot["logs"])
        self.assertGreaterEqual(snapshot["dashboard"]["strategy_count"], 1)

    def test_demo_research_payload_contains_metrics_tables_and_demo_label(self):
        result = run_demo_research(market="ALL", factor_name="momentum_2", top_n=2, cost_bps=5.0)

        self.assertEqual(result["data_mode"], "demo_fixture")
        self.assertIn("annualized_return", result["metrics"])
        self.assertIn("max_drawdown", result["metrics"])
        self.assertIn("sharpe", result["metrics"])
        self.assertIn("icir", result["factor_summary"])
        self.assertGreater(len(result["equity_curve"]), 0)
        self.assertGreater(len(result["trades"]), 0)
        self.assertGreater(len(result["holdings"]), 0)


class GuiHttpTests(unittest.TestCase):
    def test_http_app_serves_index_snapshot_and_demo_research(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_gui_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            html = _read_text(f"{base_url}/")
            self.assertIn("Quant Robot Local Console", html)

            snapshot = _read_json(f"{base_url}/api/snapshot")
            self.assertEqual(snapshot["data_mode"], "demo_fixture")

            research = _read_json(f"{base_url}/api/research/demo?market=CN&factor=momentum_2&top_n=1&cost_bps=5")
            self.assertEqual(research["request"]["market"], "CN")
            self.assertEqual(research["request"]["factor_name"], "momentum_2")
            self.assertGreater(len(research["equity_curve"]), 0)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()


def _read_text(url: str) -> str:
    with urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def _read_json(url: str) -> dict[str, object]:
    return json.loads(_read_text(url))


if __name__ == "__main__":
    unittest.main()
