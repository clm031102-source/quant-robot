import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.daily_trade_advisory import (
    build_daily_candidate_pool_top20,
    build_daily_manual_trading_session,
    build_daily_paper_allocation_playbook,
    build_manual_execution_audit,
    build_daily_trade_decision_sheet,
    build_manual_ticket_export,
    build_daily_trade_advisory_pack as _build_daily_trade_advisory_pack,
    build_daily_pretrade_workflow,
    select_daily_top_factor_candidates,
    write_daily_trade_advisory_pack,
)


_CURRENT_POSITIONS_NOT_SUPPLIED = object()


def build_daily_trade_advisory_pack(
    candidates,
    signal_snapshots,
    *args,
    current_positions=_CURRENT_POSITIONS_NOT_SUPPLIED,
    **kwargs,
):
    if current_positions is _CURRENT_POSITIONS_NOT_SUPPLIED:
        current_positions = _zero_current_positions_from_signals(signal_snapshots)
    return _build_daily_trade_advisory_pack(
        candidates,
        signal_snapshots,
        *args,
        current_positions=current_positions,
        **kwargs,
    )


def _zero_current_positions_from_signals(signal_snapshots):
    rows_by_asset = {}
    for signal in signal_snapshots:
        if not isinstance(signal, dict):
            continue
        source_rows = []
        if isinstance(signal.get("targets"), list):
            source_rows.extend(signal["targets"])
        if isinstance(signal.get("rebalance_plan"), list):
            source_rows.extend(signal["rebalance_plan"])
        for row in source_rows:
            if not isinstance(row, dict):
                continue
            asset_id = str(row.get("asset_id") or "").strip()
            if not asset_id or asset_id in rows_by_asset:
                continue
            rows_by_asset[asset_id] = {
                "asset_id": asset_id,
                "quantity": 0,
                "latest_price": row.get("latest_price") or 1.0,
                "market": row.get("market") or "CN_ETF",
            }
    return list(rows_by_asset.values())


