import unittest

import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


class DailyBasicPublicAnomalyResidualEnsembleTests(unittest.TestCase):
    def test_ensemble_exports_schema_and_registered_names(self) -> None:
        module = _module()

        factors = module.compute_daily_basic_public_anomaly_residual_ensemble_factors(
            _bars(day_count=80),
            _daily_basic_inputs(day_count=80),
        )

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(module.DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES))
        self.assertEqual(
            module.DAILY_BASIC_PUBLIC_ANOMALY_RESIDUAL_ENSEMBLE_FACTOR_NAMES,
            (
                "public_anomaly_residual_equal_weight_20",
                "public_anomaly_residual_agreement_20",
                "public_anomaly_residual_disagreement_risk_20",
                "public_anomaly_residual_regime_conditioned_20",
            ),
        )

    def test_equal_weight_prefers_fixed_public_anomaly_agreement(self) -> None:
        module = _module()

        factors = module.compute_daily_basic_public_anomaly_residual_ensemble_factors(
            _bars(day_count=80),
            _daily_basic_inputs(day_count=80),
            factor_names=("public_anomaly_residual_equal_weight_20",),
        )
        values = _values_on(factors, "2024-04-19")

        self.assertGreater(values["CN_TEST_VALUE_LOWVOL_PULLBACK"], values["CN_TEST_EXPENSIVE_VOLATILE_UP"])

    def test_disagreement_risk_prefers_consistent_components(self) -> None:
        module = _module()

        factors = module.compute_daily_basic_public_anomaly_residual_ensemble_factors(
            _bars(day_count=80),
            _daily_basic_inputs(day_count=80),
            factor_names=("public_anomaly_residual_disagreement_risk_20",),
        )
        values = _values_on(factors, "2024-04-19")

        self.assertGreater(values["CN_TEST_VALUE_LOWVOL_PULLBACK"], values["CN_TEST_MIXED_SIGNAL"])

    def test_low_liquidity_names_are_masked(self) -> None:
        module = _module()

        factors = module.compute_daily_basic_public_anomaly_residual_ensemble_factors(
            _bars(day_count=80),
            _daily_basic_inputs(day_count=80),
            factor_names=("public_anomaly_residual_equal_weight_20",),
        )
        rows = factors[factors["date"] == pd.Timestamp("2024-04-19").date()]
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertTrue(pd.isna(values["CN_TEST_ILLIQUID"]))

    def test_ensemble_uses_only_current_and_past_rows(self) -> None:
        module = _module()

        baseline = module.compute_daily_basic_public_anomaly_residual_ensemble_factors(
            _bars(day_count=80),
            _daily_basic_inputs(day_count=80),
        )
        with_future = module.compute_daily_basic_public_anomaly_residual_ensemble_factors(
            _bars(day_count=81, future_spike=True),
            _daily_basic_inputs(day_count=81, future_spike=True),
        )

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-04-19").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_ensemble_rejects_unknown_requested_names(self) -> None:
        module = _module()

        with self.assertRaisesRegex(ValueError, "Unsupported daily-basic public anomaly residual ensemble factor_names"):
            module.compute_daily_basic_public_anomaly_residual_ensemble_factors(
                _bars(day_count=80),
                _daily_basic_inputs(day_count=80),
                factor_names=("missing",),
            )


def _module():
    import importlib

    try:
        return importlib.import_module("quant_robot.factors.daily_basic_public_anomaly_residual_ensemble")
    except ModuleNotFoundError as exc:
        raise AssertionError("daily-basic public anomaly residual ensemble module should exist") from exc


def _values_on(factors: pd.DataFrame, date: str) -> dict[str, float]:
    rows = factors[factors["date"] == pd.Timestamp(date).date()].dropna(subset=["factor_value"])
    return dict(zip(rows["asset_id"], rows["factor_value"], strict=True))


