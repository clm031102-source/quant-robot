import unittest

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
        self.assertIn("scripts/run_risk_candidate_selector.py", plan[32].command)
        self.assertIn("scripts/run_constrained_candidate_search.py", plan[33].command)
        self.assertIn("scripts/run_paper_profile_optimizer.py", plan[34].command)


if __name__ == "__main__":
    unittest.main()
