import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from quant_robot.factors.etf_liquidity_capacity import (
    ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES,
    ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES,
    compute_etf_adv20,
    compute_etf_liquidity_capacity_factors,
    compute_etf_liquidity_reference_factors,
)
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


class EtfLiquidityCapacityFactorTests(unittest.TestCase):
    def test_exports_frozen_names_and_exact_formulas(self) -> None:
        bars = _bars(day_count=100, asset_count=6)

        factors = compute_etf_liquidity_capacity_factors(bars)
        adv20 = compute_etf_adv20(bars)

        self.assertEqual(
            tuple(sorted(factors["factor_name"].unique())),
            tuple(sorted(ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES)),
        )
        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        asset_id = "CN_ETF_XSHG_510000"
        asset_bars = bars[bars["asset_id"].eq(asset_id)].sort_values("date").reset_index(drop=True)
        signal_index = 90
        signal_date = asset_bars.iloc[signal_index]["date"]
        price = asset_bars["adj_close"]
        amount = asset_bars["amount"]
        amihud = price.pct_change().abs() / amount
        recent_impact = amihud.rolling(5, min_periods=5).mean()
        prior_impact = amihud.shift(5).rolling(60, min_periods=60).mean()
        expected_improvement = np.log(prior_impact.iloc[signal_index] / recent_impact.iloc[signal_index])
        prior_amount_median = amount.shift(1).rolling(60, min_periods=60).median()
        above_baseline = amount.gt(prior_amount_median).where(prior_amount_median.notna())
        expected_breadth = above_baseline.rolling(20, min_periods=20).mean().iloc[signal_index]
        window_amount = amount.iloc[signal_index - 19 : signal_index + 1]
        expected_distribution = 1.0 - float(window_amount.pow(2).sum() / window_amount.sum() ** 2)
        expected_adv20 = float(window_amount.mean())

        self.assertAlmostEqual(
            _factor_value(factors, asset_id, signal_date, "etf_amihud_improvement_5_60"),
            expected_improvement,
        )
        self.assertAlmostEqual(
            _factor_value(factors, asset_id, signal_date, "etf_amount_participation_breadth_20_60"),
            expected_breadth,
        )
        self.assertAlmostEqual(
            _factor_value(factors, asset_id, signal_date, "etf_amount_distribution_quality_20"),
            expected_distribution,
        )
        self.assertAlmostEqual(_adv20_value(adv20, asset_id, signal_date), expected_adv20)

    def test_future_rows_do_not_change_historical_values(self) -> None:
        baseline_bars = _bars(day_count=100, asset_count=6)
        future_bars = _bars(day_count=101, asset_count=6, future_spike=True)

        baseline_factors = compute_etf_liquidity_capacity_factors(baseline_bars)
        observed_factors = compute_etf_liquidity_capacity_factors(future_bars)
        baseline_adv20 = compute_etf_adv20(baseline_bars)
        observed_adv20 = compute_etf_adv20(future_bars)
        cutoff = pd.Timestamp(baseline_bars["date"].max())
        observed_factors = observed_factors[pd.to_datetime(observed_factors["date"]).le(cutoff)]
        observed_adv20 = observed_adv20[pd.to_datetime(observed_adv20["date"]).le(cutoff)]

        assert_frame_equal(
            baseline_factors.reset_index(drop=True),
            observed_factors.reset_index(drop=True),
            check_exact=False,
            rtol=1e-12,
            atol=1e-12,
        )
        assert_frame_equal(
            baseline_adv20.reset_index(drop=True),
            observed_adv20.reset_index(drop=True),
            check_exact=False,
            rtol=1e-12,
            atol=1e-12,
        )

    def test_historical_references_match_existing_direct_factors(self) -> None:
        bars = _bars(day_count=100, asset_count=6)

        observed = compute_etf_liquidity_reference_factors(bars)
        expected = compute_basic_factors(
            bars,
            windows=(5, 10, 20, 60),
            factor_names=ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES,
        )
        expected = expected[expected["factor_name"].isin(ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES)].reset_index(drop=True)

        self.assertEqual(
            tuple(sorted(observed["factor_name"].unique())),
            tuple(sorted(ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES)),
        )
        keys = ["date", "asset_id", "market", "factor_name", "lookback_window"]
        merged = expected.merge(observed, on=keys, how="outer", suffixes=("_expected", "_observed"), validate="one_to_one")
        self.assertTrue(
            np.allclose(
                merged["factor_value_expected"],
                merged["factor_value_observed"],
                equal_nan=True,
                rtol=1e-12,
                atol=1e-12,
            )
        )

    def test_materializes_only_requested_point_in_time_keys(self) -> None:
        bars = _bars(day_count=100, asset_count=6)
        eligible_keys = bars[
            bars["asset_id"].isin(["CN_ETF_XSHG_510000", "CN_ETF_XSHG_510001", "CN_ETF_XSHG_510002"])
            & bars["date"].ge(bars["date"].drop_duplicates().sort_values().iloc[-10])
        ][["date", "asset_id", "market"]]

        candidates = compute_etf_liquidity_capacity_factors(bars, eligible_keys=eligible_keys)
        references = compute_etf_liquidity_reference_factors(bars, eligible_keys=eligible_keys)
        adv20 = compute_etf_adv20(bars, eligible_keys=eligible_keys)

        expected_keys = {
            (pd.Timestamp(row.date).date(), row.asset_id, row.market)
            for row in eligible_keys.itertuples(index=False)
        }
        candidate_keys = {(row.date, row.asset_id, row.market) for row in candidates.itertuples(index=False)}
        reference_keys = {(row.date, row.asset_id, row.market) for row in references.itertuples(index=False)}
        adv20_keys = {(row.date, row.asset_id, row.market) for row in adv20.itertuples(index=False)}
        self.assertEqual(candidate_keys, expected_keys)
        self.assertEqual(reference_keys, expected_keys)
        self.assertEqual(adv20_keys, expected_keys)
        self.assertEqual(len(candidates), len(expected_keys) * len(ETF_LIQUIDITY_CAPACITY_FACTOR_NAMES))
        self.assertEqual(len(references), len(expected_keys) * len(ETF_LIQUIDITY_REFERENCE_FACTOR_NAMES))

    def test_nonpositive_amount_never_produces_infinite_values(self) -> None:
        bars = _bars(day_count=100, asset_count=6)
        target = bars["asset_id"].eq("CN_ETF_XSHG_510000") & bars["date"].eq(
            bars["date"].drop_duplicates().sort_values().iloc[-5]
        )
        bars.loc[target, "amount"] = 0.0

        factors = compute_etf_liquidity_capacity_factors(bars)
        adv20 = compute_etf_adv20(bars)

        self.assertFalse(np.isinf(pd.to_numeric(factors["factor_value"], errors="coerce")).any())
        self.assertFalse(np.isinf(pd.to_numeric(adv20["adv20"], errors="coerce")).any())

    def test_amihud_factor_does_not_forward_fill_missing_prices(self) -> None:
        bars = _bars(day_count=100, asset_count=6)
        dates = pd.DatetimeIndex(sorted(pd.to_datetime(bars["date"]).unique()))
        asset_id = "CN_ETF_XSHG_510000"
        missing = bars["asset_id"].eq(asset_id) & pd.to_datetime(bars["date"]).eq(dates[90])
        bars.loc[missing, "adj_close"] = np.nan

        factors = compute_etf_liquidity_capacity_factors(bars)

        value = _factor_value(
            factors,
            asset_id,
            dates[91],
            "etf_amihud_improvement_5_60",
        )
        self.assertTrue(np.isnan(value))


