from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from scripts.run_simulation_shortlist_paper_handoff import run_simulation_shortlist_paper_handoff


class SimulationShortlistPaperHandoffCliTest(unittest.TestCase):
    def test_run_simulation_shortlist_paper_handoff_writes_pack(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "ready.csv"
            config = root / "shortlist.json"
            output_dir = root / "handoff"
            pd.DataFrame(
                {
                    "date": ["2020-01-31", "2020-02-29", "2020-03-31", "2020-04-30"],
                    "period_return": [0.03, 0.02, -0.01, 0.03],
                }
            ).to_csv(source, index=False)
            config.write_text(
                json.dumps(
                    {
                        "paper_simulation_handoff_candidates": [
                            {
                                "id": "ready_cohort",
                                "status": "paper_simulation_cohort_entry_timed_candidate",
                                "role": "default_10bps",
                                "formula": "demo",
                                "event_return_source": {
                                    "path": str(source),
                                    "date_column": "date",
                                    "return_column": "period_return",
                                },
                                "evidence": {
                                    "paper_ready": True,
                                    "full_sample_annualized_return": 0.05,
                                    "full_sample_max_drawdown": -0.12,
                                    "mean_oos_annualized_return": 0.06,
                                    "oos_strict_pass_rate": 0.9,
                                    "csi500_beta_hedged_annualized_return": 0.05,
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            handoff = run_simulation_shortlist_paper_handoff(
                config=config,
                repo_root=root,
                output_dir=output_dir,
                periods_per_year=12.0,
                holding_period=1,
            )

            self.assertEqual(handoff["summary"]["default_candidate_id"], "ready_cohort")
            self.assertTrue((output_dir / "simulation_paper_handoff.json").exists())
            self.assertTrue((output_dir / "simulation_paper_handoff_candidates.csv").exists())
            self.assertTrue((output_dir / "simulation_paper_handoff.md").exists())


if __name__ == "__main__":
    unittest.main()
