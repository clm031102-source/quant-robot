import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.financial_pit_signal_date_filter import (
    build_financial_pit_signal_date_filter,
    render_financial_pit_signal_date_filter_markdown,
    write_financial_pit_signal_date_filter,
)
from quant_robot.ops.financial_pit_timing_audit import build_financial_pit_timing_audit
from tests.unit.test_financial_pit_timing_audit import _financial_row, _write_bars, _write_financial_rows


class FinancialPitSignalDateFilterTests(unittest.TestCase):
    def test_drops_unmapped_and_stale_rows_and_adds_available_signal_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            _write_financial_rows(
                financial_root,
                pd.DataFrame(
                    [
                        _financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.1),
                        _financial_row("CN_XSHE_000001", "2024-05-31", "2024-03-31", roe=8.2),
                        _financial_row("CN_XSHE_000002", "2024-04-30", "2024-03-31", roe=9.1),
                    ]
                ),
            )
            _write_bars(bars_root, "CN_XSHE_000001", ["2024-05-06", "2024-08-15"])

            result = build_financial_pit_signal_date_filter(
                financial_root=financial_root,
                bars_roots=[bars_root],
                max_signal_lag_calendar_days=30,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["input_rows"], 3)
            self.assertEqual(result["summary"]["filtered_rows"], 1)
            self.assertEqual(result["summary"]["dropped_stale_signal_lag_rows"], 1)
            self.assertEqual(result["summary"]["dropped_unmapped_signal_rows"], 1)
            frame = result["filtered_frame"]
            self.assertEqual(list(frame["available_date"].dt.strftime("%Y-%m-%d")), ["2024-05-06"])
            self.assertEqual(list(frame["signal_date"].dt.strftime("%Y-%m-%d")), ["2024-05-06"])
            self.assertEqual(list(frame["signal_lag_calendar_days"]), [6])

    def test_written_filtered_root_passes_timing_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            output_root = root / "filtered"
            _write_financial_rows(
                financial_root,
                pd.DataFrame(
                    [
                        _financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.1),
                        _financial_row("CN_XSHE_000001", "2024-05-31", "2024-03-31", roe=8.2),
                    ]
                ),
            )
            _write_bars(bars_root, "CN_XSHE_000001", ["2024-05-06", "2024-08-15"])
            result = build_financial_pit_signal_date_filter(
                financial_root=financial_root,
                bars_roots=[bars_root],
                max_signal_lag_calendar_days=30,
            )

            write_financial_pit_signal_date_filter(output_root, result)
            audit = build_financial_pit_timing_audit(
                financial_root=output_root,
                bars_roots=[bars_root],
                max_signal_lag_calendar_days=30,
            )

            self.assertTrue((output_root / "financial_pit_signal_date_filter.json").exists())
            self.assertTrue((output_root / "financial_pit_signal_date_filter.md").exists())
            self.assertTrue(audit["summary"]["passes"])
            self.assertEqual(audit["summary"]["financial_rows"], 1)
            markdown = render_financial_pit_signal_date_filter_markdown(result)
            self.assertIn("Financial PIT Signal-Date Filter", markdown)
            self.assertIn("Filtered rows: 1", markdown)

    def test_preserves_distinct_revision_ann_dates_after_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            _write_financial_rows(
                financial_root,
                pd.DataFrame(
                    [
                        _financial_row("CN_XSHE_000001", "2024-07-30", "2024-06-30", roe=8.4),
                        _financial_row("CN_XSHE_000001", "2024-08-15", "2024-06-30", roe=8.7),
                    ]
                ),
            )
            _write_bars(bars_root, "CN_XSHE_000001", ["2024-07-31", "2024-08-16"])

            result = build_financial_pit_signal_date_filter(
                financial_root=financial_root,
                bars_roots=[bars_root],
                max_signal_lag_calendar_days=30,
            )

            self.assertTrue(result["summary"]["passes"])
            frame = result["filtered_frame"]
            self.assertEqual(len(frame), 2)
            self.assertEqual(frame["end_date"].dt.strftime("%Y-%m-%d").nunique(), 1)
            self.assertEqual(list(frame["ann_date"].dt.strftime("%Y-%m-%d")), ["2024-07-30", "2024-08-15"])
            self.assertEqual(list(frame["signal_date"].dt.strftime("%Y-%m-%d")), ["2024-07-31", "2024-08-16"])


if __name__ == "__main__":
    unittest.main()
