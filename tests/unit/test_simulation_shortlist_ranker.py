from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.simulation_shortlist_ranker import build_simulation_shortlist_ranking


class SimulationShortlistRankerTest(unittest.TestCase):
    def test_ranking_prefers_robust_high_return_candidate_within_user_drawdown_limit(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            strong_path = root / "strong.csv"
            weak_path = root / "weak.csv"
            _write_returns(strong_path, [0.05, 0.04, -0.02, 0.04, 0.03, 0.02])
            _write_returns(weak_path, [0.01, 0.01, -0.005, 0.01, 0.01, 0.01])
            config = {
                "simulation_candidates": [
                    _candidate("weak", weak_path, mean_oos=0.03, strict_pass=0.8, hedged_ann=0.03, hedged_dd=-0.04),
                    _candidate("strong", strong_path, mean_oos=0.08, strict_pass=0.9, hedged_ann=0.07, hedged_dd=-0.10),
                ]
            }

            result = build_simulation_shortlist_ranking(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                max_user_drawdown=-0.30,
            )

            self.assertEqual(result["summary"]["best_candidate"], "strong")
            self.assertEqual(result["rows"][0]["candidate_id"], "strong")
            self.assertEqual(result["rows"][0]["selection_status"], "simulation_observation_candidate")
            self.assertGreater(result["rows"][0]["score"], result["rows"][1]["score"])

    def test_ranking_blocks_candidate_when_drawdown_exceeds_user_limit(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "large_drawdown.csv"
            _write_returns(path, [0.60, -0.40, 0.30, 0.20])
            config = {
                "simulation_candidates": [
                    _candidate("large_drawdown", path, mean_oos=0.10, strict_pass=0.9, hedged_ann=0.08, hedged_dd=-0.28)
                ]
            }

            result = build_simulation_shortlist_ranking(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                max_user_drawdown=-0.30,
            )

            self.assertEqual(result["summary"]["eligible_candidate_count"], 0)
            self.assertIn("drawdown_below_user_limit", result["rows"][0]["blockers"])
            self.assertEqual(result["rows"][0]["selection_status"], "blocked")

    def test_ranking_marks_near_duplicate_return_streams(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_path = root / "first.csv"
            second_path = root / "second.csv"
            _write_returns(first_path, [0.03, 0.02, -0.01, 0.03, 0.02, 0.01])
            _write_returns(second_path, [0.03, 0.02, -0.01, 0.03, 0.02, 0.01])
            config = {
                "simulation_candidates": [
                    _candidate("first", first_path, mean_oos=0.05, strict_pass=0.9, hedged_ann=0.04, hedged_dd=-0.07),
                    _candidate("second", second_path, mean_oos=0.07, strict_pass=0.9, hedged_ann=0.06, hedged_dd=-0.06),
                ]
            }

            result = build_simulation_shortlist_ranking(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                duplicate_correlation=0.98,
            )

            rows = {row["candidate_id"]: row for row in result["rows"]}
            self.assertEqual(rows["second"]["selection_status"], "simulation_observation_candidate")
            self.assertEqual(rows["first"]["selection_status"], "duplicate")
            self.assertEqual(rows["first"]["duplicate_of"], "second")
            self.assertEqual(result["summary"]["duplicate_candidate_count"], 1)


def _candidate(
    candidate_id: str,
    path: Path,
    *,
    mean_oos: float,
    strict_pass: float,
    hedged_ann: float,
    hedged_dd: float,
) -> dict:
    return {
        "id": candidate_id,
        "status": "simulation_shortlist",
        "formula": candidate_id,
        "event_return_source": {
            "path": str(path),
            "date_column": "date",
            "return_column": "period_return",
        },
        "evidence": {
            "mean_oos_annualized_return": mean_oos,
            "oos_strict_pass_rate": strict_pass,
            "csi500_beta_hedged_annualized_return": hedged_ann,
            "csi500_beta_hedged_max_drawdown": hedged_dd,
        },
    }


def _write_returns(path: Path, returns: list[float]) -> None:
    dates = pd.date_range("2020-01-31", periods=len(returns), freq="ME")
    pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "period_return": returns}).to_csv(path, index=False)


if __name__ == "__main__":
    unittest.main()
