from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from quant_robot.ops.simulation_paper_ops_package import (
    build_simulation_paper_ops_package,
    write_simulation_paper_ops_package,
)


class SimulationPaperOpsPackageTest(unittest.TestCase):
    def test_package_keeps_diagnostic_high_return_lane_visible(self) -> None:
        handoff = {
            "summary": {
                "default_candidate_id": "default_lane",
                "primary_high_return_candidate_id": "range_q20_lane",
            },
            "candidates": [
                {
                    "candidate_id": "default_lane",
                    "role": "default_10bps",
                    "handoff_status": "ready_for_paper_simulation",
                    "computed_annualized_return": 0.066,
                    "computed_total_return": 2.18,
                    "computed_overlap_sharpe": 0.49,
                    "computed_max_drawdown": -0.26,
                    "computed_win_rate": 0.41,
                    "oos_strict_pass_rate": 0.90,
                    "cost_rate": 0.001,
                    "source_path": "default/events.csv",
                },
                {
                    "candidate_id": "range_q20_lane",
                    "role": "diagnostic",
                    "handoff_status": "ready_for_paper_simulation",
                    "computed_annualized_return": 0.077,
                    "computed_total_return": 2.80,
                    "computed_overlap_sharpe": 0.51,
                    "computed_max_drawdown": -0.293,
                    "computed_win_rate": 0.42,
                    "oos_strict_pass_rate": 0.90,
                    "cost_rate": 0.001,
                    "source_path": "range/events.csv",
                },
            ],
        }
        config = {
            "final_holdout_2026": {"status": "sealed"},
            "round457_range_q20_paper_readiness_hardening": {
                "cost_stress": {
                    "cost20_vt8_max_drawdown": -0.31,
                    "cost30_vt7_max_drawdown": -0.32,
                },
                "capacity_stress": {
                    "safe_through_aum_multiplier": 20,
                    "unsafe_from_aum_multiplier": 50,
                },
                "extreme_trade_profile": {
                    "extreme_contribution_share": 0.35,
                    "extreme_trade_count": 123,
                },
            },
        }
        blend = {
            "summary": {"best_case_id": "range_q20_100", "blocked_case_count": 30},
            "thresholds": {"duplicate_correlation": 0.98},
        }

        package = build_simulation_paper_ops_package(
            config=config,
            paper_handoff=handoff,
            blend_audit=blend,
            max_user_drawdown=-0.30,
        )

        self.assertEqual(package["status"], "paper_ops_package_ready")
        self.assertFalse(package["live_boundary_allowed"])
        self.assertFalse(package["promotion_policy"]["promotion_allowed"])
        self.assertEqual(package["summary"]["default_candidate_id"], "default_lane")
        self.assertEqual(package["summary"]["primary_high_return_candidate_id"], "range_q20_lane")
        lanes = {row["candidate_id"]: row for row in package["paper_lanes"]}
        self.assertEqual(lanes["range_q20_lane"]["lane_role"], "primary_high_return_observation")
        self.assertIn("high_return_lane_is_diagnostic_role", package["warnings"])
        self.assertIn("high_return_cost_stress_drawdown_below_user_limit", package["warnings"])
        self.assertIn("high_return_tail_contribution_concentrated", package["warnings"])
        self.assertIn("shortlist_streams_highly_correlated", package["warnings"])
        self.assertEqual(package["risk_controls"]["capacity_safe_through_aum_multiplier"], 20)

    def test_package_prefers_candidate_cost_stress_over_stale_round457_cost_warning(self) -> None:
        handoff = {
            "summary": {
                "default_candidate_id": "default_lane",
                "primary_high_return_candidate_id": "range_q20_ps_gt10_lane",
            },
            "candidates": [
                {
                    "candidate_id": "default_lane",
                    "role": "default_10bps",
                    "handoff_status": "ready_for_paper_simulation",
                    "computed_annualized_return": 0.066,
                    "computed_max_drawdown": -0.26,
                },
                {
                    "candidate_id": "range_q20_ps_gt10_lane",
                    "role": "diagnostic",
                    "handoff_status": "ready_for_paper_simulation",
                    "computed_annualized_return": 0.078,
                    "computed_max_drawdown": -0.254,
                    "csi500_beta_hedged_annualized_return": 0.086,
                },
            ],
        }
        config = {
            "paper_simulation_handoff_candidates": [
                {
                    "id": "range_q20_ps_gt10_lane",
                    "evidence": {
                        "cost20_max_drawdown": -0.268,
                        "cost30_max_drawdown": -0.281,
                    },
                }
            ],
            "round457_range_q20_paper_readiness_hardening": {
                "cost_stress": {
                    "cost20_vt8_max_drawdown": -0.31,
                    "cost30_vt7_max_drawdown": -0.32,
                }
            },
        }

        package = build_simulation_paper_ops_package(
            config=config,
            paper_handoff=handoff,
            max_user_drawdown=-0.30,
        )

        self.assertNotIn("high_return_cost_stress_drawdown_below_user_limit", package["warnings"])
        self.assertEqual(package["risk_controls"]["worst_cost_stress_drawdown"], -0.281)

    def test_package_blocks_when_primary_high_return_is_not_ready(self) -> None:
        handoff = {
            "summary": {
                "default_candidate_id": "default_lane",
                "primary_high_return_candidate_id": "blocked_lane",
            },
            "candidates": [
                {
                    "candidate_id": "default_lane",
                    "role": "default_10bps",
                    "handoff_status": "ready_for_paper_simulation",
                },
                {
                    "candidate_id": "blocked_lane",
                    "role": "diagnostic",
                    "handoff_status": "blocked",
                    "blockers": ["not_paper_ready"],
                },
            ],
        }

        package = build_simulation_paper_ops_package(
            config={},
            paper_handoff=handoff,
            max_user_drawdown=-0.30,
        )

        self.assertEqual(package["status"], "paper_ops_package_blocked")
        self.assertIn("primary_high_return_candidate_not_ready", package["blockers"])
        self.assertFalse(package["decision"]["paper_observation_allowed"])

    def test_writer_exports_package_artifacts(self) -> None:
        package = build_simulation_paper_ops_package(
            config={},
            paper_handoff={
                "summary": {"default_candidate_id": "lane", "primary_high_return_candidate_id": "lane"},
                "candidates": [
                    {
                        "candidate_id": "lane",
                        "role": "default_10bps",
                        "handoff_status": "ready_for_paper_simulation",
                    }
                ],
            },
        )

        with TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_simulation_paper_ops_package(output, package)

            self.assertTrue((output / "simulation_paper_ops_package.json").exists())
            self.assertTrue((output / "simulation_paper_ops_package.md").exists())
            self.assertTrue((output / "simulation_paper_ops_lanes.csv").exists())
            saved = json.loads((output / "simulation_paper_ops_package.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["stage"], "simulation_paper_ops_package")


if __name__ == "__main__":
    unittest.main()
