import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.ops.financial_statement_symbol_shard_plan import write_financial_statement_symbol_shard_plan
from quant_robot.ops.financial_statement_symbol_shard_plan import build_financial_statement_symbol_shard_plan
from scripts.run_financial_statement_shard_backfill import run_financial_statement_shard_backfill_cli
from tests.unit.test_tushare_financial_statement_ingest import FakeFinancialStatementAdapter


class FinancialStatementShardBackfillCliTests(unittest.TestCase):
    def test_runs_symbol_limited_subshard_from_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_financial_statement_symbol_shard_plan(
                symbols=["000001.SZ", "600519.SH"],
                start_period="2024-03-31",
                end_period="2024-06-30",
                symbols_per_shard=2,
                max_endpoint_requests_per_shard=12,
            )
            plan_dir = root / "plan"
            write_financial_statement_symbol_shard_plan(plan_dir, plan)

            result = run_financial_statement_shard_backfill_cli(
                plan_json=plan_dir / "financial_statement_symbol_shard_plan.json",
                shard_id=1,
                symbol_offset=1,
                symbol_limit=1,
                max_endpoint_requests=6,
                output_dir=root / "subshard",
                adapter=FakeFinancialStatementAdapter(),
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["shard_id"], 1)
            self.assertEqual(result["summary"]["symbol_count"], 1)
            self.assertEqual(result["summary"]["period_count"], 2)
            self.assertEqual(result["summary"]["endpoint_request_count"], 6)
            self.assertEqual(result["summary"]["processed_rows"], 2)
            self.assertEqual(result["readiness"]["summary"]["required_column_groups_passing"], 2)
            self.assertTrue((root / "subshard" / "financial_statement_shard_backfill.json").exists())
            self.assertTrue((root / "subshard" / "financial_statement_shard_backfill.md").exists())

    def test_stock_basic_list_date_skips_pre_listing_statement_periods(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_financial_statement_symbol_shard_plan(
                symbols=["000001.SZ", "300997.SZ"],
                start_period="2020-12-31",
                end_period="2021-06-30",
                symbols_per_shard=2,
                max_endpoint_requests_per_shard=12,
            )
            plan_dir = root / "plan"
            write_financial_statement_symbol_shard_plan(plan_dir, plan)
            stock_basic = root / "stock_basic.csv"
            pd.DataFrame(
                {
                    "ts_code": ["000001.SZ", "300997.SZ"],
                    "list_date": ["19910403", "20210602"],
                }
            ).to_csv(stock_basic, index=False)
            adapter = FakeFinancialStatementAdapter()

            result = run_financial_statement_shard_backfill_cli(
                plan_json=plan_dir / "financial_statement_symbol_shard_plan.json",
                shard_id=1,
                max_endpoint_requests=12,
                output_dir=root / "subshard",
                stock_basic_path=stock_basic,
                adapter=adapter,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["endpoint_request_count"], 12)
            self.assertEqual(result["summary"]["processed_rows"], 4)
            self.assertEqual(result["ingest"]["summary"]["rows"], 4)
            self.assertEqual(result["ingest"]["summary"]["assets"], 2)
            quality_report = json.loads((root / "subshard" / "financial_statement_quality_report.json").read_text())
            self.assertEqual(quality_report["summary"]["rows"], 4)
            self.assertEqual(quality_report["summary"]["assets"], 2)
            self.assertEqual(result["summary"]["prelisting_skipped_symbol_period_count"], 2)
            self.assertEqual(result["summary"]["prelisting_skipped_endpoint_request_count"], 6)
            self.assertNotIn(("income", "300997.SZ", "20201231"), adapter.calls)
            self.assertNotIn(("income", "300997.SZ", "20210331"), adapter.calls)
            self.assertIn(("income", "300997.SZ", "20210630"), adapter.calls)

    def test_blocks_when_subshard_endpoint_budget_is_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_financial_statement_symbol_shard_plan(
                symbols=["000001.SZ", "600519.SH"],
                start_period="2024-03-31",
                end_period="2024-06-30",
                symbols_per_shard=2,
                max_endpoint_requests_per_shard=12,
            )
            plan_dir = root / "plan"
            write_financial_statement_symbol_shard_plan(plan_dir, plan)

            with self.assertRaisesRegex(RuntimeError, "endpoint request budget"):
                run_financial_statement_shard_backfill_cli(
                    plan_json=plan_dir / "financial_statement_symbol_shard_plan.json",
                    shard_id=1,
                    symbol_offset=0,
                    symbol_limit=2,
                    max_endpoint_requests=6,
                    output_dir=root / "subshard",
                    adapter=FakeFinancialStatementAdapter(),
                )

    def test_constructs_rate_limited_tushare_adapter_when_adapter_is_not_injected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = build_financial_statement_symbol_shard_plan(
                symbols=["000001.SZ"],
                start_period="2024-03-31",
                end_period="2024-03-31",
                symbols_per_shard=1,
                max_endpoint_requests_per_shard=3,
            )
            plan_dir = root / "plan"
            write_financial_statement_symbol_shard_plan(plan_dir, plan)

            with patch("scripts.run_financial_statement_shard_backfill.TushareAdapter") as adapter_cls:
                adapter_cls.return_value = FakeFinancialStatementAdapter()
                result = run_financial_statement_shard_backfill_cli(
                    plan_json=plan_dir / "financial_statement_symbol_shard_plan.json",
                    shard_id=1,
                    output_dir=root / "subshard",
                    max_endpoint_requests=3,
                    adapter_max_retries=6,
                    adapter_retry_sleep_seconds=12.5,
                    adapter_request_sleep_seconds=0.35,
                )

            self.assertTrue(result["summary"]["passes"])
            adapter_cls.assert_called_once_with(
                max_retries=6,
                retry_sleep_seconds=12.5,
                request_sleep_seconds=0.35,
            )


if __name__ == "__main__":
    unittest.main()
