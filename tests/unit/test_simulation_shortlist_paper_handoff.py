from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.simulation_shortlist_paper_handoff import (
    build_simulation_paper_handoff,
    write_simulation_paper_handoff,
)


class SimulationShortlistPaperHandoffTest(unittest.TestCase):
    def test_handoff_only_promotes_true_cohort_paper_ready_candidates(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            ready_path = root / "ready.csv"
            aggregate_path = root / "aggregate.csv"
            _write_returns(ready_path, [0.03, 0.02, -0.01, 0.02, 0.03, 0.01])
            _write_returns(aggregate_path, [0.05, 0.04, -0.01, 0.03, 0.04, 0.02])
            config = {
                "paper_simulation_handoff_candidates": [
                    _candidate(
                        "ready_cohort",
                        ready_path,
                        status="paper_simulation_cohort_entry_timed_candidate",
                        role="default_10bps",
                        paper_ready=True,
                        annualized=0.06,
                        max_drawdown=-0.20,
                        strict_pass=0.9,
                    ),
                    _candidate(
                        "aggregate_not_ready",
                        aggregate_path,
                        status="aggregate_entry_timed_research_observation_not_paper_ready",
                        role="research_reference",
                        paper_ready=False,
                        annualized=0.09,
                        max_drawdown=-0.19,
                        strict_pass=0.9,
                    ),
                ]
            }

            handoff = build_simulation_paper_handoff(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                max_user_drawdown=-0.30,
            )

            self.assertEqual(handoff["summary"]["ready_candidate_count"], 1)
            self.assertEqual(handoff["summary"]["blocked_candidate_count"], 1)
            self.assertEqual(handoff["summary"]["default_candidate_id"], "ready_cohort")
            rows = {row["candidate_id"]: row for row in handoff["candidates"]}
            self.assertEqual(rows["ready_cohort"]["handoff_status"], "ready_for_paper_simulation")
            self.assertEqual(rows["aggregate_not_ready"]["handoff_status"], "blocked")
            self.assertIn("not_true_cohort_entry_timed_candidate", rows["aggregate_not_ready"]["blockers"])
            self.assertIn("not_paper_ready", rows["aggregate_not_ready"]["blockers"])

    def test_handoff_blocks_candidates_that_breach_cost_or_drawdown_readiness(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "returns.csv"
            _write_returns(source, [0.20, -0.40, 0.04, 0.03])
            config = {
                "paper_simulation_handoff_candidates": [
                    _candidate(
                        "drawdown_breach",
                        source,
                        status="paper_simulation_cohort_entry_timed_candidate",
                        role="stress_30bps",
                        paper_ready=True,
                        annualized=0.04,
                        max_drawdown=-0.36,
                        strict_pass=0.7,
                    )
                ]
            }

            handoff = build_simulation_paper_handoff(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                max_user_drawdown=-0.30,
                min_oos_strict_pass_rate=0.75,
            )

            row = handoff["candidates"][0]
            self.assertEqual(row["handoff_status"], "blocked")
            self.assertIn("drawdown_below_user_limit", row["blockers"])
            self.assertIn("oos_strict_pass_rate_below_min", row["blockers"])
            self.assertIsNone(handoff["summary"]["default_candidate_id"])

    def test_handoff_separately_identifies_highest_return_ready_candidate(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            default_path = root / "default.csv"
            aggressive_path = root / "aggressive.csv"
            _write_returns(default_path, [0.02, 0.02, -0.01, 0.02, 0.02, 0.01])
            _write_returns(aggressive_path, [0.05, 0.04, -0.02, 0.04, 0.03, 0.02])
            config = {
                "paper_simulation_handoff_candidates": [
                    _candidate(
                        "default_lane",
                        default_path,
                        status="paper_simulation_cohort_entry_timed_candidate",
                        role="default_10bps",
                        paper_ready=True,
                        annualized=0.05,
                        max_drawdown=-0.10,
                        strict_pass=0.9,
                    ),
                    _candidate(
                        "aggressive_lane",
                        aggressive_path,
                        status="paper_simulation_cohort_entry_timed_candidate",
                        role="diagnostic",
                        paper_ready=True,
                        annualized=0.09,
                        max_drawdown=-0.22,
                        strict_pass=0.9,
                    ),
                ]
            }

            handoff = build_simulation_paper_handoff(
                config,
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
                max_user_drawdown=-0.30,
            )

            self.assertEqual(handoff["summary"]["default_candidate_id"], "default_lane")
            self.assertEqual(handoff["summary"]["primary_high_return_candidate_id"], "aggressive_lane")
            self.assertGreater(
                handoff["summary"]["primary_high_return_annualized_return"],
                handoff["candidates"][0]["computed_annualized_return"],
            )

    def test_write_handoff_outputs_json_csv_and_markdown(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ready.csv"
            output_dir = root / "handoff"
            _write_returns(source, [0.03, 0.02, -0.01, 0.02])
            handoff = build_simulation_paper_handoff(
                {
                    "paper_simulation_handoff_candidates": [
                        _candidate(
                            "ready_cohort",
                            source,
                            status="paper_simulation_cohort_entry_timed_candidate",
                            role="default_10bps",
                            paper_ready=True,
                            annualized=0.05,
                            max_drawdown=-0.15,
                            strict_pass=0.9,
                        )
                    ]
                },
                repo_root=root,
                periods_per_year=12.0,
                holding_period=1,
            )

            write_simulation_paper_handoff(output_dir, handoff)

            self.assertTrue((output_dir / "simulation_paper_handoff.json").exists())
            self.assertTrue((output_dir / "simulation_paper_handoff_candidates.csv").exists())
            self.assertTrue((output_dir / "simulation_paper_handoff.md").exists())


def _candidate(
    candidate_id: str,
    path: Path,
    *,
    status: str,
    role: str,
    paper_ready: bool,
    annualized: float,
    max_drawdown: float,
    strict_pass: float,
) -> dict:
    return {
        "id": candidate_id,
        "status": status,
        "role": role,
        "cost_rate": 0.001,
        "formula": candidate_id,
        "event_return_source": {
            "path": str(path),
            "date_column": "date",
            "return_column": "period_return",
        },
        "evidence": {
            "paper_ready": paper_ready,
            "full_sample_annualized_return": annualized,
            "full_sample_max_drawdown": max_drawdown,
            "mean_oos_annualized_return": annualized + 0.01,
            "oos_strict_pass_rate": strict_pass,
            "csi500_beta_hedged_annualized_return": annualized,
            "csi500_beta_hedged_max_drawdown": max_drawdown / 2,
        },
    }


def _write_returns(path: Path, returns: list[float]) -> None:
    dates = pd.date_range("2020-01-31", periods=len(returns), freq="ME")
    pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "period_return": returns}).to_csv(path, index=False)


if __name__ == "__main__":
    unittest.main()
