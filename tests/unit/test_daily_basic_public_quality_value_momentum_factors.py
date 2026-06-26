import unittest

import pandas as pd

from quant_robot.factors.daily_basic_public_quality_value_momentum import (
    DAILY_BASIC_PUBLIC_QVM_FACTOR_NAMES,
    compute_daily_basic_public_quality_value_momentum_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class DailyBasicPublicQualityValueMomentumFactorTests(unittest.TestCase):
    def test_factor_builder_emits_schema_columns_for_public_qvm_family(self):
        factors = compute_daily_basic_public_quality_value_momentum_factors(_bars(), _daily_basic_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(DAILY_BASIC_PUBLIC_QVM_FACTOR_NAMES))
        self.assertTrue((factors["lookback_window"] == 20).all())

    def test_value_momentum_lowvol_prefers_public_qvm_winner_inside_size_bucket(self):
        factors = compute_daily_basic_public_quality_value_momentum_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("public_qvm_value_momentum_lowvol_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(5):
            self.assertGreater(
                values[f"CN_TEST_QVM_WIN_{bucket}"],
                values[f"CN_TEST_EXPENSIVE_CHASER_{bucket}"],
            )

    def test_dividend_quality_momentum_rewards_yield_and_quality(self):
        factors = compute_daily_basic_public_quality_value_momentum_factors(
            _bars(),
            _daily_basic_inputs(dividend_rich=True),
            factor_names=("public_qvm_dividend_quality_momentum_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(5):
            self.assertGreater(
                values[f"CN_TEST_QVM_WIN_{bucket}"],
                values[f"CN_TEST_EXPENSIVE_CHASER_{bucket}"],
            )

    def test_tradeability_gate_excludes_illiquid_and_falling_knife_names(self):
        factors = compute_daily_basic_public_quality_value_momentum_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("public_qvm_value_momentum_lowvol_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(5):
            self.assertTrue(pd.isna(values[f"CN_TEST_ILLIQUID_VALUE_{bucket}"]))
            self.assertTrue(pd.isna(values[f"CN_TEST_FALLING_VALUE_{bucket}"]))

    def test_public_qvm_factors_use_only_current_and_past_bars(self):
        base = compute_daily_basic_public_quality_value_momentum_factors(
            _bars(day_count=25),
            _daily_basic_inputs(day_count=25),
            factor_names=("public_qvm_value_momentum_lowvol_20",),
        )
        with_future = compute_daily_basic_public_quality_value_momentum_factors(
            _bars(day_count=26, future_spike=True),
            _daily_basic_inputs(day_count=26),
            factor_names=("public_qvm_value_momentum_lowvol_20",),
        )

        base_day = base[base["date"] == pd.Timestamp("2024-01-25").date()].reset_index(drop=True)
        future_day = with_future[with_future["date"] == pd.Timestamp("2024-01-25").date()].reset_index(drop=True)
        pd.testing.assert_frame_equal(base_day, future_day)

    def test_unknown_factor_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported daily-basic public QVM factor_names"):
            compute_daily_basic_public_quality_value_momentum_factors(
                _bars(),
                _daily_basic_inputs(),
                factor_names=("missing_public_qvm",),
            )


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
                    _bar_row(date, day_index, f"CN_TEST_QVM_WIN_{bucket}", bucket, 2_500_000 + bucket, "steady_up"),
                    _bar_row(date, day_index, f"CN_TEST_EXPENSIVE_CHASER_{bucket}", bucket, 2_400_000 + bucket, "volatile_up"),
                    _bar_row(date, day_index, f"CN_TEST_ILLIQUID_VALUE_{bucket}", bucket, 1_000 + bucket, "steady_up"),
                    _bar_row(date, day_index, f"CN_TEST_FALLING_VALUE_{bucket}", bucket, 2_600_000 + bucket, "falling"),
                ]
            )
    if future_spike:
        rows = [
            row | {"adj_close": row["adj_close"] * 50.0, "close": row["close"] * 50.0, "high": row["high"] * 50.0}
            if row["date"] == dates[-1] and row["asset_id"].startswith("CN_TEST_QVM_WIN_")
            else row
            for row in rows
        ]
    return pd.DataFrame(rows)


def _bar_row(date, day_index: int, asset_id: str, bucket: int, amount: float, path: str) -> dict:
    base = 10.0 + bucket
    if path == "falling":
        price = base if day_index < 25 else base * (0.55 ** (day_index - 24))
    elif path == "volatile_up":
        price = base * (1.0 + day_index * 0.002 + (0.035 if day_index % 2 else -0.025))
    else:
        price = base * (1.0 + day_index * 0.004)
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
                    _daily_row(date, f"CN_TEST_QVM_WIN_{bucket}", 9.0, 1.0, 2.0, 3.5 if dividend_rich else 2.5, 1.1, circ_mv),
                    _daily_row(date, f"CN_TEST_EXPENSIVE_CHASER_{bucket}", 38.0, 7.0, 16.0, 0.4, 3.5, circ_mv * 1.1),
                    _daily_row(date, f"CN_TEST_ILLIQUID_VALUE_{bucket}", 8.0, 0.9, 1.8, 3.0, 1.0, circ_mv * 1.2),
                    _daily_row(date, f"CN_TEST_FALLING_VALUE_{bucket}", 7.0, 0.8, 1.7, 3.2, 1.1, circ_mv * 1.3),
                ]
            )
    return pd.DataFrame(rows)


def _daily_row(
    date,
    asset_id: str,
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
        "volume_ratio": 1.0,
        "pe_ttm": pe_ttm,
        "pb": pb,
        "ps_ttm": ps_ttm,
        "dv_ttm": dv_ttm,
        "total_mv": circ_mv * 1.2,
        "circ_mv": circ_mv,
    }


if __name__ == "__main__":
    unittest.main()
