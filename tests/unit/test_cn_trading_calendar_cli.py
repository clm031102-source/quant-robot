import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_cn_trading_calendar import run_cn_trading_calendar


class CnTradingCalendarCliTests(unittest.TestCase):
    def test_fetches_required_exchanges_and_writes_artifact(self) -> None:
        adapter = _FakeAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cn_trading_calendar(
                output_dir=tmp,
                start_date="2024-01-01",
                end_date="2024-01-04",
                adapter=adapter,
            )

            self.assertEqual(adapter.calls, [
                ("2024-01-01", "2024-01-04", "SSE"),
                ("2024-01-01", "2024-01-04", "SZSE"),
            ])
            self.assertTrue(Path(result["calendar_path"]).exists())
            self.assertTrue(Path(result["manifest_path"]).exists())
            self.assertEqual(result["manifest"]["status"], "cleared")

    def test_validate_only_uses_existing_artifact_without_adapter(self) -> None:
        adapter = _FakeAdapter()
        with tempfile.TemporaryDirectory() as tmp:
            created = run_cn_trading_calendar(
                output_dir=tmp,
                start_date="2024-01-01",
                end_date="2024-01-04",
                adapter=adapter,
            )
            adapter.calls.clear()

            result = run_cn_trading_calendar(
                output_dir=tmp,
                start_date="2024-01-01",
                end_date="2024-01-04",
                adapter=adapter,
                validate_only=True,
            )

            self.assertEqual(adapter.calls, [])
            self.assertEqual(result["calendar_path"], created["calendar_path"])
            self.assertEqual(result["manifest"]["status"], "cleared")


class _FakeAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def fetch_trade_calendar(self, start_date: str, end_date: str, exchange: str = "SSE") -> pd.DataFrame:
        self.calls.append((start_date, end_date, exchange))
        return pd.DataFrame(
            {
                "exchange": [exchange, exchange],
                "date": pd.to_datetime(["2024-01-02", "2024-01-03"]).date,
                "is_open": [1, 1],
            }
        )


if __name__ == "__main__":
    unittest.main()
