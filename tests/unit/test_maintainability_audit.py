import tempfile
import unittest
from pathlib import Path

from scripts.run_maintainability_audit import (
    collect_maintainability_audit,
    render_maintainability_markdown,
)


class MaintainabilityAuditTests(unittest.TestCase):
    def test_repository_audit_reports_large_modules_and_test_topology_debt(self) -> None:
        audit = collect_maintainability_audit(".")

        self.assertEqual(audit["stage"], "maintainability_baseline_audit")
        self.assertTrue(audit["decision"]["maintainability_baseline_passed"])
        self.assertGreaterEqual(audit["summary"]["oversized_module_count"], 10)
        self.assertEqual(
            audit["summary"]["largest_module"]["path"],
            "src/quant_robot/ops/daily_trade_advisory.py",
        )
        self.assertGreaterEqual(audit["summary"]["largest_module"]["lines"], 13_000)
        self.assertIn("e2e_test_layer_missing", audit["decision"]["known_debt"])

    def test_integration_debt_clears_when_test_layer_reaches_ten_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            integration = root / "tests" / "integration"
            integration.mkdir(parents=True)
            for index in range(9):
                (integration / f"test_case_{index}.py").write_text("", encoding="utf-8")

            sparse = collect_maintainability_audit(root)
            self.assertEqual(sparse["test_topology"]["integration_test_files"], 9)
            self.assertIn("integration_test_layer_sparse", sparse["decision"]["known_debt"])

            (integration / "test_case_9.py").write_text("", encoding="utf-8")
            sufficient = collect_maintainability_audit(root)
            self.assertEqual(sufficient["test_topology"]["integration_test_files"], 10)
            self.assertNotIn("integration_test_layer_sparse", sufficient["decision"]["known_debt"])
            self.assertTrue(sufficient["decision"]["maintainability_baseline_passed"])

    def test_audit_blocks_growth_in_baselined_and_new_oversized_modules(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "src" / "quant_robot"
            source.mkdir(parents=True)
            (source / "legacy.py").write_text("# 1\n# 2\n# 3\n# 4\n", encoding="utf-8")
            (source / "new_large.py").write_text("# 1\n# 2\n# 3\n# 4\n", encoding="utf-8")

            audit = collect_maintainability_audit(
                root,
                oversized_threshold=3,
                module_line_baselines={"src/quant_robot/legacy.py": 3},
                min_non_unit_test_files=0,
            )

        self.assertFalse(audit["decision"]["maintainability_baseline_passed"])
        self.assertIn("module_line_baseline_exceeded:src/quant_robot/legacy.py", audit["decision"]["blockers"])
        self.assertIn("new_oversized_module:src/quant_robot/new_large.py", audit["decision"]["blockers"])

    def test_markdown_distinguishes_known_debt_from_regressions(self) -> None:
        audit = collect_maintainability_audit(".")

        markdown = render_maintainability_markdown(audit)

        self.assertIn("Known Debt", markdown)
        self.assertIn("Baseline Regressions", markdown)
        self.assertIn("daily_trade_advisory.py", markdown)


if __name__ == "__main__":
    unittest.main()
