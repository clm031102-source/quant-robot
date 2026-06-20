import os
import unittest
from unittest.mock import patch

import scripts.run_checks as run_checks
from scripts.run_checks import build_check_plan


class CheckPlanTests(unittest.TestCase):
    def test_check_plan_is_local_and_contains_core_commands(self):
        plan = build_check_plan("python")

        names = [step.name for step in plan]
        self.assertEqual(
            names,
            [
                "unit_and_integration_tests",
                "compile_python",
                "project_audit",
                "readiness_check",
                "provider_status",
                "provider_evidence",
                "provider_remediation",
                "provider_remediation_rehearsal",
                "data_catalog",
                "data_quality_audit",
                "data_gap_resolution",
                "data_gap_evidence",
                "data_gap_rehearsal",
                "fixture_research",
                "research_pipeline",
                "experiment_grid",
                "walk_forward",
                "signal_snapshot",
                "paper_simulation",
                "paper_observation",
                "promotion_ops",
                "duplicate_registry",
                "promotion_review",
                "manual_review_rehearsal",
                "evidence_refresh",
                "pre_api_readiness_board",
                "readiness_projection",
                "blocker_worklist",
                "residual_blocker_focus",
                "residual_data_gap_review",
                "residual_provider_review",
                "daily_ops",
                "profile_observation",
                "recent_data_refresh",
                "post_refresh_replay",
                "observation_sufficiency",
                "expanded_observation_replay",
                "iterative_observation_expansion",
                "tushare_activation_gate",
                "paper_observation_history",
                "paper_ops_guardrail",
                "paper_ops_runbook",
                "risk_candidate_selector",
                "constrained_candidate_search",
                "paper_profile_optimizer",
            ],
        )
        self.assertTrue(all(not step.uses_network for step in plan))
        self.assertIn("-m", plan[0].command)
        self.assertIn("scripts/run_project_audit.py", plan[2].command)
        self.assertIn("scripts/show_provider_status.py", plan[4].command)
        self.assertIn("scripts/run_provider_evidence.py", plan[5].command)
        self.assertIn("scripts/run_provider_remediation.py", plan[6].command)
        self.assertIn("scripts/run_provider_remediation_rehearsal.py", plan[7].command)
        self.assertIn("--summary-only", plan[8].command)
        self.assertIn("--output", plan[4].command)
        self.assertIn("data/reports/provider_status/provider_status.json", plan[4].command)
        self.assertIn("scripts/run_data_quality_audit.py", plan[9].command)
        self.assertIn("scripts/run_data_gap_resolution.py", plan[10].command)
        self.assertIn("scripts/run_data_gap_evidence.py", plan[11].command)
        self.assertIn("scripts/run_data_gap_rehearsal.py", plan[12].command)
        self.assertIn("scripts/run_experiment_grid.py", plan[15].command)
        self.assertIn("scripts/run_walk_forward.py", plan[16].command)
        self.assertIn("scripts/run_signal_snapshot.py", plan[17].command)
        self.assertIn("scripts/run_paper_simulation.py", plan[18].command)
        self.assertIn("scripts/run_paper_observation.py", plan[19].command)
        self.assertIn("scripts/run_promotion_ops.py", plan[20].command)
        self.assertIn("scripts/run_duplicate_registry.py", plan[21].command)
        self.assertIn("scripts/run_promotion_review.py", plan[22].command)
        self.assertIn("scripts/run_manual_review_rehearsal.py", plan[23].command)
        self.assertIn("scripts/run_evidence_refresh.py", plan[24].command)
        self.assertIn("scripts/run_pre_api_readiness_board.py", plan[25].command)
        self.assertIn("scripts/run_readiness_projection.py", plan[26].command)
        self.assertIn("scripts/run_blocker_worklist.py", plan[27].command)
        self.assertIn("scripts/run_residual_blocker_focus.py", plan[28].command)
        self.assertIn("scripts/run_residual_data_gap_review.py", plan[29].command)
        self.assertIn("scripts/run_residual_provider_review.py", plan[30].command)
        self.assertIn("scripts/run_daily_ops.py", plan[31].command)
        self.assertIn("scripts/run_profile_observation.py", plan[32].command)
        self.assertIn("scripts/run_recent_data_refresh.py", plan[33].command)
        self.assertNotIn("--execute", plan[33].command)
        self.assertIn("scripts/run_post_refresh_replay.py", plan[34].command)
        self.assertIn("scripts/run_observation_sufficiency.py", plan[35].command)
        self.assertIn("scripts/run_expanded_observation_replay.py", plan[36].command)
        self.assertIn("scripts/run_iterative_observation_expansion.py", plan[37].command)
        self.assertIn("scripts/run_tushare_activation_gate.py", plan[38].command)
        self.assertIn("scripts/run_paper_observation_history.py", plan[39].command)
        self.assertIn("scripts/run_paper_ops_guardrail.py", plan[40].command)
        self.assertIn("scripts/run_paper_ops_runbook.py", plan[41].command)
        self.assertIn("scripts/run_risk_candidate_selector.py", plan[42].command)
        self.assertIn("scripts/run_constrained_candidate_search.py", plan[43].command)
        self.assertIn("scripts/run_paper_profile_optimizer.py", plan[44].command)

    def test_laptop_check_plan_keeps_fast_audit_and_fixture_smoke_steps(self):
        plan = build_check_plan("python", profile="laptop")

        names = [step.name for step in plan]
        self.assertEqual(
            names,
            [
                "unit_and_integration_tests",
                "compile_python",
                "project_audit",
                "readiness_check",
                "provider_status",
                "provider_evidence",
                "provider_remediation",
                "provider_remediation_rehearsal",
                "data_catalog",
                "fixture_research",
                "research_pipeline",
                "signal_snapshot",
                "paper_simulation",
                "recent_data_refresh",
                "tushare_activation_gate",
                "paper_ops_guardrail",
            ],
        )
        self.assertTrue(all(not step.uses_network for step in plan))
        self.assertNotIn("experiment_grid", names)
        self.assertNotIn("walk_forward", names)
        self.assertNotIn("paper_profile_optimizer", names)
        recent_refresh = next(step for step in plan if step.name == "recent_data_refresh")
        self.assertIn("--machine", recent_refresh.command)
        self.assertIn("laptop", recent_refresh.command)
        self.assertNotIn("--execute", recent_refresh.command)
        activation_gate = next(step for step in plan if step.name == "tushare_activation_gate")
        self.assertIn("--machine", activation_gate.command)
        self.assertIn("laptop", activation_gate.command)
        self.assertNotIn("--execute", activation_gate.command)

    def test_desktop_validation_profile_runs_safety_checks_then_residual_regime_validation(self):
        plan = build_check_plan("python", profile="desktop-validation")

        names = [step.name for step in plan]
        self.assertEqual(
            names,
            [
                "unit_and_integration_tests",
                "compile_python",
                "project_audit",
                "readiness_check",
                "provider_status",
                "data_catalog",
                "cn_stock_factor_mining_startup_gate",
                "cn_stock_data_manifest",
                "data_quality_audit",
                "desktop_factor_validation",
                "desktop_walk_forward_progress_audit",
                "desktop_market_regime_coverage",
                "desktop_promotion_report",
                "desktop_validation_summary",
            ],
        )
        self.assertTrue(all(not step.uses_network for step in plan))
        startup_gate = next(step for step in plan if step.name == "cn_stock_factor_mining_startup_gate")
        self.assertEqual(
            startup_gate.command,
            [
                "python",
                "scripts/run_factor_mining_startup_gate.py",
                "--config",
                "configs/factor_mining_startup_cn_stock.json",
                "--machine",
                "office_desktop",
                "--task",
                "factor_validation",
                "--market",
                "CN",
                "--asset-type",
                "stock",
                "--confirm-start",
            ],
        )
        data_manifest = next(step for step in plan if step.name == "cn_stock_data_manifest")
        self.assertEqual(
            data_manifest.command,
            [
                "python",
                "scripts/run_cn_stock_data_manifest.py",
                "--data-root",
                "configs/cn_stock_authority_bars_2015_2025.json",
                "--market",
                "CN",
                "--output-dir",
                "data/reports/cn_stock_data_manifest",
            ],
        )
        data_quality = next(step for step in plan if step.name == "data_quality_audit")
        self.assertEqual(
            data_quality.command,
            [
                "python",
                "scripts/run_data_quality_audit.py",
                "--data-root",
                "configs/cn_stock_authority_bars_2015_2025.json",
                "--market",
                "CN",
                "--output-dir",
                "data/reports/data_quality_gap_audit_tushare_moneyflow_residual_regime",
            ],
        )
        self.assertEqual(plan[-5].command, ["python", "scripts/run_desktop_factor_validation.py"])
        self.assertEqual(
            plan[-4].command,
            [
                "python",
                "scripts/run_walk_forward_progress_audit.py",
                "--walk-forward-root",
                "data/reports/walk_forward_tushare_moneyflow_residual_regime",
                "--output-dir",
                "data/reports/walk_forward_progress_audit_tushare_moneyflow_residual_regime",
                "--expected-folds",
                "38",
            ],
        )
        self.assertEqual(
            plan[-3].command,
            [
                "python",
                "scripts/run_market_regime_coverage.py",
                "--regime-curve-glob",
                "data/reports/walk_forward_tushare_moneyflow_residual_regime/fold_*/test/*/regime_curve.csv",
                "--output-dir",
                "data/reports/market_regime_coverage_tushare_moneyflow_residual_regime",
                "--min-regimes",
                "2",
                "--min-rows-per-regime",
                "5",
                "--min-allowed-rows",
                "5",
                "--min-blocked-rows",
                "5",
                "--require-sufficient",
            ],
        )
        self.assertEqual(
            plan[-2].command,
            [
                "python",
                "scripts/run_promotion_report.py",
                "--config",
                "configs/promotion_gate_tushare_moneyflow_residual_regime.json",
            ],
        )
        self.assertEqual(plan[-1].command, ["python", "scripts/run_desktop_validation_summary.py"])

    def test_desktop_daily_basic_validation_profile_runs_soft_capacity_bucket_validation(self):
        plan = build_check_plan("python", profile="desktop-daily-basic-validation")

        names = [step.name for step in plan]
        self.assertEqual(
            names,
            [
                "unit_and_integration_tests",
                "compile_python",
                "project_audit",
                "readiness_check",
                "provider_status",
                "data_catalog",
                "cn_stock_factor_mining_startup_gate",
                "cn_stock_data_manifest",
                "data_quality_audit",
                "desktop_daily_basic_factor_validation",
                "desktop_daily_basic_walk_forward_progress_audit",
                "desktop_daily_basic_market_regime_coverage",
            ],
        )
        self.assertTrue(all(not step.uses_network for step in plan))
        data_quality = next(step for step in plan if step.name == "data_quality_audit")
        self.assertEqual(
            data_quality.command,
            [
                "python",
                "scripts/run_data_quality_audit.py",
                "--data-root",
                "configs/cn_stock_authority_bars_2015_2024.json",
                "--market",
                "CN",
                "--output-dir",
                "data/reports/data_quality_gap_audit_cn_stock_daily_basic_value_low_turnover_bucket_20260620",
            ],
        )
        data_manifest = next(step for step in plan if step.name == "cn_stock_data_manifest")
        self.assertEqual(
            data_manifest.command,
            [
                "python",
                "scripts/run_cn_stock_data_manifest.py",
                "--data-root",
                "configs/cn_stock_authority_bars_2015_2024.json",
                "--market",
                "CN",
                "--output-dir",
                "data/reports/cn_stock_data_manifest",
                "--daily-basic-root",
                "configs/cn_stock_authority_daily_basic_inputs_2015_2024.json",
            ],
        )
        self.assertEqual(
            plan[-3].command,
            [
                "python",
                "scripts/run_desktop_factor_validation.py",
                "--config",
                "configs/walk_forward_cn_stock_daily_basic_value_low_turnover_bucket_20260620.json",
                "--source",
                "processed-bars",
                "--data-root",
                "configs/cn_stock_authority_bars_2015_2024.json",
            ],
        )
        self.assertEqual(
            plan[-2].command,
            [
                "python",
                "scripts/run_walk_forward_progress_audit.py",
                "--walk-forward-root",
                "data/reports/walk_forward_cn_stock_daily_basic_value_low_turnover_bucket_20260620",
                "--output-dir",
                "data/reports/walk_forward_progress_audit_cn_stock_daily_basic_value_low_turnover_bucket_20260620",
                "--expected-folds",
                "38",
            ],
        )
        self.assertEqual(
            plan[-1].command,
            [
                "python",
                "scripts/run_market_regime_coverage.py",
                "--regime-curve-glob",
                "data/reports/walk_forward_cn_stock_daily_basic_value_low_turnover_bucket_20260620/fold_*/test/*/regime_curve.csv",
                "--output-dir",
                "data/reports/market_regime_coverage_cn_stock_daily_basic_value_low_turnover_bucket_20260620",
                "--min-regimes",
                "2",
                "--min-rows-per-regime",
                "5",
                "--min-allowed-rows",
                "5",
                "--min-blocked-rows",
                "5",
                "--require-sufficient",
            ],
        )

    def test_unknown_check_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported check profile"):
            build_check_plan("python", profile="moonbase")

    def test_child_env_prepends_source_tree_paths(self):
        env = run_checks.build_child_env({"PYTHONPATH": "legacy_path"})

        paths = env["PYTHONPATH"].split(os.pathsep)
        self.assertEqual(paths[:2], [str(run_checks.SRC_ROOT), str(run_checks.PROJECT_ROOT)])
        self.assertEqual(paths[2], "legacy_path")

    def test_execute_check_plan_uses_project_root_and_child_env(self):
        step = run_checks.CheckStep("demo", ["python", "-c", "pass"])

        with patch("scripts.run_checks.subprocess.run") as mocked_run:
            run_checks.execute_check_plan([step], env={"PYTHONPATH": "legacy_path"})

        mocked_run.assert_called_once()
        _, kwargs = mocked_run.call_args
        self.assertEqual(kwargs["cwd"], run_checks.PROJECT_ROOT)
        self.assertTrue(kwargs["check"])
        paths = kwargs["env"]["PYTHONPATH"].split(os.pathsep)
        self.assertEqual(paths[:2], [str(run_checks.SRC_ROOT), str(run_checks.PROJECT_ROOT)])


if __name__ == "__main__":
    unittest.main()
