from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.shortlist_event_calendar_parity import (
    build_event_calendar_parity_audit,
    write_event_calendar_parity_audit,
)


class ShortlistEventCalendarParityTest(unittest.TestCase):
    def test_missing_and_extra_dates_block_parity(self) -> None:
        reference = pd.DataFrame(
            {
                "date": ["2021-01-01", "2021-01-08"],
                "period_return": [0.01, 0.02],
            }
        )
        generated = pd.DataFrame(
            {
                "date": ["2021-01-01", "2021-01-15"],
                "entry_cash_proxy_return": [0.01, 0.03],
            }
        )

        audit = build_event_calendar_parity_audit(
            reference,
            generated,
            generated_return_column="entry_cash_proxy_return",
        )

        self.assertEqual(audit["summary"]["missing_generated_dates"], 1)
        self.assertEqual(audit["summary"]["extra_generated_dates"], 1)
        self.assertIn("missing_generated_dates", audit["blockers"])
        self.assertIn("extra_generated_dates", audit["blockers"])

    def test_metric_tolerance_blocks_large_metric_drift(self) -> None:
        reference = pd.DataFrame(
            {
                "date": pd.date_range("2021-01-01", periods=12, freq="7D"),
                "period_return": [0.01] * 12,
            }
        )
        generated = reference.rename(columns={"period_return": "entry_cash_proxy_return"}).copy()
        generated["entry_cash_proxy_return"] = [0.02] * 12

        audit = build_event_calendar_parity_audit(
            reference,
            generated,
            generated_return_column="entry_cash_proxy_return",
            metric_tolerance=0.005,
        )

        self.assertEqual(audit["summary"]["missing_generated_dates"], 0)
        self.assertEqual(audit["summary"]["extra_generated_dates"], 0)
        self.assertIn("metric_drift:total_return", audit["blockers"])

    def test_write_parity_outputs_json_and_csv(self) -> None:
        reference = pd.DataFrame({"date": ["2021-01-01"], "period_return": [0.01]})
        generated = pd.DataFrame({"date": ["2021-01-01"], "entry_cash_proxy_return": [0.01]})

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            audit = build_event_calendar_parity_audit(
                reference,
                generated,
                generated_return_column="entry_cash_proxy_return",
            )
            write_event_calendar_parity_audit(root / "out", audit)

            self.assertTrue((root / "out" / "event_calendar_parity_audit.json").exists())
            self.assertTrue((root / "out" / "event_calendar_parity_rows.csv").exists())


if __name__ == "__main__":
    unittest.main()
