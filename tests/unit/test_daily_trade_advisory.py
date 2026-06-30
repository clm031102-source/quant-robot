import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.daily_trade_advisory import (
    build_daily_trade_decision_sheet,
    build_manual_ticket_export,
    build_daily_trade_advisory_pack,
    build_daily_pretrade_workflow,
    select_daily_top_factor_candidates,
    write_daily_trade_advisory_pack,
)


class DailyTradeAdvisoryTests(unittest.TestCase):
    def test_selects_top_three_signalable_cn_etf_candidates(self):
        leaderboard = {
            "leaderboards": {
                "primary_cn_etf": {
                    "rows": [
                        {"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.1},
                        {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.9},
                        {"rank": 3, "case_id": "c3", "factor_name": "cn_stock_aux", "market": "CN", "sharpe": 3.0},
                        {"rank": 4, "case_id": "c4", "factor_name": "volatility_2", "market": "CN_ETF", "sharpe": 0.8},
                        {"rank": 5, "case_id": "c5", "factor_name": "not_registered", "market": "CN_ETF", "sharpe": 2.2},
                    ]
                }
            }
        }

        selected = select_daily_top_factor_candidates(
            leaderboard,
            runnable_factor_names={"momentum_2", "reversal_2", "volatility_2"},
            limit=3,
        )

        self.assertEqual([row["factor_name"] for row in selected], ["momentum_2", "reversal_2", "volatility_2"])
        self.assertTrue(all(row["market"] == "CN_ETF" for row in selected))
        self.assertTrue(all(row["signalable"] for row in selected))

    def test_builds_manual_only_trade_pack_from_three_signals(self):
        candidates = [
            {"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.2},
            {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.8},
            {"rank": 3, "case_id": "c3", "factor_name": "volatility_2", "market": "CN_ETF", "sharpe": 0.7},
        ]
        signal_snapshots = [
            _signal("c1", "momentum_2", {"510300": 0.4, "588000": 0.3}),
            _signal("c2", "reversal_2", {"510300": 0.2, "159915": 0.5}),
            _signal("c3", "volatility_2", {"588000": 0.2, "159915": 0.4}),
        ]

        pack = build_daily_trade_advisory_pack(
            candidates,
            signal_snapshots,
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        self.assertEqual(pack["stage"], "phase_6_0_daily_trade_advisory")
        self.assertEqual(pack["summary"]["selected_factor_count"], 3)
        self.assertEqual(pack["summary"]["signal_count"], 3)
        self.assertFalse(pack["summary"]["live_trading_allowed"])
        self.assertFalse(pack["summary"]["order_placement_allowed"])
        self.assertTrue(pack["summary"]["manual_execution_required"])
        self.assertEqual(pack["combined_target_count"], 3)
        self.assertGreater(pack["combined_targets"][0]["target_value"], 0)
        self.assertTrue(all(not row["executable"] for row in pack["manual_trade_plan"]))
        self.assertTrue(all(row["board_lot_size"] == 100 for row in pack["manual_trade_plan"]))
        self.assertTrue(all(row["estimated_quantity"] > 0 for row in pack["manual_trade_plan"]))
        self.assertTrue(all(row["rounded_quantity"] % 100 == 0 for row in pack["manual_trade_plan"]))
        self.assertTrue(all(row["rounded_value"] == row["rounded_quantity"] * row["latest_price"] for row in pack["manual_trade_plan"]))
        self.assertTrue(all("cash_delta_after_rounding" in row for row in pack["manual_trade_plan"]))
        self.assertIn("manual", pack["operator_checklist"][0]["check_id"])
        self.assertIn("不连接券商", pack["safety"])

    def test_manual_plan_rounds_to_board_lot_without_enabling_orders(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        ticket = pack["manual_trade_plan"][0]

        self.assertAlmostEqual(ticket["target_value"], 33300.0)
        self.assertAlmostEqual(ticket["latest_price"], 3.2)
        self.assertAlmostEqual(ticket["estimated_quantity"], 10406.25)
        self.assertEqual(ticket["rounded_quantity"], 10400)
        self.assertAlmostEqual(ticket["rounded_value"], 33280.0)
        self.assertAlmostEqual(ticket["cash_delta_after_rounding"], 20.0)
        self.assertFalse(ticket["live_order_allowed"])
        self.assertFalse(ticket["executable"])
        self.assertIn("系统不会下单", ticket["manual_instruction"])

    def test_manual_plan_uses_current_positions_for_net_rebalance(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
            current_positions=[{"asset_id": "510300", "quantity": 1000, "latest_price": 3.2}],
        )

        ticket = pack["manual_trade_plan"][0]

        self.assertEqual(pack["summary"]["current_position_count"], 1)
        self.assertEqual(ticket["side"], "buy")
        self.assertAlmostEqual(ticket["current_quantity"], 1000)
        self.assertAlmostEqual(ticket["current_value"], 3200.0)
        self.assertAlmostEqual(ticket["target_value"], 33300.0)
        self.assertAlmostEqual(ticket["delta_value"], 30100.0)
        self.assertAlmostEqual(ticket["estimated_quantity_delta"], 9406.25)
        self.assertEqual(ticket["rounded_quantity"], 9400)
        self.assertEqual(ticket["rounded_quantity_delta"], 9400)
        self.assertAlmostEqual(ticket["rounded_value"], 30080.0)
        self.assertAlmostEqual(ticket["cash_delta_after_rounding"], 20.0)
        self.assertIn("当前持仓", ticket["manual_instruction"])
        self.assertFalse(ticket["live_order_allowed"])
        self.assertFalse(ticket["executable"])

        action_summary = pack["beginner_action_summary"]

        self.assertEqual(action_summary["stage"], "phase_6_8_beginner_action_summary")
        self.assertEqual(action_summary["summary"]["decision"], "manual_review_only")
        self.assertIn("模拟盘", action_summary["summary"]["primary_action"])
        self.assertEqual(action_summary["ticket_summary"]["buy_ticket_count"], 1)
        self.assertEqual(action_summary["ticket_summary"]["sell_ticket_count"], 0)
        self.assertEqual(action_summary["steps"][0]["step_id"], "run_paper_simulation_first")
        self.assertEqual(action_summary["steps"][1]["step_id"], "review_net_rebalance_tickets")
        self.assertTrue(all(not row["live_order_allowed"] for row in action_summary["steps"]))

        live_gate = pack["daily_live_readiness_gate"]

        self.assertEqual(live_gate["stage"], "phase_6_9_daily_live_readiness_gate")
        self.assertEqual(live_gate["summary"]["decision"], "paper_rehearsal_required")
        self.assertIn("模拟盘", live_gate["summary"]["primary_action"])
        self.assertEqual(live_gate["summary"]["cta_label"], "运行模拟盘复核")
        self.assertEqual(live_gate["summary"]["cta_target"], "paper-metrics")
        self.assertEqual(live_gate["summary"]["action_workflow"], "paper_simulation")
        self.assertFalse(live_gate["summary"]["live_trading_allowed"])
        self.assertFalse(live_gate["summary"]["order_placement_allowed"])
        self.assertEqual(live_gate["mode_ladder"][0]["mode_id"], "research_signal")
        self.assertEqual(live_gate["mode_ladder"][1]["mode_id"], "paper_simulation")
        self.assertEqual(live_gate["mode_ladder"][-1]["status"], "locked")
        self.assertIn("daily_top3_direct_buy", {row["shortcut_id"] for row in live_gate["forbidden_shortcuts"]})

        action_card = pack["beginner_trade_action_card"]
        self.assertEqual(action_card["stage"], "phase_6_10_beginner_trade_action_card")
        self.assertEqual(action_card["summary"]["decision"], "paper_rehearsal_required")
        self.assertEqual(action_card["summary"]["answer_code"], "not_yet")
        self.assertEqual(action_card["summary"]["recommended_mode"], "paper_first_manual_review")
        self.assertFalse(action_card["summary"]["auto_order_allowed"])
        self.assertFalse(action_card["summary"]["broker_connection_allowed"])
        self.assertEqual(action_card["next_action"]["workflow_id"], "paper_simulation")
        self.assertEqual(action_card["next_action"]["target_id"], "paper-metrics")
        self.assertEqual(action_card["evidence"]["manual_ticket_count"], 1)
        self.assertIn("paper_simulation", {row["check_id"] for row in action_card["plain_checklist"]})

    def test_current_position_account_fields_are_blocked_without_crashing(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
            current_positions=[{"asset_id": "510300", "quantity": 1000, "latest_price": 3.2, "account_id": "real"}],
        )

        validation = pack["current_position_validation"]
        readiness = pack["pretrade_readiness"]

        self.assertEqual(validation["status"], "error")
        self.assertEqual(validation["accepted_count"], 0)
        self.assertEqual(pack["summary"]["current_position_issue_count"], 1)
        self.assertIn("current_position_input_invalid", readiness["blockers"])
        self.assertFalse(readiness["manual_action_candidate"])
        self.assertEqual(pack["manual_trade_plan"], [])
        self.assertFalse(pack["summary"]["order_placement_allowed"])
        self.assertEqual(pack["beginner_action_summary"]["summary"]["decision"], "fix_current_positions_first")
        self.assertIn("修正当前持仓", pack["beginner_action_summary"]["summary"]["primary_action"])
        self.assertEqual(pack["beginner_action_summary"]["steps"][0]["step_id"], "fix_current_positions")
        self.assertEqual(pack["daily_live_readiness_gate"]["summary"]["decision"], "blocked_fix_current_positions")
        self.assertEqual(pack["daily_live_readiness_gate"]["summary"]["cta_label"], "修正当前持仓")
        self.assertEqual(pack["daily_live_readiness_gate"]["summary"]["cta_target"], "daily-current-positions")
        self.assertIsNone(pack["daily_live_readiness_gate"]["summary"]["action_workflow"])
        self.assertEqual(pack["daily_live_readiness_gate"]["gate_rows"][0]["gate_id"], "current_positions")
        self.assertEqual(pack["daily_live_readiness_gate"]["gate_rows"][0]["status"], "blocked")
        self.assertFalse(pack["daily_live_readiness_gate"]["summary"]["broker_connection_allowed"])
        self.assertEqual(pack["beginner_trade_action_card"]["summary"]["decision"], "blocked_fix_current_positions")
        self.assertEqual(pack["beginner_trade_action_card"]["next_action"]["target_id"], "daily-current-positions")
        self.assertFalse(pack["beginner_trade_action_card"]["summary"]["can_manual_review_today"])

    def test_pretrade_readiness_summarizes_manual_action_without_live_permissions(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        readiness = pack["pretrade_readiness"]

        self.assertEqual(readiness["stage"], "phase_6_2_manual_pretrade_readiness")
        self.assertEqual(readiness["traffic_light"], "yellow")
        self.assertTrue(readiness["manual_action_candidate"])
        self.assertFalse(readiness["live_order_allowed"])
        self.assertFalse(readiness["broker_connection_allowed"])
        self.assertFalse(readiness["order_placement_allowed"])
        self.assertEqual(readiness["blockers"], [])
        self.assertAlmostEqual(readiness["summary"]["target_value"], 33300.0)
        self.assertAlmostEqual(readiness["summary"]["rounded_value"], 33280.0)
        self.assertAlmostEqual(readiness["summary"]["cash_delta_after_rounding"], 20.0)
        self.assertEqual(readiness["action_sequence"][0]["rounded_quantity"], 10400)
        self.assertIn("manual_only_boundary", {item["check_id"] for item in readiness["required_confirmations"]})
        self.assertEqual(pack["pretrade_workflow"]["pretrade_readiness"], readiness)

    def test_pretrade_readiness_blocks_stale_signal_dates_before_manual_handoff(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2, signal_date="2026-05-21")],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        readiness = pack["pretrade_readiness"]
        handoff = pack["manual_broker_handoff"]

        self.assertEqual(readiness["traffic_light"], "red")
        self.assertFalse(readiness["manual_action_candidate"])
        self.assertIn("stale_signal_date", readiness["blockers"])
        self.assertEqual(readiness["freshness"]["run_date"], "2026-06-29")
        self.assertEqual(readiness["freshness"]["latest_signal_date"], "2026-05-21")
        self.assertFalse(readiness["freshness"]["fresh_for_run_date"])
        self.assertIn("signal_freshness", {item["check_id"] for item in readiness["required_confirmations"]})
        self.assertEqual(handoff["status"], "blocked_by_freshness")
        self.assertEqual(handoff["copyable_tickets"], [])
        self.assertIn("stale_signal_date", handoff["blocking_reasons"])
        self.assertEqual(pack["operator_next_actions"][0]["action_id"], "refresh_cn_etf_data")
        self.assertEqual(pack["operator_next_actions"][0]["status"], "blocked_until_done")
        self.assertIn("stale_signal_date", pack["operator_next_actions"][0]["why"])
        self.assertEqual(pack["operator_next_actions"][0]["cta_target"], "recent-data-refresh-status")
        self.assertEqual(pack["operator_next_actions"][0]["cta_label"], "查看刷新面板")
        self.assertIsNone(pack["operator_next_actions"][0]["action_workflow"])
        self.assertEqual(pack["operator_next_actions"][1]["action_workflow"], "daily_trade_advisory")
        self.assertEqual(pack["operator_next_actions"][2]["action_workflow"], "paper_simulation")
        self.assertEqual(pack["pretrade_workflow"]["summary"]["primary_next_action_id"], "refresh_cn_etf_data")
        self.assertEqual(pack["daily_live_readiness_gate"]["summary"]["decision"], "blocked_pretrade_red_light")
        self.assertEqual(pack["daily_live_readiness_gate"]["summary"]["cta_label"], "查看盘前红灯")
        self.assertEqual(pack["daily_live_readiness_gate"]["summary"]["cta_target"], "daily-pretrade-readiness-verdict")
        self.assertIsNone(pack["daily_live_readiness_gate"]["summary"]["action_workflow"])

    def test_manual_broker_handoff_builds_copyable_review_cards_without_orders(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        handoff = pack["manual_broker_handoff"]

        self.assertEqual(handoff["stage"], "phase_6_3_manual_broker_handoff")
        self.assertEqual(handoff["status"], "review_only")
        self.assertFalse(handoff["ready_for_auto_order"])
        self.assertFalse(handoff["live_order_allowed"])
        self.assertFalse(handoff["broker_connection_allowed"])
        self.assertFalse(handoff["order_placement_allowed"])
        self.assertEqual(handoff["summary"]["ticket_count"], 1)
        self.assertAlmostEqual(handoff["summary"]["rounded_value"], 33280.0)
        self.assertIn("paper_simulation_required", {item["check_id"] for item in handoff["confirmation_checklist"]})
        self.assertIn("manual_only_boundary", {item["check_id"] for item in handoff["confirmation_checklist"]})
        ticket = handoff["copyable_tickets"][0]
        self.assertEqual(ticket["asset_id"], "510300")
        self.assertEqual(ticket["rounded_quantity"], 10400)
        self.assertFalse(ticket["live_order_allowed"])
        self.assertTrue(ticket["do_not_submit_until_checked"])
        self.assertIn("510300", ticket["copy_text"])
        self.assertIn("10400", ticket["copy_text"])
        self.assertIn("系统不会下单", ticket["copy_text"])
        self.assertEqual(pack["pretrade_workflow"]["manual_broker_handoff"], handoff)
        self.assertEqual(pack["operator_next_actions"][0]["action_id"], "run_paper_simulation")
        self.assertEqual(pack["operator_next_actions"][0]["status"], "required_before_manual_ticket")
        self.assertFalse(pack["operator_next_actions"][0]["automation_allowed"])
        self.assertEqual(pack["operator_next_actions"][0]["action_workflow"], "paper_simulation")
        self.assertEqual(pack["operator_next_actions"][0]["cta_label"], "运行模拟盘复核")
        self.assertEqual(pack["operator_next_actions"][1]["cta_target"], "daily-pretrade-readiness-verdict")
        self.assertEqual(pack["operator_next_actions"][2]["cta_target"], "daily-manual-broker-handoff-ticket-table")
        self.assertEqual(pack["pretrade_workflow"]["summary"]["primary_next_action_id"], "run_paper_simulation")

    def test_manual_ticket_export_is_review_only_and_removes_account_order_fields(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        export = build_manual_ticket_export(pack)

        self.assertEqual(export["stage"], "phase_6_13_manual_ticket_export")
        self.assertEqual(export["summary"]["ticket_count"], 1)
        self.assertEqual(export["summary"]["export_status"], "review_only")
        self.assertFalse(export["summary"]["order_placement_allowed"])
        self.assertFalse(export["summary"]["broker_connection_allowed"])
        self.assertFalse(export["summary"]["account_read_allowed"])
        self.assertFalse(export["summary"]["auto_order_allowed"])
        self.assertEqual(export["rows"][0]["asset_id"], "510300")
        self.assertEqual(export["rows"][0]["rounded_quantity"], 10400)
        self.assertEqual(export["rows"][0]["review_only"], True)
        self.assertEqual(export["columns"][0], "step_number")
        self.assertIn("csv_text", export)
        self.assertIn("markdown_text", export)
        self.assertIn("510300", export["csv_text"])
        self.assertIn("10400", export["csv_text"])
        self.assertIn("manual_review_only", export["csv_text"])
        for forbidden in ["account_id", "broker_id", "client_id", "order_id", "order_placement_allowed"]:
            self.assertNotIn(forbidden, export["csv_text"])
            self.assertNotIn(forbidden, export["columns"])

    def test_daily_trade_decision_sheet_summarizes_today_actions_without_orders(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.2}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        sheet = build_daily_trade_decision_sheet(pack)

        self.assertEqual(sheet["stage"], "phase_6_14_daily_trade_decision_sheet")
        self.assertEqual(sheet["summary"]["decision"], "paper_first_manual_review")
        self.assertEqual(sheet["summary"]["answer_code"], "not_yet")
        self.assertFalse(sheet["summary"]["live_trading_allowed"])
        self.assertFalse(sheet["summary"]["broker_connection_allowed"])
        self.assertFalse(sheet["summary"]["account_read_allowed"])
        self.assertFalse(sheet["summary"]["order_placement_allowed"])
        self.assertEqual(sheet["what_to_do_now"]["target_id"], "paper-metrics")
        self.assertEqual(sheet["daily_top3"][0]["factor_name"], "momentum_2")
        self.assertEqual(sheet["today_actions"][0]["asset_id"], "510300")
        self.assertEqual(sheet["today_actions"][0]["rounded_quantity"], 10400)
        self.assertEqual(sheet["today_actions"][0]["action_type"], "manual_review_ticket")
        self.assertFalse(sheet["today_actions"][0]["order_placement_allowed"])
        self.assertIn("paper_simulation_receipt", {row["check_id"] for row in sheet["missing_evidence"]})
        self.assertIn("post_close_journal_plan", {row["check_id"] for row in sheet["missing_evidence"]})
        self.assertIn("daily_top3_signal_review", {row["step_id"] for row in sheet["operator_script"]})
        system_state = sheet["trade_system_state"]
        self.assertEqual(system_state["stage"], "daily_trade_system_state")
        self.assertEqual(system_state["mode"], "paper_rehearsal_required")
        self.assertFalse(system_state["permissions"]["order_placement_allowed"])
        self.assertFalse(system_state["candidate_pool_policy"]["direct_buy_from_leaderboard_allowed"])
        self.assertEqual(system_state["candidate_pool_policy"]["selection_scope"], "CN_ETF")
        stage_by_id = {row["stage_id"]: row for row in system_state["stages"]}
        self.assertEqual(stage_by_id["candidate_pool"]["status"], "done")
        self.assertEqual(stage_by_id["today_signal"]["status"], "done")
        self.assertEqual(stage_by_id["paper_simulation"]["status"], "required")
        self.assertEqual(stage_by_id["manual_ticket_review"]["status"], "required")
        self.assertEqual(stage_by_id["human_broker_execution"]["status"], "manual_locked")
        self.assertEqual(system_state["progress"]["completed_stage_count"], 2)
        self.assertEqual(system_state["progress"]["required_stage_count"], 3)
        self.assertEqual(system_state["next_gate"]["stage_id"], "paper_simulation")
        self.assertEqual(pack["daily_trade_decision_sheet"]["stage"], "phase_6_14_daily_trade_decision_sheet")

    def test_pretrade_readiness_blocks_when_signals_are_missing(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        readiness = pack["pretrade_readiness"]

        self.assertEqual(readiness["traffic_light"], "red")
        self.assertFalse(readiness["manual_action_candidate"])
        self.assertIn("signal_not_ready", readiness["blockers"])
        self.assertEqual(readiness["summary"]["manual_ticket_count"], 0)

    def test_write_daily_trade_advisory_outputs_operator_files(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.5})],
            run_date="2026-06-29",
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_daily_trade_advisory_pack(output_dir, pack)

            self.assertTrue((output_dir / "daily_trade_advisory_pack.json").exists())
            self.assertTrue((output_dir / "daily_trade_advisory_pack.md").exists())
            self.assertTrue((output_dir / "daily_trade_advisory_targets.csv").exists())
            payload = json.loads((output_dir / "daily_trade_advisory_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["stage"], "phase_6_0_daily_trade_advisory")
            markdown = (output_dir / "daily_trade_advisory_pack.md").read_text(encoding="utf-8")
            self.assertIn("每日交易演练", markdown)
            self.assertIn("收盘后复盘记录", markdown)
            self.assertIn("收盘后复盘", markdown)
            self.assertIn("今天是否人工执行", markdown)
            self.assertIn("实盘落地路径", markdown)
            self.assertIn("自动下单: False", markdown)

    def test_builds_beginner_pretrade_workflow_from_daily_advisory(self):
        pack = build_daily_trade_advisory_pack(
            [
                {"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.2},
                {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.8},
                {"rank": 3, "case_id": "c3", "factor_name": "volatility_2", "market": "CN_ETF", "sharpe": 0.7},
            ],
            [
                _signal("c1", "momentum_2", {"510300": 0.4}),
                _signal("c2", "reversal_2", {"588000": 0.3}),
                _signal("c3", "volatility_2", {"159915": 0.2}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        workflow = build_daily_pretrade_workflow(pack)

        self.assertEqual(workflow["stage"], "phase_6_1_daily_pretrade_workflow")
        self.assertEqual(workflow["summary"]["readiness_status"], "manual_review_required")
        self.assertFalse(workflow["summary"]["live_order_allowed"])
        self.assertFalse(workflow["summary"]["broker_connection_allowed"])
        self.assertEqual(workflow["summary"]["step_count"], 5)
        self.assertEqual(
            [step["step_id"] for step in workflow["steps"]],
            [
                "scope_and_data",
                "factor_signal_review",
                "paper_simulation_review",
                "risk_and_cash_review",
                "manual_broker_execution",
            ],
        )
        self.assertEqual(workflow["steps"][1]["status"], "ready")
        self.assertEqual(workflow["steps"][-1]["status"], "manual_only")
        self.assertIn("系统不会下单", workflow["steps"][-1]["plain_action"])
        self.assertTrue(any("先看前三因子" in card["text"] for card in workflow["beginner_cards"]))

    def test_daily_pack_exposes_manual_trade_system_protocol(self):
        pack = build_daily_trade_advisory_pack(
            [
                {
                    "rank": 1,
                    "case_id": "c1",
                    "factor_name": "momentum_2",
                    "market": "CN_ETF",
                    "sharpe": 1.2,
                    "annualized_return": 0.18,
                    "max_drawdown": -0.22,
                    "win_rate": 0.58,
                    "rank_ic": 0.04,
                }
            ],
            [_signal("c1", "momentum_2", {"510300": 0.4})],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        system = pack["trade_system"]

        self.assertEqual(system["stage"], "phase_6_4_manual_trade_system_protocol")
        self.assertEqual(system["primary_market"], "CN_ETF")
        self.assertEqual(system["daily_selection_rule"]["candidate_limit"], 3)
        self.assertIn("sharpe", system["daily_selection_rule"]["required_metrics"])
        self.assertIn("rank_ic", system["daily_selection_rule"]["required_metrics"])
        self.assertFalse(system["execution_boundary"]["broker_connection_allowed"])
        self.assertFalse(system["execution_boundary"]["order_placement_allowed"])
        self.assertFalse(system["execution_boundary"]["live_order_allowed"])
        self.assertEqual(system["operator_workflow"]["workflow_id"], "daily_pretrade_checkup")
        self.assertIn("manual_broker_handoff", system["operator_workflow"]["evidence_chain"])
        self.assertTrue(system["operator_workflow"]["paper_simulation_required"])
        self.assertEqual(system["go_live_decision"]["status"], "manual_review_only")

    def test_daily_pack_exposes_beginner_daily_rehearsal_daybook(self):
        pack = build_daily_trade_advisory_pack(
            [
                {"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.2},
                {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.8},
                {"rank": 3, "case_id": "c3", "factor_name": "volatility_2", "market": "CN_ETF", "sharpe": 0.7},
            ],
            [
                _signal("c1", "momentum_2", {"510300": 0.4}),
                _signal("c2", "reversal_2", {"588000": 0.3}),
                _signal("c3", "volatility_2", {"159915": 0.2}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        daybook = pack["daily_rehearsal_daybook"]

        self.assertEqual(daybook["stage"], "phase_6_5_daily_rehearsal_daybook")
        self.assertEqual(daybook["run_date"], "2026-06-29")
        self.assertEqual(daybook["summary"]["primary_market"], "CN_ETF")
        self.assertEqual(daybook["summary"]["phase_count"], 6)
        self.assertEqual(daybook["summary"]["current_phase_id"], "paper_simulation_review")
        self.assertTrue(daybook["summary"]["paper_simulation_required"])
        self.assertTrue(daybook["summary"]["post_close_review_required"])
        self.assertFalse(daybook["summary"]["live_order_allowed"])
        self.assertFalse(daybook["summary"]["broker_connection_allowed"])
        self.assertFalse(daybook["summary"]["order_placement_allowed"])
        self.assertEqual(
            [phase["phase_id"] for phase in daybook["phases"]],
            [
                "scope_and_data",
                "top3_signal_generation",
                "paper_simulation_review",
                "risk_cash_review",
                "manual_broker_review",
                "post_close_journal",
            ],
        )
        self.assertEqual(daybook["phases"][0]["status"], "done")
        self.assertEqual(daybook["phases"][1]["status"], "done")
        self.assertEqual(daybook["phases"][2]["status"], "required")
        self.assertEqual(daybook["phases"][-1]["status"], "required")
        self.assertIn("收盘后", daybook["phases"][-1]["plain_action"])
        self.assertTrue(all(not phase["automation_allowed"] for phase in daybook["phases"]))
        self.assertIn("不自动下单", daybook["safety"])

    def test_daily_pack_exposes_post_close_journal_template(self):
        pack = build_daily_trade_advisory_pack(
            [
                {"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.2},
                {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.8},
            ],
            [
                _signal("c1", "momentum_2", {"510300": 0.4}),
                _signal("c2", "reversal_2", {"588000": 0.3}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        journal = pack["post_close_journal_template"]

        self.assertEqual(journal["stage"], "phase_6_6_post_close_journal_template")
        self.assertEqual(journal["run_date"], "2026-06-29")
        self.assertEqual(journal["summary"]["primary_market"], "CN_ETF")
        self.assertEqual(journal["summary"]["question_count"], 5)
        self.assertTrue(journal["summary"]["manual_decision_required"])
        self.assertTrue(journal["summary"]["paper_receipt_required"])
        self.assertFalse(journal["summary"]["live_order_allowed"])
        self.assertFalse(journal["summary"]["order_placement_allowed"])
        self.assertEqual(
            [item["item_id"] for item in journal["items"]],
            [
                "signal_evidence",
                "paper_simulation",
                "manual_decision",
                "risk_observation",
                "next_day_follow_up",
            ],
        )
        self.assertIn("今天是否人工执行", journal["items"][2]["prompt"])
        self.assertIn("次日", journal["items"][-1]["prompt"])
        self.assertTrue(all(not item["automation_allowed"] for item in journal["items"]))
        self.assertIn("不自动下单", journal["safety"])

    def test_daily_pack_exposes_live_transition_plan_without_auto_orders(self):
        pack = build_daily_trade_advisory_pack(
            [
                {
                    "rank": 1,
                    "case_id": "c1",
                    "factor_name": "momentum_2",
                    "market": "CN_ETF",
                    "sharpe": 1.2,
                    "annualized_return": 0.22,
                    "max_drawdown": -0.28,
                    "win_rate": 0.61,
                    "rank_ic": 0.04,
                },
                {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.8},
                {"rank": 3, "case_id": "c3", "factor_name": "volatility_2", "market": "CN_ETF", "sharpe": 0.7},
            ],
            [
                _signal("c1", "momentum_2", {"510300": 0.4}),
                _signal("c2", "reversal_2", {"588000": 0.3}),
                _signal("c3", "volatility_2", {"159915": 0.2}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        plan = pack["live_transition_plan"]

        self.assertEqual(plan["stage"], "phase_6_7_live_transition_plan")
        self.assertEqual(plan["summary"]["primary_market"], "CN_ETF")
        self.assertEqual(plan["summary"]["daily_top_factor_limit"], 3)
        self.assertEqual(plan["summary"]["today_signal_count"], 3)
        self.assertEqual(plan["summary"]["status"], "paper_first_manual_pilot_candidate")
        self.assertTrue(plan["summary"]["paper_simulation_required"])
        self.assertTrue(plan["summary"]["small_capital_review_required"])
        self.assertFalse(plan["summary"]["live_order_allowed"])
        self.assertFalse(plan["summary"]["broker_connection_allowed"])
        self.assertFalse(plan["summary"]["order_placement_allowed"])
        self.assertEqual(plan["daily_top3_signal_rule"]["selection_scope"], "CN_ETF")
        self.assertIn("不能只按今日排行榜直接下单", plan["daily_top3_signal_rule"]["plain_warning"])
        self.assertEqual(
            [step["step_id"] for step in plan["operating_loop"]],
            [
                "fresh_data",
                "top3_factor_signal",
                "portfolio_sizing",
                "paper_simulation",
                "manual_risk_review",
                "small_capital_review_gate",
                "post_close_feedback",
            ],
        )
        self.assertEqual(plan["execution_rules"]["board_lot_size"], 100)
        self.assertIn("T+1", plan["execution_rules"]["settlement_note"])
        self.assertIn("T+0", plan["execution_rules"]["settlement_note"])
        self.assertIn("aggressive_30dd", {row["profile_id"] for row in plan["risk_profiles"]})
        aggressive = next(row for row in plan["risk_profiles"] if row["profile_id"] == "aggressive_30dd")
        self.assertAlmostEqual(aggressive["max_acceptable_drawdown"], 0.30)
        self.assertIn("small_capital_review_gate", plan["evidence_gates"][-1]["gate_id"])
        self.assertTrue(all(not row["automation_allowed"] for row in plan["operating_loop"]))
        self.assertIn("不自动下单", plan["safety"])

    def test_daily_pack_exposes_live_pilot_brief_for_manual_operation(self):
        pack = build_daily_trade_advisory_pack(
            [
                {"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.2},
                {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.8},
                {"rank": 3, "case_id": "c3", "factor_name": "volatility_2", "market": "CN_ETF", "sharpe": 0.7},
            ],
            [
                _signal("c1", "momentum_2", {"510300": 0.4}),
                _signal("c2", "reversal_2", {"588000": 0.3}),
                _signal("c3", "volatility_2", {"159915": 0.2}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
            risk_profile_id="aggressive_30dd",
        )

        brief = pack["daily_live_pilot_brief"]

        self.assertEqual(brief["stage"], "phase_6_11_daily_live_pilot_brief")
        self.assertEqual(brief["summary"]["primary_market"], "CN_ETF")
        self.assertEqual(brief["summary"]["status"], "manual_review_candidate")
        self.assertEqual(brief["summary"]["daily_top_factor_limit"], 3)
        self.assertEqual(brief["summary"]["today_signal_count"], 3)
        self.assertEqual(brief["summary"]["manual_ticket_count"], 3)
        self.assertEqual(brief["today_signal_rule"]["rule_id"], "daily_top3_candidates_not_direct_orders")
        self.assertIn("不能把前三因子直接当买入指令", brief["today_signal_rule"]["plain_warning"])
        self.assertEqual(
            [row["step_id"] for row in brief["manual_operation_steps"]],
            [
                "run_pretrade_checkup",
                "review_top3_signal",
                "run_paper_simulation",
                "review_manual_ticket",
                "human_broker_decision",
                "post_close_journal",
            ],
        )
        self.assertEqual(len(brief["manual_ticket_preview"]), 3)
        self.assertTrue(all(not row["executable"] for row in brief["manual_ticket_preview"]))
        self.assertTrue(all(not row["automation_allowed"] for row in brief["manual_operation_steps"]))
        self.assertFalse(brief["summary"]["broker_connection_allowed"])
        self.assertFalse(brief["summary"]["order_placement_allowed"])
        self.assertIn("aggressive_30dd", brief["risk_budget"]["risk_profile_id"])
        self.assertIn("券商端由人手工决定", brief["execution_boundary"]["plain_boundary"])

    def test_daily_pack_exposes_small_capital_observation_gate(self):
        pack = build_daily_trade_advisory_pack(
            [
                {"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.2},
                {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.8},
                {"rank": 3, "case_id": "c3", "factor_name": "volatility_2", "market": "CN_ETF", "sharpe": 0.7},
            ],
            [
                _signal("c1", "momentum_2", {"510300": 0.4}),
                _signal("c2", "reversal_2", {"588000": 0.3}),
                _signal("c3", "volatility_2", {"159915": 0.2}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
            risk_profile_id="aggressive_30dd",
        )

        gate = pack["small_capital_observation_gate"]
        brief_gate = pack["daily_live_pilot_brief"]["small_capital_observation_gate"]

        self.assertEqual(gate["stage"], "phase_6_12_small_capital_observation_gate")
        self.assertEqual(gate["summary"]["decision"], "evidence_required")
        self.assertEqual(gate["summary"]["minimum_paper_simulation_receipts"], 5)
        self.assertEqual(gate["summary"]["minimum_post_close_journal_receipts"], 5)
        self.assertAlmostEqual(gate["summary"]["max_acceptable_drawdown"], 0.30)
        self.assertFalse(gate["summary"]["live_order_allowed"])
        self.assertFalse(gate["summary"]["broker_connection_allowed"])
        self.assertFalse(gate["summary"]["order_placement_allowed"])
        self.assertEqual(brief_gate["stage"], gate["stage"])
        self.assertEqual(
            [row["gate_id"] for row in gate["gate_rows"]],
            [
                "paper_simulation_receipts",
                "post_close_journal_receipts",
                "latest_paper_drawdown",
                "latest_paper_guard_events",
                "latest_paper_fills",
                "manual_ticket_and_red_light",
                "research_only_safety_boundary",
            ],
        )
        self.assertTrue(all(not row["live_order_allowed"] for row in gate["gate_rows"]))
        self.assertIn("至少 5 次模拟盘", gate["gate_rows"][0]["plain_requirement"])
        self.assertIn("小资金观察", gate["summary"]["plain_answer"])
        self.assertEqual(gate["decision_card"]["title"], "今天能不能小资金观察")
        self.assertEqual(gate["decision_card"]["answer_code"], "not_ready")
        self.assertEqual(gate["decision_card"]["next_workflow_id"], "paper_simulation")
        self.assertEqual(gate["decision_card"]["next_gui_target"], "paper-metrics")
        self.assertFalse(gate["decision_card"]["live_order_allowed"])
        self.assertIn("还不能小资金观察", gate["decision_card"]["plain_answer"])

    def test_selected_risk_profile_caps_daily_target_exposure(self):
        pack = build_daily_trade_advisory_pack(
            [
                {"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.2},
                {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.8},
                {"rank": 3, "case_id": "c3", "factor_name": "volatility_2", "market": "CN_ETF", "sharpe": 0.7},
            ],
            [
                _signal("c1", "momentum_2", {"510300": 0.4, "588000": 0.3}),
                _signal("c2", "reversal_2", {"510300": 0.2, "159915": 0.5}),
                _signal("c3", "volatility_2", {"588000": 0.2, "159915": 0.4}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
            max_gross_exposure=1.0,
            risk_profile_id="conservative_10dd",
        )

        total_weight = sum(row["target_weight"] for row in pack["combined_targets"])
        plan = pack["live_transition_plan"]
        selected_profiles = [row for row in plan["risk_profiles"] if row.get("selected")]

        self.assertAlmostEqual(total_weight, 0.30)
        self.assertEqual(pack["summary"]["risk_profile_id"], "conservative_10dd")
        self.assertEqual(pack["summary"]["applied_max_gross_exposure"], 0.30)
        self.assertEqual(plan["summary"]["selected_risk_profile_id"], "conservative_10dd")
        self.assertEqual(plan["summary"]["applied_max_gross_exposure"], 0.30)
        self.assertEqual(len(selected_profiles), 1)
        self.assertEqual(selected_profiles[0]["profile_id"], "conservative_10dd")
        self.assertTrue(all(not row["executable"] for row in pack["manual_trade_plan"]))


def _signal(
    case_id: str,
    factor_name: str,
    weights: dict[str, float],
    latest_price: float = 1.0,
    signal_date: str = "2026-06-29",
) -> dict[str, object]:
    targets = []
    rebalance = []
    for asset_id, weight in weights.items():
        target_value = weight * 100000
        targets.append(
            {
                "asset_id": asset_id,
                "market": "CN_ETF",
                "target_weight": weight,
                "latest_price": latest_price,
                "signal_date": signal_date,
            }
        )
        rebalance.append(
            {
                "asset_id": asset_id,
                "market": "CN_ETF",
                "target_weight": weight,
                "target_value": target_value,
                "delta_value": target_value,
                "estimated_quantity_delta": target_value / latest_price,
                "action": "increase",
                "executable": False,
            }
        )
    return {
        "case_id": case_id,
        "factor_name": factor_name,
        "as_of_date": signal_date,
        "signal_date": signal_date,
        "targets": targets,
        "rebalance_plan": rebalance,
    }


if __name__ == "__main__":
    unittest.main()
