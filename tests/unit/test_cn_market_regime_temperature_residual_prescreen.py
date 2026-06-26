import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_market_regime_temperature_preregistration import (
    default_cn_market_regime_temperature_specs,
)
from quant_robot.ops.cn_market_regime_temperature_residual_prescreen import (
    build_cn_market_regime_temperature_feature_frame,
    summarize_cn_market_regime_temperature_residual_prescreen_from_features,
    write_cn_market_regime_temperature_residual_prescreen,
)


def _bars(days: int = 90, assets: int = 6) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-01", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset = f"CN_TEST_{asset_idx:03d}"
        price = 10.0 + asset_idx
        for day_idx, dt in enumerate(dates):
            drift = 0.001 * (asset_idx + 1) + (0.002 if day_idx > 45 and asset_idx % 2 == 0 else -0.001)
            price *= 1.0 + drift
            rows.append(
                {
                    "date": dt.strftime("%Y-%m-%d"),
                    "asset_id": asset,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "open": price * 0.99,
                    "high": price * 1.01,
                    "low": price * 0.98,
                    "close": price,
                    "adj_close": price,
                    "volume": 100000 + asset_idx * 1000 + day_idx * 50,
                    "amount": (100000 + asset_idx * 1000 + day_idx * 50) * price,
                }
            )
    return pd.DataFrame(rows)


def _stock_basic(assets: int = 6) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": [f"CN_TEST_{idx:03d}" for idx in range(assets)],
            "symbol": [f"{idx:06d}.SZ" for idx in range(assets)],
            "industry": ["Tech" if idx % 2 == 0 else "Finance" for idx in range(assets)],
            "list_date": ["20100101"] * assets,
        }
    )


def _factor_inputs(bars: pd.DataFrame) -> pd.DataFrame:
    frame = bars[["date", "asset_id", "market"]].copy()
    frame["pb"] = 1.0 + frame["asset_id"].str.extract(r"(\d+)$").astype(float)[0] * 0.1
    return frame


class CNMarketRegimeTemperatureResidualPrescreenTests(unittest.TestCase):
    def test_feature_frame_uses_lagged_market_temperature_state(self) -> None:
        features = build_cn_market_regime_temperature_feature_frame(
            _bars(days=40, assets=4),
            factor_inputs=_factor_inputs(_bars(days=40, assets=4)),
            stock_basic=_stock_basic(4),
            execution_lag=1,
            market_z_window=5,
        )

        state_by_date = (
            features[["date", "mkt_liquidity_temp_z", "lag_mkt_liquidity_temp_z"]]
            .drop_duplicates("date")
            .sort_values("date")
            .reset_index(drop=True)
        )
        row = state_by_date.iloc[10]
        previous = state_by_date.iloc[9]

        self.assertAlmostEqual(row["lag_mkt_liquidity_temp_z"], previous["mkt_liquidity_temp_z"])

    def test_residual_prescreen_summarizes_candidates_without_portfolio_or_promotion(self) -> None:
        bars = _bars()
        features = build_cn_market_regime_temperature_feature_frame(
            bars,
            factor_inputs=_factor_inputs(bars),
            stock_basic=_stock_basic(),
            execution_lag=1,
            market_z_window=20,
        )

        result = summarize_cn_market_regime_temperature_residual_prescreen_from_features(
            features,
            stock_basic=_stock_basic(),
            candidate_specs=default_cn_market_regime_temperature_specs(),
            horizons=(5,),
            sample_every_n_dates=5,
            min_cross_section=2,
            min_ic_observations=2,
            min_signal_date_amount=0,
            min_industries=2,
            min_assets_per_industry=2,
        )

        self.assertEqual(result["stage"], "cn_market_regime_temperature_residual_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 6)
        self.assertEqual(result["summary"]["test_count"], 6)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_grid_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertTrue(all(row["promotion_allowed"] is False for row in result["results"]))
        self.assertTrue(all(row["portfolio_grid_allowed"] is False for row in result["results"]))

    def test_write_outputs(self) -> None:
        bars = _bars()
        features = build_cn_market_regime_temperature_feature_frame(
            bars,
            factor_inputs=_factor_inputs(bars),
            stock_basic=_stock_basic(),
            market_z_window=20,
        )
        result = summarize_cn_market_regime_temperature_residual_prescreen_from_features(
            features,
            stock_basic=_stock_basic(),
            candidate_specs=default_cn_market_regime_temperature_specs(),
            horizons=(5,),
            sample_every_n_dates=5,
            min_cross_section=2,
            min_ic_observations=2,
            min_signal_date_amount=0,
            min_industries=2,
            min_assets_per_industry=2,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_cn_market_regime_temperature_residual_prescreen(output, result)
            self.assertTrue((output / "cn_market_regime_temperature_residual_prescreen.json").exists())
            self.assertTrue((output / "cn_market_regime_temperature_residual_prescreen.md").exists())
            self.assertTrue((output / "cn_market_regime_temperature_residual_prescreen_results.csv").exists())


if __name__ == "__main__":
    unittest.main()
