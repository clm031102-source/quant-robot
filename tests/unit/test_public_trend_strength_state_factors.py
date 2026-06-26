import unittest

import pandas as pd

from quant_robot.factors.public_trend_strength_state import (
    PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES,
    compute_public_trend_strength_state_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class PublicTrendStrengthStateFactorTests(unittest.TestCase):
    def test_trend_strength_state_exports_schema_and_registered_names(self) -> None:
        factors = compute_public_trend_strength_state_factors(_bars(day_count=75))

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES))
        self.assertEqual(
            PUBLIC_TREND_STRENGTH_STATE_FACTOR_NAMES,
            (
                "adx_trend_strength_exhaustion_reversal_14_20",
                "adx_choppiness_mean_reversion_quality_14_20",
                "kama_efficiency_trend_decay_10_30",
                "aroon_range_exhaustion_reversal_25_20",
                "williams_range_failure_reversal_14_20",
                "trend_strength_state_residual_composite_20",
            ),
        )

    def test_williams_reversal_prefers_oversold_range_failure(self) -> None:
        factors = compute_public_trend_strength_state_factors(
            _bars(day_count=75),
            factor_names=("williams_range_failure_reversal_14_20",),
        )
        values = _values_on(factors, "2024-04-12")

        self.assertGreater(values["CN_TEST_OVERSOLD_RANGE"], values["CN_TEST_EXTENDED_UPTREND"])

    def test_kama_decay_prefers_fading_trend_efficiency(self) -> None:
        factors = compute_public_trend_strength_state_factors(
            _bars(day_count=75),
            factor_names=("kama_efficiency_trend_decay_10_30",),
        )
        values = _values_on(factors, "2024-04-12")

        self.assertGreater(values["CN_TEST_TREND_PULLBACK"], values["CN_TEST_EXTENDED_UPTREND"])

    def test_aroon_exhaustion_prefers_recent_low_state_over_recent_high_state(self) -> None:
        factors = compute_public_trend_strength_state_factors(
            _bars(day_count=75),
            factor_names=("aroon_range_exhaustion_reversal_25_20",),
        )
        values = _values_on(factors, "2024-04-12")

        self.assertGreater(values["CN_TEST_OVERSOLD_RANGE"], values["CN_TEST_EXTENDED_UPTREND"])

    def test_low_liquidity_names_are_masked(self) -> None:
        factors = compute_public_trend_strength_state_factors(
            _bars(day_count=75),
            factor_names=("trend_strength_state_residual_composite_20",),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-04-12").date()]
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertTrue(pd.isna(values["CN_TEST_ILLIQUID"]))

    def test_trend_strength_state_uses_only_current_and_past_rows(self) -> None:
        baseline = compute_public_trend_strength_state_factors(_bars(day_count=75))
        with_future = compute_public_trend_strength_state_factors(_bars(day_count=76, future_spike=True))

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-04-12").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_trend_strength_state_rejects_unknown_requested_names(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported public trend-strength-state factor_names"):
            compute_public_trend_strength_state_factors(_bars(day_count=75), factor_names=("missing",))


def _values_on(factors: pd.DataFrame, date: str) -> dict[str, float]:
    rows = factors[factors["date"] == pd.Timestamp(date).date()].dropna(subset=["factor_value"])
    return dict(zip(rows["asset_id"], rows["factor_value"], strict=True))


def _bars(*, day_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    path_count = day_count - 1 if future_spike else day_count
    assets = {
        "CN_TEST_EXTENDED_UPTREND": _extended_uptrend(path_count),
        "CN_TEST_TREND_PULLBACK": _trend_then_pullback(path_count),
        "CN_TEST_OVERSOLD_RANGE": _oversold_range(path_count),
        "CN_TEST_CHOPPY_RANGE": _choppy_range(path_count),
        "CN_TEST_ILLIQUID": _trend_then_pullback(path_count),
    }
    amounts = {
        "CN_TEST_EXTENDED_UPTREND": 9_000_000.0,
        "CN_TEST_TREND_PULLBACK": 8_500_000.0,
        "CN_TEST_OVERSOLD_RANGE": 8_000_000.0,
        "CN_TEST_CHOPPY_RANGE": 7_500_000.0,
        "CN_TEST_ILLIQUID": 80_000.0,
    }
    rows = []
    for asset_id, prices in assets.items():
        for index, date in enumerate(dates):
            price = 1000.0 if future_spike and index == day_count - 1 else prices[index]
            rows.append(
                {
                    "date": date.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": amounts[asset_id] * (1.0 + 0.001 * index),
                }
            )
    return pd.DataFrame(rows)


def _extended_uptrend(day_count: int) -> list[float]:
    return [10.0 + 0.10 * index for index in range(day_count)]


def _trend_then_pullback(day_count: int) -> list[float]:
    prices = [10.0 + 0.12 * index for index in range(day_count)]
    for offset, index in enumerate(range(max(0, day_count - 10), day_count)):
        prices[index] = prices[index - 1] * (0.970 if offset % 2 == 0 else 1.018)
    return prices


def _oversold_range(day_count: int) -> list[float]:
    prices = [14.0 - 0.04 * index for index in range(day_count)]
    for index in range(max(0, day_count - 12), day_count):
        prices[index] = prices[index - 1] * 0.972
    return [max(price, 2.0) for price in prices]


def _choppy_range(day_count: int) -> list[float]:
    return [10.0 + (0.35 if index % 4 < 2 else -0.35) for index in range(day_count)]


if __name__ == "__main__":
    unittest.main()
