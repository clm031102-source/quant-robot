import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.index_rebalance_event_audit import (
    build_index_rebalance_event_audit,
    render_index_rebalance_event_audit_markdown,
    write_index_rebalance_event_audit,
)


class IndexRebalanceEventAuditTests(unittest.TestCase):
    def test_builds_pit_add_remove_and_weight_change_events(self) -> None:
        audit = build_index_rebalance_event_audit(
            index_weight=_index_weight_rows(),
            trade_calendar=_calendar_rows(),
            min_abs_weight_change=0.5,
        )

        self.assertTrue(audit["summary"]["passes"])
        self.assertEqual(audit["summary"]["event_rows"], 3)
        event_types = {row["event_type"] for row in audit["event_rows"]}
        self.assertEqual(event_types, {"added", "removed", "weight_changed"})
        self.assertTrue(
            all(pd.Timestamp(row["available_date"]) > pd.Timestamp(row["event_date"]) for row in audit["event_rows"])
        )
        added = next(row for row in audit["event_rows"] if row["event_type"] == "added")
        self.assertEqual(added["asset_id"], "CN_XSHE_000003")
        removed = next(row for row in audit["event_rows"] if row["event_type"] == "removed")
        self.assertEqual(removed["asset_id"], "CN_XSHE_000002")
        changed = next(row for row in audit["event_rows"] if row["event_type"] == "weight_changed")
        self.assertAlmostEqual(changed["weight_delta"], 1.0)

    def test_blocks_duplicate_snapshot_keys_and_missing_available_dates(self) -> None:
        duplicated = pd.concat([_index_weight_rows(), _index_weight_rows().iloc[[0]]], ignore_index=True)

        audit = build_index_rebalance_event_audit(
            index_weight=duplicated,
            trade_calendar=_calendar_rows().iloc[:2],
            min_abs_weight_change=0.5,
        )

        self.assertFalse(audit["summary"]["passes"])
        self.assertIn("duplicate_index_weight_keys", audit["summary"]["blockers"])
        self.assertIn("missing_available_date_rows", audit["summary"]["blockers"])

    def test_write_outputs(self) -> None:
        audit = build_index_rebalance_event_audit(
            index_weight=_index_weight_rows(),
            trade_calendar=_calendar_rows(),
            min_abs_weight_change=0.5,
        )
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "audit"

            write_index_rebalance_event_audit(output_dir, audit)

            self.assertTrue((output_dir / "index_rebalance_event_audit.json").exists())
            self.assertTrue((output_dir / "index_rebalance_event_audit.md").exists())
            self.assertTrue((output_dir / "index_weight_snapshots.csv").exists())
            self.assertTrue((output_dir / "index_rebalance_events.csv").exists())
            markdown = render_index_rebalance_event_audit_markdown(audit)
            self.assertIn("Index Rebalance Event Audit", markdown)
            self.assertIn("Event rows: 3", markdown)


def _index_weight_rows() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"index_code": "000300.SH", "con_code": "000001.SZ", "trade_date": "20240102", "weight": 1.0},
            {"index_code": "000300.SH", "con_code": "000002.SZ", "trade_date": "20240102", "weight": 2.0},
            {"index_code": "000300.SH", "con_code": "000001.SZ", "trade_date": "20240201", "weight": 2.0},
            {"index_code": "000300.SH", "con_code": "000003.SZ", "trade_date": "20240201", "weight": 3.0},
        ]
    )


def _calendar_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-02", "2024-01-03", "2024-02-01", "2024-02-02"]),
            "is_open": [1, 1, 1, 1],
        }
    )


if __name__ == "__main__":
    unittest.main()
