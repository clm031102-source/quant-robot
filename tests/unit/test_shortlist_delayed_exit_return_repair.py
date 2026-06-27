from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_delayed_exit_return_repair import (
    build_delayed_exit_return_repair,
    write_delayed_exit_return_repair,
)


class ShortlistDelayedExitReturnRepairTest(unittest.TestCase):
    def test_recomputes_weighted_return_on_first_sellable_exit_date(self) -> None:
        result = build_delayed_exit_return_repair(
            trades_source=_trades(),
            bars_source=_bars(),
            masks_source=_masks(),
            max_exit_delay_days=5,
        )

        rows = {row["asset_id"]: row for row in result["trade_rows"]}

        delayed = rows["DELAYED"]
        self.assertEqual(delayed["delayed_exit_date"], "2024-01-05")
        self.assertEqual(delayed["exit_delay_days"], 1)
        self.assertAlmostEqual(delayed["delayed_exit_gross_return"], 0.10)
        self.assertAlmostEqual(delayed["delayed_exit_weighted_return"], 0.0495)

        normal = rows["NORMAL"]
        self.assertEqual(normal["delayed_exit_date"], "2024-01-04")
        self.assertEqual(normal["exit_delay_days"], 0)
        self.assertAlmostEqual(normal["delayed_exit_weighted_return"], 0.0495)

        entry_blocked = rows["ENTRY_BLOCKED"]
        self.assertEqual(entry_blocked["delayed_exit_status"], "entry_blocked")
        self.assertEqual(entry_blocked["delayed_exit_date"], "2024-01-04")
        self.assertAlmostEqual(entry_blocked["delayed_exit_weighted_return"], 0.0)

        unresolved = rows["UNRESOLVED"]
        self.assertEqual(unresolved["delayed_exit_status"], "unresolved_exit")
        self.assertEqual(unresolved["delayed_exit_date"], "2024-01-04")
        self.assertAlmostEqual(unresolved["delayed_exit_weighted_return"], 0.0)

        self.assertEqual(result["summary"]["trade_count"], 4)
        self.assertEqual(result["summary"]["delayed_exit_trade_count"], 1)
        self.assertEqual(result["summary"]["entry_blocked_trade_count"], 1)
        self.assertEqual(result["summary"]["unresolved_exit_trade_count"], 1)

    def test_writer_outputs_trade_rows_and_summary(self) -> None:
        with TemporaryDirectory() as tmp:
            result = build_delayed_exit_return_repair(
                trades_source=_trades(),
                bars_source=_bars(),
                masks_source=_masks(),
                max_exit_delay_days=5,
            )

            write_delayed_exit_return_repair(tmp, result)

            output = Path(tmp)
            self.assertTrue((output / "delayed_exit_return_repair.json").exists())
            self.assertTrue((output / "delayed_exit_trade_rows.csv").exists())

    def test_override_cost_rate_recomputes_weighted_return(self) -> None:
        result = build_delayed_exit_return_repair(
            trades_source=_trades(),
            bars_source=_bars(),
            masks_source=_masks(),
            max_exit_delay_days=5,
            override_cost_rate=0.003,
        )

        rows = {row["asset_id"]: row for row in result["trade_rows"]}

        self.assertAlmostEqual(rows["DELAYED"]["delayed_exit_weighted_return"], 0.0485)
        self.assertAlmostEqual(rows["NORMAL"]["delayed_exit_weighted_return"], 0.0485)
        self.assertEqual(result["parameters"]["override_cost_rate"], 0.003)


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "asset_id": "DELAYED",
                "entry_date": "2024-01-02",
                "exit_date": "2024-01-04",
                "target_weight": 0.5,
                "cost_rate": 0.001,
                "entry_allowed": True,
            },
            {
                "asset_id": "NORMAL",
                "entry_date": "2024-01-02",
                "exit_date": "2024-01-04",
                "target_weight": 0.5,
                "cost_rate": 0.001,
                "entry_allowed": True,
            },
            {
                "asset_id": "ENTRY_BLOCKED",
                "entry_date": "2024-01-02",
                "exit_date": "2024-01-04",
                "target_weight": 0.5,
                "cost_rate": 0.001,
                "entry_allowed": False,
            },
            {
                "asset_id": "UNRESOLVED",
                "entry_date": "2024-01-02",
                "exit_date": "2024-01-04",
                "target_weight": 0.5,
                "cost_rate": 0.001,
                "entry_allowed": True,
            },
        ]
    )


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"asset_id": "DELAYED", "date": "2024-01-02", "market": "CN", "adj_close": 10.0},
            {"asset_id": "DELAYED", "date": "2024-01-04", "market": "CN", "adj_close": 9.0},
            {"asset_id": "DELAYED", "date": "2024-01-05", "market": "CN", "adj_close": 11.0},
            {"asset_id": "NORMAL", "date": "2024-01-02", "market": "CN", "adj_close": 20.0},
            {"asset_id": "NORMAL", "date": "2024-01-04", "market": "CN", "adj_close": 22.0},
            {"asset_id": "ENTRY_BLOCKED", "date": "2024-01-02", "market": "CN", "adj_close": 30.0},
            {"asset_id": "ENTRY_BLOCKED", "date": "2024-01-04", "market": "CN", "adj_close": 33.0},
            {"asset_id": "UNRESOLVED", "date": "2024-01-02", "market": "CN", "adj_close": 40.0},
            {"asset_id": "UNRESOLVED", "date": "2024-01-04", "market": "CN", "adj_close": 44.0},
        ]
    )


def _masks() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"asset_id": "DELAYED", "date": "2024-01-04", "market": "CN", "can_sell": False},
            {"asset_id": "DELAYED", "date": "2024-01-05", "market": "CN", "can_sell": True},
            {"asset_id": "NORMAL", "date": "2024-01-04", "market": "CN", "can_sell": True},
            {"asset_id": "ENTRY_BLOCKED", "date": "2024-01-04", "market": "CN", "can_sell": True},
            {"asset_id": "UNRESOLVED", "date": "2024-01-04", "market": "CN", "can_sell": False},
            {"asset_id": "UNRESOLVED", "date": "2024-01-05", "market": "CN", "can_sell": False},
        ]
    )


if __name__ == "__main__":
    unittest.main()
