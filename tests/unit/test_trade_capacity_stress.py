from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.trade_capacity_stress import (
    build_trade_capacity_stress,
    summarize_capacity_stress,
    write_trade_capacity_stress,
)


class TradeCapacityStressTest(unittest.TestCase):
    def test_summarize_capacity_stress_scales_allowed_entry_participation_only(self) -> None:
        trades = pd.DataFrame(
            {
                "participation_rate": [0.001, 0.02, 0.04],
                "entry_allowed": [True, True, False],
            }
        )

        rows = summarize_capacity_stress(
            trades,
            candidate_name="demo",
            multipliers=(1, 5),
            max_participation_rate=0.05,
        )

        self.assertEqual(rows[0]["aum_multiplier"], 1)
        self.assertEqual(rows[0]["candidate_name"], "demo")
        self.assertEqual(rows[0]["total_trade_rows"], 3)
        self.assertEqual(rows[0]["entry_allowed_rows"], 2)
        self.assertEqual(rows[0]["entry_blocked_rows"], 1)
        self.assertEqual(rows[0]["entry_blocked_rate"], 1 / 3)
        self.assertEqual(rows[0]["max_scaled_participation_rate"], 0.02)
        self.assertEqual(rows[0]["capacity_breach_trades"], 0)
        self.assertEqual(rows[0]["capacity_breach_rate"], 0.0)
        self.assertIs(rows[0]["capacity_safe"], True)

        self.assertEqual(rows[1]["aum_multiplier"], 5)
        self.assertEqual(rows[1]["max_scaled_participation_rate"], 0.10)
        self.assertEqual(rows[1]["capacity_breach_trades"], 1)
        self.assertEqual(rows[1]["capacity_breach_rate"], 0.5)
        self.assertIs(rows[1]["capacity_safe"], False)

    def test_build_and_write_trade_capacity_stress_outputs_summary_files(self) -> None:
        trades = pd.DataFrame({"participation_rate": [0.01, 0.02], "entry_allowed": [True, True]})

        audit = build_trade_capacity_stress(
            {"demo": trades},
            multipliers=(1, 4),
            max_participation_rate=0.05,
        )

        self.assertEqual(audit["summary"]["candidate_count"], 1)
        self.assertEqual(audit["summary"]["row_count"], 2)
        self.assertEqual(audit["summary"]["safe_rows"], 1)
        self.assertEqual(audit["summary"]["unsafe_rows"], 1)

        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_trade_capacity_stress(output_dir, audit)

            self.assertTrue((output_dir / "trade_capacity_stress_summary.json").exists())
            self.assertTrue((output_dir / "trade_capacity_stress_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
