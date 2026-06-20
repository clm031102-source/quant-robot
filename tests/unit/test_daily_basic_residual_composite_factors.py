import importlib
import math
import unittest

import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


class DailyBasicResidualCompositeFactorTests(unittest.TestCase):
    def test_factor_builder_emits_schema_columns_for_residual_composite_family(self):
        module = _residual_module()

        factors = module.compute_daily_basic_residual_composite_factors(_bars(), _daily_basic_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(module.DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES))
        self.assertEqual(
            module.DAILY_BASIC_RESIDUAL_COMPOSITE_FACTOR_NAMES,
            (
                "resid_value_quality_low_vol_20",
                "resid_value_low_turnover_quality_20",
                "resid_value_reversal_low_tail_20",
            ),
        )
        self.assertTrue((factors["lookback_window"] == 20).all())

    def test_residual_value_quality_prefers_cheaper_peer_inside_same_exposure_bucket(self):
        module = _residual_module()

        factors = module.compute_daily_basic_residual_composite_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("resid_value_quality_low_vol_20",),
        )

        values = _values_on_last_date(factors)
        for bucket in range(6):
            self.assertGreater(values[f"CN_RESID_CHEAP_{bucket}"], values[f"CN_RESID_EXPENSIVE_{bucket}"])

    def test_residual_value_quality_is_neutral_to_size_and_momentum_exposures(self):
        module = _residual_module()

        bars = _bars()
        factors = module.compute_daily_basic_residual_composite_factors(
            bars,
            _daily_basic_inputs(),
            factor_names=("resid_value_quality_low_vol_20",),
        )
        rows = factors[
            (factors["date"] == pd.Timestamp("2024-02-09").date())
            & factors["factor_value"].notna()
        ].copy()
        exposure_rows = _last_date_exposures(bars, _daily_basic_inputs())
        rows = rows.merge(exposure_rows, on="asset_id", how="left")

        self.assertLess(abs(rows["factor_value"].corr(rows["log_circ_mv"])), 1e-10)
        self.assertLess(abs(rows["factor_value"].corr(rows["momentum_20"])), 1e-10)

    def test_residual_composite_factors_use_only_current_and_past_rows(self):
        module = _residual_module()

        base = module.compute_daily_basic_residual_composite_factors(_bars(day_count=30), _daily_basic_inputs(day_count=30))
        with_future = module.compute_daily_basic_residual_composite_factors(
            _bars(day_count=31, future_spike=True),
            _daily_basic_inputs(day_count=31),
        )

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-02-09").date()].reset_index(drop=True)
        pd.testing.assert_frame_equal(base.reset_index(drop=True), before_future, check_like=True)

    def test_unknown_factor_name_is_rejected(self):
        module = _residual_module()

        with self.assertRaisesRegex(ValueError, "Unsupported daily-basic residual composite factor_names"):
            module.compute_daily_basic_residual_composite_factors(
                _bars(),
                _daily_basic_inputs(),
                factor_names=("missing",),
            )


def _residual_module():
    try:
        return importlib.import_module("quant_robot.factors.daily_basic_residual_composite")
    except ModuleNotFoundError as exc:
        raise AssertionError("daily-basic residual composite factor module should exist") from exc


def _values_on_last_date(factors: pd.DataFrame) -> dict[str, float]:
    rows = factors[factors["date"] == pd.Timestamp("2024-02-09").date()]
    return dict(zip(rows["asset_id"], rows["factor_value"], strict=True))


def _last_date_exposures(bars: pd.DataFrame, inputs: pd.DataFrame) -> pd.DataFrame:
    prices = bars.sort_values(["asset_id", "date"]).copy()
    prices["momentum_20"] = prices.groupby("asset_id", sort=False)["adj_close"].pct_change(20)
    last_prices = prices[prices["date"] == pd.Timestamp("2024-02-09").date()][["asset_id", "momentum_20"]]
    last_inputs = inputs[inputs["date"] == pd.Timestamp("2024-02-09").date()][["asset_id", "circ_mv"]]
    out = last_prices.merge(last_inputs, on="asset_id", how="left")
    out["log_circ_mv"] = out["circ_mv"].map(math.log)
    return out[["asset_id", "log_circ_mv", "momentum_20"]]


def _bars(*, day_count: int = 30, future_spike: bool = False) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B").date
    for day_index, date in enumerate(dates):
        for bucket in range(6):
            rows.extend(
                [
                    _bar_row(date, day_index, f"CN_RESID_CHEAP_{bucket}", bucket, future_spike, day_count),
                    _bar_row(date, day_index, f"CN_RESID_EXPENSIVE_{bucket}", bucket, future_spike, day_count),
                ]
            )
    return pd.DataFrame(rows)


def _bar_row(date, day_index: int, asset_id: str, bucket: int, future_spike: bool, day_count: int) -> dict:
    base = 10.0 + bucket * 3.0
    trend = 0.001 + bucket * 0.0004
    price = base * (1.0 + trend * day_index)
    if future_spike and day_index == day_count - 1 and asset_id.endswith("_0"):
        price *= 50.0
    amount = 5_000_000.0 * (1.0 + 0.001 * day_index)
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


def _daily_basic_inputs(*, day_count: int = 30) -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B").date
    for date in dates:
        for bucket in range(6):
            circ_mv = 10_000.0 * (3.0 ** bucket)
            rows.extend(
                [
                    _daily_row(date, f"CN_RESID_CHEAP_{bucket}", 8.0, 1.0, 2.0, 3.0, 1.0, 0.9, circ_mv),
                    _daily_row(date, f"CN_RESID_EXPENSIVE_{bucket}", 35.0, 6.0, 12.0, 0.5, 1.0, 1.1, circ_mv),
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
