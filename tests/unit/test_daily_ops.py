import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.daily_ops import build_daily_ops_pack, write_daily_ops_pack


class DailyOpsTests(unittest.TestCase):
    def test_pack_builds_paper_ready_decision_from_current_artifacts(self):
        promotion = {
            "selected_candidate": {
                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                "market": "CN_ETF",
                "factor_name": "liquidity_10",
                "rank": 1,
            }
        }
        readiness = {
            "overall_status": "blocked",
            "readiness_items": [
                {"track_id": "data_quality", "status": "pass", "evidence": "gap_resolution=non_blocking"},
                {"track_id": "provider_readiness", "status": "pass", "evidence": "ready_market_providers=2/2"},
                {"track_id": "manual_review_gate", "status": "block", "evidence": "manual_live_review_not_enabled"},
                {"track_id": "research_boundary", "status": "pass", "evidence": "order_placement=disabled"},
            ],
            "blocker_register": [{"blocker_id": "manual_live_review_not_enabled", "track_id": "manual_review_gate"}],
        }
        signal = {
            "as_of_date": "2026-06-12",
            "signal_date": "2026-06-12",
            "targets": [{"asset_id": "CN_ETF_XSHG_510300", "target_weight": 1.0}],
            "rebalance_plan": [
                {
                    "asset_id": "CN_ETF_XSHG_510300",
                    "market": "CN_ETF",
                    "target_weight": 1.0,
                    "estimated_quantity_delta": 100.0,
                    "delta_value": 1000.0,
                }
            ],
        }
        simulation = {
            "metrics": {"total_return": 0.12, "max_equity_drawdown": -0.08, "ending_equity": 112000.0},
            "fills": [{"asset_id": "CN_ETF_XSHG_510300", "side": "buy"}],
            "guard_events": [],
            "execution_events": [],
        }

        pack = build_daily_ops_pack(promotion, readiness, signal, simulation, run_date="2026-06-13")

        self.assertEqual(pack["stage"], "phase_5_0_daily_ops")
        self.assertEqual(pack["run_date"], "2026-06-13")
        self.assertEqual(pack["candidate"]["case_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")
        self.assertEqual(pack["decision"]["status"], "paper_ready")
        self.assertFalse(pack["decision"]["live_boundary_allowed"])
        self.assertEqual(pack["decision"]["blocking_reasons"], ["manual_live_review_not_enabled"])
        self.assertEqual(pack["risk"]["max_equity_drawdown"], -0.08)
        self.assertEqual(pack["advisory_tickets"][0]["asset_id"], "CN_ETF_XSHG_510300")
        self.assertEqual(pack["advisory_tickets"][0]["ticket_type"], "advisory_rebalance")
        self.assertIn("No broker", pack["safety"])

    def test_non_manual_blockers_keep_daily_ops_blocked(self):
        pack = build_daily_ops_pack(
            {"selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "factor_name": "liquidity_10"}},
            {
                "readiness_items": [{"track_id": "provider_readiness", "status": "block", "evidence": "provider missing"}],
                "blocker_register": [{"blocker_id": "provider_readiness_not_ready", "track_id": "provider_readiness"}],
            },
            {"targets": [], "rebalance_plan": []},
            {"metrics": {}, "fills": [], "guard_events": [], "execution_events": []},
            run_date="2026-06-13",
        )

        self.assertEqual(pack["decision"]["status"], "blocked")
        self.assertEqual(pack["decision"]["blocking_reasons"], ["provider_readiness_not_ready"])
        self.assertEqual(pack["advisory_tickets"], [])

    def test_max_drawdown_breach_blocks_daily_ops_tickets(self):
        pack = build_daily_ops_pack(
            {"selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "factor_name": "liquidity_10"}},
            {"blocker_register": [{"blocker_id": "manual_live_review_not_enabled", "track_id": "manual_review_gate"}]},
            {
                "targets": [{"asset_id": "asset_a", "target_weight": 1.0}],
                "rebalance_plan": [{"asset_id": "asset_a", "market": "CN_ETF", "estimated_quantity_delta": 100.0}],
            },
            {"metrics": {"max_equity_drawdown": -0.25}, "fills": [], "guard_events": [], "execution_events": []},
            run_date="2026-06-13",
        )

        self.assertEqual(pack["decision"]["status"], "blocked")
        self.assertIn("risk_max_drawdown_breach", pack["decision"]["blocking_reasons"])
        self.assertEqual(pack["decision"]["non_manual_blocking_reasons"], ["risk_max_drawdown_breach"])
        self.assertFalse(pack["decision"]["paper_trading_allowed"])
        self.assertEqual(pack["advisory_tickets"], [])
        self.assertEqual(pack["risk_policy"]["max_drawdown_limit"], -0.2)

    def test_write_daily_ops_pack_outputs_json_markdown_and_csvs(self):
        pack = build_daily_ops_pack(
            {"selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "factor_name": "liquidity_10"}},
            {"readiness_items": [], "blocker_register": []},
            {
                "as_of_date": "2026-06-12",
                "targets": [],
                "rebalance_plan": [{"asset_id": "asset_a", "market": "CN_ETF", "estimated_quantity_delta": 0.0}],
            },
            {"metrics": {"total_return": 0.0}, "fills": [], "guard_events": [], "execution_events": []},
            run_date="2026-06-13",
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_daily_ops_pack(output_dir, pack)

            self.assertTrue((output_dir / "daily_ops_pack.json").exists())
            self.assertTrue((output_dir / "daily_ops_pack.md").exists())
            self.assertTrue((output_dir / "daily_ops_tickets.csv").exists())
            self.assertTrue((output_dir / "daily_ops_summary.csv").exists())
            self.assertIn("max_drawdown_limit", (output_dir / "daily_ops_summary.csv").read_text(encoding="utf-8"))

    def test_blocked_daily_ops_ticket_csv_keeps_headers(self):
        pack = build_daily_ops_pack(
            {"selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "factor_name": "liquidity_10"}},
            {"blocker_register": [{"blocker_id": "manual_live_review_not_enabled"}]},
            {"targets": [], "rebalance_plan": [{"asset_id": "asset_a", "market": "CN_ETF", "estimated_quantity_delta": 100.0}]},
            {"metrics": {"max_equity_drawdown": -0.5}, "fills": [], "guard_events": [], "execution_events": []},
            run_date="2026-06-13",
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_daily_ops_pack(output_dir, pack)

            ticket_csv = (output_dir / "daily_ops_tickets.csv").read_text(encoding="utf-8")
            self.assertIn("ticket_id", ticket_csv.splitlines()[0])
            self.assertIn("live_order_allowed", ticket_csv.splitlines()[0])


if __name__ == "__main__":
    unittest.main()
