import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.external_feed_backfill_plan import build_external_feed_backfill_plan, write_external_feed_backfill_plan


class ExternalFeedBackfillPlanTests(unittest.TestCase):
    def test_builds_monthly_shards_with_endpoint_call_estimates_and_commands(self):
        plan = build_external_feed_backfill_plan(
            start_date="2025-01-01",
            end_date="2025-03-31",
            output_root="data/processed/external_feed_backfill_round172",
            shard_months=1,
            max_estimated_business_days_per_shard=25,
        )

        self.assertEqual(plan["stage"], "external_feed_long_cycle_backfill_plan")
        self.assertEqual(plan["status"], "ready")
        self.assertEqual(plan["summary"]["shard_count"], 3)
        self.assertGreater(plan["summary"]["total_estimated_endpoint_calls"], 0)
        first = plan["shards"][0]
        self.assertEqual(first["shard_id"], "202501")
        self.assertEqual(first["start_date"], "2025-01-01")
        self.assertEqual(first["end_date"], "2025-01-31")
        self.assertEqual(first["processed_output_dir"], "data\\processed\\external_feed_backfill_round172")
        self.assertIn("--output-dir data\\processed\\external_feed_backfill_round172", first["command"])
        self.assertIn("--report-copy-dir", first["command"])
        self.assertIn("--execute-write-processed", first["command"])
        self.assertIn("run_tushare_external_feed_ingest.py", first["command"])
        self.assertIn("external_feed_portfolio_grid_before_long_cycle_backfill_coverage", plan["blocked_uses"])

    def test_marks_plan_blocked_when_shards_exceed_budget(self):
        plan = build_external_feed_backfill_plan(
            start_date="2025-01-01",
            end_date="2025-03-31",
            output_root="data/processed/external_feed_backfill_round172",
            shard_months=3,
            max_estimated_business_days_per_shard=20,
        )

        self.assertEqual(plan["status"], "blocked")
        self.assertIn("shard_estimated_business_days_over_budget", plan["blockers"])

    def test_write_plan_outputs_json_and_markdown(self):
        plan = build_external_feed_backfill_plan(
            start_date="2025-01-01",
            end_date="2025-01-31",
            output_root="data/processed/external_feed_backfill_round172",
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_external_feed_backfill_plan(plan, Path(tmp))
            self.assertTrue((Path(tmp) / "external_feed_long_cycle_backfill_plan.json").exists())
            markdown = (Path(tmp) / "external_feed_long_cycle_backfill_plan.md").read_text(encoding="utf-8")

        self.assertIn("External Feed Long-Cycle Backfill Plan", markdown)
        self.assertIn("202501", markdown)


if __name__ == "__main__":
    unittest.main()
