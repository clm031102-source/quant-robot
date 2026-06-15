import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_small_capital_review_gate import run_small_capital_review_gate


class SmallCapitalReviewGateCliTests(unittest.TestCase):
    def test_run_small_capital_review_gate_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            review_path = root / "promotion_review_packet.json"
            review_path.write_text(
                json.dumps(
                    {
                        "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
                        "manual_review_gate": {"allowed": True, "reasons": []},
                        "selected_candidate": {
                            "case_id": "case_a",
                            "market": "CN",
                            "factor_name": "pe_ttm_rank",
                            "promotion_status": "manual_live_review",
                        },
                    }
                ),
                encoding="utf-8",
            )
            rehearsal_path = root / "manual_review_rehearsal.json"
            rehearsal_path.write_text(
                json.dumps(
                    {
                        "gate_status": "ready_for_manual_review_rehearsal",
                        "blockers": [],
                        "dry_run": {
                            "would_cross_live_boundary": False,
                            "broker_connection": "disabled",
                            "account_reads": "disabled",
                            "order_placement": "disabled",
                            "live_trading": "disabled",
                            "executable": False,
                        },
                    }
                ),
                encoding="utf-8",
            )
            paper_path = root / "paper_observation_pack.json"
            paper_path.write_text(
                json.dumps(
                    {
                        "summary": {
                            "observed_candidates": 1,
                            "completed_candidates": 1,
                            "total_guard_events": 0,
                            "total_execution_events": 0,
                        },
                        "candidates": [
                            {
                                "case_id": "case_a",
                                "status": "completed",
                                "observation_status": "observed",
                                "fills": 36,
                                "max_equity_drawdown": -0.05,
                                "observation_window": {"start_date": "2026-01-01", "end_date": "2026-02-10"},
                                "guard_summary": {"guard_events": 0},
                                "execution_summary": {"execution_events": 0},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            board_path = root / "pre_api_readiness_board.json"
            board_path.write_text(
                json.dumps(
                    {
                        "overall_status": "ready_for_api_boundary_planning",
                        "blocker_register": [],
                        "boundary": {
                            "would_cross_live_boundary": False,
                            "broker_connection": "disabled",
                            "account_reads": "disabled",
                            "order_placement": "disabled",
                            "live_trading": "disabled",
                        },
                    }
                ),
                encoding="utf-8",
            )
            sufficiency_path = root / "observation_sufficiency_pack.json"
            sufficiency_path.write_text(
                json.dumps({"status": "sufficient", "decision": {"observation_sufficiency_cleared": True, "blockers": []}}),
                encoding="utf-8",
            )
            regime_path = root / "market_regime_coverage_pack.json"
            regime_path.write_text(
                json.dumps(
                    {
                        "status": "sufficient",
                        "summary": {"covered_regimes": 3, "required_regimes": 2, "regimes": ["bull", "bear", "sideways"]},
                        "decision": {"market_regime_coverage_cleared": True, "blockers": []},
                    }
                ),
                encoding="utf-8",
            )
            policy_path = root / "small_capital_policy.json"
            policy_path.write_text(
                json.dumps({"max_initial_capital": 8000, "max_single_order_notional": 1200, "max_daily_loss": 160}),
                encoding="utf-8",
            )
            output_dir = root / "small_capital_review_gate"

            gate = run_small_capital_review_gate(
                review_packet=review_path,
                manual_rehearsal=rehearsal_path,
                paper_observation=paper_path,
                pre_api_readiness=board_path,
                observation_sufficiency=sufficiency_path,
                market_regime_coverage=regime_path,
                policy=policy_path,
                output_dir=output_dir,
                reviewer="operator",
            )

            self.assertEqual(gate["stage"], "phase_6_1_small_capital_review_gate")
            self.assertEqual(gate["status"], "ready_for_manual_small_capital_review")
            self.assertTrue((output_dir / "small_capital_review_gate.json").exists())
            self.assertTrue((output_dir / "small_capital_review_gate.md").exists())
            self.assertTrue((output_dir / "small_capital_review_requirements.csv").exists())
            payload = json.loads((output_dir / "small_capital_review_gate.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["decision"]["live_boundary_allowed"])
            self.assertFalse(payload["manual_approval_packet"]["executable"])
            self.assertEqual(payload["risk_limits"]["max_initial_capital"], 8000)


if __name__ == "__main__":
    unittest.main()
