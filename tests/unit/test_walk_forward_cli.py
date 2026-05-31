import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_walk_forward import assert_walk_forward_succeeded, run_walk_forward


class WalkForwardCliTests(unittest.TestCase):
    def test_run_walk_forward_uses_config_and_fixture_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "wf"
            config_path = Path(tmp) / "walk_forward.json"
            config_path.write_text(
                json.dumps(
                    {
                        "split_date": "2024-01-08",
                        "output_dir": str(output_dir),
                        "experiment_grid": {
                            "markets": ["CN"],
                            "factor_names": ["momentum_2"],
                            "factor_windows": [2],
                            "top_n_values": [1],
                            "cost_bps_values": [0],
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = run_walk_forward(config_path=config_path, source="fixture")

            self.assertEqual(result["summary"]["cases"], 1)
            self.assertTrue((output_dir / "walk_forward_leaderboard.csv").exists())

    def test_assert_walk_forward_succeeded_fails_when_no_case_is_accepted(self):
        result = {
            "summary": {"cases": 1, "accepted": 0, "rejected": 1},
            "leaderboard": [{"case_id": "weak_case", "train_status": "completed", "test_status": "completed"}],
        }

        with self.assertRaisesRegex(RuntimeError, "no accepted walk-forward cases"):
            assert_walk_forward_succeeded(result)

    def test_assert_walk_forward_succeeded_fails_when_underlying_grid_failed(self):
        result = {
            "summary": {"cases": 1, "accepted": 0, "rejected": 1},
            "leaderboard": [{"case_id": "bad_case", "train_status": "completed", "test_status": "failed"}],
        }

        with self.assertRaisesRegex(RuntimeError, "walk-forward grid failures"):
            assert_walk_forward_succeeded(result)


if __name__ == "__main__":
    unittest.main()
