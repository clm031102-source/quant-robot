import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_profitability_quality_family_rejection_audit import (
    run_profitability_quality_family_rejection_audit_cli,
)


class ProfitabilityQualityFamilyRejectionAuditCliTests(unittest.TestCase):
    def test_cli_writes_rejection_audit_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            screen_path = root / "controlled_ic.json"
            screen_path.write_text(
                json.dumps(
                    {
                        "stage": "profitability_quality_controlled_ic_screen",
                        "summary": {
                            "passes": True,
                            "candidate_count": 14,
                            "test_count": 28,
                            "ic_observation_count": 1204,
                            "bonferroni_significant": 0,
                            "fdr_significant": 0,
                            "research_lead_count": 0,
                            "aligned_rows": 117394,
                            "blockers": [],
                        },
                        "multiple_testing": {"test_count": 28, "bonferroni_alpha": 0.0017857142857142859},
                        "promotion_policy": {"portfolio_backtest_allowed": False, "promotion_allowed": False},
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "audit"

            audit = run_profitability_quality_family_rejection_audit_cli(
                controlled_ic_json=screen_path,
                output_dir=output_dir,
                source_report="docs/research/round98.md",
                rounds=[97, 98, 99],
            )

            self.assertEqual(audit["status"], "family_rejected_rotate_after_sync")
            self.assertTrue((output_dir / "profitability_quality_family_rejection_audit.json").exists())
            self.assertTrue((output_dir / "profitability_quality_family_rejection_audit.md").exists())
            self.assertTrue((output_dir / "profitability_quality_family_rejection_requirements.csv").exists())
            payload = json.loads(
                (output_dir / "profitability_quality_family_rejection_audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["decision"]["immediate_next_direction"], "round100_lightweight_stage_report_and_github_safe_sync")
            self.assertFalse(payload["live_boundary_allowed"])


if __name__ == "__main__":
    unittest.main()
