import unittest

import pandas as pd

from quant_robot.ops.bar_factor_clean_portfolio_diagnostic import build_bar_factor_frames
from quant_robot.ops.clean_technical_portfolio_diagnostic import forward_trade_frame, run_fast_factor_backtest


def _bars(asset_count: int = 8, day_count: int = 90) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-02", periods=day_count)
    rows = []
    for asset_idx in range(asset_count):
        for day_idx, date in enumerate(dates):
            close = 10.0 + asset_idx * 0.5 + day_idx * (0.03 + asset_idx * 0.003)
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
                    "volume": 1_000_000.0 + asset_idx * 20_000.0,
                    "amount": 50_000_000.0 + asset_idx * 2_000_000.0,
                    "vwap": close,
                }
            )
    return pd.DataFrame(rows)


class BarFactorCleanPortfolioDiagnosticTests(unittest.TestCase):
    def test_public_bar_factor_frames_attach_capacity_fields(self) -> None:
        bars = _bars()

        factors = build_bar_factor_frames(
            bars,
            candidate_factor_names=("fip_smooth_momentum_quality_60_20",),
            min_signal_date_amount=1.0,
        )

        frame = factors["fip_smooth_momentum_quality_60_20"]
        self.assertFalse(frame.empty)
        self.assertIn("amount", frame.columns)
        self.assertIn("adv20_amount", frame.columns)

    def test_public_bar_factor_can_run_fast_backtest(self) -> None:
        bars = _bars()
        factors = build_bar_factor_frames(
            bars,
            candidate_factor_names=("fip_smooth_momentum_quality_60_20",),
            min_signal_date_amount=1.0,
        )["fip_smooth_momentum_quality_60_20"]
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


if __name__ == "__main__":
    unittest.main()
