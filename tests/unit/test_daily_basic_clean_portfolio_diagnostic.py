import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_clean_portfolio_diagnostic import (
    build_daily_basic_factor_frames,
    run_fast_factor_backtest,
    write_daily_basic_clean_portfolio_diagnostic,
)
from quant_robot.ops.clean_technical_portfolio_diagnostic import forward_trade_frame


def _bars(asset_count: int = 8, day_count: int = 70) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-02", periods=day_count)
    rows = []
    for asset_idx in range(asset_count):
        for day_idx, date in enumerate(dates):
            close = 10.0 + asset_idx * 0.8 + day_idx * (0.04 + asset_idx * 0.005)
            rows.append(
                {
                    "date": date,
                    "asset_id": f"CN_XSHG_{asset_idx:06d}",
                    "market": "CN",
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "adj_close": close,
                    "volume": 1_000_000.0 + asset_idx,
                    "amount": 50_000_000.0 + asset_idx * 1_000_000.0,
                    "vwap": close,
                }
            )
    return pd.DataFrame(rows)


def _daily_basic(bars: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in bars.itertuples(index=False):
        idx = int(str(row.asset_id).rsplit("_", 1)[-1])
        rows.append(
            {
                "date": row.date,
                "asset_id": row.asset_id,
                "market": row.market,
                "turnover_rate": 1.0 + idx * 0.1,
                "turnover_rate_f": 0.8 + idx * 0.08,
                "volume_ratio": 1.0 + idx * 0.03,
                "pe": 10.0 + idx,
                "pe_ttm": 10.0 + idx,
                "pb": 1.0 + idx * 0.1,
                "ps": 2.0 + idx * 0.1,
                "ps_ttm": 2.0 + idx * 0.1,
                "dv_ratio": 0.5 + idx * 0.02,
                "dv_ttm": 0.5 + idx * 0.02,
                "total_share": 1_000_000_000.0,
                "float_share": 600_000_000.0,
                "free_share": 500_000_000.0,
                "total_mv": 10_000_000.0 + idx * 100_000.0,
                "circ_mv": 8_000_000.0 + idx * 100_000.0,
            }
        )
    return pd.DataFrame(rows)


class DailyBasicCleanPortfolioDiagnosticTests(unittest.TestCase):
    def test_build_daily_basic_factor_frames_attaches_capacity_fields(self) -> None:
        bars = _bars()
        daily_basic = _daily_basic(bars)

        factors = build_daily_basic_factor_frames(
            bars,
            daily_basic,
            candidate_factor_names=("public_qvm_value_momentum_lowvol_20",),
            min_signal_date_amount=1.0,
        )

        frame = factors["public_qvm_value_momentum_lowvol_20"]
        self.assertFalse(frame.empty)
        self.assertIn("amount", frame.columns)
        self.assertIn("adv20_amount", frame.columns)

    def test_daily_basic_carry_factor_gets_lookback_window(self) -> None:
        bars = _bars()
        daily_basic = _daily_basic(bars)

        factors = build_daily_basic_factor_frames(
            bars,
            daily_basic,
            candidate_factor_names=("daily_basic_value_yield_size_neutral_20",),
            min_signal_date_amount=1.0,
        )

        frame = factors["daily_basic_value_yield_size_neutral_20"]
        self.assertFalse(frame.empty)
        self.assertEqual(set(frame["lookback_window"]), {20})

    def test_value_yield_risk_repair_factor_builds(self) -> None:
        bars = _bars(asset_count=10, day_count=90)
        daily_basic = _daily_basic(bars)

        factors = build_daily_basic_factor_frames(
            bars,
            daily_basic,
            candidate_factor_names=("daily_basic_value_yield_lowtail_guard_20",),
            min_signal_date_amount=1.0,
        )

        frame = factors["daily_basic_value_yield_lowtail_guard_20"]
        self.assertFalse(frame.empty)
        self.assertEqual(set(frame["lookback_window"]), {20})

    def test_raw_tushare_daily_basic_factor_builds(self) -> None:
        bars = _bars()
        daily_basic = _daily_basic(bars)

        factors = build_daily_basic_factor_frames(
            bars,
            daily_basic,
            candidate_factor_names=("turnover_rate_low",),
            min_signal_date_amount=1.0,
        )

        frame = factors["turnover_rate_low"]
        self.assertFalse(frame.empty)
        self.assertEqual(set(frame["lookback_window"]), {1})

    def test_daily_basic_factor_frame_can_run_fast_portfolio_diagnostic(self) -> None:
        bars = _bars()
        daily_basic = _daily_basic(bars)
        factors = build_daily_basic_factor_frames(
            bars,
            daily_basic,
            candidate_factor_names=("public_qvm_value_momentum_lowvol_20",),
            min_signal_date_amount=1.0,
        )["public_qvm_value_momentum_lowvol_20"]
        forward = forward_trade_frame(bars, execution_lag=1, holding_period=5)

        metrics, trades = run_fast_factor_backtest(
            factors,
            forward,
            top_n=2,
            cost_bps=0.0,
            holding_period=5,
            rebalance_interval=1,
            target_gross_exposure=1.0,
            periods_per_year=252.0,
            market_impact_bps=0.0,
            max_participation_rate=0.05,
            portfolio_value=1_000_000.0,
        )

        self.assertFalse(trades.empty)
        self.assertIn("total_return", metrics)

    def test_writer_outputs_json_and_leaderboard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_daily_basic_clean_portfolio_diagnostic(
                output,
                {
                    "stage": "daily_basic_clean_portfolio_diagnostic",
                    "summary": {"cases": 0},
                    "leaderboard": [],
                },
            )

            self.assertTrue((output / "daily_basic_clean_portfolio_diagnostic.json").exists())
            self.assertTrue((output / "daily_basic_clean_portfolio_diagnostic_leaderboard.csv").exists())


if __name__ == "__main__":
    unittest.main()
