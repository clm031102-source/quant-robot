import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.experiments.runner import ExperimentGridConfig, run_experiment_grid
from quant_robot.ops.etf_liquid_universe import (
    ETFLiquidUniversePolicy,
    build_etf_liquid_universe,
    write_etf_liquid_universe,
)
from scripts.run_etf_liquid_universe_filter import run_etf_liquid_universe_filter


class ETFLiquidUniverseTests(unittest.TestCase):
    def test_selects_only_assets_that_pass_continuity_liquidity_quality_filters(self) -> None:
        packet = build_etf_liquid_universe(
            _bars(),
            market="CN_ETF",
            policy=ETFLiquidUniversePolicy(
                min_history_days=8,
                recent_window_days=5,
                min_recent_observations=4,
                min_recent_amount=1_000.0,
                max_stale_price_rate=0.20,
                max_extreme_return_rate=0.0,
                extreme_return_threshold=0.20,
                min_selected_assets=1,
                required_asset_ids=("ETF_GOOD",),
            ),
        )

        self.assertEqual(packet["status"], "cleared")
        self.assertEqual(packet["selected_asset_ids"], ["ETF_GOOD"])
        assets = {row["asset_id"]: row for row in packet["assets"]}
        self.assertEqual(assets["ETF_GOOD"]["rejection_reasons"], [])
        self.assertIn("history_days_below_minimum", assets["ETF_SHORT"]["rejection_reasons"])
        self.assertIn("recent_amount_below_minimum", assets["ETF_ILLQ"]["rejection_reasons"])
        self.assertIn("stale_price_rate_above_limit", assets["ETF_STALE"]["rejection_reasons"])
        self.assertIn("extreme_return_rate_above_limit", assets["ETF_EXTREME"]["rejection_reasons"])

    def test_blocks_when_required_asset_is_rejected_or_selected_count_is_too_low(self) -> None:
        packet = build_etf_liquid_universe(
            _bars(),
            market="CN_ETF",
            policy=ETFLiquidUniversePolicy(
                min_history_days=8,
                recent_window_days=5,
                min_recent_observations=4,
                min_recent_amount=1_000.0,
                max_stale_price_rate=0.20,
                max_extreme_return_rate=0.0,
                extreme_return_threshold=0.20,
                min_selected_assets=2,
                required_asset_ids=("ETF_STALE",),
            ),
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertIn("selected_asset_count_below_minimum", packet["decision"]["blockers"])
        self.assertIn("required_asset_rejected:ETF_STALE", packet["decision"]["blockers"])

    def test_write_universe_packet_writes_json_markdown_and_asset_list(self) -> None:
        packet = build_etf_liquid_universe(
            _bars(),
            market="CN_ETF",
            policy=ETFLiquidUniversePolicy(
                min_history_days=8,
                recent_window_days=5,
                min_recent_observations=4,
                min_recent_amount=1_000.0,
                max_stale_price_rate=0.20,
                max_extreme_return_rate=0.0,
                extreme_return_threshold=0.20,
                min_selected_assets=1,
            ),
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_etf_liquid_universe(Path(tmp), packet)

            self.assertTrue((Path(tmp) / "etf_liquid_universe.json").exists())
            self.assertTrue((Path(tmp) / "etf_liquid_universe.md").exists())
            self.assertEqual((Path(tmp) / "selected_asset_ids.txt").read_text(encoding="utf-8").strip(), "ETF_GOOD")


class ExperimentGridAssetUniverseTests(unittest.TestCase):
    def test_experiment_grid_filters_bars_by_asset_universe_before_precompute_and_pipeline(self) -> None:
        bars = _runner_bars()
        matrix = pd.DataFrame(columns=["date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"])
        pipeline_result = {
            "data_mode": "research",
            "metrics": {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "annualized_volatility": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
            },
            "benchmark_metrics": {"benchmark_total_return": 0.0, "relative_return": 0.0, "excess_over_cash": 0.0},
            "decision": {"decision_status": "approved", "rejection_reasons": []},
            "factor_summary": {"mean_ic": 0.0, "ic_p_value": 1.0, "significance_status": "unknown"},
            "artifact_rows": {"trades": 1, "holdings": 1},
        }

        with tempfile.TemporaryDirectory() as tmp:
            universe_path = Path(tmp) / "universe.json"
            universe_path.write_text(json.dumps({"selected_asset_ids": ["ETF_KEEP"]}), encoding="utf-8")
            config = ExperimentGridConfig(
                markets=("CN_ETF",),
                factor_names=("momentum_2",),
                factor_windows=(2,),
                top_n_values=(1,),
                cost_bps_values=(0.0,),
                asset_universe_path=universe_path,
                precompute_factor_matrix=True,
            )

            with (
                patch("quant_robot.experiments.runner.compute_basic_factors", return_value=matrix) as factor_builder,
                patch("quant_robot.experiments.runner.run_research_pipeline", return_value=pipeline_result) as pipeline,
            ):
                result = run_experiment_grid(bars, config)

        self.assertEqual(result["config"]["asset_universe_path"], str(universe_path))
        self.assertEqual(set(factor_builder.call_args.args[0]["asset_id"]), {"ETF_KEEP"})
        self.assertEqual(set(pipeline.call_args.args[0]["asset_id"]), {"ETF_KEEP"})


class ETFLiquidUniverseCliTests(unittest.TestCase):
    def test_run_filter_loads_processed_bars_and_writes_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "universe"
            with patch("scripts.run_etf_liquid_universe_filter.load_processed_bars", return_value=_bars()) as loader:
                packet = run_etf_liquid_universe_filter(
                    source="processed-bars",
                    data_root=Path(tmp),
                    market="CN_ETF",
                    output_dir=output_dir,
                    min_history_days=8,
                    recent_window_days=5,
                    min_recent_observations=4,
                    min_recent_amount=1_000.0,
                    max_stale_price_rate=0.20,
                    max_extreme_return_rate=0.0,
                    extreme_return_threshold=0.20,
                    min_selected_assets=1,
                )

                loader.assert_called_once_with(Path(tmp), "CN_ETF")
                self.assertEqual(packet["stage"], "cn_etf_liquid_universe_filter")
                self.assertTrue((output_dir / "etf_liquid_universe.json").exists())


def _bars() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    paths = {
        "ETF_GOOD": [10.0 + i * 0.1 for i in range(10)],
        "ETF_SHORT": [10.0 + i * 0.1 for i in range(4)],
        "ETF_ILLQ": [10.0 + i * 0.1 for i in range(10)],
        "ETF_STALE": [10.0 for _ in range(10)],
        "ETF_EXTREME": [10.0, 10.1, 10.2, 15.0, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8],
    }
    for asset_id, prices in paths.items():
        for date, price in zip(dates, prices, strict=False):
            volume = 10.0 if asset_id == "ETF_ILLQ" else 1_000.0
            rows.append(
                {
                    "date": date.date(),
                    "timestamp": date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN_ETF",
                    "source": "fixture",
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "adj_close": price,
                    "volume": volume,
                    "amount": price * volume,
                }
            )
    return pd.DataFrame(rows)


def _runner_bars() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=5, freq="B")
    for asset_id in ("ETF_KEEP", "ETF_DROP"):
        for day, current_date in enumerate(dates):
            price = 10.0 + day * 0.1
            rows.append(
                {
                    "date": current_date.date(),
                    "timestamp": current_date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN_ETF",
                    "source": "fixture",
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "adj_close": price,
                    "volume": 1_000.0,
                    "amount": price * 1_000.0,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
