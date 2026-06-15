import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_paper_observation import run_paper_observation


class PaperObservationCliTests(unittest.TestCase):
    def test_run_paper_observation_writes_pack_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case_dir = root / "case_a"
            case_dir.mkdir()
            (case_dir / "manifest.json").write_text(
                json.dumps(
                    {
                        "data_mode": "research",
                        "request": {"case_id": "case_a", "risk_profile_id": "balanced", "market": "CN_ETF"},
                        "metrics": {"sharpe": 0.6, "total_return": 0.1, "max_equity_drawdown": -0.08},
                    }
                ),
                encoding="utf-8",
            )
            pd.DataFrame(
                [
                    {"date": "2024-01-02", "equity": 100000.0},
                    {"date": "2024-01-05", "equity": 110000.0},
                ]
            ).to_csv(case_dir / "equity_curve.csv", index=False)
            pd.DataFrame([{"date": "2024-01-04", "event_type": "drawdown_guard_triggered"}]).to_csv(
                case_dir / "guard_events.csv",
                index=False,
            )
            pd.DataFrame([{"date": "2024-01-05", "blocked_reason": "limit_up"}]).to_csv(
                case_dir / "execution_events.csv",
                index=False,
            )
            summary_path = root / "paper_batch_summary.json"
            summary_path.write_text(
                json.dumps(
                    {
                        "summary": {"cases": 1, "completed": 1, "failed": 0, "skipped": 0},
                        "candidates": [
                            {
                                "case_id": "case_a",
                                "status": "completed",
                                "manifest_path": str(case_dir / "manifest.json"),
                                "output_dir": str(case_dir),
                                "risk_profile_id": "balanced",
                                "sharpe": 0.6,
                                "total_return": 0.1,
                                "max_equity_drawdown": -0.08,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "paper_observation"

            pack = run_paper_observation(paper_batch_summary=summary_path, output_dir=output_dir)

            self.assertEqual(pack["stage"], "phase_3_3_paper_observation_extension")
            self.assertTrue((output_dir / "paper_observation_pack.json").exists())
            self.assertTrue((output_dir / "paper_observation_pack.md").exists())
            self.assertTrue((output_dir / "paper_observation_candidates.csv").exists())
            self.assertTrue((output_dir / "paper_observation_risk_profiles.csv").exists())
            self.assertTrue((output_dir / "paper_observation_trend.csv").exists())
            payload = json.loads((output_dir / "paper_observation_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["observed_candidates"], 1)


if __name__ == "__main__":
    unittest.main()
