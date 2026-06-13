import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_constrained_candidate_search import run_constrained_candidate_search


class ConstrainedCandidateSearchCliTests(unittest.TestCase):
    def test_run_constrained_candidate_search_orchestrates_local_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "constrained_search.json"
            output_dir = root / "search"
            walk_output = root / "walk"
            paper_output = root / "paper"
            promotion_output = root / "promotion"
            risk_output = root / "risk"
            config_path.write_text(
                json.dumps(
                    {
                        "source": "processed-bars",
                        "data_root": str(root / "bars"),
                        "walk_forward_config": str(root / "walk.json"),
                        "walk_forward_output_dir": str(walk_output),
                        "paper_batch_config": str(root / "paper.json"),
                        "paper_batch_output_dir": str(paper_output),
                        "promotion_config": str(root / "promotion.json"),
                        "promotion_output_dir": str(promotion_output),
                        "daily_ops_pack": str(root / "daily.json"),
                        "risk_candidate_output_dir": str(risk_output),
                        "output_dir": str(output_dir),
                        "max_drawdown_limit": 0.2,
                        "min_walk_forward_sharpe": 0.3,
                        "min_relative_return": 0.0,
                        "min_paper_sharpe": 0.5,
                        "min_trades": 20,
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.run_constrained_candidate_search.run_walk_forward") as walk_mock,
                patch("scripts.run_constrained_candidate_search.run_paper_batch") as paper_mock,
                patch("scripts.run_constrained_candidate_search.run_promotion_report") as promotion_mock,
                patch("scripts.run_constrained_candidate_search.run_risk_candidate_selector") as risk_mock,
            ):
                walk_mock.return_value = {"summary": {"cases": 12, "accepted": 2}, "leaderboard": []}
                paper_mock.return_value = {"summary": {"cases": 2, "completed": 2, "skipped": 10}}
                promotion_mock.return_value = {"summary": {"candidates": 12, "paper_ready": 1}, "candidates": []}
                risk_mock.return_value = {
                    "selection_status": "risk_candidate_selected",
                    "summary": {"risk_eligible_candidates": 1, "candidates": 12},
                    "selected_candidate": {"case_id": "case_a"},
                }

                pack = run_constrained_candidate_search(config_path)

            walk_mock.assert_called_once_with(
                config_path=root / "walk.json",
                source="processed-bars",
                data_root=root / "bars",
                output_dir=walk_output,
            )
            paper_mock.assert_called_once_with(config_path=root / "paper.json", output_dir=paper_output)
            promotion_mock.assert_called_once_with(config_path=root / "promotion.json", output_dir=promotion_output)
            risk_mock.assert_called_once_with(
                promotion_report=promotion_output / "promotion_report.json",
                daily_ops_pack=root / "daily.json",
                output_dir=risk_output,
                max_drawdown_limit=0.2,
                min_walk_forward_sharpe=0.3,
                min_relative_return=0.0,
                min_paper_sharpe=0.5,
                min_trades=20,
            )
            self.assertEqual(pack["stage"], "phase_5_2_constrained_candidate_search")
            self.assertEqual(pack["selection_status"], "risk_candidate_selected")
            self.assertEqual(pack["selected_candidate"]["case_id"], "case_a")
            self.assertEqual(pack["summary"]["risk_eligible_candidates"], 1)
            self.assertTrue((output_dir / "constrained_candidate_search_pack.json").exists())
            self.assertTrue((output_dir / "constrained_candidate_search_pack.md").exists())

    def test_run_constrained_candidate_search_reuses_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "search"
            walk_output = root / "walk"
            paper_output = root / "paper"
            promotion_output = root / "promotion"
            risk_output = root / "risk"
            walk_output.mkdir()
            paper_output.mkdir()
            promotion_output.mkdir()
            risk_output.mkdir()
            (walk_output / "manifest.json").write_text(json.dumps({"summary": {"cases": 3, "accepted": 1, "rejected": 2}}), encoding="utf-8")
            (paper_output / "paper_batch_summary.json").write_text(json.dumps({"summary": {"cases": 3, "completed": 1, "skipped": 2}}), encoding="utf-8")
            (promotion_output / "promotion_report.json").write_text(json.dumps({"summary": {"candidates": 3, "paper_ready": 0}}), encoding="utf-8")
            (risk_output / "risk_candidate_pack.json").write_text(
                json.dumps(
                    {
                        "selection_status": "no_risk_eligible_candidate",
                        "summary": {"candidates": 3, "risk_eligible_candidates": 0, "rejected_candidates": 3},
                        "selected_candidate": None,
                        "policy": {"max_drawdown_limit": -0.2, "min_paper_sharpe": 0.5},
                        "candidates": [
                            {
                                "case_id": "case_a",
                                "walk_forward_status": "accepted",
                                "walk_forward_sharpe": 0.7,
                                "walk_forward_relative_return": 0.02,
                                "walk_forward_max_drawdown": -0.18,
                                "paper_matched": True,
                                "paper_sharpe": 0.47,
                                "paper_max_drawdown": -0.15,
                                "paper_total_return": 0.2,
                                "duplicate_of": None,
                                "rejection_reasons": ["paper_sharpe_below_min"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            config_path = root / "constrained_search.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_output_dir": str(walk_output),
                        "paper_batch_output_dir": str(paper_output),
                        "promotion_output_dir": str(promotion_output),
                        "risk_candidate_output_dir": str(risk_output),
                        "output_dir": str(output_dir),
                        "reuse_existing_artifacts": True,
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.run_constrained_candidate_search.run_walk_forward") as walk_mock,
                patch("scripts.run_constrained_candidate_search.run_paper_batch") as paper_mock,
                patch("scripts.run_constrained_candidate_search.run_promotion_report") as promotion_mock,
                patch("scripts.run_constrained_candidate_search.run_risk_candidate_selector") as risk_mock,
            ):
                pack = run_constrained_candidate_search(config_path)

            walk_mock.assert_not_called()
            paper_mock.assert_not_called()
            promotion_mock.assert_not_called()
            risk_mock.assert_not_called()
            self.assertEqual(pack["selection_status"], "no_risk_eligible_candidate")
            self.assertEqual(pack["summary"]["walk_forward_accepted"], 1)
            self.assertEqual(pack["summary"]["frontier_candidates"], 1)
            self.assertEqual(pack["frontier_candidates"][0]["case_id"], "case_a")


if __name__ == "__main__":
    unittest.main()
