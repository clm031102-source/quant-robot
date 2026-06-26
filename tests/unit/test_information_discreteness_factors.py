import unittest

import pandas as pd

from quant_robot.factors.information_discreteness import (
    INFORMATION_DISCRETENESS_FACTOR_NAMES,
    compute_information_discreteness_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class InformationDiscretenessFactorTests(unittest.TestCase):
    def test_information_discreteness_exports_schema_and_registered_names(self) -> None:
        factors = compute_information_discreteness_factors(_bars(day_count=95))

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(INFORMATION_DISCRETENESS_FACTOR_NAMES))
        self.assertEqual(
            INFORMATION_DISCRETENESS_FACTOR_NAMES,
            (
                "fip_smooth_momentum_quality_60_20",
                "fip_smooth_momentum_skip5_60",
                "fip_continuous_accumulation_low_jump_20_60",
                "fip_discrete_jump_reversal_20_5",
                "fip_smooth_pullback_resilience_60_20",
                "fip_volume_confirmed_smooth_trend_20_60",
            ),
        )

    def test_smooth_momentum_quality_prefers_continuous_information_over_single_jump(self) -> None:
        factors = compute_information_discreteness_factors(
            _bars(day_count=95),
            factor_names=("fip_smooth_momentum_quality_60_20",),
        )
        values = _values_on_last_date(factors)

        self.assertGreater(values["CN_FIP_SMOOTH_UP"], values["CN_FIP_JUMP_UP"])

    def test_discrete_jump_reversal_penalizes_recent_positive_jump_and_prefers_negative_shock(self) -> None:
        factors = compute_information_discreteness_factors(
            _bars(day_count=95),
            factor_names=("fip_discrete_jump_reversal_20_5",),
        )
        values = _values_on_last_date(factors)

        self.assertGreater(values["CN_FIP_NEGATIVE_SHOCK"], values["CN_FIP_POSITIVE_SHOCK"])

    def test_low_liquidity_names_are_masked(self) -> None:
        factors = compute_information_discreteness_factors(
            _bars(day_count=95),
            factor_names=("fip_volume_confirmed_smooth_trend_20_60",),
        )
        rows = factors[factors["date"] == factors["date"].max()]
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertTrue(pd.isna(values["CN_FIP_ILLIQUID"]))

    def test_information_discreteness_uses_only_current_and_past_rows(self) -> None:
        baseline = compute_information_discreteness_factors(_bars(day_count=95))
        with_future = compute_information_discreteness_factors(_bars(day_count=96, future_spike=True))

        before_future = with_future[with_future["date"] <= baseline["date"].max()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_information_discreteness_rejects_unknown_requested_names(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported information-discreteness factor_names"):
            compute_information_discreteness_factors(_bars(day_count=95), factor_names=("missing",))


def _values_on_last_date(factors: pd.DataFrame) -> dict[str, float]:
    rows = factors[factors["date"] == factors["date"].max()].dropna(subset=["factor_value"])
    return dict(zip(rows["asset_id"], rows["factor_value"], strict=True))


def _bars(*, day_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    path_count = day_count - 1 if future_spike else day_count
    assets = {
        "CN_FIP_SMOOTH_UP": _smooth_up(path_count),
        "CN_FIP_JUMP_UP": _jump_up(path_count),
        "CN_FIP_POSITIVE_SHOCK": _positive_shock(path_count),
        "CN_FIP_NEGATIVE_SHOCK": _negative_shock(path_count),
        "CN_FIP_STEADY_PULLBACK": _steady_pullback(path_count),
        "CN_FIP_ILLIQUID": _smooth_up(path_count),
    }
    amounts = {
        "CN_FIP_SMOOTH_UP": 9_000_000.0,
        "CN_FIP_JUMP_UP": 8_700_000.0,
        "CN_FIP_POSITIVE_SHOCK": 8_400_000.0,
        "CN_FIP_NEGATIVE_SHOCK": 8_100_000.0,
        "CN_FIP_STEADY_PULLBACK": 7_800_000.0,
        "CN_FIP_ILLIQUID": 80_000.0,
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


def _smooth_up(day_count: int) -> list[float]:
    return [10.0 * (1.003 ** index) for index in range(day_count)]


def _jump_up(day_count: int) -> list[float]:
    prices = [10.0 for _ in range(day_count)]
    jump_at = max(1, day_count - 25)
    for index in range(jump_at, day_count):
        prices[index] = 12.50
    return prices


def _positive_shock(day_count: int) -> list[float]:
    prices = [10.0 + 0.01 * index for index in range(day_count)]
    for index in range(max(1, day_count - 5), day_count):
        prices[index] = prices[index - 1] * 1.07
    return prices


def _negative_shock(day_count: int) -> list[float]:
    prices = [12.0 - 0.005 * index for index in range(day_count)]
    for index in range(max(1, day_count - 5), day_count):
        prices[index] = prices[index - 1] * 0.93
    return prices


def _steady_pullback(day_count: int) -> list[float]:
    prices = [10.0 * (1.0025 ** index) for index in range(day_count)]
    for offset, index in enumerate(range(max(1, day_count - 15), day_count)):
        prices[index] = prices[index - 1] * (0.986 if offset % 2 == 0 else 1.002)
    return prices


if __name__ == "__main__":
    unittest.main()
