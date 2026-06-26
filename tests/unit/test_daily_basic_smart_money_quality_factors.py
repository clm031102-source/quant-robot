import importlib
import unittest

import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


class DailyBasicSmartMoneyQualityFactorTests(unittest.TestCase):
    def test_factor_builder_emits_schema_columns_for_smart_money_quality_family(self):
        module = _smart_money_module()

        factors = module.compute_daily_basic_smart_money_quality_factors(_bars(), _daily_basic_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(module.DAILY_BASIC_SMART_MONEY_QUALITY_FACTOR_NAMES))
        self.assertEqual(
            module.DAILY_BASIC_SMART_MONEY_QUALITY_FACTOR_NAMES,
            (
                "smart_money_quality_lowvol_20",
                "smart_money_efficiency_lowvol_20",
                "smart_money_reversal_value_20",
            ),
        )
        self.assertTrue((factors["lookback_window"] == 20).all())

    def test_smart_money_quality_prefers_accumulated_cheap_lowvol_peer_inside_size_bucket(self):
        module = _smart_money_module()

        factors = module.compute_daily_basic_smart_money_quality_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("smart_money_quality_lowvol_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(6):
            self.assertGreater(values[f"CN_SMART_STRONG_{bucket}"], values[f"CN_SMART_WEAK_{bucket}"])

    def test_efficiency_variant_rewards_smooth_close_high_accumulation_over_noisy_turnover(self):
        module = _smart_money_module()

        factors = module.compute_daily_basic_smart_money_quality_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("smart_money_efficiency_lowvol_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(6):
            self.assertGreater(values[f"CN_SMART_STRONG_{bucket}"], values[f"CN_SMART_NOISY_{bucket}"])

    def test_reversal_value_variant_still_prefers_accumulation_after_short_pullback(self):
        module = _smart_money_module()

        factors = module.compute_daily_basic_smart_money_quality_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("smart_money_reversal_value_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(6):
            self.assertGreater(values[f"CN_SMART_STRONG_{bucket}"], values[f"CN_SMART_WEAK_{bucket}"])

    def test_tradeability_gate_excludes_illiquid_and_falling_knife_names(self):
        module = _smart_money_module()

        factors = module.compute_daily_basic_smart_money_quality_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("smart_money_quality_lowvol_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(6):
            self.assertTrue(pd.isna(values[f"CN_SMART_ILLIQUID_{bucket}"]))
            self.assertTrue(pd.isna(values[f"CN_SMART_FALLING_{bucket}"]))

    def test_smart_money_quality_factors_use_only_current_and_past_rows(self):
        module = _smart_money_module()

        base = module.compute_daily_basic_smart_money_quality_factors(_bars(day_count=30), _daily_basic_inputs(day_count=30))
        with_future = module.compute_daily_basic_smart_money_quality_factors(
            _bars(day_count=31, future_spike=True),
            _daily_basic_inputs(day_count=31),
        )

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-02-09").date()].reset_index(drop=True)
        pd.testing.assert_frame_equal(base.reset_index(drop=True), before_future, check_like=True)

    def test_unknown_factor_name_is_rejected(self):
        module = _smart_money_module()

        with self.assertRaisesRegex(ValueError, "Unsupported daily-basic smart money quality factor_names"):
            module.compute_daily_basic_smart_money_quality_factors(
                _bars(),
                _daily_basic_inputs(),
                factor_names=("missing",),
            )


def _smart_money_module():
    try:
        return importlib.import_module("quant_robot.factors.daily_basic_smart_money_quality")
    except ModuleNotFoundError as exc:
        raise AssertionError("daily-basic smart money quality factor module should exist") from exc


def _values_on_last_date(factors: pd.DataFrame) -> dict[str, float]:
    rows = factors[factors["date"] == pd.Timestamp("2024-02-09").date()]
    return dict(zip(rows["asset_id"], rows["factor_value"], strict=True))


def _bars(*, day_count: int = 30, future_spike: bool = False) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B").date
    for day_index, date in enumerate(dates):
        for bucket in range(6):
            rows.extend(
                [
                    _bar_row(date, day_index, f"CN_SMART_STRONG_{bucket}", bucket, "strong", future_spike, day_count),
                    _bar_row(date, day_index, f"CN_SMART_WEAK_{bucket}", bucket, "weak", future_spike, day_count),
                    _bar_row(date, day_index, f"CN_SMART_NOISY_{bucket}", bucket, "noisy", future_spike, day_count),
                    _bar_row(date, day_index, f"CN_SMART_ILLIQUID_{bucket}", bucket, "illiquid", future_spike, day_count),
                    _bar_row(date, day_index, f"CN_SMART_FALLING_{bucket}", bucket, "falling", future_spike, day_count),
                ]
            )
    return pd.DataFrame(rows)


def _bar_row(
    date,
    day_index: int,
    asset_id: str,
    bucket: int,
    profile: str,
    future_spike: bool,
    day_count: int,
) -> dict:
    base = 10.0 + bucket * 2.5
    if profile == "falling":
        midpoint = base * (1.0 + 0.0005 * day_index) if day_index < 25 else base * (0.55 ** (day_index - 24))
    elif profile == "weak":
        midpoint = base * (1.0 + 0.0004 * day_index)
    elif profile == "noisy":
        midpoint = base * (1.0 + 0.001 * day_index + (0.025 if day_index % 2 == 0 else -0.025))
    else:
        midpoint = base * (1.0 + 0.0015 * day_index)

    if future_spike and day_index == day_count - 1 and profile == "strong":
        midpoint *= 40.0

    if profile == "strong":
        low = midpoint * 0.985
        high = midpoint * 1.015
        close = high * 0.995
        amount = 8_000_000.0 + bucket * 10_000.0
    elif profile == "weak":
        low = midpoint * 0.985
        high = midpoint * 1.015
        close = low * 1.005
        amount = 5_000_000.0 + bucket * 10_000.0
    elif profile == "noisy":
        low = midpoint * 0.94
        high = midpoint * 1.06
        close = midpoint
        amount = 12_000_000.0 + bucket * 10_000.0
    elif profile == "illiquid":
        low = midpoint * 0.985
        high = midpoint * 1.015
        close = high * 0.995
        amount = 2_000.0 + bucket
    else:
        low = midpoint * 0.95
        high = midpoint * 1.05
        close = low * 1.002
        amount = 9_000_000.0 + bucket * 10_000.0

    return {
        "date": date,
        "asset_id": asset_id,
        "market": "CN",
        "adj_close": close,
        "close": close,
        "high": high,
        "low": low,
        "volume": amount / max(close, 1.0),
        "amount": amount,
        "source": "fixture",
    }


def _daily_basic_inputs(*, day_count: int = 30) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B").date
    for date in dates:
        for bucket in range(6):
            circ_mv = 10_000.0 * (3.0 ** bucket)
            rows.extend(
                [
                    _daily_row(date, f"CN_SMART_STRONG_{bucket}", 8.0, 1.0, 2.0, 3.2, 1.0, 0.8, circ_mv),
                    _daily_row(date, f"CN_SMART_WEAK_{bucket}", 36.0, 6.0, 12.0, 0.3, 3.0, 1.4, circ_mv * 1.05),
                    _daily_row(date, f"CN_SMART_NOISY_{bucket}", 20.0, 2.6, 5.0, 1.0, 9.0, 2.5, circ_mv * 1.10),
                    _daily_row(date, f"CN_SMART_ILLIQUID_{bucket}", 7.0, 0.9, 1.6, 3.5, 0.6, 0.7, circ_mv * 1.15),
                    _daily_row(date, f"CN_SMART_FALLING_{bucket}", 7.0, 0.8, 1.5, 3.8, 1.0, 0.9, circ_mv * 1.20),
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
    volume_ratio: float,
    circ_mv: float,
) -> dict:
    return {
        "date": date,
        "asset_id": asset_id,
        "market": "CN",
        "turnover_rate": turnover_rate,
        "turnover_rate_f": turnover_rate + 0.1,
        "volume_ratio": volume_ratio,
        "pe_ttm": pe_ttm,
        "pb": pb,
        "ps_ttm": ps_ttm,
        "dv_ttm": dv_ttm,
        "total_mv": circ_mv * 1.2,
        "circ_mv": circ_mv,
    }


if __name__ == "__main__":
    unittest.main()
