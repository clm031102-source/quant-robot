import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_daily_ops import run_daily_ops


class DailyOpsCliTests(unittest.TestCase):
    def test_run_daily_ops_writes_pack_from_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promotion = root / "promotion_review_packet.json"
            readiness = root / "pre_api_readiness_board.json"
            signal = root / "signal_snapshot.json"
            simulation = root / "paper_simulation.json"
            output_dir = root / "daily_ops"
            promotion.write_text(
                json.dumps(
                    {
                        "selected_candidate": {
                            "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                            "market": "CN_ETF",
                            "factor_name": "liquidity_10",
                            "rank": 1,
                        }
                    }
                ),
                encoding="utf-8",
            )
            readiness.write_text(
                json.dumps(
                    {
                        "readiness_items": [{"track_id": "manual_review_gate", "status": "block"}],
                        "blocker_register": [{"blocker_id": "manual_live_review_not_enabled", "track_id": "manual_review_gate"}],
                    }
                ),
                encoding="utf-8",
            )
            signal.write_text(
                json.dumps(
                    {
                        "as_of_date": "2026-06-12",
                        "signal_date": "2026-06-12",
                        "targets": [{"asset_id": "asset_a", "target_weight": 1.0}],
                        "rebalance_plan": [{"asset_id": "asset_a", "market": "CN_ETF", "estimated_quantity_delta": 100.0, "delta_value": 1000.0}],
                    }
                ),
                encoding="utf-8",
            )
            simulation.write_text(
                json.dumps(
                    {
                        "metrics": {"total_return": 0.1, "max_equity_drawdown": -0.05},
                        "fills": [],
                        "guard_events": [],
                        "execution_events": [],
                    }
                ),
                encoding="utf-8",
            )

            pack = run_daily_ops(
                promotion_review=promotion,
                readiness_board=readiness,
                signal_snapshot=signal,
                paper_simulation=simulation,
                output_dir=output_dir,
                run_date="2026-06-13",
            )

            self.assertEqual(pack["stage"], "phase_5_0_daily_ops")
            self.assertEqual(pack["decision"]["status"], "paper_ready")
            self.assertTrue((output_dir / "daily_ops_pack.json").exists())
            self.assertTrue((output_dir / "daily_ops_pack.md").exists())
            self.assertTrue((output_dir / "daily_ops_tickets.csv").exists())
            self.assertTrue((output_dir / "daily_ops_summary.csv").exists())
            payload = json.loads((output_dir / "daily_ops_pack.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["decision"]["live_boundary_allowed"])

    def test_run_daily_ops_applies_configured_drawdown_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promotion = root / "promotion_review_packet.json"
            readiness = root / "pre_api_readiness_board.json"
            signal = root / "signal_snapshot.json"
            simulation = root / "paper_simulation.json"
            output_dir = root / "daily_ops"
            promotion.write_text(
                json.dumps({"selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "factor_name": "liquidity_10"}}),
                encoding="utf-8",
            )
            readiness.write_text(
                json.dumps({"blocker_register": [{"blocker_id": "manual_live_review_not_enabled", "track_id": "manual_review_gate"}]}),
                encoding="utf-8",
            )
            signal.write_text(
                json.dumps(
                    {
                        "targets": [{"asset_id": "asset_a", "target_weight": 1.0}],
                        "rebalance_plan": [{"asset_id": "asset_a", "market": "CN_ETF", "estimated_quantity_delta": 100.0}],
                    }
                ),
                encoding="utf-8",
            )
            simulation.write_text(
                json.dumps({"metrics": {"max_equity_drawdown": -0.05}, "fills": [], "guard_events": [], "execution_events": []}),
                encoding="utf-8",
            )

            pack = run_daily_ops(
                promotion_review=promotion,
                readiness_board=readiness,
                signal_snapshot=signal,
                paper_simulation=simulation,
                output_dir=output_dir,
                run_date="2026-06-13",
                max_drawdown_limit=0.04,
            )

            self.assertEqual(pack["decision"]["status"], "blocked")
            self.assertEqual(pack["decision"]["non_manual_blocking_reasons"], ["risk_max_drawdown_breach"])
            self.assertEqual(pack["risk_policy"]["max_drawdown_limit"], -0.04)


if __name__ == "__main__":
    unittest.main()
