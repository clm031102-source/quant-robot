import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_financial_statement_limited_backfill_smoke import (
    run_financial_statement_limited_backfill_smoke_cli,
)
from tests.unit.test_tushare_financial_statement_ingest import FakeFinancialStatementAdapter


class FinancialStatementLimitedBackfillSmokeCliTests(unittest.TestCase):
    def test_limited_statement_smoke_writes_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "smoke"

            result = run_financial_statement_limited_backfill_smoke_cli(
                adapter=FakeFinancialStatementAdapter(),
                symbols=["000001.SZ", "600519.SH"],
                start_period="2024-03-31",
                end_period="2024-06-30",
                batch_size=10,
                max_endpoint_requests=20,
                output_dir=output_dir,
            )

            self.assertEqual(result["summary"]["symbol_count"], 2)
            self.assertEqual(result["summary"]["period_count"], 2)
            self.assertEqual(result["summary"]["endpoint_request_count"], 12)
            self.assertEqual(result["summary"]["processed_rows"], 4)
            self.assertTrue((output_dir / "financial_statement_limited_backfill_smoke.json").exists())
            self.assertTrue((output_dir / "financial_statement_limited_backfill_smoke.md").exists())
            payload = json.loads(
                (output_dir / "financial_statement_limited_backfill_smoke.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["required_column_groups_passing"], 2)

    def test_limited_statement_smoke_blocks_when_endpoint_budget_is_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "endpoint request budget"):
                run_financial_statement_limited_backfill_smoke_cli(
                    adapter=FakeFinancialStatementAdapter(),
                    symbols=["000001.SZ", "600519.SH"],
                    start_period="2024-03-31",
                    end_period="2024-06-30",
                    batch_size=10,
                    max_endpoint_requests=3,
                    output_dir=Path(tmp) / "smoke",
                )


if __name__ == "__main__":
    unittest.main()
