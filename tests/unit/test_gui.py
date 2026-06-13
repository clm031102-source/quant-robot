import json
import threading
import tempfile
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.gui.app import create_gui_handler
from quant_robot.gui.research_service import (
    build_constrained_search_snapshot,
    build_daily_ops_snapshot,
    build_promotion_ops_snapshot,
    build_promotion_review_snapshot,
    build_evidence_refresh_snapshot,
    build_gui_snapshot,
    build_paper_profile_snapshot,
    build_project_status_snapshot,
    build_risk_candidate_snapshot,
    run_gui_paper_simulation,
    run_gui_research,
    run_gui_signal_snapshot,
    run_demo_paper_simulation,
    run_demo_research,
    run_demo_signal_snapshot,
)
from quant_robot.storage.dataset_store import DatasetStore


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

    def test_promotion_ops_snapshot_has_research_only_boundary(self):
        result = build_promotion_ops_snapshot()

        self.assertEqual(result["stage"], "phase_2_8_promotion_operations")
        self.assertFalse(result["live_review_allowed"])
        self.assertIn("No broker", result["safety"])

    def test_promotion_review_snapshot_has_candidate_packet(self):
        result = build_promotion_review_snapshot()

        self.assertEqual(result["stage"], "phase_2_9_promotion_review_packet")
        self.assertEqual(result["manual_review_gate"]["status"], "blocked")
        self.assertIn("Research only", result["markdown"])

    def test_evidence_refresh_snapshot_has_refresh_tracks(self):
        result = build_evidence_refresh_snapshot()

        self.assertEqual(result["stage"], "phase_3_0_evidence_refresh")
        self.assertIn(result["refresh_status"], {"action_required", "clear", "blocked"})
        self.assertGreaterEqual(len(result["tracks"]), 1)

    def test_project_status_snapshot_summarizes_local_readiness_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            board = root / "board.json"
            gap = root / "gap.json"
            provider = root / "provider.json"
            focus = root / "focus.json"
            board.write_text(
                json.dumps(
                    {
                        "overall_status": "blocked",
                        "selected_candidate": {
                            "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                            "promotion_status": "paper_ready",
                            "test_sharpe": 0.78,
                            "paper_sharpe": 0.52,
                        },
                        "readiness_items": [
                            {"track_id": "data_gap_resolution", "label": "Data gap resolution", "status": "block", "evidence": "blocking_gap_rows=6"},
                            {"track_id": "research_boundary", "label": "Research boundary", "status": "pass", "evidence": "order_placement=disabled"},
                        ],
                        "blocker_register": [
                            {"blocker_id": "data_gap_resolution_blocking_gaps", "severity": "block", "evidence": "blocking_gap_rows=6"}
                        ],
                        "next_local_actions": [
                            {"priority": 1, "track_id": "data_gap_evidence", "command": "python scripts\\run_data_gap_evidence.py", "reason": "Attach local raw CSV evidence."}
                        ],
                        "boundary": {"broker_connection": "disabled", "account_reads": "disabled", "order_placement": "disabled"},
                    }
                ),
                encoding="utf-8",
            )
            gap.write_text(
                json.dumps(
                    {
                        "summary": {"gap_rows": 6, "target_raw_rows_found": 0, "gaps_with_peer_trading": 6, "blocks_api_boundary": True},
                        "evidence_rows": [{"gap_id": "DG-1", "symbol": "159915.SZ", "missing_date": "2021-02-08", "target_raw_row_found": False}],
                    }
                ),
                encoding="utf-8",
            )
            provider.write_text(
                json.dumps(
                    {
                        "summary": {"remediation_items": 3, "blocking_remediation_items": 1, "blocks_api_boundary": True},
                        "remediation_items": [
                            {
                                "remediation_id": "PR-tushare-credential",
                                "provider": "tushare",
                                "review_status": "blocked_external_change",
                                "blocker": "TUSHARE_TOKEN is not set",
                                "blocks_provider_readiness": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            focus.write_text(
                json.dumps(
                    {
                        "summary": {"root_focus_items": 2, "residual_blockers": 5, "highest_priority_track": "data_gap_resolution"},
                        "focus_items": [{"track_id": "data_gap_resolution", "remaining_blockers": 4}],
                    }
                ),
                encoding="utf-8",
            )

            result = build_project_status_snapshot(
                readiness_board=board,
                data_gap_evidence=gap,
                provider_remediation=provider,
                residual_focus=focus,
            )

        self.assertEqual(result["stage"], "gui_project_status")
        self.assertEqual(result["overall_status"], "blocked")
        self.assertEqual(result["selected_candidate"]["promotion_status"], "paper_ready")
        self.assertEqual(result["data_gaps"]["gap_rows"], 6)
        self.assertEqual(result["provider_remediation"]["blocking_remediation_items"], 1)
        self.assertEqual(result["residual_focus"]["residual_blockers"], 5)
        self.assertFalse(result["tushare"]["required_now"])
        self.assertIn("run_data_gap_evidence.py", result["next_actions"][0]["command"])

    def test_daily_ops_snapshot_exposes_decision_risk_and_tickets(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "daily_ops_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_0_daily_ops",
                        "run_date": "2026-06-13",
                        "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
                        "candidate": {"case_id": "case_a", "market": "CN_ETF"},
                        "decision": {
                            "status": "blocked",
                            "paper_trading_allowed": False,
                            "live_boundary_allowed": False,
                            "blocking_reasons": ["manual_live_review_not_enabled", "risk_max_drawdown_breach"],
                            "non_manual_blocking_reasons": ["risk_max_drawdown_breach"],
                        },
                        "risk": {"total_return": 0.2, "max_equity_drawdown": -0.35},
                        "risk_policy": {"max_drawdown_limit": -0.2, "max_drawdown_breached": True},
                        "advisory_tickets": [],
                    }
                ),
                encoding="utf-8",
            )

            result = build_daily_ops_snapshot(daily_ops_pack=pack)

        self.assertEqual(result["stage"], "gui_daily_ops")
        self.assertTrue(result["artifact_present"])
        self.assertEqual(result["decision"]["status"], "blocked")
        self.assertFalse(result["decision"]["paper_trading_allowed"])
        self.assertEqual(result["risk_policy"]["max_drawdown_limit"], -0.2)
        self.assertEqual(result["ticket_count"], 0)
        self.assertIn("risk_max_drawdown_breach", result["blockers"])

    def test_risk_candidate_snapshot_exposes_summary_and_next_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "risk_candidate_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_1_risk_candidate_selector",
                        "selection_status": "no_risk_eligible_candidate",
                        "paper_trading_allowed": False,
                        "live_boundary_allowed": False,
                        "summary": {"candidates": 270, "risk_eligible_candidates": 0, "paper_matched_candidates": 5},
                        "selected_candidate": None,
                        "next_actions": [{"action": "run_constrained_candidate_search", "reason": "tighten risk policy"}],
                    }
                ),
                encoding="utf-8",
            )

            result = build_risk_candidate_snapshot(risk_candidate_pack=pack)

        self.assertEqual(result["stage"], "gui_risk_candidate_selector")
        self.assertTrue(result["artifact_present"])
        self.assertEqual(result["selection_status"], "no_risk_eligible_candidate")
        self.assertEqual(result["summary"]["risk_eligible_candidates"], 0)
        self.assertEqual(result["next_actions"][0]["action"], "run_constrained_candidate_search")

    def test_constrained_search_snapshot_exposes_frontier_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "constrained_candidate_search_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_2_constrained_candidate_search",
                        "selection_status": "no_risk_eligible_candidate",
                        "summary": {"walk_forward_accepted": 5, "risk_eligible_candidates": 0, "frontier_candidates": 1},
                        "frontier_candidates": [{"case_id": "case_a", "paper_sharpe_gap": 0.048, "paper_drawdown_headroom": 0.046}],
                        "next_actions": [{"action": "inspect_factor_families_with_low_drawdown", "reason": "frontier"}],
                    }
                ),
                encoding="utf-8",
            )

            result = build_constrained_search_snapshot(constrained_search_pack=pack)

        self.assertEqual(result["stage"], "gui_constrained_candidate_search")
        self.assertTrue(result["artifact_present"])
        self.assertEqual(result["summary"]["frontier_candidates"], 1)
        self.assertEqual(result["frontier_candidates"][0]["case_id"], "case_a")

    def test_paper_profile_snapshot_exposes_attempts_and_selected_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "paper_profile_optimizer_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_3_paper_profile_optimizer",
                        "selection_status": "no_paper_profile_candidate",
                        "summary": {"profile_attempts": 12, "eligible_profiles": 0, "rejected_profiles": 12},
                        "selected_profile": None,
                        "attempts": [{"case_id": "case_a", "profile_id": "cap46", "paper_sharpe": 0.41}],
                        "next_actions": [{"action": "expand_profile_grid_or_factor_family", "reason": "no pass"}],
                    }
                ),
                encoding="utf-8",
            )

            result = build_paper_profile_snapshot(paper_profile_pack=pack)

        self.assertEqual(result["stage"], "gui_paper_profile_optimizer")
        self.assertTrue(result["artifact_present"])
        self.assertEqual(result["summary"]["profile_attempts"], 12)
        self.assertEqual(result["attempts"][0]["profile_id"], "cap46")

    def test_gui_research_can_run_on_processed_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_processed_cn_etf_fixture(Path(tmp))

            result = run_gui_research(
                source="processed-bars",
                data_root=root,
                market="CN_ETF",
                factor_name="momentum_2",
                top_n=2,
                start_date="2026-01-02",
                end_date="2026-01-13",
            )

        self.assertEqual(result["data_mode"], "research")
        self.assertEqual(result["data_source"], "processed-bars")
        self.assertEqual(result["request"]["market"], "CN_ETF")
        self.assertGreater(len(result["equity_curve"]), 0)
        self.assertTrue(all(str(row["date"]).startswith("2026-") for row in result["equity_curve"]))

    def test_gui_signal_snapshot_can_run_on_processed_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_processed_cn_etf_fixture(Path(tmp))

            result = run_gui_signal_snapshot(
                source="processed-bars",
                data_root=root,
                market="CN_ETF",
                factor_name="momentum_2",
                top_n=2,
                as_of_date="2026-01-13",
                max_asset_weight=0.4,
                min_cash_weight=0.1,
            )

        self.assertEqual(result["data_mode"], "research")
        self.assertEqual(result["data_source"], "processed-bars")
        self.assertTrue(str(result["signal_date"]).startswith("2026-"))
        self.assertGreater(len(result["targets"]), 0)
        self.assertGreater(len(result["rebalance_plan"]), 0)
        self.assertTrue(all(row["executable"] is False for row in result["rebalance_plan"]))

    def test_gui_paper_simulation_can_run_on_processed_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_processed_cn_etf_fixture(Path(tmp))

            result = run_gui_paper_simulation(
                source="processed-bars",
                data_root=root,
                market="CN_ETF",
                factor_name="momentum_2",
                top_n=2,
                start_date="2026-01-04",
                end_date="2026-01-13",
                initial_cash=100000.0,
                max_asset_weight=0.4,
                min_cash_weight=0.1,
            )

        self.assertEqual(result["data_mode"], "research")
        self.assertEqual(result["data_source"], "processed-bars")
        self.assertGreater(len(result["equity_curve"]), 0)
        self.assertTrue(all(str(row["date"]).startswith("2026-") for row in result["equity_curve"]))
        self.assertGreater(len(result["fills"]), 0)
        self.assertTrue(all(row["fill_type"] == "simulated" for row in result["fills"]))


