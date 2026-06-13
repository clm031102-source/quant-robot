import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_akshare_gap_backfill import run_akshare_gap_backfill_cli


class FakeCliGapAdapter:
    def fetch_ohlcv(self, asset, request):
        return pd.DataFrame(
            {
                "date": [request.start],
                "open": [1.0],
                "high": [1.1],
                "low": [0.9],
                "close": [1.05],
                "adj_close": [1.05],
                "volume": [1000],
                "amount": [1050.0],
            }
        )


class AkshareGapBackfillCliTests(unittest.TestCase):
    def test_run_akshare_gap_backfill_cli_reads_gap_csv_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gap_rows = root / "gaps.csv"
            gap_rows.write_text(
                "gap_id,symbol,missing_date\n"
                "DG-CN_ETF_XSHG_510300-20240103,510300.SH,2024-01-03\n",
                encoding="utf-8",
            )
            processed_root = root / "processed"
            output_dir = root / "akshare_backfill"

            report = run_akshare_gap_backfill_cli(
                gap_rows=gap_rows,
                processed_root=processed_root,
                output_dir=output_dir,
                adapter=FakeCliGapAdapter(),
            )

            self.assertEqual(report["summary"]["resolved_with_provider"], 1)
            payload = json.loads((output_dir / "akshare_gap_backfill_report.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["stage"], "phase_4_17_akshare_gap_backfill")


if __name__ == "__main__":
    unittest.main()
