import unittest

import pandas as pd

from quant_robot.factors.public_trend_volume import (
    PUBLIC_TREND_VOLUME_FACTOR_NAMES,
    compute_public_trend_volume_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class PublicTrendVolumeFactorTests(unittest.TestCase):
    def test_trend_volume_exports_schema_and_registered_names(self):
        factors = compute_public_trend_volume_factors(_bars(day_count=70))

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(PUBLIC_TREND_VOLUME_FACTOR_NAMES))
        self.assertEqual(
            PUBLIC_TREND_VOLUME_FACTOR_NAMES,
            (
                "supertrend_volume_confirmed_10_3_20",
                "smart_money_trend_20",
                "obv_breakout_low_tail_20",
                "anti_supertrend_volume_confirmed_10_3_20",
                "anti_smart_money_trend_20",
                "anti_obv_breakout_low_tail_20",
                "supertrend_volume_capacity_strict_10_3_20",
                "obv_breakout_capacity_strict_20",
            ),
        )

    def test_supertrend_volume_prefers_confirmed_volume_trend(self):
        factors = compute_public_trend_volume_factors(
            _bars(day_count=70),
            factor_names=("supertrend_volume_confirmed_10_3_20",),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-04-05").date()].dropna(subset=["factor_value"])
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertGreater(values["CN_TEST_CONFIRMED_TREND"], values["CN_TEST_WEAK_VOLUME_TREND"])

    def test_trend_volume_filters_illiquid_and_high_tail_assets(self):
        factors = compute_public_trend_volume_factors(
            _bars(day_count=70),
            factor_names=("smart_money_trend_20",),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-04-05").date()]
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertFalse(pd.isna(values["CN_TEST_CONFIRMED_TREND"]))
        self.assertTrue(pd.isna(values["CN_TEST_ILLIQUID_TREND"]))
        self.assertTrue(pd.isna(values["CN_TEST_HIGH_TAIL_TREND"]))

    def test_obv_breakout_prefers_breakout_with_accumulation(self):
        factors = compute_public_trend_volume_factors(
            _bars(day_count=70),
            factor_names=("obv_breakout_low_tail_20",),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-04-05").date()].dropna(subset=["factor_value"])
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertGreater(values["CN_TEST_CONFIRMED_TREND"], values["CN_TEST_WEAK_VOLUME_TREND"])

    def test_capacity_strict_variants_filter_unstable_liquidity(self):
        factors = compute_public_trend_volume_factors(
            _bars(day_count=70),
            factor_names=(
                "supertrend_volume_capacity_strict_10_3_20",
                "obv_breakout_capacity_strict_20",
            ),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-04-05").date()]
        values = {
            (row["asset_id"], row["factor_name"]): row["factor_value"]
            for _, row in rows.iterrows()
        }

        self.assertFalse(pd.isna(values[("CN_TEST_CONFIRMED_TREND", "supertrend_volume_capacity_strict_10_3_20")]))
        self.assertFalse(pd.isna(values[("CN_TEST_CONFIRMED_TREND", "obv_breakout_capacity_strict_20")]))
        self.assertTrue(pd.isna(values[("CN_TEST_UNSTABLE_LIQUIDITY_TREND", "supertrend_volume_capacity_strict_10_3_20")]))
        self.assertTrue(pd.isna(values[("CN_TEST_UNSTABLE_LIQUIDITY_TREND", "obv_breakout_capacity_strict_20")]))

    def test_anti_trend_volume_factors_invert_matching_public_signal(self):
        bars = _bars(day_count=70)
        factors = compute_public_trend_volume_factors(
            bars,
            factor_names=(
                "smart_money_trend_20",
                "anti_smart_money_trend_20",
            ),
        )
        rows = factors[
            (factors["date"] == pd.Timestamp("2024-04-05").date())
            & (factors["asset_id"] == "CN_TEST_CONFIRMED_TREND")
        ]
        values = dict(zip(rows["factor_name"], rows["factor_value"], strict=True))

        self.assertAlmostEqual(values["anti_smart_money_trend_20"], -values["smart_money_trend_20"])

    def test_trend_volume_uses_only_current_and_past_rows(self):
        baseline = compute_public_trend_volume_factors(_bars(day_count=70))
        with_future = compute_public_trend_volume_factors(_bars(day_count=71, future_spike=True))

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-04-05").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_trend_volume_rejects_unknown_requested_names(self):
        with self.assertRaisesRegex(ValueError, "Unsupported public trend-volume factor_names"):
            compute_public_trend_volume_factors(_bars(day_count=70), factor_names=("missing",))


def _bars(*, day_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    path_count = day_count - 1 if future_spike else day_count
    assets = {
        "CN_TEST_CONFIRMED_TREND": _steady_trend_path(start=10.0, step=0.08, day_count=path_count),
        "CN_TEST_WEAK_VOLUME_TREND": _steady_trend_path(start=10.0, step=0.05, day_count=path_count),
        "CN_TEST_ILLIQUID_TREND": _steady_trend_path(start=10.0, step=0.09, day_count=path_count),
        "CN_TEST_HIGH_TAIL_TREND": _high_tail_path(day_count=path_count),
        "CN_TEST_UNSTABLE_LIQUIDITY_TREND": _steady_trend_path(start=10.0, step=0.07, day_count=path_count),
    }
    amounts = {
        "CN_TEST_CONFIRMED_TREND": _accumulating_amounts(path_count, base=8_000_000.0),
        "CN_TEST_WEAK_VOLUME_TREND": [8_000_000.0] * path_count,
        "CN_TEST_ILLIQUID_TREND": [100_000.0] * path_count,
        "CN_TEST_HIGH_TAIL_TREND": _accumulating_amounts(path_count, base=4_900_000.0),
        "CN_TEST_UNSTABLE_LIQUIDITY_TREND": _unstable_amounts(path_count),
    }
    rows = []
    for asset_id, prices in assets.items():
        for index, date in enumerate(dates):
            price = 1000.0 if future_spike and index == day_count - 1 else prices[index]
            amount = amounts[asset_id][min(index, path_count - 1)]
            rows.append(
                {
                    "date": date.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": amount,
                }
            )
    return pd.DataFrame(rows)


def _steady_trend_path(*, start: float, step: float, day_count: int) -> list[float]:
    return [start + step * index for index in range(day_count)]


def _high_tail_path(*, day_count: int) -> list[float]:
    prices = _steady_trend_path(start=10.0, step=0.08, day_count=day_count)
    for index in range(25, day_count, 9):
        prices[index] = max(prices[index - 1] * 0.72, 1.0)
        if index + 1 < day_count:
            prices[index + 1] = prices[index] * 1.20
    return prices


def _accumulating_amounts(day_count: int, *, base: float) -> list[float]:
    return [base * (1.0 + 0.01 * index) for index in range(day_count)]


def _unstable_amounts(day_count: int) -> list[float]:
    amounts = _accumulating_amounts(day_count, base=9_000_000.0)
    for index in range(56, day_count, 7):
        amounts[index] = 10_000.0
    return amounts


if __name__ == "__main__":
    unittest.main()
