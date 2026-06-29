import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.daily_trade_advisory import (
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


def _signal(
    case_id: str,
    factor_name: str,
    weights: dict[str, float],
    latest_price: float = 1.0,
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
                "signal_date": "2026-06-29",
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
        "as_of_date": "2026-06-29",
        "signal_date": "2026-06-29",
        "targets": targets,
        "rebalance_plan": rebalance,
    }


if __name__ == "__main__":
    unittest.main()