class GuiHttpTests(unittest.TestCase):
    def test_http_app_serves_index_snapshot_and_demo_workflows(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_gui_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            html = _read_text(f"{base_url}/")
            self.assertIn("Quant Robot Local Console", html)
            self.assertIn('rel="icon"', html)
            self.assertIn('href="data:,"', html)
            self.assertIn("信号快照", html)
            self.assertIn("纸面模拟", html)
            self.assertIn("A股ETF", html)
            self.assertIn("决策风控", html)
            self.assertIn("项目作战台", html)
            self.assertIn("project-action-table", html)
            self.assertIn("operator-strip", html)
            self.assertIn("command-card", html)
            self.assertIn("page-grid", html)
            self.assertIn("metric-card", html)
            self.assertIn("chart-panel", html)
            self.assertIn("table-panel", html)
            self.assertIn("promotion-metrics", html)
            self.assertIn("promotion-candidate-table", html)
            self.assertIn("promotion-action-list", html)
            self.assertIn("promotion-review-status", html)
            self.assertIn("promotion-review-markdown", html)
            self.assertIn("evidence-refresh-status", html)
            self.assertIn("evidence-refresh-action-table", html)
            self.assertIn("daily-ops-status", html)
            self.assertIn("daily-ops-ticket-table", html)
            self.assertIn("risk-candidate-status", html)
            self.assertIn("risk-candidate-action-table", html)
            self.assertIn("constrained-search-status", html)
            self.assertIn("constrained-frontier-table", html)
            self.assertIn("paper-profile-status", html)
            self.assertIn("paper-profile-attempt-table", html)
            self.assertIn("run-startup-workflows", html)
            self.assertIn("data-source-select", html)
            self.assertIn("data-root-input", html)
            self.assertIn("dashboard-equity-source", html)
            self.assertIn("processed-bars", html)
            self.assertNotIn('<span class="tag">demo fixture</span>', html)
            self.assertNotIn("鎬", html)
            self.assertNotIn("鐮", html)
            self.assertNotIn("妯", html)
            self.assertNotIn("鑲", html)

            app_js = _read_text(f"{base_url}/app.js")
            self.assertIn("/api/research?", app_js)
            self.assertIn("/api/signals?", app_js)
            self.assertIn("/api/paper?", app_js)
            self.assertIn("/api/daily/ops", app_js)
            self.assertIn("/api/risk/candidates", app_js)
            self.assertIn("/api/risk/constrained-search", app_js)
            self.assertIn("/api/risk/paper-profiles", app_js)
            self.assertIn("dashboard-equity-source", app_js)
            self.assertIn("runStartupWorkflows", app_js)
            startup_block = app_js.split('document.addEventListener("DOMContentLoaded", async () => {', 1)[1].split("});", 1)[0]
            self.assertIn("await loadRiskCandidates();", startup_block)
            self.assertNotIn("await runResearch();", startup_block)
            self.assertNotIn("await runSignals();", startup_block)
            self.assertNotIn("await runPaper();", startup_block)
            self.assertNotIn("await runPromotionOps();", startup_block)

            snapshot = _read_json(f"{base_url}/api/snapshot")
            self.assertEqual(snapshot["data_mode"], "demo_fixture")

            project = _read_json(f"{base_url}/api/project/status")
            self.assertEqual(project["stage"], "gui_project_status")
            self.assertIn("overall_status", project)

            daily_ops = _read_json(f"{base_url}/api/daily/ops")
            self.assertEqual(daily_ops["stage"], "gui_daily_ops")
            self.assertIn("decision", daily_ops)

            risk_candidates = _read_json(f"{base_url}/api/risk/candidates")
            self.assertEqual(risk_candidates["stage"], "gui_risk_candidate_selector")
            self.assertIn("selection_status", risk_candidates)

            constrained = _read_json(f"{base_url}/api/risk/constrained-search")
            self.assertEqual(constrained["stage"], "gui_constrained_candidate_search")
            self.assertIn("frontier_candidates", constrained)

            profiles = _read_json(f"{base_url}/api/risk/paper-profiles")
            self.assertEqual(profiles["stage"], "gui_paper_profile_optimizer")
            self.assertIn("attempts", profiles)

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

            promotion = _read_json(f"{base_url}/api/promotion/ops")
            self.assertEqual(promotion["stage"], "phase_2_8_promotion_operations")
            self.assertFalse(promotion["live_review_allowed"])

            review = _read_json(f"{base_url}/api/promotion/review")
            self.assertEqual(review["stage"], "phase_2_9_promotion_review_packet")
            self.assertEqual(review["manual_review_gate"]["status"], "blocked")

            refresh = _read_json(f"{base_url}/api/promotion/evidence-refresh")
            self.assertEqual(refresh["stage"], "phase_3_0_evidence_refresh")
            self.assertGreaterEqual(len(refresh["ordered_actions"]), 1)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_http_app_runs_processed_research_workflow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _write_processed_cn_etf_fixture(Path(tmp))
            server = ThreadingHTTPServer(("127.0.0.1", 0), create_gui_handler())
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            query = urlencode(
                {
                    "source": "processed-bars",
                    "data_root": str(root),
                    "market": "CN_ETF",
                    "factor": "momentum_2",
                    "top_n": "2",
                    "cost_bps": "5",
                    "start_date": "2026-01-02",
                    "end_date": "2026-01-13",
                }
            )
            try:
                research = _read_json(f"{base_url}/api/research?{query}")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

        self.assertEqual(research["data_mode"], "research")
        self.assertEqual(research["data_source"], "processed-bars")
        self.assertGreater(len(research["equity_curve"]), 0)
        self.assertTrue(all(str(row["date"]).startswith("2026-") for row in research["equity_curve"]))


def _read_text(url: str) -> str:
    with urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def _read_json(url: str) -> dict[str, object]:
    return json.loads(_read_text(url))


def _write_processed_cn_etf_fixture(root: Path) -> Path:
    bars = load_demo_market_bars()
    cn_etf = bars[bars["market"] == "CN_ETF"].copy().reset_index(drop=True)
    source_dates = sorted(pd.to_datetime(cn_etf["date"]).dt.date.unique())
    target_dates = pd.date_range("2026-01-02", periods=len(source_dates), freq="D").date
    date_map = dict(zip(source_dates, target_dates))
    cn_etf["date"] = pd.to_datetime(cn_etf["date"]).dt.date.map(date_map)
    cn_etf["timestamp"] = pd.to_datetime(cn_etf["date"])
    cn_etf["source"] = "processed_test"
    DatasetStore(root).write_frame(cn_etf, "processed/bars", {"frequency": "1d", "market": "CN_ETF", "year": "2026"})
    return root


if __name__ == "__main__":
    unittest.main()
