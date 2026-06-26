import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_fina_indicator_limited_backfill_smoke import run_fina_indicator_limited_backfill_smoke_cli


class FakeLimitedBackfillAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_fina_indicator(self, period: str, ts_code: str = "") -> pd.DataFrame:
        self.calls.append((ts_code, period))
        if ts_code == "600519.SH":
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "ann_date",
                    "end_date",
                    "roe",
                    "roa",
                    "grossprofit_margin",
                    "netprofit_margin",
                    "netprofit_yoy",
                    "or_yoy",
                    "ocfps",
                    "cfps",
                ]
            )
        period_date = pd.to_datetime(period, format="%Y%m%d").date()
        ann_date = (pd.Timestamp(period_date) + pd.Timedelta(days=25)).date()
        return pd.DataFrame(
            {
                "symbol": [ts_code],
                "ann_date": [ann_date],
                "end_date": [period_date],
                "roe": [10.0],
                "roa": [1.0],
                "grossprofit_margin": [30.0],
                "netprofit_margin": [12.0],
                "netprofit_yoy": [8.0],
                "or_yoy": [6.0],
                "ocfps": [1.2],
                "cfps": [1.8],
            }
        )


class FinaIndicatorLimitedBackfillSmokeCliTests(unittest.TestCase):
    def test_limited_smoke_writes_report_and_records_empty_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "smoke"
            adapter = FakeLimitedBackfillAdapter()

            result = run_fina_indicator_limited_backfill_smoke_cli(
                adapter=adapter,
                symbols=["000001.SZ", "600519.SH"],
                start_period="2024-03-31",
                end_period="2024-06-30",
                batch_size=10,
                max_requests=10,
                output_dir=output_dir,
            )

            self.assertEqual(result["plan"]["summary"]["request_count"], 4)
            self.assertEqual(result["ingest"]["processed_rows"], 2)
            self.assertEqual(result["ingest"]["empty_requests"], ["600519.SH:20240331", "600519.SH:20240630"])
            self.assertTrue((output_dir / "limited_backfill_smoke.json").exists())
            self.assertTrue((output_dir / "limited_backfill_smoke.md").exists())
            payload = json.loads((output_dir / "limited_backfill_smoke.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["empty_request_count"], 2)

    def test_limited_smoke_blocks_when_budget_is_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "request budget"):
                run_fina_indicator_limited_backfill_smoke_cli(
                    adapter=FakeLimitedBackfillAdapter(),
                    symbols=["000001.SZ", "600519.SH"],
                    start_period="2024-03-31",
                    end_period="2024-06-30",
                    batch_size=10,
                    max_requests=1,
                    output_dir=Path(tmp) / "smoke",
                )


if __name__ == "__main__":
    unittest.main()
