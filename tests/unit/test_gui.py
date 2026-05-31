import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen

from quant_robot.gui.app import create_gui_handler
from quant_robot.gui.research_service import (
    build_gui_snapshot,
    run_demo_paper_simulation,
    run_demo_research,
    run_demo_signal_snapshot,
)


class GuiSnapshotTests(unittest.TestCase):
    def test_snapshot_marks_demo_data_and_includes_required_sections(self):
        snapshot = build_gui_snapshot()

        self.assertEqual(snapshot["data_mode"], "demo_fixture")
        self.assertFalse(snapshot["risk"]["account_connected"])
        self.assertEqual({market["market"] for market in snapshot["markets"]}, {"CN", "CN_ETF", "HK", "US", "CRYPTO"})
        self.assertIn("research", snapshot["logs"])
        self.assertGreaterEqual(snapshot["dashboard"]["strategy_count"], 1)

    def test_demo_research_payload_contains_metrics_tables_decision_and_demo_label(self):
        result = run_demo_research(
            market="CN_ETF",
            factor_name="momentum_2",
            top_n=2,
            cost_bps=5.0,
            benchmark_asset_id="CN_ETF_XSHG_510300",
            cash_annual_return=0.015,
            regime_filter=True,
            regime_lookback=3,
            min_relative_return=-1.0,
            max_drawdown_limit=0.25,
        )

        self.assertEqual(result["data_mode"], "demo_fixture")
        self.assertIn("annualized_return", result["metrics"])
        self.assertIn("max_drawdown", result["metrics"])
        self.assertIn("sharpe", result["metrics"])
        self.assertIn("icir", result["factor_summary"])
        self.assertEqual(result["request"]["portfolio_scope"], "market")
        self.assertEqual(result["request"]["periods_per_year"], 252)
        self.assertIn("relative_return", result["benchmark_metrics"])
        self.assertIn(result["decision"]["decision_status"], {"approved", "rejected"})
        self.assertGreaterEqual(result["regime"]["blocked_signal_dates"], 0)
        self.assertGreater(len(result["equity_curve"]), 0)
        self.assertGreater(len(result["trades"]), 0)
        self.assertGreater(len(result["holdings"]), 0)

    def test_demo_signal_snapshot_contains_targets_and_research_only_rebalance_plan(self):
        result = run_demo_signal_snapshot(market="ALL", factor_name="momentum_2", top_n=2, max_asset_weight=0.4, min_cash_weight=0.1)

        self.assertEqual(result["data_mode"], "demo_fixture")
        self.assertGreater(len(result["targets"]), 0)
        self.assertGreater(len(result["rebalance_plan"]), 0)
        self.assertTrue(all(row["executable"] is False for row in result["rebalance_plan"]))
        self.assertLessEqual(result["target_gross_exposure"], 0.9)

    def test_demo_paper_simulation_contains_local_only_fills_positions_and_equity(self):
        result = run_demo_paper_simulation(
            market="ALL",
            factor_name="momentum_2",
            top_n=2,
            start_date="2024-01-04",
            end_date="2024-01-12",
            initial_cash=100000.0,
            max_asset_weight=0.4,
            min_cash_weight=0.1,
            max_drawdown_guard=0.50,
            guard_cooldown_periods=3,
        )

        self.assertEqual(result["data_mode"], "demo_fixture")
        self.assertIn("ending_equity", result["metrics"])
        self.assertIn("guard_event_count", result["metrics"])
        self.assertIn("guard_events", result)
        self.assertGreater(len(result["equity_curve"]), 0)
        self.assertGreater(len(result["fills"]), 0)
        self.assertGreater(len(result["positions"]), 0)
        self.assertTrue(all(row["fill_type"] == "simulated" for row in result["fills"]))
        self.assertTrue(all(row["executable"] is False for row in result["intents"]))


class GuiHttpTests(unittest.TestCase):
    def test_http_app_serves_index_snapshot_and_demo_workflows(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_gui_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            html = _read_text(f"{base_url}/")
            self.assertIn("Quant Robot Local Console", html)
            self.assertIn("信号快照", html)
            self.assertIn("纸面模拟", html)
            self.assertIn("A股ETF", html)
            self.assertIn("决策风控", html)
            self.assertNotIn("鎬", html)
            self.assertNotIn("鐮", html)
            self.assertNotIn("妯", html)
            self.assertNotIn("鑲", html)

            snapshot = _read_json(f"{base_url}/api/snapshot")
            self.assertEqual(snapshot["data_mode"], "demo_fixture")

            research = _read_json(
                f"{base_url}/api/research/demo?market=CN_ETF&factor=momentum_2&top_n=2&cost_bps=5"
                "&benchmark_asset_id=CN_ETF_XSHG_510300&cash_annual_return=0.015&regime_filter=true&regime_lookback=3"
            )
            self.assertEqual(research["request"]["market"], "CN_ETF")
            self.assertEqual(research["request"]["factor_name"], "momentum_2")
            self.assertIn("decision", research)
            self.assertIn("benchmark_metrics", research)
            self.assertGreater(len(research["equity_curve"]), 0)

            signal = _read_json(f"{base_url}/api/signals/demo?market=CN_ETF&factor=momentum_2&top_n=2&max_asset_weight=0.4&min_cash_weight=0.1")
            self.assertGreater(len(signal["targets"]), 0)
            self.assertFalse(signal["rebalance_plan"][0]["executable"])

            paper = _read_json(
                f"{base_url}/api/paper/demo?market=CN_ETF&factor=momentum_2&top_n=2&max_asset_weight=0.4&min_cash_weight=0.1"
                "&max_drawdown_guard=0.0001&guard_cooldown_periods=3"
            )
            self.assertGreater(len(paper["equity_curve"]), 0)
            self.assertGreater(len(paper["fills"]), 0)
            self.assertIn("guard_events", paper)
            self.assertFalse(paper["intents"][0]["executable"])
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
