import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_same_parameter_full_sample_replay import run_same_parameter_full_sample_replay_from_files


class SameParameterReplayCliTests(unittest.TestCase):
    def test_cli_runner_loads_fixture_candidates_and_writes_replay_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_momentum_2_top1_cost0_reb1",
                        "market": "CN",
                        "factor_source": "technical",
                        "factor_name": "momentum_2",
                        "top_n": 1,
                        "cost_bps": 0.0,
                        "forward_horizon": 1,
                        "execution_lag": 1,
                        "rebalance_interval": 1,
                        "strict_split_status": "pass",
                        "strict_split_violations": 0,
                        "strict_split_folds": 1,
                    }
                ]
            ).to_csv(candidates, index=False)
            base_config = root / "base_config.json"
            base_config.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_source": "technical",
                        "factor_names": ["momentum_2"],
                        "factor_windows": [2],
                        "top_n_values": [1],
                        "cost_bps_values": [0],
                        "forward_horizon": 1,
                        "execution_lag": 1,
                        "rebalance_intervals": [1],
                        "min_trades": 1,
                        "write_case_artifacts": False,
                    }
                ),
                encoding="utf-8",
            )

            pack = run_same_parameter_full_sample_replay_from_files(
                candidates_csv=candidates,
                base_config_path=base_config,
                source="fixture",
                data_root=root / "unused",
                output_dir=root / "out",
                start_date="2024-01-02",
                end_date="2024-01-14",
            )

            self.assertEqual(pack["stage"], "same_parameter_full_sample_replay")
            self.assertEqual(pack["summary"]["candidates"], 1)
            self.assertTrue((root / "out" / "same_parameter_full_sample_replay.csv").exists())


if __name__ == "__main__":
    unittest.main()
