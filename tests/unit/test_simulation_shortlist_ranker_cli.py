from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from scripts.run_simulation_shortlist_ranker import run_simulation_shortlist_ranker


class SimulationShortlistRankerCliTest(unittest.TestCase):
    def test_run_simulation_shortlist_ranker_writes_pack(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "returns.csv"
            config = root / "shortlist.json"
            output_dir = root / "ranking"
            pd.DataFrame(
                {
                    "date": ["2020-01-31", "2020-02-29", "2020-03-31", "2020-04-30"],
                    "period_return": [0.03, 0.02, -0.01, 0.03],
                }
            ).to_csv(source, index=False)
            config.write_text(
                json.dumps(
                    {
                        "simulation_candidates": [
                            {
                                "id": "candidate_a",
                                "formula": "demo",
                                "event_return_source": {"path": str(source), "return_column": "period_return"},
                                "evidence": {
                                    "mean_oos_annualized_return": 0.05,
                                    "oos_strict_pass_rate": 0.9,
                                    "csi500_beta_hedged_annualized_return": 0.04,
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            ranking = run_simulation_shortlist_ranker(
                config=config,
                repo_root=root,
                output_dir=output_dir,
                periods_per_year=12.0,
                holding_period=1,
            )

            self.assertEqual(ranking["summary"]["best_candidate"], "candidate_a")
            self.assertTrue((output_dir / "simulation_shortlist_ranking.json").exists())
            self.assertTrue((output_dir / "simulation_shortlist_ranking_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
