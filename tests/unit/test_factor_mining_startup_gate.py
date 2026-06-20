import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from quant_robot.ops.factor_mining_startup import build_factor_mining_startup_gate, validate_cleared_startup_gate_packet


class FactorMiningStartupGateTests(unittest.TestCase):
    def test_blocks_factor_mining_until_required_items_are_confirmed(self) -> None:
        config = {
            "scope_id": "cn_stock_factor_mining",
            "market": "CN",
            "asset_type": "stock",
            "allowed_machines": ["office_desktop"],
            "allowed_tasks": ["factor_batch", "factor_validation"],
            "recommended_branch_prefix": "codex/factor-batch-cn-stock-",
            "forbidden_markets": ["CN_ETF", "HK", "US", "CRYPTO"],
            "required_confirmations": [
                "machine_confirmed",
                "task_confirmed",
                "branch_confirmed",
                "push_policy_confirmed",
                "cn_stock_scope_confirmed",
                "etf_scope_rejected",
                "candidate_plan_pre_registered",
                "capacity_cost_gate_confirmed",
                "failed_direction_rotation_confirmed",
            ],
        }

        packet = build_factor_mining_startup_gate(
            config,
            request={
                "machine": "office_desktop",
                "task": "factor_batch",
                "branch": "codex/factor-batch-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                },
            },
            current_branch="codex/factor-batch-cn-stock-20260617",
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertFalse(packet["decision"]["startup_gate_cleared"])
        self.assertEqual(
            packet["decision"]["blockers"],
            [
                "missing_confirmation:branch_confirmed",
                "missing_confirmation:push_policy_confirmed",
                "missing_confirmation:cn_stock_scope_confirmed",
                "missing_confirmation:etf_scope_rejected",
                "missing_confirmation:candidate_plan_pre_registered",
                "missing_confirmation:capacity_cost_gate_confirmed",
                "missing_confirmation:failed_direction_rotation_confirmed",
            ],
        )
        self.assertIn("Confirm CN stock scope", packet["confirmation_questions"][0])

    def test_clears_cn_stock_factor_mining_start_when_scope_branch_and_confirmations_match(self) -> None:
        config = {
            "scope_id": "cn_stock_factor_mining",
            "market": "CN",
            "asset_type": "stock",
            "allowed_machines": ["office_desktop"],
            "allowed_tasks": ["factor_batch", "factor_validation"],
            "recommended_branch_prefix": "codex/factor-batch-cn-stock-",
            "forbidden_markets": ["CN_ETF", "HK", "US", "CRYPTO"],
            "required_confirmations": [
                "machine_confirmed",
                "task_confirmed",
                "branch_confirmed",
                "push_policy_confirmed",
                "cn_stock_scope_confirmed",
                "etf_scope_rejected",
            ],
            "validation_windows": {
                "discovery": {"start": "2023-07-03", "end": "2024-12-31"},
                "validation": {"start": "2025-01-01", "end": "2025-12-31"},
                "final_holdout": {"start": "2026-01-01", "end": "2026-06-15"},
            },
            "research_direction": {
                "objective": "cn_stock_cross_sectional_alpha",
                "mandate": "Mine tradable CN stock alpha factors, not ETF rotation signals.",
                "allowed_factor_families": ["price_volume", "daily_basic", "moneyflow", "composite"],
                "forbidden_directions": ["cn_etf_rotation", "single_family_lockin", "oos_tuning"],
                "stage_policy": {
                    "discovery": "Design and filter candidates only.",
                    "validation": "Run OOS only after discovery evidence clears.",
                    "final_holdout": "Read once; never tune after reading.",
                },
                "factor_family_rotation": {
                    "max_failed_batches_before_rotation": 1,
                    "max_single_family_share": 0.5,
                    "record_rejected_families": True,
                },
            },
        }

        packet = build_factor_mining_startup_gate(
            config,
            request={
                "machine": "office_desktop",
                "task": "factor_batch",
                "branch": "codex/factor-batch-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
                "commits_allowed": False,
                "pushes_allowed": False,
                "confirmations": {name: True for name in config["required_confirmations"]},
            },
            current_branch="codex/factor-batch-cn-stock-20260617",
        )

        self.assertEqual(packet["status"], "cleared")
        self.assertTrue(packet["decision"]["startup_gate_cleared"])
        self.assertEqual(packet["decision"]["blockers"], [])
        self.assertEqual(packet["summary"]["market"], "CN")
        self.assertEqual(packet["summary"]["asset_type"], "stock")
        self.assertEqual(packet["summary"]["excluded_markets"], ["CN_ETF", "HK", "US", "CRYPTO"])
        self.assertFalse(packet["summary"]["pushes_allowed"])
        self.assertIn("final_holdout", packet["validation_windows"])
        self.assertEqual(packet["research_direction"]["objective"], "cn_stock_cross_sectional_alpha")
        self.assertIn("moneyflow", packet["research_direction"]["allowed_factor_families"])
        self.assertEqual(packet["research_direction"]["factor_family_rotation"]["max_failed_batches_before_rotation"], 1)
        self.assertEqual(
            packet["repeatable_mining_protocol"]["next_direction"],
            "factor_validation_required_for_daily_champion_oos_candidates",
        )
        self.assertIn(
            "overlap_aware_return_statistics",
            packet["repeatable_mining_protocol"]["required_experiment_design"],
        )
        self.assertIn(
            "factor_validation_branch_confirmed",
            packet["repeatable_mining_protocol"]["confirm_before_each_run"],
        )
        self.assertIn(
            "batch12_validation_handoff_read",
            packet["repeatable_mining_protocol"]["confirm_before_each_run"],
        )
        self.assertTrue(
            any("Do not tune parameters after reading final_holdout" in item for item in packet["pre_run_checklist"])
        )
        self.assertTrue(
            any("overlap-aware" in question.lower() for question in packet["confirmation_questions"])
        )

    def test_build_packet_carries_repeatable_protocol_from_audit_plan(self) -> None:
        config = {
            "scope_id": "cn_stock_factor_mining",
            "market": "CN",
            "asset_type": "stock",
            "allowed_machines": ["office_desktop"],
            "allowed_tasks": ["factor_batch"],
            "recommended_branch_prefix": "codex/factor-batch-cn-stock-",
            "required_confirmations": [
                "machine_confirmed",
                "task_confirmed",
                "branch_confirmed",
                "push_policy_confirmed",
                "cn_stock_scope_confirmed",
                "etf_scope_rejected",
                "audit_optimization_plan_confirmed",
                "next_direction_confirmed",
                "portfolio_construction_gate_confirmed",
            ],
            "research_direction": {
                "objective": "cn_stock_cross_sectional_alpha",
                "allowed_factor_families": ["price_volume", "daily_basic", "moneyflow", "composite"],
                "stage_policy": {
                    "discovery": "Design and filter candidates only.",
                    "validation": "Run OOS only after discovery evidence clears.",
                    "final_holdout": "Read once; never tune after reading.",
                },
                "factor_family_rotation": {
                    "max_failed_batches_before_rotation": 1,
                    "max_single_family_share": 0.5,
                    "record_rejected_families": True,
                },
                "repeatable_mining_protocol": {
                    "source_audit": "data/reports/cn_stock_factor_mining_20260617_batch_audit.md",
                    "next_direction": "two_stage_portfolio_construction_and_holding_sensitivity",
                    "recently_rejected_directions": ["single_factor_top50_daily_long_only"],
                    "required_experiment_design": [
                        "rank_band_vs_topn_comparison",
                        "holding_period_and_rebalance_sensitivity",
                    ],
                    "confirm_before_each_run": [
                        "previous_audit_read",
                        "next_direction_pre_registered",
                        "oos_holdout_not_touched",
                    ],
                },
            },
        }

        packet = build_factor_mining_startup_gate(
            config,
            request={
                "machine": "office_desktop",
                "task": "factor_batch",
                "branch": "codex/factor-batch-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {name: True for name in config["required_confirmations"]},
            },
            current_branch="codex/factor-batch-cn-stock-20260617",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertEqual(protocol["next_direction"], "two_stage_portfolio_construction_and_holding_sensitivity")
        self.assertIn("single_factor_top50_daily_long_only", protocol["recently_rejected_directions"])
        self.assertIn("holding_period_and_rebalance_sensitivity", protocol["required_experiment_design"])
        self.assertIn("previous_audit_read", protocol["confirm_before_each_run"])
        self.assertTrue(
            any("audit optimization plan" in question.lower() for question in packet["confirmation_questions"])
        )

    def test_allows_task_specific_validation_branch_prefixes(self) -> None:
        config = {
            "scope_id": "cn_stock_factor_mining",
            "market": "CN",
            "asset_type": "stock",
            "allowed_machines": ["office_desktop"],
            "allowed_tasks": ["factor_batch", "factor_validation"],
            "recommended_branch_prefixes": [
                "codex/factor-batch-cn-stock-",
                "codex/factor-validation-cn-stock-",
            ],
            "required_confirmations": [
                "machine_confirmed",
                "task_confirmed",
                "branch_confirmed",
                "push_policy_confirmed",
                "cn_stock_scope_confirmed",
                "etf_scope_rejected",
            ],
        }

        packet = build_factor_mining_startup_gate(
            config,
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {name: True for name in config["required_confirmations"]},
            },
            current_branch="codex/factor-validation-cn-stock-20260617",
        )

        self.assertEqual(packet["status"], "cleared")
        self.assertEqual(packet["decision"]["blockers"], [])

        bad_packet = build_factor_mining_startup_gate(
            config,
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/random-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {name: True for name in config["required_confirmations"]},
            },
            current_branch="codex/random-cn-stock-20260617",
        )

        self.assertEqual(bad_packet["status"], "blocked")
        self.assertIn("branch_prefix_mismatch", bad_packet["decision"]["blockers"])

    def test_validate_startup_gate_rejects_stale_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(
                json.dumps(
                    {
                        "generated_at": (date.today() - timedelta(days=1)).isoformat(),
                        "status": "cleared",
                        "summary": {"market": "CN", "asset_type": "stock"},
                        "decision": {"startup_gate_cleared": True, "blockers": []},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "generated today"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_audit_research_direction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(
                json.dumps(
                    {
                        "generated_at": date.today().isoformat(),
                        "status": "cleared",
                        "summary": {"market": "CN", "asset_type": "stock"},
                        "decision": {"startup_gate_cleared": True, "blockers": []},
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "research direction"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_repeatable_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(
                json.dumps(
                    {
                        "generated_at": date.today().isoformat(),
                        "status": "cleared",
                        "summary": {"market": "CN", "asset_type": "stock"},
                        "decision": {"startup_gate_cleared": True, "blockers": []},
                        "research_direction": {
                            "objective": "cn_stock_cross_sectional_alpha",
                            "allowed_factor_families": ["price_volume"],
                            "stage_policy": {
                                "discovery": "Design and filter candidates only.",
                                "long_cycle_replay": "Replay frozen parameters across the long cycle.",
                                "validation": "Run OOS only after discovery evidence clears.",
                                "final_holdout": "Read once; never tune after reading.",
                            },
                            "factor_family_rotation": {"max_failed_batches_before_rotation": 1},
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "repeatable mining protocol"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_long_cycle_protocol(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(
                json.dumps(
                    {
                        "generated_at": date.today().isoformat(),
                        "status": "cleared",
                        "summary": {"market": "CN", "asset_type": "stock"},
                        "decision": {"startup_gate_cleared": True, "blockers": []},
                        "research_direction": {
                            "objective": "cn_stock_cross_sectional_alpha",
                            "allowed_factor_families": ["price_volume"],
                            "stage_policy": {
                                "discovery": "Design and filter candidates only.",
                                "validation": "Run OOS only after discovery evidence clears.",
                                "final_holdout": "Read once; never tune after reading.",
                            },
                            "factor_family_rotation": {"max_failed_batches_before_rotation": 1},
                        },
                        "repeatable_mining_protocol": {
                            "source_audit": "data/reports/cn_stock_factor_mining_20260617_batch_audit.md",
                            "next_direction": "legacy_short_window_validation",
                            "recently_rejected_directions": ["single_factor_top50_daily_long_only"],
                            "required_experiment_design": ["twenty_twenty_five_oos_only"],
                            "confirm_before_each_run": ["final_holdout_not_touched"],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "long-cycle"):
                validate_cleared_startup_gate_packet(path)


if __name__ == "__main__":
    unittest.main()
