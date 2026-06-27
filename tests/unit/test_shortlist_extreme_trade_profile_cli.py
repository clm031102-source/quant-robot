from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd


class ShortlistExtremeTradeProfileCliTest(unittest.TestCase):
    def test_cli_writes_profile_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            trades = root / "trades.csv"
            output = root / "out"
            pd.DataFrame(
                {
                    "entry_date": ["2024-01-02", "2024-01-02"],
                    "exit_date": ["2024-01-22", "2024-01-22"],
                    "asset_id": ["CN_XSHG_688001", "CN_XSHG_600001"],
                    "gross_return": [0.8, 0.1],
                    "final_return_contribution": [0.01, 0.001],
                    "final_target_weight": [0.01, 0.01],
                    "stock_market": ["STAR", "MAIN"],
                    "entry_amount": [1_000_000.0, 10_000_000.0],
                }
            ).to_csv(trades, index=False)

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_shortlist_extreme_trade_profile.py",
                    "--trades",
                    str(trades),
                    "--group-column",
                    "stock_market",
                    "--numeric-column",
                    "entry_amount",
                    "--threshold",
                    "0.5",
                    "--min-group-extreme-count",
                    "1",
                    "--output-dir",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["summary"]["extreme_trade_count"], 1)
            self.assertTrue((output / "extreme_trade_profile.json").exists())
            self.assertTrue((output / "extreme_trade_group_profile.csv").exists())


if __name__ == "__main__":
    unittest.main()
