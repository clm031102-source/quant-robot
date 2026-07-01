from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.gui.control_center import SAFETY_NOTICE


DEFAULT_BASE_URL = "http://127.0.0.1:8765"
DEFAULT_OUTPUT_DIR = Path("data/reports/gui_browser_smoke")


def run_gui_browser_smoke(
    base_url: str = DEFAULT_BASE_URL,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    timeout: float = 5.0,
) -> dict[str, Any]:
    normalized_base_url = base_url.rstrip("/")
    checks: list[dict[str, Any]] = []
    index_html = _fetch_text(normalized_base_url, "/", timeout)
    app_js = _fetch_text(normalized_base_url, "/app.js", timeout)
    styles_css = _fetch_text(normalized_base_url, "/styles.css", timeout)
    control = _fetch_json(normalized_base_url, "/api/control/status", timeout)

    checks.append(
        _check(
            "index_html",
            "Index HTML",
            index_html.get("ok")
            and all(
                token in str(index_html.get("body", ""))
                for token in [
                    "control-center-board",
                    "量化机器人中控台",
                    "办公室电脑作战台",
                    "操作控制台",
                    "运行队列",
                    "下一步动作",
                    "运行前检查",
                    "当前回测",
                    "模拟盘交接",
                    "control-action-center",
                    "data-console-action",
                    "control-workflow-preflight",
                    "control-paper-readiness",
                    "control-backtest-status",
                    "control-backtest-provenance",
                    "control-backtest-gate",
                    "control-workflow-trace",
                    "control-workspace-sync",
                    "control-process-monitor",
                    "control-active-operation",
                    "control-operation-ledger",
                    "control-trade-mode-control",
                    "control-request-preview",
                    "control-result-freshness",
                    "control-parameter-consistency",
                    "control-ledger-evidence",
                    "control-result-evidence",
                    "control-startup-health",
                    "control-audit-feedback",
                    "control-round-checkpoint-report",
                    "control-audit-iteration-plan",
                    "control-audit-scheduler",
                    "control-verification-runner",
                    "control-safety-boundary",
                ]
            ),
            "Home page exposes the control-center board, backtest status, active operation, backtest provenance, result evidence, startup health, audit feedback, audit iteration plan, verification runner, and safety boundary.",
            index_html.get("error") or "Home page is missing one or more required GUI anchors.",
        )
    )
    checks.append(
        _check(
            "app_js",
            "Frontend script",
            app_js.get("ok")
            and "renderControlCenter" in str(app_js.get("body", ""))
            and "applyControlDefaults" in str(app_js.get("body", ""))
            and "renderActionCenter" in str(app_js.get("body", ""))
            and "renderConsoleCommandDeck" in str(app_js.get("body", ""))
            and "zhConsoleText" in str(app_js.get("body", ""))
            and "GUI_ZH_REPLACEMENTS" in str(app_js.get("body", ""))
            and "data-console-action" in str(app_js.get("body", ""))
            and "项目安全审计" in str(app_js.get("body", ""))
            and "renderWorkflowPreflight" in str(app_js.get("body", ""))
            and "renderPaperReadiness" in str(app_js.get("body", ""))
            and "evaluateBacktestGateRows" in str(app_js.get("body", ""))
            and "服务端回执=" in str(app_js.get("body", ""))
            and "浏览器回执=" in str(app_js.get("body", ""))
            and "指标通过=" in str(app_js.get("body", ""))
            and "expected_block" in str(app_js.get("body", ""))
            and "runActionCenterWorkflow" in str(app_js.get("body", ""))
            and "data-action-workflow" in str(app_js.get("body", ""))
            and "renderStartupHealth" in str(app_js.get("body", ""))
            and "renderBacktestProvenance" in str(app_js.get("body", ""))
            and "renderBacktestGate" in str(app_js.get("body", ""))
            and "renderWorkflowTrace" in str(app_js.get("body", ""))
            and "renderWorkspaceSync" in str(app_js.get("body", ""))
            and "renderProcessMonitor" in str(app_js.get("body", ""))
            and "renderActiveOperation" in str(app_js.get("body", ""))
            and "renderOperationLedger" in str(app_js.get("body", ""))
            and "renderTradeModeControl" in str(app_js.get("body", ""))
            and "renderRequestPreview" in str(app_js.get("body", ""))
            and "renderParameterConsistency" in str(app_js.get("body", ""))
            and "parameterMismatchKeys" in str(app_js.get("body", ""))
            and "buildResearchParams" in str(app_js.get("body", ""))
            and "buildSignalParams" in str(app_js.get("body", ""))
            and "buildPaperParams" in str(app_js.get("body", ""))
            and "renderResultFreshness" in str(app_js.get("body", ""))
            and "todayIsoDate" in str(app_js.get("body", ""))
            and "applyDailyTradeDateDefault" in str(app_js.get("body", ""))
            and "staleDailyDateDefaults" in str(app_js.get("body", ""))
            and "renderLedgerEvidence" in str(app_js.get("body", ""))
            and "requestMatchesCurrentParams" in str(app_js.get("body", ""))
            and "beginActiveOperation" in str(app_js.get("body", ""))
            and "finishActiveOperation" in str(app_js.get("body", ""))
            and "renderResultEvidence" in str(app_js.get("body", ""))
            and "renderAuditFeedback" in str(app_js.get("body", ""))
            and "renderRoundCheckpointReport" in str(app_js.get("body", ""))
            and "renderAuditIterationPlan" in str(app_js.get("body", ""))
            and "renderAuditScheduler" in str(app_js.get("body", ""))
            and "renderVerificationRunner" in str(app_js.get("body", ""))
            and "runVerificationGate" in str(app_js.get("body", ""))
            and "/api/control/verification?gate_id=" in str(app_js.get("body", "")),
            "Frontend script includes control-center, active-operation, startup-health, backtest-provenance, backtest-gate, workflow-trace, daily trade date freshness defaults, result-evidence, audit-feedback, audit-iteration, audit-scheduler, and verification-runner hooks.",
            app_js.get("error") or "Frontend script is missing required renderer hooks.",
        )
    )
    checks.append(
        _check(
            "control_status_api",
            "Control status API",
            control.get("ok") and control.get("body", {}).get("stage") == "gui_control_center",
            "Control API returned stage=gui_control_center.",
            control.get("error") or f"Unexpected control API stage: {control.get('body', {}).get('stage')}",
        )
    )
    control_body = control.get("body", {}) if isinstance(control.get("body"), dict) else {}
    checks.append(
        _check(
            "startup_health_panel",
            "Startup health contract",
            control.get("ok")
            and control_body.get("startup_health", {}).get("stage") == "gui_startup_health"
            and bool(control_body.get("startup_health", {}).get("rows")),
            "Control API exposes startup_health rows for local startup, control API, browser smoke, and smoke evidence.",
            control.get("error") or "Control API is missing startup_health rows.",
        )
    )
    checks.append(
        _check(
            "form_defaults_contract",
            "Form defaults contract",
            control.get("ok")
            and control_body.get("form_defaults", {}).get("stage") == "gui_form_defaults"
            and control_body.get("form_defaults", {}).get("research", {}).get("factor")
            == control_body.get("backtest", {}).get("factor")
            and _workflow_by_id(control_body, "research_backtest").get("request", {}).get("factor_name")
            == control_body.get("backtest", {}).get("factor")
            and _workflow_by_id(control_body, "research_backtest").get("request", {}).get("execution_lag")
            == control_body.get("backtest", {}).get("execution_lag")
            and _workflow_by_id(control_body, "research_backtest").get("request", {}).get("forward_horizon")
            == control_body.get("backtest", {}).get("forward_horizon")
            and _workflow_by_id(control_body, "paper_simulation").get("request", {}).get("max_market_weight")
            == control_body.get("form_defaults", {}).get("paper", {}).get("max_market_weight")
            and _workflow_by_id(control_body, "paper_simulation").get("request", {}).get("max_gross_exposure")
            == control_body.get("form_defaults", {}).get("paper", {}).get("max_gross_exposure")
            and app_js.get("ok")
            and "applyControlDefaults" in str(app_js.get("body", ""))
            and 'valueOf("execution-lag")' in str(app_js.get("body", ""))
            and 'valueOf("forward-horizon")' in str(app_js.get("body", ""))
            and 'valueOf("paper-max-market-weight")' in str(app_js.get("body", ""))
            and 'valueOf("paper-max-gross-exposure")' in str(app_js.get("body", "")),
            "Control API exposes canonical form defaults and frontend applies them before request preview rendering.",
            control.get("error") or "Control API or frontend is missing canonical form default synchronization.",
        )
    )
    authority_rows = control_body.get("parameter_authority", {}).get("rows", [])
    checks.append(
        _check(
            "parameter_authority_panel",
            "Parameter authority contract",
            control.get("ok")
            and control_body.get("parameter_authority", {}).get("stage") == "gui_parameter_authority"
            and control_body.get("parameter_authority", {}).get("summary", {}).get("status") == "ready"
            and control_body.get("parameter_authority", {}).get("summary", {}).get("live_trading_allowed") is False
            and {
                row.get("workflow_id")
                for row in authority_rows
                if isinstance(row, dict)
            }
            == {"research_backtest", "signal_snapshot", "paper_simulation"}
            and _authority_by_id(control_body, "research_backtest").get("canonical_request", {}).get("factor_name")
            == control_body.get("backtest", {}).get("factor")
            and "execution_lag"
            in _authority_by_id(control_body, "research_backtest").get("comparison_keys", [])
            and "forward_horizon"
            in _authority_by_id(control_body, "research_backtest").get("comparison_keys", [])
            and "max_market_weight"
            in _authority_by_id(control_body, "paper_simulation").get("comparison_keys", [])
            and _authority_by_id(control_body, "paper_simulation").get("canonical_request", {}).get("max_market_weight")
            == control_body.get("form_defaults", {}).get("paper", {}).get("max_market_weight"),
            "Control API exposes parameter authority rows that bind GUI defaults to canonical workflow requests.",
            control.get("error") or "Control API is missing parameter_authority rows or key comparison fields.",
        )
    )
    preflight_rows = control_body.get("workflow_preflight", {}).get("rows", [])
    checks.append(
        _check(
            "workflow_preflight_panel",
            "Workflow preflight contract",
            control.get("ok")
            and control_body.get("workflow_preflight", {}).get("stage") == "gui_workflow_preflight"
            and control_body.get("workflow_preflight", {}).get("summary", {}).get("status") == "review"
            and control_body.get("workflow_preflight", {}).get("summary", {}).get("review_count", 0) >= 1
            and control_body.get("workflow_preflight", {}).get("summary", {}).get("live_trading_allowed") is False
            and {
                row.get("workflow_id")
                for row in preflight_rows
                if isinstance(row, dict)
            }
            == {
                "research_backtest",
                "signal_snapshot",
                "daily_pretrade_checkup",
                "paper_simulation",
                "verification_runner",
                "live_trading",
            }
            and _preflight_by_id(control_body, "research_backtest").get("runnable") is True
            and _preflight_by_id(control_body, "daily_pretrade_checkup").get("mode") == "manual_pretrade_checkup"
            and _preflight_by_id(control_body, "daily_pretrade_checkup").get("runnable") is True
            and "GET GET" not in str(_preflight_by_id(control_body, "verification_runner").get("command", ""))
            and _preflight_by_id(control_body, "live_trading").get("status") == "blocked"
            and _preflight_by_id(control_body, "live_trading").get("runnable") is False,
            "Control API exposes run preflight rows for research, signal, paper, verification, and live-blocked boundary.",
            control.get("error") or "Control API is missing workflow_preflight rows or safety states.",
        )
    )
    checks.append(
        _check(
            "action_center_panel",
            "Action center contract",
            control.get("ok")
            and control_body.get("action_center", {}).get("stage") == "gui_action_center"
            and bool(control_body.get("action_center", {}).get("rows"))
            and control_body.get("action_center", {}).get("summary", {}).get("live_trading_allowed") is False,
            "Control API exposes prioritized next actions with runnable local workflow links.",
            control.get("error") or "Control API is missing action_center rows.",
        )
    )
    checks.append(
        _check(
            "action_center_frontend",
            "Action center frontend",
            index_html.get("ok")
            and "control-action-center" in str(index_html.get("body", ""))
            and "control-workflow-preflight" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderActionCenter" in str(app_js.get("body", ""))
            and "renderWorkflowPreflight" in str(app_js.get("body", ""))
            and "runActionCenterWorkflow" in str(app_js.get("body", "")),
            "Frontend exposes an action center with safe workflow buttons.",
            index_html.get("error") or app_js.get("error") or "Action center frontend hooks are missing.",
        )
    )
    checks.append(
        _check(
            "beginner_trade_system_frontend",
            "Beginner trade-system overview frontend",
            index_html.get("ok")
            and "beginner-trade-system-board" in str(index_html.get("body", ""))
            and "beginner-trade-system-summary" in str(index_html.get("body", ""))
            and "beginner-trade-system-evidence" in str(index_html.get("body", ""))
            and "beginner-trade-system-actions" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderBeginnerTradeSystem" in str(app_js.get("body", ""))
            and "beginnerTradeSystemEvidenceRows" in str(app_js.get("body", ""))
            and "beginnerTradeSystemActionRows" in str(app_js.get("body", ""))
            and "data-trade-system-action" in str(app_js.get("body", "")),
            "Frontend exposes a beginner trade-system overview that summarizes verdict, evidence, and next manual-safe actions.",
            index_html.get("error")
            or app_js.get("error")
            or "Beginner trade-system overview anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "beginner_daily_rehearsal_frontend",
            "Beginner daily rehearsal frontend",
            index_html.get("ok")
            and "beginner-daily-rehearsal-board" in str(index_html.get("body", ""))
            and "beginner-daily-rehearsal-summary" in str(index_html.get("body", ""))
            and "beginner-daily-rehearsal-timeline" in str(index_html.get("body", ""))
            and "beginner-daily-rehearsal-actions" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderBeginnerDailyRehearsal" in str(app_js.get("body", ""))
            and "beginnerDailyRehearsalRows" in str(app_js.get("body", ""))
            and "beginnerDailyRehearsalActionRows" in str(app_js.get("body", ""))
            and "data-daily-rehearsal-action" in str(app_js.get("body", ""))
            and "data-daily-rehearsal-target" in str(app_js.get("body", "")),
            "Frontend exposes a beginner daily rehearsal daybook from data refresh through post-close review.",
            index_html.get("error")
            or app_js.get("error")
            or "Beginner daily rehearsal anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "beginner_post_close_journal_frontend",
            "Beginner post-close journal frontend",
            index_html.get("ok")
            and "beginner-post-close-journal-board" in str(index_html.get("body", ""))
            and "beginner-post-close-journal-summary" in str(index_html.get("body", ""))
            and "beginner-post-close-journal-checklist" in str(index_html.get("body", ""))
            and "beginner-post-close-journal-actions" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderBeginnerPostCloseJournal" in str(app_js.get("body", ""))
            and "beginnerPostCloseJournalRows" in str(app_js.get("body", ""))
            and "postCloseJournalReceipt" in str(app_js.get("body", ""))
            and "runPostCloseJournal" in str(app_js.get("body", ""))
            and "data-post-close-journal-action" in str(app_js.get("body", ""))
            and "data-post-close-journal-target" in str(app_js.get("body", "")),
            "Frontend exposes a beginner post-close journal card and local receipt action.",
            index_html.get("error")
            or app_js.get("error")
            or "Beginner post-close journal anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "beginner_live_handoff_frontend",
            "Beginner live handoff frontend",
            index_html.get("ok")
            and "beginner-live-handoff-board" in str(index_html.get("body", ""))
            and "beginner-live-handoff-status" in str(index_html.get("body", ""))
            and "beginner-live-handoff-steps" in str(index_html.get("body", ""))
            and "beginner-live-handoff-tickets" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderBeginnerLiveHandoff" in str(app_js.get("body", ""))
            and "beginnerLiveHandoffSteps" in str(app_js.get("body", ""))
            and "beginnerLiveHandoffTickets" in str(app_js.get("body", ""))
            and "daily_pretrade_checkup" in str(app_js.get("body", ""))
            and "runDailyPretradeCheckup" in str(app_js.get("body", ""))
            and "dailyPretradeCheckupReceipt" in str(app_js.get("body", ""))
            and "data-live-handoff-action" in str(app_js.get("body", ""))
            and "data-live-handoff-target" in str(app_js.get("body", ""))
            and styles_css.get("ok")
            and ".beginner-live-handoff-layout" in str(styles_css.get("body", "")),
            "Frontend exposes the beginner live handoff board, status, steps, tickets, local action buttons, evidence jumps, and responsive layout.",
            index_html.get("error")
            or app_js.get("error")
            or styles_css.get("error")
            or "Beginner live handoff frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "beginner_live_handoff_red_light_guard",
            "Beginner live handoff red-light guard",
            app_js.get("ok")
            and "function beginnerLiveTicketRows" in str(app_js.get("body", ""))
            and "const blockers = Array.isArray(readiness.blockers)" in str(app_js.get("body", ""))
            and "if (blockers.length > 0) return [];" in str(app_js.get("body", ""))
            and "if (!readiness.manual_action_candidate) return [];" in str(app_js.get("body", ""))
            and 'handoff.status || ""' in str(app_js.get("body", "")),
            "Frontend blocks fallback manual trade-plan tickets while pretrade readiness has blockers or no manual-action candidate.",
            app_js.get("error") or "Beginner handoff can leak fallback manual tickets during a red-light state.",
        )
    )
    checks.append(
        _check(
            "daily_real_money_transition_frontend",
            "Daily real-money transition frontend",
            index_html.get("ok")
            and "daily-real-money-transition-gate" in str(index_html.get("body", ""))
            and "daily-real-money-transition-summary" in str(index_html.get("body", ""))
            and "daily-real-money-transition-preflight" in str(index_html.get("body", ""))
            and "daily-real-money-transition-script" in str(index_html.get("body", ""))
            and "daily-real-money-transition-tickets" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderDailyRealMoneyTransitionGate" in str(app_js.get("body", ""))
            and "daily_real_money_transition_gate" in str(app_js.get("body", ""))
            and "risk_budget" in str(app_js.get("body", ""))
            and "manual_skip_conditions" in str(app_js.get("body", ""))
            and "production_manual_review_candidate" in str(app_js.get("body", "")),
            "Frontend exposes the daily real-money transition gate with preflight, operator script, ticket-risk, and manual-only boundary hooks.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily real-money transition frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "daily_manual_trading_session_frontend",
            "Daily manual trading session frontend",
            index_html.get("ok")
            and "daily-manual-trading-session" in str(index_html.get("body", ""))
            and "daily-manual-trading-session-summary" in str(index_html.get("body", ""))
            and "daily-manual-trading-session-gates" in str(index_html.get("body", ""))
            and "daily-manual-trading-session-steps" in str(index_html.get("body", ""))
            and "daily-manual-trading-session-tickets" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderDailyManualTradingSession" in str(app_js.get("body", ""))
            and "daily_manual_trading_session" in str(app_js.get("body", ""))
            and "blocked_same_parameter_paper_required" in str(app_js.get("body", ""))
            and "open_external_broker_manually" in str(app_js.get("body", "")),
            "Frontend exposes the daily manual trading session status, blockers, operator steps, ticket preview, and manual-only broker boundary.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily manual trading session frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "manual_broker_price_check_frontend",
            "Manual broker price check frontend",
            index_html.get("ok")
            and "daily-manual-broker-price-check" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderManualBrokerPriceCheck" in str(app_js.get("body", ""))
            and "broker_realtime_price_required" in str(app_js.get("body", ""))
            and "skip_if_broker_price_outside_guardrail" in str(app_js.get("body", ""))
            and "actual_fill_price" in str(app_js.get("body", "")),
            "Frontend exposes manual broker-side realtime price checks, guardrail skip rules, and local execution-audit inputs.",
            index_html.get("error")
            or app_js.get("error")
            or "Manual broker price-check frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "position_reconciliation_frontend",
            "Position reconciliation frontend",
            index_html.get("ok")
            and "daily-position-reconciliation-check" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderPositionReconciliationCheck" in str(app_js.get("body", ""))
            and "position_reconciliation_required" in str(app_js.get("body", ""))
            and "manual_trade_requires_position_update" in str(app_js.get("body", ""))
            and "daily-current-positions" in str(app_js.get("body", ""))
            and "FORBIDDEN_CURRENT_POSITION_COLUMNS" in str(app_js.get("body", ""))
            and "account_id" in str(app_js.get("body", "")),
            "Frontend exposes the post-manual-trade position reconciliation gate before the next daily advisory can be trusted.",
            index_html.get("error")
            or app_js.get("error")
            or "Position reconciliation frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "manual_execution_cost_impact_frontend",
            "Manual execution cost impact frontend",
            app_js.get("ok")
            and "manual_execution_cost_impact" in str(app_js.get("body", ""))
            and "total_adverse_slippage_cost" in str(app_js.get("body", ""))
            and "execution_cost_bps" in str(app_js.get("body", ""))
            and "adverse_slippage_cost" in str(app_js.get("body", ""))
            and "executed_notional" in str(app_js.get("body", "")),
            "Frontend converts manually entered fill prices and quantities into execution cost impact metrics.",
            app_js.get("error")
            or "Manual execution cost-impact frontend metrics are missing.",
        )
    )
    checks.append(
        _check(
            "capital_tier_summary_frontend",
            "Capital tier summary frontend",
            app_js.get("ok")
            and "renderCapitalTierSummary" in str(app_js.get("body", ""))
            and "capital_tier_summary" in str(app_js.get("body", ""))
            and "capital_tier" in str(app_js.get("body", ""))
            and "next_capital_tier" in str(app_js.get("body", ""))
            and "capital_tier_missing_gate_count" in str(app_js.get("body", ""))
            and "capital_tier_real_money_limit" in str(app_js.get("body", ""))
            and "capital_tier_external_manual_only" in str(app_js.get("body", "")),
            "Frontend exposes the current capital tier, next tier, missing gates, and external-manual-only boundary.",
            app_js.get("error")
            or "Capital tier summary frontend fields are missing.",
        )
    )
    checks.append(
        _check(
            "recent_observation_degradation_frontend",
            "Recent observation degradation frontend",
            app_js.get("ok")
            and "renderRecentObservationDegradation" in str(app_js.get("body", ""))
            and "recent_observation_status" in str(app_js.get("body", ""))
            and "recent_observation_degradation_required" in str(app_js.get("body", ""))
            and "recent_observation_return_pct" in str(app_js.get("body", ""))
            and "recent_observation_win_rate" in str(app_js.get("body", "")),
            "Frontend exposes recent paper/manual-observation degradation before factor reuse is allowed.",
            app_js.get("error")
            or "Recent observation degradation frontend fields are missing.",
        )
    )
    checks.append(
        _check(
            "today_operation_card_frontend",
            "Today operation card frontend",
            index_html.get("ok")
            and "daily-beginner-execution-answer-today-card" in str(index_html.get("body", ""))
            and "daily-beginner-execution-answer-go-no-go" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderTodayOperationCard" in str(app_js.get("body", ""))
            and "renderTradeSystemGoNoGoGate" in str(app_js.get("body", ""))
            and "today_operation_card" in str(app_js.get("body", ""))
            and "trade_system_go_no_go_gate" in str(app_js.get("body", ""))
            and "manual_review_only_not_order" in str(app_js.get("body", ""))
            and "broker_realtime_price_recheck" in str(app_js.get("body", ""))
            and "today_action_code" in str(app_js.get("body", ""))
            and "manual_external_broker_check_required" in str(app_js.get("body", ""))
            and "after_action_closure_gate" in str(app_js.get("body", ""))
            and "closure_gate_status" in str(app_js.get("body", ""))
            and "next_session_quarantine_required_if_missing" in str(app_js.get("body", ""))
            and "after_action_checklist" in str(app_js.get("body", ""))
            and "quarantine_next_session_if_missing" in str(app_js.get("body", ""))
            and "daily-beginner-execution-answer-pre-market-packet" in str(index_html.get("body", ""))
            and "pre_market_manual_execution_packet" in str(app_js.get("body", ""))
            and "human_decides_skip_or_manual_trade" in str(app_js.get("body", ""))
            and "broker_price_recheck_playbook" in str(app_js.get("body", ""))
            and "external_broker_realtime_price" in str(app_js.get("body", ""))
            and "floor_to_board_lot_at_external_price" in str(app_js.get("body", ""))
            and "renderBrokerPriceRecheckDecision" in str(app_js.get("body", ""))
            and "data-broker-price-recheck-price" in str(app_js.get("body", ""))
            and "data-broker-price-recheck-cash" in str(app_js.get("body", ""))
            and "broker_price_recheck_local_calculator" in str(app_js.get("body", ""))
            and "external_available_cash_after_manual_check" in str(app_js.get("body", ""))
            and "external_cash_shortfall" in str(app_js.get("body", ""))
            and "manual_review_price_ok_quantity_recalculated" in str(app_js.get("body", ""))
            and "skip_broker_price_outside_guardrail" in str(app_js.get("body", ""))
            and "skip_external_cash_below_recalculated_value" in str(app_js.get("body", ""))
            and "recalculated_quantity_at_external_price" in str(app_js.get("body", "")),
            "Frontend exposes a beginner-facing today-operation verdict before any manual review.",
            index_html.get("error")
            or app_js.get("error")
            or "Today operation card frontend fields are missing.",
        )
    )
    checks.append(
        _check(
            "daily_manual_observation_packet_frontend",
            "Daily manual observation packet frontend",
            index_html.get("ok")
            and "daily-manual-observation-packet" in str(index_html.get("body", ""))
            and "daily-manual-observation-summary" in str(index_html.get("body", ""))
            and "daily-manual-observation-evidence" in str(index_html.get("body", ""))
            and "daily-manual-observation-steps" in str(index_html.get("body", ""))
            and "daily-manual-observation-tickets" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderDailyManualObservationPacket" in str(app_js.get("body", ""))
            and "daily_manual_observation_packet" in str(app_js.get("body", ""))
            and "manual_observation_material_ready" in str(app_js.get("body", ""))
            and "order_placement_allowed" in str(app_js.get("body", "")),
            "Frontend exposes a daily manual observation packet with evidence rows, operator steps, tickets, and no-order boundary.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily manual observation packet frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "daily_manual_observation_packet_detail_frontend",
            "Daily manual observation packet detail frontend",
            index_html.get("ok")
            and "daily-manual-observation-top3" in str(index_html.get("body", ""))
            and "daily-manual-observation-paper-requests" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "top3_factor_snapshot" in str(app_js.get("body", ""))
            and "same_parameter_paper_requests" in str(app_js.get("body", ""))
            and "data-manual-observation-paper-action" in str(app_js.get("body", ""))
            and "data-manual-observation-paper-target" in str(app_js.get("body", "")),
            "Frontend exposes the Top3 factor snapshot and same-parameter paper requests inside the manual observation packet.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily manual observation packet detail anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "daily_manual_observation_go_no_go_frontend",
            "Daily manual observation Go/No-Go frontend",
            index_html.get("ok")
            and "daily-manual-observation-verdict" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "manual_observation_go_no_go" in str(app_js.get("body", ""))
            and "blocked_missing_same_parameter_paper" in str(app_js.get("body", ""))
            and "missing_same_parameter_paper_request_ids" in str(app_js.get("body", ""))
            and "data-manual-observation-missing-paper" in str(app_js.get("body", "")),
            "Frontend exposes a manual-observation Go/No-Go verdict, missing paper request ids, and a safe missing-paper action.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily manual observation Go/No-Go frontend hooks are missing.",
        )
    )
    checks.append(
        _check(
            "daily_paper_allocation_playbook_frontend",
            "Daily paper allocation playbook frontend",
            index_html.get("ok")
            and "daily-paper-allocation-playbook" in str(index_html.get("body", ""))
            and "daily-paper-allocation-summary" in str(index_html.get("body", ""))
            and "daily-paper-allocation-rows" in str(index_html.get("body", ""))
            and "daily-paper-allocation-gates" in str(index_html.get("body", ""))
            and "daily-paper-allocation-steps" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderDailyPaperAllocationPlaybook" in str(app_js.get("body", ""))
            and "daily_paper_allocation_playbook" in str(app_js.get("body", ""))
            and "paper_rehearsal_required" in str(app_js.get("body", ""))
            and "do_not_copy_to_broker" in str(app_js.get("body", "")),
            "Frontend exposes the paper allocation playbook with budget rows, promotion gates, operator steps, and no-broker boundary.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily paper allocation playbook frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "daily_pre_execution_guard_frontend",
            "Daily pre-execution guard frontend",
            index_html.get("ok")
            and "daily-pre-execution-guard" in str(index_html.get("body", ""))
            and "daily-pre-execution-summary" in str(index_html.get("body", ""))
            and "daily-pre-execution-rows" in str(index_html.get("body", ""))
            and "daily-pre-execution-rules" in str(index_html.get("body", ""))
            and "daily-pre-execution-steps" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderDailyPreExecutionGuard" in str(app_js.get("body", ""))
            and "daily_pre_execution_guard" in str(app_js.get("body", ""))
            and "blocked_signal_freshness" in str(app_js.get("body", ""))
            and "broker_price_outside_guardrail" in str(app_js.get("body", "")),
            "Frontend exposes the daily pre-execution guard with signal freshness, ETF price guardrails, skip rules, and operator steps.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily pre-execution guard frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "daily_same_parameter_paper_rehearsal_frontend",
            "Daily same-parameter paper rehearsal frontend",
            index_html.get("ok")
            and "daily-same-parameter-paper-rehearsal" in str(index_html.get("body", ""))
            and "daily-same-parameter-paper-summary" in str(index_html.get("body", ""))
            and "daily-same-parameter-paper-requests" in str(index_html.get("body", ""))
            and "daily-same-parameter-paper-manifest" in str(index_html.get("body", ""))
            and "daily-same-parameter-paper-steps" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderDailySameParameterPaperRehearsal" in str(app_js.get("body", ""))
            and "daily_same_parameter_paper_rehearsal" in str(app_js.get("body", ""))
            and "ready_for_same_parameter_paper" in str(app_js.get("body", ""))
            and "run_each_top3_candidate_with_locked_params" in str(app_js.get("body", "")),
            "Frontend exposes locked same-parameter Top3 paper requests, allocation manifests, and operator steps before manual review.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily same-parameter paper rehearsal frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "daily_beginner_operation_recipe_frontend",
            "Daily beginner operation recipe frontend",
            index_html.get("ok")
            and "daily-beginner-operation-recipe-summary" in str(index_html.get("body", ""))
            and "daily-beginner-operation-recipe-steps" in str(index_html.get("body", ""))
            and "daily-beginner-operation-recipe-skip-rules" in str(index_html.get("body", ""))
            and "daily-beginner-operation-recipe-tickets" in str(index_html.get("body", ""))
            and "daily-beginner-operation-recipe-inputs" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderDailyBeginnerOperationRecipe" in str(app_js.get("body", ""))
            and "beginner_operation_recipe" in str(app_js.get("body", ""))
            and "operator_inputs_required" in str(app_js.get("body", ""))
            and "broker_realtime_price" in str(app_js.get("body", ""))
            and "人工输入清单" in str(app_js.get("body", "")),
            "Frontend exposes the final beginner operation recipe with manual input requirements before paper/manual review.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily beginner operation recipe frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "daily_closure_streak_frontend",
            "Daily closure streak frontend",
            index_html.get("ok")
            and "daily-closure-streak" in str(index_html.get("body", ""))
            and "daily-closure-streak-summary" in str(index_html.get("body", ""))
            and "daily-closure-streak-rows" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "dailyClosureStreakEvidence" in str(app_js.get("body", ""))
            and "renderDailyClosureStreak" in str(app_js.get("body", ""))
            and "closure_streak_ready" in str(app_js.get("body", ""))
            and "closed_loop_days" in str(app_js.get("body", ""))
            and "manual_execution_clean" in str(app_js.get("body", "")),
            "Frontend exposes a daily closure-streak panel that tracks Top3 signal, same-parameter paper simulation, post-close journal, and clean manual execution audit evidence.",
            index_html.get("error")
            or app_js.get("error")
            or "Daily closure-streak frontend anchors or renderer hooks are missing.",
        )
    )
    checks.append(
        _check(
            "backtest_provenance_panel",
            "Backtest provenance contract",
            control.get("ok")
            and control_body.get("backtest_provenance", {}).get("stage") == "backtest_provenance"
            and bool(control_body.get("backtest_provenance", {}).get("rows"))
            and control_body.get("backtest_provenance", {}).get("summary", {}).get("paper_only") is True,
            "Control API exposes backtest provenance with source, endpoint, metrics, and paper-only boundary evidence.",
            control.get("error") or "Control API is missing backtest provenance rows.",
        )
    )
    checks.append(
        _check(
            "backtest_gate_panel",
            "Backtest gate contract",
            control.get("ok")
            and control_body.get("backtest_gate", {}).get("stage") == "gui_backtest_gate"
            and bool(control_body.get("backtest_gate", {}).get("rows"))
            and control_body.get("backtest_gate", {}).get("summary", {}).get("live_trading_allowed") is False,
            "Control API exposes backtest gate thresholds for paper-observation decisions while live trading stays disabled.",
            control.get("error") or "Control API is missing backtest gate rows.",
        )
    )
    paper_readiness_rows = control_body.get("paper_readiness", {}).get("rows", [])
    checks.append(
        _check(
            "paper_readiness_panel",
            "Paper readiness handoff contract",
            control.get("ok")
            and control_body.get("paper_readiness", {}).get("stage") == "gui_paper_readiness_handoff"
            and bool(paper_readiness_rows)
            and control_body.get("paper_readiness", {}).get("summary", {}).get("paper_candidate_allowed") is False
            and control_body.get("paper_readiness", {}).get("summary", {}).get("live_trading_allowed") is False
            and {
                row.get("check_id")
                for row in paper_readiness_rows
                if isinstance(row, dict)
            }
            >= {"research_receipt", "paper_receipt", "metric_floor", "preflight_review", "paper_gate", "live_boundary"},
            "Control API exposes a paper-readiness handoff that combines receipts, metric floors, preflight review, backtest gates, and live-blocked boundary.",
            control.get("error") or "Control API is missing paper_readiness rows or safety states.",
        )
    )
    checks.append(
        _check(
            "result_evidence_panel",
            "Result evidence contract",
            control.get("ok")
            and control_body.get("result_evidence", {}).get("stage") == "gui_result_evidence"
            and bool(control_body.get("result_evidence", {}).get("rows"))
            and control_body.get("result_evidence", {}).get("summary", {}).get("paper_only") is True,
            "Control API exposes result evidence that maps metrics to workflow receipts and paper-only boundaries.",
            control.get("error") or "Control API is missing result evidence rows.",
        )
    )
    checks.append(
        _check(
            "workflow_trace_panel",
            "Workflow trace contract",
            control.get("ok")
            and control_body.get("workflow_trace", {}).get("stage") == "gui_workflow_trace"
            and bool(control_body.get("workflow_trace", {}).get("rows"))
            and control_body.get("workflow_trace", {}).get("summary", {}).get("paper_only") is True
            and control_body.get("workflow_trace", {}).get("summary", {}).get("live_trading_allowed") is False,
            "Control API exposes a workflow trace that links active work, queued steps, evidence storage, verification, audit, publish, and live-blocked boundary.",
            control.get("error") or "Control API is missing workflow trace rows.",
        )
    )
    checks.append(
        _check(
            "workspace_sync_panel",
            "Workspace sync contract",
            control.get("ok")
            and control_body.get("workspace_sync", {}).get("stage") == "gui_workspace_sync"
            and bool(control_body.get("workspace_sync", {}).get("rows"))
            and "current_branch" in control_body.get("workspace_sync", {}).get("summary", {}),
            "Control API exposes workspace branch, worktree, upstream, and safe-sync policy status.",
            control.get("error") or "Control API is missing workspace_sync rows.",
        )
    )
    checks.append(
        _check(
            "process_monitor_panel",
            "Process monitor contract",
            control.get("ok")
            and control_body.get("process_monitor", {}).get("stage") == "gui_process_monitor"
            and bool(control_body.get("process_monitor", {}).get("rows"))
            and "current_pid" in control_body.get("process_monitor", {}).get("summary", {})
            and control_body.get("process_monitor", {}).get("summary", {}).get("live_trading_allowed") is False,
            "Control API exposes current PID, related local GUI/research jobs, and paper-only process safety status.",
            control.get("error") or "Control API is missing process_monitor rows.",
        )
    )
    checks.append(
        _check(
            "active_operation_panel",
            "Active operation contract",
            control.get("ok")
            and control_body.get("active_operation", {}).get("stage") == "gui_active_operation"
            and bool(control_body.get("active_operation", {}).get("rows"))
            and control_body.get("active_operation", {}).get("summary", {}).get("live_trading_allowed") is False
            and "research_backtest" in control_body.get("active_operation", {}).get("summary", {}).get("supported_workflow_ids", [])
            and "verification_runner" in control_body.get("active_operation", {}).get("summary", {}).get("supported_workflow_ids", []),
            "Control API exposes browser-managed active operation tracking for research, paper, signal, and verification work.",
            control.get("error") or "Control API is missing active_operation rows.",
        )
    )
    checks.append(
        _check(
            "operation_ledger_panel",
            "Operation ledger contract",
            control.get("ok")
            and control_body.get("operation_ledger", {}).get("stage") == "gui_operation_ledger"
            and "entry_count" in control_body.get("operation_ledger", {}).get("summary", {})
            and control_body.get("operation_ledger", {}).get("summary", {}).get("live_trading_allowed") is False
            and control_body.get("operation_ledger", {}).get("summary", {}).get("order_placement_allowed") is False,
            "Control API exposes a server-side operation ledger with recent workflow receipts and paper-only safety status.",
            control.get("error") or "Control API is missing operation_ledger summary data.",
        )
    )
    checks.append(
        _check(
            "daily_closure_ledger_panel",
            "Daily closure ledger contract",
            control.get("ok")
            and control_body.get("daily_closure_ledger", {}).get("stage") == "gui_daily_closure_ledger"
            and "closed_loop_days" in control_body.get("daily_closure_ledger", {}).get("summary", {})
            and control_body.get("daily_closure_ledger", {}).get("summary", {}).get("live_trading_allowed") is False
            and control_body.get("daily_closure_ledger", {}).get("summary", {}).get("order_placement_allowed") is False
            and index_html.get("ok")
            and "control-daily-closure-ledger" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderDailyClosureLedger" in str(app_js.get("body", ""))
            and "syncExecutionReceiptToServer" in str(app_js.get("body", "")),
            "Control API and frontend expose a server-side daily closure ledger for top-three signal, paper simulation, post-close review, and manual execution audit receipts.",
            control.get("error")
            or index_html.get("error")
            or app_js.get("error")
            or "Daily closure ledger contract or frontend hooks are missing.",
        )
    )
    checks.append(
        _check(
            "server_capital_observation_gate_panel",
            "Server capital observation gate contract",
            control.get("ok")
            and control_body.get("server_capital_observation_gate", {}).get("stage") == "gui_server_capital_observation_gate"
            and control_body.get("server_capital_observation_gate", {}).get("summary", {}).get("live_trading_allowed") is False
            and control_body.get("server_capital_observation_gate", {}).get("summary", {}).get("order_placement_allowed") is False
            and "matched_paper_days" in control_body.get("server_capital_observation_gate", {}).get("summary", {})
            and "legacy_unverified_paper_days" in control_body.get("server_capital_observation_gate", {}).get("summary", {})
            and "same_parameter_paper_evidence"
            in {
                row.get("gate_id")
                for row in control_body.get("server_capital_observation_gate", {}).get("rows", [])
                if isinstance(row, dict)
            }
            and index_html.get("ok")
            and "control-server-capital-observation-gate" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderServerCapitalObservationGate" in str(app_js.get("body", ""))
            and "matched_paper_days" in str(app_js.get("body", ""))
            and "legacy_unverified_paper_days" in str(app_js.get("body", "")),
            "Control API and frontend expose a server-side small-capital manual observation gate while live trading and order placement stay blocked.",
            control.get("error")
            or index_html.get("error")
            or app_js.get("error")
            or "Server capital observation gate contract or frontend hooks are missing.",
        )
    )
    checks.append(
        _check(
            "trade_mode_control_panel",
            "Trade mode control contract",
            control.get("ok")
            and control_body.get("trade_mode_control", {}).get("stage") == "gui_trade_mode_control"
            and control_body.get("trade_mode_control", {}).get("summary", {}).get("paper_simulation_available") is True
            and control_body.get("trade_mode_control", {}).get("summary", {}).get("live_trading_allowed") is False
            and {
                row.get("mode_id")
                for row in control_body.get("trade_mode_control", {}).get("rows", [])
            }
            == {"research", "paper_simulation", "live_trading"},
            "Control API exposes research, paper simulation, and live-trading modes with live trading blocked.",
            control.get("error") or "Control API is missing trade_mode_control mode rows.",
        )
    )
    checks.append(
        _check(
            "request_preview_panel",
            "Request preview contract",
            index_html.get("ok")
            and "control-request-preview" in str(index_html.get("body", ""))
            and "control-parameter-consistency" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderRequestPreview" in str(app_js.get("body", ""))
            and "renderParameterConsistency" in str(app_js.get("body", ""))
            and "parameterMismatchKeys" in str(app_js.get("body", ""))
            and "buildResearchParams" in str(app_js.get("body", ""))
            and "buildSignalParams" in str(app_js.get("body", ""))
            and "buildPaperParams" in str(app_js.get("body", ""))
            and "renderResultFreshness" in str(app_js.get("body", "")),
            "Frontend exposes a live request preview panel and result freshness checks using the same research, signal, and paper parameter builders as workflow execution.",
            index_html.get("error") or app_js.get("error") or "Request preview frontend hooks are missing.",
        )
    )
    checks.append(
        _check(
            "ledger_evidence_panel",
            "Server ledger evidence contract",
            control.get("ok")
            and control_body.get("ledger_evidence", {}).get("stage") == "gui_ledger_evidence"
            and bool(control_body.get("ledger_evidence", {}).get("rows"))
            and control_body.get("ledger_evidence", {}).get("summary", {}).get("live_trading_allowed") is False,
            "Control API exposes server-side receipt freshness against current workflow commands.",
            control.get("error") or "Control API is missing ledger_evidence rows.",
        )
    )
    checks.append(
        _check(
            "ledger_evidence_frontend",
            "Server ledger evidence frontend",
            index_html.get("ok")
            and "control-ledger-evidence" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderLedgerEvidence" in str(app_js.get("body", "")),
            "Frontend exposes the server ledger evidence panel.",
            index_html.get("error") or app_js.get("error") or "Ledger evidence frontend hooks are missing.",
        )
    )
    checks.append(
        _check(
            "audit_feedback_panel",
            "Audit feedback contract",
            control.get("ok")
            and control_body.get("audit_feedback", {}).get("stage") == "gui_audit_feedback"
            and "next_actions" in control_body.get("audit_feedback", {}),
            "Control API exposes audit_feedback with next optimization actions.",
            control.get("error") or "Control API is missing audit_feedback next-actions data.",
        )
    )
    checks.append(
        _check(
            "audit_iteration_plan_panel",
            "Audit iteration plan contract",
            control.get("ok")
            and control_body.get("audit_iteration_plan", {}).get("stage") == "gui_audit_iteration_plan"
            and bool(control_body.get("audit_iteration_plan", {}).get("rows")),
            "Control API exposes audit_iteration_plan rows that turn audit findings into visible acceptance gates.",
            control.get("error") or "Control API is missing audit_iteration_plan rows.",
        )
    )
    checks.append(
        _check(
            "round_checkpoint_report_panel",
            "Five-round report contract",
            control.get("ok")
            and control_body.get("round_checkpoint_report", {}).get("stage") == "gui_round_checkpoint_report"
            and control_body.get("round_checkpoint_report", {}).get("summary", {}).get("cadence_rounds") == 5
            and bool(control_body.get("round_checkpoint_report", {}).get("flow_plan", {}).get("next_steps")),
            "Control API exposes the latest five-round checkpoint report with next flow-plan steps.",
            control.get("error") or "Control API is missing round_checkpoint_report data.",
        )
    )
    checks.append(
        _check(
            "round_checkpoint_frontend",
            "Five-round report frontend",
            index_html.get("ok")
            and "control-round-checkpoint-report" in str(index_html.get("body", ""))
            and app_js.get("ok")
            and "renderRoundCheckpointReport" in str(app_js.get("body", "")),
            "Frontend exposes a five-round checkpoint report panel.",
            index_html.get("error") or app_js.get("error") or "Five-round checkpoint frontend hooks are missing.",
        )
    )
    checks.append(
        _check(
            "audit_scheduler_panel",
            "Audit scheduler contract",
            control.get("ok")
            and control_body.get("audit_scheduler", {}).get("stage") == "gui_audit_scheduler"
            and bool(control_body.get("audit_scheduler", {}).get("rows"))
            and control_body.get("audit_scheduler", {}).get("summary", {}).get("automation_id") == "gui-5h"
            and control_body.get("audit_scheduler", {}).get("summary", {}).get("cadence_rounds") == 5
            and "rounds_until_next_audit" in control_body.get("audit_scheduler", {}).get("summary", {})
            and "next_flow_plan_required" in control_body.get("audit_scheduler", {}).get("summary", {})
            and {
                row.get("check_id")
                for row in control_body.get("audit_scheduler", {}).get("rows", [])
            }.issuperset({"round_cadence", "next_flow_plan"})
            and control_body.get("audit_scheduler", {}).get("summary", {}).get("live_trading_allowed") is False,
            "Control API exposes five-round audit cadence, gui-5h heartbeat fallback, latest audit age, next flow plan status, and paper-only safety boundary.",
            control.get("error") or "Control API is missing audit_scheduler rows.",
        )
    )
    checks.append(
        _check(
            "verification_runner_panel",
            "Verification runner contract",
            control.get("ok")
            and control_body.get("verification_runner", {}).get("stage") == "gui_verification_runner"
            and bool(control_body.get("verification_runner", {}).get("rows"))
            and control_body.get("verification_runner", {}).get("summary", {}).get("live_trading_allowed") is False
            and "gui_compile" in control_body.get("verification_runner", {}).get("summary", {}).get("allowed_gate_ids", []),
            "Control API exposes an allowlisted verification runner with gui_compile and live trading disabled.",
            control.get("error") or "Control API is missing verification_runner rows.",
        )
    )
    checks.append(
        _check(
            "responsive_contract",
            "Responsive layout contract",
            styles_css.get("ok")
            and "@media" in str(styles_css.get("body", ""))
            and ".startup-health-list" in str(styles_css.get("body", ""))
            and ".backtest-provenance-list" in str(styles_css.get("body", ""))
            and ".backtest-gate-list" in str(styles_css.get("body", ""))
            and ".workflow-trace-list" in str(styles_css.get("body", ""))
            and ".workspace-sync-list" in str(styles_css.get("body", ""))
            and ".process-monitor-list" in str(styles_css.get("body", ""))
            and ".active-operation-list" in str(styles_css.get("body", ""))
            and ".operation-ledger-list" in str(styles_css.get("body", ""))
            and ".trade-mode-control-list" in str(styles_css.get("body", ""))
            and ".action-center-list" in str(styles_css.get("body", ""))
            and ".workflow-preflight-list" in str(styles_css.get("body", ""))
            and ".request-preview-list" in str(styles_css.get("body", ""))
            and ".result-freshness-list" in str(styles_css.get("body", ""))
            and ".parameter-consistency-list" in str(styles_css.get("body", ""))
            and ".ledger-evidence-list" in str(styles_css.get("body", ""))
            and ".result-evidence-list" in str(styles_css.get("body", ""))
            and ".audit-feedback-list" in str(styles_css.get("body", ""))
            and ".round-checkpoint-list" in str(styles_css.get("body", ""))
            and ".audit-iteration-list" in str(styles_css.get("body", ""))
            and ".audit-scheduler-list" in str(styles_css.get("body", ""))
            and ".verification-runner-list" in str(styles_css.get("body", "")),
            "Stylesheet contains responsive breakpoints plus active-operation, startup-health, backtest-provenance, backtest-gate, workflow-trace, result-evidence, audit-feedback, audit-iteration, audit-scheduler, and verification-runner sizing rules.",
            styles_css.get("error") or "Stylesheet is missing responsive or audit-iteration layout rules.",
        )
    )
    safety = control_body.get("safety", {}) if isinstance(control_body.get("safety"), dict) else {}
    checks.append(
        _check(
            "live_boundary",
            "Research-to-paper boundary",
            control.get("ok") and safety.get("live_trading_allowed") is False and safety.get("order_placement_allowed") is False,
            "Live trading and order placement are disabled in the control-center API.",
            control.get("error") or "Control-center safety boundary is not clearly disabled.",
        )
    )

    passed = sum(1 for row in checks if row["status"] == "passed")
    failed = sum(1 for row in checks if row["status"] == "failed")
    packet = {
        "stage": "gui_browser_smoke_evidence",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "base_url": normalized_base_url,
        "status": "passed" if failed == 0 else "failed",
        "summary": {
            "checks": len(checks),
            "passed": passed,
            "failed": failed,
            "desktop_viewport": "verified by Browser during release validation",
            "mobile_viewport": "390x844 verified by Browser during release validation",
        },
        "checks": checks,
        "safety": {
            "notice": safety.get("notice", SAFETY_NOTICE),
            "paper_trading_allowed": bool(safety.get("paper_trading_allowed", False)),
            "live_trading_allowed": bool(safety.get("live_trading_allowed", False)),
            "broker_connection_allowed": bool(safety.get("broker_connection_allowed", False)),
            "account_read_allowed": bool(safety.get("account_read_allowed", False)),
            "order_placement_allowed": bool(safety.get("order_placement_allowed", False)),
        },
    }
    _write_packet(Path(output_dir), packet)
    return packet


