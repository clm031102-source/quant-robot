import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_factor_mining_startup_gate import run_factor_mining_startup_gate


class FactorMiningStartupGateCliTests(unittest.TestCase):
    def test_run_factor_mining_startup_gate_writes_confirmation_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "startup_gate.json"
            output_dir = root / "startup_gate_output"
            config_path.write_text(
                json.dumps(
                    {
                        "scope_id": "cn_stock_factor_mining",
                        "market": "CN",
                        "asset_type": "stock",
                        "allowed_machines": ["office_desktop"],
                        "allowed_tasks": ["factor_batch"],
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
                ),
                encoding="utf-8",
            )

            packet = run_factor_mining_startup_gate(
                config_path=config_path,
                output_dir=output_dir,
                machine="office_desktop",
                task="factor_batch",
                branch="codex/factor-batch-cn-stock-20260617",
                current_branch="codex/factor-batch-cn-stock-20260617",
                market="CN",
                asset_type="stock",
                confirm_start=True,
            )

            self.assertEqual(packet["status"], "cleared")
            self.assertTrue((output_dir / "factor_mining_startup_gate.json").exists())
            self.assertTrue((output_dir / "factor_mining_startup_gate.md").exists())
            payload = json.loads((output_dir / "factor_mining_startup_gate.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["machine"], "office_desktop")
            self.assertEqual(payload["research_direction"]["objective"], "cn_stock_cross_sectional_alpha")
            self.assertIn("moneyflow", payload["research_direction"]["allowed_factor_families"])
            self.assertEqual(
                payload["repeatable_mining_protocol"]["next_direction"],
                "factor_validation_required_for_daily_champion_oos_candidates",
            )
            self.assertIn(
                "daily_champion_oos_candidates_pre_registered",
                payload["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "overlap_aware_return_statistics",
                payload["repeatable_mining_protocol"]["required_experiment_design"],
            )
            markdown = (output_dir / "factor_mining_startup_gate.md").read_text(encoding="utf-8")
            self.assertIn("Research Direction", markdown)
            self.assertIn("Repeatable Mining Protocol", markdown)
            self.assertIn("Round Governance", markdown)
            self.assertIn("Review cadence: every 3 rounds", markdown)
            self.assertIn("GitHub sync cadence: every 10 rounds", markdown)
            self.assertIn("cn_stock_cross_sectional_alpha", markdown)

    def test_default_cn_stock_config_is_runnable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            packet = run_factor_mining_startup_gate(
                output_dir=Path(tmp),
                machine="office_desktop",
                task="factor_batch",
                branch="codex/factor-batch-cn-stock-20260617",
                current_branch="codex/factor-batch-cn-stock-20260617",
                market="CN",
                asset_type="stock",
                confirm_start=True,
            )

            self.assertEqual(packet["summary"]["scope_id"], "cn_stock_factor_mining")
            self.assertEqual(packet["status"], "cleared")
            self.assertEqual(packet["research_direction"]["objective"], "cn_stock_cross_sectional_alpha")
            self.assertIn("single_family_lockin", packet["research_direction"]["forbidden_directions"])
            self.assertEqual(
                packet["repeatable_mining_protocol"]["next_direction"],
                "round81_public_supertrend_exclusion_preregistration",
            )
            self.assertEqual(
                packet["repeatable_mining_protocol"]["source_audit"],
                "docs/research/cn_stock_round80_lightweight_sync_2026-06-21.md",
            )
            self.assertIn("daily_basic_inputs", packet["config_required_inputs"])
            self.assertIn(
                "daily_basic_hard_liquidity_low_turnover_gate",
                packet["repeatable_mining_protocol"]["recently_rejected_directions"],
            )
            self.assertIn(
                "industry_neutral_ic_audit_for_stock_factors",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "smart_money_quality_round55_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "public_trend_volume_anti_round56_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "industry_breadth_bridge_audit_registered",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "market_regime_cash_overlay_registered",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "dynamic_market_state_cash_overlay_registered",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round72_dynamic_cash_overlay_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round73_benchmark_beta_exposure_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "beta_hedged_spread_translation_audit_after_beta_diagnostic",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "round74_beta_hedged_spread_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round75_beta_hedged_spread_stress_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round76_public_rsrs_preregistration_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round74_76_three_round_review_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round77_public_rsrs_long_cycle_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "public_rsrs_reversal_translation_audit_after_round77",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "public_rsrs_direct_topn_positive_direction",
                packet["repeatable_mining_protocol"]["recently_rejected_directions"],
            )
            self.assertIn(
                "public_rsrs_industry_neutral_topn_as_promotion_candidate",
                packet["repeatable_mining_protocol"]["recently_rejected_directions"],
            )
            self.assertIn(
                "public_rsrs_bottom_exclusion_costed_walk_forward_after_round78",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "round78_public_rsrs_translation_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round79_public_rsrs_bottom_exclusion_walk_forward_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round71_79_work_report_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round80_lightweight_sync_report_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "public_rsrs_bottom_exclusion_costed_walk_forward_promotion",
                packet["repeatable_mining_protocol"]["recently_rejected_directions"],
            )
            self.assertIn(
                "public_supertrend_pre_registration_after_rsrs_hibernation",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "spread_candidate_cost_impact_execution_stress_before_paper_readiness",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "three_round_review_cadence_confirmed",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "ten_round_github_sync_after_every_ten_factor_batches",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "final_holdout_not_touched",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertEqual(packet["validation_windows"]["long_cycle_replay"]["start"], "2015-01-01")
            self.assertEqual(packet["validation_windows"]["same_parameter_full_sample"]["start"], "2015-01-01")
            self.assertIn(
                "long_cycle_same_parameter_replay",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "market_regime_coverage_enabled",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "lookahead_bias_audit_enabled",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "overfit_multiple_testing_audit_enabled",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "batch12_validation_handoff_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "industry_neutral_ic_audit_enabled",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "round55_57_three_round_review_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "shared_factor_matrix_cache_plan_registered",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "industry_neutral_public_formula_replay_registered",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "public_formula_round58_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "pv_corr_reversal_research_lead_registered",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "single_lead_portfolio_conversion_audit_before_family_expansion",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "costed_bottom_exclusion_portfolio_for_pv_corr_reversal",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "round58_60_three_round_review_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "costed_exclusion_portfolio_plan_registered",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "constrained_exposure_sensitivity_for_pv_corr_exclusion",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "pv_corr_costed_exclusion_round61_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "public_reference_review_before_pv_corr_continuation",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "pv_corr_exposure_sensitivity_round62_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "daily_basic_quality_value_lowvol_pre_registered_candidates",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "pv_corr_standalone_line_hibernated",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "daily_basic_residual_portfolio_conversion_after_neutral_ic",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "daily_basic_residual_round64_ic_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "daily_basic_residual_industry_neutral_top100_long_only_promotion",
                packet["repeatable_mining_protocol"]["recently_rejected_directions"],
            )
            self.assertIn(
                "daily_basic_residual_ic_portfolio_gap_audit_after_topn_rejection",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "daily_basic_residual_round65_portfolio_audit_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "daily_basic_residual_quality_low_vol_bottom_exclusion_continuation",
                packet["repeatable_mining_protocol"]["recently_rejected_directions"],
            )
            self.assertIn(
                "daily_basic_residual_costed_bottom_exclusion_portfolio_after_overlay",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "round64_66_three_round_review_read",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )
            self.assertIn(
                "daily_basic_residual_costed_exclusion_continuation_after_drawdown_failure",
                packet["repeatable_mining_protocol"]["recently_rejected_directions"],
            )
            self.assertIn(
                "stock_to_etf_breadth_bridge_if_public_risk_regime_fails",
                packet["repeatable_mining_protocol"]["required_experiment_design"],
            )
            self.assertIn(
                "anti_obv_regime_focus_config_registered",
                packet["repeatable_mining_protocol"]["confirm_before_each_run"],
            )

    def test_run_factor_mining_startup_gate_can_infer_current_branch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "scripts.run_factor_mining_startup_gate._current_branch",
                return_value="codex/factor-validation-cn-stock-20260620",
            ):
                packet = run_factor_mining_startup_gate(
                    output_dir=Path(tmp),
                    machine="office_desktop",
                    task="factor_validation",
                    market="CN",
                    asset_type="stock",
                    confirm_start=True,
                )

            self.assertEqual(packet["status"], "cleared")
            self.assertEqual(packet["summary"]["branch"], "codex/factor-validation-cn-stock-20260620")
            self.assertEqual(packet["summary"]["current_branch"], "codex/factor-validation-cn-stock-20260620")


if __name__ == "__main__":
    unittest.main()
