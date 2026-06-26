import unittest

import pandas as pd

from quant_robot.factors.public_technical_tail_guard import (
    PUBLIC_TECHNICAL_TAIL_GUARD_FACTOR_NAMES,
    compute_public_technical_tail_guard_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class PublicTechnicalTailGuardFactorTests(unittest.TestCase):
    def test_tail_guard_exports_schema_and_registered_names(self):
        factors = compute_public_technical_tail_guard_factors(_bars(day_count=45))

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(PUBLIC_TECHNICAL_TAIL_GUARD_FACTOR_NAMES))
        self.assertEqual(
            PUBLIC_TECHNICAL_TAIL_GUARD_FACTOR_NAMES,
            (
                "rsi_reversal_liquid_low_tail_14_20",
                "bollinger_reversal_liquid_low_tail_20",
            ),
        )

    def test_tail_guard_filters_high_downside_volatility_names(self):
        factors = compute_public_technical_tail_guard_factors(
            _bars(day_count=45),
            factor_names=("rsi_reversal_liquid_low_tail_14_20",),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-03-01").date()]
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertFalse(pd.isna(values["CN_TEST_LOW_TAIL_OVERSOLD"]))
        self.assertTrue(pd.isna(values["CN_TEST_HIGH_TAIL_OVERSOLD"]))

    def test_tail_guard_filters_falling_knife_at_rolling_low(self):
        factors = compute_public_technical_tail_guard_factors(
            _bars(day_count=45),
            factor_names=("bollinger_reversal_liquid_low_tail_20",),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-03-01").date()]
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertFalse(pd.isna(values["CN_TEST_LOW_TAIL_OVERSOLD"]))
        self.assertTrue(pd.isna(values["CN_TEST_FALLING_KNIFE"]))

    def test_tail_guard_prefers_low_tail_oversold_peer(self):
        factors = compute_public_technical_tail_guard_factors(
            _bars(day_count=45),
            factor_names=("bollinger_reversal_liquid_low_tail_20",),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-03-01").date()].dropna(subset=["factor_value"])
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertGreater(values["CN_TEST_LOW_TAIL_OVERSOLD"], values["CN_TEST_LOW_TAIL_STABLE"])

    def test_tail_guard_uses_only_current_and_past_rows(self):
        baseline = compute_public_technical_tail_guard_factors(_bars(day_count=40))
        with_future = compute_public_technical_tail_guard_factors(_bars(day_count=41, future_spike=True))

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-02-23").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_tail_guard_rejects_unknown_requested_names(self):
        with self.assertRaisesRegex(ValueError, "Unsupported public technical tail-guard factor_names"):
            compute_public_technical_tail_guard_factors(_bars(day_count=25), factor_names=("missing",))


def _bars(*, day_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    rows = []
    path_count = day_count - 1 if future_spike else day_count
    assets = {
        "CN_TEST_LOW_TAIL_OVERSOLD": _low_tail_oversold_path(day_count=path_count),
        "CN_TEST_LOW_TAIL_STABLE": _smooth_path(start=10.0, end=10.1, day_count=path_count),
        "CN_TEST_HIGH_TAIL_OVERSOLD": _volatile_path(day_count=path_count),
        "CN_TEST_FALLING_KNIFE": _smooth_path(start=12.0, end=7.2, day_count=path_count),
    }
    amounts = {
        "CN_TEST_LOW_TAIL_OVERSOLD": 5_300_000.0,
        "CN_TEST_LOW_TAIL_STABLE": 5_200_000.0,
        "CN_TEST_HIGH_TAIL_OVERSOLD": 5_100_000.0,
        "CN_TEST_FALLING_KNIFE": 5_000_000.0,
    }
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
                    "amount": amounts[asset_id],
                }
            )
    return pd.DataFrame(rows)


def _smooth_path(*, start: float, end: float, day_count: int) -> list[float]:
    if day_count <= 1:
        return [end]
    step = (end - start) / float(day_count - 1)
    return [start + step * index for index in range(day_count)]


def _low_tail_oversold_path(*, day_count: int) -> list[float]:
    prices = _smooth_path(start=12.0, end=10.2, day_count=day_count)
    if day_count >= 8:
        prices[-8:] = [9.8, 9.6, 9.3, 9.1, 9.0, 9.2, 9.4, 9.5]
    return prices


def _volatile_path(*, day_count: int) -> list[float]:
    prices = []
    for index in range(day_count):
        base = 12.0 - 0.03 * index
        shock = -1.5 if index % 5 == 0 else 0.8 if index % 5 == 1 else 0.0
        prices.append(max(base + shock, 2.0))
    prices[-1] = 9.4
    return prices


if __name__ == "__main__":
    unittest.main()
