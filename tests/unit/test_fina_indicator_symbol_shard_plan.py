import unittest

from quant_robot.ops.fina_indicator_symbol_shard_plan import build_fina_indicator_symbol_shard_plan


class FinaIndicatorSymbolShardPlanTests(unittest.TestCase):
    def test_builds_deterministic_symbol_shards(self) -> None:
        plan = build_fina_indicator_symbol_shard_plan(
            symbols=["600519.SH", "000001.SZ", "920001.BJ", "000002.SZ", "600000.SH"],
            start_period="2024-03-31",
            end_period="2024-06-30",
            symbols_per_shard=2,
            max_requests_per_shard=4,
            exclude_suffixes=["BJ"],
        )

        self.assertTrue(plan["summary"]["passes"])
        self.assertEqual(plan["summary"]["symbol_count"], 4)
        self.assertEqual(plan["summary"]["period_count"], 2)
        self.assertEqual(plan["summary"]["total_request_count"], 8)
        self.assertEqual(plan["summary"]["shard_count"], 2)
        self.assertEqual(plan["excluded_symbols"], ["920001.BJ"])
        self.assertEqual(plan["shards"][0]["symbols"], ["000001.SZ", "000002.SZ"])
        self.assertEqual(plan["shards"][0]["request_count"], 4)
        self.assertEqual(plan["shards"][1]["symbols"], ["600000.SH", "600519.SH"])

    def test_blocks_shards_that_exceed_request_budget(self) -> None:
        plan = build_fina_indicator_symbol_shard_plan(
            symbols=["000001.SZ", "000002.SZ", "600000.SH"],
            start_period="2024-03-31",
            end_period="2024-06-30",
            symbols_per_shard=3,
            max_requests_per_shard=5,
        )

        self.assertFalse(plan["summary"]["passes"])
        self.assertIn("shard_request_count_exceeds_budget", plan["summary"]["blockers"])


if __name__ == "__main__":
    unittest.main()
