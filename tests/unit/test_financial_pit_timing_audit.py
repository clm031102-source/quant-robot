import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.financial_pit_timing_audit import (
    build_financial_pit_timing_audit,
    render_financial_pit_timing_audit_markdown,
    write_financial_pit_timing_audit,
)
from quant_robot.storage.dataset_store import DatasetStore


class FinancialPitTimingAuditTests(unittest.TestCase):
    def test_passes_with_distinct_revision_ann_dates_and_strict_signal_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            _write_financial_rows(
                financial_root,
                pd.DataFrame(
                    [
                        _financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.1),
                        _financial_row("CN_XSHE_000001", "2024-07-30", "2024-06-30", roe=8.4),
                        _financial_row("CN_XSHE_000001", "2024-08-15", "2024-06-30", roe=8.7),
                    ]
                ),
            )
            _write_bars(
                bars_root,
                "CN_XSHE_000001",
                ["2024-05-06", "2024-07-31", "2024-08-16", "2024-08-19"],
            )

            result = build_financial_pit_timing_audit(
                financial_root=financial_root,
                bars_roots=[bars_root],
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["revision_group_count"], 1)
            self.assertEqual(result["summary"]["revision_row_count"], 2)
            self.assertEqual(result["summary"]["exact_duplicate_key_rows"], 0)
            self.assertEqual(result["summary"]["signal_unmapped_rows"], 0)
            self.assertEqual(result["summary"]["signal_alignment_violation_rows"], 0)
            self.assertEqual(result["revision_policy"]["revision_handling_status"], "revision_aware_distinct_ann_dates")
            self.assertFalse(result["availability_policy"]["same_day_announcement_trading_allowed"])
            self.assertEqual(result["timing_rows"][0]["signal_date"], "2024-05-06")

    def test_blocks_exact_duplicate_financial_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            frame = pd.DataFrame(
                [
                    _financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.1),
                    _financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.2),
                ]
            )
            _write_financial_rows(financial_root, frame)
            _write_bars(bars_root, "CN_XSHE_000001", ["2024-05-06"])

            result = build_financial_pit_timing_audit(
                financial_root=financial_root,
                bars_roots=[bars_root],
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("exact_duplicate_financial_keys", result["summary"]["blockers"])
            self.assertEqual(result["summary"]["exact_duplicate_key_rows"], 1)
            self.assertEqual(result["revision_policy"]["revision_handling_status"], "blocked_duplicate_revision_keys")

    def test_blocks_report_period_values_that_precede_report_end_or_have_no_later_bar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            _write_financial_rows(
                financial_root,
                pd.DataFrame(
                    [
                        _financial_row("CN_XSHE_000001", "2024-03-15", "2024-03-31", roe=8.1),
                        _financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.2),
                    ]
                ),
            )
            _write_bars(bars_root, "CN_XSHE_000001", ["2024-04-30"])

            result = build_financial_pit_timing_audit(
                financial_root=financial_root,
                bars_roots=[bars_root],
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("ann_date_before_report_period", result["summary"]["blockers"])
            self.assertIn("signal_date_unmapped_rows", result["summary"]["blockers"])
            self.assertEqual(result["summary"]["ann_date_before_report_period_rows"], 1)
            self.assertEqual(result["summary"]["signal_unmapped_rows"], 1)

    def test_blocks_stale_signal_mapping_when_first_later_bar_is_too_late(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            _write_financial_rows(
                financial_root,
                pd.DataFrame([_financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.1)]),
            )
            _write_bars(bars_root, "CN_XSHE_000001", ["2024-07-15"])

            result = build_financial_pit_timing_audit(
                financial_root=financial_root,
                bars_roots=[bars_root],
                max_signal_lag_calendar_days=30,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("signal_lag_exceeds_max_calendar_days", result["summary"]["blockers"])
            self.assertEqual(result["summary"]["stale_signal_lag_rows"], 1)
            self.assertEqual(result["summary"]["max_signal_lag_calendar_days_allowed"], 30)

    def test_write_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            output_dir = root / "output"
            _write_financial_rows(
                financial_root,
                pd.DataFrame([_financial_row("CN_XSHE_000001", "2024-04-30", "2024-03-31", roe=8.1)]),
            )
            _write_bars(bars_root, "CN_XSHE_000001", ["2024-05-06"])
            result = build_financial_pit_timing_audit(financial_root=financial_root, bars_roots=[bars_root])

            write_financial_pit_timing_audit(output_dir, result)

            self.assertTrue((output_dir / "financial_pit_timing_audit.json").exists())
            self.assertTrue((output_dir / "financial_pit_timing_audit.md").exists())
            self.assertTrue((output_dir / "financial_pit_timing_audit_timing_rows.csv").exists())
            markdown = render_financial_pit_timing_audit_markdown(result)
            self.assertIn("Financial PIT Timing Audit", markdown)
            self.assertIn("Passes: True", markdown)


def _financial_row(asset_id: str, ann_date: str, end_date: str, *, roe: float) -> dict[str, object]:
    return {
        "date": pd.Timestamp(ann_date),
        "asset_id": asset_id,
        "symbol": asset_id.removeprefix("CN_XSHE_") + ".SZ",
        "market": "CN",
        "source": "tushare_fina_indicator",
        "ann_date": pd.Timestamp(ann_date),
        "end_date": pd.Timestamp(end_date),
        "roe": roe,
        "roa": 3.0,
        "grossprofit_margin": 20.0,
        "netprofit_margin": 6.0,
        "netprofit_yoy": 5.0,
        "or_yoy": 4.0,
        "ocfps": 1.0,
        "cfps": 1.2,
    }


def _write_financial_rows(root: Path, frame: pd.DataFrame) -> None:
    DatasetStore(root).write_frame(
        frame,
        "processed/fina_indicator_inputs",
        {"frequency": "1q", "market": "CN", "year": "2024"},
    )


def _write_bars(root: Path, asset_id: str, dates: list[str]) -> None:
    DatasetStore(root).write_frame(
        pd.DataFrame(
            [
                {"date": pd.Timestamp(day), "asset_id": asset_id, "market": "CN", "adj_close": 10.0 + index}
                for index, day in enumerate(dates)
            ]
        ),
        "processed/bars",
        {"frequency": "1d", "market": "CN", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
