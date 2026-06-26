import unittest

from quant_robot.ops.fina_indicator_backfill_plan import build_fina_indicator_backfill_plan


class FinaIndicatorBackfillPlanTests(unittest.TestCase):
    def test_builds_quarterly_request_plan(self) -> None:
        plan = build_fina_indicator_backfill_plan(
            symbols=["000001.SZ", "600519.SH"],
            start_period="2015-03-31",
            end_period="2025-12-31",
            batch_size=20,
            max_requests=200,
        )

        self.assertEqual(plan["summary"]["period_count"], 44)
        self.assertEqual(plan["summary"]["symbol_count"], 2)
        self.assertEqual(plan["summary"]["request_count"], 88)
        self.assertEqual(plan["summary"]["batch_count"], 5)
        self.assertTrue(plan["summary"]["passes"])
        self.assertEqual(plan["periods"][0], "20150331")
        self.assertEqual(plan["periods"][-1], "20251231")
        self.assertEqual(
            plan["request_batches"][0]["requests"][0],
            {"ts_code": "000001.SZ", "period": "20150331"},
        )

    def test_blocks_when_request_budget_is_exceeded(self) -> None:
        plan = build_fina_indicator_backfill_plan(
            symbols=["000001.SZ", "600519.SH"],
            start_period="2015-03-31",
            end_period="2025-12-31",
            batch_size=20,
            max_requests=20,
        )

        self.assertFalse(plan["summary"]["passes"])
        self.assertIn("request_count_exceeds_max_requests", plan["summary"]["blockers"])


if __name__ == "__main__":
    unittest.main()