def _bars(*, day_count: int, asset_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2023-01-02", periods=day_count)
    rows = []
    for asset_index in range(asset_count):
        price = 10.0 + asset_index
        for day_index, signal_date in enumerate(dates):
            daily_return = 0.0005 + asset_index * 0.0002 + ((day_index % 11) - 5) * 0.0001
            amount = 20_000_000.0 + asset_index * 1_000_000.0 + (day_index % 17) * 250_000.0
            if future_spike and day_index == day_count - 1:
                daily_return = 2.0 + asset_index
                amount = 2_000_000_000.0 + asset_index
            price *= 1.0 + daily_return
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": f"CN_ETF_XSHG_{510000 + asset_index}",
                    "symbol": f"{510000 + asset_index}.SH",
                    "market": "CN_ETF",
                    "adj_close": price,
                    "volume": 1_000_000.0 + asset_index * 100_000.0,
                    "amount": amount,
                }
            )
    return pd.DataFrame(rows)


def _factor_value(factors: pd.DataFrame, asset_id: str, signal_date: pd.Timestamp, factor_name: str) -> float:
    match = factors[
        factors["asset_id"].eq(asset_id)
        & pd.to_datetime(factors["date"]).eq(pd.Timestamp(signal_date))
        & factors["factor_name"].eq(factor_name)
    ]
    if len(match) != 1:
        raise AssertionError(f"Expected one {factor_name} row, found {len(match)}")
    return float(match.iloc[0]["factor_value"])


def _adv20_value(adv20: pd.DataFrame, asset_id: str, signal_date: pd.Timestamp) -> float:
    match = adv20[
        adv20["asset_id"].eq(asset_id)
        & pd.to_datetime(adv20["date"]).eq(pd.Timestamp(signal_date))
    ]
    if len(match) != 1:
        raise AssertionError(f"Expected one ADV20 row, found {len(match)}")
    return float(match.iloc[0]["adv20"])
