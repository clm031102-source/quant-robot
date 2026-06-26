import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.tushare_tradeability_backfill_plan import (
    build_tushare_tradeability_backfill_plan,
    run_tushare_tradeability_backfill,
    write_tushare_tradeability_backfill_plan,
)


class TushareTradeabilityBackfillPlanTests(unittest.TestCase):
    def test_builds_monthly_shards_with_safe_commands_and_estimates(self):
        plan = build_tushare_tradeability_backfill_plan(
            start_date="2024-01-02",
            end_date="2024-03-05",
            processed_root="data/processed/round198_tradeability_backfill",
            report_root="data/reports/round198_tradeability_backfill_shards",
            max_shards=2,
        )

        self.assertEqual(plan["stage"], "tushare_tradeability_long_cycle_backfill_plan")
        self.assertEqual(plan["status"], "ready")
        self.assertFalse(plan["execute"])
        self.assertFalse(plan["processed_writes_enabled"])
        self.assertEqual(plan["summary"]["planned_shards"], 3)
        self.assertEqual(plan["summary"]["selected_shards"], 2)
        self.assertGreater(plan["summary"]["total_estimated_endpoint_calls"], 0)
        first = plan["shards"][0]
        self.assertEqual(first["shard_id"], "202401")
        self.assertEqual(first["start_date"], "2024-01-02")
        self.assertEqual(first["end_date"], "2024-01-31")
        self.assertIn("run_tushare_tradeability_feed_ingest.py", first["command"])
        self.assertIn("--start-date 2024-01-02", first["command"])
        self.assertNotIn("--execute-write-processed", first["command"])
        self.assertIn("direct_cn_stock_factor_mining_before_tradeability_backfill", plan["blocked_uses"])

    def test_rejects_non_cn_market_and_bad_date_range(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            build_tushare_tradeability_backfill_plan(
                start_date="2024-01-01",
                end_date="2024-01-31",
                processed_root="data/processed/out",
                market="US",
            )
        with self.assertRaisesRegex(ValueError, "start_date"):
            build_tushare_tradeability_backfill_plan(
                start_date="2024-02-01",
                end_date="2024-01-31",
                processed_root="data/processed/out",
            )

    def test_skip_covered_uses_manifest_to_select_next_uncovered_months(self):
        with tempfile.TemporaryDirectory() as tmp:
            processed_root = Path(tmp) / "processed"
            manifest = pd.DataFrame(
                {
                    "feed": [
                        "tradeability_stk_limit",
                        "tradeability_suspension",
                        "tradeability_namechange",
                    ],
                    "start_date": ["2015-01-01", "2015-01-01", "2015-01-01"],
                    "end_date": ["2015-03-31", "2015-03-31", "2015-03-31"],
                    "market": ["CN", "CN", "CN"],
                    "shard_id": ["20150101_20150331"] * 3,
                }
            )
            manifest_path = (
                processed_root
                / "metadata/tushare_tradeability_feed_coverage/market=CN/shard=20150101_20150331/part-00000.parquet"
            )
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest.to_parquet(manifest_path, index=False)

            plan = build_tushare_tradeability_backfill_plan(
                start_date="2015-01-01",
                end_date="2015-06-30",
                processed_root=processed_root,
                max_shards=2,
                skip_covered=True,
            )

        self.assertEqual(plan["summary"]["planned_shards"], 6)
        self.assertEqual(plan["summary"]["covered_shards"], 3)
        self.assertEqual(plan["summary"]["selected_shards"], 2)
        self.assertEqual([shard["shard_id"] for shard in plan["shards"]], ["201504", "201505"])
        self.assertEqual(plan["shards"][0]["start_date"], "2015-04-01")
        self.assertEqual(plan["summary"]["remaining_unselected_shards"], 1)

    def test_execute_runs_only_selected_shards_and_writes_progress(self):
        calls = []

        def fake_runner(**kwargs):
            calls.append(kwargs)
            return {
                "summary": {"status": "pass", "warn_count": 0, "fail_count": 0},
                "processed_writes_enabled": kwargs["execute_write_processed"],
                "start_date": kwargs["start_date"],
                "end_date": kwargs["end_date"],
            }

        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_tradeability_backfill(
                start_date="2024-01-02",
                end_date="2024-03-05",
                processed_root=Path(tmp) / "processed",
                report_root=Path(tmp) / "reports" / "shards",
                output_dir=Path(tmp) / "reports" / "plan",
                max_shards=2,
                execute=True,
                execute_write_processed=True,
                snapshot="2026-06-23",
                runner=fake_runner,
            )
            progress_path = Path(tmp) / "reports" / "plan" / "tradeability_backfill_progress.jsonl"
            summary_path = Path(tmp) / "reports" / "plan" / "tushare_tradeability_long_cycle_backfill_plan.json"

            self.assertEqual(result["execution_summary"]["executed_shards"], 2)
            self.assertEqual(result["execution_summary"]["failed_shards"], 0)
            self.assertTrue(progress_path.exists())
            self.assertTrue(summary_path.exists())
            progress_rows = [json.loads(line) for line in progress_path.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["start_date"], "2024-01-02")
        self.assertEqual(calls[0]["end_date"], "2024-01-31")
        self.assertTrue(calls[0]["execute_write_processed"])
        self.assertEqual(calls[0]["snapshot"], "2026-06-23")
        self.assertEqual(progress_rows[0]["shard_id"], "202401")
        self.assertEqual(progress_rows[0]["status"], "pass")

    def test_write_plan_outputs_json_and_markdown(self):
        plan = build_tushare_tradeability_backfill_plan(
            start_date="2024-01-02",
            end_date="2024-01-31",
            processed_root="data/processed/round198_tradeability_backfill",
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_tushare_tradeability_backfill_plan(plan, Path(tmp))
            self.assertTrue((Path(tmp) / "tushare_tradeability_long_cycle_backfill_plan.json").exists())
            markdown = (Path(tmp) / "tushare_tradeability_long_cycle_backfill_plan.md").read_text(encoding="utf-8")

        self.assertIn("Tushare Tradeability Long-Cycle Backfill Plan", markdown)
        self.assertIn("202401", markdown)


if __name__ == "__main__":
    unittest.main()
