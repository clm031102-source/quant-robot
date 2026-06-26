import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from quant_robot.ops.factor_mining_quality_gate import required_control_ids
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

    def test_validate_startup_gate_rejects_packet_without_source_evidence_protocol(self) -> None:
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
                        "repeatable_mining_protocol": {
                            "source_audit": "data/reports/cn_stock_factor_mining_20260617_batch_audit.md",
                            "next_direction": "long_cycle_validation",
                            "recently_rejected_directions": ["single_factor_top50_daily_long_only"],
                            "required_experiment_design": [
                                "long_cycle_same_parameter_replay",
                                "same_parameter_full_sample_diagnostic",
                                "rolling_walk_forward_train_test_split",
                                "market_regime_coverage",
                                "lookahead_bias_audit",
                                "overfit_multiple_testing_audit",
                            ],
                            "confirm_before_each_run": [
                                "same_parameter_full_sample_enabled",
                                "market_regime_coverage_enabled",
                                "lookahead_bias_audit_enabled",
                                "overfit_multiple_testing_audit_enabled",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "source-evidence"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_signal_window_regime_protocol(self) -> None:
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
                        "repeatable_mining_protocol": {
                            "source_audit": "data/reports/cn_stock_factor_mining_20260617_batch_audit.md",
                            "next_direction": "long_cycle_validation",
                            "recently_rejected_directions": ["single_factor_top50_daily_long_only"],
                            "required_experiment_design": [
                                "long_cycle_same_parameter_replay",
                                "same_parameter_full_sample_diagnostic",
                                "rolling_walk_forward_train_test_split",
                                "walk_forward_progress_audit",
                                "market_regime_coverage",
                                "lookahead_bias_audit",
                                "overfit_multiple_testing_audit",
                                "source_performance_evidence_required",
                                "source_evidence_status_gate",
                            ],
                            "confirm_before_each_run": [
                                "same_parameter_full_sample_enabled",
                                "promotion_progress_audit_gate_enabled",
                                "market_regime_coverage_enabled",
                                "lookahead_bias_audit_enabled",
                                "overfit_multiple_testing_audit_enabled",
                                "source_performance_evidence_gate_enabled",
                                "promotion_source_evidence_gate_enabled",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "signal-window regime"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_progress_audit_protocol(self) -> None:
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
                        "repeatable_mining_protocol": {
                            "source_audit": "data/reports/cn_stock_factor_mining_20260617_batch_audit.md",
                            "next_direction": "long_cycle_validation",
                            "recently_rejected_directions": ["single_factor_top50_daily_long_only"],
                            "required_experiment_design": [
                                "long_cycle_same_parameter_replay",
                                "same_parameter_full_sample_diagnostic",
                                "rolling_walk_forward_train_test_split",
                                "market_regime_coverage",
                                "market_regime_signal_window_coverage",
                                "lookahead_bias_audit",
                                "overfit_multiple_testing_audit",
                                "source_performance_evidence_required",
                                "source_evidence_status_gate",
                            ],
                            "confirm_before_each_run": [
                                "same_parameter_full_sample_enabled",
                                "market_regime_coverage_enabled",
                                "market_regime_signal_window_coverage_enabled",
                                "lookahead_bias_audit_enabled",
                                "overfit_multiple_testing_audit_enabled",
                                "source_performance_evidence_gate_enabled",
                                "promotion_source_evidence_gate_enabled",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "progress-audit"):
                validate_cleared_startup_gate_packet(path)

    def test_default_startup_protocol_requires_source_evidence_gate(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn("source_performance_evidence_required", protocol["required_experiment_design"])
        self.assertIn("source_evidence_status_gate", protocol["required_experiment_design"])
        self.assertIn("source_performance_evidence_gate_enabled", protocol["confirm_before_each_run"])
        self.assertIn("promotion_source_evidence_gate_enabled", protocol["confirm_before_each_run"])

    def test_default_startup_protocol_requires_signal_window_regime_gate(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn("market_regime_signal_window_coverage", protocol["required_experiment_design"])
        self.assertIn("market_regime_signal_window_coverage_enabled", protocol["confirm_before_each_run"])
        self.assertIn("walk_forward_progress_audit", protocol["required_experiment_design"])
        self.assertIn("promotion_progress_audit_gate_enabled", protocol["confirm_before_each_run"])

    def test_default_startup_protocol_requires_round_governance(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        governance = packet["round_governance"]
        self.assertEqual(governance["round_unit"], "factor_family_batch")
        self.assertEqual(governance["review_every_n_rounds"], 3)
        self.assertEqual(governance["sync_every_n_rounds"], 10)
        self.assertIn("direction_adjustment_decision", governance["three_round_review_required_actions"])
        self.assertIn("github_safe_sync_after_validation", governance["ten_round_sync_required_actions"])
        self.assertIn("qlib", governance["public_reference_projects"])
        self.assertIn("alphalens", governance["public_reference_projects"])
        self.assertIn(
            "three_round_review_gate_enabled",
            packet["repeatable_mining_protocol"]["confirm_before_each_run"],
        )
        self.assertIn(
            "ten_round_github_sync_gate_enabled",
            packet["repeatable_mining_protocol"]["confirm_before_each_run"],
        )
        self.assertTrue(any("3 rounds" in item for item in packet["pre_run_checklist"]))
        self.assertTrue(any("10 rounds" in item for item in packet["pre_run_checklist"]))

    def test_default_startup_protocol_requires_candidate_plan_control_gate(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        for item in (
            "candidate_plan_control_gate_before_factor_generation",
            "real_tradeability_controls_declared_before_mining",
            "pit_availability_lag_controls_declared_before_mining",
            "industry_style_neutralization_controls_declared_before_mining",
            "portfolio_construction_controls_declared_before_portfolio_grid",
            "strict_statistics_controls_declared_before_result_ranking",
            "china_regime_controls_declared_before_walk_forward",
            "event_or_event_contamination_controls_declared_before_promotion",
        ):
            self.assertIn(item, protocol["required_experiment_design"])
        for item in (
            "candidate_plan_control_gate_enabled",
            "real_tradeability_controls_declared",
            "pit_availability_lag_controls_declared",
            "industry_style_neutralization_controls_declared",
            "portfolio_construction_controls_declared",
            "strict_statistics_controls_declared",
            "china_regime_controls_declared",
            "event_or_event_contamination_controls_declared",
        ):
            self.assertIn(item, protocol["confirm_before_each_run"])
        self.assertTrue(any("candidate plan gate" in item.lower() for item in packet["pre_run_checklist"]))
        self.assertTrue(any("tradeability, PIT, neutralization" in item for item in packet["confirmation_questions"]))

    def test_default_startup_protocol_requires_candidate_hypothesis_source(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn("candidate_hypothesis_source_required_before_generation", protocol["required_experiment_design"])
        self.assertIn("candidate_hypothesis_source_declared", protocol["confirm_before_each_run"])
        self.assertTrue(any("hypothesis source" in item.lower() for item in packet["pre_run_checklist"]))

    def test_startup_checklist_surfaces_quality_gate_evidence_and_next_actions(self) -> None:
        controls = required_control_ids()
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "quality_gate": {
                    "control_status": {control_id: "planned" for control_id in controls},
                    "control_next_actions": {control_id: "finish the control" for control_id in controls},
                },
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        checklist = "\n".join(packet["pre_run_checklist"])
        self.assertIn("missing_evidence=0", checklist)
        self.assertIn("missing_next_actions=0", checklist)

    def test_startup_checklist_surfaces_research_execution_policy(self) -> None:
        controls = required_control_ids()
        planned_controls = {control_id: "planned" for control_id in controls}
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "quality_gate": {
                    "control_status": planned_controls,
                    "control_next_actions": {control_id: "finish the control" for control_id in controls},
                },
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        checklist = "\n".join(packet["pre_run_checklist"])
        protocol = packet["repeatable_mining_protocol"]
        self.assertIn(
            "quality_gate_research_execution_policy_before_mining",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "direct_factor_generation_blocked_until_pre_mining_controls_ready",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "research_execution_policy_reviewed_before_factor_generation",
            protocol["confirm_before_each_run"],
        )
        self.assertIn(
            "candidate_preregistration_only_when_controls_incomplete_confirmed",
            protocol["confirm_before_each_run"],
        )
        self.assertIn("Research execution policy", checklist)
        self.assertIn("direct_factor_generation_allowed=False", checklist)
        self.assertIn("candidate_preregistration_without_profit_claims", checklist)

    def test_default_startup_protocol_requires_tradeability_data_readiness_audit(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        checklist = "\n".join(packet["pre_run_checklist"])
        self.assertIn(
            "tradeability_data_readiness_audit_before_direct_factor_generation",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "official_limit_suspend_st_delist_feeds_required_before_direct_mining",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "official_tradeability_feed_coverage_manifest_required_before_direct_mining",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "tradeability_data_readiness_audit_read",
            protocol["confirm_before_each_run"],
        )
        self.assertIn(
            "official_tradeability_feeds_confirmed_before_direct_mining",
            protocol["confirm_before_each_run"],
        )
        self.assertIn(
            "official_tradeability_feed_coverage_manifest_confirmed",
            protocol["confirm_before_each_run"],
        )
        self.assertIn("tradeability data readiness", checklist.lower())

    def test_validate_startup_gate_rejects_packet_without_tradeability_data_readiness_protocol(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )
        protocol = packet["repeatable_mining_protocol"]
        protocol["required_experiment_design"] = [
            item
            for item in protocol["required_experiment_design"]
            if item != "tradeability_data_readiness_audit_before_direct_factor_generation"
        ]
        protocol["confirm_before_each_run"] = [
            item
            for item in protocol["confirm_before_each_run"]
            if item != "tradeability_data_readiness_audit_read"
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "tradeability data readiness"):
                validate_cleared_startup_gate_packet(path)

    def test_default_startup_protocol_requires_strict_candidate_promotion_policy(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        checklist = "\n".join(packet["pre_run_checklist"])
        self.assertIn(
            "candidate_strict_promotion_policy_before_screening",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "candidate_strict_promotion_policy_declared",
            protocol["confirm_before_each_run"],
        )
        self.assertIn("strict promotion policy", checklist)

    def test_default_startup_protocol_requires_quality_gate_evidence_action_ledger(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn("quality_gate_evidence_next_action_ledger", protocol["required_experiment_design"])
        self.assertIn("quality_gate_evidence_next_actions_confirmed", protocol["confirm_before_each_run"])

    def test_default_startup_protocol_requires_tradeability_mask_cache_before_replay(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn(
            "year_sliced_tradeability_mask_cache_before_old_candidate_replay",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "short_window_mask_cache_smoke_not_promotion_evidence",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "tradeability_mask_cache_cross_year_namechange_interval_check",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "tradeability_cache_direct_equivalence_check_before_profit_claims",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "tradeability_mask_cache_stock_basic_l_d_p_status_required",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "tradeability_mask_cache_metadata_blocker_counts_required",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "tradeability_mask_cache_full_window_confirmed",
            protocol["confirm_before_each_run"],
        )
        self.assertIn(
            "short_window_smoke_rejected_as_profitability_evidence",
            protocol["confirm_before_each_run"],
        )
        self.assertIn(
            "tradeability_mask_cache_cross_year_namechange_confirmed",
            protocol["confirm_before_each_run"],
        )
        self.assertIn(
            "tradeability_cache_direct_equivalence_confirmed",
            protocol["confirm_before_each_run"],
        )
        self.assertIn(
            "tradeability_mask_cache_stock_basic_l_d_p_confirmed",
            protocol["confirm_before_each_run"],
        )
        self.assertIn(
            "tradeability_mask_cache_metadata_blockers_confirmed",
            protocol["confirm_before_each_run"],
        )
        self.assertTrue(any("mask cache" in item.lower() for item in packet["pre_run_checklist"]))
        self.assertTrue(any("stock_basic" in item for item in packet["pre_run_checklist"]))

    def test_default_startup_protocol_requires_financial_pit_timing_audit_before_financial_mining(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn(
            "financial_pit_timing_audit_before_financial_factor_generation",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "financial_signal_lag_stale_threshold_required",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "financial_pit_timing_audit_confirmed",
            protocol["confirm_before_each_run"],
        )
        self.assertIn(
            "financial_stale_or_unmapped_signal_rows_blocked",
            protocol["confirm_before_each_run"],
        )
        checklist = "\n".join(packet["pre_run_checklist"])
        self.assertIn("Financial PIT timing audit", checklist)
        self.assertIn("stale", checklist)
        self.assertIn("unmapped", checklist)

    def test_default_startup_protocol_requires_portfolio_policy_gate_before_portfolio_grid(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn("portfolio_construction_policy_gate_before_portfolio_grid", protocol["required_experiment_design"])
        self.assertIn("portfolio_required_metric_pack_before_promotion", protocol["required_experiment_design"])
        self.assertIn("portfolio_construction_policy_gate_confirmed", protocol["confirm_before_each_run"])
        self.assertIn("portfolio_grid_without_policy_gate_rejected", protocol["confirm_before_each_run"])
        checklist = "\n".join(packet["pre_run_checklist"])
        self.assertIn("portfolio construction policy gate", checklist.lower())
        self.assertIn("risk budget", checklist.lower())

    def test_default_startup_protocol_requires_industry_style_exposure_audit_before_portfolio_grid(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn("industry_style_exposure_audit_before_portfolio_grid", protocol["required_experiment_design"])
        self.assertIn("industry_r2_and_style_correlation_report_required", protocol["required_experiment_design"])
        self.assertIn("residual_factor_matrix_required_before_portfolio_grid", protocol["required_experiment_design"])
        self.assertIn("style_decomposition_size_value_lowvol_momentum_liquidity_required", protocol["required_experiment_design"])
        self.assertIn("industry_style_exposure_audit_confirmed", protocol["confirm_before_each_run"])
        self.assertIn("raw_topn_without_residual_audit_rejected", protocol["confirm_before_each_run"])
        checklist = "\n".join(packet["pre_run_checklist"])
        self.assertIn("industry/style exposure audit", checklist)
        self.assertIn("residual factor matrix", checklist)

    def test_default_startup_protocol_requires_method_optimization_controls(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260624",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260624",
        )

        protocol = packet["repeatable_mining_protocol"]
        expected_design_items = [
            "a_share_microstructure_limit_suspend_st_new_delist_board_filters",
            "financial_pit_announcement_revision_available_date_lag",
            "industry_style_neutral_combination_policy",
            "cn_etf_rotation_dedicated_signal_pack_separation",
            "portfolio_metric_pack_profit_rate_sharpe_win_rate_drawdown_turnover",
            "strict_deflated_sharpe_cpcv_white_reality_check_sensitivity",
            "china_regime_policy_credit_flow_liquidity_index_location",
            "event_factor_forecast_dividend_buyback_holder_lockup_index_rebalance",
        ]
        expected_confirmations = [
            "method_optimization_controls_reviewed_before_mining",
            "a_share_real_trading_filters_confirmed",
            "financial_available_date_controls_confirmed",
            "industry_style_neutral_combination_confirmed",
            "cn_etf_dedicated_signal_pack_separated_confirmed",
            "portfolio_metric_pack_confirmed",
            "strict_statistics_suite_confirmed",
            "china_market_regime_suite_confirmed",
            "event_factor_suite_confirmed",
        ]

        for item in expected_design_items:
            self.assertIn(item, protocol["required_experiment_design"])
        for item in expected_confirmations:
            self.assertIn(item, protocol["confirm_before_each_run"])
        checklist = "\n".join(packet["pre_run_checklist"])
        self.assertIn("A-share microstructure", checklist)
        self.assertIn("announcement dates", checklist)
        self.assertIn("Deflated Sharpe", checklist)

    def test_validate_startup_gate_rejects_packet_without_method_optimization_controls(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260624",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260624",
        )
        protocol = packet["repeatable_mining_protocol"]
        protocol["required_experiment_design"] = [
            item
            for item in protocol["required_experiment_design"]
            if item != "a_share_microstructure_limit_suspend_st_new_delist_board_filters"
        ]
        protocol["confirm_before_each_run"] = [
            item
            for item in protocol["confirm_before_each_run"]
            if item != "method_optimization_controls_reviewed_before_mining"
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "method optimization controls"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_industry_style_exposure_audit_protocol(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )
        protocol = packet["repeatable_mining_protocol"]
        protocol["required_experiment_design"] = [
            item
            for item in protocol["required_experiment_design"]
            if item != "industry_style_exposure_audit_before_portfolio_grid"
        ]
        protocol["confirm_before_each_run"] = [
            item
            for item in protocol["confirm_before_each_run"]
            if item != "industry_style_exposure_audit_confirmed"
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "industry/style exposure audit"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_tradeability_mask_cache_protocol(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )
        protocol = packet["repeatable_mining_protocol"]
        protocol["required_experiment_design"] = [
            item
            for item in protocol["required_experiment_design"]
            if item != "year_sliced_tradeability_mask_cache_before_old_candidate_replay"
        ]
        protocol["confirm_before_each_run"] = [
            item
            for item in protocol["confirm_before_each_run"]
            if item != "tradeability_mask_cache_full_window_confirmed"
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "tradeability mask cache"):
                validate_cleared_startup_gate_packet(path)

    def test_default_startup_protocol_requires_translation_audits(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn("ic_to_portfolio_gap_audit_before_topn_expansion", protocol["required_experiment_design"])
        self.assertIn("industry_neutral_ic_audit_for_stock_factors", protocol["required_experiment_design"])
        self.assertIn("translation_layer_required_after_strong_ic_rejection", protocol["required_experiment_design"])
        self.assertIn("bottom_exclusion_overlay_audit_for_strong_ic_rejected_topn", protocol["required_experiment_design"])
        self.assertIn("bottom_exclusion_costed_walk_forward_before_promotion", protocol["required_experiment_design"])
        self.assertIn("ic_to_portfolio_gap_audit_read", protocol["confirm_before_each_run"])
        self.assertIn("industry_neutral_ic_audit_enabled", protocol["confirm_before_each_run"])
        self.assertIn("translation_layer_plan_registered", protocol["confirm_before_each_run"])
        self.assertIn("bottom_exclusion_overlay_audit_read", protocol["confirm_before_each_run"])
        self.assertIn("bottom_exclusion_costed_walk_forward_registered", protocol["confirm_before_each_run"])
        self.assertTrue(any("industry-neutral IC" in item for item in packet["pre_run_checklist"]))
        self.assertTrue(any("bottom-quantile exclusion" in item for item in packet["pre_run_checklist"]))

    def test_startup_packet_contains_pre_mining_control_contract(self) -> None:
        controls = required_control_ids()
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "quality_gate": {
                    "control_status": {control_id: "planned" for control_id in controls},
                    "control_next_actions": {control_id: "finish the control" for control_id in controls},
                },
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )

        contract = packet["pre_mining_control_contract"]
        self.assertEqual(contract["scope"], "CN stock alpha pre-mining controls")
        self.assertFalse(contract["direct_factor_generation_allowed"])
        area_ids = {area["area_id"] for area in contract["areas"]}
        self.assertIn("a_share_real_tradeability", area_ids)
        self.assertIn("financial_pit_timing", area_ids)
        self.assertIn("industry_style_neutralization", area_ids)
        self.assertIn("cn_etf_rotation_boundary", area_ids)
        self.assertIn("portfolio_construction", area_ids)
        self.assertIn("strict_statistics", area_ids)
        self.assertIn("china_market_regime", area_ids)
        self.assertIn("event_factors", area_ids)
        portfolio_area = next(area for area in contract["areas"] if area["area_id"] == "portfolio_construction")
        self.assertIn("annual_return", portfolio_area["required_outputs"])
        self.assertIn("win_rate", portfolio_area["required_outputs"])
        self.assertIn("max_drawdown", portfolio_area["required_outputs"])
        protocol = packet["repeatable_mining_protocol"]
        self.assertIn(
            "pre_mining_control_contract_before_factor_generation",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "pre_mining_control_contract_reviewed_before_generation",
            protocol["confirm_before_each_run"],
        )
        self.assertTrue(any("pre-mining control contract" in item.lower() for item in packet["pre_run_checklist"]))

    def test_default_startup_protocol_requires_candidate_plan_gate_packet_for_mining_entrypoints(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260625",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260625",
        )

        protocol = packet["repeatable_mining_protocol"]
        self.assertIn(
            "candidate_plan_gate_packet_required_by_mining_entrypoints",
            protocol["required_experiment_design"],
        )
        self.assertIn(
            "candidate_plan_gate_packet_validated_before_factor_generation",
            protocol["confirm_before_each_run"],
        )

    def test_startup_packet_contains_method_optimization_contract(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
                "method_optimization_contract": {
                    "source_audit": "docs/research/cn_stock_round226_method_optimization_contract_2026-06-24.md",
                    "next_allowed_direction": "round227_public_method_family_rotation_candidate_plan_after_method_contract",
                    "hibernated_families": [
                        "public_risk_filter_bridge",
                        "financial_post_announcement_gap_reversal_without_new_orthogonal_repair",
                    ],
                    "family_stop_loss": {
                        "max_failed_batches_before_rotation": 1,
                        "hibernate_after_zero_accepted_walk_forward": True,
                        "reentry_requires_new_orthogonal_hypothesis": True,
                    },
                },
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260624",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260624",
        )

        contract = packet["method_optimization_contract"]
        self.assertEqual(contract["scope"], "CN stock factor mining method optimization")
        self.assertEqual(
            contract["source_audit"],
            "docs/research/cn_stock_round226_method_optimization_contract_2026-06-24.md",
        )
        self.assertFalse(contract["promotion_allowed_without_contract"])
        self.assertFalse(contract["direct_topn_expansion_allowed_without_contract"])
        area_ids = {area["area_id"] for area in contract["optimization_areas"]}
        self.assertEqual(
            area_ids,
            {
                "a_share_real_tradeability",
                "financial_pit_timing",
                "industry_style_neutralization",
                "cn_etf_rotation_boundary",
                "portfolio_construction",
                "strict_statistics",
                "china_market_regime",
                "event_factors",
            },
        )
        self.assertIn("public_risk_filter_bridge", contract["hibernated_families"])
        self.assertTrue(contract["family_stop_loss"]["hibernate_after_zero_accepted_walk_forward"])
        self.assertTrue(contract["family_stop_loss"]["reentry_requires_new_orthogonal_hypothesis"])
        self.assertEqual(
            contract["next_allowed_direction"],
            "round227_public_method_family_rotation_candidate_plan_after_method_contract",
        )

    def test_validate_startup_gate_rejects_method_contract_missing_required_area_outputs(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260624",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260624",
        )
        for area in packet["method_optimization_contract"]["optimization_areas"]:
            if area["area_id"] == "portfolio_construction":
                area["required_outputs"] = [
                    output for output in area["required_outputs"] if output != "profit_rate"
                ]
                break

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "method optimization contract lacks required outputs"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_method_optimization_contract(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260624",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260624",
        )
        packet.pop("method_optimization_contract", None)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "method optimization contract"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_pre_mining_control_contract(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260620",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260620",
        )
        packet.pop("pre_mining_control_contract")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "pre-mining control contract"):
                validate_cleared_startup_gate_packet(path)

    def test_validate_startup_gate_rejects_packet_without_round_governance(self) -> None:
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
                        "repeatable_mining_protocol": {
                            "source_audit": "data/reports/cn_stock_factor_mining_20260617_batch_audit.md",
                            "next_direction": "long_cycle_validation",
                            "recently_rejected_directions": ["single_factor_top50_daily_long_only"],
                            "required_experiment_design": [
                                "long_cycle_same_parameter_replay",
                                "same_parameter_full_sample_diagnostic",
                                "rolling_walk_forward_train_test_split",
                                "walk_forward_progress_audit",
                                "market_regime_coverage",
                                "market_regime_signal_window_coverage",
                                "lookahead_bias_audit",
                                "overfit_multiple_testing_audit",
                                "source_performance_evidence_required",
                                "source_evidence_status_gate",
                            ],
                            "confirm_before_each_run": [
                                "same_parameter_full_sample_enabled",
                                "promotion_progress_audit_gate_enabled",
                                "market_regime_coverage_enabled",
                                "market_regime_signal_window_coverage_enabled",
                                "lookahead_bias_audit_enabled",
                                "overfit_multiple_testing_audit_enabled",
                                "source_performance_evidence_gate_enabled",
                                "promotion_source_evidence_gate_enabled",
                            ],
                        },
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "round governance"):
                validate_cleared_startup_gate_packet(path)

    def test_startup_packet_tracks_current_round_state_after_three_round_review(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
                "research_direction": {
                    "repeatable_mining_protocol": {
                        "source_audit": "docs/research/cn_stock_round245_247_three_round_review_2026-06-25.md",
                        "next_direction": "round248_rotate_to_external_revision_or_nonfinancial_event_context",
                    },
                },
                "round_state": {
                    "last_completed_round": 247,
                    "next_round": 248,
                    "last_three_round_review": "docs/research/cn_stock_round245_247_three_round_review_2026-06-25.md",
                    "last_three_round_decision": "rotate_family",
                    "family_rotation_required": True,
                    "next_direction": "round248_rotate_to_external_revision_or_nonfinancial_event_context",
                    "blocked_reentry_families": [
                        "accounting_quality_realized_statement_formula_mutations",
                    ],
                    "required_before_next_round": [
                        "preregister_external_revision_or_nonfinancial_event_family",
                        "block_more_realized_statement_formula_mutations",
                    ],
                },
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260625",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260625",
        )

        state = packet["round_state"]
        self.assertEqual(state["last_completed_round"], 247)
        self.assertEqual(state["next_round"], 248)
        self.assertEqual(state["last_three_round_decision"], "rotate_family")
        self.assertTrue(state["family_rotation_required"])
        self.assertEqual(
            state["next_direction"],
            "round248_rotate_to_external_revision_or_nonfinancial_event_context",
        )
        self.assertIn(
            "accounting_quality_realized_statement_formula_mutations",
            state["blocked_reentry_families"],
        )
        self.assertTrue(any("Round247" in item for item in packet["pre_run_checklist"]))

    def test_validate_startup_gate_rejects_round_state_next_direction_drift(self) -> None:
        packet = build_factor_mining_startup_gate(
            {
                "scope_id": "cn_stock_factor_mining",
                "market": "CN",
                "asset_type": "stock",
                "allowed_machines": ["office_desktop"],
                "allowed_tasks": ["factor_validation"],
                "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
                "required_confirmations": [
                    "machine_confirmed",
                    "task_confirmed",
                    "branch_confirmed",
                    "push_policy_confirmed",
                    "cn_stock_scope_confirmed",
                    "etf_scope_rejected",
                ],
                "research_direction": {
                    "repeatable_mining_protocol": {
                        "source_audit": "docs/research/cn_stock_round245_247_three_round_review_2026-06-25.md",
                        "next_direction": "round248_rotate_to_external_revision_or_nonfinancial_event_context",
                    },
                },
                "round_state": {
                    "last_completed_round": 247,
                    "next_round": 248,
                    "last_three_round_review": "docs/research/cn_stock_round245_247_three_round_review_2026-06-25.md",
                    "last_three_round_decision": "rotate_family",
                    "family_rotation_required": True,
                    "next_direction": "round248_rotate_to_external_revision_or_nonfinancial_event_context",
                    "required_before_next_round": [
                        "preregister_external_revision_or_nonfinancial_event_family",
                    ],
                },
            },
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260625",
                "market": "CN",
                "asset_type": "stock",
                "confirmations": {
                    "machine_confirmed": True,
                    "task_confirmed": True,
                    "branch_confirmed": True,
                    "push_policy_confirmed": True,
                    "cn_stock_scope_confirmed": True,
                    "etf_scope_rejected": True,
                },
            },
            current_branch="codex/factor-validation-cn-stock-20260625",
        )
        packet["round_state"]["next_direction"] = "round236_accounting_quality_statement_full_universe_shard_backfill_before_preregistration"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "factor_mining_startup_gate.json"
            path.write_text(json.dumps(packet), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "round state next direction"):
                validate_cleared_startup_gate_packet(path)


if __name__ == "__main__":
    unittest.main()
