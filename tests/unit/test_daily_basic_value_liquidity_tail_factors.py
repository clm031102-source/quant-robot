import unittest

import pandas as pd

from quant_robot.factors.daily_basic_value_liquidity_tail import (
    DAILY_BASIC_VALUE_LIQUIDITY_TAIL_FACTOR_NAMES,
    compute_daily_basic_value_liquidity_tail_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class DailyBasicValueLiquidityTailFactorTests(unittest.TestCase):
    def test_factor_builder_emits_schema_columns_for_public_value_tail_family(self):
        factors = compute_daily_basic_value_liquidity_tail_factors(_bars(), _daily_basic_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(DAILY_BASIC_VALUE_LIQUIDITY_TAIL_FACTOR_NAMES))
        self.assertTrue((factors["lookback_window"] == 20).all())

    def test_value_liquid_low_tail_prefers_cheaper_tradeable_peer_inside_size_bucket(self):
        factors = compute_daily_basic_value_liquidity_tail_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("value_liquid_low_tail_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(5):
            self.assertGreater(
                values[f"CN_TEST_CHEAP_LIQUID_{bucket}"],
                values[f"CN_TEST_EXPENSIVE_LIQUID_{bucket}"],
            )

    def test_tradeability_gate_excludes_illiquid_and_falling_knife_names(self):
        factors = compute_daily_basic_value_liquidity_tail_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("value_liquid_low_tail_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(5):
            self.assertTrue(pd.isna(values[f"CN_TEST_ILLIQUID_CHEAP_{bucket}"]))
            self.assertTrue(pd.isna(values[f"CN_TEST_FALLING_CHEAP_{bucket}"]))

    def test_dividend_value_variant_rewards_yield_after_value_and_tail_gates(self):
        factors = compute_daily_basic_value_liquidity_tail_factors(
            _bars(),
            _daily_basic_inputs(dividend_rich=True),
            factor_names=("dividend_value_liquid_low_tail_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(5):
            self.assertGreater(
                values[f"CN_TEST_CHEAP_LIQUID_{bucket}"],
                values[f"CN_TEST_EXPENSIVE_LIQUID_{bucket}"],
            )

    def test_low_turnover_variant_prefers_quiet_cheap_names_over_hot_turnover(self):
        factors = compute_daily_basic_value_liquidity_tail_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("value_low_turnover_low_tail_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(5):
            self.assertGreater(
                values[f"CN_TEST_CHEAP_LIQUID_{bucket}"],
                values[f"CN_TEST_HOT_CHEAP_{bucket}"],
            )

    def test_value_tail_factors_use_only_current_and_past_bars(self):
        base = compute_daily_basic_value_liquidity_tail_factors(
            _bars(day_count=25),
            _daily_basic_inputs(day_count=25),
            factor_names=("value_liquid_low_tail_20",),
        )
        with_future = compute_daily_basic_value_liquidity_tail_factors(
            _bars(day_count=26, future_spike=True),
            _daily_basic_inputs(day_count=26),
            factor_names=("value_liquid_low_tail_20",),
        )

        base_day = base[base["date"] == pd.Timestamp("2024-01-25").date()].reset_index(drop=True)
        future_day = with_future[with_future["date"] == pd.Timestamp("2024-01-25").date()].reset_index(drop=True)
        pd.testing.assert_frame_equal(base_day, future_day)

    def test_unknown_factor_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported daily-basic value liquidity tail factor_names"):
            compute_daily_basic_value_liquidity_tail_factors(_bars(), _daily_basic_inputs(), factor_names=("missing",))


def _values_on_last_date(factors: pd.DataFrame) -> dict[str, float]:
    rows = factors[factors["date"] == pd.Timestamp("2024-01-30").date()]
    return dict(zip(rows["asset_id"], rows["factor_value"], strict=True))


def _bars(*, day_count: int = 30, future_spike: bool = False) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=day_count, freq="D").date
    for day_index, date in enumerate(dates):
        for bucket in range(5):
            rows.extend(
                [
                    _bar_row(date, day_index, f"CN_TEST_CHEAP_LIQUID_{bucket}", bucket, 2_000_000 + bucket, "stable"),
                    _bar_row(date, day_index, f"CN_TEST_EXPENSIVE_LIQUID_{bucket}", bucket, 1_900_000 + bucket, "stable"),
                    _bar_row(date, day_index, f"CN_TEST_HOT_CHEAP_{bucket}", bucket, 1_800_000 + bucket, "stable"),
                    _bar_row(date, day_index, f"CN_TEST_ILLIQUID_CHEAP_{bucket}", bucket, 1_000 + bucket, "stable"),
                    _bar_row(date, day_index, f"CN_TEST_FALLING_CHEAP_{bucket}", bucket, 2_100_000 + bucket, "falling"),
                ]
            )
    if future_spike:
        rows = [
            row | {"adj_close": row["adj_close"] * 50.0, "close": row["close"] * 50.0, "high": row["high"] * 50.0}
            if row["date"] == dates[-1] and row["asset_id"].startswith("CN_TEST_CHEAP_LIQUID_")
            else row
            for row in rows
        ]
    return pd.DataFrame(rows)


def _bar_row(date, day_index: int, asset_id: str, bucket: int, amount: float, path: str) -> dict:
    base = 10.0 + bucket
    if path == "falling":
        price = base if day_index < 25 else base * (0.55 ** (day_index - 24))
    else:
        price = base * (1.0 + day_index * 0.001)
    return {
        "date": date,
        "asset_id": asset_id,
        "market": "CN",
        "adj_close": price,
        "close": price,
        "high": price * 1.01,
        "low": price * 0.99,
        "volume": amount / max(price, 1.0),
        "amount": amount,
        "source": "fixture",
    }


def _daily_basic_inputs(*, day_count: int = 30, dividend_rich: bool = False) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=day_count, freq="D").date
    for date in dates:
        for bucket in range(5):
            circ_mv = 10_000.0 * (10 ** bucket)
            rows.extend(
                [
                    _daily_row(date, f"CN_TEST_CHEAP_LIQUID_{bucket}", bucket, 8.0, 1.0, 2.0, 3.5 if dividend_rich else 2.5, 1.0, circ_mv),
                    _daily_row(date, f"CN_TEST_EXPENSIVE_LIQUID_{bucket}", bucket, 35.0, 6.0, 12.0, 0.5, 2.0, circ_mv * 1.1),
                    _daily_row(date, f"CN_TEST_HOT_CHEAP_{bucket}", bucket, 8.0, 1.0, 2.0, 2.5, 9.0, circ_mv * 1.2),
                    _daily_row(date, f"CN_TEST_ILLIQUID_CHEAP_{bucket}", bucket, 7.0, 0.8, 1.5, 3.0, 0.8, circ_mv * 1.3),
                    _daily_row(date, f"CN_TEST_FALLING_CHEAP_{bucket}", bucket, 7.0, 0.9, 1.8, 3.2, 1.1, circ_mv * 1.4),
                ]
            )
    return pd.DataFrame(rows)


def _daily_row(
    date,
    asset_id: str,
    bucket: int,
    pe_ttm: float,
    pb: float,
    ps_ttm: float,
    dv_ttm: float,
    turnover_rate: float,
    circ_mv: float,
) -> dict:
    return {
        "date": date,
        "asset_id": asset_id,
        "market": "CN",
        "turnover_rate": turnover_rate,
        "turnover_rate_f": turnover_rate + 0.1,
        "volume_ratio": 1.0 + bucket * 0.1,
        "pe_ttm": pe_ttm,
        "pb": pb,
        "ps_ttm": ps_ttm,
        "dv_ttm": dv_ttm,
        "total_mv": circ_mv * 1.2,
        "circ_mv": circ_mv,
    }


if __name__ == "__main__":
    unittest.main()
