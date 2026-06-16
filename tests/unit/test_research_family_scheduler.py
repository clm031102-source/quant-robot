import tempfile
import unittest
from pathlib import Path

from quant_robot.research.family_scheduler import (
    build_research_family_schedule,
    load_research_family_config,
    write_research_family_schedule,
)


class ResearchFamilySchedulerTests(unittest.TestCase):
    def test_scheduler_accepts_diversified_cn_etf_hypothesis_portfolio(self):
        config = {
            "primary_market": "CN_ETF",
            "min_active_primary_families": 3,
            "max_budget_share_per_family": 0.5,
            "stop_loss_policy": {"max_repeated_failure_rounds": 2, "max_rescue_iterations": 3},
            "families": [
                {"family_id": "momentum", "market": "CN_ETF", "status": "active", "budget_share": 0.4},
                {"family_id": "liquidity", "market": "CN_ETF", "status": "active", "budget_share": 0.35},
                {"family_id": "volatility", "market": "CN_ETF", "status": "exploratory", "budget_share": 0.25},
                {
                    "family_id": "cn_stock_moneyflow_selection",
                    "market": "CN",
                    "status": "auxiliary_only",
                    "budget_share": 0.0,
                    "failed_rounds": 5,
                    "rescue_iterations": 4,
                    "failure_reasons": ["capacity_limited", "oos_relative_return_failed", "cost_sensitive"],
                },
            ],
        }

        pack = build_research_family_schedule(config)

        self.assertEqual(pack["summary"]["scheduler_status"], "ready")
        self.assertEqual(pack["summary"]["active_primary_families"], 3)
        self.assertEqual(pack["blockers"], [])
        moneyflow = next(row for row in pack["families"] if row["family_id"] == "cn_stock_moneyflow_selection")
        self.assertEqual(moneyflow["allocation_status"], "auxiliary_only")
        self.assertFalse(moneyflow["primary_allocation_allowed"])

    def test_scheduler_blocks_stop_lossed_family_with_budget(self):
        config = {
            "min_active_primary_families": 1,
            "stop_loss_policy": {"max_repeated_failure_rounds": 2, "max_rescue_iterations": 3},
            "families": [
                {
                    "family_id": "cn_stock_moneyflow_selection",
                    "market": "CN",
                    "status": "active",
                    "budget_share": 0.2,
                    "failed_rounds": 3,
                    "rescue_iterations": 3,
                    "failure_reasons": ["capacity_limited", "oos_relative_return_failed", "cost_sensitive"],
                }
            ],
        }

        pack = build_research_family_schedule(config)

        self.assertEqual(pack["summary"]["scheduler_status"], "blocked")
        self.assertIn("cn_stock_moneyflow_selection_stop_lossed_but_still_budgeted", pack["blockers"])
        family = pack["families"][0]
        self.assertTrue(family["stop_loss_triggered"])
        self.assertIn("research_family_stop_loss", family["stop_loss_reasons"])
        self.assertIn("rescue_iteration_limit_reached", family["stop_loss_reasons"])

    def test_scheduler_requires_multiple_active_research_families(self):
        config = {
            "min_active_primary_families": 3,
            "families": [
                {"family_id": "momentum", "market": "CN_ETF", "status": "active", "budget_share": 1.0},
            ],
        }

        pack = build_research_family_schedule(config)

        self.assertEqual(pack["summary"]["scheduler_status"], "blocked")
        self.assertIn("insufficient_active_research_families", pack["blockers"])

    def test_load_and_write_scheduler_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "scheduler.json"
            config_path.write_text(
                """{
  "primary_market": "CN_ETF",
  "min_active_primary_families": 1,
  "families": [
    {"family_id": "momentum", "market": "CN_ETF", "status": "active", "budget_share": 1.0}
  ]
}
""",
                encoding="utf-8",
            )

            pack = build_research_family_schedule(load_research_family_config(config_path))
            write_research_family_schedule(root / "out", pack)

            self.assertTrue((root / "out" / "research_family_schedule_pack.json").exists())
            self.assertTrue((root / "out" / "research_family_schedule_pack.md").exists())
            self.assertTrue((root / "out" / "research_family_schedule_families.csv").exists())


if __name__ == "__main__":
    unittest.main()
