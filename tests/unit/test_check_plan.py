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
                "data_catalog",
                "fixture_research",
                "research_pipeline",
                "experiment_grid",
                "walk_forward",
            ],
        )
        self.assertTrue(all(not step.uses_network for step in plan))
        self.assertIn("-m", plan[0].command)
        self.assertIn("scripts/run_project_audit.py", plan[2].command)
        self.assertIn("scripts/show_provider_status.py", plan[4].command)
        self.assertIn("--summary-only", plan[5].command)
        self.assertIn("scripts/run_experiment_grid.py", plan[8].command)
        self.assertIn("scripts/run_walk_forward.py", plan[9].command)


if __name__ == "__main__":
    unittest.main()
