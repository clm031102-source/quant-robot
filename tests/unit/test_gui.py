import json
import threading
import tempfile
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.gui.app import create_gui_handler
from quant_robot.gui.desktop_app import (
    DESKTOP_APP_COPY,
    DEFAULT_DAILY_TARGET_ID,
    DEFAULT_JOURNAL_TARGET_ID,
    DEFAULT_PAPER_TARGET_ID,
    DEFAULT_TOP3_TARGET_ID,
    DesktopAppState,
    DesktopGuiController,
    desktop_beginner_status_texts,
    desktop_beginner_status_rows,
    find_available_port,
    main as desktop_app_main,
)
from quant_robot.gui.research_service import (
    build_constrained_search_snapshot,
    build_daily_trade_advisory_snapshot,
    build_daily_ops_snapshot,
    build_expanded_observation_replay_snapshot,
    build_factor_leaderboard_snapshot,
    _candidate_factor_windows,
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


class GuiDesktopAppTests(unittest.TestCase):
    def test_desktop_controller_starts_local_gui_and_opens_beginner_console(self):
        events: list[object] = []

        class FakeServer:
            def serve_forever(self) -> None:
                events.append("serve_forever")

            def shutdown(self) -> None:
                events.append("shutdown")

            def server_close(self) -> None:
                events.append("server_close")

        def server_factory(host: str, port: int) -> FakeServer:
            events.append(("server_factory", host, port))
            return FakeServer()

        opened: list[str] = []
        controller = DesktopGuiController(
            host="127.0.0.1",
            port=9001,
            server_factory=server_factory,
            browser_open=opened.append,
        )

        state = controller.open_console()

        self.assertEqual(state.status, "running")
        self.assertEqual(state.url, "http://127.0.0.1:9001/")
        self.assertEqual(opened, ["http://127.0.0.1:9001/"])
        self.assertIn("新手", DESKTOP_APP_COPY["title"])
        self.assertIn("不连接券商", state.safety_text)
        self.assertIn(("server_factory", "127.0.0.1", 9001), events)
        self.assertIsNotNone(controller.thread)
        self.assertTrue(controller.thread.daemon)

        stopped = controller.stop()

        self.assertEqual(stopped.status, "stopped")
        self.assertIn("shutdown", events)
        self.assertIn("server_close", events)

    def test_desktop_controller_falls_back_when_default_port_is_busy(self):
        used_ports: list[int] = []

        class FakeServer:
            def serve_forever(self) -> None:
                return

            def shutdown(self) -> None:
                return

            def server_close(self) -> None:
                return

        def server_factory(host: str, port: int) -> FakeServer:
            used_ports.append(port)
            if port == 8765:
                raise OSError("address already in use")
            return FakeServer()

        controller = DesktopGuiController(
            host="127.0.0.1",
            port=8765,
            port_scan_limit=3,
            server_factory=server_factory,
            browser_open=lambda _url: None,
        )

        state = controller.start()

        self.assertEqual(state.status, "running")
        self.assertEqual(state.port, 8766)
        self.assertEqual(state.url, "http://127.0.0.1:8766/")
        self.assertEqual(used_ports[:2], [8765, 8766])
        controller.stop()

    def test_desktop_controller_opens_beginner_task_sections_as_hash_links(self):
        events: list[object] = []

        class FakeServer:
            def serve_forever(self) -> None:
                events.append("serve_forever")

            def shutdown(self) -> None:
                events.append("shutdown")

            def server_close(self) -> None:
                events.append("server_close")

        def server_factory(host: str, port: int) -> FakeServer:
            events.append(("server_factory", host, port))
            return FakeServer()

        opened: list[str] = []
        controller = DesktopGuiController(
            host="127.0.0.1",
            port=9002,
            server_factory=server_factory,
            browser_open=opened.append,
        )

        daily_state = controller.open_section("daily")

        self.assertEqual(daily_state.status, "running")
        self.assertEqual(daily_state.url, "http://127.0.0.1:9002/#daily")
        self.assertEqual(opened, ["http://127.0.0.1:9002/#daily"])
        self.assertEqual(controller.url_for_page("logs"), "http://127.0.0.1:9002/#logs")
        self.assertEqual(
            controller.url_for_page("dashboard", "factor-leaderboard-table"),
            "http://127.0.0.1:9002/#dashboard:factor-leaderboard-table",
        )
        self.assertEqual(
            controller.url_for_page("daily", "daily-real-world-handoff-gate"),
            "http://127.0.0.1:9002/#daily:daily-real-world-handoff-gate",
        )
        self.assertEqual(controller.url_for_page("unknown"), "http://127.0.0.1:9002/")
        controller.stop()

    def test_desktop_launcher_files_are_beginner_facing(self):
        launcher = Path("scripts/run_desktop_app.py")
        batch_file = Path("scripts/start_quant_robot_desktop.bat")

        self.assertTrue(launcher.exists())
        self.assertTrue(batch_file.exists())
        self.assertIn("run_desktop_app", launcher.read_text(encoding="utf-8"))
        self.assertIn("--no-open", launcher.read_text(encoding="utf-8"))
        self.assertIn("scripts\\run_desktop_app.py", batch_file.read_text(encoding="utf-8"))
        self.assertIn("research-to-paper", batch_file.read_text(encoding="utf-8"))
        self.assertIn("--page dashboard", batch_file.read_text(encoding="utf-8"))
        self.assertIn("--target-id ordinary-daily-action-card", batch_file.read_text(encoding="utf-8"))
        self.assertIn("today_action_button", DESKTOP_APP_COPY)
        self.assertIn("top3_button", DESKTOP_APP_COPY)
        self.assertIn("paper_button", DESKTOP_APP_COPY)
        self.assertIn("daily_button", DESKTOP_APP_COPY)
        self.assertIn("profitability_button", DESKTOP_APP_COPY)
        self.assertIn("leaderboard_button", DESKTOP_APP_COPY)
        self.assertIn("journal_button", DESKTOP_APP_COPY)
        self.assertIn("logs_button", DESKTOP_APP_COPY)
        self.assertIn("今日前三信号", DESKTOP_APP_COPY["top3_button"])
        self.assertIn("模拟盘复核", DESKTOP_APP_COPY["paper_button"])
        self.assertIn("今日交易检查", DESKTOP_APP_COPY["daily_button"])
        self.assertIn("盈利证据", DESKTOP_APP_COPY["profitability_button"])

    def test_desktop_beginner_status_rows_explain_first_actions_and_safety(self):
        rows = desktop_beginner_status_rows()
        rows_by_id = {row["row_id"]: row for row in rows}

        self.assertEqual(rows[0]["row_id"], "today_action")
        self.assertIn("ordinary-daily-action-card", rows_by_id["today_action"]["target"])
        self.assertIn("今天先做哪一步", rows_by_id["today_action"]["detail"])
        self.assertEqual(rows_by_id["top3_signal"]["target"], DEFAULT_TOP3_TARGET_ID)
        self.assertIn("今日前三因子", rows_by_id["top3_signal"]["detail"])
        self.assertEqual(rows_by_id["paper_rehearsal"]["target"], DEFAULT_PAPER_TARGET_ID)
        self.assertIn("同一组参数", rows_by_id["paper_rehearsal"]["detail"])
        self.assertEqual(rows_by_id["profitability_evidence"]["target"], "daily-live-profitability-readiness")
        self.assertIn("盈利证据", rows_by_id["profitability_evidence"]["label"])
        self.assertIn("小资金", rows_by_id["profitability_evidence"]["detail"])
        self.assertEqual(rows_by_id["daily_check"]["target"], DEFAULT_DAILY_TARGET_ID)
        self.assertIn("Sharpe", rows_by_id["factor_leaderboard"]["detail"])
        self.assertEqual(rows_by_id["post_close_journal"]["target"], DEFAULT_JOURNAL_TARGET_ID)
        self.assertIn("明天", rows_by_id["post_close_journal"]["detail"])
        self.assertIn("不会连接券商", rows_by_id["safety_boundary"]["detail"])
        self.assertFalse(rows_by_id["safety_boundary"]["broker_connection_allowed"])
        self.assertFalse(rows_by_id["safety_boundary"]["order_placement_allowed"])

    def test_desktop_beginner_status_texts_are_plain_chinese_and_safe(self):
        texts = desktop_beginner_status_texts()

        self.assertGreaterEqual(len(texts), 7)
        joined = "\n".join(texts)
        self.assertIn("第一步：看总闸门", texts[0])
        self.assertIn("盈利证据", joined)
        self.assertIn("小资金", joined)
        self.assertIn("不会连接券商", joined)
        self.assertIn("不会自动下单", joined)
        self.assertNotIn("锛", joined)
        self.assertNotIn("歿", joined)
        self.assertNotIn("閲", joined)

    def test_desktop_cli_accepts_beginner_workflow_deep_link_options(self):
        calls: list[dict[str, object]] = []

        def fake_runner(**kwargs: object) -> DesktopAppState:
            calls.append(kwargs)
            return DesktopAppState(
                status="running",
                host=str(kwargs["host"]),
                port=int(kwargs["port"]),
                url="http://127.0.0.1:9100/#daily:daily-real-world-handoff-gate",
                message="started",
            )

        state = desktop_app_main(
            [
                "--host",
                "127.0.0.1",
                "--port",
                "9100",
                "--page",
                "daily",
                "--target-id",
                "daily-real-world-handoff-gate",
            ],
            runner=fake_runner,
        )

        self.assertEqual(state.status, "running")
        self.assertEqual(calls[0]["host"], "127.0.0.1")
        self.assertEqual(calls[0]["port"], 9100)
        self.assertEqual(calls[0]["open_on_start"], True)
        self.assertEqual(calls[0]["initial_page"], "daily")
        self.assertEqual(calls[0]["initial_target_id"], "daily-real-world-handoff-gate")

    def test_desktop_cli_defaults_to_today_action_card(self):
        calls: list[dict[str, object]] = []

        def fake_runner(**kwargs: object) -> DesktopAppState:
            calls.append(kwargs)
            return DesktopAppState(
                status="running",
                host=str(kwargs["host"]),
                port=int(kwargs["port"]),
                url="http://127.0.0.1:8765/#dashboard:ordinary-daily-action-card",
                message="started",
            )

        state = desktop_app_main([], runner=fake_runner)

        self.assertEqual(state.status, "running")
        self.assertEqual(calls[0]["initial_page"], "dashboard")
        self.assertEqual(calls[0]["initial_target_id"], "ordinary-daily-action-card")

    def test_desktop_shortcut_installer_writes_beginner_workflow_launchers(self):
        from scripts.install_quant_robot_desktop_shortcuts import (
            DEFAULT_DESKTOP_SHORTCUTS,
            install_desktop_shortcuts,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "Desktop"
            result = install_desktop_shortcuts(
                output_dir=output_dir,
                repo_root=Path("F:/lhjqr"),
            )

            written = {Path(item["path"]).name: Path(item["path"]).read_text(encoding="utf-8") for item in result["shortcuts"]}
            shortcut_bodies_by_id = {
                item["shortcut_id"]: Path(item["path"]).read_text(encoding="utf-8") for item in result["shortcuts"]
            }
            readme_path = Path(result["readme_path"])
            readme_text = readme_path.read_text(encoding="utf-8")

        self.assertEqual(result["stage"], "desktop_shortcut_install")
        self.assertFalse(result["safety"]["broker_connection_allowed"])
        self.assertFalse(result["safety"]["account_read_allowed"])
        self.assertFalse(result["safety"]["order_placement_allowed"])
        self.assertEqual(len(result["shortcuts"]), len(DEFAULT_DESKTOP_SHORTCUTS))
        shortcuts_by_id = {item["shortcut_id"]: item for item in result["shortcuts"]}
        self.assertIn("today_action", shortcuts_by_id)
        self.assertEqual(shortcuts_by_id["today_action"]["page"], "dashboard")
        self.assertEqual(shortcuts_by_id["today_action"]["target_id"], "ordinary-daily-action-card")
        self.assertIn("python scripts\\run_desktop_app.py --page dashboard --target-id ordinary-daily-action-card", shortcut_bodies_by_id["today_action"])
        self.assertIn("top3_signal", shortcuts_by_id)
        self.assertEqual(shortcuts_by_id["top3_signal"]["target_id"], "daily-trade-decision-sheet")
        self.assertIn("paper_rehearsal", shortcuts_by_id)
        self.assertEqual(shortcuts_by_id["paper_rehearsal"]["target_id"], "daily-signal-execution-bridge")
        self.assertIn("profitability_evidence", shortcuts_by_id)
        self.assertEqual(shortcuts_by_id["profitability_evidence"]["target_id"], "daily-live-profitability-readiness")
        self.assertIn("post_close_journal", shortcuts_by_id)
        self.assertEqual(shortcuts_by_id["post_close_journal"]["target_id"], "beginner-post-close-journal-board")
        self.assertEqual(readme_path.name, "量化机器人-先读我.txt")
        self.assertIn("第一步", readme_text)
        self.assertIn("今日前三信号", readme_text)
        self.assertIn("模拟盘复核", readme_text)
        self.assertIn("盈利证据", readme_text)
        self.assertIn("盘后复盘", readme_text)
        self.assertIn("今天先做哪一步", readme_text)
        self.assertIn("Sharpe", readme_text)
        self.assertIn("今日交易检查", readme_text)
        self.assertIn("因子排行榜", readme_text)
        self.assertIn("日志报告", readme_text)
        self.assertIn("不会连接券商", readme_text)
        self.assertIn("不会自动下单", readme_text)
        self.assertIn("量化机器人-今日交易检查.bat", written)
        self.assertIn("量化机器人-今日前三信号.bat", written)
        self.assertIn("量化机器人-模拟盘复核.bat", written)
        self.assertIn("量化机器人-盈利证据.bat", written)
        self.assertIn("量化机器人-因子排行榜.bat", written)
        self.assertIn("量化机器人-盘后复盘.bat", written)
        self.assertIn("量化机器人-日志报告.bat", written)
        self.assertIn("python scripts\\run_desktop_app.py --page daily --target-id daily-manual-trading-session", written["量化机器人-今日交易检查.bat"])
        self.assertIn("python scripts\\run_desktop_app.py --page daily --target-id daily-trade-decision-sheet", written["量化机器人-今日前三信号.bat"])
        self.assertIn("python scripts\\run_desktop_app.py --page daily --target-id daily-signal-execution-bridge", written["量化机器人-模拟盘复核.bat"])
        self.assertIn("python scripts\\run_desktop_app.py --page daily --target-id daily-live-profitability-readiness", written["量化机器人-盈利证据.bat"])
        self.assertIn("python scripts\\run_desktop_app.py --page dashboard --target-id factor-leaderboard-table", written["量化机器人-因子排行榜.bat"])
        self.assertIn("python scripts\\run_desktop_app.py --page daily --target-id beginner-post-close-journal-board", written["量化机器人-盘后复盘.bat"])
        self.assertIn("research-to-paper only", written["量化机器人-日志报告.bat"])
        self.assertNotIn("broker", written["量化机器人-今日交易检查.bat"].lower().replace("no broker", ""))
        self.assertNotIn("TUSHARE_TOKEN", "\n".join(written.values()))
        self.assertNotIn("TUSHARE_TOKEN", readme_text)

    def test_desktop_shortcut_install_batch_is_beginner_safe(self):
        batch_file = Path("scripts/install_quant_robot_desktop_shortcuts.bat")

        self.assertTrue(batch_file.exists())
        body = batch_file.read_text(encoding="utf-8")
        self.assertIn("install_quant_robot_desktop_shortcuts.py", body)
        self.assertIn("--repo-root", body)
        self.assertIn("research-to-paper only", body)
        self.assertIn("no broker/account/order/live trading", body)
        self.assertNotIn("TUSHARE_TOKEN", body)
        self.assertNotIn("order placement", body.lower())

    def test_daily_page_exposes_trading_system_blueprint_panel(self):
        html = Path("src/quant_robot/gui/static/index.html").read_text(encoding="utf-8")
        app_js = Path("src/quant_robot/gui/static/app.js").read_text(encoding="utf-8")

        self.assertIn("daily-signal-execution-bridge", html)
        self.assertIn("daily-signal-execution-summary", html)
        self.assertIn("daily-signal-execution-steps", html)
        self.assertIn("daily-signal-execution-gates", html)
        self.assertIn("daily-signal-execution-paper", html)
        self.assertIn("renderDailySignalExecutionBridge", app_js)
        self.assertIn("daily_signal_execution_bridge", app_js)
        self.assertIn("daily-deployment-readiness", html)
        self.assertIn("daily-deployment-readiness-summary", html)
        self.assertIn("daily-deployment-readiness-sequence", html)
        self.assertIn("daily-deployment-readiness-tickets", html)
        self.assertIn("daily-deployment-readiness-gates", html)
        self.assertIn("renderDailyDeploymentReadiness", app_js)
        self.assertIn("daily_deployment_readiness", app_js)
        self.assertIn("daily-live-profitability-readiness", html)
        self.assertIn("daily-live-profitability-summary", html)
        self.assertIn("daily-live-profitability-gates", html)
        self.assertIn("daily-live-profitability-actions", html)
        self.assertIn("daily-live-profitability-controls", html)
        self.assertIn("daily-closure-streak", html)
        self.assertIn("daily-closure-streak-summary", html)
        self.assertIn("daily-closure-streak-rows", html)
        self.assertIn("renderLiveProfitabilityReadiness", app_js)
        self.assertIn("live_profitability_readiness", app_js)
        self.assertIn("renderCapitalTierSummary", app_js)
        self.assertIn("capital_tier_summary", app_js)
        self.assertIn("capital_tier", app_js)
        self.assertIn("next_capital_tier", app_js)
        self.assertIn("capital_tier_missing_gate_count", app_js)
        self.assertIn("capital_tier_real_money_limit", app_js)
        self.assertIn("capital_tier_external_manual_only", app_js)
        self.assertIn("liveProfitabilityRuntimeEvidence", app_js)
        self.assertIn("mergeLiveProfitabilityRuntimeEvidence", app_js)
        self.assertIn("dailyTradeAdvisoryEvidencePayload", app_js)
        self.assertIn("dailyClosureStreakEvidence", app_js)
        self.assertIn("renderDailyClosureStreak", app_js)
        self.assertIn("closure_streak_ready", app_js)
        self.assertIn("closed_loop_days", app_js)
        self.assertIn("manual_execution_clean", app_js)
        self.assertIn("dailyEvidencePaperRequest", app_js)
        self.assertIn("same_parameter_browser_execution_receipts", app_js)
        self.assertIn("paperReceiptMatchesRequest(item, paperRequest).matches", app_js)
        self.assertIn('params.set("evidence_snapshot"', app_js)
        self.assertIn("recent_observation_status", app_js)
        self.assertIn("recent_observation_degradation_required", app_js)
        self.assertIn("recent_observation_return_pct", app_js)
        self.assertIn("recent_observation_win_rate", app_js)
        self.assertIn("renderRecentObservationDegradation", app_js)
        self.assertIn("matched_paper_receipts", app_js)
        self.assertIn("post_close_journal_receipts", app_js)
        self.assertIn("paper_ready_observations", app_js)
        self.assertIn("dailyExecutionRiskStateFromReceipts", app_js)
        self.assertIn("receiptRiskStateNumber", app_js)
        self.assertIn("risk_state", app_js)
        self.assertIn("today_pnl_pct", app_js)
        self.assertIn("today_loss_pct", app_js)
        self.assertIn("current_drawdown_pct", app_js)
        self.assertIn("consecutive_loss_days", app_js)
        self.assertIn("cooldown_days_remaining", app_js)
        self.assertIn("numberOrNull(riskState[key])", app_js)
        self.assertIn('evidence.mode === "browser_execution_receipts" && !hasRiskState', app_js)
        self.assertIn("renderOrdinaryExecutionBridgeStrip", app_js)
        self.assertIn("applyDailyPaperHandoffToForm", app_js)
        self.assertIn("data-daily-paper-handoff-apply", app_js)
        self.assertIn("dailyPaperReceiptStatus", app_js)
        self.assertIn("paperReceiptMatchesRequest", app_js)
        self.assertIn("dailyPaperRequestSignature", app_js)
        self.assertIn("paper_request_signature", app_js)
        self.assertIn("renderDailyPaperReceiptStatusRows", app_js)
        self.assertIn('latestExecutionReceipt("paper_simulation")', app_js)
        self.assertIn('data-beginner-action="paper_simulation"', app_js)
        self.assertIn("data-daily-paper-handoff-run", app_js)
        self.assertIn("runDailyPaperHandoffSimulation", app_js)
        self.assertIn("renderDailyPaperManualReviewRows", app_js)
        self.assertIn("dailyPaperManualReviewRow", app_js)
        self.assertIn("daily-manual-broker-handoff-ticket-table", app_js)
        self.assertIn("execution_guardrails", app_js)
        self.assertIn("lower_price_bound", app_js)
        self.assertIn("upper_price_bound", app_js)
        self.assertIn("max_slippage_bps", app_js)
        self.assertIn("daily-factor-health-monitor", html)
        self.assertIn("daily-factor-health-summary", html)
        self.assertIn("daily-factor-health-rows", html)
        self.assertIn("daily-factor-health-actions", html)
        self.assertIn("renderDailyFactorHealthMonitor", app_js)
        self.assertIn("daily_factor_health_monitor", app_js)
        self.assertIn("factor_health_status", app_js)
        self.assertIn("retire_candidate", app_js)
        self.assertIn("next_session_quarantine_required", app_js)
        self.assertIn("next_session_quarantine_rules", app_js)
        self.assertIn("same_parameter_top3_paper_incomplete", app_js)
        self.assertIn("quarantine_pending_evidence", app_js)
        self.assertIn("blocked_next_session_quarantine_required", app_js)
        self.assertIn("next_session_quarantine", app_js)
        self.assertIn("daily-trading-system-blueprint", html)
        self.assertIn("daily-trading-system-blueprint-summary", html)
        self.assertIn("daily-trading-system-blueprint-evidence", html)
        self.assertIn("daily-trading-system-blueprint-actions", html)
        self.assertIn("renderDailyTradingSystemBlueprint", app_js)
        self.assertIn("trading_system_blueprint", app_js)
        self.assertIn("daily-real-world-handoff-gate", html)
        self.assertIn("daily-real-world-handoff-summary", html)
        self.assertIn("daily-real-world-handoff-runbook", html)
        self.assertIn("daily-real-world-handoff-tickets", html)
        self.assertIn("daily-real-world-handoff-ladder", html)
        self.assertIn("renderDailyRealWorldHandoffGate", app_js)
        self.assertIn("renderDailyRealWorldCapitalLadder", app_js)
        self.assertIn("real_world_manual_handoff_gate", app_js)
        self.assertIn("daily-real-money-transition-gate", html)
        self.assertIn("daily-real-money-transition-summary", html)
        self.assertIn("daily-real-money-transition-preflight", html)
        self.assertIn("daily-real-money-transition-script", html)
        self.assertIn("daily-real-money-transition-tickets", html)
        self.assertIn("renderDailyRealMoneyTransitionGate", app_js)
        self.assertIn("daily_real_money_transition_gate", app_js)
        self.assertIn("daily-manual-trading-session", html)
        self.assertIn("daily-manual-trading-session-summary", html)
        self.assertIn("daily-manual-trading-session-gates", html)
        self.assertIn("daily-manual-trading-session-steps", html)
        self.assertIn("daily-manual-trading-session-tickets", html)
        self.assertIn("renderDailyManualTradingSession", app_js)
        self.assertIn("daily_manual_trading_session", app_js)
        self.assertIn("blocked_same_parameter_paper_required", app_js)
        self.assertIn("open_external_broker_manually", app_js)
        self.assertIn("daily-paper-allocation-playbook", html)
        self.assertIn("daily-paper-allocation-summary", html)
        self.assertIn("daily-paper-allocation-rows", html)
        self.assertIn("daily-paper-allocation-gates", html)
        self.assertIn("daily-paper-allocation-steps", html)
        self.assertIn("renderDailyPaperAllocationPlaybook", app_js)
        self.assertIn("daily_paper_allocation_playbook", app_js)
        self.assertIn("paper_rehearsal_required", app_js)
        self.assertIn("do_not_copy_to_broker", app_js)
        self.assertIn("仓位预算状态", app_js)
        self.assertIn("一句话结论", app_js)
        self.assertIn("纸面预算", app_js)
        self.assertIn("权限边界", app_js)
        self.assertIn("运行下一步", app_js)
        self.assertIn("查看证据", app_js)
        self.assertIn("只做同参数模拟盘演练，不要复制到券商端", app_js)
        self.assertIn("不连接券商、不读取账户、不自动下单", app_js)
        self.assertIn("renderTodayOperationCard", app_js)
        self.assertIn("today_operation_card", app_js)
        self.assertIn("today_action_code", app_js)
        self.assertIn("manual_external_broker_check_required", app_js)
        self.assertIn("after_action_closure_gate", app_js)
        self.assertIn("closure_gate_status", app_js)
        self.assertIn("next_session_quarantine_required_if_missing", app_js)
        self.assertIn("after_action_checklist", app_js)
        self.assertIn("quarantine_next_session_if_missing", app_js)
        self.assertIn("daily-beginner-execution-answer-today-card", html)
        self.assertIn("daily-beginner-execution-answer-go-no-go", html)
        self.assertIn("daily-beginner-execution-answer-pre-market-packet", html)
        self.assertIn("daily-beginner-execution-answer-final-packet", html)
        self.assertIn("renderTradeSystemGoNoGoGate", app_js)
        self.assertIn("trade_system_go_no_go_gate", app_js)
        self.assertIn("manual_review_only_not_order", app_js)
        self.assertIn("broker_realtime_price_recheck", app_js)
        self.assertIn("pre_market_manual_execution_packet", app_js)
        self.assertIn("packet_status", app_js)
        self.assertIn("evidence_checklist", app_js)
        self.assertIn("human_decides_skip_or_manual_trade", app_js)
        self.assertIn("broker_price_recheck_playbook", app_js)
        self.assertIn("external_broker_realtime_price", app_js)
        self.assertIn("floor_to_board_lot_at_external_price", app_js)
        self.assertIn("renderBrokerPriceRecheckDecision", app_js)
        self.assertIn("brokerPriceRecheckSessionVerdict", app_js)
        self.assertIn("data-broker-price-recheck-session-output", app_js)
        self.assertIn("data-broker-price-recheck-price", app_js)
        self.assertIn("data-broker-price-recheck-cash", app_js)
        self.assertIn("broker_price_recheck_local_calculator", app_js)
        self.assertIn("broker_price_recheck_session_verdict", app_js)
        self.assertIn("external_available_cash_after_manual_check", app_js)
        self.assertIn("external_cash_shortfall", app_js)
        self.assertIn("waiting_for_all_external_inputs", app_js)
        self.assertIn("manual_review_price_ok_quantity_recalculated", app_js)
        self.assertIn("manual_review_all_rows_price_cash_ok", app_js)
        self.assertIn("manual_review_some_rows_skipped_or_blocked", app_js)
        self.assertIn("skip_broker_price_outside_guardrail", app_js)
        self.assertIn("skip_external_cash_below_recalculated_value", app_js)
        self.assertIn("recalculated_quantity_at_external_price", app_js)
        self.assertNotIn('"Allocation status"', app_js)
        self.assertNotIn('"Plain answer"', app_js)
        self.assertNotIn('"Paper budget"', app_js)
        self.assertNotIn('"Boundary"', app_js)
        self.assertNotIn('"Run next"', app_js)
        self.assertNotIn('"View evidence"', app_js)
        beginner_execution_block = app_js.split("function renderDailyBeginnerExecutionAnswer", 1)[1].split(
            "function renderDailyPreExecutionGuard",
            1,
        )[0]
        self.assertIn("纸面演练=", beginner_execution_block)
        self.assertIn("人工复核=", beginner_execution_block)
        self.assertIn("目标权重=", beginner_execution_block)
        self.assertIn("预算=", beginner_execution_block)
        self.assertIn("数量=", beginner_execution_block)
        self.assertIn("参考价=", beginner_execution_block)
        self.assertIn("价格护栏=", beginner_execution_block)
        self.assertIn("最大滑点=", beginner_execution_block)
        self.assertIn("流动性/容量", beginner_execution_block)
        self.assertIn("人工检查=", beginner_execution_block)
        self.assertIn("券商实时价格", beginner_execution_block)
        self.assertNotIn("paper=", beginner_execution_block)
        self.assertNotIn("manual_review=", beginner_execution_block)
        self.assertNotIn("weight=", beginner_execution_block)
        self.assertNotIn("budget=", beginner_execution_block)
        self.assertNotIn("qty=", beginner_execution_block)
        self.assertNotIn("price=", beginner_execution_block)
        self.assertNotIn("guard=", beginner_execution_block)
        self.assertNotIn("capacity=", beginner_execution_block)
        self.assertNotIn("check_external_realtime_price", beginner_execution_block)
        self.assertIn("daily-pre-execution-guard", html)
        self.assertIn("daily-pre-execution-summary", html)
        self.assertIn("daily-pre-execution-rows", html)
        self.assertIn("daily-pre-execution-rules", html)
        self.assertIn("daily-pre-execution-steps", html)
        self.assertIn("renderDailyPreExecutionGuard", app_js)
        self.assertIn("daily_pre_execution_guard", app_js)
        self.assertIn("blocked_signal_freshness", app_js)
        self.assertIn("broker_price_outside_guardrail", app_js)
        pre_execution_block = app_js.split("function renderDailyPreExecutionGuard", 1)[1].split(
            "function dailyPreExecutionTone",
            1,
        )[0]
        self.assertIn("信号新鲜度", pre_execution_block)
        self.assertIn("新鲜=", pre_execution_block)
        self.assertIn("纸面演练=", pre_execution_block)
        self.assertIn("今天能买=", pre_execution_block)
        self.assertIn("价格护栏", pre_execution_block)
        self.assertIn("最大滑点", pre_execution_block)
        self.assertIn("流动性/容量", pre_execution_block)
        self.assertIn("流动性证据缺失", pre_execution_block)
        self.assertIn("容量超限", pre_execution_block)
        self.assertNotIn("fresh=", pre_execution_block)
        self.assertNotIn("weight=", pre_execution_block)
        self.assertNotIn("budget=", pre_execution_block)
        self.assertNotIn("qty=", pre_execution_block)
        self.assertNotIn("price=", pre_execution_block)
        self.assertNotIn("guard=", pre_execution_block)
        self.assertNotIn("capacity=", pre_execution_block)
        self.assertNotIn("max_slippage_bps=", pre_execution_block)
        self.assertIn("daily-same-parameter-paper-rehearsal", html)
        self.assertIn("daily-same-parameter-paper-summary", html)
        self.assertIn("daily-same-parameter-paper-requests", html)
        self.assertIn("daily-same-parameter-paper-manifest", html)
        self.assertIn("daily-same-parameter-paper-steps", html)
        self.assertIn("renderDailySameParameterPaperRehearsal", app_js)
        self.assertIn("daily_same_parameter_paper_rehearsal", app_js)
        self.assertIn("ready_for_same_parameter_paper", app_js)
        self.assertIn("run_each_top3_candidate_with_locked_params", app_js)
        self.assertIn("data-same-parameter-paper-run", app_js)
        self.assertIn("sameParameterPaperRequestFromButton", app_js)
        self.assertIn("applySameParameterPaperToForm", app_js)
        self.assertIn("runSameParameterPaperSimulation", app_js)
        self.assertIn("sameParameterPaperCompletion", app_js)
        self.assertIn("renderSameParameterPaperCompletionRows", app_js)
        self.assertIn("dailySameParameterManualReviewGate", app_js)
        self.assertIn("renderSameParameterManualReviewBlocker", app_js)
        self.assertIn("same_parameter_paper_required_before_manual_tickets", app_js)
        self.assertIn("manual_ticket_masked_until_same_parameter_paper", app_js)
        self.assertIn("all_top3_same_parameter_paper_ready", app_js)
        self.assertIn("missing_same_parameter_paper_request_ids", app_js)
        self.assertIn("same_parameter_lock_id", app_js)
        self.assertIn("same_parameter_request_id", app_js)
        self.assertIn("function todayIsoDate", app_js)
        self.assertIn("function applyDailyTradeDateDefault", app_js)
        self.assertIn("staleDailyDateDefaults", app_js)
        self.assertIn("setValue(\"daily-trade-as-of\", today)", app_js)
        self.assertIn("setValue(\"signal-as-of\", today)", app_js)

    def test_next_session_quarantine_summary_only_renders_in_factor_health_monitor(self):
        app_js = Path("src/quant_robot/gui/static/app.js").read_text(encoding="utf-8")
        beginner_trade_block = app_js.split("function renderBeginnerTradeSystem()", 1)[1].split(
            "function renderBeginnerTradeSystemCapitalLadder",
            1,
        )[0]
        factor_health_block = app_js.split("function renderDailyFactorHealthMonitor", 1)[1].split(
            "function dailyFactorHealthTone",
            1,
        )[0]

        self.assertNotIn("nextSessionReuseStatus", beginner_trade_block)
        self.assertNotIn("nextSessionQuarantineTone", beginner_trade_block)
        self.assertIn("nextSessionReuseStatus", factor_health_block)
        self.assertIn("nextSessionQuarantineTone", factor_health_block)
        self.assertIn("next_session_quarantine_required", factor_health_block)
        self.assertIn("same_parameter_top3_matched_requests", factor_health_block)


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

    def test_daily_trade_advisory_parses_leaderboard_factor_window_lists(self):
        self.assertEqual(
            _candidate_factor_windows(
                {
                    "factor_name": "volume_change_20",
                    "params": {"factor_windows": "[5, 10, 20]"},
                }
            ),
            (5, 10, 20),
        )

    def test_daily_trade_advisory_exposes_selected_candidate_alias(self):
        snapshot = build_daily_trade_advisory_snapshot(
            source="demo_fixture",
            market="CN_ETF",
            limit=3,
            risk_profile_id="conservative_10dd",
        )

        self.assertEqual(snapshot["stage"], "phase_6_0_daily_trade_advisory")
        self.assertIn("factors", snapshot)
        self.assertIn("selected_candidates", snapshot)
        self.assertIn("pretrade_workflow", snapshot)
        self.assertIn("pretrade_readiness", snapshot)
        self.assertIn("manual_broker_handoff", snapshot)
        self.assertIn("manual_ticket_export", snapshot)
        self.assertIn("daily_trade_decision_sheet", snapshot)
        self.assertIn("operator_next_actions", snapshot)
        self.assertIn("live_transition_plan", snapshot)
        self.assertIn("trading_system_blueprint", snapshot)
        self.assertIn("daily_signal_execution_bridge", snapshot)
        self.assertIn("real_world_manual_handoff_gate", snapshot)
        self.assertIn("daily_deployment_readiness", snapshot)
        self.assertIn("live_profitability_readiness", snapshot)
        self.assertIn("daily_factor_health_monitor", snapshot)
        self.assertIn("daily_real_money_transition_gate", snapshot)
        self.assertIn("daily_manual_trading_session", snapshot)
        self.assertIn("daily_paper_allocation_playbook", snapshot)
        self.assertIn("daily_pre_execution_guard", snapshot)
        self.assertIn("daily_same_parameter_paper_rehearsal", snapshot)
        self.assertIn("daily_operator_mission_control", snapshot)
        self.assertIn("daily_live_trading_system_status", snapshot)
        self.assertIn("daily_manual_observation_packet", snapshot)
        observation_packet = snapshot["daily_manual_observation_packet"]
        self.assertEqual(observation_packet["stage"], "phase_6_32_daily_manual_observation_packet")
        self.assertEqual(observation_packet["summary"]["primary_market"], "CN_ETF")
        self.assertIn(
            observation_packet["summary"]["packet_status"],
            {
                "blocked_pretrade_red_light",
                "paper_rehearsal_required",
                "manual_observation_material_ready",
                "waiting_for_today_signal",
                "waiting_for_manual_tickets",
            },
        )
        self.assertFalse(observation_packet["summary"]["broker_connection_allowed"])
        self.assertFalse(observation_packet["summary"]["account_read_allowed"])
        self.assertFalse(observation_packet["summary"]["order_placement_allowed"])
        self.assertFalse(observation_packet["summary"]["auto_order_allowed"])
        self.assertIn("top3_factor_snapshot", observation_packet)
        self.assertIn("same_parameter_paper_requests", observation_packet)
        self.assertGreaterEqual(len(observation_packet["top3_factor_snapshot"]), 1)
        self.assertGreaterEqual(len(observation_packet["same_parameter_paper_requests"]), 1)
        self.assertTrue(all(row["direct_buy_allowed"] is False for row in observation_packet["top3_factor_snapshot"]))
        self.assertTrue(all(row["order_placement_allowed"] is False for row in observation_packet["top3_factor_snapshot"]))
        self.assertTrue(
            all(row["order_placement_allowed"] is False for row in observation_packet["same_parameter_paper_requests"])
        )
        self.assertTrue(all(row["auto_order_allowed"] is False for row in observation_packet["same_parameter_paper_requests"]))
        self.assertIn("manual_ticket_preview", observation_packet)
        self.assertIn("evidence_rows", observation_packet)
        self.assertIn("run_same_parameter_paper", {row["step_id"] for row in observation_packet["operator_steps"]})
        self.assertEqual(
            snapshot["daily_operator_mission_control"]["stage"],
            "phase_6_30_daily_operator_mission_control",
        )
        self.assertFalse(snapshot["daily_operator_mission_control"]["summary"]["order_placement_allowed"])
        live_system = snapshot["daily_live_trading_system_status"]
        self.assertEqual(live_system["stage"], "phase_6_31_daily_live_trading_system_status")
        self.assertEqual(live_system["summary"]["daily_top3_policy"], "top3_candidates_not_orders")
        self.assertFalse(live_system["summary"]["direct_buy_top3_allowed"])
        self.assertFalse(live_system["summary"]["broker_connection_allowed"])
        self.assertFalse(live_system["summary"]["account_read_allowed"])
        self.assertFalse(live_system["summary"]["order_placement_allowed"])
        self.assertFalse(live_system["summary"]["auto_order_allowed"])
        live_step_ids = {row["step_id"] for row in live_system["operating_ladder"]}
        self.assertIn("select_top3_candidates", live_step_ids)
        self.assertIn("run_same_parameter_paper", live_step_ids)
        self.assertIn("manual_broker_review", live_step_ids)
        self.assertTrue(all(row["order_placement_allowed"] is False for row in live_system["operating_ladder"]))
        self.assertEqual(
            snapshot["daily_operator_mission_control"]["live_trading_system_status"]["stage"],
            "phase_6_31_daily_live_trading_system_status",
        )
        self.assertIn(
            "live_trading_system_status",
            {row["card_id"] for row in snapshot["daily_operator_mission_control"]["cards"]},
        )
        self.assertIn("candidate_pool_top20", snapshot)
        self.assertEqual(snapshot["candidate_pool_top20"]["stage"], "phase_6_22_daily_candidate_pool_top20")
        self.assertIn("rows", snapshot["candidate_pool_top20"])
        self.assertFalse(snapshot["candidate_pool_top20"]["summary"]["direct_buy_from_leaderboard_allowed"])
        same_paper = snapshot["daily_same_parameter_paper_rehearsal"]
        self.assertEqual(same_paper["stage"], "phase_6_27_daily_same_parameter_paper_rehearsal")
        self.assertGreaterEqual(len(same_paper["recommended_requests"]), 1)
        same_paper_request = same_paper["recommended_requests"][0]
        self.assertEqual(same_paper_request["same_parameter_lock_id"], same_paper["lock_id"])
        self.assertEqual(same_paper_request["same_parameter_request_id"], same_paper_request["request_id"])
        self.assertIn("/api/paper?", same_paper_request["request_url"])
        self.assertIn("query_string", same_paper_request)
        query = parse_qs(urlparse(same_paper_request["request_url"]).query)
        self.assertEqual(query["market"], ["CN_ETF"])
        self.assertEqual(query["factor"], [same_paper_request["factor"]])
        self.assertEqual(query["top_n"], [str(same_paper_request["top_n"])])
        self.assertEqual(query["same_parameter_lock_id"], [same_paper["lock_id"]])
        self.assertEqual(query["same_parameter_request_id"], [same_paper_request["request_id"]])
        self.assertFalse(same_paper_request["order_placement_allowed"])
        self.assertEqual(snapshot["selected_candidates"], snapshot["factors"])
        self.assertEqual(snapshot["pretrade_workflow"]["stage"], "phase_6_1_daily_pretrade_workflow")
        self.assertFalse(snapshot["pretrade_workflow"]["summary"]["live_order_allowed"])
        self.assertEqual(snapshot["live_transition_plan"]["stage"], "phase_6_7_live_transition_plan")
        self.assertFalse(snapshot["live_transition_plan"]["summary"]["order_placement_allowed"])
        self.assertEqual(snapshot["trading_system_blueprint"]["stage"], "phase_6_15_daily_trading_system_blueprint")
        self.assertTrue(snapshot["trading_system_blueprint"]["summary"]["daily_top3_signal_supported"])
        self.assertFalse(snapshot["trading_system_blueprint"]["summary"]["direct_live_trading_supported"])
        self.assertFalse(snapshot["trading_system_blueprint"]["candidate_pool_policy"]["direct_buy_from_leaderboard_allowed"])
        self.assertIn("paper_simulation_receipt", {item["evidence_id"] for item in snapshot["trading_system_blueprint"]["evidence_chain"]})
        self.assertIn("manual_broker_review", {item["step_id"] for item in snapshot["trading_system_blueprint"]["operator_buy_process"]})
        self.assertTrue(
            all(
                item["order_placement_allowed"] is False
                for item in snapshot["trading_system_blueprint"]["operator_buy_process"]
            )
        )
        bridge = snapshot["daily_signal_execution_bridge"]
        self.assertEqual(bridge["stage"], "phase_6_16_daily_signal_execution_bridge")
        self.assertEqual(bridge["summary"]["primary_market"], "CN_ETF")
        self.assertTrue(bridge["summary"]["daily_top3_signal_supported"])
        self.assertFalse(bridge["summary"]["direct_buy_from_top3_allowed"])
        self.assertFalse(bridge["summary"]["order_placement_allowed"])
        self.assertFalse(bridge["summary"]["auto_order_allowed"])
        self.assertIn("select_top3_candidates", {item["step_id"] for item in bridge["daily_operating_steps"]})
        self.assertIn("manual_broker_review", {item["step_id"] for item in bridge["daily_operating_steps"]})
        self.assertIn("post_close_journal", {item["step_id"] for item in bridge["daily_operating_steps"]})
        self.assertTrue(all(item["order_placement_allowed"] is False for item in bridge["daily_operating_steps"]))
        self.assertIn("paper_simulation_receipt", {item["gate_id"] for item in bridge["deployment_gates"]})
        self.assertIn("manual_broker_review", {item["gate_id"] for item in bridge["deployment_gates"]})
        handoff = bridge["paper_simulation_handoff"]
        self.assertEqual(handoff["stage"], "daily_signal_paper_simulation_handoff")
        self.assertEqual(handoff["recommended_request"]["market"], "CN_ETF")
        self.assertEqual(handoff["recommended_request"]["initial_cash"], 100000.0)
        self.assertIn("factor", handoff["recommended_request"])
        self.assertIn("factor_windows", handoff["recommended_request"])
        self.assertIn("top_n", handoff["recommended_request"])
        self.assertFalse(handoff["summary"]["order_placement_allowed"])
        self.assertFalse(handoff["summary"]["auto_order_allowed"])
        real_world_gate = snapshot["real_world_manual_handoff_gate"]
        self.assertEqual(real_world_gate["stage"], "phase_6_17_real_world_manual_handoff_gate")
        self.assertEqual(real_world_gate["summary"]["primary_market"], "CN_ETF")
        self.assertFalse(real_world_gate["summary"]["direct_buy_from_top3_allowed"])
        self.assertFalse(real_world_gate["summary"]["broker_connection_allowed"])
        self.assertIn("human_broker_manual_decision", {item["step_id"] for item in real_world_gate["manual_operation_runbook"]})
        self.assertIn("paper_simulation_receipt", {item["gate_id"] for item in real_world_gate["go_live_blockers"]})
        self.assertIn("capital_deployment_ladder", real_world_gate)
        self.assertIn("production_manual_review", {item["stage_id"] for item in real_world_gate["capital_deployment_ladder"]})
        deployment = snapshot["daily_deployment_readiness"]
        self.assertEqual(deployment["stage"], "phase_6_18_daily_deployment_readiness_pack")
        self.assertTrue(deployment["summary"]["daily_top3_supported"])
        self.assertFalse(deployment["summary"]["direct_buy_from_top3_allowed"])
        self.assertFalse(deployment["summary"]["order_placement_allowed"])
        self.assertIn("same_parameter_paper_rehearsal", {item["step_id"] for item in deployment["daily_operating_sequence"]})
        self.assertIn("paper_simulation_receipt", {item["gate_id"] for item in deployment["readiness_gates"]})
        profitability = snapshot["live_profitability_readiness"]
        self.assertEqual(profitability["stage"], "phase_6_19_live_profitability_readiness_scorecard")
        self.assertIn(
            profitability["summary"]["decision"],
            {"blocked_pretrade_red_light", "not_ready_for_real_money"},
        )
        self.assertFalse(profitability["summary"]["profitability_claim_allowed"])
        self.assertFalse(profitability["summary"]["real_money_allowed"])
        self.assertFalse(profitability["summary"]["order_placement_allowed"])
        self.assertIn("matched_paper_receipts", {item["gate_id"] for item in profitability["hard_gates"]})
        self.assertIn("follow_primary_next_step", {item["action_id"] for item in profitability["today_allowed_actions"]})
        self.assertIn("direct_buy_top3", {item["action_id"] for item in profitability["forbidden_actions"]})
        health = snapshot["daily_factor_health_monitor"]
        self.assertEqual(health["stage"], "phase_6_20_daily_factor_health_monitor")
        self.assertIn(
            health["summary"]["decision"],
            {"factor_health_watch_required", "retire_or_reduce_weight_required", "factor_health_clear_for_paper"},
        )
        self.assertFalse(health["summary"]["top3_auto_buy_allowed"])
        self.assertFalse(health["summary"]["order_placement_allowed"])
        self.assertTrue(all(row["order_placement_allowed"] is False for row in health["factor_rows"]))
        transition = snapshot["daily_real_money_transition_gate"]
        self.assertEqual(transition["stage"], "phase_6_21_daily_real_money_transition_gate")
        self.assertIn(
            transition["summary"]["decision"],
            {
                "paper_rehearsal_required",
                "rotate_or_reduce_top3_first",
                "blocked_pretrade_red_light",
                "production_manual_review_candidate",
                "small_capital_manual_observation_candidate",
            },
        )
        self.assertFalse(transition["summary"]["real_money_allowed"])
        self.assertFalse(transition["summary"]["order_placement_allowed"])
        self.assertIn("manual_ticket_risk_budget", {row["gate_id"] for row in transition["preflight_rows"]})
        self.assertIn("open_external_broker_manually", {row["step_id"] for row in transition["operator_script"]})
        self.assertIn("direct_buy_top3", {row["action_id"] for row in transition["forbidden_actions"]})
        session = snapshot["daily_manual_trading_session"]
        self.assertEqual(session["stage"], "phase_6_24_daily_manual_trading_session")
        self.assertIn(
            session["summary"]["session_status"],
            {
                "blocked_pretrade_red_light",
                "blocked_same_parameter_paper_required",
                "blocked_factor_health_rotation_required",
                "paper_rehearsal_required",
                "production_manual_review_candidate",
                "small_capital_manual_observation_candidate",
            },
        )
        self.assertFalse(session["summary"]["order_placement_allowed"])
        self.assertFalse(session["summary"]["broker_connection_allowed"])
        self.assertIn("record_post_close_journal", {row["step_id"] for row in session["operator_checklist"]})
        self.assertTrue(all(row["order_placement_allowed"] is False for row in session["operator_checklist"]))
        allocation = snapshot["daily_paper_allocation_playbook"]
        self.assertEqual(allocation["stage"], "phase_6_25_daily_paper_allocation_playbook")
        self.assertIn(
            allocation["summary"]["allocation_status"],
            {
                "blocked_pretrade_red_light",
                "blocked_factor_health_rotation_required",
                "blocked_no_allocation_rows",
                "blocked_risk_budget",
                "paper_rehearsal_required",
                "manual_review_candidate",
            },
        )
        self.assertFalse(allocation["summary"]["order_placement_allowed"])
        self.assertFalse(allocation["summary"]["broker_connection_allowed"])
        self.assertIn("same_parameter_paper", {row["gate_id"] for row in allocation["promotion_gates"]})
        self.assertIn("run_same_parameter_paper", {row["step_id"] for row in allocation["operator_steps"]})
        self.assertTrue(all(row["order_placement_allowed"] is False for row in allocation["allocation_rows"]))
        pre_execution = snapshot["daily_pre_execution_guard"]
        self.assertEqual(pre_execution["stage"], "phase_6_26_daily_pre_execution_guard")
        self.assertIn(
            pre_execution["summary"]["guard_status"],
            {
                "blocked_signal_freshness",
                "blocked_no_allocation_rows",
                "blocked_risk_budget",
                "blocked_price_reference",
                "paper_rehearsal_only",
                "manual_review_candidate",
            },
        )
        self.assertFalse(pre_execution["summary"]["can_buy_today"])
        self.assertFalse(pre_execution["summary"]["order_placement_allowed"])
        self.assertIn("broker_price_outside_guardrail", {row["rule_id"] for row in pre_execution["skip_rules"]})
        self.assertIn("verify_realtime_price_guardrail", {row["step_id"] for row in pre_execution["operator_steps"]})
        self.assertTrue(all(row["order_placement_allowed"] is False for row in pre_execution["row_guardrails"]))
        same_paper = snapshot["daily_same_parameter_paper_rehearsal"]
        self.assertEqual(same_paper["stage"], "phase_6_27_daily_same_parameter_paper_rehearsal")
        self.assertIn(
            same_paper["summary"]["rehearsal_status"],
            {
                "blocked_signal_freshness",
                "blocked_no_allocation_rows",
                "blocked_risk_budget",
                "blocked_price_reference",
                "ready_for_same_parameter_paper",
                "manual_review_candidate",
            },
        )
        self.assertFalse(same_paper["summary"]["order_placement_allowed"])
        self.assertIn("paper_simulation", same_paper["summary"]["workflow_id"])
        self.assertIn("run_each_top3_candidate_with_locked_params", {row["step_id"] for row in same_paper["operator_steps"]})
        beginner_execution = snapshot["daily_beginner_execution_answer"]
        self.assertEqual(beginner_execution["stage"], "phase_6_28_daily_beginner_execution_answer")
        self.assertIn(
            beginner_execution["summary"]["allowed_mode"],
            {
                "blocked_no_action",
                "same_parameter_paper_rehearsal_only",
                "manual_review_material_only",
            },
        )
        self.assertFalse(beginner_execution["summary"]["can_buy_today"])
        self.assertFalse(beginner_execution["summary"]["order_placement_allowed"])
        self.assertIn("review_rows", beginner_execution)
        self.assertEqual(snapshot["live_transition_plan"]["summary"]["selected_risk_profile_id"], "conservative_10dd")
        self.assertEqual(snapshot["summary"]["risk_profile_id"], "conservative_10dd")
        self.assertIn("small_capital_review_gate", {gate["gate_id"] for gate in snapshot["live_transition_plan"]["evidence_gates"]})
        self.assertIn("primary_next_action_id", snapshot["pretrade_workflow"]["summary"])
        self.assertEqual(snapshot["pretrade_readiness"]["stage"], "phase_6_2_manual_pretrade_readiness")
        self.assertFalse(snapshot["pretrade_readiness"]["live_order_allowed"])
        self.assertIn("freshness", snapshot["pretrade_readiness"])
        self.assertIn("signal_freshness", {item["check_id"] for item in snapshot["pretrade_readiness"]["required_confirmations"]})
        self.assertEqual(snapshot["manual_broker_handoff"]["stage"], "phase_6_3_manual_broker_handoff")
        self.assertFalse(snapshot["manual_broker_handoff"]["order_placement_allowed"])
        self.assertEqual(snapshot["manual_ticket_export"]["stage"], "phase_6_13_manual_ticket_export")
        self.assertFalse(snapshot["manual_ticket_export"]["summary"]["order_placement_allowed"])
        self.assertEqual(snapshot["daily_trade_decision_sheet"]["stage"], "phase_6_14_daily_trade_decision_sheet")
        self.assertFalse(snapshot["daily_trade_decision_sheet"]["summary"]["order_placement_allowed"])
        self.assertIn("daily_top3", snapshot["daily_trade_decision_sheet"])
        self.assertIn("candidate_pool_top20", snapshot["daily_trade_decision_sheet"])
        self.assertFalse(
            snapshot["daily_trade_decision_sheet"]["candidate_pool_top20"]["summary"][
                "direct_buy_from_leaderboard_allowed"
            ]
        )
        self.assertEqual(len(snapshot["pretrade_workflow"]["steps"]), 5)
        self.assertGreaterEqual(len(snapshot["operator_next_actions"]), 1)
        self.assertEqual(snapshot["operator_next_actions"][0]["automation_allowed"], False)
        self.assertLessEqual(snapshot["summary"]["selected_factor_count"], 3)

    def test_daily_trade_advisory_accepts_runtime_evidence_snapshot(self):
        snapshot = build_daily_trade_advisory_snapshot(
            source="demo_fixture",
            market="CN_ETF",
            limit=3,
            evidence_snapshot={
                "mode": "browser_execution_receipts",
                "counts": {
                    "matched_paper_receipts": 5,
                    "post_close_journal_receipts": 5,
                    "manual_execution_clean_receipts": 5,
                    "manual_execution_blocked_receipts": 0,
                    "paper_ready_observations": 20,
                },
                "flags": {
                    "walk_forward_oos_passed": True,
                    "lookahead_bias_audit_passed": True,
                    "multiple_testing_control_passed": True,
                    "transaction_cost_capacity_passed": True,
                },
            },
        )

        readiness = snapshot["live_profitability_readiness"]
        transition = snapshot["daily_real_money_transition_gate"]

        self.assertEqual(readiness["summary"]["evidence_mode"], "browser_execution_receipts")
        self.assertEqual(readiness["summary"]["matched_paper_receipts"], 5)
        self.assertEqual(readiness["summary"]["post_close_journal_receipts"], 5)
        self.assertEqual(readiness["summary"]["manual_execution_clean_receipts"], 5)
        self.assertEqual(readiness["summary"]["manual_execution_blocked_receipts"], 0)
        self.assertEqual(readiness["summary"]["paper_ready_observations"], 20)
        self.assertEqual(readiness["evidence_snapshot"]["missing_counts"]["matched_paper_receipts"], 0)
        self.assertEqual(readiness["evidence_snapshot"]["missing_counts"]["manual_execution_clean_receipts"], 0)
        self.assertFalse(readiness["summary"]["order_placement_allowed"])
        self.assertFalse(transition["summary"]["order_placement_allowed"])

    def test_daily_trade_advisory_fallback_baseline_is_observation_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reports_root = root / "reports"
            configs_root = root / "configs"
            reports_root.mkdir()
            configs_root.mkdir()

            snapshot = build_daily_trade_advisory_snapshot(
                reports_root=reports_root,
                configs_root=configs_root,
                source="demo_fixture",
                market="CN_ETF",
                limit=3,
                as_of_date="2026-05-21",
            )

        self.assertTrue(snapshot["fallback_used"])
        self.assertTrue(snapshot["summary"]["fallback_signal_only"])
        self.assertTrue(snapshot["summary"]["manual_trade_plan_blocked"])
        self.assertEqual(snapshot["summary"]["manual_trade_plan_blocked_reason"], "fallback_baseline_not_tradeable")
        self.assertEqual(snapshot["summary"]["manual_ticket_count"], 0)
        self.assertEqual(snapshot["manual_trade_plan"], [])
        self.assertTrue(all(row["fallback_baseline"] for row in snapshot["selected_candidates"]))
        self.assertFalse(any(row["manual_trade_allowed"] for row in snapshot["selected_candidates"]))
        self.assertFalse(snapshot["pretrade_readiness"]["manual_action_candidate"])
        self.assertIn("fallback_baseline_not_tradeable", snapshot["pretrade_readiness"]["blockers"])
        self.assertEqual(
            snapshot["daily_deployment_readiness"]["summary"]["decision"],
            "blocked_pretrade_red_light",
        )
        self.assertFalse(snapshot["daily_deployment_readiness"]["summary"]["paper_rehearsal_allowed"])
        self.assertFalse(snapshot["daily_deployment_readiness"]["summary"]["manual_review_material_ready"])
        self.assertEqual(snapshot["daily_deployment_readiness"]["manual_buy_sell_preview"], [])
        self.assertIn(
            "qualified_candidate_gate",
            {row["gate_id"] for row in snapshot["daily_deployment_readiness"]["readiness_gates"]},
        )
        self.assertEqual(
            snapshot["real_world_manual_handoff_gate"]["summary"]["decision"],
            "blocked_pretrade_red_light",
        )

        app_js = Path("src/quant_robot/gui/static/app.js").read_text(encoding="utf-8")
        self.assertIn("fallback_baseline_not_tradeable", app_js)
        self.assertIn("兜底基线仅供观察", app_js)

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
            {
                "research_backtest",
                "signal_snapshot",
                "daily_pretrade_checkup",
                "paper_simulation",
                "verification_runner",
                "live_trading",
            },
        )
        self.assertEqual(preflight_rows["research_backtest"]["status"], "ready_to_run")
        self.assertTrue(preflight_rows["research_backtest"]["runnable"])
        self.assertIn("/api/research?", preflight_rows["research_backtest"]["endpoint"])
        self.assertEqual(preflight_rows["daily_pretrade_checkup"]["mode"], "manual_pretrade_checkup")
        self.assertTrue(preflight_rows["daily_pretrade_checkup"]["runnable"])
        self.assertFalse(preflight_rows["daily_pretrade_checkup"]["permissions"]["order_placement_allowed"])
        self.assertIn(
            "daily_trade_advisory",
            {check["check_id"] for check in preflight_rows["daily_pretrade_checkup"]["checks"]},
        )
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
        self.assertTrue(any(item.get("workflow_id") == "daily_pretrade_checkup" for item in action_rows))
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

    def test_control_center_builds_daily_closure_ledger_from_server_receipts(self):
        from quant_robot.gui.control_center import build_control_center_snapshot
        from quant_robot.gui.operation_ledger import append_operation_ledger_entry

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="daily_trade_advisory",
                label="Generate top-three manual trade advisory",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": "2026-06-30"},
                result={
                    "stage": "phase_daily_trade_advisory",
                    "summary": {"signal_count": 3, "selected_factor_count": 3},
                    "metrics": {"signal_count": 3, "manual_ticket_count": 2},
                },
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="paper_simulation",
                label="Run local paper simulation",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": "2026-06-30", "factor_name": "momentum_2", "top_n": 2},
                result={"stage": "gui_paper_simulation", "metrics": {"total_return": 0.12, "max_drawdown": -0.18}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="post_close_journal",
                label="Post-close journal receipt",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": "2026-06-30"},
                result={
                    "stage": "phase_post_close_journal",
                    "metrics": {
                        "manual_review_recorded": True,
                        "manual_execution_decision": "manual_execution_evidence_ready",
                        "manual_execution_missing_review_count": 0,
                        "manual_execution_guardrail_breach_count": 0,
                        "manual_execution_slippage_breach_count": 0,
                    },
                },
            )

            control = build_control_center_snapshot(repo_root=root)

        ledger = control["daily_closure_ledger"]
        self.assertEqual(ledger["stage"], "gui_daily_closure_ledger")
        self.assertEqual(ledger["summary"]["closed_loop_days"], 1)
        self.assertEqual(ledger["summary"]["server_observed_days"], 1)
        self.assertFalse(ledger["summary"]["live_trading_allowed"])
        self.assertFalse(ledger["summary"]["order_placement_allowed"])
        self.assertEqual(ledger["rows"][0]["date"], "2026-06-30")
        self.assertTrue(ledger["rows"][0]["top3_signal_ready"])
        self.assertTrue(ledger["rows"][0]["same_parameter_paper_ready"])
        self.assertTrue(ledger["rows"][0]["post_close_journal_ready"])
        self.assertTrue(ledger["rows"][0]["manual_execution_clean"])
        self.assertTrue(ledger["rows"][0]["completed_loop"])

    def test_daily_closure_ledger_requires_all_top3_same_parameter_paper_receipts(self):
        from quant_robot.gui.control_center import build_control_center_snapshot
        from quant_robot.gui.operation_ledger import append_operation_ledger_entry

        def paper_request(index: int, factor: str) -> dict[str, object]:
            return {
                "request_id": f"top3-paper-00{index}",
                "same_parameter_request_id": f"top3-paper-00{index}",
                "same_parameter_lock_id": "lock_top3_001",
                "market": "CN_ETF",
                "factor": factor,
                "factor_name": factor,
                "factor_windows": "2",
                "top_n": 2,
                "rebalance_interval": 1,
                "as_of_date": "2026-06-30",
                "run_date": "2026-06-30",
                "initial_cash": 100000.0,
                "commission_bps": 5.0,
                "slippage_bps": 5.0,
                "max_asset_weight": 0.3,
                "max_market_weight": 1.0,
                "max_gross_exposure": 0.6,
                "min_cash_weight": 0.4,
            }

        top3_requests = [
            paper_request(1, "momentum_2"),
            paper_request(2, "reversal_5"),
            paper_request(3, "liquidity_20"),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="daily_trade_advisory",
                label="Generate top-three manual trade advisory",
                status="completed",
                request={
                    "market": "CN_ETF",
                    "as_of_date": "2026-06-30",
                    "signal_count": 3,
                    "selected_factor_count": 3,
                    "same_parameter_lock_id": "lock_top3_001",
                    "same_parameter_top3_paper_requests": top3_requests,
                },
                result={"stage": "phase_daily_trade_advisory", "metrics": {"signal_count": 3}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="paper_simulation",
                label="Run local paper simulation",
                status="completed",
                request=top3_requests[0],
                result={"stage": "gui_paper_simulation", "metrics": {"total_return": 0.12, "max_drawdown": -0.18}},
            )

            partial = build_control_center_snapshot(repo_root=root)["daily_closure_ledger"]["rows"][0]

            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="paper_simulation",
                label="Run local paper simulation",
                status="completed",
                request=top3_requests[1],
                result={"stage": "gui_paper_simulation", "metrics": {"total_return": 0.05, "max_drawdown": -0.08}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="paper_simulation",
                label="Run local paper simulation",
                status="completed",
                request=top3_requests[2],
                result={"stage": "gui_paper_simulation", "metrics": {"total_return": 0.03, "max_drawdown": -0.06}},
            )

            complete = build_control_center_snapshot(repo_root=root)["daily_closure_ledger"]["rows"][0]

        self.assertFalse(partial["same_parameter_paper_ready"])
        self.assertEqual(partial["paper_request_match_status"], "partial")
        self.assertEqual(partial["same_parameter_paper_required_count"], 3)
        self.assertEqual(partial["same_parameter_paper_matched_count"], 1)
        self.assertEqual(partial["matched_same_parameter_paper_request_ids"], ["top3-paper-001"])
        self.assertEqual(
            partial["missing_same_parameter_paper_request_ids"],
            ["top3-paper-002", "top3-paper-003"],
        )
        self.assertTrue(complete["same_parameter_paper_ready"])
        self.assertEqual(complete["paper_request_match_status"], "matched")
        self.assertEqual(complete["same_parameter_paper_matched_count"], 3)
        self.assertEqual(complete["missing_same_parameter_paper_request_ids"], [])

    def test_daily_closure_ledger_blocks_mismatched_same_parameter_paper_receipt(self):
        from quant_robot.gui.control_center import build_control_center_snapshot
        from quant_robot.gui.operation_ledger import append_operation_ledger_entry

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            expected_paper_request = {
                "market": "CN_ETF",
                "factor_name": "momentum_2",
                "top_n": 2,
                "commission_bps": 5,
                "max_gross_exposure": 0.6,
                "as_of_date": "2026-06-30",
            }
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="daily_trade_advisory",
                label="Generate top-three manual trade advisory",
                status="completed",
                request={
                    "market": "CN_ETF",
                    "as_of_date": "2026-06-30",
                    "paper_request_signature": expected_paper_request,
                },
                result={"metrics": {"signal_count": 3, "selected_factor_count": 3}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="paper_simulation",
                label="Run local paper simulation",
                status="completed",
                request={
                    "market": "CN_ETF",
                    "factor_name": "reversal_2",
                    "top_n": 2,
                    "commission_bps": 5,
                    "max_gross_exposure": 0.6,
                    "as_of_date": "2026-06-30",
                },
                result={"stage": "gui_paper_simulation", "metrics": {"total_return": 0.12, "max_drawdown": -0.18}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="post_close_journal",
                label="Post-close journal receipt",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": "2026-06-30"},
                result={
                    "metrics": {
                        "manual_review_recorded": True,
                        "manual_execution_decision": "manual_execution_evidence_ready",
                        "manual_execution_missing_review_count": 0,
                        "manual_execution_guardrail_breach_count": 0,
                        "manual_execution_slippage_breach_count": 0,
                    }
                },
            )

            control = build_control_center_snapshot(repo_root=root)

        row = control["daily_closure_ledger"]["rows"][0]
        self.assertTrue(row["top3_signal_ready"])
        self.assertFalse(row["same_parameter_paper_ready"])
        self.assertEqual(row["paper_request_match_status"], "mismatched")
        self.assertIn("factor_name", row["paper_request_mismatch_keys"])
        self.assertIn("paper_simulation", row["missing_steps"])
        self.assertFalse(row["completed_loop"])

    def test_daily_closure_ledger_accepts_matching_signature_with_factor_window_list(self):
        from quant_robot.gui.control_center import build_control_center_snapshot
        from quant_robot.gui.operation_ledger import append_operation_ledger_entry

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            expected_paper_request = {
                "market": "CN_ETF",
                "factor_name": "momentum_2",
                "factor_windows": [2, 5, 20],
                "top_n": "2",
                "commission_bps": "5.0",
                "as_of_date": "2026-06-30",
            }
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="daily_trade_advisory",
                label="Generate top-three manual trade advisory",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": "2026-06-30", "paper_request_signature": expected_paper_request},
                result={"metrics": {"signal_count": 3, "selected_factor_count": 3}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="paper_simulation",
                label="Run local paper simulation",
                status="completed",
                request={
                    "market": "cn_etf",
                    "factor": "momentum_2",
                    "factor_windows": [2, 5, 20],
                    "top_n": 2,
                    "commission_bps": 5,
                    "as_of_date": "2026-06-30",
                },
                result={"stage": "gui_paper_simulation", "metrics": {"total_return": 0.12, "max_drawdown": -0.18}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="post_close_journal",
                label="Post-close journal receipt",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": "2026-06-30"},
                result={
                    "metrics": {
                        "manual_review_recorded": True,
                        "manual_execution_decision": "manual_execution_evidence_ready",
                        "manual_execution_missing_review_count": 0,
                        "manual_execution_guardrail_breach_count": 0,
                        "manual_execution_slippage_breach_count": 0,
                    }
                },
            )

            control = build_control_center_snapshot(repo_root=root)

        row = control["daily_closure_ledger"]["rows"][0]
        self.assertTrue(row["same_parameter_paper_ready"])
        self.assertEqual(row["paper_request_match_status"], "matched")
        self.assertEqual(row["paper_request_mismatch_keys"], [])
        self.assertTrue(row["completed_loop"])

    def test_control_center_promotes_only_clean_server_closure_streak_to_small_capital_candidate(self):
        from quant_robot.gui.control_center import build_control_center_snapshot
        from quant_robot.gui.operation_ledger import append_operation_ledger_entry

        def append_clean_day(root: Path, day: str) -> None:
            paper_request = {
                "market": "CN_ETF",
                "factor_name": "momentum_2",
                "top_n": 2,
                "commission_bps": 5,
                "as_of_date": day,
            }
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="daily_trade_advisory",
                label="Generate top-three manual trade advisory",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": day, "paper_request_signature": paper_request},
                result={"metrics": {"signal_count": 3, "selected_factor_count": 3}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="paper_simulation",
                label="Run local paper simulation",
                status="completed",
                request=paper_request,
                result={"metrics": {"total_return": 0.01, "max_drawdown": -0.02}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="post_close_journal",
                label="Post-close journal receipt",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": day},
                result={
                    "metrics": {
                        "manual_review_recorded": True,
                        "manual_execution_decision": "manual_execution_evidence_ready",
                        "manual_execution_missing_review_count": 0,
                        "manual_execution_guardrail_breach_count": 0,
                        "manual_execution_slippage_breach_count": 0,
                    },
                },
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for day in ["2026-06-24", "2026-06-25", "2026-06-26", "2026-06-29", "2026-06-30"]:
                append_clean_day(root, day)

            control = build_control_center_snapshot(repo_root=root)

        gate = control["server_capital_observation_gate"]
        self.assertEqual(gate["stage"], "gui_server_capital_observation_gate")
        self.assertEqual(gate["summary"]["status"], "manual_small_capital_observation_candidate")
        self.assertTrue(gate["summary"]["manual_small_capital_observation_candidate"])
        self.assertEqual(gate["summary"]["server_closed_loop_days"], 5)
        self.assertFalse(gate["summary"]["live_trading_allowed"])
        self.assertFalse(gate["summary"]["order_placement_allowed"])
        self.assertFalse(gate["summary"]["broker_connection_allowed"])
        self.assertFalse(gate["summary"]["account_read_allowed"])
        self.assertIn("server_closure_streak", {row["gate_id"] for row in gate["rows"]})
        self.assertIn("live_boundary", {row["gate_id"] for row in gate["rows"]})
        scorecard = gate["evidence_scorecard"]
        score_rows = {row["gate_id"]: row for row in scorecard["rows"]}
        self.assertEqual(scorecard["stage"], "gui_small_capital_observation_evidence_scorecard")
        self.assertEqual(scorecard["summary"]["status"], "ready_for_manual_small_capital_packet")
        self.assertEqual(scorecard["summary"]["readiness_score_pct"], 100)
        self.assertEqual(scorecard["summary"]["next_missing_gate_id"], "")
        self.assertTrue(scorecard["summary"]["manual_observation_material_ready"])
        self.assertFalse(scorecard["summary"]["order_placement_allowed"])
        self.assertEqual(score_rows["server_closed_loop_days"]["current_value"], 5)
        self.assertEqual(score_rows["same_parameter_paper_days"]["status"], "pass")
        self.assertEqual(score_rows["blocked_manual_execution_days"]["required_value"], 0)

    def test_legacy_unverified_paper_receipts_do_not_unlock_small_capital_gate(self):
        from quant_robot.gui.control_center import build_control_center_snapshot
        from quant_robot.gui.operation_ledger import append_operation_ledger_entry

        def append_legacy_day(root: Path, day: str) -> None:
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="daily_trade_advisory",
                label="Generate top-three manual trade advisory",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": day},
                result={"metrics": {"signal_count": 3, "selected_factor_count": 3}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="paper_simulation",
                label="Run local paper simulation",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": day, "factor_name": "momentum_2", "top_n": 2},
                result={"metrics": {"total_return": 0.01, "max_drawdown": -0.02}},
            )
            append_operation_ledger_entry(
                repo_root=root,
                workflow_id="post_close_journal",
                label="Post-close journal receipt",
                status="completed",
                request={"market": "CN_ETF", "as_of_date": day},
                result={
                    "metrics": {
                        "manual_review_recorded": True,
                        "manual_execution_decision": "manual_execution_evidence_ready",
                        "manual_execution_missing_review_count": 0,
                        "manual_execution_guardrail_breach_count": 0,
                        "manual_execution_slippage_breach_count": 0,
                    },
                },
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            for day in ["2026-06-24", "2026-06-25", "2026-06-26", "2026-06-29", "2026-06-30"]:
                append_legacy_day(root, day)

            control = build_control_center_snapshot(repo_root=root)

        ledger = control["daily_closure_ledger"]
        gate = control["server_capital_observation_gate"]
        self.assertEqual(ledger["summary"]["matched_paper_days"], 0)
        self.assertTrue(all(row["paper_request_match_status"] == "legacy_unverified" for row in ledger["rows"]))
        self.assertEqual(gate["summary"]["status"], "blocked_need_same_parameter_paper_evidence")
        self.assertFalse(gate["summary"]["manual_small_capital_observation_candidate"])
        self.assertEqual(gate["summary"]["matched_paper_days"], 0)
        self.assertIn("same_parameter_paper_evidence", {row["gate_id"] for row in gate["rows"]})
        scorecard = gate["evidence_scorecard"]
        self.assertEqual(scorecard["summary"]["status"], "blocked_need_more_evidence")
        self.assertEqual(scorecard["summary"]["next_missing_gate_id"], "same_parameter_paper_days")
        self.assertEqual(scorecard["summary"]["readiness_score_pct"], 80)
        self.assertFalse(scorecard["summary"]["manual_observation_material_ready"])

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
                self.assertIn("daily_closure_ledger_panel", check_ids)
                self.assertIn("server_capital_observation_gate_panel", check_ids)
                self.assertIn("audit_scheduler_panel", check_ids)
                self.assertIn("verification_runner_panel", check_ids)
                self.assertIn("audit_feedback_panel", check_ids)
                self.assertIn("audit_iteration_plan_panel", check_ids)
                self.assertIn("beginner_live_handoff_frontend", check_ids)
                self.assertIn("beginner_live_handoff_red_light_guard", check_ids)
                self.assertIn("manual_broker_price_check_frontend", check_ids)
                self.assertIn("position_reconciliation_frontend", check_ids)
                self.assertIn("manual_execution_cost_impact_frontend", check_ids)
                self.assertIn("daily_closure_streak_frontend", check_ids)
                self.assertIn("daily_manual_observation_packet_frontend", check_ids)
                self.assertIn("daily_manual_observation_packet_detail_frontend", check_ids)
                self.assertIn("daily_manual_observation_go_no_go_frontend", check_ids)
                self.assertIn("daily_trading_runtime_contract_frontend", check_ids)
                self.assertIn("daily_beginner_final_operation_packet_frontend", check_ids)
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
                        "signal": {
                            "as_of_date": "2026-05-22",
                            "signal_date": "2026-05-22",
                            "run_date": "2026-06-13",
                            "signal_age_days": 22,
                            "max_signal_age_days": 7,
                            "freshness_status": "blocked_stale_signal",
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
        self.assertEqual(result["signal"]["signal_age_days"], 22)
        self.assertEqual(result["signal"]["max_signal_age_days"], 7)
        self.assertEqual(result["signal"]["freshness_status"], "blocked_stale_signal")
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
            self.assertIn("data-ordinary-live-gate-root", html)
            self.assertIn("beginner-guide-board", html)
            self.assertIn("beginner-step-list", html)
            self.assertIn("beginner-primary-action", html)
            self.assertIn("beginner-help-text", html)
            self.assertIn("beginner-verdict-board", html)
            self.assertIn("beginner-safety-light", html)
            self.assertIn("beginner-verdict-reason", html)
            self.assertIn("beginner-next-button", html)
            self.assertIn('data-runtime-guard="research_backtest"', html)
            self.assertIn('data-runtime-guard="startup_workflows"', html)
            self.assertIn("beginner-task-wizard", html)
            self.assertIn("beginner-task-intent-list", html)
            self.assertIn("beginner-task-detail", html)
            self.assertIn("data-beginner-task-root", html)
            self.assertIn("beginner-troubleshooter", html)
            self.assertIn("beginner-troubleshooter-summary", html)
            self.assertIn("beginner-troubleshooter-rows", html)
            self.assertIn("data-beginner-troubleshooter-root", html)
            self.assertIn("beginner-progress-board", html)
            self.assertIn("beginner-progress-status", html)
            self.assertIn("beginner-progress-steps", html)
            self.assertIn("beginner-progress-next", html)
            self.assertIn("beginner-progress-recovery", html)
            self.assertIn("beginner-data-trust-card", html)
            self.assertIn("beginner-live-handoff-board", html)
            self.assertIn("beginner-live-handoff-status", html)
            self.assertIn("beginner-live-handoff-steps", html)
            self.assertIn("beginner-live-handoff-tickets", html)
            self.assertIn("data-beginner-progress-root", html)
            self.assertIn("data-beginner-recovery-root", html)
            self.assertIn("data-beginner-data-trust-root", html)
            self.assertIn("data-beginner-action", html)
            self.assertIn("data-beginner-target", html)
            self.assertIn("leaderboard-tab-primary", html)
            self.assertIn("leaderboard-tab-cn", html)
            self.assertIn("leaderboard-tab-all", html)
            self.assertIn("factor-leaderboard-explanation", html)
            self.assertIn("factor-runtime-gap-panel", html)
            self.assertIn("factor-runtime-gap-summary", html)
            self.assertIn("factor-runtime-gap-list", html)
            self.assertIn("data-factor-runtime-gap-root", html)
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
            self.assertIn("control-daily-closure-ledger", html)
            self.assertIn("control-server-capital-observation-gate", html)
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
            self.assertIn("daily-readiness-card", html)
            self.assertIn("daily-readiness-light", html)
            self.assertIn("daily-readiness-primary-action", html)
            self.assertIn("daily-readiness-safety", html)
            self.assertIn("daily-command-rail", html)
            self.assertIn("daily-command-rail-status", html)
            self.assertIn("daily-command-rail-actions", html)
            self.assertIn("今天先按这条线走", html)
            self.assertIn("data-daily-command-action", html)
            self.assertIn("data-daily-command-target", html)
            self.assertIn("daily-beginner-action-summary", html)
            self.assertIn("今日行动摘要", html)
            self.assertIn("daily-live-readiness-gate", html)
            self.assertIn("实盘前总闸门", html)
            self.assertIn("beginner-trade-system-board", html)
            self.assertIn("beginner-trade-system-summary", html)
            self.assertIn("beginner-trade-system-capital-ladder", html)
            self.assertIn("beginner-trade-action-card", html)
            self.assertIn("data-beginner-trade-action-card-root", html)
            self.assertIn("beginner-pretrade-receipt-card", html)
            self.assertIn("data-beginner-pretrade-receipt-root", html)
            self.assertIn("beginner-live-pilot-brief", html)
            self.assertIn("data-beginner-live-pilot-root", html)
            self.assertIn("beginner-trade-system-evidence", html)
            self.assertIn("beginner-trade-system-actions", html)
            self.assertIn("daily-live-transition-board", html)
            self.assertIn("daily-live-transition-summary", html)
            self.assertIn("daily-live-transition-loop", html)
            self.assertIn("daily-live-transition-risk-profiles", html)
            self.assertIn("daily-live-transition-gates", html)
            self.assertIn("实盘落地路径", html)
            self.assertIn("风险档位", html)
            self.assertIn("纸面资金规模", html)
            self.assertIn("daily-portfolio-value-help", html)
            self.assertIn("资金只用于纸面估算", html)
            self.assertNotIn("建议账户规模", html)
            self.assertIn("daily-trade-risk-profile", html)
            self.assertIn("daily-current-positions", html)
            self.assertIn("当前持仓", html)
            self.assertIn("daily-current-position-help", html)
            self.assertIn("当前持仓安全检查", html)
            self.assertIn("日常运营包", html)
            self.assertIn("风险候选包", html)
            self.assertIn("约束搜索包", html)
            self.assertIn("模拟盘参数包", html)
            self.assertIn("参数观察包", html)
            self.assertIn("近期数据刷新包", html)
            self.assertIn("刷新后回放包", html)
            self.assertIn("观察样本充足包", html)
            self.assertIn("扩展观察回放包", html)
            self.assertIn("迭代观察扩展包", html)
            self.assertIn("Tushare 启用闸门包", html)
            self.assertIn("推广报告", html)
            self.assertIn("数据源状态", html)
            self.assertIn("数据质量报告", html)
            self.assertIn("总仓位上限", html)
            self.assertIn("市场状态窗口", html)
            self.assertIn("市场状态", html)
            self.assertIn("本地清洗行情 / A股ETF CSV", html)
            self.assertNotIn("Daily ops pack", html)
            self.assertNotIn("Risk candidate pack", html)
            self.assertNotIn("Constrained search pack", html)
            self.assertNotIn("Paper profile pack", html)
            self.assertNotIn("Profile observation pack", html)
            self.assertNotIn("Recent refresh pack", html)
            self.assertNotIn("Post refresh replay pack", html)
            self.assertNotIn("Observation sufficiency pack", html)
            self.assertNotIn("Expanded observation replay pack", html)
            self.assertNotIn("Iterative observation expansion pack", html)
            self.assertNotIn("Tushare activation gate pack", html)
            self.assertNotIn("Promotion report", html)
            self.assertNotIn("Provider status", html)
            self.assertNotIn("Quality report", html)
            self.assertNotIn("Gross cap", html)
            self.assertNotIn("Regime 窗口", html)
            self.assertNotIn("Regime 状态", html)
            self.assertIn("conservative_10dd", html)
            self.assertIn("balanced_20dd", html)
            self.assertIn("aggressive_30dd", html)
            self.assertIn("beginner-daily-rehearsal-board", html)
            self.assertIn("beginner-daily-rehearsal-summary", html)
            self.assertIn("beginner-daily-rehearsal-timeline", html)
            self.assertIn("beginner-daily-rehearsal-actions", html)
            self.assertIn("beginner-post-close-journal-board", html)
            self.assertIn("beginner-post-close-journal-summary", html)
            self.assertIn("beginner-post-close-journal-checklist", html)
            self.assertIn("beginner-post-close-journal-form", html)
            self.assertIn("post-close-manual-outcome", html)
            self.assertIn("post-close-execution-reviews", html)
            self.assertIn("beginner-post-close-execution-audit", html)
            self.assertIn("post-close-manual-note", html)
            self.assertIn("post-close-risk-note", html)
            self.assertIn("post-close-today-pnl-pct", html)
            self.assertIn("post-close-current-drawdown-pct", html)
            self.assertIn("post-close-consecutive-loss-days", html)
            self.assertIn("post-close-cooldown-days-remaining", html)
            self.assertIn("post-close-next-day-note", html)
            self.assertIn("beginner-post-close-journal-actions", html)
            self.assertIn("daily-pretrade-readiness-verdict", html)
            self.assertIn("daily-pretrade-readiness-status", html)
            self.assertIn("daily-pretrade-readiness-action-table", html)
            self.assertIn("daily-trade-decision-sheet", html)
            self.assertIn("daily-trade-decision-summary", html)
            self.assertIn("daily-trade-decision-top3", html)
            self.assertIn("daily-trade-decision-candidate-pool", html)
            self.assertIn("daily-trade-decision-actions", html)
            self.assertIn("daily-trade-decision-evidence", html)
            self.assertIn("daily-trade-package-checklist", html)
            self.assertIn("daily-beginner-operation-recipe-summary", html)
            self.assertIn("daily-beginner-operation-recipe-steps", html)
            self.assertIn("daily-beginner-operation-recipe-skip-rules", html)
            self.assertIn("daily-beginner-operation-recipe-tickets", html)
            self.assertIn("daily-beginner-operation-recipe-inputs", html)
            self.assertIn("daily-manual-broker-handoff-status", html)
            self.assertIn("daily-manual-broker-handoff-ticket-table", html)
            self.assertIn("daily-manual-broker-handoff-checklist", html)
            self.assertIn("daily-manual-broker-handoff-beginner-checklist", html)
            self.assertIn("daily-manual-broker-price-check", html)
            self.assertIn("daily-position-reconciliation-check", html)
            self.assertIn("daily-manual-ticket-export", html)
            self.assertIn("data-manual-ticket-export-root", html)
            self.assertIn("daily-manual-broker-copy-cards", html)
            self.assertIn("daily-pretrade-workflow-steps", html)
            self.assertIn("daily-pretrade-beginner-cards", html)
            self.assertIn("daily-pretrade-next-actions", html)
            self.assertIn("daily-evidence-chain", html)
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
            self.assertIn("ordinary-daily-action-card", html)
            self.assertIn("今日交易系统总览", html)
            self.assertIn("每日交易演练", html)
            self.assertIn("收盘后复盘", html)
            self.assertNotIn('<span class="tag">demo fixture</span>', html)
            self.assertNotIn("鎬", html)
            self.assertNotIn("鐮", html)
            self.assertNotIn("妯", html)
            self.assertNotIn("鑲", html)

            app_js = _read_text(f"{base_url}/app.js")
            css = _read_text(f"{base_url}/styles.css")
            self.assertIn("/api/research?", app_js)
            self.assertIn("/api/signals?", app_js)
            self.assertIn("/api/paper?", app_js)
            self.assertIn("/api/daily/ops", app_js)
            self.assertIn("const signal = daily.signal || {}", app_js)
            self.assertIn("Signal freshness", app_js)
            self.assertIn("activatePageFromHash", app_js)
            self.assertIn("targetIdFromHash", app_js)
            self.assertIn("window.location.hash", app_js)
            self.assertIn("updateHashForBeginnerTarget", app_js)
            self.assertIn("#${pageName}:${targetId}", app_js)
            self.assertIn("hashchange", app_js)
            self.assertIn("jumpToBeginnerTarget(targetIdFromHash", app_js)
            self.assertIn("renderDailyPretradeReadiness", app_js)
            self.assertIn("renderDailyBeginnerActionSummary", app_js)
            self.assertIn("beginner_action_summary", app_js)
            self.assertIn("renderDailyLiveReadinessGate", app_js)
            self.assertIn("daily_live_readiness_gate", app_js)
            self.assertIn("renderDailyTradeDecisionSheet", app_js)
            self.assertIn("daily_trade_decision_sheet", app_js)
            self.assertIn("renderDailyBeginnerExecutionAnswer", app_js)
            self.assertIn("daily_beginner_execution_answer", app_js)
            self.assertIn("renderBeginnerFinalOperationPacket", app_js)
            self.assertIn("beginner_final_operation_packet", app_js)
            self.assertIn("今天到底买什么、卖什么、跳过什么？", app_js)
            self.assertIn("final_quantity_rule", app_js)
            self.assertIn("external_realtime_price_required", app_js)
            self.assertIn("blocked_risk_circuit_breaker", app_js)
            self.assertIn("daily_risk_circuit_breaker", app_js)
            self.assertIn("risk_circuit_decision", app_js)
            self.assertIn("daily_operator_mission_control", app_js)
            self.assertIn("renderDailyOperatorMissionControl", app_js)
            self.assertIn("daily_manual_observation_packet", app_js)
            self.assertIn("renderDailyManualObservationPacket", app_js)
            self.assertIn("manual_observation_material_ready", app_js)
            self.assertIn("top3_factor_snapshot", app_js)
            self.assertIn("same_parameter_paper_requests", app_js)
            self.assertIn("data-manual-observation-paper-action", app_js)
            self.assertIn("data-manual-observation-paper-target", app_js)
            self.assertIn("manual_observation_go_no_go", app_js)
            self.assertIn("blocked_missing_same_parameter_paper", app_js)
            self.assertIn("missing_same_parameter_paper_request_ids", app_js)
            self.assertIn("data-manual-observation-missing-paper", app_js)
            self.assertIn("daily-manual-observation-packet", html)
            self.assertIn("daily-manual-observation-summary", html)
            self.assertIn("daily-manual-observation-verdict", html)
            self.assertIn("daily-manual-observation-top3", html)
            self.assertIn("daily-manual-observation-paper-requests", html)
            self.assertIn("daily-manual-observation-evidence", html)
            self.assertIn("daily-manual-observation-steps", html)
            self.assertIn("daily-manual-observation-tickets", html)
            self.assertIn("daily-operator-mission-control-summary", html)
            self.assertIn("daily-operator-mission-control-cards", html)
            self.assertIn("daily-operator-mission-control-next-actions", html)
            self.assertIn("daily-beginner-execution-answer-summary", html)
            self.assertIn("renderDailyTradeSystemState", app_js)
            self.assertIn("trade_system_state", app_js)
            self.assertIn("renderDailyTradePackageChecklist", app_js)
            self.assertIn("trade_package_checklist", app_js)
            self.assertIn("renderDailyBeginnerOperationRecipe", app_js)
            self.assertIn("beginner_operation_recipe", app_js)
            self.assertIn("daily-beginner-operation-recipe-summary", app_js)
            self.assertIn("operator_inputs_required", app_js)
            self.assertIn("人工输入清单", app_js)
            self.assertIn("输入状态", app_js)
            self.assertIn("manual_required", app_js)
            self.assertIn("missing", app_js)
            self.assertIn("ready", app_js)
            self.assertIn("最终操作单", app_js)
            self.assertIn("renderOrdinaryDailyActionCard", app_js)
            self.assertIn("ordinaryDailyActionDecision", app_js)
            self.assertIn("renderOrdinaryRealWorldHandoffStrip", app_js)
            self.assertIn("state.dailyTradeAdvisory?.real_world_manual_handoff_gate", app_js)
            self.assertIn("实盘前总闸门", app_js)
            self.assertIn("人工观察", app_js)
            self.assertIn("daily_trade_decision_sheet || {}", app_js)
            self.assertIn("data-ordinary-daily-action", app_js)
            self.assertIn("daily-trade-system-state", html)
            self.assertIn("candidate_pool_policy", app_js)
            self.assertIn("paper_rehearsal_required", app_js)
            self.assertIn("dailyTradeDecisionRuntimeState", app_js)
            self.assertIn("dailyTradeDecisionNextAction", app_js)
            self.assertIn("renderDailyCandidatePoolTop20", app_js)
            self.assertIn("candidate_pool_top20", app_js)
            self.assertIn("selection_status", app_js)
            self.assertIn("direct_buy_from_leaderboard_allowed", app_js)
            self.assertIn("completedEvidenceCount", app_js)
            self.assertIn("missingEvidenceCount", app_js)
            self.assertIn("renderDailyTradeDecisionSheet(state.dailyTradeAdvisory?.daily_trade_decision_sheet || {})", app_js)
            self.assertIn("dailyTradeDecisionEvidenceTone", app_js)
            self.assertIn("daily-trade-decision-sheet", app_js)
            self.assertIn("daily_operator_mission_control", app_js)
            self.assertIn("renderDailyOperatorMissionControl", app_js)
            self.assertIn("daily-operator-mission-control-summary", html)
            self.assertIn("daily-operator-mission-control-cards", html)
            self.assertIn("daily-operator-mission-control-next-actions", html)
            self.assertIn("daily-operator-mission-control-tickets", html)
            self.assertIn("每日操作中控台", app_js)
            self.assertIn("当前阶段", app_js)
            self.assertIn("阶段进度", app_js)
            self.assertIn("current_phase_id", app_js)
            self.assertIn("current_phase_target_id", app_js)
            self.assertIn("daily_phase_progress", app_js)
            self.assertIn("容量占用", app_js)
            self.assertIn("参与率", app_js)
            self.assertIn("流动性参考", app_js)
            self.assertIn("capacity_blocked_count", app_js)
            self.assertIn("成交反馈", app_js)
            self.assertIn("次日隔离", app_js)
            self.assertIn("manual_execution_blocked_receipts", app_js)
            self.assertIn("manual_execution_feedback_status", app_js)
            self.assertIn("blocked_manual_execution_feedback", app_js)
            self.assertIn("review_manual_execution_feedback", app_js)
            self.assertIn("next_session_quarantine_required", app_js)
            self.assertIn("盈利证据", app_js)
            self.assertIn("profitability_readiness_score_pct", app_js)
            self.assertIn("small_capital_observation_candidate", app_js)
            self.assertIn("evidence_scorecard", app_js)
            self.assertIn("readiness_score_pct", app_js)
            self.assertIn("next_missing_gate_id", app_js)
            self.assertIn("server_closed_loop_days", app_js)
            self.assertIn("same_parameter_paper_days", app_js)
            self.assertIn("blocked_manual_execution_days", app_js)
            self.assertIn("profitability_evidence", app_js)
            self.assertIn("dailyLiveGateDecision", app_js)
            self.assertIn("dailyLiveGateStepRows", app_js)
            self.assertIn("blocked_fix_current_positions", app_js)
            self.assertIn("decision.liveGateDecision", app_js)
            self.assertIn("renderDailyReadinessCard", app_js)
            self.assertIn("renderDailyCommandRail", app_js)
            self.assertIn("dailyCommandRailRows", app_js)
            self.assertIn("runDailyCommandRailAction", app_js)
            self.assertIn("data-daily-command-action", app_js)
            self.assertIn("data-daily-command-target", app_js)
            self.assertIn("每日交易主路径", app_js)
            self.assertIn("交易系统闭环", app_js)
            self.assertIn("trading_runtime_contract", app_js)
            self.assertIn("runtime_contract_status", app_js)
            self.assertIn("approved_factor_pool", app_js)
            self.assertIn("same_day_signal", app_js)
            self.assertIn("portfolio_rebalance_plan", app_js)
            self.assertIn("risk_cost_capacity_guard", app_js)
            self.assertIn("post_close_feedback_loop", app_js)
            self.assertIn("renderDailyLiveTransitionPlan", app_js)
            self.assertIn("dailyLiveTransitionTone", app_js)
            self.assertIn("data-live-transition-target", app_js)
            self.assertIn("small_capital_review_required", app_js)
            self.assertIn("aggressive_30dd", app_js)
            self.assertIn("risk_profile_id: valueOf(\"daily-trade-risk-profile\")", app_js)
            self.assertIn("current_positions: valueOf(\"daily-current-positions\")", app_js)
            self.assertIn("function todayIsoDate", app_js)
            self.assertIn("function applyDailyTradeDateDefault", app_js)
            self.assertIn("staleDailyDateDefaults", app_js)
            self.assertIn("setValue(\"daily-trade-as-of\", today)", app_js)
            self.assertIn("setValue(\"signal-as-of\", today)", app_js)
            self.assertIn("renderDailyPortfolioValueHelp", app_js)
            self.assertIn("portfolioValueInputState", app_js)
            self.assertIn("daily-portfolio-value-help", app_js)
            self.assertIn("paper_capital_only", app_js)
            self.assertIn("FORBIDDEN_CURRENT_POSITION_COLUMNS", app_js)
            self.assertIn("renderDailyCurrentPositionHelp", app_js)
            self.assertIn("currentPositionInputState", app_js)
            self.assertIn("daily-current-position-help", app_js)
            self.assertIn("current_position_forbidden_field", app_js)
            self.assertIn("dailyReadinessDecision", app_js)
            self.assertIn("renderBeginnerLiveHandoff", app_js)
            self.assertIn("beginnerLiveHandoffSteps", app_js)
            self.assertIn("beginnerLiveHandoffTickets", app_js)
            self.assertIn("daily_pretrade_checkup", app_js)
            self.assertIn("runDailyPretradeCheckup", app_js)
            self.assertIn("dailyPretradeCheckupReceipt", app_js)
            self.assertIn("loadDailyOps();\n    await loadDailyTradeAdvisory();", app_js)
            self.assertIn("renderBeginnerTradeSystem", app_js)
            self.assertIn("renderBeginnerTradeSystemCapitalLadder", app_js)
            self.assertIn("renderBeginnerTradeActionCard", app_js)
            self.assertIn("beginnerTradeActionCardRows", app_js)
            self.assertIn("beginner_trade_action_card", app_js)
            self.assertIn("capital_deployment_ladder", app_js)
            self.assertIn("data-beginner-trade-action-workflow", app_js)
            self.assertIn("renderBeginnerPretradeReceiptCard", app_js)
            self.assertIn("beginnerPretradeReceiptRows", app_js)
            self.assertIn('latestExecutionReceipt("daily_pretrade_checkup")', app_js)
            self.assertIn("data-beginner-pretrade-receipt-target", app_js)
            self.assertIn("pretrade_receipt_only", app_js)
            self.assertIn("beginnerTradeSystemEvidenceRows", app_js)
            self.assertIn("beginnerTradeSystemActionRows", app_js)
            self.assertIn("data-trade-system-action", app_js)
            self.assertIn("renderBeginnerLivePilotBrief", app_js)
            self.assertIn("beginnerLivePilotBriefRows", app_js)
            self.assertIn("beginnerLivePilotEvidenceRows", app_js)
            self.assertIn("daily_live_pilot_brief", app_js)
            self.assertIn("data-beginner-live-pilot-action", app_js)
            self.assertIn("data-beginner-live-pilot-target", app_js)
            self.assertIn("不能把前三因子直接当买入指令", app_js)
            self.assertIn('latestExecutionReceipt("paper_simulation")', app_js)
            self.assertIn('latestExecutionReceipt("post_close_journal")', app_js)
            self.assertIn("离实盘还差什么", app_js)
            self.assertIn("小资金观察闸门仍未打开", app_js)
            self.assertIn("beginnerSmallCapitalGateRows", app_js)
            self.assertIn("executionReceiptsForWorkflow", app_js)
            self.assertIn("renderManualTicketExport", app_js)
            self.assertIn("manual_ticket_export", app_js)
            self.assertIn("data-manual-ticket-export-copy", app_js)
            self.assertIn("data-manual-ticket-export-download", app_js)
            self.assertIn("downloadManualTicketExport", app_js)
            self.assertIn("模拟盘观察次数", app_js)
            self.assertIn("盘后复盘次数", app_js)
            self.assertIn("最大回撤预算", app_js)
            self.assertIn("保护事件", app_js)
            self.assertIn("至少 5 次模拟盘和复盘回执", app_js)
            self.assertIn("small_capital_observation_gate", app_js)
            self.assertIn("smallCapitalGateSpecRows", app_js)
            self.assertIn("paper_simulation_receipts", app_js)
            self.assertIn("latest_paper_drawdown", app_js)
            self.assertIn("smallCapitalObservationDecisionRow", app_js)
            self.assertIn("今天能不能小资金观察", app_js)
            self.assertIn("还不能小资金观察", app_js)
            self.assertIn("missingGateCount", app_js)
            self.assertIn("completedGateCount", app_js)
            self.assertIn("小资金观察进度", app_js)
            self.assertIn("下一步", app_js)
            self.assertIn("renderBeginnerDailyRehearsal", app_js)
            self.assertIn("beginnerDailyRehearsalRows", app_js)
            self.assertIn("beginnerDailyRehearsalActionRows", app_js)
            self.assertIn("data-daily-rehearsal-action", app_js)
            self.assertIn("data-daily-rehearsal-target", app_js)
            self.assertIn("renderBeginnerPostCloseJournal", app_js)
            self.assertIn("beginnerPostCloseJournalRows", app_js)
            self.assertIn("postCloseManualReviewForm", app_js)
            self.assertIn("postCloseRiskStateForm", app_js)
            self.assertIn("percentInputNumberOrNull", app_js)
            self.assertIn("risk_state_recorded", app_js)
            self.assertIn("manualReview.risk_state", app_js)
            self.assertIn("sanitizePostCloseJournalText", app_js)
            self.assertIn("bindPostCloseManualFormStatus", app_js)
            self.assertIn('form.addEventListener("input"', app_js)
            self.assertIn('form.addEventListener("change"', app_js)
            self.assertIn("manual_review_recorded", app_js)
            self.assertIn("manualExecutionReviewRowsFromInput", app_js)
            self.assertIn("localManualExecutionAudit", app_js)
            self.assertIn("renderPostCloseExecutionAudit", app_js)
            self.assertIn("manual_execution_audit", app_js)
            self.assertIn("post-close-broker-recheck-session-decision", html)
            self.assertIn("broker_price_recheck_session_decision", app_js)
            self.assertIn("broker_recheck_session_ok", app_js)
            self.assertIn("broker_recheck_session_missing", app_js)
            self.assertIn("broker_recheck_session_not_ok", app_js)
            self.assertIn("broker_recheck_session_missing_count", app_js)
            self.assertIn("broker_recheck_session_blocked_count", app_js)
            self.assertIn("adverse_slippage_bps", app_js)
            self.assertIn("manual_execution_cost_impact", app_js)
            self.assertIn("total_adverse_slippage_cost", app_js)
            self.assertIn("execution_cost_bps", app_js)
            self.assertIn("adverse_slippage_cost", app_js)
            self.assertIn("executed_notional", app_js)
            self.assertIn("manual_outcome", app_js)
            self.assertIn("manual_note_count", app_js)
            self.assertIn("postCloseJournalReceipt", app_js)
            self.assertIn("runPostCloseJournal", app_js)
            self.assertIn("data-post-close-journal-action", app_js)
            self.assertIn("data-post-close-journal-target", app_js)
            self.assertIn("post_close_journal", app_js)
            self.assertIn("最终结论", app_js)
            self.assertIn("下一步", app_js)
            self.assertIn("if (blockers.length > 0) return [];", app_js)
            self.assertIn("readiness.manual_action_candidate", app_js)
            self.assertIn("handoff.status || \"\"", app_js)
            self.assertIn("data-live-handoff-action", app_js)
            self.assertIn("data-live-handoff-target", app_js)
            self.assertIn("人工券商票据", app_js)
            self.assertIn("不会自动下单", app_js)
            self.assertIn("今天先别买", app_js)
            self.assertIn("可以进入人工复核", app_js)
            self.assertIn("仍然禁止自动下单", app_js)
            self.assertIn("data-daily-readiness-target", app_js)
            self.assertIn("data-daily-readiness-workflow", app_js)
            self.assertIn("dailyReadinessButtons", app_js)
            self.assertIn("action_workflow: \"daily_ops\"", app_js)
            self.assertIn("action_workflow: \"paper_simulation\"", app_js)
            self.assertIn("action_workflow: \"daily_trade_advisory\"", app_js)
            self.assertIn("escapeRawHtml(decision.action_workflow)", app_js)
            self.assertIn("data-beginner-action=\"${escapeRawHtml(decision.action_workflow)}\"", app_js)
            self.assertIn("renderDailyReadinessCard();\n  renderDailyEvidenceChain();", app_js)
            self.assertIn("renderDailyReadinessCard();\n  renderDailyEvidenceChain();\n  renderBeginnerTradeSystem();\n  renderBeginnerDailyRehearsal();\n  renderBeginnerPostCloseJournal();\n  renderBeginnerLiveHandoff();", app_js)
            self.assertIn("renderBeginnerLiveHandoff();\n  renderControlCenter();", app_js)
            self.assertIn("pretrade_readiness", app_js)
            self.assertIn("signal_freshness", app_js)
            self.assertIn("latest_signal_date", app_js)
            self.assertIn("renderManualBrokerHandoff", app_js)
            self.assertIn("manual_broker_handoff", app_js)
            self.assertIn("renderManualBrokerPriceCheck", app_js)
            self.assertIn("daily-manual-broker-price-check", app_js)
            self.assertIn("broker_realtime_price_required", app_js)
            self.assertIn("skip_if_broker_price_outside_guardrail", app_js)
            self.assertIn("actual_fill_price", app_js)
            self.assertIn("renderPositionReconciliationCheck", app_js)
            self.assertIn("position_reconciliation_required", app_js)
            self.assertIn("manual_trade_requires_position_update", app_js)
            self.assertIn("daily-current-positions", app_js)
            self.assertIn("FORBIDDEN_CURRENT_POSITION_COLUMNS", app_js)
            self.assertIn("renderManualBrokerCopyCards", app_js)
            self.assertIn("renderTicketReviewChecklist", app_js)
            self.assertIn("review_checklist", app_js)
            self.assertIn("red_flags", app_js)
            self.assertIn("risk_budget", app_js)
            self.assertIn("manual_skip_conditions", app_js)
            self.assertIn("renderTicketRiskBudget", app_js)
            self.assertIn("ticket_loss_budget_share", app_js)
            self.assertIn("single_etf_limit_breached", app_js)
            self.assertIn("price_changed_from_reference", app_js)
            self.assertIn("cash_or_position_limit_breach", app_js)
            self.assertIn("data-copy-ticket-text", app_js)
            self.assertIn("copyTicketTextToClipboard", app_js)
            self.assertIn("复制人工票据", app_js)
            self.assertIn("复制后仍要人工核对", app_js)
            self.assertIn("renderManualBrokerBeginnerChecklist", app_js)
            self.assertIn("ETF代码", app_js)
            self.assertIn("实时价格", app_js)
            self.assertIn("数量", app_js)
            self.assertIn("现金", app_js)
            self.assertIn("风险", app_js)
            self.assertIn("不是订单", app_js)
            self.assertIn("clipboard_unavailable", app_js)
            self.assertIn("renderDailyPretradeWorkflow", app_js)
            self.assertIn("pretrade_workflow", app_js)
            self.assertIn("renderDailyPretradeNextActions", app_js)
            self.assertIn("renderDailyEvidenceChain", app_js)
            self.assertIn("latestExecutionReceipt", app_js)
            self.assertIn("数据刷新", app_js)
            self.assertIn("今日前三因子", app_js)
            self.assertIn("模拟盘复核", app_js)
            self.assertIn("人工券商复核", app_js)
            self.assertIn("daily-evidence-step", app_js)
            self.assertIn("data-daily-evidence-target", app_js)
            self.assertIn("renderDailyEvidenceChain();\n  renderBeginnerTradeSystem();\n  renderBeginnerDailyRehearsal();\n  renderBeginnerPostCloseJournal();\n  renderBeginnerLiveHandoff();\n  byId(\"daily-trade-factor-table\")", app_js)
            self.assertIn("renderDailyEvidenceChain();\n  renderBeginnerTradeSystem();\n  renderBeginnerDailyRehearsal();\n  renderBeginnerPostCloseJournal();\n  renderBeginnerLiveHandoff();\n  renderDailyRealWorldHandoffGate", app_js)
            self.assertIn("renderDailyEvidenceChain();\n  renderBeginnerTradeSystem();\n  renderBeginnerDailyRehearsal();\n  renderBeginnerPostCloseJournal();\n  renderBeginnerLiveHandoff();\n  renderControlCenter();", app_js)
            self.assertIn("operator_next_actions", app_js)
            self.assertIn("refresh_cn_etf_data", app_js)
            self.assertIn("dailyNextActionButtons", app_js)
            self.assertIn("data-daily-next-action", app_js)
            self.assertIn("data-beginner-target", app_js)
            self.assertIn("data-beginner-action", app_js)
            self.assertIn("action_workflow", app_js)
            self.assertIn("cta_target", app_js)
            self.assertIn("escapeRawHtml(workflow)", app_js)
            self.assertIn("escapeRawHtml(target)", app_js)
            daily_manual_table_block = app_js.split('byId("daily-trade-manual-table")', 1)[1].split("]);", 1)[0]
            self.assertIn('"current_quantity"', daily_manual_table_block)
            self.assertIn('"delta_value"', daily_manual_table_block)
            self.assertIn('"rounded_quantity_delta"', daily_manual_table_block)
            self.assertIn('"latest_price"', daily_manual_table_block)
            self.assertIn('"estimated_quantity"', daily_manual_table_block)
            self.assertIn('"rounded_quantity"', daily_manual_table_block)
            self.assertIn('"rounded_value"', daily_manual_table_block)
            self.assertIn('"cash_delta_after_rounding"', daily_manual_table_block)
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
            self.assertIn("leaderboardScoreText", app_js)
            self.assertIn("leaderboardQualityText", app_js)
            self.assertIn("leaderboardRankingBasisText", app_js)
            self.assertIn('leaderboardRankingBasisText(summary.ranking_basis || "--")', app_js)
            factor_explainer_block = app_js.split("function renderFactorBeginnerExplainer", 1)[1].split("function renderFactorLeaderboardTable", 1)[0]
            self.assertIn("leaderboardScoreText(row)", factor_explainer_block)
            self.assertIn("leaderboardQualityText(row.ranking_quality)", factor_explainer_block)
            self.assertNotIn('${row.score_metric || "--"}=', factor_explainer_block)
            self.assertIn("data-factor-beginner-jump", app_js)
            self.assertIn("applyLeaderboardRowToForms", app_js)
            self.assertIn("leaderboardRowPayload", app_js)
            self.assertIn("normalizeLeaderboardWindowValue", app_js)
            self.assertIn("leaderboardRowFromButton", app_js)
            self.assertIn("ensureFactorOption", app_js)
            self.assertIn("manualFormOverride", app_js)
            self.assertIn("markManualFormOverride", app_js)
            self.assertIn("data-factor-apply-row", app_js)
            self.assertIn("data-factor-run-row", app_js)
            self.assertIn("factorRuntimeStatus", app_js)
            self.assertIn("runtimeFactorNames", app_js)
            self.assertIn("data-factor-runtime", app_js)
            self.assertIn("factor-row-runtime", app_js)
            self.assertIn("leaderboardRuntimeRows", app_js)
            self.assertIn("renderFactorRuntimeGapPanel", app_js)
            self.assertIn("factor-runtime-gap-action", app_js)
            self.assertIn("leaderboardRuntimeGapRowPayload", app_js)
            self.assertIn("data-factor-runtime-gap-apply", app_js)
            self.assertIn("factor-runtime-gap-apply", app_js)
            self.assertIn("factor-row-actions", app_js)
            leaderboard_table_blocks = app_js.split("function renderFactorLeaderboardTable")[1:]
            self.assertGreaterEqual(len(leaderboard_table_blocks), 1)
            for leaderboard_table_block in leaderboard_table_blocks:
                self.assertIn("leaderboardScoreText(row)", leaderboard_table_block)
                self.assertIn("leaderboardQualityText(row.ranking_quality)", leaderboard_table_block)
                self.assertIn("leaderboardParamsText(row)", leaderboard_table_block)
                self.assertIn("<th>因子 / 编号</th>", leaderboard_table_block)
                self.assertIn("<th>夏普</th>", leaderboard_table_block)
                self.assertIn("<th>排序相关性</th>", leaderboard_table_block)
                self.assertNotIn('${row.score_metric || "--"}=', leaderboard_table_block)
                self.assertNotIn("JSON.stringify(row.params)", leaderboard_table_block)
                self.assertNotIn("<th>因子 / case</th>", leaderboard_table_block)
                self.assertNotIn("<th>因子 / CASE</th>", leaderboard_table_block)
                self.assertNotIn("<th>Sharpe</th>", leaderboard_table_block)
                self.assertNotIn("<th>SHARPE</th>", leaderboard_table_block)
                self.assertNotIn("<th>RankIC</th>", leaderboard_table_block)
                self.assertNotIn("<th>RANKIC</th>", leaderboard_table_block)
            self.assertIn("renderBeginnerParameterExplainer", app_js)
            self.assertIn("beginnerParameterRows", app_js)
            self.assertIn("parameterRuntimeStatus", app_js)
            self.assertIn("renderBeginnerParameterActions", app_js)
            self.assertIn("data-beginner-parameter-runtime", app_js)
            self.assertIn("data-beginner-parameter-runtime-jump", app_js)
            self.assertIn("parameterPlainValue", app_js)
            self.assertIn("data-beginner-parameter-jump", app_js)
            self.assertIn("renderBeginnerResultInterpreter", app_js)
            self.assertIn("beginnerResultVerdict", app_js)
            self.assertIn("beginnerResultMetric", app_js)
            self.assertIn("data-beginner-result-jump", app_js)
            self.assertIn('emptyChart("暂无数据")', app_js)
            self.assertNotIn('emptyChart("No data")', app_js)
            self.assertIn("operationLedgerText", app_js)
            operation_ledger_block = app_js.split("function renderOperationLedger", 1)[1].split("function renderTradeModeControl", 1)[0]
            self.assertIn("operationLedgerText(item.request_summary || item.command || \"\")", operation_ledger_block)
            self.assertNotIn("item.request_summary || item.command || \"\"", operation_ledger_block.replace("operationLedgerText(item.request_summary || item.command || \"\")", ""))
            run_history_block = app_js.split("function renderRunHistory", 1)[1].split("function loadExecutionReceipts", 1)[0]
            self.assertIn("暂无本机运行历史", run_history_block)
            self.assertIn("zhConsoleText(item.label || item.workflow_id || \"\")", run_history_block)
            self.assertNotIn("<strong>No local run history</strong>", run_history_block)
            self.assertNotIn("Run a local workflow to record it in this browser.", run_history_block)
            execution_receipts_block = app_js.split("function renderExecutionReceipts", 1)[1].split("function researchReceipt", 1)[0]
            self.assertIn("暂无执行回执", execution_receipts_block)
            self.assertIn("zhConsoleText(item.label || item.workflow_id || \"\")", execution_receipts_block)
            self.assertIn("zhConsoleText(item.safety || \"\")", execution_receipts_block)
            self.assertNotIn("<strong>No execution receipts</strong>", execution_receipts_block)
            self.assertNotIn("Run research, signals, or paper simulation to record a structured receipt.", execution_receipts_block)
            self.assertIn("releaseReadinessText", app_js)
            release_readiness_block = app_js.split("function renderReleaseReadiness", 1)[1].split("function loadRunHistory", 1)[0]
            self.assertIn("releaseReadinessText(summary.next_action || \"\")", release_readiness_block)
            self.assertIn("releaseReadinessText(item.evidence || item.command || \"\")", release_readiness_block)
            self.assertIn("renderOrdinaryHome", app_js)
            self.assertIn("ordinaryLiveGateActionRows", app_js)
            self.assertIn("data-ordinary-live-gate-action", app_js)
            self.assertIn("data-ordinary-live-gate-target", app_js)
            self.assertIn("今日总闸门", app_js)
            self.assertIn("renderFactorGlossary", app_js)
            self.assertIn("BEGINNER_STEPS", app_js)
            self.assertIn("BEGINNER_TASKS", app_js)
            self.assertIn("beginnerVerdict", app_js)
            self.assertIn("renderBeginnerVerdict", app_js)
            blocker_verdict_block = app_js.split("if (blockerCount > 0)", 1)[1].split("if (!primaryRows.length)", 1)[0]
            self.assertIn('button: "看阻断与修复队列"', blocker_verdict_block)
            self.assertIn('target: "control-audit-repair-queue"', blocker_verdict_block)
            self.assertNotIn('button: "看安全边界"', blocker_verdict_block)
            self.assertIn("beginnerRecommendedTaskId", app_js)
            self.assertIn("beginnerTaskRows", app_js)
            self.assertIn("renderBeginnerTaskWizard", app_js)
            self.assertIn("beginnerTroubleshooterState", app_js)
            self.assertIn("beginnerTroubleshooterRows", app_js)
            self.assertIn("renderBeginnerTroubleshooter", app_js)
            self.assertIn("beginnerProgressState", app_js)
            self.assertIn("beginnerProgressStepRows", app_js)
            self.assertIn("beginnerProgressActionButtons", app_js)
            self.assertIn("beginnerProgressRecoveryRows", app_js)
            self.assertIn("renderBeginnerProgressRecovery", app_js)
            self.assertIn("beginnerDataTrustState", app_js)
            self.assertIn("beginnerDataTrustRows", app_js)
            self.assertIn("beginnerEvidenceMatchState", app_js)
            self.assertIn("renderBeginnerEvidenceMatch", app_js)
            self.assertIn("data-beginner-evidence-match-root", app_js)
            self.assertIn("data-beginner-evidence-match-action", app_js)
            self.assertIn("data-beginner-evidence-match-jump", app_js)
            self.assertIn("requestMatchesReceipt", app_js)
            self.assertIn("renderBeginnerDataTrust", app_js)
            self.assertIn("renderBeginnerProgress", app_js)
            self.assertIn("renderBeginnerGuide", app_js)
            self.assertIn("jumpToBeginnerTarget", app_js)
            self.assertIn("runBeginnerAction", app_js)
            self.assertIn("currentBacktestRuntimeGuard", app_js)
            self.assertIn("syncCurrentBacktestRuntimeGuard", app_js)
            self.assertIn("renderRuntimeGuardHelp", app_js)
            self.assertIn("isRuntimeGuardedAction", app_js)
            self.assertIn("data-runtime-guard", app_js)
            self.assertIn("data-runtime-guard-help", app_js)
            self.assertIn("data-runtime-guard-help-jump", app_js)
            self.assertIn("runtime-guarded-action", app_js)
            self.assertIn("data-beginner-next", app_js)
            self.assertIn("data-beginner-task-select", app_js)
            self.assertIn("data-beginner-task-run", app_js)
            self.assertIn("data-beginner-troubleshooter-jump", app_js)
            self.assertIn("data-beginner-troubleshooter-action", app_js)
            self.assertIn("data-beginner-progress-jump", app_js)
            self.assertIn("data-beginner-progress-action", app_js)
            self.assertIn("data-beginner-recovery-jump", app_js)
            self.assertIn("data-beginner-data-trust-jump", app_js)
            self.assertIn("beginner-progress-actions", app_js)
            self.assertIn("beginner-recovery-actions", app_js)
            self.assertIn("beginner-data-trust-actions", app_js)
            self.assertIn("beginner-evidence-match", css)
            self.assertIn("beginner-evidence-match-actions", css)
            self.assertIn("beginner-task-actions", app_js)
            self.assertIn("beginner-troubleshooter-actions", app_js)
            self.assertIn("[data-beginner-action]", app_js)
            self.assertIn("[data-beginner-target]", app_js)
            self.assertIn(".segmented-button[data-leaderboard-tab]", app_js)
            self.assertIn("factor-runtime-gap-list", css)
            self.assertIn("factor-runtime-gap-action", css)
            self.assertIn("factor-runtime-gap-apply", css)
            self.assertIn("beginner-parameter-runtime", css)
            self.assertIn("runtime-guarded-action", css)
            self.assertIn("runtime-guard-help", css)
            self.assertIn("workspace.scrollTo", app_js)
            self.assertIn("window.scrollTo", app_js)
            self.assertIn("jumpTargetForScroll", app_js)
            self.assertIn('closest(".control-cell, .panel")', app_js)
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
            self.assertIn("服务端回执=", app_js)
            self.assertIn("浏览器回执=", app_js)
            self.assertIn("指标通过=", app_js)
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
            self.assertIn("control-daily-closure-ledger", app_js)
            self.assertIn("renderDailyClosureLedger", app_js)
            self.assertIn("control-server-capital-observation-gate", app_js)
            self.assertIn("renderServerCapitalObservationGate", app_js)
            self.assertIn("syncExecutionReceiptToServer", app_js)
            self.assertIn("/api/control/execution-receipt", app_js)
            self.assertIn("control-trade-mode-control", app_js)
            self.assertIn("renderTradeModeControl", app_js)
            self.assertIn("control-request-preview", app_js)
            self.assertIn("renderRequestPreview", app_js)
            request_preview_block = app_js.split("function renderRequestPreview", 1)[1].split("function applyControlDefaults", 1)[0]
            self.assertIn("friendlyCommandText(row.endpoint)", request_preview_block)
            self.assertIn("requestPreviewSummary(row.params)", request_preview_block)
            self.assertNotIn("<span>${escapeHtml(row.endpoint)}</span>", request_preview_block)
            self.assertIn("control-parameter-consistency", html)
            self.assertIn("renderParameterConsistency", app_js)
            parameter_consistency_block = app_js.split("function renderParameterConsistency", 1)[1].split("function parameterConsistencyRows", 1)[0]
            self.assertIn("参数权威 /", parameter_consistency_block)
            self.assertIn("工作流=", parameter_consistency_block)
            self.assertIn("偏离=", parameter_consistency_block)
            self.assertIn("当前表单参数匹配标准工作流请求。", parameter_consistency_block)
            self.assertIn("暂无参数权威表", parameter_consistency_block)
            self.assertIn("加载中控状态后，会比较当前表单参数和标准工作流请求。", parameter_consistency_block)
            self.assertNotIn("Parameter authority /", parameter_consistency_block)
            self.assertNotIn("workflows=", parameter_consistency_block)
            self.assertNotIn("drift=", parameter_consistency_block)
            self.assertNotIn("<strong>No parameter authority</strong>", parameter_consistency_block)
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
            request_summary_block = app_js.split("function requestPreviewSummary", 1)[1].split("function renderResultFreshness", 1)[0]
            self.assertIn("数据源=", request_summary_block)
            self.assertIn("市场=", request_summary_block)
            self.assertIn("因子=", request_summary_block)
            self.assertIn("窗口=", request_summary_block)
            self.assertIn("TopN=", request_summary_block)
            self.assertIn("成本=", request_summary_block)
            self.assertIn("日期=", request_summary_block)
            self.assertNotIn("source=", request_summary_block)
            self.assertNotIn("market=", request_summary_block)
            self.assertNotIn("top_n=", request_summary_block)
            self.assertIn("control-result-freshness", app_js)
            self.assertIn("renderResultFreshness", app_js)
            freshness_summary_block = app_js.split("function requestFreshnessSummary", 1)[1].split("function applySourcePreset", 1)[0]
            self.assertIn("TopN=", freshness_summary_block)
            self.assertIn("成本=", freshness_summary_block)
            self.assertIn("初始资金=", freshness_summary_block)
            self.assertNotIn("top_n=", freshness_summary_block)
            self.assertNotIn("cash=", freshness_summary_block)
            self.assertIn("研究回测结果", app_js)
            self.assertIn("页面指标匹配当前表单参数", app_js)
            self.assertIn("修改市场、因子、TopN、成本或日期后，需要重新跑研究回测。", app_js)
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
            execution_receipts_block = app_js.split("function renderExecutionReceipts", 1)[1].split("function researchReceipt", 1)[0]
            self.assertIn("收益=", execution_receipts_block)
            self.assertIn("夏普=", execution_receipts_block)
            self.assertIn("回撤=", execution_receipts_block)
            self.assertIn("权益=", execution_receipts_block)
            self.assertIn("目标数=", execution_receipts_block)
            self.assertIn("TopN=", execution_receipts_block)
            self.assertIn("成本=", execution_receipts_block)
            self.assertNotIn("return=", execution_receipts_block)
            self.assertNotIn("sharpe=", execution_receipts_block)
            self.assertNotIn("dd=", execution_receipts_block)
            self.assertNotIn("top_n=", execution_receipts_block)
            self.assertIn("researchReceipt", app_js)
            self.assertIn("signalReceipt", app_js)
            self.assertIn("paperReceipt", app_js)
            self.assertIn("dailyTradeAdvisoryReceipt", app_js)
            self.assertIn("appendExecutionReceipt(dailyTradeAdvisoryReceipt(state.dailyTradeAdvisory))", app_js)
            self.assertIn("灯号=", app_js)
            self.assertIn("信号=", app_js)
            self.assertIn("票据=", app_js)
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
            self.assertIn("默认模式：研究", app_js)
            self.assertIn("没有额外 GUI 工作进程", app_js)
            self.assertIn("本地启动冒烟", app_js)
            self.assertIn("运行验证闸门", app_js)
            self.assertIn("证据包位于", app_js)
            self.assertIn("中控状态 API", app_js)
            self.assertIn("GUI 浏览器冒烟证据", app_js)
            self.assertIn("仅计算指标；无券商、账户或下单副作用。", app_js)
            self.assertIn("暂无本地验证回执", app_js)
            self.assertIn("发布 GUI 改动前先运行 gui_compile。", app_js)
            self.assertIn("<strong>暂无本地验证回执</strong>", app_js)
            self.assertIn("监控中", app_js)
            self.assertIn("研究接口", app_js)
            self.assertIn("服务端回执", app_js)
            self.assertIn("运行后刷新", app_js)
            self.assertIn("需要闸门", app_js)
            self.assertIn("白名单", app_js)
            self.assertIn("浏览器检查", app_js)
            self.assertIn("运行当前显示命令完成研究回测。", app_js)
            self.assertIn("运行当前显示命令完成本地模拟盘。", app_js)
            self.assertIn("保持实盘交易禁用；只允许研究和本地模拟盘。", app_js)
            self.assertIn("证据账本", app_js)
            self.assertIn("实盘边界", app_js)
            self.assertIn("界面=", app_js)
            self.assertIn("实盘=", app_js)
            self.assertIn("证据为当前", app_js)
            self.assertIn("匹配当前请求=否", app_js)
            self.assertIn("夏普、总收益、年化收益、最大回撤、胜率、交易次数、相对基准收益、模拟盘期末权益、存储回执", app_js)
            self.assertNotIn('["gui", "界面"]', app_js)
            self.assertNotIn('["live", "实盘"]', app_js)
            self.assertNotIn('["lookback=", "回看="]', app_js)
            self.assertIn("回看周期", app_js)
            self.assertIn("GUI 测试、项目审计、编译检查、安全同步审计和浏览器冒烟都要通过。", app_js)
            self.assertIn("function friendlyCommandText", app_js)
            self.assertIn("研究回测接口", app_js)
            self.assertIn("本地模拟盘接口", app_js)
            self.assertIn("建议信号接口", app_js)
            self.assertIn("本地验证接口", app_js)
            self.assertIn("数据范围", app_js)
            self.assertIn("因子输入", app_js)
            self.assertIn("执行模型", app_js)
            self.assertIn("成本和风控模型", app_js)
            self.assertIn("输出指标", app_js)
            self.assertIn("读取本地清洗行情", app_js)
            self.assertIn("按窗口", app_js)
            self.assertIn("每", app_js)
            self.assertIn("根K线调仓", app_js)
            self.assertIn("报告总收益、年化收益、夏普、最大回撤、胜率、交易次数、相对基准收益和模拟盘权益。", app_js)
            action_center_block = app_js.split("function renderActionCenter", 1)[1].split("function renderConsoleCommandDeck", 1)[0]
            self.assertIn("friendlyCommandText(item.command", action_center_block)
            self.assertNotIn("<span>${escapeHtml(item.command || \"\")}</span>", action_center_block)
            self.assertIn("暂无下一步动作", action_center_block)
            self.assertIn("运行中控状态接口后，会生成下一步安全操作建议。", action_center_block)
            self.assertNotIn("<strong>No action center rows</strong>", action_center_block)
            self.assertNotIn("Run the control status API to derive the next safe GUI action.", action_center_block)
            trade_mode_block = app_js.split("function renderTradeModeControl", 1)[1].split("function renderStartupHealth", 1)[0]
            self.assertIn("friendlyCommandText(item.entrypoint", trade_mode_block)
            self.assertNotIn("<span>${escapeHtml(item.entrypoint || \"\")}</span>", trade_mode_block)
            self.assertIn("暂无模式行", trade_mode_block)
            self.assertIn("中控 API 需要展示研究、模拟盘和实盘模式。", trade_mode_block)
            self.assertIn("只允许研究和本地模拟盘模式。", trade_mode_block)
            self.assertNotIn("<strong>No mode rows</strong>", trade_mode_block)
            self.assertNotIn("Use research and paper simulation modes only.", trade_mode_block)
            workflow_trace_block = app_js.split("function renderWorkflowTrace", 1)[1].split("function renderVerificationRunner", 1)[0]
            self.assertIn("friendlyCommandText(item.command || item.endpoint", workflow_trace_block)
            self.assertNotIn("<span>${escapeHtml(item.command || item.endpoint || \"\")}</span>", workflow_trace_block)
            self.assertIn("暂无工作流追踪", workflow_trace_block)
            self.assertIn("中控 API 需要展示当前工作流、队列步骤、证据存储、验证闸门和实盘边界。", workflow_trace_block)
            self.assertNotIn("<strong>No workflow trace</strong>", workflow_trace_block)
            self.assertNotIn("The control API must expose the active workflow, queued steps, evidence storage, verification gates, and live boundary.", workflow_trace_block)
            backtest_provenance_block = app_js.split("function renderBacktestProvenance", 1)[1].split("function renderResultEvidence", 1)[0]
            self.assertIn("暂无回测溯源", backtest_provenance_block)
            self.assertIn("中控 API 需要展示每次回测的数据源、参数、端点、输出和安全溯源。", backtest_provenance_block)
            self.assertNotIn("<strong>No backtest provenance</strong>", backtest_provenance_block)
            self.assertNotIn("The control API must expose source, parameter, endpoint, output, and safety provenance for each backtest.", backtest_provenance_block)
            verification_runner_block = app_js.split("function renderVerificationRunner", 1)[1].split("function renderWorkspaceSync", 1)[0]
            self.assertIn("暂无允许的验证闸门", verification_runner_block)
            self.assertIn("验证闸门元数据恢复前，验证执行器会保持禁用。", verification_runner_block)
            self.assertNotIn("<strong>No allowlisted gates</strong>", verification_runner_block)
            self.assertNotIn("Verification runner is disabled until gate metadata is restored.", verification_runner_block)
            workspace_sync_block = app_js.split("function renderWorkspaceSync", 1)[1].split("function renderActionCenter", 1)[0]
            self.assertIn("暂无工作区同步状态", workspace_sync_block)
            self.assertIn("发布前需要看到 Git 分支、工作区、上游和同步策略。", workspace_sync_block)
            self.assertIn("落后=", workspace_sync_block)
            self.assertIn("超前=", workspace_sync_block)
            self.assertIn("变更=", workspace_sync_block)
            self.assertNotIn("<strong>No workspace sync status</strong>", workspace_sync_block)
            self.assertNotIn("Git branch, worktree, upstream, and sync policy should be visible before publishing.", workspace_sync_block)
            self.assertNotIn("behind=", workspace_sync_block)
            self.assertNotIn("ahead=", workspace_sync_block)
            self.assertNotIn("changed=", workspace_sync_block)
            process_monitor_block = app_js.split("function renderProcessMonitor", 1)[1].split("function renderTradeModeControl", 1)[0]
            self.assertIn("暂无进程监控数据", process_monitor_block)
            self.assertIn("中控 API 需要展示当前 GUI、审计、冒烟和研究进程。", process_monitor_block)
            self.assertNotIn("<strong>No process monitor data</strong>", process_monitor_block)
            result_evidence_block = app_js.split("function renderResultEvidence", 1)[1].split("function renderPaperReadiness", 1)[0]
            self.assertIn("暂无结果证据", result_evidence_block)
            self.assertIn("运行研究、信号或模拟盘后，会把结果指标连接到工作流回执。", result_evidence_block)
            self.assertNotIn("<strong>No result evidence</strong>", result_evidence_block)
            self.assertNotIn("Run research, signals, or paper simulation to connect result metrics to workflow receipts.", result_evidence_block)
            backtest_gate_block = app_js.split("function renderBacktestGate", 1)[1].split("function evaluateBacktestGateRows", 1)[0]
            self.assertIn("暂无回测闸门", backtest_gate_block)
            self.assertIn("显示模拟盘观察判断前，中控 API 必须给出指标门槛。", backtest_gate_block)
            self.assertIn("只检查指标门槛", backtest_gate_block)
            self.assertIn("风险=", backtest_gate_block)
            self.assertNotIn("<strong>No backtest gate</strong>", backtest_gate_block)
            self.assertNotIn("The control API must expose metric thresholds before paper-observation decisions are shown.", backtest_gate_block)
            self.assertNotIn("metrics floor only", backtest_gate_block)
            self.assertNotIn("risk=", backtest_gate_block)
            paper_readiness_block = app_js.split("function renderPaperReadiness", 1)[1].split("function renderLedgerEvidence", 1)[0]
            self.assertIn("暂无模拟盘交接", paper_readiness_block)
            self.assertIn("先运行当前研究和模拟盘工作流，再评估回执、指标、预检、闸门和实盘边界。", paper_readiness_block)
            self.assertNotIn("<strong>No paper readiness handoff</strong>", paper_readiness_block)
            self.assertNotIn("Run current research and paper workflows, then evaluate receipts, metrics, preflight, gates, and live boundary.", paper_readiness_block)
            ledger_evidence_block = app_js.split("function renderLedgerEvidence", 1)[1].split("function renderBacktestGate", 1)[0]
            self.assertIn("暂无服务端回执账本", ledger_evidence_block)
            self.assertIn("从这个 GUI 运行研究、信号、模拟盘或验证任务后，会生成服务端回执。", ledger_evidence_block)
            self.assertIn("服务端回执 /", ledger_evidence_block)
            self.assertIn("缺失或过期=", ledger_evidence_block)
            self.assertNotIn("<strong>No server ledger evidence</strong>", ledger_evidence_block)
            self.assertNotIn("Run research, signals, paper, or verification from this GUI to create server-side receipts.", ledger_evidence_block)
            self.assertNotIn("Server receipts", ledger_evidence_block)
            self.assertNotIn("missing_or_stale=", ledger_evidence_block)
            release_readiness_block = app_js.split("function renderReleaseReadiness", 1)[1].split("function renderLocalRunHistory", 1)[0]
            self.assertIn("暂无发布就绪检查行", release_readiness_block)
            self.assertIn("刷新中控台快照后会填充本地发布闸门。", release_readiness_block)
            self.assertIn("证据=", release_readiness_block)
            self.assertIn("人工=", release_readiness_block)
            self.assertIn("缺失=", release_readiness_block)
            self.assertNotIn("<strong>No release readiness rows</strong>", release_readiness_block)
            self.assertNotIn("Run the control-center snapshot to populate local release gates.", release_readiness_block)
            self.assertNotIn("evidence=", release_readiness_block)
            self.assertNotIn("manual=", release_readiness_block)
            self.assertNotIn("missing=", release_readiness_block)
            workflow_preflight_block = app_js.split("function renderWorkflowPreflight", 1)[1].split("function workflowPreflightEndpointSummary", 1)[0]
            self.assertIn("workflowPreflightCheckText", app_js)
            self.assertIn("workflowPreflightModeText", app_js)
            self.assertIn("模式=", workflow_preflight_block)
            self.assertIn("可运行=", workflow_preflight_block)
            self.assertIn("workflowPreflightCheckText(check)", workflow_preflight_block)
            self.assertIn("暂无运行前检查行", workflow_preflight_block)
            self.assertIn("使用工作流按钮前，中控状态应展示运行就绪情况。", workflow_preflight_block)
            self.assertNotIn("mode=", workflow_preflight_block)
            self.assertNotIn("runnable=", workflow_preflight_block)
            endpoint_summary_block = app_js.split("function workflowPreflightEndpointSummary", 1)[1].split("function renderProcessMonitor", 1)[0]
            self.assertIn("friendlyCommandText(endpoint)", endpoint_summary_block)
            self.assertIn('friendlyCommandText(command.replace("GET ", ""))', endpoint_summary_block)
            self.assertNotIn("return endpoint;", endpoint_summary_block)
            self.assertNotIn("<strong>No workflow preflight rows</strong>", workflow_preflight_block)
            operation_ledger_block = app_js.split("function renderOperationLedger", 1)[1].split("function renderTradeModeControl", 1)[0]
            self.assertIn("暂无服务端操作记录", operation_ledger_block)
            self.assertIn("等待工作流回执", operation_ledger_block)
            self.assertIn("从这个 GUI 运行研究、信号、模拟盘或验证任务后，会生成服务端回执。", operation_ledger_block)
            self.assertIn("记录=", operation_ledger_block)
            self.assertIn("账本=", operation_ledger_block)
            self.assertNotIn("No server operation logged", operation_ledger_block)
            self.assertNotIn("Awaiting workflow receipt", operation_ledger_block)
            self.assertNotIn("entries=", operation_ledger_block)
            self.assertNotIn("path=", operation_ledger_block)
            audit_packets_block = app_js.split("function renderAuditPackets", 1)[1].split("function renderAuditFeedback", 1)[0]
            self.assertIn("暂无审计包配置", audit_packets_block)
            self.assertIn("运行 GUI 中控台审计后，会生成证据主线。", audit_packets_block)
            self.assertNotIn("<strong>No audit packets configured</strong>", audit_packets_block)
            audit_feedback_block = app_js.split("function renderAuditFeedback", 1)[1].split("function renderRoundCheckpointReport", 1)[0]
            self.assertIn("暂无审计反馈动作", audit_feedback_block)
            self.assertIn("下一轮 GUI 优化前，先复核独立审计包。", audit_feedback_block)
            self.assertNotIn("<strong>No audit feedback actions</strong>", audit_feedback_block)
            round_checkpoint_block = app_js.split("function renderRoundCheckpointReport", 1)[1].split("function renderAuditIterationPlan", 1)[0]
            self.assertIn("节奏=", round_checkpoint_block)
            self.assertIn("已汇总=", round_checkpoint_block)
            self.assertIn("剩余=", round_checkpoint_block)
            self.assertIn("暂无近期 GUI 轮次", round_checkpoint_block)
            self.assertIn("暂无下一步流程计划", round_checkpoint_block)
            self.assertIn("每五轮 GUI 工作生成一次复盘报告。", round_checkpoint_block)
            self.assertNotIn("cadence=", round_checkpoint_block)
            self.assertNotIn("<strong>No recent GUI rounds</strong>", round_checkpoint_block)
            self.assertNotIn("<strong>No next flow plan</strong>", round_checkpoint_block)
            audit_iteration_block = app_js.split("function renderAuditIterationPlan", 1)[1].split("function renderAuditScheduler", 1)[0]
            self.assertIn("暂无审计迭代动作", audit_iteration_block)
            self.assertIn("下一轮优化前，先运行独立 GUI 审计。", audit_iteration_block)
            self.assertIn("动作=", audit_iteration_block)
            self.assertIn("节奏=", audit_iteration_block)
            self.assertNotIn("<strong>No audit iteration actions</strong>", audit_iteration_block)
            self.assertNotIn("actions=", audit_iteration_block)
            self.assertNotIn("cadence=", audit_iteration_block)
            audit_scheduler_block = app_js.split("function renderAuditScheduler", 1)[1].split("function formatSchedulerAge", 1)[0]
            self.assertIn("暂无审计调度数据", audit_scheduler_block)
            self.assertIn("中控 API 需要展示 gui-5h 心跳状态和最近审计时间。", audit_scheduler_block)
            self.assertNotIn("<strong>No audit scheduler data</strong>", audit_scheduler_block)
            startup_health_block = app_js.split("function renderStartupHealth", 1)[1].split("function renderBacktestProvenance", 1)[0]
            self.assertIn("本地启动就绪", startup_health_block)
            self.assertIn("需要启动证据", startup_health_block)
            self.assertIn("暂无启动健康行", startup_health_block)
            self.assertIn("给操作员使用前，先运行本地 GUI 启动和浏览器冒烟。", startup_health_block)
            self.assertNotIn("Local startup ready", startup_health_block)
            self.assertNotIn("Startup evidence required", startup_health_block)
            self.assertNotIn("<strong>No startup health rows</strong>", startup_health_block)
            self.assertIn("return String(zhConsoleText(value))", app_js)
            startup_block = app_js.split('document.addEventListener("DOMContentLoaded", () => {', 1)[1].split("});", 1)[0]
            self.assertIn("initializeApp();", startup_block)
            initialize_block = app_js.split("async function initializeApp()", 1)[1].split(
                "async function loadSecondaryPanels", 1
            )[0]
            self.assertIn('safeLoadPanel("control_center", loadControlCenter)', initialize_block)
            self.assertIn('safeLoadPanel("daily_trade_advisory", loadDailyTradeAdvisory)', initialize_block)
            secondary_block = app_js.split("async function loadSecondaryPanels()", 1)[1].split(
                "function bindNavigation", 1
            )[0]
            load_control_block = app_js.split("async function loadControlCenter()", 1)[1].split("async function loadProjectStatus", 1)[0]
            self.assertIn("applyControlDefaults();", load_control_block)
            self.assertLess(app_js.index('safeLoadPanel("daily_trade_advisory", loadDailyTradeAdvisory)'), app_js.index("async function loadSecondaryPanels"))
            self.assertIn('safeLoadPanel("risk_candidates", loadRiskCandidates)', secondary_block)
            self.assertIn('safeLoadPanel("recent_data_refresh", loadRecentDataRefresh)', secondary_block)
            self.assertIn('safeLoadPanel("post_refresh_replay", loadPostRefreshReplay)', secondary_block)
            self.assertIn('safeLoadPanel("observation_sufficiency", loadObservationSufficiency)', secondary_block)
            self.assertIn('safeLoadPanel("expanded_observation_replay", loadExpandedObservationReplay)', secondary_block)
            self.assertIn('safeLoadPanel("iterative_observation_expansion", loadIterativeObservationExpansion)', secondary_block)
            self.assertIn('safeLoadPanel("tushare_activation_gate", loadTushareActivationGate)', secondary_block)
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
            self.assertEqual(control_preflight_rows["daily_pretrade_checkup"]["mode"], "manual_pretrade_checkup")
            self.assertTrue(control_preflight_rows["daily_pretrade_checkup"]["runnable"])
            self.assertFalse(control_preflight_rows["daily_pretrade_checkup"]["permissions"]["order_placement_allowed"])
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

            trade_advisory = _read_json(
                f"{base_url}/api/trade/daily-advisory?source=demo_fixture&market=CN_ETF&limit=3"
                "&risk_profile_id=conservative_10dd"
                "&current_positions=asset_id%2Cquantity%2Clatest_price%0ACN_ETF_XSHG_510300%2C1000%2C4.864"
                "&"
                + urlencode(
                    {
                        "evidence_snapshot": json.dumps(
                            {
                                "mode": "browser_execution_receipts",
                                "counts": {
                                    "matched_paper_receipts": 5,
                                    "post_close_journal_receipts": 5,
                                    "paper_ready_observations": 20,
                                },
                                "flags": {
                                    "walk_forward_oos_passed": True,
                                    "lookahead_bias_audit_passed": True,
                                    "multiple_testing_control_passed": True,
                                    "transaction_cost_capacity_passed": True,
                                },
                            },
                            ensure_ascii=False,
                        )
                    }
                )
            )
            self.assertEqual(trade_advisory["stage"], "phase_6_0_daily_trade_advisory")
            self.assertIn("summary", trade_advisory)
            self.assertEqual(trade_advisory["summary"]["risk_profile_id"], "conservative_10dd")
            self.assertLessEqual(trade_advisory["summary"]["applied_max_gross_exposure"], 0.30)
            self.assertEqual(trade_advisory["summary"]["current_position_count"], 1)
            self.assertEqual(trade_advisory["beginner_action_summary"]["stage"], "phase_6_8_beginner_action_summary")
            self.assertEqual(trade_advisory["daily_live_readiness_gate"]["stage"], "phase_6_9_daily_live_readiness_gate")
            self.assertEqual(trade_advisory["beginner_trade_action_card"]["stage"], "phase_6_10_beginner_trade_action_card")
            self.assertEqual(trade_advisory["daily_trade_decision_sheet"]["stage"], "phase_6_14_daily_trade_decision_sheet")
            self.assertFalse(trade_advisory["daily_trade_decision_sheet"]["summary"]["order_placement_allowed"])
            self.assertIn("daily_top3", trade_advisory["daily_trade_decision_sheet"])
            self.assertIn("today_actions", trade_advisory["daily_trade_decision_sheet"])
            self.assertEqual(trade_advisory["daily_signal_execution_bridge"]["stage"], "phase_6_16_daily_signal_execution_bridge")
            self.assertFalse(trade_advisory["daily_signal_execution_bridge"]["summary"]["direct_buy_from_top3_allowed"])
            self.assertIn(
                "manual_broker_review",
                {item["step_id"] for item in trade_advisory["daily_signal_execution_bridge"]["daily_operating_steps"]},
            )
            self.assertIn(trade_advisory["beginner_trade_action_card"]["summary"]["answer_code"], {"no", "not_yet"})
            self.assertFalse(trade_advisory["beginner_trade_action_card"]["summary"]["auto_order_allowed"])
            self.assertIn("plain_answer", trade_advisory["beginner_trade_action_card"]["summary"])
            self.assertIn("target_id", trade_advisory["beginner_trade_action_card"]["next_action"])
            self.assertIn("live_boundary", {row["check_id"] for row in trade_advisory["beginner_trade_action_card"]["plain_checklist"]})
            self.assertFalse(trade_advisory["daily_live_readiness_gate"]["summary"]["order_placement_allowed"])
            self.assertFalse(trade_advisory["summary"]["live_trading_allowed"])
            self.assertFalse(trade_advisory["summary"]["order_placement_allowed"])
            self.assertTrue(trade_advisory["summary"]["manual_execution_required"])
            self.assertEqual(trade_advisory["selected_candidates"], trade_advisory["factors"])
            self.assertEqual(trade_advisory["pretrade_workflow"]["stage"], "phase_6_1_daily_pretrade_workflow")
            self.assertEqual(trade_advisory["trade_system"]["stage"], "phase_6_4_manual_trade_system_protocol")
            self.assertEqual(trade_advisory["trade_system"]["operator_workflow"]["workflow_id"], "daily_pretrade_checkup")
            self.assertFalse(trade_advisory["pretrade_workflow"]["summary"]["live_order_allowed"])
            self.assertEqual(len(trade_advisory["pretrade_workflow"]["steps"]), 5)
            self.assertLessEqual(trade_advisory["summary"]["selected_factor_count"], 3)
            self.assertEqual(
                trade_advisory["live_profitability_readiness"]["summary"]["evidence_mode"],
                "browser_execution_receipts",
            )
            self.assertEqual(trade_advisory["live_profitability_readiness"]["summary"]["matched_paper_receipts"], 5)
            self.assertEqual(trade_advisory["live_profitability_readiness"]["summary"]["post_close_journal_receipts"], 5)
            self.assertFalse(trade_advisory["daily_real_money_transition_gate"]["summary"]["order_placement_allowed"])
            self.assertEqual(trade_advisory["daily_manual_trading_session"]["stage"], "phase_6_24_daily_manual_trading_session")
            self.assertFalse(trade_advisory["daily_manual_trading_session"]["summary"]["order_placement_allowed"])
            self.assertIn(
                "record_post_close_journal",
                {row["step_id"] for row in trade_advisory["daily_manual_trading_session"]["operator_checklist"]},
            )
            self.assertEqual(
                trade_advisory["daily_paper_allocation_playbook"]["stage"],
                "phase_6_25_daily_paper_allocation_playbook",
            )
            self.assertFalse(trade_advisory["daily_paper_allocation_playbook"]["summary"]["order_placement_allowed"])
            self.assertIn(
                "run_same_parameter_paper",
                {row["step_id"] for row in trade_advisory["daily_paper_allocation_playbook"]["operator_steps"]},
            )
            self.assertEqual(
                trade_advisory["daily_pre_execution_guard"]["stage"],
                "phase_6_26_daily_pre_execution_guard",
            )
            self.assertFalse(trade_advisory["daily_pre_execution_guard"]["summary"]["order_placement_allowed"])
            self.assertIn(
                "broker_price_outside_guardrail",
                {row["rule_id"] for row in trade_advisory["daily_pre_execution_guard"]["skip_rules"]},
            )
            self.assertEqual(
                trade_advisory["daily_same_parameter_paper_rehearsal"]["stage"],
                "phase_6_27_daily_same_parameter_paper_rehearsal",
            )
            self.assertFalse(trade_advisory["daily_same_parameter_paper_rehearsal"]["summary"]["order_placement_allowed"])
            self.assertIn(
                "run_each_top3_candidate_with_locked_params",
                {row["step_id"] for row in trade_advisory["daily_same_parameter_paper_rehearsal"]["operator_steps"]},
            )
            self.assertEqual(
                trade_advisory["daily_beginner_execution_answer"]["stage"],
                "phase_6_28_daily_beginner_execution_answer",
            )
            self.assertFalse(trade_advisory["daily_beginner_execution_answer"]["summary"]["can_buy_today"])
            self.assertFalse(trade_advisory["daily_beginner_execution_answer"]["summary"]["order_placement_allowed"])

            invalid_positions = _read_json(
                f"{base_url}/api/trade/daily-advisory?source=demo_fixture&market=CN_ETF&limit=3"
                "&current_positions=asset_id%2Cquantity%2Clatest_price%2Caccount_id%0ACN_ETF_XSHG_510300%2C1000%2C4.864%2Creal"
            )
            self.assertEqual(invalid_positions["stage"], "phase_6_0_daily_trade_advisory")
            self.assertEqual(invalid_positions["current_position_validation"]["status"], "error")
            self.assertEqual(invalid_positions["beginner_action_summary"]["summary"]["decision"], "fix_current_positions_first")
            self.assertEqual(invalid_positions["daily_live_readiness_gate"]["summary"]["decision"], "blocked_fix_current_positions")
            self.assertEqual(invalid_positions["beginner_trade_action_card"]["summary"]["decision"], "blocked_fix_current_positions")
            self.assertEqual(invalid_positions["beginner_trade_action_card"]["next_action"]["target_id"], "daily-current-positions")
            self.assertIn("current_position_input_invalid", invalid_positions["pretrade_readiness"]["blockers"])
            self.assertEqual(invalid_positions["manual_trade_plan"], [])
            self.assertFalse(invalid_positions["summary"]["order_placement_allowed"])

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

            locked_paper = _read_json(
                f"{base_url}/api/paper?source=demo_fixture&market=CN_ETF&factor=momentum_2&top_n=2"
                "&same_parameter_lock_id=lock_test_001&same_parameter_request_id=top3-paper-001&case_id=case_lock_001"
            )
            self.assertEqual(locked_paper["request"]["same_parameter_lock_id"], "lock_test_001")
            self.assertEqual(locked_paper["request"]["same_parameter_request_id"], "top3-paper-001")
            self.assertEqual(locked_paper["request"]["case_id"], "case_lock_001")

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

    def test_http_app_records_browser_execution_receipts_to_server_ledger(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), create_gui_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_port}"
        try:
            payload = {
                "workflow_id": "post_close_journal",
                "label": "Post-close journal receipt",
                "status": "completed",
                "request": {"market": "CN_ETF", "as_of_date": "2026-06-30"},
                "metrics": {
                    "manual_review_recorded": True,
                    "manual_execution_decision": "manual_execution_evidence_ready",
                    "manual_execution_missing_review_count": 0,
                },
                "manual_review": {"manual_note": "should not be persisted to operation ledger"},
            }

            response = _post_json(f"{base_url}/api/control/execution-receipt", payload)
            ledger = _read_json(f"{base_url}/api/control/operation-ledger")

            self.assertEqual(response["stage"], "gui_browser_execution_receipt")
            self.assertEqual(response["status"], "recorded")
            self.assertFalse(response["safety"]["live_trading_allowed"])
            self.assertEqual(ledger["rows"][0]["workflow_id"], "post_close_journal")
            self.assertEqual(ledger["rows"][0]["request"]["as_of_date"], "2026-06-30")
            self.assertIn("manual_execution_decision=manual_execution_evidence_ready", ledger["rows"][0]["metric_summary"])
            self.assertNotIn("manual_note", json.dumps(ledger["rows"][0], ensure_ascii=False))
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


def _post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


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
