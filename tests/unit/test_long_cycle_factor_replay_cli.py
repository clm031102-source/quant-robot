import tempfile
import unittest
import json
from pathlib import Path

import pandas as pd

from scripts.run_long_cycle_factor_replay import run_long_cycle_factor_replay


class LongCycleFactorReplayCliTests(unittest.TestCase):
    def test_run_long_cycle_factor_replay_writes_blocked_pack_for_short_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            bars = root / "bars.csv"
            output = root / "out"
            pd.DataFrame(
                [
                    {
                        "case_id": "case_a",
                        "market": "CN",
                        "factor_name": "factor_x",
                        "top_n": 50,
                        "cost_bps": 10,
                        "sharpe": 4.2,
                        "source_report": "fixture",
                    }
                ]
            ).to_csv(candidates, index=False)
            pd.DataFrame(
                [
                    {"date": "2023-07-03", "asset_id": "CN_A", "market": "CN", "adj_close": 10.0},
                    {"date": "2024-01-02", "asset_id": "CN_A", "market": "CN", "adj_close": 11.0},
                ]
            ).to_csv(bars, index=False)

            pack = run_long_cycle_factor_replay(
                candidates_csv=candidates,
                bars_csv=bars,
                market="CN",
                required_start="2015-01-01",
                output_dir=output,
            )

            self.assertEqual(pack["coverage"]["status"], "insufficient")
            self.assertEqual(pack["summary"]["candidates"], 1)
            self.assertTrue((output / "long_cycle_replay_pack.json").exists())
            self.assertTrue((output / "candidate_decisions.csv").exists())

    def test_run_long_cycle_factor_replay_can_use_manifest_instead_of_bars_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            manifest = root / "manifest.json"
            output = root / "out"
            pd.DataFrame(
                [
                    {
                        "case_id": "case_a",
                        "market": "CN",
                        "factor_name": "factor_x",
                        "source_report": "fixture",
                    }
                ]
            ).to_csv(candidates, index=False)
            manifest.write_text(
                json.dumps(
                    {
                        "summary": {
                            "date_start": "2023-07-03",
                            "date_end": "2026-06-15",
                            "bar_rows": 8286202,
                            "bar_asset_ids": 5634,
                        }
                    }
                ),
                encoding="utf-8",
            )

            pack = run_long_cycle_factor_replay(
                candidates_csv=candidates,
                manifest_json=manifest,
                market="CN",
                required_start="2015-01-01",
                output_dir=output,
            )

            self.assertEqual(pack["coverage"]["bar_rows"], 8286202)
            self.assertEqual(pack["coverage"]["asset_ids"], 5634)
            self.assertEqual(pack["coverage"]["status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
