import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.clean_technical_portfolio_diagnostic import (
    apply_market_regime_filter,
    apply_data_quality_quarantine,
    build_clean_technical_factor_frame,
    market_regime_allowed_dates,
    run_clean_technical_portfolio_diagnostic,
)


def _bars(asset_count: int = 4, day_count: int = 45) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-02", periods=day_count)
    rows = []
    for asset_idx in range(asset_count):
        asset_id = f"CN_XSHG_{asset_idx:06d}"
        for day_idx, date in enumerate(dates):
            close = 10.0 + asset_idx + day_idx * (0.20 if asset_idx == 0 else 0.04 * asset_idx)
            adj_close = 100.0 - day_idx if asset_idx == 0 else close
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "open": close,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "adj_close": adj_close,
                    "volume": 1_000_000.0,
                    "amount": 50_000_000.0,
                    "vwap": close,
                }
            )
    return pd.DataFrame(rows)


class CleanTechnicalPortfolioDiagnosticTests(unittest.TestCase):
    def test_factor_builder_uses_requested_close_price_column(self) -> None:
        factors = build_clean_technical_factor_frame(
            _bars(),
            candidate_factor_names=("momentum_5",),
            price_column="close",
            min_signal_date_amount=1.0,
        )

        first_asset = factors[factors["asset_id"] == "CN_XSHG_000000"].sort_values("date").tail(1)

        self.assertFalse(first_asset.empty)
        self.assertGreater(float(first_asset.iloc[0]["factor_value"]), 0.0)

    def test_quarantine_excludes_prefix_and_extreme_return_assets(self) -> None:
        bars = _bars(asset_count=2, day_count=10)
        prefix_rows = bars[bars["asset_id"] == "CN_XSHG_000000"].copy()
        prefix_rows["asset_id"] = "CN_XBEI_830000"
        extreme_rows = bars[bars["asset_id"] == "CN_XSHG_000001"].copy()
        extreme_rows.loc[extreme_rows.index[-1], "close"] = extreme_rows.loc[extreme_rows.index[-2], "close"] * 2.0
        frame = pd.concat([prefix_rows, extreme_rows], ignore_index=True)

        clean, report = apply_data_quality_quarantine(
            frame,
            exclude_asset_prefixes=("CN_XBEI",),
            max_abs_daily_return_quarantine=0.50,
        )

        self.assertEqual(report["excluded_assets"], 2)
        self.assertTrue(clean.empty)

    def test_market_regime_filter_reduces_signal_dates(self) -> None:
        bars = _bars(asset_count=4, day_count=40)
        factors = build_clean_technical_factor_frame(
            bars,
            candidate_factor_names=("momentum_5",),
            price_column="close",
            min_signal_date_amount=1.0,
        )
        allowed, report = market_regime_allowed_dates(
            bars,
            price_column="close",
            lookback=10,
            min_market_momentum=0.0,
        )
        filtered = apply_market_regime_filter(factors, allowed)

        self.assertTrue(report["enabled"])
        self.assertLessEqual(filtered["date"].nunique(), factors["date"].nunique())

    def test_runner_writes_structured_diagnostic_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bars_dir = root / "bars"
            bars_dir.mkdir()
            _bars(asset_count=6, day_count=50).to_csv(bars_dir / "bars.csv", index=False)
            output_dir = root / "report"

            result = run_clean_technical_portfolio_diagnostic(
                bars_roots=(root,),
                output_dir=output_dir,
                analysis_start_date="2020-01-01",
                analysis_end_date="2020-12-31",
                candidate_factor_names=("momentum_5", "defensive_reversal_5"),
                top_n_values=(1,),
                cost_bps_values=(0.0,),
                holding_period=5,
                rebalance_intervals=(1,),
                min_signal_date_amount=1.0,
                max_abs_daily_return_quarantine=None,
            )

            self.assertEqual(result["stage"], "clean_technical_portfolio_diagnostic")
            self.assertEqual(result["summary"]["candidates"], 2)
            self.assertTrue((output_dir / "clean_technical_portfolio_diagnostic.json").exists())
            self.assertTrue((output_dir / "clean_technical_portfolio_diagnostic_leaderboard.csv").exists())


if __name__ == "__main__":
    unittest.main()
