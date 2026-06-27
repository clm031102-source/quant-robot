from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from quant_robot.ops.simulation_shortlist_check import validate_simulation_shortlist_config


class SimulationShortlistCheckTest(unittest.TestCase):
    def test_validate_simulation_shortlist_config_accepts_sealed_config_with_existing_docs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            doc = root / "docs" / "research" / "ok.md"
            doc.parent.mkdir(parents=True)
            doc.write_text("# ok\n", encoding="utf-8")
            config = {
                "final_holdout_2026": {"status": "sealed", "read_once_required": True},
                "simulation_candidates": [
                    {"id": "primary", "status": "shortlist", "formula": "demo", "evidence": {"ann": 0.1}}
                ],
                "raw_generation_policy": {
                    "parity_gate_required": True,
                    "simulation_event_source_policy": "use_frozen_validated_event_sources_until_raw_generation_parity_passes",
                    "blocked_generated_event_sources": [{"path": "data/reports/generated.csv", "status": "blocked"}],
                },
                "source_docs": ["docs/research/ok.md"],
                "superseded_outputs": [{"path": "data/reports/bad", "reason": "superseded"}],
            }

            result = validate_simulation_shortlist_config(config, repo_root=root)

            self.assertEqual(result["blockers"], [])
            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertEqual(result["summary"]["source_doc_count"], 1)

    def test_validate_simulation_shortlist_config_blocks_unsealed_holdout_and_superseded_sources(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {
                "final_holdout_2026": {"status": "open", "read_once_required": False},
                "simulation_candidates": [{"id": "primary", "status": "shortlist"}],
                "source_docs": ["data/reports/bad"],
                "superseded_outputs": [{"path": "data/reports/bad", "reason": "superseded"}],
            }

            result = validate_simulation_shortlist_config(config, repo_root=root)

            self.assertIn("final_holdout_2026_not_sealed", result["blockers"])
            self.assertIn("final_holdout_2026_read_once_not_required", result["blockers"])
            self.assertIn("source_docs_include_superseded_output:data/reports/bad", result["blockers"])
            self.assertIn("candidate_missing_formula:primary", result["blockers"])
            self.assertIn("candidate_missing_evidence:primary", result["blockers"])
            self.assertIn("raw_generation_policy_missing_or_invalid", result["blockers"])

    def test_validate_simulation_shortlist_config_blocks_unapproved_raw_generated_event_source(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {
                "final_holdout_2026": {"status": "sealed", "read_once_required": True},
                "simulation_candidates": [
                    {
                        "id": "primary",
                        "status": "shortlist",
                        "formula": "demo",
                        "event_return_source": {"path": "data/reports/generated.csv"},
                        "evidence": {"ann": 0.1},
                    }
                ],
                "raw_generation_policy": {
                    "parity_gate_required": True,
                    "simulation_event_source_policy": "use_frozen_validated_event_sources_until_raw_generation_parity_passes",
                    "blocked_generated_event_sources": [{"path": "data/reports/generated.csv", "status": "blocked"}],
                },
                "source_docs": [],
                "superseded_outputs": [],
            }

            result = validate_simulation_shortlist_config(config, repo_root=root)

            self.assertIn("candidate_uses_blocked_generated_event_source:primary", result["blockers"])


if __name__ == "__main__":
    unittest.main()