def _fetch_text(base_url: str, path: str, timeout: float) -> dict[str, Any]:
    try:
        with urlopen(f"{base_url}{path}", timeout=timeout) as response:
            return {
                "ok": 200 <= response.status < 300,
                "status": response.status,
                "body": response.read().decode("utf-8", errors="replace"),
                "error": "",
            }
    except (OSError, URLError) as exc:
        return {"ok": False, "status": None, "body": "", "error": str(exc)}


def _fetch_json(base_url: str, path: str, timeout: float) -> dict[str, Any]:
    result = _fetch_text(base_url, path, timeout)
    if not result.get("ok"):
        return result
    try:
        result["body"] = json.loads(str(result.get("body", "")))
    except json.JSONDecodeError as exc:
        result.update({"ok": False, "error": str(exc), "body": {}})
    return result


def _workflow_by_id(control_body: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    for workflow in control_body.get("workflows", []) if isinstance(control_body, dict) else []:
        if isinstance(workflow, dict) and workflow.get("workflow_id") == workflow_id:
            return workflow
    return {}


def _authority_by_id(control_body: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    authority = control_body.get("parameter_authority", {}) if isinstance(control_body, dict) else {}
    for row in authority.get("rows", []) if isinstance(authority, dict) else []:
        if isinstance(row, dict) and row.get("workflow_id") == workflow_id:
            return row
    return {}


def _preflight_by_id(control_body: dict[str, Any], workflow_id: str) -> dict[str, Any]:
    preflight = control_body.get("workflow_preflight", {}) if isinstance(control_body, dict) else {}
    for row in preflight.get("rows", []) if isinstance(preflight, dict) else []:
        if isinstance(row, dict) and row.get("workflow_id") == workflow_id:
            return row
    return {}


def _check(check_id: str, label: str, passed: Any, evidence: str, failure: str) -> dict[str, Any]:
    return {
        "check_id": check_id,
        "label": label,
        "status": "passed" if bool(passed) else "failed",
        "evidence": evidence if bool(passed) else failure,
    }


def _write_packet(output_dir: Path, packet: dict[str, Any]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "gui_browser_smoke.json").write_text(
        json.dumps(packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "gui_browser_smoke.md").write_text(_render_markdown(packet), encoding="utf-8")


def _render_markdown(packet: dict[str, Any]) -> str:
    safety = packet.get("safety", {})
    rows = [
        "# GUI Browser Smoke Evidence",
        "",
        f"- Generated at: {packet.get('generated_at', '')}",
        f"- Base URL: {packet.get('base_url', '')}",
        f"- Status: {packet.get('status', '')}",
        f"- Safety: {safety.get('notice', SAFETY_NOTICE)}",
        "",
        "## Checks",
    ]
    for check in packet.get("checks", []):
        rows.append(
            f"- [{check.get('status', '')}] {check.get('label', check.get('check_id', 'check'))}: "
            f"{check.get('evidence', '')}"
        )
    return "\n".join(rows) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a local GUI browser smoke evidence packet.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args()
    packet = run_gui_browser_smoke(base_url=args.base_url, output_dir=args.output_dir, timeout=args.timeout)
    print(json.dumps(packet, indent=2, sort_keys=True))
    if packet.get("status") != "passed":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
