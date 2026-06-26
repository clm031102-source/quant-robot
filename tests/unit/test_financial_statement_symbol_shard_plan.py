import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.financial_statement_symbol_shard_plan import (
    build_financial_statement_symbol_shard_plan,
    write_financial_statement_symbol_shard_plan,
)


class FinancialStatementSymbolShardPlanTests(unittest.TestCase):
    def test_builds_endpoint_budgeted_statement_shard_plan(self) -> None:
        plan = build_financial_statement_symbol_shard_plan(
            symbols=["000001.SZ", "600519.SH"],
            start_period="2024-03-31",
            end_period="2024-06-30",
            symbols_per_shard=1,
            max_endpoint_requests_per_shard=6,
        )

        self.assertTrue(plan["summary"]["passes"])
        self.assertEqual(plan["summary"]["symbol_count"], 2)
        self.assertEqual(plan["summary"]["period_count"], 2)
        self.assertEqual(plan["summary"]["endpoint_count"], 3)
        self.assertEqual(plan["summary"]["total_base_request_count"], 4)
        self.assertEqual(plan["summary"]["total_endpoint_request_count"], 12)
        self.assertEqual(plan["shards"][0]["base_request_count"], 2)
        self.assertEqual(plan["shards"][0]["endpoint_request_count"], 6)

    def test_blocks_when_statement_endpoint_budget_is_exceeded(self) -> None:
        plan = build_financial_statement_symbol_shard_plan(
            symbols=["000001.SZ", "600519.SH"],
            start_period="2024-03-31",
            end_period="2024-06-30",
            symbols_per_shard=1,
            max_endpoint_requests_per_shard=5,
        )

        self.assertFalse(plan["summary"]["passes"])
        self.assertIn("endpoint_request_count_exceeds_max_endpoint_requests_per_shard", plan["summary"]["blockers"])

    def test_writes_statement_shard_plan_reports(self) -> None:
        plan = build_financial_statement_symbol_shard_plan(
            symbols=["000001.SZ"],
            start_period="2024-03-31",
            end_period="2024-03-31",
            symbols_per_shard=1,
            max_endpoint_requests_per_shard=3,
        )
        with tempfile.TemporaryDirectory() as tmp:
            write_financial_statement_symbol_shard_plan(Path(tmp), plan)

            self.assertTrue((Path(tmp) / "financial_statement_symbol_shard_plan.json").exists())
            self.assertTrue((Path(tmp) / "financial_statement_symbol_shard_plan.md").exists())


if __name__ == "__main__":
    unittest.main()
