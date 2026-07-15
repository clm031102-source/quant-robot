import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.cn_trading_calendar import (
    build_cn_trading_calendar,
    validate_cn_trading_calendar_artifact,
    write_cn_trading_calendar,
)


class CnTradingCalendarTests(unittest.TestCase):
    def test_build_requires_synchronized_sse_and_szse_sessions(self) -> None:
        calendar, manifest = build_cn_trading_calendar(
            {
                "SSE": _calendar_frame("SSE", ["2024-01-02", "2024-01-03"]),
                "SZSE": _calendar_frame("SZSE", ["2024-01-02", "2024-01-03"]),
            },
            start_date="2024-01-01",
            end_date="2024-01-04",
        )

        self.assertEqual(calendar.to_dict(orient="records"), [
            {"market": "CN", "date": "2024-01-02", "is_open": 1, "source": "tushare"},
            {"market": "CN", "date": "2024-01-03", "is_open": 1, "source": "tushare"},
        ])
        self.assertEqual(manifest["provider"], "tushare")
        self.assertEqual(manifest["endpoint"], "trade_cal")
        self.assertEqual(manifest["required_exchanges"], ["SSE", "SZSE"])
        self.assertEqual(manifest["summary"]["session_rows"], 2)
        self.assertEqual(manifest["summary"]["exchange_session_rows"], {"SSE": 2, "SZSE": 2})
        self.assertFalse(manifest["live_boundary_allowed"])

    def test_build_rejects_exchange_calendar_divergence(self) -> None:
        with self.assertRaisesRegex(ValueError, "exchange calendars diverge"):
            build_cn_trading_calendar(
                {
                    "SSE": _calendar_frame("SSE", ["2024-01-02", "2024-01-03"]),
                    "SZSE": _calendar_frame("SZSE", ["2024-01-02"]),
                },
                start_date="2024-01-01",
                end_date="2024-01-04",
            )

    def test_build_rejects_empty_required_exchange(self) -> None:
        with self.assertRaisesRegex(ValueError, "SZSE calendar is empty"):
            build_cn_trading_calendar(
                {
                    "SSE": _calendar_frame("SSE", ["2024-01-02"]),
                    "SZSE": _calendar_frame("SZSE", []),
                },
                start_date="2024-01-01",
                end_date="2024-01-04",
            )

    def test_written_artifact_validates_and_tampering_is_rejected(self) -> None:
        calendar, manifest = build_cn_trading_calendar(
            {
                "SSE": _calendar_frame("SSE", ["2024-01-02", "2024-01-03"]),
                "SZSE": _calendar_frame("SZSE", ["2024-01-02", "2024-01-03"]),
            },
            start_date="2024-01-01",
            end_date="2024-01-04",
        )
        with tempfile.TemporaryDirectory() as tmp:
            paths = write_cn_trading_calendar(tmp, calendar, manifest)

            validated = validate_cn_trading_calendar_artifact(
                paths["calendar_path"],
                paths["manifest_path"],
                expected_start_date="2024-01-01",
                expected_end_date="2024-01-04",
            )
            self.assertEqual(validated["summary"]["session_rows"], 2)

            Path(paths["calendar_path"]).write_text(
                Path(paths["calendar_path"]).read_text(encoding="utf-8") + "CN,2024-01-04,1,tushare\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "artifact fingerprint mismatch"):
                validate_cn_trading_calendar_artifact(paths["calendar_path"], paths["manifest_path"])


def _calendar_frame(exchange: str, dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "exchange": [exchange] * len(dates),
            "date": pd.to_datetime(dates).date,
            "is_open": [1] * len(dates),
        }
    )


if __name__ == "__main__":
    unittest.main()
