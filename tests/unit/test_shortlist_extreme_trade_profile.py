from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_extreme_trade_profile import (
    build_extreme_trade_profile,
    write_extreme_trade_profile,
)


class ShortlistExtremeTradeProfileTest(unittest.TestCase):
    def test_profiles_extreme_trades_by_entry_known_groups_and_ignores_inactive_rows(self) -> None:
        audit = build_extreme_trade_profile(
            _trades(),
            group_columns=("stock_market", "industry"),
            numeric_columns=("entry_amount", "turnover_rate_f"),
            threshold=0.5,
            min_group_extreme_count=1,
            min_extreme_rate_lift=1.5,
        )

        self.assertEqual(audit["summary"]["active_trade_count"], 3)
        self.assertEqual(audit["summary"]["extreme_trade_count"], 1)
        self.assertAlmostEqual(audit["summary"]["extreme_trade_rate"], 1.0 / 3.0)

        group_rows = pd.DataFrame(audit["group_profile_rows"])
        star = group_rows[
            (group_rows["group_column"] == "stock_market")
            & (group_rows["group_value"] == "STAR")
        ].iloc[0]
        self.assertEqual(int(star["trade_count"]), 2)
        self.assertEqual(int(star["extreme_trade_count"]), 1)
        self.assertAlmostEqual(float(star["extreme_rate_lift"]), 1.5)
        self.assertTrue(bool(star["risk_candidate"]))

        numeric_rows = pd.DataFrame(audit["numeric_profile_rows"])
        turnover = numeric_rows[numeric_rows["numeric_column"] == "turnover_rate_f"].iloc[0]
        self.assertAlmostEqual(float(turnover["extreme_mean"]), 8.0)
        self.assertAlmostEqual(float(turnover["non_extreme_mean"]), 4.0)

        top = audit["top_extreme_trade_rows"][0]
        self.assertEqual(top["asset_id"], "CN_XSHG_688001")
        self.assertEqual(top["stock_market"], "STAR")

    def test_writer_outputs_json_and_csv_files(self) -> None:
        with TemporaryDirectory() as tmp:
            audit = build_extreme_trade_profile(
                _trades(),
                group_columns=("stock_market",),
                numeric_columns=("entry_amount",),
                threshold=0.5,
            )

            write_extreme_trade_profile(tmp, audit)

            output = Path(tmp)
            self.assertTrue((output / "extreme_trade_profile.json").exists())
            self.assertTrue((output / "extreme_trade_group_profile.csv").exists())
            self.assertTrue((output / "extreme_trade_numeric_profile.csv").exists())
            self.assertTrue((output / "top_extreme_trade_rows.csv").exists())


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal_date": "2024-01-01",
                "entry_date": "2024-01-02",
                "exit_date": "2024-01-22",
                "asset_id": "CN_XSHG_688001",
                "gross_return": 0.8,
                "final_return_contribution": 0.01,
                "final_target_weight": 0.01,
                "entry_amount": 1_000_000.0,
                "turnover_rate_f": 8.0,
                "stock_market": "STAR",
                "industry": "tech",
            },
            {
                "signal_date": "2024-01-01",
                "entry_date": "2024-01-02",
                "exit_date": "2024-01-22",
                "asset_id": "CN_XSHG_688002",
                "gross_return": 0.1,
                "final_return_contribution": 0.001,
                "final_target_weight": 0.01,
                "entry_amount": 1_200_000.0,
                "turnover_rate_f": 7.0,
                "stock_market": "STAR",
                "industry": "tech",
            },
            {
                "signal_date": "2024-01-01",
                "entry_date": "2024-01-02",
                "exit_date": "2024-01-22",
                "asset_id": "CN_XSHG_600001",
                "gross_return": 0.05,
                "final_return_contribution": 0.001,
                "final_target_weight": 0.01,
                "entry_amount": 10_000_000.0,
                "turnover_rate_f": 1.0,
                "stock_market": "MAIN",
                "industry": "bank",
            },
            {
                "signal_date": "2024-01-01",
                "entry_date": "2024-01-02",
                "exit_date": "2024-01-22",
                "asset_id": "CN_XSHG_600002",
                "gross_return": 0.9,
                "final_return_contribution": 0.0,
                "final_target_weight": 0.0,
                "entry_amount": 2_000_000.0,
                "turnover_rate_f": 9.0,
                "stock_market": "MAIN",
                "industry": "bank",
            },
        ]
    )


if __name__ == "__main__":
    unittest.main()
