import importlib
import unittest

import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


class PublicFormulaPriceVolumeFactorTests(unittest.TestCase):
    def test_formula_price_volume_exports_schema_and_registered_names(self):
        module = _formula_module()

        factors = module.compute_public_formula_price_volume_factors(_bars(day_count=70))

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(module.PUBLIC_FORMULA_PRICE_VOLUME_FACTOR_NAMES))
        self.assertEqual(
            module.PUBLIC_FORMULA_PRICE_VOLUME_FACTOR_NAMES,
            (
                "formula_pv_corr_reversal_20",
                "formula_volume_contraction_reversal_20",
                "formula_range_contraction_breakout_20",
                "formula_range_contraction_breakout_liquid_20",
                "formula_range_contraction_breakout_lowvol_20",
                "formula_range_contraction_breakout_liquid_lowvol_20",
                "formula_pv_corr_momentum_confirmed_20_60",
                "formula_volume_contraction_momentum_confirmed_20_60",
            ),
        )

    def test_price_volume_correlation_reversal_prefers_divergence_over_confirmation(self):
        module = _formula_module()

        factors = module.compute_public_formula_price_volume_factors(
            _bars(day_count=70),
            factor_names=("formula_pv_corr_reversal_20",),
        )
        values = _values_on_last_date(factors)

        self.assertGreater(values["CN_FORMULA_DIVERGENCE"], values["CN_FORMULA_CONFIRMATION"])

    def test_formula_price_volume_filters_illiquid_and_high_tail_assets(self):
        module = _formula_module()

        factors = module.compute_public_formula_price_volume_factors(
            _bars(day_count=70),
            factor_names=("formula_volume_contraction_reversal_20",),
        )
        values = _values_on_last_date(factors)

        self.assertFalse(pd.isna(values["CN_FORMULA_DIVERGENCE"]))
        self.assertTrue(pd.isna(values["CN_FORMULA_ILLIQUID"]))
        self.assertTrue(pd.isna(values["CN_FORMULA_HIGH_TAIL"]))

    def test_range_contraction_breakout_prefers_tight_range_near_high(self):
        module = _formula_module()

        factors = module.compute_public_formula_price_volume_factors(
            _bars(day_count=70),
            factor_names=("formula_range_contraction_breakout_20",),
        )
        values = _values_on_last_date(factors)

        self.assertGreater(values["CN_FORMULA_TIGHT_BREAKOUT"], values["CN_FORMULA_CHOPPY"])

    def test_range_contraction_liquid_variant_prefers_more_liquid_peer(self):
        module = _formula_module()

        factors = module.compute_public_formula_price_volume_factors(
            _bars(day_count=70),
            factor_names=("formula_range_contraction_breakout_liquid_20",),
        )
        values = _values_on_last_date(factors)

        self.assertGreater(values["CN_FORMULA_TIGHT_BREAKOUT"], values["CN_FORMULA_TIGHT_BREAKOUT_LOW_LIQ"])

    def test_range_contraction_lowvol_variant_prefers_smoother_peer(self):
        module = _formula_module()

        factors = module.compute_public_formula_price_volume_factors(
            _bars(day_count=70),
            factor_names=("formula_range_contraction_breakout_lowvol_20",),
        )
        values = _values_on_last_date(factors)

        self.assertGreater(values["CN_FORMULA_TIGHT_BREAKOUT"], values["CN_FORMULA_TIGHT_BREAKOUT_BUMPY"])

    def test_range_contraction_composite_keeps_tradeable_filter(self):
        module = _formula_module()

        factors = module.compute_public_formula_price_volume_factors(
            _bars(day_count=70),
            factor_names=("formula_range_contraction_breakout_liquid_lowvol_20",),
        )
        values = _values_on_last_date(factors)

        self.assertTrue(pd.isna(values["CN_FORMULA_ILLIQUID"]))
        self.assertTrue(pd.isna(values["CN_FORMULA_HIGH_TAIL"]))

    def test_momentum_confirmed_formula_excludes_declining_reversal_trap(self):
        module = _formula_module()

        factors = module.compute_public_formula_price_volume_factors(
            _bars(day_count=90),
            factor_names=("formula_pv_corr_momentum_confirmed_20_60",),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-05-03").date()]
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertTrue(pd.isna(values["CN_FORMULA_DIVERGENCE"]))
        self.assertFalse(pd.isna(values["CN_FORMULA_CONFIRMED_PULLBACK"]))
        self.assertGreater(values["CN_FORMULA_CONFIRMED_PULLBACK"], values["CN_FORMULA_CONFIRMATION"])

    def test_formula_price_volume_uses_only_current_and_past_rows(self):
        module = _formula_module()

        baseline = module.compute_public_formula_price_volume_factors(_bars(day_count=70))
        with_future = module.compute_public_formula_price_volume_factors(_bars(day_count=71, future_spike=True))

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-04-05").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_formula_price_volume_rejects_unknown_requested_names(self):
        module = _formula_module()

        with self.assertRaisesRegex(ValueError, "Unsupported public formula price-volume factor_names"):
            module.compute_public_formula_price_volume_factors(_bars(day_count=70), factor_names=("missing",))


def _formula_module():
    try:
        return importlib.import_module("quant_robot.factors.public_formula_price_volume")
    except ModuleNotFoundError as exc:
        raise AssertionError("public formula price-volume factor module should exist") from exc


def _values_on_last_date(factors: pd.DataFrame) -> dict[str, float]:
    rows = factors[factors["date"] == pd.Timestamp("2024-04-05").date()]
    return dict(zip(rows["asset_id"], rows["factor_value"], strict=True))


def _bars(*, day_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    path_count = day_count - 1 if future_spike else day_count
    assets = {
        "CN_FORMULA_DIVERGENCE": _declining_path(day_count=path_count),
        "CN_FORMULA_CONFIRMATION": _rising_path(day_count=path_count),
        "CN_FORMULA_CONFIRMED_PULLBACK": _confirmed_pullback_path(day_count=path_count),
        "CN_FORMULA_TIGHT_BREAKOUT": _tight_breakout_path(day_count=path_count),
        "CN_FORMULA_TIGHT_BREAKOUT_LOW_LIQ": _tight_breakout_path(day_count=path_count),
        "CN_FORMULA_TIGHT_BREAKOUT_BUMPY": _bumpy_tight_breakout_path(day_count=path_count),
        "CN_FORMULA_CHOPPY": _choppy_path(day_count=path_count),
        "CN_FORMULA_ILLIQUID": _declining_path(day_count=path_count),
        "CN_FORMULA_HIGH_TAIL": _high_tail_path(day_count=path_count),
    }
    amounts = {
        "CN_FORMULA_DIVERGENCE": _rising_amounts(path_count, base=6_000_000.0),
        "CN_FORMULA_CONFIRMATION": _rising_amounts(path_count, base=7_000_000.0),
        "CN_FORMULA_CONFIRMED_PULLBACK": _rising_amounts(path_count, base=7_500_000.0),
        "CN_FORMULA_TIGHT_BREAKOUT": _flat_amounts(path_count, base=11_200_000.0),
        "CN_FORMULA_TIGHT_BREAKOUT_LOW_LIQ": _flat_amounts(path_count, base=10_500_000.0),
        "CN_FORMULA_TIGHT_BREAKOUT_BUMPY": _flat_amounts(path_count, base=11_200_000.0),
        "CN_FORMULA_CHOPPY": _flat_amounts(path_count, base=11_300_000.0),
        "CN_FORMULA_ILLIQUID": _flat_amounts(path_count, base=50_000.0),
        "CN_FORMULA_HIGH_TAIL": _rising_amounts(path_count, base=5_400_000.0),
    }
    rows = []
    for asset_id, prices in assets.items():
        for index, date in enumerate(dates):
            price = 500.0 if future_spike and index == day_count - 1 else prices[index]
            amount = amounts[asset_id][min(index, path_count - 1)]
            tail_scale = 1.10 if asset_id == "CN_FORMULA_HIGH_TAIL" and index >= 30 else 1.01
            rows.append(
                {
                    "date": date.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * tail_scale,
                    "low": price / tail_scale,
                    "amount": amount,
                }
            )
    return pd.DataFrame(rows)


def _declining_path(*, day_count: int) -> list[float]:
    return [12.0 - 0.025 * index for index in range(day_count)]


def _rising_path(*, day_count: int) -> list[float]:
    return [10.0 + 0.035 * index for index in range(day_count)]


def _confirmed_pullback_path(*, day_count: int) -> list[float]:
    prices = [10.0 + 0.045 * index for index in range(day_count)]
    for index in range(max(day_count - 12, 0), day_count):
        prices[index] -= 0.02 * (index - (day_count - 12))
    return prices


def _tight_breakout_path(*, day_count: int) -> list[float]:
    return [10.0 + 0.01 * index + (0.20 if index > day_count - 10 else 0.0) for index in range(day_count)]


def _bumpy_tight_breakout_path(*, day_count: int) -> list[float]:
    prices = _tight_breakout_path(day_count=day_count)
    for index in range(30, day_count, 9):
        prices[index] = prices[index - 1] * 0.96
    return prices


def _choppy_path(*, day_count: int) -> list[float]:
    return [10.0 + (0.02 if index % 2 == 0 else -0.015) + 0.005 * index for index in range(day_count)]


def _high_tail_path(*, day_count: int) -> list[float]:
    prices = _rising_path(day_count=day_count)
    for index in range(30, day_count, 8):
        prices[index] = max(prices[index - 1] * 0.65, 1.0)
    return prices


def _rising_amounts(day_count: int, *, base: float) -> list[float]:
    return [base * (1.0 + 0.015 * index) for index in range(day_count)]


def _flat_amounts(day_count: int, *, base: float) -> list[float]:
    return [base for _ in range(day_count)]


if __name__ == "__main__":
    unittest.main()
