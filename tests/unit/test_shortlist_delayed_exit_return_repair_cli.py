from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd


class ShortlistDelayedExitReturnRepairCliTest(unittest.TestCase):
    def test_cli_writes_delayed_exit_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            trades = root / "trades.csv"
            bars = root / "bars.csv"
            masks = root / "masks.csv"
            output = root / "out"
            pd.DataFrame(
                {
                    "asset_id": ["DELAYED"],
                    "entry_date": ["2024-01-02"],
                    "exit_date": ["2024-01-04"],
                    "target_weight": [0.5],
                    "cost_rate": [0.001],
                    "entry_allowed": [True],
                }
            ).to_csv(trades, index=False)
            pd.DataFrame(
                {
                    "asset_id": ["DELAYED", "DELAYED"],
                    "date": ["2024-01-02", "2024-01-05"],
                    "adj_close": [10.0, 11.0],
                }
            ).to_csv(bars, index=False)
            pd.DataFrame(
                {
                    "asset_id": ["DELAYED", "DELAYED"],
                    "date": ["2024-01-04", "2024-01-05"],
                    "can_sell": [False, True],
                }
            ).to_csv(masks, index=False)

            completed = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_shortlist_delayed_exit_return_repair.py",
                    "--trades",
                    str(trades),
                    "--bars-source",
                    str(bars),
                    "--masks-source",
                    str(masks),
                    "--output-dir",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            payload = json.loads(completed.stdout)
            self.assertEqual(payload["summary"]["delayed_exit_trade_count"], 1)
            self.assertTrue((output / "delayed_exit_return_repair.json").exists())
            self.assertTrue((output / "delayed_exit_trade_rows.csv").exists())

    def test_cli_override_cost_rate_writes_recomputed_rows(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            trades = root / "trades.csv"
            bars = root / "bars.csv"
            masks = root / "masks.csv"
            output = root / "out"
            pd.DataFrame(
                {
                    "asset_id": ["DELAYED"],
                    "entry_date": ["2024-01-02"],
                    "exit_date": ["2024-01-04"],
                    "target_weight": [0.5],
                    "cost_rate": [0.001],
                    "entry_allowed": [True],
                }
            ).to_csv(trades, index=False)
            pd.DataFrame(
                {
                    "asset_id": ["DELAYED", "DELAYED"],
                    "date": ["2024-01-02", "2024-01-05"],
                    "adj_close": [10.0, 11.0],
                }
            ).to_csv(bars, index=False)
            pd.DataFrame(
                {
                    "asset_id": ["DELAYED", "DELAYED"],
                    "date": ["2024-01-04", "2024-01-05"],
                    "can_sell": [False, True],
                }
            ).to_csv(masks, index=False)

            subprocess.run(
                [
                    sys.executable,
                    "scripts/run_shortlist_delayed_exit_return_repair.py",
                    "--trades",
                    str(trades),
                    "--bars-source",
                    str(bars),
                    "--masks-source",
                    str(masks),
                    "--output-dir",
                    str(output),
                    "--override-cost-rate",
                    "0.003",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            rows = pd.read_csv(output / "delayed_exit_trade_rows.csv")
            self.assertAlmostEqual(float(rows.loc[0, "delayed_exit_weighted_return"]), 0.0485)


if __name__ == "__main__":
    unittest.main()
