import tempfile
import unittest
from pathlib import Path

from scripts.run_paper_simulation import run_simulation


class PaperSimulationCliTests(unittest.TestCase):
    def test_run_simulation_writes_local_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_simulation(
                source="fixture",
                market="CN",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=1,
                start_date="2024-01-04",
                end_date="2024-01-10",
                output_dir=Path(tmp),
            )

            self.assertGreater(len(result["fills"]), 0)
            self.assertTrue((Path(tmp) / "intents.csv").exists())
            self.assertTrue((Path(tmp) / "fills.csv").exists())
            self.assertTrue((Path(tmp) / "equity_curve.csv").exists())
            self.assertTrue((Path(tmp) / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
