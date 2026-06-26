import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_turnover_repair_champion_portfolio_conversion import (
    run_turnover_repair_champion_portfolio_conversion_cli,
)
from tests.unit.test_turnover_continuous_capacity_repair_prescreen import (
    _synthetic_bars_and_daily_basic,
)


class TurnoverRepairChampionPortfolioConversionCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_leaderboard_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            factor_root = Path(tmp) / "daily_basic"
            output = Path(tmp) / "output"
            bars, daily_basic = _synthetic_bars_and_daily_basic(days=80, assets=20)
            DatasetStore(root).write_frame(
                bars,
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(factor_root).write_frame(
                daily_basic,
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_turnover_repair_champion_portfolio_conversion_cli(
                bars_roots=[root],
                factor_input_root=factor_root,
                output_dir=output,
                analysis_end_date="2025-12-31",
                cost_bps_values=(0.0,),
                portfolio_values=(100_000.0,),
                top_n=5,
                holding_period=5,
                rebalance_interval=5,
                min_signal_amount=0.0,
                min_signal_date_amount=10_000_000,
                max_calendar_holding_days=15,
                min_overlap_adjusted_sharpe=-10.0,
            )

            self.assertEqual(result["stage"], "turnover_repair_champion_portfolio_conversion")
            self.assertTrue((output / "turnover_repair_champion_portfolio_conversion.json").exists())
            self.assertTrue((output / "turnover_repair_champion_portfolio_conversion.md").exists())
            self.assertTrue((output / "turnover_repair_champion_portfolio_conversion_leaderboard.csv").exists())
            payload = json.loads(
                (output / "turnover_repair_champion_portfolio_conversion.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["case_count"], 1)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])

    def test_cli_accepts_official_stk_limit_masks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            factor_root = Path(tmp) / "daily_basic"
            output = Path(tmp) / "output"
            official_root = Path(tmp) / "official"
            bars, daily_basic = _synthetic_bars_and_daily_basic(days=80, assets=20)
            DatasetStore(root).write_frame(
                bars,
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(factor_root).write_frame(
                daily_basic,
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            stk_limit_path = official_root / "stk_limit.csv"
            official_root.mkdir(parents=True)
            limit_frame = bars[["date", "asset_id", "adj_close"]].copy()
            limit_frame["up_limit"] = limit_frame["adj_close"]
            limit_frame["down_limit"] = limit_frame["adj_close"] * 0.9
            limit_frame = limit_frame.drop(columns=["adj_close"])
            limit_frame.to_csv(stk_limit_path, index=False)

            result = run_turnover_repair_champion_portfolio_conversion_cli(
                bars_roots=[root],
                factor_input_root=factor_root,
                stk_limit_path=stk_limit_path,
                output_dir=output,
                analysis_end_date="2025-12-31",
                cost_bps_values=(10.0,),
                portfolio_values=(100_000.0,),
                top_n=1,
                holding_period=5,
                rebalance_interval=5,
                min_signal_amount=0.0,
                min_signal_date_amount=10_000_000,
                max_calendar_holding_days=15,
                min_overlap_adjusted_sharpe=-10.0,
            )

            row = result["leaderboard"][0]
            self.assertGreaterEqual(row["trades_filtered_entry_tradeability"], 1)
            self.assertGreaterEqual(result["summary"]["max_tradeability_filtered_trades"], 1)

    def test_cli_reuses_precomputed_tradeability_mask_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            factor_root = Path(tmp) / "daily_basic"
            mask_root = Path(tmp) / "mask_cache"
            output = Path(tmp) / "output"
            bars, daily_basic = _synthetic_bars_and_daily_basic(days=80, assets=20)
            DatasetStore(root).write_frame(
                bars,
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            DatasetStore(factor_root).write_frame(
                daily_basic,
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            masks = bars[["date", "asset_id", "market"]].copy()
            masks["entry_tradeable"] = False
            masks["exit_tradeable"] = True
            DatasetStore(mask_root).write_frame(
                masks,
                "processed/tradeability_masks",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_turnover_repair_champion_portfolio_conversion_cli(
                bars_roots=[root],
                factor_input_root=factor_root,
                tradeability_mask_path=mask_root,
                output_dir=output,
                analysis_end_date="2025-12-31",
                cost_bps_values=(10.0,),
                portfolio_values=(100_000.0,),
                top_n=1,
                holding_period=5,
                rebalance_interval=5,
                min_signal_amount=0.0,
                min_signal_date_amount=10_000_000,
                max_calendar_holding_days=15,
                min_overlap_adjusted_sharpe=-10.0,
            )

            row = result["leaderboard"][0]
            self.assertEqual(row["trades"], 0)
            self.assertGreater(row["trades_filtered_entry_tradeability"], 0)
            self.assertGreater(result["summary"]["max_tradeability_filtered_trades"], 0)
            payload = json.loads(
                (output / "turnover_repair_champion_portfolio_conversion.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["input_paths"]["tradeability_mask_path"], str(mask_root))
            self.assertEqual(payload["input_paths"]["bars_roots"], [str(root)])
            self.assertEqual(payload["input_paths"]["factor_input_root"], str(factor_root))


if __name__ == "__main__":
    unittest.main()
