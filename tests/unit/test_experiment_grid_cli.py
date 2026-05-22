import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_experiment_grid import run_grid


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


if __name__ == "__main__":
    unittest.main()
