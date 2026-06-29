import json
import threading
import tempfile
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.gui.app import create_gui_handler
from quant_robot.gui.research_service import (
    build_constrained_search_snapshot,
    build_daily_ops_snapshot,
    build_expanded_observation_replay_snapshot,
    build_factor_leaderboard_snapshot,
    build_promotion_ops_snapshot,
    build_promotion_review_snapshot,
    build_evidence_refresh_snapshot,
    build_gui_snapshot,
    build_iterative_observation_expansion_snapshot,
    build_observation_sufficiency_snapshot,
    build_paper_profile_snapshot,
    build_post_refresh_replay_snapshot,
    build_profile_observation_snapshot,
    build_project_status_snapshot,
    build_recent_data_refresh_snapshot,
    build_risk_candidate_snapshot,
    build_tushare_activation_gate_snapshot,
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

    def test_factor_leaderboard_snapshot_aggregates_configs_and_report_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports_root = root / "reports"
            configs_root = root / "configs"
            (reports_root / "round999").mkdir(parents=True)
            configs_root.mkdir()
            (configs_root / "experiment.json").write_text(
                json.dumps(
                    {
                        "experiment_grid": {
                            "factor_names": ["momentum_2", "turnover_rate_low_large_mv"],
                        },
                        "factor_name": "public_supertrend_state",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            leaderboard = [
                {
                    "case_id": f"case_{index:02d}",
                    "factor_name": f"factor_{index:02d}",
                    "market": "CN_ETF",
                    "total_return": 0.01 * index,
                    "annualized_return": 0.002 * index,
                    "sharpe": 0.1 * index,
                    "max_drawdown": -0.01 * index,
                    "win_rate": 0.5 + index / 1000,
                    "rank_ic": 0.001 * index,
                    "trade_count": 30 + index,
                    "params": {"top_n": (index % 5) + 1, "cost_bps": 5},
                    "decision_status": "rejected" if index < 24 else "watchlist",
                }
                for index in range(25)
            ]
            (reports_root / "round999" / "candidate_leaderboard.json").write_text(
                json.dumps({"stage": "unit_round", "leaderboard": leaderboard}, ensure_ascii=False),
                encoding="utf-8",
            )

            snapshot = build_factor_leaderboard_snapshot(
                reports_root=reports_root,
                configs_root=configs_root,
                limit=20,
            )

        self.assertEqual(snapshot["stage"], "gui_factor_leaderboard")
        self.assertGreaterEqual(snapshot["summary"]["config_factor_names"], 3)
        self.assertEqual(snapshot["summary"]["candidate_rows"], 25)
        self.assertEqual(snapshot["summary"]["top_n"], 20)
        self.assertEqual(len(snapshot["top20"]), 20)
        self.assertEqual(snapshot["top20"][0]["factor_name"], "factor_24")
        self.assertEqual(snapshot["top20"][0]["score_metric"], "sharpe")
        self.assertIn("momentum_2", snapshot["factor_names"]["from_configs"])
        self.assertIn("factor_00", snapshot["factor_names"]["from_reports"])
        self.assertIn("all_data", snapshot["top20"][0])
        self.assertIn("params", snapshot["top20"][0])
        self.assertIn("source_path", snapshot["top20"][0])

    def test_factor_leaderboard_segments_primary_etf_and_auxiliary_stock_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports_root = root / "reports"
            configs_root = root / "configs"
            (reports_root / "round100").mkdir(parents=True)
            (reports_root / "gui_factor_leaderboard_cache").mkdir()
            configs_root.mkdir()
            (configs_root / "grid.json").write_text(
                json.dumps({"factor_names": ["cn_etf_supertrend_state", "cn_stock_moneyflow_aux"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            rows = [
                {
                    "case_id": "CN_ETF_supertrend_top2_cost5",
                    "factor_name": "cn_etf_supertrend_state",
                    "market": "CN_ETF",
                    "paper_sharpe": 1.42,
                    "total_return": 0.68,
                    "annualized_return": 0.16,
                    "max_drawdown": -0.21,
                    "win_rate": 0.59,
                    "rank_ic": 0.042,
                    "trade_count": 64,
                    "sample_count": 560,
                    "oos_sharpe": 1.08,
                    "status": "watchlist",
                    "params": {"top_n": 2, "cost_bps": 5},
                },
                {
                    "case_id": "CN_moneyflow_rank_top10",
                    "factor_name": "cn_stock_moneyflow_aux",
                    "market": "CN",
                    "sharpe": 2.3,
                    "total_return": 1.2,
                    "annualized_return": 0.28,
                    "max_drawdown": -0.34,
                    "win_rate": 0.61,
                    "rank_ic": 0.05,
                    "trade_count": 80,
                    "sample_count": 700,
                    "params": {"top_n": 10, "cost_bps": 5},
                },
            ]
            (reports_root / "round100" / "candidate_leaderboard.json").write_text(
                json.dumps({"candidate_leaderboard": rows}, ensure_ascii=False),
                encoding="utf-8",
            )
            (reports_root / "gui_factor_leaderboard_cache" / "gui_factor_leaderboard_cache.json").write_text(
                json.dumps(
                    {
                        "stage": "gui_factor_leaderboard",
                        "top20": [
                            {
                                "case_id": "stale_cache_row",
                                "factor_name": "cache_should_not_appear",
                                "market": "CN_ETF",
                                "sharpe": 99,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            snapshot = build_factor_leaderboard_snapshot(
                reports_root=reports_root,
                configs_root=configs_root,
                limit=20,
            )

        self.assertEqual(snapshot["summary"]["primary_market"], "CN_ETF")
        self.assertEqual(snapshot["summary"]["candidate_rows_by_market"]["CN_ETF"], 1)
        self.assertEqual(snapshot["summary"]["candidate_rows_by_market"]["CN"], 1)
        self.assertEqual(snapshot["summary"]["primary_market_candidate_rows"], 1)
        self.assertIn("leaderboards", snapshot)
        self.assertEqual(snapshot["leaderboards"]["primary_cn_etf"]["rows"][0]["market"], "CN_ETF")
        self.assertEqual(snapshot["leaderboards"]["cn_stock_research"]["rows"][0]["market"], "CN")
        self.assertEqual(len(snapshot["leaderboards"]["all_history"]["rows"]), 2)
        primary_row = snapshot["leaderboards"]["primary_cn_etf"]["rows"][0]
        stock_row = snapshot["leaderboards"]["cn_stock_research"]["rows"][0]
        self.assertTrue(primary_row["is_primary_market"])
        self.assertIn(primary_row["promotion_label"], {"可进模拟盘观察", "可继续研究"})
        self.assertIn("CN_ETF 主线", primary_row["plain_conclusion"])
        self.assertFalse(stock_row["is_primary_market"])
        self.assertEqual(stock_row["market_role"], "cn_stock_auxiliary")
        self.assertIn("非ETF主线", stock_row["audit_badges"])
        self.assertIn("不能直接用于ETF轮动", stock_row["plain_conclusion"])
        self.assertNotIn("cache_should_not_appear", snapshot["factor_names"]["from_reports"])
        self.assertTrue(all(row.get("source_file") != "gui_factor_leaderboard_cache.json" for row in snapshot["top20"]))

    def test_control_center_snapshot_exposes_work_backtest_method_and_safety(self):
        from quant_robot.gui.control_center import build_control_center_snapshot

        result = build_control_center_snapshot(repo_root=Path.cwd(), active_goal="Build GUI control center")

        self.assertEqual(result["stage"], "gui_control_center")
        self.assertIn("work", result)
        self.assertIn("backtest", result)
        self.assertIn("form_defaults", result)
        self.assertIn("method", result)
        self.assertIn("results", result)
        self.assertIn("result_evidence", result)
        self.assertIn("ledger_evidence", result)
        self.assertIn("parameter_authority", result)
        self.assertIn("workflow_preflight", result)
        self.assertIn("paper_readiness", result)
        self.assertIn("action_center", result)
        self.assertIn("artifacts", result)
        self.assertIn("workflows", result)
        self.assertIn("report_links", result)
        self.assertIn("workspace_sync", result)
        self.assertIn("process_monitor", result)
        self.assertIn("active_operation", result)
        self.assertIn("operation_ledger", result)
        self.assertIn("trade_mode_control", result)
        self.assertIn("run_queue", result)
        self.assertIn("verification_gates", result)
        self.assertIn("verification_runner", result)
        self.assertIn("operator_checklist", result)
        self.assertIn("execution_plan", result)
        self.assertIn("startup_health", result)
        self.assertIn("backtest_provenance", result)
        self.assertIn("backtest_gate", result)
        self.assertIn("workflow_trace", result)
        self.assertIn("readiness_matrix", result)
        self.assertIn("release_readiness", result)
        self.assertIn("audit_scorecard", result)
        self.assertIn("operator_timeline", result)
        self.assertIn("run_history", result)
        self.assertIn("execution_receipts", result)
        self.assertIn("audit_packets", result)
        self.assertIn("audit_feedback", result)
        self.assertIn("audit_iteration_plan", result)
        self.assertIn("round_checkpoint_report", result)
        self.assertIn("audit_scheduler", result)
        self.assertIn("safety", result)
        self.assertIn("automation", result)
        self.assertFalse(result["safety"]["live_trading_allowed"])
        self.assertEqual(result["form_defaults"]["stage"], "gui_form_defaults")
        self.assertEqual(result["form_defaults"]["research"]["factor"], result["backtest"]["factor"])
        self.assertEqual(result["form_defaults"]["research"]["factor_windows"], result["backtest"]["factor_windows"])
        selected_window = result["backtest"]["factor"].rsplit("_", 1)[-1]
        self.assertIn(selected_window, result["backtest"]["factor_windows"].split(","))
        self.assertLessEqual(result["backtest"]["start_date"], "2016-01-01")
        self.assertEqual(result["form_defaults"]["research"]["start_date"], result["backtest"]["start_date"])
        self.assertEqual(result["form_defaults"]["research"]["end_date"], result["backtest"]["end_date"])
        self.assertEqual(result["form_defaults"]["research"]["top_n"], result["backtest"]["top_n"])
        self.assertEqual(result["form_defaults"]["research"]["rebalance_interval"], result["backtest"]["rebalance_interval"])
        self.assertEqual(result["form_defaults"]["research"]["execution_lag"], result["backtest"]["execution_lag"])
        self.assertEqual(result["form_defaults"]["research"]["forward_horizon"], result["backtest"]["forward_horizon"])
        self.assertEqual(result["form_defaults"]["signal"]["factor"], result["backtest"]["factor"])
        self.assertEqual(result["form_defaults"]["signal"]["as_of_date"], result["backtest"]["end_date"])
        self.assertEqual(result["form_defaults"]["paper"]["factor"], result["backtest"]["factor"])
        self.assertEqual(result["form_defaults"]["paper"]["initial_cash"], 100000)
        self.assertEqual(result["form_defaults"]["paper"]["max_market_weight"], 1)
        self.assertEqual(result["form_defaults"]["paper"]["max_gross_exposure"], 1)
        self.assertGreaterEqual(len(result["method"]["steps"]), 6)
        self.assertGreaterEqual(len(result["workflows"]), 4)
        self.assertGreaterEqual(len(result["verification_gates"]), 5)
        self.assertTrue(all(item["mode"] == "local" for item in result["workflows"]))
        workflow_by_id = {item["workflow_id"]: item for item in result["workflows"]}
        self.assertEqual(workflow_by_id["research_backtest"]["request"]["factor_name"], result["backtest"]["factor"])
        self.assertEqual(workflow_by_id["research_backtest"]["request"]["execution_lag"], result["backtest"]["execution_lag"])
        self.assertIn(f"execution_lag={result['backtest']['execution_lag']}", workflow_by_id["research_backtest"]["command"])
        self.assertIn(f"forward_horizon={result['backtest']['forward_horizon']}", workflow_by_id["research_backtest"]["command"])
        self.assertEqual(workflow_by_id["signal_snapshot"]["request"]["factor_name"], result["backtest"]["factor"])
        self.assertEqual(workflow_by_id["paper_simulation"]["request"]["max_market_weight"], result["form_defaults"]["paper"]["max_market_weight"])
        self.assertEqual(workflow_by_id["paper_simulation"]["request"]["max_gross_exposure"], result["form_defaults"]["paper"]["max_gross_exposure"])
        self.assertTrue(all(item["mode"] == "local" for item in result["verification_gates"]))
        self.assertTrue(any("test_gui" in item["command"] for item in result["verification_gates"]))
        self.assertTrue(any("run_project_audit.py" in item["command"] for item in result["verification_gates"]))
        self.assertEqual(result["verification_runner"]["stage"], "gui_verification_runner")
        self.assertFalse(result["verification_runner"]["summary"]["live_trading_allowed"])
        self.assertIn("gui_compile", result["verification_runner"]["summary"]["allowed_gate_ids"])
        runner_row_ids = {item["gate_id"] for item in result["verification_runner"]["rows"]}
        self.assertIn("gui_compile", runner_row_ids)
        self.assertTrue(
            all(str(item.get("endpoint", "")).startswith("/api/control/verification?gate_id=") for item in result["verification_runner"]["rows"])
        )
        self.assertEqual(result["active_operation"]["stage"], "gui_active_operation")
        self.assertFalse(result["active_operation"]["summary"]["live_trading_allowed"])
        self.assertFalse(result["active_operation"]["summary"]["order_placement_allowed"])
        self.assertIn("research_backtest", result["active_operation"]["summary"]["supported_workflow_ids"])
        self.assertIn("verification_runner", result["active_operation"]["summary"]["supported_workflow_ids"])
        active_operation_ids = {item["check_id"] for item in result["active_operation"]["rows"]}
        self.assertIn("current_browser_operation", active_operation_ids)
        self.assertIn("last_browser_receipt", active_operation_ids)
        self.assertIn("safe_boundary", active_operation_ids)
        self.assertEqual(result["operation_ledger"]["stage"], "gui_operation_ledger")
        self.assertFalse(result["operation_ledger"]["summary"]["live_trading_allowed"])
        self.assertEqual(result["trade_mode_control"]["stage"], "gui_trade_mode_control")
        self.assertEqual(result["trade_mode_control"]["summary"]["default_mode"], "research")
        self.assertTrue(result["trade_mode_control"]["summary"]["paper_simulation_available"])
        self.assertFalse(result["trade_mode_control"]["summary"]["live_trading_allowed"])
        mode_ids = {item["mode_id"] for item in result["trade_mode_control"]["rows"]}
        self.assertEqual(mode_ids, {"research", "paper_simulation", "live_trading"})
        mode_rows = {item["mode_id"]: item for item in result["trade_mode_control"]["rows"]}
        self.assertEqual(mode_rows["research"]["status"], "ready")
        self.assertEqual(mode_rows["paper_simulation"]["status"], "gate_controlled")
        self.assertEqual(mode_rows["live_trading"]["status"], "blocked")
        self.assertIn("/api/paper?", mode_rows["paper_simulation"]["entrypoint"])
        self.assertFalse(mode_rows["live_trading"]["permissions"]["order_placement_allowed"])
        self.assertEqual(result["operator_checklist"]["stage"], "operator_checklist")
        self.assertFalse(result["operator_checklist"]["summary"]["live_ready"])
        self.assertGreaterEqual(result["operator_checklist"]["summary"]["required"], 3)
        self.assertTrue(any(item["check_id"] == "live_boundary" for item in result["operator_checklist"]["items"]))
        self.assertEqual(result["execution_plan"]["stage"], "execution_plan")
        self.assertEqual(result["execution_plan"]["summary"]["active_step"], "research_backtest")
        self.assertGreaterEqual(len(result["execution_plan"]["steps"]), 6)
        self.assertTrue(any(item["status"] == "blocked" for item in result["execution_plan"]["steps"]))
        self.assertEqual(result["startup_health"]["stage"], "gui_startup_health")
        self.assertIn(result["startup_health"]["summary"]["status"], {"ready", "needs_evidence"})
        self.assertIn("control_status_endpoint", result["startup_health"]["summary"])
        self.assertIn("browser_smoke_ready", result["startup_health"]["summary"])
        startup_ids = {item["check_id"] for item in result["startup_health"]["rows"]}
        self.assertIn("local_startup_smoke", startup_ids)
        self.assertIn("control_status_api", startup_ids)
        self.assertIn("browser_desktop_smoke", startup_ids)
        self.assertIn("browser_mobile_smoke", startup_ids)
        self.assertIn("browser_smoke_packet", startup_ids)
        self.assertTrue(all(item.get("command") for item in result["startup_health"]["rows"]))
        self.assertTrue(all(item.get("evidence") for item in result["startup_health"]["rows"]))
        self.assertEqual(result["backtest_provenance"]["stage"], "backtest_provenance")
        self.assertEqual(result["backtest_provenance"]["summary"]["market"], "CN_ETF")
        self.assertEqual(result["backtest_provenance"]["summary"]["factor"], result["backtest"]["factor"])
        self.assertIn("/api/research?", result["backtest_provenance"]["summary"]["research_endpoint"])
        self.assertIn("/api/paper?", result["backtest_provenance"]["summary"]["paper_endpoint"])
        self.assertTrue(result["backtest_provenance"]["summary"]["paper_only"])
        provenance_ids = {item["check_id"] for item in result["backtest_provenance"]["rows"]}
        self.assertIn("data_scope", provenance_ids)
        self.assertIn("factor_inputs", provenance_ids)
        self.assertIn("execution_model", provenance_ids)
        self.assertIn("cost_model", provenance_ids)
        self.assertIn("output_metrics", provenance_ids)
        self.assertIn("paper_live_boundary", provenance_ids)
        self.assertTrue(all(item.get("detail") for item in result["backtest_provenance"]["rows"]))
        self.assertEqual(result["result_evidence"]["stage"], "gui_result_evidence")
        self.assertEqual(result["result_evidence"]["summary"]["receipt_storage_key"], result["execution_receipts"]["storage_key"])
        self.assertIn("/api/research?", result["result_evidence"]["summary"]["research_endpoint"])
        self.assertIn("/api/paper?", result["result_evidence"]["summary"]["paper_endpoint"])
        self.assertTrue(result["result_evidence"]["summary"]["paper_only"])
        self.assertFalse(result["result_evidence"]["summary"]["live_trading_allowed"])
        result_evidence_ids = {item["check_id"] for item in result["result_evidence"]["rows"]}
        self.assertIn("research_metrics", result_evidence_ids)
        self.assertIn("benchmark_metrics", result_evidence_ids)
        self.assertIn("paper_metrics", result_evidence_ids)
        self.assertIn("signal_metrics", result_evidence_ids)
        self.assertIn("execution_receipts", result_evidence_ids)
        self.assertIn("live_boundary", result_evidence_ids)
        self.assertTrue(any("sharpe" in item.get("metric_keys", []) for item in result["result_evidence"]["rows"]))
        self.assertTrue(all(item.get("source_workflow") for item in result["result_evidence"]["rows"] if item["check_id"] != "live_boundary"))
        self.assertEqual(result["ledger_evidence"]["stage"], "gui_ledger_evidence")
        self.assertFalse(result["ledger_evidence"]["summary"]["live_trading_allowed"])
        self.assertIn(result["ledger_evidence"]["summary"]["status"], {"current", "partial", "needs_current_receipts"})
        ledger_workflows = {item["workflow_id"] for item in result["ledger_evidence"]["rows"]}
        self.assertIn("research_backtest", ledger_workflows)
        self.assertIn("signal_snapshot", ledger_workflows)
        self.assertIn("paper_simulation", ledger_workflows)
        self.assertIn("verification_runner", ledger_workflows)
        self.assertTrue(all(item.get("current_command") for item in result["ledger_evidence"]["rows"]))
        self.assertTrue(all("matches_current_command" in item for item in result["ledger_evidence"]["rows"]))
        self.assertTrue(all("matches_current_request" in item for item in result["ledger_evidence"]["rows"]))
        self.assertEqual(result["parameter_authority"]["stage"], "gui_parameter_authority")
        self.assertEqual(result["parameter_authority"]["summary"]["status"], "ready")
        self.assertFalse(result["parameter_authority"]["summary"]["live_trading_allowed"])
        authority_rows = {item["workflow_id"]: item for item in result["parameter_authority"]["rows"]}
        self.assertEqual(set(authority_rows), {"research_backtest", "signal_snapshot", "paper_simulation"})
        self.assertIn("execution_lag", authority_rows["research_backtest"]["comparison_keys"])
        self.assertIn("forward_horizon", authority_rows["research_backtest"]["comparison_keys"])
        self.assertIn("max_gross_exposure", authority_rows["paper_simulation"]["comparison_keys"])
        self.assertEqual(authority_rows["research_backtest"]["canonical_request"]["factor_name"], result["backtest"]["factor"])
        self.assertEqual(authority_rows["paper_simulation"]["canonical_request"]["max_market_weight"], result["form_defaults"]["paper"]["max_market_weight"])
        self.assertEqual(result["workflow_preflight"]["stage"], "gui_workflow_preflight")
        self.assertEqual(result["workflow_preflight"]["summary"]["status"], "review")
        self.assertGreaterEqual(result["workflow_preflight"]["summary"]["review_count"], 1)
        self.assertFalse(result["workflow_preflight"]["summary"]["live_trading_allowed"])
        preflight_rows = {item["workflow_id"]: item for item in result["workflow_preflight"]["rows"]}
        self.assertEqual(
            set(preflight_rows),
            {"research_backtest", "signal_snapshot", "paper_simulation", "verification_runner", "live_trading"},
        )
        self.assertEqual(preflight_rows["research_backtest"]["status"], "ready_to_run")
        self.assertTrue(preflight_rows["research_backtest"]["runnable"])
        self.assertIn("/api/research?", preflight_rows["research_backtest"]["endpoint"])
        self.assertEqual(preflight_rows["paper_simulation"]["mode"], "paper_simulation")
        self.assertEqual(preflight_rows["paper_simulation"]["status"], "gate_controlled")
        self.assertTrue(preflight_rows["paper_simulation"]["paper_only"])
        self.assertIn("parameter_authority", {check["check_id"] for check in preflight_rows["research_backtest"]["checks"]})
        self.assertIn("server_receipt", {check["check_id"] for check in preflight_rows["research_backtest"]["checks"]})
        self.assertTrue(preflight_rows["verification_runner"]["endpoint"].startswith("/api/control/verification?gate_id="))
        self.assertTrue(preflight_rows["verification_runner"]["command"].startswith("GET /api/control/verification?gate_id="))
        self.assertNotIn("GET GET", preflight_rows["verification_runner"]["command"])
        self.assertEqual(preflight_rows["live_trading"]["status"], "blocked")
        self.assertFalse(preflight_rows["live_trading"]["runnable"])
        self.assertFalse(preflight_rows["live_trading"]["permissions"]["order_placement_allowed"])
        self.assertEqual(result["paper_readiness"]["stage"], "gui_paper_readiness_handoff")
        self.assertIn(result["paper_readiness"]["summary"]["status"], {"awaiting_current_evidence", "review", "paper_candidate"})
        self.assertFalse(result["paper_readiness"]["summary"]["paper_candidate_allowed"])
        self.assertFalse(result["paper_readiness"]["summary"]["live_trading_allowed"])
        self.assertEqual(
            result["paper_readiness"]["summary"]["required_workflows"],
            ["research_backtest", "paper_simulation"],
        )
        self.assertIn("next_action", result["paper_readiness"]["summary"])
        readiness_rows = {item["check_id"]: item for item in result["paper_readiness"]["rows"]}
        self.assertEqual(
            set(readiness_rows),
            {"research_receipt", "paper_receipt", "metric_floor", "preflight_review", "paper_gate", "live_boundary"},
        )
        self.assertEqual(readiness_rows["research_receipt"]["source_workflow"], "research_backtest")
        self.assertEqual(readiness_rows["paper_receipt"]["source_workflow"], "paper_simulation")
        self.assertEqual(readiness_rows["metric_floor"]["source"], "backtest_gate")
        self.assertIn("sharpe", readiness_rows["metric_floor"]["metric_keys"])
        self.assertEqual(readiness_rows["paper_gate"]["source"], "gui_backtest_gate")
        self.assertEqual(readiness_rows["live_boundary"]["status"], "blocked_live")
        self.assertFalse(readiness_rows["live_boundary"]["permissions"]["order_placement_allowed"])
        self.assertTrue(all(item.get("evidence") for item in result["paper_readiness"]["rows"]))
        self.assertTrue(all(item.get("next_action") for item in result["paper_readiness"]["rows"]))
        audit_category_ids = {item["category_id"] for item in result["audit_scorecard"]["categories"]}
        self.assertIn("server_ledger_evidence", audit_category_ids)
        self.assertIn("ledger_current_receipts", result["audit_scorecard"]["summary"])
        self.assertEqual(result["action_center"]["stage"], "gui_action_center")
        self.assertFalse(result["action_center"]["summary"]["live_trading_allowed"])
        self.assertGreaterEqual(result["action_center"]["summary"]["action_count"], 1)
        self.assertIn(result["action_center"]["summary"]["status"], {"ready", "review", "blocked"})
        action_rows = result["action_center"]["rows"]
        self.assertTrue(all(item.get("priority") for item in action_rows))
        self.assertTrue(all("runnable" in item for item in action_rows))
        self.assertTrue(all(item.get("command") for item in action_rows if item.get("runnable")))
        self.assertTrue(all(item.get("safety") for item in action_rows))
        self.assertTrue(any(item.get("workflow_id") in {"research_backtest", "signal_snapshot", "paper_simulation", "verification_runner"} for item in action_rows))
        self.assertEqual(result["backtest_gate"]["stage"], "gui_backtest_gate")
        self.assertFalse(result["backtest_gate"]["summary"]["live_trading_allowed"])
        self.assertFalse(result["backtest_gate"]["summary"]["paper_candidate_allowed"])
        gate_ids = {item["gate_id"] for item in result["backtest_gate"]["rows"]}
        self.assertIn("sharpe", gate_ids)
        self.assertIn("total_return", gate_ids)
        self.assertIn("annualized_return", gate_ids)
        self.assertIn("max_drawdown", gate_ids)
        self.assertIn("win_rate", gate_ids)
        self.assertIn("trade_count", gate_ids)
        self.assertIn("benchmark_relative_return", gate_ids)
        self.assertIn("paper_ending_equity", gate_ids)
        self.assertIn("execution_receipts", gate_ids)
        self.assertIn("live_boundary", gate_ids)
        self.assertTrue(all(item.get("command") for item in result["backtest_gate"]["rows"]))
        self.assertTrue(all(item.get("evidence") for item in result["backtest_gate"]["rows"]))
        gate_rows = {item["gate_id"]: item for item in result["backtest_gate"]["rows"]}
        self.assertEqual(gate_rows["max_drawdown"]["comparator"], ">=")
        self.assertEqual(gate_rows["max_drawdown"]["threshold"], -0.30)
        self.assertEqual(gate_rows["paper_ending_equity"]["threshold_source"], "paper_request.initial_cash")
        self.assertEqual(gate_rows["execution_receipts"]["receipt_workflow_ids"], ["research_backtest", "paper_simulation"])
        self.assertTrue(gate_rows["execution_receipts"]["requires_current_request"])
        self.assertEqual(gate_rows["live_boundary"]["source"], "safety")
        self.assertEqual(result["workflow_trace"]["stage"], "gui_workflow_trace")
        self.assertEqual(result["workflow_trace"]["summary"]["current_workflow"], "research_backtest")
        self.assertTrue(result["workflow_trace"]["summary"]["paper_only"])
        self.assertFalse(result["workflow_trace"]["summary"]["live_trading_allowed"])
        trace_ids = {item["trace_id"] for item in result["workflow_trace"]["rows"]}
        self.assertIn("startup_health", trace_ids)
        self.assertIn("research_backtest", trace_ids)
        self.assertIn("result_evidence", trace_ids)
        self.assertIn("signal_snapshot", trace_ids)
        self.assertIn("paper_simulation", trace_ids)
        self.assertIn("verification_pack", trace_ids)
        self.assertIn("audit_packet", trace_ids)
        self.assertIn("publish_branch", trace_ids)
        self.assertIn("live_boundary", trace_ids)
        self.assertTrue(all(item.get("command") for item in result["workflow_trace"]["rows"]))
        self.assertTrue(all(item.get("evidence") for item in result["workflow_trace"]["rows"]))
        self.assertEqual(result["readiness_matrix"]["stage"], "readiness_matrix")
        self.assertGreaterEqual(len(result["readiness_matrix"]["rows"]), 4)
        self.assertTrue(any(item["mode_id"] == "paper_simulation" for item in result["readiness_matrix"]["rows"]))
        self.assertTrue(any(item["mode_id"] == "live_trading" and item["status"] == "blocked" for item in result["readiness_matrix"]["rows"]))
        self.assertEqual(result["release_readiness"]["stage"], "gui_release_readiness")
        self.assertIn("evidence_ready", result["release_readiness"]["summary"])
        self.assertIn("manual_required", result["release_readiness"]["summary"])
        readiness_ids = {item["check_id"] for item in result["release_readiness"]["rows"]}
        self.assertIn("gui_unit_tests", readiness_ids)
        self.assertIn("project_audit_packet", readiness_ids)
        self.assertIn("browser_smoke_packet", readiness_ids)
        self.assertIn("independent_gui_audit_packet", readiness_ids)
        self.assertIn("live_boundary", readiness_ids)
        self.assertTrue(
            any(
                item["check_id"] == "live_boundary" and item["status"] == "blocked_expected"
                for item in result["release_readiness"]["rows"]
            )
        )
        self.assertEqual(result["audit_scorecard"]["stage"], "gui_audit_scorecard")
        self.assertEqual(result["audit_scorecard"]["summary"]["cadence_hours"], 5)
        self.assertEqual(
            result["audit_scorecard"]["summary"]["independent_audit_complete"],
            result["audit_packets"]["summary"]["independent_audit_complete"],
        )
        self.assertGreaterEqual(len(result["audit_scorecard"]["categories"]), 5)
        self.assertTrue(any(item["category_id"] == "paper_live_boundary" for item in result["audit_scorecard"]["categories"]))
        self.assertTrue(any(item["category_id"] == "audit_feedback_loop" for item in result["audit_scorecard"]["categories"]))
        self.assertGreaterEqual(result["audit_scorecard"]["summary"]["local_self_check_score"], 99)
        if result["audit_packets"]["summary"]["independent_audit_complete"]:
            self.assertFalse(
                any(item["action"] == "Run independent 5h GUI audit" for item in result["audit_scorecard"]["repair_queue"])
            )
            if result["audit_packets"]["summary"]["required_missing"] == 0:
                repair_actions = {item["action"] for item in result["audit_scorecard"]["repair_queue"]}
                self.assertNotIn("Attach audit findings to next optimization round", repair_actions)
                self.assertNotIn("Review linked audit packets during next audit", repair_actions)
        else:
            self.assertTrue(any(item["priority"] == "P0" for item in result["audit_scorecard"]["repair_queue"]))
        self.assertEqual(result["operator_timeline"]["stage"], "operator_timeline")
        self.assertGreaterEqual(len(result["operator_timeline"]["events"]), 6)
        self.assertTrue(any(item["event_id"] == "audit_repair_queue" for item in result["operator_timeline"]["events"]))
        self.assertTrue(any(item["event_id"] == "live_handoff" and item["status"] == "blocked" for item in result["operator_timeline"]["events"]))
        self.assertEqual(result["run_history"]["stage"], "gui_run_history")
        self.assertEqual(result["run_history"]["storage_key"], "quant_robot.gui.run_history.v1")
        self.assertGreaterEqual(result["run_history"]["max_entries"], 20)
        self.assertEqual(result["execution_receipts"]["stage"], "gui_execution_receipts")
        self.assertEqual(result["execution_receipts"]["storage_key"], "quant_robot.gui.execution_receipts.v1")
        self.assertGreaterEqual(result["execution_receipts"]["max_entries"], 20)
        receipt_workflows = {item["workflow_id"] for item in result["execution_receipts"]["capture_events"]}
        self.assertIn("research_backtest", receipt_workflows)
        self.assertIn("signal_snapshot", receipt_workflows)
        self.assertIn("paper_simulation", receipt_workflows)
        self.assertEqual(result["audit_packets"]["stage"], "gui_audit_packets")
        self.assertGreaterEqual(result["audit_packets"]["summary"]["tracked_packets"], 4)
        self.assertTrue(any(item["packet_id"] == "independent_gui_audit" for item in result["audit_packets"]["rows"]))
        self.assertTrue(any(item["packet_id"] == "project_audit" for item in result["audit_packets"]["rows"]))
        self.assertTrue(any(item["packet_id"] == "promotion_review_packet" for item in result["audit_packets"]["rows"]))
        self.assertTrue(any("run_gui_control_center_audit.py" in item["command"] for item in result["audit_packets"]["rows"]))
        self.assertTrue(
            any(
                item["packet_id"] == "browser_smoke" and "run_gui_browser_smoke.py" in item["command"]
                for item in result["audit_packets"]["rows"]
            )
        )
        self.assertEqual(result["audit_feedback"]["stage"], "gui_audit_feedback")
        self.assertIn(result["audit_feedback"]["status"], {"packet_present", "packet_missing", "packet_invalid"})
        self.assertIn("required_missing_audit_packets", result["audit_feedback"]["summary"])
        self.assertIn("next_action_count", result["audit_feedback"]["summary"])
        self.assertEqual(result["audit_iteration_plan"]["stage"], "gui_audit_iteration_plan")
        self.assertIn("active_actions", result["audit_iteration_plan"]["summary"])
        self.assertIn("source", result["audit_iteration_plan"]["summary"])
        self.assertGreaterEqual(len(result["audit_iteration_plan"]["rows"]), 1)
        self.assertTrue(all(item.get("verification_command") for item in result["audit_iteration_plan"]["rows"]))
        self.assertTrue(all(item.get("acceptance_evidence") for item in result["audit_iteration_plan"]["rows"]))
        self.assertTrue(
            any(
                item["action_id"] == "live_boundary_guard"
                and item["status"] == "blocked_expected"
                and "No broker connection" in item["acceptance_evidence"]
                for item in result["audit_iteration_plan"]["rows"]
            )
        )
        self.assertEqual(result["round_checkpoint_report"]["stage"], "gui_round_checkpoint_report")
        self.assertEqual(result["round_checkpoint_report"]["summary"]["cadence_rounds"], 5)
        self.assertIn("current_round", result["round_checkpoint_report"]["summary"])
        self.assertIn("next_review_trigger", result["round_checkpoint_report"]["summary"])
        self.assertIn("flow_plan", result["round_checkpoint_report"])
        self.assertTrue(result["round_checkpoint_report"]["flow_plan"]["next_steps"])
        self.assertEqual(result["audit_scheduler"]["stage"], "gui_audit_scheduler")
        self.assertEqual(result["audit_scheduler"]["summary"]["automation_id"], "gui-5h")
        self.assertEqual(result["audit_scheduler"]["summary"]["cadence_hours"], 5)
        self.assertEqual(result["audit_scheduler"]["summary"]["cadence_rounds"], 5)
        self.assertEqual(result["audit_scheduler"]["summary"]["current_round"], result["operation_ledger"]["summary"]["entry_count"])
        self.assertIn("rounds_until_next_audit", result["audit_scheduler"]["summary"])
        self.assertIn("next_round_audit_due_status", result["audit_scheduler"]["summary"])
        self.assertIn("next_report_required", result["audit_scheduler"]["summary"])
        self.assertIn("next_flow_plan_required", result["audit_scheduler"]["summary"])
        self.assertIn(result["audit_scheduler"]["summary"]["status"], {"active", "missing", "paused", "unknown"})
        self.assertIn("last_audit_age_hours", result["audit_scheduler"]["summary"])
        self.assertIn("next_due_status", result["audit_scheduler"]["summary"])
        scheduler_row_ids = {item["check_id"] for item in result["audit_scheduler"]["rows"]}
        self.assertIn("automation_config", scheduler_row_ids)
        self.assertIn("round_cadence", scheduler_row_ids)
        self.assertIn("last_audit_packet", scheduler_row_ids)
        self.assertIn("next_due", scheduler_row_ids)
        self.assertIn("next_flow_plan", scheduler_row_ids)
        self.assertIn("safety_boundary", scheduler_row_ids)
        self.assertTrue(any(item["kind"] == "logs" for item in result["report_links"]))
        self.assertTrue(any(item["kind"] == "audit_packet" for item in result["report_links"]))
        self.assertEqual(result["workspace_sync"]["stage"], "gui_workspace_sync")
        self.assertIn(result["workspace_sync"]["summary"]["status"], {"clean", "dirty", "unknown"})
        self.assertIn("current_branch", result["workspace_sync"]["summary"])
        self.assertIn("upstream_sync", result["workspace_sync"]["summary"])
        self.assertIn("head", result["workspace_sync"]["summary"])
        sync_row_ids = {item["check_id"] for item in result["workspace_sync"]["rows"]}
        self.assertIn("current_branch", sync_row_ids)
        self.assertIn("worktree", sync_row_ids)
        self.assertIn("upstream_sync", sync_row_ids)
        self.assertIn("safe_sync_policy", sync_row_ids)
        self.assertIn("publish_command", sync_row_ids)
        self.assertEqual(result["process_monitor"]["stage"], "gui_process_monitor")
        self.assertIn(result["process_monitor"]["summary"]["status"], {"observing", "unknown"})
        self.assertIn("current_pid", result["process_monitor"]["summary"])
        self.assertIn("related_processes", result["process_monitor"]["summary"])
        self.assertFalse(result["process_monitor"]["summary"]["live_trading_allowed"])
        process_row_ids = {item["check_id"] for item in result["process_monitor"]["rows"]}
        self.assertIn("current_process", process_row_ids)
        self.assertEqual(result["run_queue"]["active"]["workflow_id"], "research_backtest")
        self.assertGreaterEqual(result["run_queue"]["summary"]["pending"], 1)

    def test_workspace_sync_preserves_git_porcelain_leading_status_space(self):
        from quant_robot.gui.control_center import _parse_git_status_paths

        paths = _parse_git_status_paths(
            " M scripts/run_gui_browser_smoke.py\n"
            "M  src/quant_robot/gui/control_center.py\n"
            "?? tests/unit/test_gui.py\n"
        )

        self.assertEqual(
            paths,
            [
                "scripts/run_gui_browser_smoke.py",
                "src/quant_robot/gui/control_center.py",
                "tests/unit/test_gui.py",
            ],
        )

    def test_process_monitor_normalizes_related_process_roles_without_live_permissions(self):
        from quant_robot.gui.control_center import _normalize_process_rows

        rows = _normalize_process_rows(
            [
                {
                    "ProcessId": 101,
                    "Name": "python.exe",
                    "CommandLine": "python scripts\\run_gui.py --host 127.0.0.1 --port 8765",
                    "CreationDate": "20260628083000.000000+480",
                },
                {
                    "ProcessId": 202,
                    "Name": "python.exe",
                    "CommandLine": "python scripts\\run_gui_browser_smoke.py --base-url http://127.0.0.1:8765",
                    "CreationDate": "",
                },
                {
                    "ProcessId": 303,
                    "Name": "python.exe",
                    "CommandLine": "python scripts\\run_project_audit.py --json",
                    "CreationDate": "",
                },
            ],
            current_pid=101,
        )

        roles = {row["process_id"]: row["role"] for row in rows}
        self.assertEqual(roles[101], "gui_server")
        self.assertEqual(roles[202], "browser_smoke")
        self.assertEqual(roles[303], "project_audit")
        self.assertTrue(all(row["paper_only"] for row in rows))
        self.assertTrue(all(row["live_trading_allowed"] is False for row in rows))

    def test_audit_scheduler_reads_gui_heartbeat_config_and_audit_packet(self):
        from quant_robot.gui.control_center import build_control_center_snapshot
        from quant_robot.gui.operation_ledger import append_operation_ledger_entry

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit_dir = root / "data" / "reports" / "gui_control_center_audit"
            audit_dir.mkdir(parents=True)
            (audit_dir / "gui_control_center_audit.json").write_text(
                json.dumps(
                    {
                        "stage": "gui_control_center_independent_audit",
                        "generated_at": "2026-06-28T00:00:00+00:00",
                        "score": 96,
                        "max_score": 100,
                        "verdict": "clear",
                        "next_actions": [],
                    }
                ),
                encoding="utf-8",
            )
            for index in range(5):
                append_operation_ledger_entry(
                    repo_root=root,
                    workflow_id="gui_iteration",
                    label=f"GUI iteration round {index + 1}",
                    status="completed",
                    command="python -m unittest -v tests.unit.test_gui",
                    request={"round": index + 1},
                    result={"metrics": {"returncode": 0}},
                )
            codex_home = root / ".codex"
            automation_dir = codex_home / "automations" / "gui-5h"
            automation_dir.mkdir(parents=True)
            (automation_dir / "automation.toml").write_text(
                "\n".join(
                    [
                        'id = "gui-5h"',
                        'kind = "heartbeat"',
                        'name = "GUI control center 5h audit"',
                        'status = "ACTIVE"',
                        'rrule = "FREQ=HOURLY;INTERVAL=5"',
                        'target_thread_id = "thread-123"',
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"CODEX_HOME": str(codex_home)}):
                result = build_control_center_snapshot(repo_root=root)

        scheduler = result["audit_scheduler"]
        self.assertEqual(scheduler["summary"]["status"], "active")
        self.assertEqual(scheduler["summary"]["automation_kind"], "heartbeat")
        self.assertEqual(scheduler["summary"]["cadence_hours"], 5)
        self.assertEqual(scheduler["summary"]["cadence_rounds"], 5)
        self.assertEqual(scheduler["summary"]["current_round"], 5)
        self.assertEqual(scheduler["summary"]["rounds_until_next_audit"], 0)
        self.assertEqual(scheduler["summary"]["next_round_audit_due_status"], "due_now")
        self.assertTrue(scheduler["summary"]["next_report_required"])
        self.assertTrue(scheduler["summary"]["next_flow_plan_required"])
        self.assertEqual(scheduler["summary"]["last_audit_score"], 96)
        self.assertEqual(scheduler["summary"]["last_audit_verdict"], "clear")
        self.assertFalse(scheduler["summary"]["live_trading_allowed"])
        row_values = {row["check_id"]: row["value"] for row in scheduler["rows"]}
        self.assertIn("ACTIVE", row_values["automation_config"])
        self.assertIn("round 5", row_values["round_cadence"])
        self.assertIn("96 / 100", row_values["last_audit_packet"])
        self.assertIn("audit report + next flow plan", row_values["next_flow_plan"])
        self.assertIn("Research-to-paper only", row_values["safety_boundary"])

    def test_audit_scheduler_paused_heartbeat_keeps_round_cadence_primary(self):
        from quant_robot.gui.control_center import _audit_scheduler_next_action

        action = _audit_scheduler_next_action("paused", "on_schedule")

        self.assertIn("5-round audit cadence", action)
        self.assertIn("time-based fallback", action)

    def test_control_verification_runner_allows_only_registered_local_gates(self):
        from quant_robot.gui.control_center import build_verification_runner_snapshot, run_verification_gate

        runner = build_verification_runner_snapshot()
        allowed_ids = {row["gate_id"] for row in runner["rows"]}

        self.assertEqual(runner["stage"], "gui_verification_runner")
        self.assertIn("gui_compile", allowed_ids)
        self.assertFalse(runner["summary"]["live_trading_allowed"])
        self.assertTrue(all(row["allowed"] for row in runner["rows"]))

        result = run_verification_gate("gui_compile", repo_root=Path.cwd())

        self.assertEqual(result["stage"], "gui_verification_result")
        self.assertEqual(result["gate_id"], "gui_compile")
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["returncode"], 0)
        self.assertFalse(result["safety"]["live_trading_allowed"])

        rejected = run_verification_gate("live_trading", repo_root=Path.cwd())

        self.assertEqual(rejected["status"], "blocked")
        self.assertEqual(rejected["returncode"], None)
        self.assertFalse(rejected["safety"]["live_trading_allowed"])

    def test_operation_ledger_records_lightweight_safe_workflow_receipts(self):
        from quant_robot.gui.control_center import build_control_center_snapshot
        from quant_robot.gui.operation_ledger import append_operation_ledger_entry, build_operation_ledger_snapshot

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            entry = append_operation_ledger_entry(
                repo_root=root,
                workflow_id="research_backtest",
                label="Run research backtest",
                status="completed",
                command="GET /api/research?market=CN_ETF&factor=momentum_2",
                request={"market": "CN_ETF", "factor_name": "momentum_2", "top_n": 2},
                result={
                    "stage": "gui_research_result",
                    "metrics": {
                        "total_return": 0.1234,
                        "annualized_return": 0.231,
                        "sharpe": 1.87,
                        "max_drawdown": -0.18,
                        "win_rate": 0.58,
                    },
                },
            )
            snapshot = build_operation_ledger_snapshot(repo_root=root)
            control = build_control_center_snapshot(repo_root=root)

        self.assertEqual(entry["workflow_id"], "research_backtest")
        self.assertEqual(entry["status"], "completed")
        self.assertFalse(entry["safety"]["live_trading_allowed"])
        self.assertFalse(entry["safety"]["order_placement_allowed"])
        self.assertIn("sharpe=1.87", entry["metric_summary"])
        self.assertEqual(snapshot["stage"], "gui_operation_ledger")
        self.assertEqual(snapshot["summary"]["entry_count"], 1)
        self.assertEqual(snapshot["summary"]["latest_workflow_id"], "research_backtest")
        self.assertFalse(snapshot["summary"]["live_trading_allowed"])
        self.assertTrue(snapshot["summary"]["path"].endswith("data/reports/gui_operation_ledger/gui_operation_ledger.json"))
        self.assertEqual(snapshot["rows"][0]["workflow_id"], "research_backtest")
        self.assertEqual(snapshot["rows"][0]["request"]["factor_name"], "momentum_2")
        self.assertEqual(snapshot["rows"][0]["request"]["top_n"], 2)
        self.assertEqual(control["operation_ledger"]["stage"], "gui_operation_ledger")
        self.assertEqual(control["operation_ledger"]["summary"]["latest_workflow_id"], "research_backtest")

    def test_ledger_evidence_distinguishes_current_from_stale_server_receipts(self):
        from quant_robot.gui.control_center import build_control_center_snapshot
        from quant_robot.gui.operation_ledger import append_operation_ledger_entry

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            initial = build_control_center_snapshot(repo_root=root)
            workflow_by_id = {item["workflow_id"]: item for item in initial["workflows"]}
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="paper_simulation",
                label="Run local paper simulation",
                status="completed",
                command="GET /api/paper?market=CN_ETF&factor=old_factor&top_n=1",
                request={"market": "CN_ETF", "factor_name": "old_factor", "top_n": 1},
                result={"stage": "gui_paper_simulation", "metrics": {"ending_equity": 99800}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="research_backtest",
                label="Run research backtest",
                status="completed",
                command="GET /api/research?top_n=2&factor=momentum_2&market=CN_ETF",
                request=workflow_by_id["research_backtest"]["request"],
                result={"stage": "gui_research_result", "metrics": {"sharpe": 1.87}},
            )

            result = build_control_center_snapshot(repo_root=root)

        evidence = result["ledger_evidence"]
        rows = {item["workflow_id"]: item for item in evidence["rows"]}
        self.assertEqual(evidence["stage"], "gui_ledger_evidence")
        self.assertEqual(rows["research_backtest"]["freshness"], "current")
        self.assertTrue(rows["research_backtest"]["matches_current_command"])
        self.assertTrue(rows["research_backtest"]["matches_current_request"])
        self.assertNotEqual(rows["research_backtest"]["latest_command"], rows["research_backtest"]["current_command"])
        self.assertEqual(rows["research_backtest"]["current_request"]["factor_name"], "momentum_2")
        self.assertEqual(rows["paper_simulation"]["freshness"], "stale")
        self.assertFalse(rows["paper_simulation"]["matches_current_command"])
        self.assertFalse(rows["paper_simulation"]["matches_current_request"])
        self.assertIn("Run local paper simulation", rows["paper_simulation"]["next_action"])
        self.assertEqual(evidence["summary"]["current_receipts"], 1)
        self.assertGreaterEqual(evidence["summary"]["missing_or_stale"], 2)
        self.assertFalse(evidence["summary"]["live_trading_allowed"])
        action_center = result["action_center"]
        self.assertEqual(action_center["stage"], "gui_action_center")
        action_ids = {item["action_id"] for item in action_center["rows"]}
        self.assertIn("refresh_paper_simulation", action_ids)
        self.assertNotIn("enable_live_trading", action_ids)
        action_by_id = {item["action_id"]: item for item in action_center["rows"]}
        self.assertTrue(action_by_id["refresh_paper_simulation"]["runnable"])
        self.assertEqual(action_by_id["refresh_paper_simulation"]["workflow_id"], "paper_simulation")
        self.assertFalse(action_center["summary"]["live_trading_allowed"])

    def test_control_center_uses_independent_audit_packet_as_next_optimization_input(self):
        from quant_robot.gui.control_center import build_control_center_snapshot

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            packet_dir = root / "data" / "reports" / "gui_control_center_audit"
            packet_dir.mkdir(parents=True)
            (packet_dir / "gui_control_center_audit.json").write_text(
                json.dumps(
                    {
                        "stage": "gui_control_center_independent_audit",
                        "generated_at": "2026-06-28T00:00:00+00:00",
                        "score": 88,
                        "max_score": 100,
                        "verdict": "needs_repair",
                        "next_actions": [
                            {
                                "priority": "P1",
                                "action": "Tighten audit feedback loop",
                                "reason": "Use packet-driven fixes as the next GUI optimization queue.",
                            },
                            {
                                "priority": "P1",
                                "action": "Tighten audit feedback loop",
                                "reason": "Duplicate packet actions should not clutter the GUI queue.",
                            }
                        ],
                        "safety": {"live_trading_allowed": False},
                    }
                ),
                encoding="utf-8",
            )

            result = build_control_center_snapshot(repo_root=root)

        self.assertTrue(result["audit_scorecard"]["summary"]["independent_audit_complete"])
        self.assertEqual(result["audit_scorecard"]["summary"]["score_source"], "independent_gui_audit_packet")
        self.assertEqual(result["audit_scorecard"]["summary"]["independent_audit_score"], 88)
        self.assertEqual(result["audit_scorecard"]["summary"]["independent_audit_verdict"], "needs_repair")
        self.assertEqual(result["audit_feedback"]["status"], "packet_present")
        self.assertEqual(result["audit_feedback"]["summary"]["score"], 88)
        self.assertEqual(result["audit_feedback"]["summary"]["verdict"], "needs_repair")
        self.assertTrue(
            any(item["action"] == "Tighten audit feedback loop" for item in result["audit_feedback"]["next_actions"])
        )
        self.assertEqual(result["audit_iteration_plan"]["summary"]["source"], "independent_gui_audit_packet")
        self.assertEqual(result["audit_iteration_plan"]["summary"]["audit_score"], 88)
        self.assertTrue(
            any(
                item["action"] == "Tighten audit feedback loop"
                and item["status"] == "queued"
                and "next GUI optimization queue" in item["acceptance_evidence"]
                for item in result["audit_iteration_plan"]["rows"]
            )
        )
        feedback_actions = [item["action"] for item in result["audit_feedback"]["next_actions"]]
        self.assertEqual(feedback_actions.count("Tighten audit feedback loop"), 1)
        self.assertFalse(
            any(item["action"] == "Run independent 5h GUI audit" for item in result["audit_scorecard"]["repair_queue"])
        )

    def test_gui_control_center_audit_script_writes_packet(self):
        from scripts.run_gui_control_center_audit import run_gui_control_center_audit

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "gui_control_center_audit"

            packet = run_gui_control_center_audit(repo_root=Path.cwd(), output_dir=output_dir)

            self.assertEqual(packet["stage"], "gui_control_center_independent_audit")
            self.assertGreaterEqual(packet["score"], 1)
            self.assertGreaterEqual(packet["max_score"], packet["score"])
            self.assertIn("scorecard", packet)
            self.assertIn("audit_packets", packet)
            self.assertIn("audit_iteration_plan", packet)
            self.assertIn("round_checkpoint_report", packet)
            self.assertIn("next_actions", packet)
            category_ids = {item["category_id"] for item in packet["scorecard"]["categories"]}
            self.assertIn("audit_feedback_loop", category_ids)
            action_names = {item["action"] for item in packet["next_actions"]}
            self.assertNotIn("Attach audit findings to next optimization round", action_names)
            self.assertNotIn("Review linked audit packets during next audit", action_names)
            self.assertEqual(packet["audit_iteration_plan"]["summary"]["audit_score"], packet["score"])
            self.assertEqual(packet["audit_iteration_plan"]["summary"]["verdict"], packet["verdict"])
            if not packet["next_actions"]:
                self.assertEqual(packet["audit_iteration_plan"]["summary"]["active_actions"], 0)
            checkpoint = packet["round_checkpoint_report"]
            self.assertEqual(checkpoint["stage"], "gui_round_checkpoint_report")
            self.assertEqual(checkpoint["summary"]["cadence_rounds"], 5)
            self.assertIn("completed_rounds", checkpoint["summary"])
            self.assertLessEqual(len(checkpoint["recent_work"]), 5)
            self.assertGreaterEqual(len(checkpoint["flow_plan"]["next_steps"]), 1)
            self.assertIn("verification_plan", checkpoint["flow_plan"])
            self.assertFalse(packet["safety"]["live_trading_allowed"])
            self.assertTrue((output_dir / "gui_control_center_audit.json").exists())
            self.assertTrue((output_dir / "gui_control_center_audit.md").exists())
            markdown = (output_dir / "gui_control_center_audit.md").read_text(encoding="utf-8")
            self.assertIn("GUI Control Center Independent Audit", markdown)
            self.assertIn("Five-Round Checkpoint Report", markdown)
            self.assertIn("Next Flow Plan", markdown)
            self.assertIn("Audit Iteration Plan", markdown)
            self.assertIn("Research-to-paper only", markdown)

    def test_gui_control_center_audit_normalizes_iteration_plan_when_old_findings_clear(self):
        from scripts.run_gui_control_center_audit import run_gui_control_center_audit

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            audit_dir = root / "data" / "reports" / "gui_control_center_audit"
            audit_dir.mkdir(parents=True)
            (audit_dir / "gui_control_center_audit.json").write_text(
                json.dumps(
                    {
                        "stage": "gui_control_center_independent_audit",
                        "generated_at": "2026-06-28T00:00:00+00:00",
                        "score": 92,
                        "max_score": 100,
                        "verdict": "needs_repair",
                        "next_actions": [
                            {
                                "priority": "P1",
                                "action": "Attach audit findings to next optimization round",
                                "reason": "The old generic finding should be treated as closed.",
                            },
                            {
                                "priority": "P2",
                                "action": "Review linked audit packets during next audit",
                                "reason": "The old packet-review finding should be treated as closed.",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            for relative in [
                "data/reports/project_audit/project_audit.json",
                "data/reports/gui_browser_smoke/gui_browser_smoke.json",
            ]:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("{}", encoding="utf-8")

            output_dir = root / "data" / "reports" / "gui_control_center_audit_next"
            packet = run_gui_control_center_audit(repo_root=root, output_dir=output_dir)

        self.assertEqual(packet["verdict"], "clear")
        self.assertEqual(packet["next_actions"], [])
        self.assertEqual(packet["audit_iteration_plan"]["summary"]["audit_score"], packet["score"])
        self.assertEqual(packet["audit_iteration_plan"]["summary"]["verdict"], "clear")
        self.assertEqual(packet["audit_iteration_plan"]["summary"]["active_actions"], 0)
        self.assertEqual(
            [row["action_id"] for row in packet["audit_iteration_plan"]["rows"]],
            ["live_boundary_guard"],
        )

    def test_gui_browser_smoke_script_writes_evidence_packet(self):
        from scripts.run_gui_browser_smoke import run_gui_browser_smoke

        server = ThreadingHTTPServer(("127.0.0.1", 0), create_gui_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_dir = Path(tmpdir) / "gui_browser_smoke"

                packet = run_gui_browser_smoke(base_url=base_url, output_dir=output_dir)

                self.assertEqual(packet["stage"], "gui_browser_smoke_evidence")
                self.assertEqual(packet["status"], "passed")
                self.assertEqual(packet["summary"]["failed"], 0)
                self.assertGreaterEqual(packet["summary"]["passed"], 5)
                check_ids = {row["check_id"] for row in packet["checks"]}
                self.assertIn("index_html", check_ids)
                self.assertIn("control_status_api", check_ids)
                self.assertIn("startup_health_panel", check_ids)
                self.assertIn("backtest_provenance_panel", check_ids)
                self.assertIn("backtest_gate_panel", check_ids)
                self.assertIn("paper_readiness_panel", check_ids)
                self.assertIn("result_evidence_panel", check_ids)
                self.assertIn("workflow_trace_panel", check_ids)
                self.assertIn("workspace_sync_panel", check_ids)
                self.assertIn("process_monitor_panel", check_ids)
                self.assertIn("active_operation_panel", check_ids)
                self.assertIn("operation_ledger_panel", check_ids)
                self.assertIn("audit_scheduler_panel", check_ids)
                self.assertIn("verification_runner_panel", check_ids)
                self.assertIn("audit_feedback_panel", check_ids)
                self.assertIn("audit_iteration_plan_panel", check_ids)
                self.assertIn("responsive_contract", check_ids)
                self.assertIn("live_boundary", check_ids)
                self.assertFalse(packet["safety"]["live_trading_allowed"])
                self.assertTrue((output_dir / "gui_browser_smoke.json").exists())
                self.assertTrue((output_dir / "gui_browser_smoke.md").exists())
                markdown = (output_dir / "gui_browser_smoke.md").read_text(encoding="utf-8")
                self.assertIn("GUI Browser Smoke Evidence", markdown)
                self.assertIn("Research-to-paper only", markdown)
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

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
                        "paper_profile": {"profile_id": "cap60_guard12_cd3", "risk_tier": "aggressive_growth"},
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
        self.assertEqual(result["paper_profile"]["profile_id"], "cap60_guard12_cd3")
        self.assertEqual(result["paper_profile"]["risk_tier"], "aggressive_growth")
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
                        "policy": {
                            "primary_risk_tier": "capital_preservation",
                            "risk_tiers": [{"tier_id": "aggressive_growth", "max_drawdown_limit": -0.3}],
                        },
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
        self.assertEqual(result["policy"]["risk_tiers"][0]["tier_id"], "aggressive_growth")
        self.assertEqual(result["next_actions"][0]["action"], "run_constrained_candidate_search")

    def test_risk_candidate_snapshot_prefers_constrained_pack_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy_pack = root / "legacy" / "risk_candidate_pack.json"
            constrained_pack = root / "constrained" / "risk_candidate_pack.json"
            legacy_pack.parent.mkdir(parents=True)
            constrained_pack.parent.mkdir(parents=True)
            legacy_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_1_risk_candidate_selector",
                        "selection_status": "no_risk_eligible_candidate",
                        "summary": {"candidates": 270, "risk_eligible_candidates": 0},
                        "candidates": [],
                    }
                ),
                encoding="utf-8",
            )
            constrained_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_4_risk_tier_policy",
                        "selection_status": "risk_tier_candidate_selected",
                        "summary": {"candidates": 48, "risk_eligible_candidates": 0, "tier_eligible_candidates": 1},
                        "policy": {"risk_tiers": [{"tier_id": "aggressive_growth", "max_drawdown_limit": -0.3}]},
                        "selected_candidate": {"case_id": "case_aggressive", "risk_tier": "aggressive_growth"},
                        "candidates": [{"case_id": "case_aggressive", "risk_tier": "aggressive_growth"}],
                    }
                ),
                encoding="utf-8",
            )

            with patch("quant_robot.gui.research_service.DEFAULT_RISK_CANDIDATE_PACK", legacy_pack), patch(
                "quant_robot.gui.research_service.DEFAULT_CONSTRAINED_RISK_CANDIDATE_PACK",
                constrained_pack,
                create=True,
            ):
                result = build_risk_candidate_snapshot()

        self.assertEqual(result["source_path"], str(constrained_pack))
        self.assertEqual(result["selection_status"], "risk_tier_candidate_selected")
        self.assertEqual(result["selected_candidate"]["risk_tier"], "aggressive_growth")

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
                        "policy": {
                            "primary_risk_tier": "capital_preservation",
                            "risk_tiers": [{"tier_id": "aggressive_growth", "max_drawdown_limit": -0.3}],
                        },
                        "selected_profile": None,
                        "attempts": [{"case_id": "case_a", "profile_id": "cap46", "paper_sharpe": 0.41, "risk_tier": "aggressive_growth"}],
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
        self.assertEqual(result["attempts"][0]["risk_tier"], "aggressive_growth")

    def test_profile_observation_snapshot_exposes_stop_rules_and_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "profile_observation_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_6_profile_observation_ledger",
                        "decision": {
                            "observation_status": "stopped",
                            "paper_observation_allowed": False,
                            "stop_reasons": ["signal_data_stale"],
                        },
                        "summary": {"stop_count": 1, "warning_count": 0},
                        "paper_profile": {"profile_id": "cap60_guard12_cd3", "risk_tier": "aggressive_growth"},
                        "stop_rules": [{"rule_id": "signal_data_stale", "status": "stop"}],
                        "ledger": [{"case_id": "case_a", "profile_id": "cap60_guard12_cd3", "signal_age_days": 23}],
                        "next_actions": [{"action": "refresh_tushare_recent_data", "reason": "stale"}],
                    }
                ),
                encoding="utf-8",
            )

            result = build_profile_observation_snapshot(profile_observation_pack=pack)

        self.assertEqual(result["stage"], "gui_profile_observation")
        self.assertTrue(result["artifact_present"])
        self.assertEqual(result["decision"]["observation_status"], "stopped")
        self.assertEqual(result["paper_profile"]["risk_tier"], "aggressive_growth")
        self.assertEqual(result["stop_rules"][0]["rule_id"], "signal_data_stale")
        self.assertEqual(result["ledger"][0]["signal_age_days"], 23)
        self.assertEqual(result["next_actions"][0]["action"], "refresh_tushare_recent_data")

    def test_recent_data_refresh_snapshot_exposes_token_gate_and_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "recent_data_refresh_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_7_tushare_recent_data_refresh",
                        "status": "blocked",
                        "mode": "dry_run",
                        "will_download": False,
                        "target_window": {
                            "start_date": "2026-05-23",
                            "end_date": "2026-06-14",
                            "signal_date": "2026-05-22",
                        },
                        "decision": {
                            "signal_data_stale_cleared": False,
                            "recent_data_ready": False,
                            "blockers": ["TUSHARE_TOKEN is not set"],
                        },
                        "coverage": {
                            "coverage_status": "missing",
                            "processed_rows": 0,
                            "latest_data_date": None,
                        },
                        "next_actions": [{"action": "set_tushare_token_env", "reason": "token"}],
                    }
                ),
                encoding="utf-8",
            )

            result = build_recent_data_refresh_snapshot(recent_data_refresh_pack=pack)

        self.assertEqual(result["stage"], "gui_recent_data_refresh")
        self.assertTrue(result["artifact_present"])
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["target_window"]["start_date"], "2026-05-23")
        self.assertFalse(result["decision"]["signal_data_stale_cleared"])
        self.assertEqual(result["decision"]["blockers"][0], "TUSHARE_TOKEN is not set")
        self.assertEqual(result["coverage"]["coverage_status"], "missing")
        self.assertEqual(result["next_actions"][0]["action"], "set_tushare_token_env")
        self.assertFalse(result["live_boundary_allowed"])

    def test_post_refresh_replay_snapshot_exposes_downstream_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "post_refresh_replay_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_8_post_refresh_replay",
                        "status": "replay_blocked",
                        "recent_data_refresh": {"status": "completed", "source": "tushare-fixture"},
                        "daily_ops": {"status": "paper_ready", "paper_trading_allowed": True},
                        "profile_observation": {
                            "observation_status": "stopped",
                            "paper_observation_allowed": False,
                            "stop_reasons": ["minimum_fills_observed"],
                        },
                        "decision": {
                            "recent_data_ready": True,
                            "daily_ops_paper_allowed": True,
                            "profile_observation_allowed": False,
                            "post_refresh_replay_allowed": False,
                            "blockers": ["minimum_fills_observed"],
                        },
                        "next_actions": [{"action": "inspect_post_refresh_daily_ops_or_observation"}],
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )

            result = build_post_refresh_replay_snapshot(post_refresh_replay_pack=pack)

        self.assertEqual(result["stage"], "gui_post_refresh_replay")
        self.assertTrue(result["artifact_present"])
        self.assertEqual(result["status"], "replay_blocked")
        self.assertEqual(result["recent_data_refresh"]["status"], "completed")
        self.assertTrue(result["daily_ops"]["paper_trading_allowed"])
        self.assertEqual(result["decision"]["blockers"], ["minimum_fills_observed"])
        self.assertFalse(result["live_boundary_allowed"])

    def test_observation_sufficiency_snapshot_exposes_window_recommendation(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "observation_sufficiency_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_9_observation_sufficiency",
                        "status": "needs_more_observation_data",
                        "fills": {"observed_fills": 2, "required_fills": 20, "fill_deficit": 18},
                        "recommendation": {
                            "priority": "extend_recent_data_window",
                            "estimated_total_observation_days": 170,
                            "suggested_start_date": "2025-12-26",
                            "suggested_end_date": "2026-06-13",
                            "threshold_relaxation_allowed": False,
                        },
                        "decision": {"blockers": ["minimum_fills_observed"], "observation_sufficiency_cleared": False},
                        "next_actions": [{"action": "extend_recent_refresh_window"}],
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )

            result = build_observation_sufficiency_snapshot(observation_sufficiency_pack=pack)

        self.assertEqual(result["stage"], "gui_observation_sufficiency")
        self.assertEqual(result["status"], "needs_more_observation_data")
        self.assertEqual(result["fills"]["fill_deficit"], 18)
        self.assertEqual(result["recommendation"]["suggested_start_date"], "2025-12-26")
        self.assertFalse(result["recommendation"]["threshold_relaxation_allowed"])
        self.assertEqual(result["next_actions"][0]["action"], "extend_recent_refresh_window")

    def test_expanded_observation_replay_snapshot_exposes_final_sample_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "expanded_observation_replay_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_10_expanded_observation_replay",
                        "status": "expanded_replay_blocked",
                        "window": {"start_date": "2025-12-26", "end_date": "2026-06-13"},
                        "recent_data_refresh": {"status": "completed", "coverage": {"processed_rows": 340}},
                        "final_observation_sufficiency": {
                            "status": "needs_more_observation_data",
                            "fills": {"observed_fills": 15, "required_fills": 20, "fill_deficit": 5},
                        },
                        "decision": {"expanded_observation_cleared": False, "blockers": ["minimum_fills_observed"]},
                        "next_actions": [{"action": "review_expanded_observation_blockers"}],
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )

            result = build_expanded_observation_replay_snapshot(expanded_observation_replay_pack=pack)

        self.assertEqual(result["stage"], "gui_expanded_observation_replay")
        self.assertEqual(result["status"], "expanded_replay_blocked")
        self.assertEqual(result["window"]["start_date"], "2025-12-26")
        self.assertEqual(result["final_observation_sufficiency"]["fills"]["observed_fills"], 15)
        self.assertEqual(result["decision"]["blockers"], ["minimum_fills_observed"])
        self.assertFalse(result["live_boundary_allowed"])

    def test_iterative_observation_expansion_snapshot_exposes_rounds_and_final_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "iterative_observation_expansion_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_11_iterative_observation_expansion",
                        "status": "completed",
                        "round_count": 2,
                        "max_rounds": 3,
                        "rounds": [
                            {
                                "round": 1,
                                "expanded_observation_replay": {
                                    "status": "expanded_replay_blocked",
                                    "window": {"start_date": "2025-12-26", "end_date": "2026-06-13"},
                                    "final_observation_sufficiency": {
                                        "fills": {"observed_fills": 15, "required_fills": 20, "fill_deficit": 5}
                                    },
                                },
                            },
                            {
                                "round": 2,
                                "expanded_observation_replay": {
                                    "status": "completed",
                                    "window": {"start_date": "2025-11-07", "end_date": "2026-06-10"},
                                    "final_observation_sufficiency": {
                                        "fills": {"observed_fills": 29, "required_fills": 20, "fill_deficit": 0}
                                    },
                                },
                            },
                        ],
                        "final_observation_sufficiency": {
                            "status": "sufficient",
                            "fills": {"observed_fills": 29, "required_fills": 20, "fill_deficit": 0},
                        },
                        "decision": {"iterative_observation_cleared": True, "blockers": []},
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )

            result = build_iterative_observation_expansion_snapshot(iterative_observation_expansion_pack=pack)

        self.assertEqual(result["stage"], "gui_iterative_observation_expansion")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["round_count"], 2)
        self.assertTrue(result["decision"]["iterative_observation_cleared"])
        self.assertEqual(result["final_observation_sufficiency"]["fills"]["observed_fills"], 29)
        self.assertEqual(result["rounds"][1]["expanded_observation_replay"]["window"]["start_date"], "2025-11-07")
        self.assertFalse(result["live_boundary_allowed"])

    def test_tushare_activation_gate_snapshot_exposes_stage_ledger_and_final_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack = Path(tmp) / "tushare_activation_gate_pack.json"
            pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_12_tushare_activation_gate",
                        "status": "paper_observation_ready",
                        "mode": "execute",
                        "source": "tushare-fixture",
                        "market": "CN_ETF",
                        "readiness": {"ready": True, "missing": []},
                        "recent_data_refresh": {
                            "status": "completed",
                            "coverage": {"processed_rows": 46, "coverage_status": "pass"},
                        },
                        "post_refresh_replay": {"status": "completed"},
                        "observation_sufficiency": {
                            "status": "needs_more_observation_data",
                            "fills": {"observed_fills": 15, "required_fills": 20, "fill_deficit": 5},
                        },
                        "iterative_observation_expansion": {"status": "completed", "round_count": 2},
                        "final_observation_sufficiency": {
                            "status": "sufficient",
                            "fills": {"observed_fills": 29, "required_fills": 20, "fill_deficit": 0},
                        },
                        "stage_ledger": [
                            {"stage": "recent_data_refresh", "status": "completed", "cleared": True},
                            {"stage": "post_refresh_replay", "status": "completed", "cleared": True},
                            {"stage": "observation_sufficiency", "status": "needs_more_observation_data", "cleared": False},
                            {"stage": "iterative_observation_expansion", "status": "completed", "cleared": True},
                        ],
                        "decision": {
                            "recent_data_ready": True,
                            "post_refresh_replay_allowed": True,
                            "observation_sufficiency_cleared": False,
                            "iterative_observation_cleared": True,
                            "paper_continuation_allowed": True,
                            "blockers": [],
                        },
                        "next_actions": [{"action": "continue_paper_observation_on_validated_window"}],
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )

            result = build_tushare_activation_gate_snapshot(tushare_activation_gate_pack=pack)

        self.assertEqual(result["stage"], "gui_tushare_activation_gate")
        self.assertEqual(result["status"], "paper_observation_ready")
        self.assertTrue(result["decision"]["paper_continuation_allowed"])
        self.assertEqual(result["final_observation_sufficiency"]["fills"]["observed_fills"], 29)
        self.assertEqual(result["stage_ledger"][3]["stage"], "iterative_observation_expansion")
        self.assertFalse(result["live_boundary_allowed"])

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
            self.assertIn("量化机器人本地中控台", html)
            self.assertIn('rel="icon"', html)
            self.assertIn('href="data:,"', html)
            self.assertIn("信号快照", html)
            self.assertIn("纸面模拟", html)
            self.assertIn("A股ETF", html)
            self.assertIn("决策风控", html)
            self.assertIn("项目作战台", html)
            self.assertIn("project-action-table", html)
            self.assertIn("factor-inventory-metrics", html)
            self.assertIn("factor-leaderboard-table", html)
            self.assertIn("ordinary-home-board", html)
            self.assertIn("ordinary-status-metrics", html)
            self.assertIn("ordinary-next-action", html)
            self.assertIn("ordinary-mainline-warning", html)
            self.assertIn("beginner-guide-board", html)
            self.assertIn("beginner-step-list", html)
            self.assertIn("beginner-primary-action", html)
            self.assertIn("beginner-help-text", html)
            self.assertIn("beginner-verdict-board", html)
            self.assertIn("beginner-safety-light", html)
            self.assertIn("beginner-verdict-reason", html)
            self.assertIn("beginner-next-button", html)
            self.assertIn("beginner-progress-board", html)
            self.assertIn("beginner-progress-status", html)
            self.assertIn("beginner-progress-steps", html)
            self.assertIn("beginner-progress-next", html)
            self.assertIn("beginner-progress-recovery", html)
            self.assertIn("beginner-data-trust-card", html)
            self.assertIn("data-beginner-progress-root", html)
            self.assertIn("data-beginner-recovery-root", html)
            self.assertIn("data-beginner-data-trust-root", html)
            self.assertIn("data-beginner-action", html)
            self.assertIn("data-beginner-target", html)
            self.assertIn("leaderboard-tab-primary", html)
            self.assertIn("leaderboard-tab-cn", html)
            self.assertIn("leaderboard-tab-all", html)
            self.assertIn("factor-leaderboard-explanation", html)
            self.assertIn("factor-beginner-explainer", html)
            self.assertIn("data-factor-beginner-root", html)
            self.assertIn("beginner-parameter-explainer", html)
            self.assertIn("beginner-parameter-summary", html)
            self.assertIn("beginner-parameter-rows", html)
            self.assertIn("data-beginner-parameter-root", html)
            self.assertIn("beginner-result-interpreter", html)
            self.assertIn("beginner-result-summary", html)
            self.assertIn("beginner-result-metrics", html)
            self.assertIn("beginner-result-rows", html)
            self.assertIn("data-beginner-result-root", html)
            self.assertIn("factor-glossary", html)
            self.assertIn("safe-run-modal", html)
            self.assertIn("safe-run-beginner-summary", html)
            self.assertIn("safe-run-outcome", html)
            self.assertIn("safe-run-risk-boundary", html)
            self.assertIn("safe-run-next-place", html)
            self.assertIn("safe-run-confirm", html)
            self.assertIn("因子资产总账", html)
            self.assertIn("Top20 因子排行榜", html)
            self.assertIn("operator-strip", html)
            self.assertIn("control-center-board", html)
            self.assertIn("量化机器人中控台", html)
            self.assertIn("办公室电脑作战台", html)
            self.assertIn("操作控制台", html)
            self.assertIn("运行队列", html)
            self.assertIn("下一步动作", html)
            self.assertIn("运行前检查", html)
            self.assertIn("当前回测", html)
            self.assertIn("模拟盘交接", html)
            self.assertIn("实盘边界", html)
            self.assertIn("data-console-action", html)
            self.assertIn("本地回测当前参数", html)
            self.assertIn("生成本地建议信号", html)
            self.assertIn("本地模拟盘回放", html)
            self.assertIn("GUI 编译检查", html)
            self.assertIn("项目安全审计", html)
            self.assertIn("同步预检", html)
            self.assertIn("control-work-status", html)
            self.assertIn("control-backtest-status", html)
            self.assertIn("control-run-queue", html)
            self.assertIn("control-action-center", html)
            self.assertIn("control-workflow-preflight", html)
            self.assertIn("control-operator-checklist", html)
            self.assertIn("control-execution-plan", html)
            self.assertIn("control-workflow-trace", html)
            self.assertIn("control-workspace-sync", html)
            self.assertIn("control-process-monitor", html)
            self.assertIn("control-active-operation", html)
            self.assertIn("control-operation-ledger", html)
            self.assertIn("control-trade-mode-control", html)
            self.assertIn("control-request-preview", html)
            self.assertIn("control-result-freshness", html)
            self.assertIn("control-ledger-evidence", html)
            self.assertIn("control-startup-health", html)
            self.assertIn("control-backtest-provenance", html)
            self.assertIn("control-backtest-gate", html)
            self.assertIn("control-readiness-matrix", html)
            self.assertIn("control-release-readiness", html)
            self.assertIn("control-audit-scorecard", html)
            self.assertIn("control-operator-timeline", html)
            self.assertIn("control-audit-repair-queue", html)
            self.assertIn("control-run-history", html)
            self.assertIn("control-execution-receipts", html)
            self.assertIn("control-audit-packets", html)
            self.assertIn("control-audit-feedback", html)
            self.assertIn("control-round-checkpoint-report", html)
            self.assertIn("control-audit-iteration-plan", html)
            self.assertIn("control-audit-scheduler", html)
            self.assertIn("control-method-steps", html)
            self.assertIn("control-result-slots", html)
            self.assertIn("control-result-evidence", html)
            self.assertIn("control-workflow-commands", html)
            self.assertIn("control-report-links", html)
            self.assertIn("control-verification-gates", html)
            self.assertIn("control-verification-runner", html)
            self.assertIn("control-safety-boundary", html)
            self.assertIn("control-audit-cadence", html)
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
            self.assertIn("execution-lag", html)
            self.assertIn("forward-horizon", html)
            self.assertIn("paper-max-market-weight", html)
            self.assertIn("paper-max-gross-exposure", html)
            self.assertIn("recent-data-refresh-status", html)
            self.assertIn("recent-data-refresh-action-table", html)
            self.assertIn("recent-data-refresh-coverage", html)
            self.assertIn("post-refresh-replay-status", html)
            self.assertIn("post-refresh-replay-action-table", html)
            self.assertIn("observation-sufficiency-status", html)
            self.assertIn("observation-sufficiency-action-table", html)
            self.assertIn("expanded-observation-replay-status", html)
            self.assertIn("expanded-observation-replay-action-table", html)
            self.assertIn("iterative-observation-expansion-status", html)
            self.assertIn("iterative-observation-expansion-round-table", html)
            self.assertIn("tushare-activation-gate-status", html)
            self.assertIn("tushare-activation-gate-ledger-table", html)
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
            self.assertIn("/api/risk/profile-observation", app_js)
            self.assertIn("/api/data/recent-refresh", app_js)
            self.assertIn("renderRecentDataRefresh", app_js)
            self.assertIn("/api/data/post-refresh-replay", app_js)
            self.assertIn("renderPostRefreshReplay", app_js)
            self.assertIn("/api/risk/observation-sufficiency", app_js)
            self.assertIn("renderObservationSufficiency", app_js)
            self.assertIn("/api/risk/expanded-observation-replay", app_js)
            self.assertIn("renderExpandedObservationReplay", app_js)
            self.assertIn("/api/risk/iterative-observation-expansion", app_js)
            self.assertIn("renderIterativeObservationExpansion", app_js)
            self.assertIn("/api/risk/tushare-activation-gate", app_js)
            self.assertIn("renderTushareActivationGate", app_js)
            self.assertIn("/api/factors/leaderboard", app_js)
            self.assertIn("renderFactorLeaderboard", app_js)
            self.assertIn("renderFactorBeginnerExplainer", app_js)
            self.assertIn("factorBeginnerMetric", app_js)
            self.assertIn("data-factor-beginner-jump", app_js)
            self.assertIn("renderBeginnerParameterExplainer", app_js)
            self.assertIn("beginnerParameterRows", app_js)
            self.assertIn("parameterPlainValue", app_js)
            self.assertIn("data-beginner-parameter-jump", app_js)
            self.assertIn("renderBeginnerResultInterpreter", app_js)
            self.assertIn("beginnerResultVerdict", app_js)
            self.assertIn("beginnerResultMetric", app_js)
            self.assertIn("data-beginner-result-jump", app_js)
            self.assertIn("renderOrdinaryHome", app_js)
            self.assertIn("renderFactorGlossary", app_js)
            self.assertIn("BEGINNER_STEPS", app_js)
            self.assertIn("beginnerVerdict", app_js)
            self.assertIn("renderBeginnerVerdict", app_js)
            self.assertIn("beginnerProgressState", app_js)
            self.assertIn("beginnerProgressStepRows", app_js)
            self.assertIn("beginnerProgressActionButtons", app_js)
            self.assertIn("beginnerProgressRecoveryRows", app_js)
            self.assertIn("renderBeginnerProgressRecovery", app_js)
            self.assertIn("beginnerDataTrustState", app_js)
            self.assertIn("beginnerDataTrustRows", app_js)
            self.assertIn("renderBeginnerDataTrust", app_js)
            self.assertIn("renderBeginnerProgress", app_js)
            self.assertIn("renderBeginnerGuide", app_js)
            self.assertIn("jumpToBeginnerTarget", app_js)
            self.assertIn("runBeginnerAction", app_js)
            self.assertIn("data-beginner-next", app_js)
            self.assertIn("data-beginner-progress-jump", app_js)
            self.assertIn("data-beginner-progress-action", app_js)
            self.assertIn("data-beginner-recovery-jump", app_js)
            self.assertIn("data-beginner-data-trust-jump", app_js)
            self.assertIn("beginner-progress-actions", app_js)
            self.assertIn("beginner-recovery-actions", app_js)
            self.assertIn("beginner-data-trust-actions", app_js)
            self.assertIn("[data-beginner-action]", app_js)
            self.assertIn("[data-beginner-target]", app_js)
            self.assertIn(".segmented-button[data-leaderboard-tab]", app_js)
            self.assertIn("workspace.scrollTo", app_js)
            self.assertIn("window.scrollTo", app_js)
            self.assertIn("getComputedStyle(workspace).overflowY", app_js)
            self.assertIn("document.scrollingElement", app_js)
            self.assertIn("scrollBehaviorForDistance", app_js)
            self.assertIn("setLeaderboardTab", app_js)
            self.assertIn("confirmSafeWorkflow", app_js)
            self.assertIn("safeWorkflowBeginnerSummary", app_js)
            self.assertIn("safeWorkflowPlainOutcome", app_js)
            self.assertIn("safeWorkflowNextPlace", app_js)
            self.assertIn("renderSafeWorkflowBeginnerSummary", app_js)
            self.assertIn("GLOSSARY_TERMS", app_js)
            self.assertIn("leaderboards", app_js)
            self.assertIn("risk_tier", app_js)
            self.assertIn("dailyPaperProfile", app_js)
            self.assertIn("dashboard-equity-source", app_js)
            self.assertIn("runStartupWorkflows", app_js)
            self.assertIn("/api/control/status", app_js)
            self.assertIn("renderControlCenter", app_js)
            self.assertIn("applyControlDefaults", app_js)
            self.assertIn("state.controlCenter?.form_defaults", app_js)
            self.assertIn('setValue("execution-lag"', app_js)
            self.assertIn('setValue("forward-horizon"', app_js)
            self.assertIn('setValue("paper-max-market-weight"', app_js)
            self.assertIn('setValue("paper-max-gross-exposure"', app_js)
            self.assertIn("control-run-queue", app_js)
            self.assertIn("control-action-center", app_js)
            self.assertIn("renderActionCenter", app_js)
            self.assertIn("runActionCenterWorkflow", app_js)
            self.assertIn("data-action-workflow", app_js)
            self.assertIn("renderConsoleCommandDeck", app_js)
            self.assertIn("zhConsoleText", app_js)
            self.assertIn("GUI_ZH_REPLACEMENTS", app_js)
            self.assertIn("data-console-action", app_js)
            self.assertIn("运行中", app_js)
            self.assertIn("研究回测", app_js)
            self.assertIn("模拟盘", app_js)
            self.assertIn("项目安全审计", app_js)
            self.assertIn("control-workflow-preflight", app_js)
            self.assertIn("renderWorkflowPreflight", app_js)
            self.assertIn("control-paper-readiness", html)
            self.assertIn("renderPaperReadiness", app_js)
            self.assertIn("evaluateBacktestGateRows", app_js)
            self.assertIn("server_receipts=", app_js)
            self.assertIn("browser_receipts=", app_js)
            self.assertIn("metric_passed=", app_js)
            self.assertIn("expected_block", app_js)
            self.assertIn(
                "renderPaperReadiness(\n    paperReadiness,\n    backtestGate,\n    metrics,\n    benchmark,\n    paperMetrics,\n    executionReceipts,\n    researchRequest,\n    paperRequest,",
                app_js,
            )
            self.assertIn("control-operator-checklist", app_js)
            self.assertIn("control-execution-plan", app_js)
            self.assertIn("control-workflow-trace", app_js)
            self.assertIn("control-workspace-sync", app_js)
            self.assertIn("renderWorkspaceSync", app_js)
            self.assertIn("control-process-monitor", app_js)
            self.assertIn("renderProcessMonitor", app_js)
            self.assertIn("control-active-operation", app_js)
            self.assertIn("renderActiveOperation", app_js)
            self.assertIn("beginActiveOperation", app_js)
            self.assertIn("finishActiveOperation", app_js)
            self.assertIn("control-operation-ledger", app_js)
            self.assertIn("renderOperationLedger", app_js)
            self.assertIn("control-trade-mode-control", app_js)
            self.assertIn("renderTradeModeControl", app_js)
            self.assertIn("control-request-preview", app_js)
            self.assertIn("renderRequestPreview", app_js)
            self.assertIn("control-parameter-consistency", html)
            self.assertIn("renderParameterConsistency", app_js)
            self.assertIn("parameterMismatchKeys", app_js)
            self.assertIn("buildResearchParams", app_js)
            self.assertIn("function factorWindowCsvForFactor", app_js)
            build_research_block = app_js.split("function buildResearchParams()", 1)[1].split("function buildSignalParams", 1)[0]
            self.assertIn("factorWindowCsvForFactor(factor", build_research_block)
            self.assertIn('valueOf("execution-lag")', build_research_block)
            self.assertIn('valueOf("forward-horizon")', build_research_block)
            self.assertIn("buildSignalParams", app_js)
            self.assertIn("buildPaperParams", app_js)
            build_paper_block = app_js.split("function buildPaperParams()", 1)[1].split("function renderRequestPreview", 1)[0]
            self.assertIn("factorWindowCsvForFactor(factor", build_paper_block)
            self.assertIn('valueOf("paper-max-market-weight")', build_paper_block)
            self.assertIn('valueOf("paper-max-gross-exposure")', build_paper_block)
            self.assertIn("REQUEST_PREVIEW_INPUT_IDS", app_js)
            self.assertIn("control-result-freshness", app_js)
            self.assertIn("renderResultFreshness", app_js)
            self.assertIn("control-ledger-evidence", app_js)
            self.assertIn("renderLedgerEvidence", app_js)
            self.assertIn("requestObjectFromParams", app_js)
            self.assertIn("requestMatchesCurrentParams", app_js)
            self.assertIn("control-startup-health", app_js)
            self.assertIn("control-backtest-provenance", app_js)
            self.assertIn("control-backtest-gate", app_js)
            self.assertIn("control-readiness-matrix", app_js)
            self.assertIn("control-release-readiness", app_js)
            self.assertIn("control-audit-scorecard", app_js)
            self.assertIn("control-operator-timeline", app_js)
            self.assertIn("control-audit-repair-queue", app_js)
            self.assertIn("control-run-history", app_js)
            self.assertIn("control-execution-receipts", app_js)
            self.assertIn("control-audit-packets", app_js)
            self.assertIn("control-audit-feedback", app_js)
            self.assertIn("control-audit-scheduler", app_js)
            self.assertIn("renderAuditScheduler", app_js)
            self.assertIn("RUN_HISTORY_STORAGE_KEY", app_js)
            self.assertIn("EXECUTION_RECEIPT_STORAGE_KEY", app_js)
            self.assertIn("appendRunHistory", app_js)
            self.assertIn("renderRunHistory", app_js)
            self.assertIn("appendExecutionReceipt", app_js)
            self.assertIn("renderExecutionReceipts", app_js)
            self.assertIn("researchReceipt", app_js)
            self.assertIn("signalReceipt", app_js)
            self.assertIn("paperReceipt", app_js)
            self.assertIn("renderAuditPackets", app_js)
            self.assertIn("renderAuditFeedback", app_js)
            self.assertIn("control-round-checkpoint-report", app_js)
            self.assertIn("renderRoundCheckpointReport", app_js)
            self.assertIn("renderAuditIterationPlan", app_js)
            self.assertIn("renderWorkflowTrace", app_js)
            self.assertIn("renderStartupHealth", app_js)
            self.assertIn("renderBacktestProvenance", app_js)
            self.assertIn("renderBacktestGate", app_js)
            self.assertIn("matchedExecutionReceiptCount", app_js)
            self.assertIn("requestMatchesReceipt", app_js)
            self.assertIn("paperInitialCash", app_js)
            self.assertIn("state.controlCenter?.safety", app_js)
            self.assertIn("renderControlCenter();\n  return nextReceipt;", app_js)
            self.assertIn("renderResultEvidence", app_js)
            result_evidence_block = app_js.split("function renderResultEvidence", 1)[1].split("function renderReleaseReadiness", 1)[0]
            self.assertIn("<span>${escapeHtml(item.command || \"\")}</span>", result_evidence_block)
            self.assertIn("renderReleaseReadiness", app_js)
            self.assertIn("auditCategories.slice(0, 7)", app_js)
            self.assertIn("localStorage", app_js)
            self.assertIn("control-workflow-commands", app_js)
            self.assertIn("control-report-links", app_js)
            self.assertIn("control-verification-gates", app_js)
            self.assertIn("control-verification-runner", app_js)
            self.assertIn("/api/control/verification?gate_id=", app_js)
            self.assertIn("runVerificationGate", app_js)
            self.assertIn("renderVerificationRunner", app_js)
            self.assertIn("const phraseReplacements", app_js)
            self.assertIn("return String(zhConsoleText(value))", app_js)
            startup_block = app_js.split('document.addEventListener("DOMContentLoaded", async () => {', 1)[1].split("});", 1)[0]
            self.assertIn("await loadControlCenter();", startup_block)
            load_control_block = app_js.split("async function loadControlCenter()", 1)[1].split("async function loadProjectStatus", 1)[0]
            self.assertIn("applyControlDefaults();", load_control_block)
            self.assertIn("await loadRiskCandidates();", startup_block)
            self.assertIn("await loadRecentDataRefresh();", startup_block)
            self.assertIn("await loadPostRefreshReplay();", startup_block)
            self.assertIn("await loadObservationSufficiency();", startup_block)
            self.assertIn("await loadExpandedObservationReplay();", startup_block)
            self.assertIn("await loadIterativeObservationExpansion();", startup_block)
            self.assertIn("await loadTushareActivationGate();", startup_block)
            self.assertNotIn("await runResearch();", startup_block)
            self.assertNotIn("await runSignals();", startup_block)
            self.assertNotIn("await runPaper();", startup_block)
            self.assertNotIn("await runPromotionOps();", startup_block)

            snapshot = _read_json(f"{base_url}/api/snapshot")
            self.assertEqual(snapshot["data_mode"], "demo_fixture")

            control = _read_json(f"{base_url}/api/control/status")
            self.assertEqual(control["stage"], "gui_control_center")
            self.assertIn("backtest", control)
            self.assertIn("form_defaults", control)
            self.assertIn("parameter_authority", control)
            self.assertIn("workflow_preflight", control)
            self.assertIn("paper_readiness", control)
            self.assertIn("method", control)
            self.assertIn("result_evidence", control)
            self.assertIn("ledger_evidence", control)
            self.assertIn("workflows", control)
            self.assertIn("report_links", control)
            self.assertIn("workspace_sync", control)
            self.assertIn("process_monitor", control)
            self.assertIn("active_operation", control)
            self.assertIn("operation_ledger", control)
            self.assertIn("trade_mode_control", control)
            self.assertIn("run_queue", control)
            self.assertIn("action_center", control)
            self.assertIn("verification_gates", control)
            self.assertIn("verification_runner", control)
            self.assertIn("operator_checklist", control)
            self.assertIn("execution_plan", control)
            self.assertIn("workflow_trace", control)
            self.assertIn("startup_health", control)
            self.assertIn("backtest_provenance", control)
            self.assertIn("backtest_gate", control)
            self.assertIn("readiness_matrix", control)
            self.assertIn("release_readiness", control)
            self.assertIn("audit_scorecard", control)
            self.assertIn("operator_timeline", control)
            self.assertIn("run_history", control)
            self.assertIn("execution_receipts", control)
            self.assertIn("audit_packets", control)
            self.assertIn("audit_feedback", control)
            self.assertIn("audit_iteration_plan", control)
            self.assertIn("round_checkpoint_report", control)
            self.assertIn("audit_scheduler", control)
            self.assertEqual(control["ledger_evidence"]["stage"], "gui_ledger_evidence")
            self.assertEqual(control["action_center"]["stage"], "gui_action_center")
            self.assertFalse(control["safety"]["live_trading_allowed"])
            self.assertFalse(control["trade_mode_control"]["summary"]["live_trading_allowed"])
            self.assertTrue(control["trade_mode_control"]["summary"]["paper_simulation_available"])
            self.assertEqual(control["form_defaults"]["research"]["factor"], control["backtest"]["factor"])
            self.assertEqual(control["parameter_authority"]["summary"]["status"], "ready")
            control_authority_rows = {item["workflow_id"]: item for item in control["parameter_authority"]["rows"]}
            self.assertEqual(
                control_authority_rows["research_backtest"]["canonical_request"]["factor_name"],
                control["backtest"]["factor"],
            )
            self.assertIn("max_market_weight", control_authority_rows["paper_simulation"]["comparison_keys"])
            self.assertEqual(control["workflow_preflight"]["summary"]["status"], "review")
            self.assertGreaterEqual(control["workflow_preflight"]["summary"]["review_count"], 1)
            control_preflight_rows = {item["workflow_id"]: item for item in control["workflow_preflight"]["rows"]}
            self.assertEqual(control_preflight_rows["live_trading"]["status"], "blocked")
            self.assertFalse(control_preflight_rows["live_trading"]["runnable"])
            self.assertTrue(control_preflight_rows["research_backtest"]["runnable"])
            self.assertNotIn("GET GET", control_preflight_rows["verification_runner"]["command"])
            self.assertIn("execution_boundary", {check["check_id"] for check in control_preflight_rows["paper_simulation"]["checks"]})
            self.assertEqual(control["paper_readiness"]["stage"], "gui_paper_readiness_handoff")
            self.assertFalse(control["paper_readiness"]["summary"]["paper_candidate_allowed"])
            self.assertFalse(control["paper_readiness"]["summary"]["live_trading_allowed"])
            control_readiness_ids = {item["check_id"] for item in control["paper_readiness"]["rows"]}
            self.assertIn("research_receipt", control_readiness_ids)
            self.assertIn("paper_receipt", control_readiness_ids)
            self.assertIn("metric_floor", control_readiness_ids)
            self.assertIn("live_boundary", control_readiness_ids)

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

            profile_observation = _read_json(f"{base_url}/api/risk/profile-observation")
            self.assertEqual(profile_observation["stage"], "gui_profile_observation")
            self.assertIn("stop_rules", profile_observation)

            recent_refresh = _read_json(f"{base_url}/api/data/recent-refresh")
            self.assertEqual(recent_refresh["stage"], "gui_recent_data_refresh")
            self.assertIn("coverage", recent_refresh)

            post_refresh = _read_json(f"{base_url}/api/data/post-refresh-replay")
            self.assertEqual(post_refresh["stage"], "gui_post_refresh_replay")
            self.assertIn("decision", post_refresh)

            sufficiency = _read_json(f"{base_url}/api/risk/observation-sufficiency")
            self.assertEqual(sufficiency["stage"], "gui_observation_sufficiency")
            self.assertIn("recommendation", sufficiency)

            expanded = _read_json(f"{base_url}/api/risk/expanded-observation-replay")
            self.assertEqual(expanded["stage"], "gui_expanded_observation_replay")
            self.assertIn("final_observation_sufficiency", expanded)

            iterative = _read_json(f"{base_url}/api/risk/iterative-observation-expansion")
            self.assertEqual(iterative["stage"], "gui_iterative_observation_expansion")
            self.assertIn("rounds", iterative)

            activation = _read_json(f"{base_url}/api/risk/tushare-activation-gate")
            self.assertEqual(activation["stage"], "gui_tushare_activation_gate")
            self.assertIn("stage_ledger", activation)

            factor_leaderboard = _read_json(f"{base_url}/api/factors/leaderboard?limit=20")
            self.assertEqual(factor_leaderboard["stage"], "gui_factor_leaderboard")
            self.assertIn("summary", factor_leaderboard)
            self.assertIn("top20", factor_leaderboard)

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

            verification = _read_json(f"{base_url}/api/control/verification?gate_id=gui_compile")
            self.assertEqual(verification["stage"], "gui_verification_result")
            self.assertEqual(verification["gate_id"], "gui_compile")
            self.assertEqual(verification["status"], "passed")
            self.assertFalse(verification["safety"]["live_trading_allowed"])

            ledger = _read_json(f"{base_url}/api/control/operation-ledger")
            self.assertEqual(ledger["stage"], "gui_operation_ledger")
            self.assertGreaterEqual(ledger["summary"]["entry_count"], 1)
            self.assertEqual(ledger["rows"][0]["workflow_id"], "verification_runner")
            self.assertFalse(ledger["summary"]["live_trading_allowed"])
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_http_app_serves_factor_leaderboard_from_requested_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports_root = root / "reports"
            configs_root = root / "configs"
            reports_root.mkdir()
            configs_root.mkdir()
            (configs_root / "grid.json").write_text(
                json.dumps({"factor_names": ["cn_etf_public_indicator_combo"]}, ensure_ascii=False),
                encoding="utf-8",
            )
            (reports_root / "leaderboard.json").write_text(
                json.dumps(
                    {
                        "candidate_leaderboard": [
                            {
                                "case_id": "cn_etf_public_indicator_combo_top2_cost5",
                                "factor_name": "cn_etf_public_indicator_combo",
                                "market": "CN_ETF",
                                "sharpe": 1.23,
                                "total_return": 0.42,
                                "annualized_return": 0.12,
                                "max_drawdown": -0.18,
                                "win_rate": 0.57,
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            server = ThreadingHTTPServer(("127.0.0.1", 0), create_gui_handler())
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_port}"
            query = urlencode(
                {
                    "reports_root": str(reports_root),
                    "configs_root": str(configs_root),
                    "limit": "20",
                }
            )
            try:
                result = _read_json(f"{base_url}/api/factors/leaderboard?{query}")
            finally:
                server.shutdown()
                thread.join(timeout=5)
                server.server_close()

        self.assertEqual(result["stage"], "gui_factor_leaderboard")
        self.assertEqual(result["summary"]["candidate_rows"], 1)
        self.assertEqual(result["top20"][0]["factor_name"], "cn_etf_public_indicator_combo")
        self.assertEqual(result["top20"][0]["score_metric"], "sharpe")

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
