import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from quant_robot.experiments.runner import ExperimentGridConfig
from quant_robot.ops.etf_validation_preflight import (
    ETFValidationPreflightPolicy,
    build_etf_validation_preflight,
    write_etf_validation_preflight,
)
from quant_robot.validation.walk_forward import WalkForwardConfig


class ETFValidationPreflightTests(unittest.TestCase):
    def test_blocks_narrow_universe_and_low_regime_fold_coverage(self) -> None:
        bars = _bars(asset_count=4, benchmark_trend="late_only")
        config = _config()

        packet = build_etf_validation_preflight(
            bars,
            config,
            policy=ETFValidationPreflightPolicy(
                min_assets=5,
                min_rebalance_opportunities_per_fold=4,
                min_median_allowed_rebalance_dates=4,
                max_zero_allowed_fold_rate=0.0,
            ),
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertFalse(packet["decision"]["preflight_cleared"])
        self.assertIn("asset_count_below_minimum", packet["decision"]["blockers"])
        self.assertIn("median_regime_allowed_rebalance_dates_below_minimum", packet["decision"]["blockers"])
        self.assertIn("zero_allowed_fold_rate_above_limit", packet["decision"]["blockers"])
        self.assertEqual(packet["summary"]["asset_count"], 4)
        self.assertEqual(packet["summary"]["fold_count"], 3)

    def test_clears_when_universe_and_regime_coverage_are_sufficient(self) -> None:
        bars = _bars(asset_count=6, benchmark_trend="up")
        config = _config()

        packet = build_etf_validation_preflight(
            bars,
            config,
            policy=ETFValidationPreflightPolicy(
                min_assets=5,
                min_rebalance_opportunities_per_fold=4,
                min_median_allowed_rebalance_dates=4,
                max_zero_allowed_fold_rate=0.0,
            ),
        )

        self.assertEqual(packet["status"], "cleared")
        self.assertTrue(packet["decision"]["preflight_cleared"])
        self.assertEqual(packet["decision"]["blockers"], [])
        self.assertGreaterEqual(packet["summary"]["median_allowed_rebalance_dates"], 4)

    def test_write_preflight_packet_writes_json_and_markdown(self) -> None:
        packet = build_etf_validation_preflight(
            _bars(asset_count=6, benchmark_trend="up"),
            _config(),
            policy=ETFValidationPreflightPolicy(min_assets=5),
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_etf_validation_preflight(Path(tmp), packet)

            self.assertTrue((Path(tmp) / "etf_validation_preflight.json").exists())
            self.assertTrue((Path(tmp) / "etf_validation_preflight.md").exists())


def _config() -> WalkForwardConfig:
    return WalkForwardConfig(
        split_date="2024-01-01",
        experiment_grid=ExperimentGridConfig(
            markets=("CN_ETF",),
            factor_names=("momentum_2",),
            factor_windows=(2,),
            top_n_values=(2,),
            cost_bps_values=(5.0,),
            rebalance_intervals=(2,),
            benchmark_asset_id="ETF_000",
            regime_filter=True,
            regime_lookback_values=(3,),
        ),
        min_test_trades=4,
        rolling_train_days=10,
        rolling_test_days=10,
        rolling_step_days=10,
        min_accepted_folds=2,
    )


def _bars(*, asset_count: int, benchmark_trend: str) -> pd.DataFrame:
    start = date(2024, 1, 1)
    rows = []
    for day in range(40):
        current_date = start + timedelta(days=day)
        if benchmark_trend == "up":
            benchmark_close = 100.0 + day
        elif benchmark_trend == "late_only":
            benchmark_close = 100.0 - min(day, 29) + max(day - 29, 0) * 2.0
        else:
            raise ValueError(f"Unsupported benchmark trend: {benchmark_trend}")
        for asset_index in range(asset_count):
            asset_id = f"ETF_{asset_index:03d}"
            close = benchmark_close + asset_index * 0.1
            rows.append(
                {
                    "date": current_date.isoformat(),
                    "timestamp": pd.Timestamp(current_date),
                    "asset_id": asset_id,
                    "market": "CN_ETF",
                    "open": close,
                    "high": close,
                    "low": close,
                    "close": close,
                    "adj_close": close,
                    "volume": 1000 + asset_index,
                    "amount": close * (1000 + asset_index),
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
