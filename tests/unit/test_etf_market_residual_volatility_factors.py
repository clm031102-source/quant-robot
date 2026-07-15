import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from quant_robot.factors.etf_market_residual_volatility import (
    ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES,
    ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES,
    compute_etf_market_residual_volatility_factors,
    compute_etf_market_residual_volatility_references,
    compute_point_in_time_etf_market_proxy,
)
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


class EtfMarketResidualVolatilityFactorTests(unittest.TestCase):
    def test_market_proxy_uses_only_same_day_eligible_assets_and_median(self) -> None:
        bars = _bars(day_count=8, asset_count=5)
        dates = sorted(pd.to_datetime(bars["date"]).unique())
        target_date = pd.Timestamp(dates[-1])
        eligible_assets = [
            "CN_ETF_XSHG_510000",
            "CN_ETF_XSHG_510001",
            "CN_ETF_XSHG_510002",
        ]
        eligible_keys = bars[
            bars["asset_id"].isin(eligible_assets)
            & pd.to_datetime(bars["date"]).eq(target_date)
        ][["date", "asset_id", "market"]]
        ineligible_target = (
            bars["asset_id"].eq("CN_ETF_XSHG_510004")
            & pd.to_datetime(bars["date"]).eq(target_date)
        )
        bars.loc[ineligible_target, "adj_close"] *= 20.0

        proxy = compute_point_in_time_etf_market_proxy(
            bars,
            eligible_keys=eligible_keys,
            min_cross_section=3,
        )

        returns = (
            bars.sort_values(["asset_id", "date"])
            .groupby("asset_id", sort=False)["adj_close"]
            .pct_change()
        )
        expected = float(
            returns.loc[
                pd.to_datetime(bars["date"]).eq(target_date)
                & bars["asset_id"].isin(eligible_assets)
            ].median()
        )
        self.assertEqual(len(proxy), 1)
        self.assertEqual(int(proxy.iloc[0]["eligible_asset_count"]), 3)
        self.assertAlmostEqual(float(proxy.iloc[0]["market_return"]), expected)

    def test_exports_frozen_names_and_exact_formulas(self) -> None:
        bars = _bars(day_count=210, asset_count=7)
        eligible_keys = bars[["date", "asset_id", "market"]]

        factors = compute_etf_market_residual_volatility_factors(
            bars,
            eligible_keys=eligible_keys,
            market_proxy_min_cross_section=5,
        )

        self.assertEqual(
            tuple(sorted(factors["factor_name"].unique())),
            tuple(sorted(ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES)),
        )
        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        target_asset = "CN_ETF_XSHG_510003"
        target_date = pd.Timestamp(bars["date"].max())
        expected = _expected_features(bars, target_asset=target_asset)

        self.assertAlmostEqual(
            _factor_value(factors, target_asset, target_date, "etf_idio_vol_low_60"),
            -float(expected.iloc[-1]["residual_vol_60"]),
            places=12,
        )
        self.assertAlmostEqual(
            _factor_value(factors, target_asset, target_date, "etf_downside_beta_low_120"),
            -float(expected.iloc[-1]["downside_beta_120"]),
            places=12,
        )
        self.assertAlmostEqual(
            _factor_value(factors, target_asset, target_date, "etf_positive_residual_skew_60"),
            float(expected.iloc[-1]["residual_skew_60"]),
            places=12,
        )

    def test_future_rows_do_not_change_historical_values(self) -> None:
        baseline_bars = _bars(day_count=210, asset_count=7)
        future_bars = _bars(day_count=211, asset_count=7, future_spike=True)
        baseline_keys = baseline_bars[["date", "asset_id", "market"]]
        future_keys = future_bars[["date", "asset_id", "market"]]

        baseline = compute_etf_market_residual_volatility_factors(
            baseline_bars,
            eligible_keys=baseline_keys,
            market_proxy_min_cross_section=5,
        )
        observed = compute_etf_market_residual_volatility_factors(
            future_bars,
            eligible_keys=future_keys,
            market_proxy_min_cross_section=5,
        )
        cutoff = pd.Timestamp(baseline_bars["date"].max())
        observed = observed[pd.to_datetime(observed["date"]).le(cutoff)]

        assert_frame_equal(
            baseline.reset_index(drop=True),
            observed.reset_index(drop=True),
            check_exact=False,
            rtol=1e-12,
            atol=1e-12,
        )

    def test_materializes_only_requested_point_in_time_keys(self) -> None:
        bars = _bars(day_count=210, asset_count=7)
        cutoff = sorted(pd.to_datetime(bars["date"]).unique())[-12]
        eligible_keys = bars[
            bars["asset_id"].isin(
                [
                    "CN_ETF_XSHG_510000",
                    "CN_ETF_XSHG_510001",
                    "CN_ETF_XSHG_510002",
                    "CN_ETF_XSHG_510003",
                    "CN_ETF_XSHG_510004",
                ]
            )
            & pd.to_datetime(bars["date"]).ge(pd.Timestamp(cutoff))
        ][["date", "asset_id", "market"]]

        factors = compute_etf_market_residual_volatility_factors(
            bars,
            eligible_keys=eligible_keys,
            market_proxy_min_cross_section=5,
        )
        references = compute_etf_market_residual_volatility_references(
            bars,
            eligible_keys=eligible_keys,
        )

        expected_keys = {
            (pd.Timestamp(row.date).date(), row.asset_id, row.market)
            for row in eligible_keys.itertuples(index=False)
        }
        factor_keys = {(row.date, row.asset_id, row.market) for row in factors.itertuples(index=False)}
        reference_keys = {
            (row.date, row.asset_id, row.market) for row in references.itertuples(index=False)
        }
        self.assertEqual(factor_keys, expected_keys)
        self.assertEqual(reference_keys, expected_keys)
        self.assertEqual(len(factors), len(expected_keys) * len(ETF_MARKET_RESIDUAL_VOLATILITY_FACTOR_NAMES))
        self.assertEqual(
            len(references),
            len(expected_keys) * len(ETF_MARKET_RESIDUAL_VOLATILITY_REFERENCE_NAMES),
        )

    def test_direct_technical_references_match_existing_implementation(self) -> None:
        bars = _bars(day_count=210, asset_count=7)
        eligible_keys = bars[["date", "asset_id", "market"]]
        observed = compute_etf_market_residual_volatility_references(
            bars,
            eligible_keys=eligible_keys,
        )
        direct_names = (
            "low_volatility_20",
            "low_volatility_60",
            "low_downside_volatility_60",
            "drawdown_resilience_60",
            "crash_recovery_60",
            "recovery_quality_60",
        )
        expected = compute_basic_factors(
            bars,
            windows=(20, 60),
            factor_names=direct_names,
        )
        expected = expected[expected["factor_name"].isin(direct_names)]
        observed = observed[observed["factor_name"].isin(direct_names)]
        keys = ["date", "asset_id", "market", "factor_name", "lookback_window"]
        merged = expected.merge(
            observed,
            on=keys,
            how="outer",
            suffixes=("_expected", "_observed"),
            validate="one_to_one",
        )
        self.assertTrue(
            np.allclose(
                merged["factor_value_expected"],
                merged["factor_value_observed"],
                equal_nan=True,
                rtol=1e-12,
                atol=1e-12,
            )
        )


