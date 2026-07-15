import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from quant_robot.factors.etf_skip_momentum import (
    ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES,
    ETF_SKIP_MOMENTUM_FACTOR_NAMES,
    compute_etf_price_rotation_reference_factors,
    compute_etf_skip_momentum_factors,
)
from quant_robot.factors.information_discreteness import compute_information_discreteness_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


class EtfSkipMomentumFactorTests(unittest.TestCase):
    def test_exports_frozen_names_and_exact_pure_price_ratios(self) -> None:
        bars = _bars(day_count=165, asset_count=6)

        factors = compute_etf_skip_momentum_factors(bars)

        self.assertEqual(tuple(sorted(factors["factor_name"].unique())), tuple(sorted(ETF_SKIP_MOMENTUM_FACTOR_NAMES)))
        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        asset = "CN_ETF_XSHG_510000"
        asset_bars = bars[bars["asset_id"] == asset].sort_values("date").reset_index(drop=True)
        signal_date = asset_bars.iloc[150]["date"]
        price = asset_bars["adj_close"]
        expected_skip5 = price.iloc[145] / price.iloc[85] - 1.0
        expected_skip20 = price.iloc[130] / price.iloc[10] - 1.0
        self.assertAlmostEqual(_factor_value(factors, asset, signal_date, "etf_skip5_momentum_60"), expected_skip5)
        self.assertAlmostEqual(
            _factor_value(factors, asset, signal_date, "etf_skip20_momentum_120"),
            expected_skip20,
        )

    def test_fip_diagnostic_matches_existing_registered_factor(self) -> None:
        bars = _bars(day_count=100, asset_count=8)

        expected = compute_information_discreteness_factors(
            bars,
            factor_names=("fip_smooth_momentum_skip5_60",),
        )
        observed = compute_etf_skip_momentum_factors(
            bars,
            factor_names=("fip_smooth_momentum_skip5_60",),
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

    def test_future_rows_do_not_change_historical_factor_values(self) -> None:
        baseline_bars = _bars(day_count=165, asset_count=6)
        future_bars = _bars(day_count=166, asset_count=6, future_spike=True)

        baseline = compute_etf_skip_momentum_factors(baseline_bars)
        observed = compute_etf_skip_momentum_factors(future_bars)
        cutoff = baseline_bars["date"].max()
        observed = observed[pd.to_datetime(observed["date"]) <= pd.Timestamp(cutoff)].reset_index(drop=True)

        assert_frame_equal(baseline.reset_index(drop=True), observed, check_exact=False, rtol=1e-12, atol=1e-12)

    def test_computes_only_frozen_reference_exposures(self) -> None:
        references = compute_etf_price_rotation_reference_factors(_bars(day_count=100, asset_count=6))

        self.assertEqual(
            tuple(sorted(references["factor_name"].unique())),
            tuple(sorted(ETF_PRICE_ROTATION_REFERENCE_FACTOR_NAMES)),
        )
        self.assertEqual(list(references.columns), FACTOR_COLUMNS)
        latest = references[references["date"] == references["date"].max()]
        momentum = latest[latest["factor_name"] == "momentum_60"].set_index("asset_id")["factor_value"]
        relative = latest[latest["factor_name"] == "market_relative_strength_60"].set_index("asset_id")[
            "factor_value"
        ]
        self.assertTrue(momentum.rank().equals(relative.rank()))

    def test_rejects_unknown_requested_factor(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported ETF skip-momentum factor_names"):
            compute_etf_skip_momentum_factors(_bars(day_count=20), factor_names=("missing",))


def _bars(*, day_count: int, asset_count: int = 6, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2023-01-02", periods=day_count)
    rows = []
    for asset_index in range(asset_count):
        price = 10.0 + asset_index
        for day_index, signal_date in enumerate(dates):
            daily_return = 0.0005 + asset_index * 0.0002 + ((day_index % 11) - 5) * 0.0001
            if future_spike and day_index == day_count - 1:
                daily_return = 2.0 + asset_index
            price *= 1.0 + daily_return
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": f"CN_ETF_XSHG_{510000 + asset_index}",
                    "symbol": f"{510000 + asset_index}.SH",
                    "market": "CN_ETF",
                    "adj_close": price,
                    "volume": 1_000_000.0 + asset_index * 100_000.0,
                    "amount": 20_000_000.0 + asset_index * 1_000_000.0 + (day_index % 7) * 100_000.0,
                }
            )
    return pd.DataFrame(rows)


def _factor_value(factors: pd.DataFrame, asset_id: str, signal_date: pd.Timestamp, factor_name: str) -> float:
    match = factors[
        (factors["asset_id"] == asset_id)
        & (pd.to_datetime(factors["date"]) == pd.Timestamp(signal_date))
        & (factors["factor_name"] == factor_name)
    ]
    if len(match) != 1:
        raise AssertionError(f"Expected one {factor_name} row, found {len(match)}")
    return float(match.iloc[0]["factor_value"])
