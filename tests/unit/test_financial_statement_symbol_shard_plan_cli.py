import tempfile
import unittest
from pathlib import Path

from scripts.run_financial_statement_symbol_shard_plan import run_financial_statement_symbol_shard_plan_cli


class FinancialStatementSymbolShardPlanCliTests(unittest.TestCase):
    def test_cli_writes_statement_shard_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_financial_statement_symbol_shard_plan_cli(
                symbols=["000001.SZ", "600519.SH"],
                start_period="2024-03-31",
                end_period="2024-06-30",
                symbols_per_shard=1,
                max_endpoint_requests_per_shard=6,
                output_dir=Path(tmp),
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["total_endpoint_request_count"], 12)
            self.assertTrue((Path(tmp) / "financial_statement_symbol_shard_plan.json").exists())

    def test_cli_blocks_unless_blocked_plan_is_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(RuntimeError, "statement symbol shard plan is blocked"):
                run_financial_statement_symbol_shard_plan_cli(
                    symbols=["000001.SZ", "600519.SH"],
                    start_period="2024-03-31",
                    end_period="2024-06-30",
                    symbols_per_shard=1,
                    max_endpoint_requests_per_shard=5,
                    output_dir=Path(tmp),
                )


if __name__ == "__main__":
    unittest.main()
