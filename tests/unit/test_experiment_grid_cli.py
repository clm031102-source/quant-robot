import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_experiment_grid import assert_grid_succeeded, run_grid


class ExperimentGridCliTests(unittest.TestCase):
    def test_run_grid_uses_json_config_and_fixture_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "grid.json"
            output_dir = Path(tmp) / "reports"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_names": ["momentum_2"],
                        "factor_windows": [2],
                        "top_n_values": [1],
                        "cost_bps_values": [0],
                        "output_dir": str(output_dir),
                    }
                ),
                encoding="utf-8",
            )

            result = run_grid(config_path=config_path, source="fixture")

            self.assertEqual(result["summary"]["cases"], 1)
            self.assertTrue((output_dir / "leaderboard.csv").exists())

    def test_assert_grid_succeeded_fails_when_cases_failed(self):
        result = {
            "summary": {"cases": 1, "completed": 0, "failed": 1, "no_trades": 0},
            "leaderboard": [{"case_id": "bad_case", "status": "failed", "error": "top_n must be positive"}],
        }

        with self.assertRaisesRegex(RuntimeError, "experiment grid failed"):
            assert_grid_succeeded(result)

    def test_assert_grid_succeeded_fails_when_no_case_completed(self):
        result = {
            "summary": {"cases": 1, "completed": 0, "failed": 0, "no_trades": 1},
            "leaderboard": [{"case_id": "empty_case", "status": "no_trades", "error": None}],
        }

        with self.assertRaisesRegex(RuntimeError, "no completed experiment cases"):
            assert_grid_succeeded(result)


if __name__ == "__main__":
    unittest.main()