def _bars(*, day_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    path_count = day_count - 1 if future_spike else day_count
    prices = {
        "CN_TEST_VALUE_LOWVOL_PULLBACK": _gentle_pullback(path_count),
        "CN_TEST_EXPENSIVE_VOLATILE_UP": _volatile_up(path_count),
        "CN_TEST_MIXED_SIGNAL": _mixed_signal(path_count),
        "CN_TEST_LOWVOL_NEUTRAL": _lowvol_neutral(path_count),
        "CN_TEST_ILLIQUID": _gentle_pullback(path_count),
    }
    amounts = {
        "CN_TEST_VALUE_LOWVOL_PULLBACK": 12_000_000.0,
        "CN_TEST_EXPENSIVE_VOLATILE_UP": 13_000_000.0,
        "CN_TEST_MIXED_SIGNAL": 11_000_000.0,
        "CN_TEST_LOWVOL_NEUTRAL": 10_000_000.0,
        "CN_TEST_ILLIQUID": 50_000.0,
    }
    rows = []
    for asset_id, path in prices.items():
        for index, trade_date in enumerate(dates):
            price = 1000.0 if future_spike and index == day_count - 1 else path[index]
            rows.append(
                {
                    "date": trade_date.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": amounts[asset_id] * (1.0 + index * 0.0005),
                }
            )
    return pd.DataFrame(rows)


def _daily_basic_inputs(*, day_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    rows = []
    fundamentals = {
        "CN_TEST_VALUE_LOWVOL_PULLBACK": {"pe_ttm": 8.0, "pb": 0.8, "dv_ttm": 4.0, "turnover_rate_f": 1.0},
        "CN_TEST_EXPENSIVE_VOLATILE_UP": {"pe_ttm": 90.0, "pb": 7.0, "dv_ttm": 0.0, "turnover_rate_f": 6.0},
        "CN_TEST_MIXED_SIGNAL": {"pe_ttm": 9.0, "pb": 0.9, "dv_ttm": 3.5, "turnover_rate_f": 8.0},
        "CN_TEST_LOWVOL_NEUTRAL": {"pe_ttm": 20.0, "pb": 2.0, "dv_ttm": 1.0, "turnover_rate_f": 1.5},
        "CN_TEST_ILLIQUID": {"pe_ttm": 8.0, "pb": 0.8, "dv_ttm": 4.0, "turnover_rate_f": 1.0},
    }
    for asset_id, values in fundamentals.items():
        for index, trade_date in enumerate(dates):
            row = dict(values)
            if future_spike and index == day_count - 1:
                row = {"pe_ttm": 1.0, "pb": 0.1, "dv_ttm": 20.0, "turnover_rate_f": 0.1}
            rows.append(
                {
                    "date": trade_date.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "turnover_rate": row["turnover_rate_f"],
                    "turnover_rate_f": row["turnover_rate_f"],
                    "volume_ratio": 1.0,
                    "pe_ttm": row["pe_ttm"],
                    "pb": row["pb"],
                    "ps_ttm": 1.0,
                    "dv_ttm": row["dv_ttm"],
                    "total_mv": 100_000_000.0,
                    "circ_mv": 80_000_000.0,
                }
            )
    return pd.DataFrame(rows)


def _gentle_pullback(day_count: int) -> list[float]:
    prices = [10.0 + 0.02 * index for index in range(day_count)]
    for index in range(max(0, day_count - 20), day_count):
        prices[index] = prices[index - 1] * 0.996
    return prices


def _volatile_up(day_count: int) -> list[float]:
    return [10.0 + 0.10 * index + (0.80 if index % 2 == 0 else -0.80) for index in range(day_count)]


def _mixed_signal(day_count: int) -> list[float]:
    return [10.0 + 0.08 * index for index in range(day_count)]


def _lowvol_neutral(day_count: int) -> list[float]:
    return [10.0 + (0.03 if index % 2 == 0 else -0.03) for index in range(day_count)]


if __name__ == "__main__":
    unittest.main()