def _bars(*, day_count: int, asset_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2023-01-02", periods=day_count)
    rows = []
    prices = [1.0 + asset_index * 0.15 for asset_index in range(asset_count)]
    for day_index, signal_date in enumerate(dates):
        common = 0.004 * np.sin(day_index / 3.0) - 0.002 * np.cos(day_index / 7.0)
        for asset_index in range(asset_count):
            loading = 0.55 + asset_index * 0.12
            residual = 0.0015 * np.sin(day_index / (2.0 + asset_index * 0.15) + asset_index)
            residual += 0.0002 * ((day_index + asset_index * 3) % 5 - 2)
            daily_return = common * loading + residual
            if future_spike and day_index == day_count - 1:
                daily_return = 1.0 + asset_index * 0.25
            prices[asset_index] *= 1.0 + daily_return
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": f"CN_ETF_XSHG_{510000 + asset_index}",
                    "symbol": f"{510000 + asset_index}.SH",
                    "market": "CN_ETF",
                    "adj_close": prices[asset_index],
                    "high": prices[asset_index] * (1.005 + asset_index * 0.0001),
                    "low": prices[asset_index] * (0.995 - asset_index * 0.0001),
                    "volume": 1_000_000.0 + asset_index * 100_000.0,
                    "amount": 20_000_000.0 + asset_index * 1_000_000.0 + (day_index % 11) * 100_000.0,
                }
            )
    return pd.DataFrame(rows)


def _expected_features(bars: pd.DataFrame, *, target_asset: str) -> pd.DataFrame:
    frame = bars.sort_values(["asset_id", "date"]).copy()
    frame["return"] = frame.groupby("asset_id", sort=False)["adj_close"].pct_change()
    proxy = frame.groupby("date", sort=True)["return"].median().rename("market_return")
    asset = frame[frame["asset_id"].eq(target_asset)].copy()
    asset = asset.merge(proxy, left_on="date", right_index=True, how="left", validate="many_to_one")
    covariance = asset["return"].rolling(120, min_periods=80).cov(asset["market_return"])
    market_variance = asset["market_return"].rolling(120, min_periods=80).var()
    beta = covariance / market_variance.where(market_variance.abs() > 1e-12)
    alpha = asset["return"].rolling(120, min_periods=80).mean() - beta * asset[
        "market_return"
    ].rolling(120, min_periods=80).mean()
    residual = asset["return"] - alpha.shift(1) - beta.shift(1) * asset["market_return"]
    downside_return = asset["return"].where(asset["market_return"] < 0.0)
    downside_market = asset["market_return"].where(asset["market_return"] < 0.0)
    downside_covariance = downside_return.rolling(120, min_periods=24).cov(downside_market)
    downside_variance = downside_market.rolling(120, min_periods=24).var()
    asset["downside_beta_120"] = downside_covariance / downside_variance.where(
        downside_variance.abs() > 1e-12
    )
    asset["residual_vol_60"] = residual.rolling(60, min_periods=40).std(ddof=0)
    asset["residual_skew_60"] = residual.rolling(60, min_periods=40).skew()
    return asset


def _factor_value(
    factors: pd.DataFrame,
    asset_id: str,
    signal_date: pd.Timestamp,
    factor_name: str,
) -> float:
    match = factors[
        factors["asset_id"].eq(asset_id)
        & pd.to_datetime(factors["date"]).eq(signal_date)
        & factors["factor_name"].eq(factor_name)
    ]
    if len(match) != 1:
        raise AssertionError(f"Expected one {factor_name} row, found {len(match)}")
    return float(match.iloc[0]["factor_value"])


if __name__ == "__main__":
    unittest.main()