class DailyTradeAdvisoryTests(unittest.TestCase):
    def test_daily_candidate_pool_top20_keeps_rank_context_and_marks_top3(self):
        leaderboard = {
            "leaderboards": {
                "primary_cn_etf": {
                    "rows": [
                        {
                            "rank": 1,
                            "case_id": "c1",
                            "factor_name": "momentum_2",
                            "market": "CN_ETF",
                            "status": "paper_ready",
                            "sharpe": 1.4,
                            "annualized_return": 0.21,
                            "params": {"top_n": 2, "cost_bps": 5},
                        },
                        {
                            "rank": 2,
                            "case_id": "blocked",
                            "factor_name": "reversal_2",
                            "market": "CN_ETF",
                            "status": "rejected",
                            "sharpe": 2.8,
                        },
                        {
                            "rank": 3,
                            "case_id": "not_runnable",
                            "factor_name": "private_factor_x",
                            "market": "CN_ETF",
                            "status": "accepted",
                            "sharpe": 1.2,
                        },
                        {
                            "rank": 4,
                            "case_id": "c4",
                            "factor_name": "liquidity_2",
                            "market": "CN_ETF",
                            "status": "manual_live_review",
                            "sharpe": 1.1,
                        },
                        {
                            "rank": 5,
                            "case_id": "duplicate_factor",
                            "factor_name": "momentum_2",
                            "market": "CN_ETF",
                            "status": "accepted",
                            "sharpe": 1.0,
                        },
                        {
                            "rank": 6,
                            "case_id": "eligible_not_selected",
                            "factor_name": "volume_change_2",
                            "market": "CN_ETF",
                            "status": "accepted",
                            "sharpe": 0.9,
                        },
                        {
                            "rank": 7,
                            "case_id": "cn_stock_aux",
                            "factor_name": "stock_factor",
                            "market": "CN",
                            "status": "accepted",
                            "sharpe": 3.0,
                        },
                    ]
                }
            }
        }
        runnable = {"momentum_2", "reversal_2", "liquidity_2", "volume_change_2"}
        selected = select_daily_top_factor_candidates(leaderboard, runnable_factor_names=runnable, limit=2)

        pool = build_daily_candidate_pool_top20(
            leaderboard,
            selected_candidates=selected,
            runnable_factor_names=runnable,
            limit=20,
        )

        self.assertEqual(pool["stage"], "phase_6_22_daily_candidate_pool_top20")
        self.assertEqual(pool["summary"]["primary_market"], "CN_ETF")
        self.assertEqual(pool["summary"]["row_count"], 6)
        self.assertEqual(pool["summary"]["selected_top3_count"], 2)
        self.assertFalse(pool["summary"]["direct_buy_from_leaderboard_allowed"])
        rows_by_case = {row["case_id"]: row for row in pool["rows"]}
        self.assertEqual(rows_by_case["c1"]["selection_status"], "selected_top3")
        self.assertEqual(rows_by_case["c1"]["params"], {"top_n": 2, "cost_bps": 5})
        self.assertEqual(rows_by_case["blocked"]["selection_status"], "blocked")
        self.assertEqual(rows_by_case["not_runnable"]["selection_status"], "not_runnable")
        self.assertEqual(rows_by_case["duplicate_factor"]["selection_status"], "duplicate_factor_name_not_selected")
        self.assertEqual(rows_by_case["eligible_not_selected"]["selection_status"], "eligible_not_selected")
        self.assertTrue(all(row["market"] == "CN_ETF" for row in pool["rows"]))
        self.assertNotIn("cn_stock_aux", rows_by_case)

    def test_selects_top_three_signalable_cn_etf_candidates(self):
        leaderboard = {
            "leaderboards": {
                "primary_cn_etf": {
                    "rows": [
                        {"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.1, "status": "paper_ready"},
                        {"rank": 2, "case_id": "c2", "factor_name": "reversal_2", "market": "CN_ETF", "sharpe": 0.9, "status": "accepted"},
                        {"rank": 3, "case_id": "c3", "factor_name": "cn_stock_aux", "market": "CN", "sharpe": 3.0},
                        {"rank": 4, "case_id": "c4", "factor_name": "volatility_2", "market": "CN_ETF", "sharpe": 0.8, "status": "manual_live_review"},
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
        self.assertTrue(all(row["advisory_eligible"] for row in selected))

    def test_daily_top_three_skips_research_only_blocked_or_thin_candidates(self):
        leaderboard = {
            "leaderboards": {
                "primary_cn_etf": {
                    "rows": [
                        {
                            "rank": 1,
                            "case_id": "blocked_high_return",
                            "factor_name": "momentum_2",
                            "market": "CN_ETF",
                            "status": "blocked",
                            "sharpe": 4.8,
                            "ranking_quality": "qualified",
                            "has_oos_evidence": True,
                        },
                        {
                            "rank": 2,
                            "case_id": "research_only",
                            "factor_name": "reversal_2",
                            "market": "CN_ETF",
                            "status": "research_only",
                            "sharpe": 2.1,
                            "ranking_quality": "qualified",
                            "has_oos_evidence": True,
                        },
                        {
                            "rank": 3,
                            "case_id": "thin_sample",
                            "factor_name": "volatility_2",
                            "market": "CN_ETF",
                            "status": "accepted",
                            "sharpe": 1.4,
                            "ranking_quality": "thin_sample",
                            "has_oos_evidence": True,
                        },
                        {
                            "rank": 4,
                            "case_id": "paper_ready",
                            "factor_name": "liquidity_2",
                            "market": "CN_ETF",
                            "status": "paper_ready",
                            "sharpe": 0.9,
                            "ranking_quality": "qualified",
                            "has_oos_evidence": True,
                        },
                        {
                            "rank": 5,
                            "case_id": "manual_review",
                            "factor_name": "volume_change_2",
                            "market": "CN_ETF",
                            "status": "manual_live_review",
                            "sharpe": 0.8,
                            "ranking_quality": "qualified",
                            "has_oos_evidence": True,
                        },
                    ]
                }
            }
        }

        selected = select_daily_top_factor_candidates(
            leaderboard,
            runnable_factor_names={"momentum_2", "reversal_2", "volatility_2", "liquidity_2", "volume_change_2"},
            limit=3,
        )

        self.assertEqual([row["case_id"] for row in selected], ["paper_ready", "manual_review"])
        self.assertTrue(all(row["advisory_eligible"] for row in selected))
        self.assertNotIn("blocked_high_return", {row["case_id"] for row in selected})
        self.assertNotIn("research_only", {row["case_id"] for row in selected})
        self.assertNotIn("thin_sample", {row["case_id"] for row in selected})

    def test_daily_top_three_blocks_legacy_rows_without_oos_or_paper_gate(self):
        leaderboard = {
            "leaderboards": {
                "primary_cn_etf": {
                    "rows": [
                        {
                            "rank": 1,
                            "case_id": "legacy_high_sharpe",
                            "factor_name": "momentum_2",
                            "market": "CN_ETF",
                            "sharpe": 3.2,
                            "annualized_return": 0.58,
                        },
                        {
                            "rank": 2,
                            "case_id": "paper_ready",
                            "factor_name": "liquidity_2",
                            "market": "CN_ETF",
                            "status": "paper_ready",
                            "sharpe": 0.9,
                        },
                    ]
                }
            }
        }

        selected = select_daily_top_factor_candidates(
            leaderboard,
            runnable_factor_names={"momentum_2", "liquidity_2"},
            limit=3,
        )
        pool = build_daily_candidate_pool_top20(
            leaderboard,
            selected_candidates=selected,
            runnable_factor_names={"momentum_2", "liquidity_2"},
        )

        self.assertEqual([row["case_id"] for row in selected], ["paper_ready"])
        rows_by_case = {row["case_id"]: row for row in pool["rows"]}
        self.assertEqual(rows_by_case["legacy_high_sharpe"]["selection_status"], "blocked")
        self.assertEqual(rows_by_case["legacy_high_sharpe"]["selection_reason"], "missing_paper_ready_or_oos_gate")
        self.assertFalse(rows_by_case["legacy_high_sharpe"]["advisory_eligible"])

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

    def test_current_position_market_mismatch_blocks_manual_tickets(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
            current_positions=[{"asset_id": "CN_XSHE_000001", "market": "CN", "quantity": 1000, "latest_price": 10.0}],
        )

        validation = pack["current_position_validation"]
        readiness = pack["pretrade_readiness"]

        self.assertEqual(validation["status"], "error")
        self.assertEqual(validation["accepted_count"], 0)
        self.assertIn("current_position_market_mismatch", {row["issue_id"] for row in validation["issues"]})
        self.assertIn("current_position_input_invalid", readiness["blockers"])
        self.assertFalse(readiness["manual_action_candidate"])
        self.assertEqual(pack["manual_trade_plan"], [])
        self.assertEqual(pack["manual_broker_handoff"]["copyable_tickets"], [])
        self.assertEqual(pack["daily_live_readiness_gate"]["summary"]["decision"], "blocked_fix_current_positions")
        self.assertEqual(pack["beginner_trade_action_card"]["next_action"]["target_id"], "daily-current-positions")

    def test_missing_current_positions_block_manual_tickets_before_live_handoff(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
            current_positions=None,
        )

        readiness = pack["pretrade_readiness"]
        handoff = pack["manual_broker_handoff"]

        self.assertEqual(pack["current_position_validation"]["status"], "not_provided")
        self.assertIn("current_position_not_provided", readiness["blockers"])
        self.assertFalse(readiness["manual_action_candidate"])
        self.assertEqual(pack["manual_trade_plan"], [])
        self.assertEqual(pack["summary"]["manual_ticket_count"], 0)
        self.assertTrue(pack["summary"]["manual_trade_plan_blocked"])
        self.assertEqual(pack["summary"]["manual_trade_plan_blocked_reason"], "current_positions_not_provided")
        self.assertEqual(handoff["status"], "blocked_by_readiness")
        self.assertEqual(handoff["copyable_tickets"], [])
        self.assertEqual(pack["daily_live_readiness_gate"]["summary"]["decision"], "blocked_fix_current_positions")
        self.assertEqual(pack["beginner_trade_action_card"]["next_action"]["target_id"], "daily-current-positions")

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
        self.assertEqual(
            [row["check_id"] for row in ticket["review_checklist"]],
            [
                "asset_code_match",
                "broker_realtime_price",
                "price_guardrail",
                "quantity_and_lot_size",
                "cash_and_weight_limit",
                "risk_budget_gate",
                "final_human_decision",
            ],
        )
        self.assertTrue(all(row["status"] == "required" for row in ticket["review_checklist"]))
        self.assertIn("price_changed_from_reference", {row["flag_id"] for row in ticket["red_flags"]})
        self.assertIn("cash_or_position_limit_breach", {row["flag_id"] for row in ticket["red_flags"]})
        self.assertTrue(all(not row["order_placement_allowed"] for row in ticket["review_checklist"]))
        self.assertEqual(ticket["risk_budget"]["risk_profile_id"], "balanced_20dd")
        self.assertAlmostEqual(ticket["risk_budget"]["portfolio_value"], 100000.0)
        self.assertAlmostEqual(ticket["risk_budget"]["max_single_etf_weight"], 0.30)
        self.assertAlmostEqual(ticket["risk_budget"]["daily_loss_stop"], 0.02)
        self.assertAlmostEqual(ticket["risk_budget"]["portfolio_daily_loss_budget"], 2000.0)
        self.assertAlmostEqual(ticket["risk_budget"]["ticket_adverse_move_loss"], 665.6)
        self.assertAlmostEqual(ticket["risk_budget"]["ticket_loss_budget_share"], 0.3328)
        self.assertTrue(ticket["risk_budget"]["single_etf_limit_breached"])
        self.assertIn("manual_skip_conditions", ticket)
        skip_conditions = {row["condition_id"]: row for row in ticket["manual_skip_conditions"]}
        self.assertEqual(skip_conditions["single_etf_limit_breached"]["status"], "blocked")
        self.assertIn("broker_price_outside_guardrail", skip_conditions)
        self.assertEqual(skip_conditions["broker_price_outside_guardrail"]["status"], "required")
        self.assertTrue(all(not row["order_placement_allowed"] for row in ticket["manual_skip_conditions"]))
        guardrails = ticket["execution_guardrails"]
        self.assertEqual(guardrails["guardrail_id"], "manual_pretrade_price_slippage_guard")
        self.assertAlmostEqual(guardrails["reference_price"], 3.2)
        self.assertAlmostEqual(guardrails["max_reference_price_deviation_pct"], 0.005)
        self.assertAlmostEqual(guardrails["lower_price_bound"], 3.184)
        self.assertAlmostEqual(guardrails["upper_price_bound"], 3.216)
        self.assertEqual(guardrails["max_slippage_bps"], 10)
        self.assertAlmostEqual(guardrails["max_estimated_slippage_cost"], 33.28)
        self.assertIn("broker_realtime_price", guardrails["manual_input_fields"])
        self.assertIn("execute_or_skip_reason", guardrails["manual_input_fields"])
        self.assertFalse(guardrails["order_placement_allowed"])
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
        self.assertIn("lower_price_bound", export["columns"])
        self.assertIn("upper_price_bound", export["columns"])
        self.assertIn("max_slippage_bps", export["columns"])
        self.assertIn("manual_price_guardrail_note", export["columns"])
        self.assertAlmostEqual(export["rows"][0]["lower_price_bound"], 3.184)
        self.assertAlmostEqual(export["rows"][0]["upper_price_bound"], 3.216)
        self.assertEqual(export["rows"][0]["max_slippage_bps"], 10)
        self.assertIn("csv_text", export)
        self.assertIn("markdown_text", export)
        self.assertIn("510300", export["csv_text"])
        self.assertIn("10400", export["csv_text"])
        self.assertIn("3.184", export["csv_text"])
        self.assertIn("3.216", export["csv_text"])
        self.assertIn("manual_review_only", export["csv_text"])
        for forbidden in ["account_id", "broker_id", "client_id", "order_id", "order_placement_allowed"]:
            self.assertNotIn(forbidden, export["csv_text"])
            self.assertNotIn(forbidden, export["columns"])

    def test_manual_execution_audit_records_fill_slippage_without_orders(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        audit = build_manual_execution_audit(
            pack,
            [
                {
                    "ticket_id": "daily-top3-001",
                    "manual_outcome": "manual_trade_by_human",
                    "actual_fill_price": 3.201,
                    "fill_quantity": 10400,
                    "execute_or_skip_reason": "broker price inside guardrail",
                }
            ],
        )

        self.assertEqual(audit["stage"], "phase_6_23_manual_execution_audit")
        self.assertEqual(audit["summary"]["decision"], "manual_execution_evidence_ready")
        self.assertEqual(audit["summary"]["executed_count"], 1)
        self.assertEqual(audit["summary"]["guardrail_breach_count"], 0)
        self.assertEqual(audit["summary"]["missing_review_count"], 0)
        self.assertFalse(audit["summary"]["order_placement_allowed"])
        row = audit["rows"][0]
        self.assertEqual(row["ticket_id"], "daily-top3-001")
        self.assertEqual(row["asset_id"], "510300")
        self.assertEqual(row["manual_outcome"], "manual_trade_by_human")
        self.assertAlmostEqual(row["reference_price"], 3.2)
        self.assertAlmostEqual(row["actual_fill_price"], 3.201)
        self.assertAlmostEqual(row["adverse_slippage_bps"], 3.125)
        self.assertTrue(row["price_within_guardrail"])
        self.assertTrue(row["slippage_within_limit"])
        self.assertTrue(row["quantity_matches_ticket"])
        self.assertEqual(row["review_status"], "passed")
        self.assertFalse(row["order_placement_allowed"])

    def test_manual_execution_audit_blocks_price_guardrail_breach_and_sensitive_fields(self):
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF"}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
        )

        audit = build_manual_execution_audit(
            pack,
            [
                {
                    "ticket_id": "daily-top3-001",
                    "manual_outcome": "manual_trade_by_human",
                    "actual_fill_price": 3.25,
                    "fill_quantity": 10000,
                    "execute_or_skip_reason": "chased price",
                    "account_id": "real-account",
                }
            ],
        )

        self.assertEqual(audit["summary"]["decision"], "guardrail_breach_review_required")
        self.assertEqual(audit["summary"]["guardrail_breach_count"], 1)
        self.assertEqual(audit["summary"]["sensitive_field_count"], 1)
        row = audit["rows"][0]
        self.assertFalse(row["price_within_guardrail"])
        self.assertFalse(row["slippage_within_limit"])
        self.assertFalse(row["quantity_matches_ticket"])
        self.assertIn("broker_price_outside_guardrail", row["breach_reasons"])
        self.assertIn("slippage_limit_breached", row["breach_reasons"])
        self.assertIn("quantity_mismatch", row["breach_reasons"])
        self.assertIn("sensitive_field_removed", row["breach_reasons"])
        self.assertEqual(row["review_status"], "blocked")
        self.assertFalse(row["order_placement_allowed"])

    def test_daily_trade_decision_sheet_summarizes_today_actions_without_orders(self):
        candidate_pool_top20 = {
            "stage": "phase_6_22_daily_candidate_pool_top20",
            "summary": {
                "primary_market": "CN_ETF",
                "row_count": 2,
                "selected_top3_count": 1,
                "direct_buy_from_leaderboard_allowed": False,
            },
            "rows": [
                {
                    "rank": 1,
                    "case_id": "c1",
                    "factor_name": "momentum_2",
                    "market": "CN_ETF",
                    "selection_status": "selected_top3",
                    "sharpe": 1.2,
                    "annualized_return": 0.18,
                    "max_drawdown": -0.22,
                    "win_rate": 0.58,
                    "rank_ic": 0.04,
                    "params": {"top_n": 2},
                    "direct_buy_allowed": False,
                },
                {
                    "rank": 2,
                    "case_id": "watch",
                    "factor_name": "liquidity_2",
                    "market": "CN_ETF",
                    "selection_status": "eligible_not_selected",
                    "sharpe": 0.9,
                    "params": {"top_n": 3},
                    "direct_buy_allowed": False,
                },
            ],
        }
        pack = build_daily_trade_advisory_pack(
            [{"rank": 1, "case_id": "c1", "factor_name": "momentum_2", "market": "CN_ETF", "sharpe": 1.2}],
            [_signal("c1", "momentum_2", {"510300": 0.333}, latest_price=3.2)],
            run_date="2026-06-29",
            portfolio_value=100000,
            candidate_pool_top20=candidate_pool_top20,
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
        self.assertEqual(sheet["candidate_pool_top20"]["summary"]["row_count"], 2)
        self.assertEqual(sheet["candidate_pool_top20"]["rows"][0]["selection_status"], "selected_top3")
        self.assertEqual(sheet["candidate_pool_top20"]["rows"][1]["selection_status"], "eligible_not_selected")
        self.assertFalse(sheet["candidate_pool_top20"]["summary"]["direct_buy_from_leaderboard_allowed"])
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
        package = sheet["trade_package_checklist"]
        self.assertEqual(package["stage"], "daily_trade_package_checklist")
        self.assertEqual(package["summary"]["status"], "needs_manual_evidence")
        self.assertEqual(package["summary"]["next_step_id"], "paper_simulation_receipt")
        self.assertFalse(package["summary"]["order_placement_allowed"])
        package_steps = {row["step_id"]: row for row in package["items"]}
        self.assertEqual(package_steps["top_factor_pool"]["status"], "done")
        self.assertEqual(package_steps["today_signal_targets"]["status"], "done")
        self.assertEqual(package_steps["manual_ticket_review"]["status"], "done")
        self.assertEqual(package_steps["paper_simulation_receipt"]["status"], "required")
        self.assertEqual(package_steps["post_close_journal"]["status"], "required")
        self.assertEqual(package_steps["manual_safety_boundary"]["status"], "manual_locked")
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

    def test_daily_pack_exposes_real_world_manual_handoff_gate(self):
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

        gate = pack["real_world_manual_handoff_gate"]

        self.assertEqual(gate["stage"], "phase_6_17_real_world_manual_handoff_gate")
        self.assertEqual(gate["summary"]["primary_market"], "CN_ETF")
        self.assertEqual(gate["summary"]["decision"], "paper_first_manual_review_candidate")
        self.assertEqual(gate["summary"]["daily_top_factor_limit"], 3)
        self.assertEqual(gate["summary"]["today_signal_count"], 3)
        self.assertEqual(gate["summary"]["manual_ticket_count"], 3)
        self.assertFalse(gate["summary"]["direct_buy_from_top3_allowed"])
        self.assertFalse(gate["summary"]["live_order_allowed"])
        self.assertFalse(gate["summary"]["broker_connection_allowed"])
        self.assertFalse(gate["summary"]["account_read_allowed"])
        self.assertFalse(gate["summary"]["order_placement_allowed"])
        self.assertFalse(gate["summary"]["auto_order_allowed"])
        self.assertEqual(gate["daily_top3_signal_contract"]["selection_scope"], "CN_ETF")
        self.assertIn("前三因子只是候选入口", gate["daily_top3_signal_contract"]["plain_warning"])
        self.assertEqual(
            [row["step_id"] for row in gate["manual_operation_runbook"]],
            [
                "generate_daily_top3_signal",
                "run_pretrade_checkup",
                "run_same_parameter_paper",
                "review_manual_tickets",
                "human_broker_manual_decision",
                "post_close_journal",
            ],
        )
        self.assertTrue(all(not row["order_placement_allowed"] for row in gate["manual_operation_runbook"]))
        preview_by_asset = {row["asset_id"]: row for row in gate["manual_ticket_preview"]}
        self.assertIn("510300", preview_by_asset)
        self.assertFalse(preview_by_asset["510300"]["executable"])
        self.assertIn("软件不会下单", preview_by_asset["510300"]["plain_instruction"])
        self.assertIn("aggressive_30dd", gate["risk_budget"]["risk_profile_id"])
        self.assertIn("30%", gate["risk_budget"]["plain_budget"])
        self.assertIn("paper_simulation_receipt", {row["gate_id"] for row in gate["go_live_blockers"]})
        self.assertIn("manual_broker_manual_decision", {row["boundary_id"] for row in gate["safety_boundaries"]})
        self.assertEqual(
            [row["stage_id"] for row in gate["capital_deployment_ladder"]],
            [
                "research_signal",
                "same_parameter_paper",
                "small_capital_manual_observation",
                "production_manual_review",
            ],
        )
        paper_stage = gate["capital_deployment_ladder"][1]
        small_capital_stage = gate["capital_deployment_ladder"][2]
        production_stage = gate["capital_deployment_ladder"][3]
        self.assertEqual(paper_stage["status"], "required")
        self.assertEqual(paper_stage["workflow_id"], "paper_simulation")
        self.assertIn("同参数模拟盘", paper_stage["plain_requirement"])
        self.assertEqual(small_capital_stage["minimum_matched_paper_receipts"], 5)
        self.assertEqual(small_capital_stage["minimum_post_close_journals"], 5)
        self.assertEqual(production_stage["minimum_paper_ready_observations"], 20)
        self.assertTrue(all(not row["broker_connection_allowed"] for row in gate["capital_deployment_ladder"]))
        self.assertTrue(all(not row["order_placement_allowed"] for row in gate["capital_deployment_ladder"]))

    def test_daily_pack_exposes_deployment_readiness_pack_for_top3_to_manual_flow(self):
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

        readiness = pack["daily_deployment_readiness"]

        self.assertEqual(readiness["stage"], "phase_6_18_daily_deployment_readiness_pack")
        self.assertEqual(readiness["summary"]["primary_market"], "CN_ETF")
        self.assertEqual(readiness["summary"]["decision"], "paper_first_manual_review_candidate")
        self.assertTrue(readiness["summary"]["daily_top3_supported"])
        self.assertTrue(readiness["summary"]["paper_rehearsal_allowed"])
        self.assertTrue(readiness["summary"]["manual_review_material_ready"])
        self.assertFalse(readiness["summary"]["direct_buy_from_top3_allowed"])
        self.assertFalse(readiness["summary"]["live_order_allowed"])
        self.assertFalse(readiness["summary"]["broker_connection_allowed"])
        self.assertFalse(readiness["summary"]["account_read_allowed"])
        self.assertFalse(readiness["summary"]["order_placement_allowed"])
        self.assertEqual(readiness["summary"]["next_workflow_id"], "paper_simulation")
        self.assertEqual(readiness["summary"]["next_target_id"], "paper-metrics")
        self.assertEqual(
            [row["step_id"] for row in readiness["daily_operating_sequence"]],
            [
                "qualified_top3_candidates",
                "same_day_signal_snapshot",
                "pretrade_red_light_gate",
                "same_parameter_paper_rehearsal",
                "manual_ticket_review",
                "human_broker_decision",
                "post_close_feedback",
            ],
        )
        self.assertIn("paper_simulation_receipt", {row["gate_id"] for row in readiness["readiness_gates"]})
        self.assertIn("lookahead_bias_audit", {row["control_id"] for row in readiness["profitability_controls"]})
        self.assertIn("multiple_testing_control", {row["control_id"] for row in readiness["profitability_controls"]})
        preview_by_asset = {row["asset_id"]: row for row in readiness["manual_buy_sell_preview"]}
        self.assertIn("510300", preview_by_asset)
        self.assertEqual(preview_by_asset["510300"]["operation"], "buy")
        self.assertFalse(preview_by_asset["510300"]["order_placement_allowed"])
        self.assertIn("not_order", preview_by_asset["510300"]["warning_code"])

    def test_daily_pack_exposes_live_profitability_readiness_scorecard(self):
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

        readiness = pack["live_profitability_readiness"]

        self.assertEqual(readiness["stage"], "phase_6_19_live_profitability_readiness_scorecard")
        self.assertEqual(readiness["summary"]["decision"], "not_ready_for_real_money")
        self.assertFalse(readiness["summary"]["profitability_claim_allowed"])
        self.assertFalse(readiness["summary"]["real_money_allowed"])
        self.assertFalse(readiness["summary"]["live_order_allowed"])
        self.assertFalse(readiness["summary"]["broker_connection_allowed"])
        self.assertFalse(readiness["summary"]["order_placement_allowed"])
        self.assertTrue(readiness["summary"]["paper_rehearsal_allowed"])
        self.assertTrue(readiness["summary"]["manual_review_material_ready"])
        self.assertEqual(readiness["summary"]["next_workflow_id"], "paper_simulation")
        self.assertEqual(readiness["summary"]["next_target_id"], "paper-metrics")
        self.assertLess(readiness["summary"]["readiness_score_pct"], 60)
        self.assertEqual(pack["summary"]["live_profitability_readiness_status"], "not_ready_for_real_money")
        self.assertEqual(
            [row["gate_id"] for row in readiness["hard_gates"]],
            [
                "cn_etf_scope",
                "same_day_signal",
                "pretrade_red_light",
                "manual_ticket",
                "walk_forward_oos",
                "lookahead_bias_audit",
                "multiple_testing_control",
                "transaction_cost_capacity",
                "matched_paper_receipts",
                "post_close_journals",
                "manual_execution_quality",
                "production_sample_size",
                "research_only_safety_boundary",
            ],
        )
        gate_by_id = {row["gate_id"]: row for row in readiness["hard_gates"]}
        self.assertEqual(gate_by_id["matched_paper_receipts"]["minimum_required_observations"], 5)
        self.assertEqual(gate_by_id["post_close_journals"]["minimum_required_observations"], 5)
        self.assertEqual(gate_by_id["manual_execution_quality"]["minimum_required_observations"], 5)
        self.assertEqual(gate_by_id["production_sample_size"]["minimum_required_observations"], 20)
        self.assertIn("run_same_parameter_paper", {row["action_id"] for row in readiness["today_allowed_actions"]})
        self.assertIn("direct_buy_top3", {row["action_id"] for row in readiness["forbidden_actions"]})
        self.assertIn("kill_switch_drawdown", {row["control_id"] for row in readiness["stability_controls"]})
        self.assertTrue(all(not row["order_placement_allowed"] for row in readiness["hard_gates"]))

    def test_live_profitability_readiness_uses_evidence_snapshot_without_opening_orders(self):
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
            evidence_snapshot={
                "walk_forward_oos_passed": True,
                "lookahead_bias_audit_passed": True,
                "multiple_testing_control_passed": True,
                "transaction_cost_capacity_passed": True,
                "matched_paper_receipts": 5,
                "post_close_journals": 5,
                "manual_execution_clean_receipts": 5,
                "manual_execution_blocked_receipts": 0,
                "paper_ready_observations": 20,
            },
        )

        readiness = pack["live_profitability_readiness"]
        gate_by_id = {row["gate_id"]: row for row in readiness["hard_gates"]}

        self.assertEqual(readiness["summary"]["evidence_mode"], "snapshot")
        self.assertEqual(readiness["summary"]["matched_paper_receipts"], 5)
        self.assertEqual(readiness["summary"]["post_close_journal_receipts"], 5)
        self.assertEqual(readiness["summary"]["manual_execution_clean_receipts"], 5)
        self.assertEqual(readiness["summary"]["manual_execution_blocked_receipts"], 0)
        self.assertEqual(readiness["summary"]["paper_ready_observations"], 20)
        self.assertGreaterEqual(readiness["summary"]["readiness_score_pct"], 90)
        self.assertTrue(readiness["summary"]["small_capital_observation_candidate"])
        self.assertTrue(readiness["summary"]["production_manual_review_candidate"])
        self.assertFalse(readiness["summary"]["real_money_allowed"])
        self.assertFalse(readiness["summary"]["order_placement_allowed"])
        self.assertEqual(gate_by_id["walk_forward_oos"]["status"], "pass")
        self.assertEqual(gate_by_id["lookahead_bias_audit"]["status"], "pass")
        self.assertEqual(gate_by_id["multiple_testing_control"]["status"], "pass")
        self.assertEqual(gate_by_id["transaction_cost_capacity"]["status"], "pass")
        self.assertEqual(gate_by_id["matched_paper_receipts"]["status"], "pass")
        self.assertEqual(gate_by_id["matched_paper_receipts"]["observed_count"], 5)
        self.assertEqual(gate_by_id["post_close_journals"]["status"], "pass")
        self.assertEqual(gate_by_id["manual_execution_quality"]["status"], "pass")
        self.assertEqual(gate_by_id["manual_execution_quality"]["observed_count"], 5)
        self.assertEqual(gate_by_id["production_sample_size"]["status"], "pass")
        self.assertEqual(
            readiness["evidence_snapshot"]["missing_counts"]["matched_paper_receipts"],
            0,
        )
        self.assertEqual(
            readiness["evidence_snapshot"]["missing_counts"]["manual_execution_clean_receipts"],
            0,
        )
        self.assertEqual(readiness["summary"]["next_target_id"], "beginner-live-handoff-board")

    def test_live_profitability_readiness_blocks_dirty_manual_execution_audit(self):
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
            evidence_snapshot={
                "walk_forward_oos_passed": True,
                "lookahead_bias_audit_passed": True,
                "multiple_testing_control_passed": True,
                "transaction_cost_capacity_passed": True,
                "matched_paper_receipts": 5,
                "post_close_journals": 5,
                "manual_execution_clean_receipts": 4,
                "manual_execution_blocked_receipts": 1,
                "manual_execution_missing_review_receipts": 0,
                "paper_ready_observations": 20,
            },
        )

        readiness = pack["live_profitability_readiness"]
        gate_by_id = {row["gate_id"]: row for row in readiness["hard_gates"]}

        self.assertEqual(readiness["summary"]["decision"], "blocked_manual_execution_audit")
        self.assertFalse(readiness["summary"]["small_capital_observation_candidate"])
        self.assertFalse(readiness["summary"]["production_manual_review_candidate"])
        self.assertEqual(readiness["summary"]["manual_execution_clean_receipts"], 4)
        self.assertEqual(readiness["summary"]["manual_execution_blocked_receipts"], 1)
        self.assertEqual(gate_by_id["manual_execution_quality"]["status"], "blocked")
        self.assertEqual(gate_by_id["manual_execution_quality"]["observed_count"], 4)
        self.assertEqual(gate_by_id["manual_execution_quality"]["missing_count"], 1)
        self.assertEqual(readiness["summary"]["next_target_id"], "beginner-post-close-journal-board")

    def test_daily_pack_exposes_real_money_transition_gate_without_auto_orders(self):
        pack = build_daily_trade_advisory_pack(
            [
                {
                    "rank": 1,
                    "case_id": "c1",
                    "factor_name": "momentum_quality_combo",
                    "market": "CN_ETF",
                    "sharpe": 1.35,
                    "annualized_return": 0.18,
                    "max_drawdown": -0.14,
                    "win_rate": 0.59,
                    "rank_ic": 0.045,
                    "trade_count": 96,
                },
                {
                    "rank": 2,
                    "case_id": "c2",
                    "factor_name": "low_vol_overlay",
                    "market": "CN_ETF",
                    "sharpe": 1.05,
                    "annualized_return": 0.14,
                    "max_drawdown": -0.11,
                    "win_rate": 0.57,
                    "rank_ic": 0.033,
                    "trade_count": 80,
                },
                {
                    "rank": 3,
                    "case_id": "c3",
                    "factor_name": "breadth_trend_state",
                    "market": "CN_ETF",
                    "sharpe": 0.98,
                    "annualized_return": 0.12,
                    "max_drawdown": -0.10,
                    "win_rate": 0.56,
                    "rank_ic": 0.028,
                    "trade_count": 72,
                },
            ],
            [
                _signal("c1", "momentum_quality_combo", {"510300": 0.2}),
                _signal("c2", "low_vol_overlay", {"588000": 0.2}),
                _signal("c3", "breadth_trend_state", {"159915": 0.2}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
            risk_profile_id="aggressive_30dd",
            evidence_snapshot={
                "walk_forward_oos_passed": True,
                "lookahead_bias_audit_passed": True,
                "multiple_testing_control_passed": True,
                "transaction_cost_capacity_passed": True,
                "matched_paper_receipts": 5,
                "post_close_journals": 5,
                "manual_execution_clean_receipts": 5,
                "manual_execution_blocked_receipts": 0,
                "paper_ready_observations": 20,
            },
        )

        gate = pack["daily_real_money_transition_gate"]

        self.assertEqual(gate["stage"], "phase_6_21_daily_real_money_transition_gate")
        self.assertEqual(gate["summary"]["decision"], "production_manual_review_candidate")
        self.assertEqual(gate["summary"]["capital_mode"], "production_manual_review_only")
        self.assertTrue(gate["summary"]["small_capital_observation_candidate"])
        self.assertTrue(gate["summary"]["production_manual_review_candidate"])
        self.assertFalse(gate["summary"]["real_money_allowed"])
        self.assertFalse(gate["summary"]["live_order_allowed"])
        self.assertFalse(gate["summary"]["broker_connection_allowed"])
        self.assertFalse(gate["summary"]["account_read_allowed"])
        self.assertFalse(gate["summary"]["order_placement_allowed"])
        self.assertFalse(gate["summary"]["auto_order_allowed"])
        self.assertEqual(pack["summary"]["real_money_transition_status"], "production_manual_review_candidate")
        row_by_id = {row["gate_id"]: row for row in gate["preflight_rows"]}
        self.assertEqual(row_by_id["factor_health"]["status"], "pass")
        self.assertEqual(row_by_id["paper_receipts"]["status"], "pass")
        self.assertEqual(row_by_id["post_close_journals"]["status"], "pass")
        self.assertEqual(row_by_id["manual_execution_quality"]["status"], "pass")
        self.assertEqual(row_by_id["manual_ticket_risk_budget"]["status"], "pass")
        self.assertEqual(row_by_id["research_only_safety_boundary"]["status"], "pass")
        self.assertIn("open_external_broker_manually", {row["step_id"] for row in gate["operator_script"]})
        self.assertIn("record_post_close_journal", {row["step_id"] for row in gate["operator_script"]})
        self.assertIn("direct_buy_top3", {row["action_id"] for row in gate["forbidden_actions"]})
        self.assertIn("skip_paper_and_journal", {row["action_id"] for row in gate["forbidden_actions"]})
        self.assertTrue(gate["manual_execution_preview"])
        self.assertIn("risk_budget", gate["manual_execution_preview"][0])
        self.assertIn("manual_skip_conditions", gate["manual_execution_preview"][0])
        self.assertTrue(all(not row["order_placement_allowed"] for row in gate["operator_script"]))

    def test_daily_pack_exposes_manual_trading_session_that_blocks_missing_paper_evidence(self):
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

        session = pack["daily_manual_trading_session"]

        self.assertEqual(session["stage"], "phase_6_24_daily_manual_trading_session")
        self.assertEqual(session["summary"]["session_status"], "blocked_same_parameter_paper_required")
        self.assertEqual(session["summary"]["traffic_light"], "red")
        self.assertFalse(session["summary"]["manual_broker_review_candidate"])
        self.assertFalse(session["summary"]["small_capital_observation_candidate"])
        self.assertFalse(session["summary"]["order_placement_allowed"])
        self.assertEqual(session["summary"]["matched_paper_receipts"], 0)
        self.assertIn("same_parameter_paper", {row["gate_id"] for row in session["blocking_gates"]})
        self.assertIn("pre_open_check", {row["phase_id"] for row in session["session_phases"]})
        self.assertIn("record_post_close_journal", {row["step_id"] for row in session["operator_checklist"]})
        self.assertTrue(all(not row["order_placement_allowed"] for row in session["operator_checklist"]))
        self.assertTrue(session["manual_ticket_preview"])

    def test_manual_trading_session_uses_profitability_evidence_without_enabling_orders(self):
        pack = build_daily_trade_advisory_pack(
            [
                {
                    "rank": 1,
                    "case_id": "c1",
                    "factor_name": "momentum_quality_combo",
                    "market": "CN_ETF",
                    "sharpe": 1.35,
                    "annualized_return": 0.18,
                    "max_drawdown": -0.14,
                    "win_rate": 0.59,
                    "rank_ic": 0.045,
                    "trade_count": 96,
                },
                {
                    "rank": 2,
                    "case_id": "c2",
                    "factor_name": "low_vol_overlay",
                    "market": "CN_ETF",
                    "sharpe": 1.05,
                    "annualized_return": 0.14,
                    "max_drawdown": -0.11,
                    "win_rate": 0.57,
                    "rank_ic": 0.033,
                    "trade_count": 80,
                },
                {
                    "rank": 3,
                    "case_id": "c3",
                    "factor_name": "breadth_trend_state",
                    "market": "CN_ETF",
                    "sharpe": 0.98,
                    "annualized_return": 0.12,
                    "max_drawdown": -0.10,
                    "win_rate": 0.56,
                    "rank_ic": 0.028,
                    "trade_count": 72,
                },
            ],
            [
                _signal("c1", "momentum_quality_combo", {"510300": 0.2}),
                _signal("c2", "low_vol_overlay", {"588000": 0.2}),
                _signal("c3", "breadth_trend_state", {"159915": 0.2}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
            risk_profile_id="aggressive_30dd",
            evidence_snapshot={
                "walk_forward_oos_passed": True,
                "lookahead_bias_audit_passed": True,
                "multiple_testing_control_passed": True,
                "transaction_cost_capacity_passed": True,
                "matched_paper_receipts": 5,
                "post_close_journals": 5,
                "manual_execution_clean_receipts": 5,
                "manual_execution_blocked_receipts": 0,
                "paper_ready_observations": 20,
            },
        )
        direct = build_daily_manual_trading_session(pack)

        self.assertEqual(direct, pack["daily_manual_trading_session"])
        self.assertEqual(direct["summary"]["session_status"], "production_manual_review_candidate")
        self.assertEqual(direct["summary"]["traffic_light"], "yellow")
        self.assertTrue(direct["summary"]["manual_broker_review_candidate"])
        self.assertTrue(direct["summary"]["small_capital_observation_candidate"])
        self.assertFalse(direct["summary"]["real_money_allowed"])
        self.assertFalse(direct["summary"]["broker_connection_allowed"])
        self.assertFalse(direct["summary"]["account_read_allowed"])
        self.assertFalse(direct["summary"]["order_placement_allowed"])
        self.assertEqual(direct["summary"]["matched_paper_receipts"], 5)
        self.assertEqual(direct["summary"]["manual_execution_clean_receipts"], 5)
        self.assertIn("open_external_broker_manually", {row["step_id"] for row in direct["operator_checklist"]})
        self.assertIn("direct_buy_top3", {row["action_id"] for row in direct["forbidden_actions"]})
        self.assertTrue(all(not row["order_placement_allowed"] for row in direct["manual_ticket_preview"]))

    def test_daily_pack_exposes_paper_allocation_playbook_for_top3_signals(self):
        pack = build_daily_trade_advisory_pack(
            [
                {"rank": 1, "case_id": "c1", "factor_name": "momentum_quality_combo", "market": "CN_ETF", "sharpe": 1.3},
                {"rank": 2, "case_id": "c2", "factor_name": "low_vol_overlay", "market": "CN_ETF", "sharpe": 1.1},
                {"rank": 3, "case_id": "c3", "factor_name": "breadth_trend_state", "market": "CN_ETF", "sharpe": 0.9},
            ],
            [
                _signal("c1", "momentum_quality_combo", {"510300": 0.20}, latest_price=4.0),
                _signal("c2", "low_vol_overlay", {"588000": 0.15}, latest_price=1.5),
                _signal("c3", "breadth_trend_state", {"159915": 0.10}, latest_price=2.0),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
            risk_profile_id="aggressive_30dd",
        )

        playbook = pack["daily_paper_allocation_playbook"]
        direct = build_daily_paper_allocation_playbook(pack)

        self.assertEqual(direct, playbook)
        self.assertEqual(playbook["stage"], "phase_6_25_daily_paper_allocation_playbook")
        self.assertEqual(pack["summary"]["paper_allocation_playbook_status"], "paper_rehearsal_required")
        self.assertEqual(playbook["summary"]["allocation_status"], "paper_rehearsal_required")
        self.assertEqual(playbook["summary"]["traffic_light"], "yellow")
        self.assertEqual(playbook["summary"]["portfolio_value"], 100000)
        self.assertEqual(playbook["summary"]["allocated_value"], 14550)
        self.assertEqual(playbook["summary"]["residual_cash_value"], 85450)
        self.assertEqual(playbook["summary"]["allocation_row_count"], 3)
        self.assertFalse(playbook["summary"]["broker_connection_allowed"])
        self.assertFalse(playbook["summary"]["account_read_allowed"])
        self.assertFalse(playbook["summary"]["order_placement_allowed"])
        self.assertIn("same_parameter_paper", {row["gate_id"] for row in playbook["promotion_gates"]})
        rows_by_asset = {row["asset_id"]: row for row in playbook["allocation_rows"]}
        self.assertEqual(rows_by_asset["510300"]["paper_budget_value"], 6400)
        self.assertAlmostEqual(rows_by_asset["510300"]["target_weight"], 0.0666666667)
        self.assertEqual(rows_by_asset["510300"]["paper_quantity"], 1600)
        self.assertEqual(rows_by_asset["588000"]["paper_quantity"], 3300)
        self.assertTrue(all(row["execution_mode"] == "paper_rehearsal_only" for row in playbook["allocation_rows"]))
        self.assertTrue(all(row["order_placement_allowed"] is False for row in playbook["allocation_rows"]))
        self.assertIn("run_same_parameter_paper", {row["step_id"] for row in playbook["operator_steps"]})
        self.assertIn("do_not_copy_to_broker", {row["action_id"] for row in playbook["forbidden_actions"]})

    def test_paper_allocation_playbook_marks_manual_review_candidate_after_evidence(self):
        pack = build_daily_trade_advisory_pack(
            [
                {"rank": 1, "case_id": "c1", "factor_name": "momentum_quality_combo", "market": "CN_ETF", "sharpe": 1.35},
                {"rank": 2, "case_id": "c2", "factor_name": "low_vol_overlay", "market": "CN_ETF", "sharpe": 1.05},
                {"rank": 3, "case_id": "c3", "factor_name": "breadth_trend_state", "market": "CN_ETF", "sharpe": 0.98},
            ],
            [
                _signal("c1", "momentum_quality_combo", {"510300": 0.2}),
                _signal("c2", "low_vol_overlay", {"588000": 0.2}),
                _signal("c3", "breadth_trend_state", {"159915": 0.2}),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
            risk_profile_id="aggressive_30dd",
            evidence_snapshot={
                "walk_forward_oos_passed": True,
                "lookahead_bias_audit_passed": True,
                "multiple_testing_control_passed": True,
                "transaction_cost_capacity_passed": True,
                "matched_paper_receipts": 5,
                "post_close_journals": 5,
                "manual_execution_clean_receipts": 5,
                "manual_execution_blocked_receipts": 0,
                "paper_ready_observations": 20,
            },
        )

        playbook = pack["daily_paper_allocation_playbook"]

        self.assertEqual(playbook["summary"]["allocation_status"], "manual_review_candidate")
        self.assertEqual(playbook["summary"]["traffic_light"], "yellow")
        self.assertTrue(playbook["summary"]["manual_broker_review_candidate"])
        self.assertFalse(playbook["summary"]["order_placement_allowed"])
        self.assertFalse(playbook["summary"]["real_money_allowed"])
        self.assertTrue(all(row["execution_mode"] == "manual_review_candidate_not_order" for row in playbook["allocation_rows"]))
        self.assertTrue(all(row["order_placement_allowed"] is False for row in playbook["allocation_rows"]))
        self.assertIn("open_external_broker_manually_if_human_chooses", {row["step_id"] for row in playbook["operator_steps"]})

    def test_paper_allocation_playbook_can_rehearse_targets_without_current_positions(self):
        pack = _build_daily_trade_advisory_pack(
            [
                {"rank": 1, "case_id": "c1", "factor_name": "momentum_quality_combo", "market": "CN_ETF", "sharpe": 1.3},
                {"rank": 2, "case_id": "c2", "factor_name": "low_vol_overlay", "market": "CN_ETF", "sharpe": 1.1},
            ],
            [
                _signal("c1", "momentum_quality_combo", {"510300": 0.20}, latest_price=4.0),
                _signal("c2", "low_vol_overlay", {"588000": 0.10}, latest_price=1.5),
            ],
            run_date="2026-06-29",
            portfolio_value=100000,
            risk_profile_id="balanced_20dd",
        )

        playbook = pack["daily_paper_allocation_playbook"]

        self.assertEqual(pack["summary"]["current_position_status"], "not_provided")
        self.assertEqual(pack["summary"]["manual_ticket_count"], 0)
        self.assertEqual(playbook["summary"]["allocation_status"], "paper_rehearsal_required")
        self.assertEqual(playbook["summary"]["allocation_row_count"], 2)
        self.assertGreater(playbook["summary"]["allocated_value"], 0)
        self.assertTrue(all(row["source_kind"] == "combined_target" for row in playbook["allocation_rows"]))
        self.assertTrue(all(row["execution_mode"] == "paper_rehearsal_only" for row in playbook["allocation_rows"]))
        self.assertTrue(all(row["order_placement_allowed"] is False for row in playbook["allocation_rows"]))
        self.assertIn("manual_ticket_pack", {row["gate_id"] for row in playbook["promotion_gates"]})
        self.assertIn("run_same_parameter_paper", {row["step_id"] for row in playbook["operator_steps"]})

    def test_daily_pack_exposes_factor_health_monitor_for_top3_retirement_gate(self):
        pack = build_daily_trade_advisory_pack(
            [
                {
                    "rank": 1,
                    "case_id": "healthy_oos",
                    "factor_name": "momentum_quality_combo",
                    "market": "CN_ETF",
                    "sharpe": 1.35,
                    "annualized_return": 0.18,
                    "max_drawdown": -0.14,
                    "win_rate": 0.59,
                    "rank_ic": 0.045,
                    "trade_count": 96,
                },
                {
                    "rank": 2,
                    "case_id": "bad_decay",
                    "factor_name": "turnover_chase_combo",
                    "market": "CN_ETF",
                    "sharpe": -0.2,
                    "annualized_return": 0.05,
                    "max_drawdown": -0.36,
                    "win_rate": 0.42,
                    "rank_ic": -0.03,
                    "trade_count": 12,
                },
                {
                    "rank": 3,
                    "case_id": "watch_thin",
                    "factor_name": "low_vol_overlay",
                    "market": "CN_ETF",
                    "sharpe": 0.72,
                    "annualized_return": 0.09,
                    "max_drawdown": -0.18,
                    "win_rate": 0.53,
                    "rank_ic": 0.011,
                    "trade_count": 40,
                },
            ],
            [
                _signal("healthy_oos", "momentum_quality_combo", {"510300": 0.4}),
                _signal("bad_decay", "turnover_chase_combo", {"588000": 0.3}),
                _signal("watch_thin", "low_vol_overlay", {"159915": 0.2}),
            ],
            run_date="2026-06-30",
            portfolio_value=100000,
            evidence_snapshot={
                "walk_forward_oos_passed": True,
                "lookahead_bias_audit_passed": True,
                "multiple_testing_control_passed": True,
                "transaction_cost_capacity_passed": True,
            },
        )

        monitor = pack["daily_factor_health_monitor"]

        self.assertEqual(monitor["stage"], "phase_6_20_daily_factor_health_monitor")
        self.assertEqual(pack["summary"]["factor_health_status"], "retire_or_reduce_weight_required")
        self.assertEqual(monitor["summary"]["selected_factor_count"], 3)
        self.assertEqual(monitor["summary"]["healthy_count"], 1)
        self.assertEqual(monitor["summary"]["watch_count"], 1)
        self.assertEqual(monitor["summary"]["retire_candidate_count"], 1)
        self.assertFalse(monitor["summary"]["top3_auto_buy_allowed"])
        self.assertFalse(monitor["summary"]["order_placement_allowed"])
        self.assertTrue(monitor["summary"]["retirement_required_before_live"])
        rows = {row["factor_name"]: row for row in monitor["factor_rows"]}
        self.assertEqual(rows["momentum_quality_combo"]["health_status"], "healthy_for_paper_observation")
        self.assertEqual(rows["turnover_chase_combo"]["health_status"], "retire_candidate")
        self.assertIn("high_drawdown", rows["turnover_chase_combo"]["reason_codes"])
        self.assertIn("negative_rank_ic", rows["turnover_chase_combo"]["reason_codes"])
        self.assertEqual(rows["low_vol_overlay"]["health_status"], "watch")
        self.assertTrue(all(row["order_placement_allowed"] is False for row in monitor["factor_rows"]))
        self.assertIn("retire_bad_factor", {item["action_id"] for item in monitor["recommended_actions"]})

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
