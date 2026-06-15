import tempfile
import unittest
from pathlib import Path

from quant_robot.audit.project_audit import collect_project_audit, render_markdown_report


class ProjectAuditTests(unittest.TestCase):
    def test_audit_flags_order_implementation_but_allows_boundary_docs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "docs").mkdir()
            (root / "src" / "danger.py").write_text("def place_order(order):\n    return order\n", encoding="utf-8")
            (root / "docs" / "safety.md").write_text("No broker connection and no live trading.\n", encoding="utf-8")

            audit = collect_project_audit(root)

            self.assertFalse(audit["safety"]["passes"])
            self.assertEqual(len(audit["safety"]["forbidden_hits"]), 1)
            self.assertEqual(audit["safety"]["forbidden_hits"][0]["path"], "src/danger.py")
            self.assertEqual(audit["safety"]["boundary_mentions"], 1)

    def test_audit_allows_explicitly_disabled_live_order_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "safe.py").write_text(
                "FIELDS = ('live_order_allowed',)\n"
                "def decision():\n"
                "    return {'live_order_allowed': False}\n",
                encoding="utf-8",
            )
            (root / "src" / "unsafe.py").write_text(
                "def decision():\n"
                "    payload = {}\n"
                "    payload['live_order_allowed'] = True\n"
                "    return {'live_order_allowed': True}\n",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            hits = audit["safety"]["forbidden_hits"]
            self.assertEqual([hit["path"] for hit in hits], ["src/unsafe.py", "src/unsafe.py"])
            self.assertTrue(all(hit["pattern"] == "live_order" for hit in hits))

    def test_audit_reports_mock_boundary_files_separately(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src" / "quant_robot" / "gui" / "fixtures").mkdir(parents=True)
            (root / "src" / "quant_robot" / "gui" / "fixtures" / "mock_data.py").write_text(
                "DATA_MODE = 'demo_fixture'\n",
                encoding="utf-8",
            )

            audit = collect_project_audit(root)

            self.assertIn("src/quant_robot/gui/fixtures/mock_data.py", audit["mock_boundaries"]["mock_files"])
            self.assertTrue(audit["mock_boundaries"]["passes"])

    def test_markdown_report_contains_core_sections(self):
        audit = {
            "summary": {"passes": True, "files_scanned": 2},
            "safety": {"passes": True, "forbidden_hits": [], "boundary_mentions": 1},
            "mock_boundaries": {"passes": True, "mock_files": ["src/mock_data.py"]},
            "real_data": {"tushare_ready": False, "parquet_ready": False},
        }

        report = render_markdown_report(audit)

        self.assertIn("# Quant Robot Project Audit", report)
        self.assertIn("Safety Boundary", report)
        self.assertIn("Mock Data Boundary", report)


if __name__ == "__main__":
    unittest.main()
