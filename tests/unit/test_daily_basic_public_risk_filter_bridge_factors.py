import unittest
from unittest.mock import patch

import pandas as pd

from quant_robot.schema.factors import FACTOR_COLUMNS


class DailyBasicPublicRiskFilterBridgeTests(unittest.TestCase):
    def test_bridge_exports_schema_and_registered_names(self):
        module = _module()

        with _patched_components(module, _component_values()):
            factors = module.compute_daily_basic_public_risk_filter_bridge_factors(_bars(), _daily_basic_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(module.DAILY_BASIC_PUBLIC_RISK_FILTER_BRIDGE_FACTOR_NAMES))
        self.assertEqual(
            module.DAILY_BASIC_PUBLIC_RISK_FILTER_BRIDGE_FACTOR_NAMES,
            (
                "risk_filter_bridge_equal_20",
                "risk_filter_bridge_agreement_20",
                "risk_filter_bridge_anti_obv_weighted_20",
            ),
        )

    def test_equal_bridge_prefers_assets_that_pass_both_independent_filters(self):
        module = _module()

        with _patched_components(module, _component_values()):
            factors = module.compute_daily_basic_public_risk_filter_bridge_factors(
                _bars(),
                _daily_basic_inputs(),
                factor_names=("risk_filter_bridge_equal_20",),
            )

        rows = factors[factors["date"] == pd.Timestamp("2024-01-03").date()].dropna(subset=["factor_value"])
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))
        self.assertGreater(values["CN_TEST_STRONG"], values["CN_TEST_MIXED"])
        self.assertGreater(values["CN_TEST_MIXED"], values["CN_TEST_WEAK"])

    def test_agreement_bridge_penalizes_one_sided_filter_failure(self):
        module = _module()

        with _patched_components(module, _component_values()):
            factors = module.compute_daily_basic_public_risk_filter_bridge_factors(
                _bars(),
                _daily_basic_inputs(),
                factor_names=("risk_filter_bridge_equal_20", "risk_filter_bridge_agreement_20"),
            )

        rows = factors[factors["date"] == pd.Timestamp("2024-01-03").date()].dropna(subset=["factor_value"])
        values = {
            (row["asset_id"], row["factor_name"]): row["factor_value"]
            for _, row in rows.iterrows()
        }
        self.assertLess(
            values[("CN_TEST_MIXED", "risk_filter_bridge_agreement_20")],
            values[("CN_TEST_MIXED", "risk_filter_bridge_equal_20")],
        )
        self.assertGreater(
            values[("CN_TEST_STRONG", "risk_filter_bridge_agreement_20")],
            values[("CN_TEST_MIXED", "risk_filter_bridge_agreement_20")],
        )

    def test_bridge_uses_only_current_and_past_component_rows(self):
        module = _module()
        base_bars = _bars(day_count=3)
        future_bars = _bars(day_count=4)
        base_inputs = _daily_basic_inputs(day_count=3)
        future_inputs = _daily_basic_inputs(day_count=4)

        with _patched_components(module, _component_values(day_count=3)):
            base = module.compute_daily_basic_public_risk_filter_bridge_factors(base_bars, base_inputs)
        with _patched_components(module, _component_values(day_count=4, future_spike=True)):
            with_future = module.compute_daily_basic_public_risk_filter_bridge_factors(future_bars, future_inputs)

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-01-03").date()]
        pd.testing.assert_frame_equal(
            base.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_bridge_rejects_unknown_requested_names(self):
        module = _module()

        with self.assertRaisesRegex(ValueError, "Unsupported daily-basic public risk filter bridge factor_names"):
            module.compute_daily_basic_public_risk_filter_bridge_factors(
                _bars(),
                _daily_basic_inputs(),
                factor_names=("missing",),
            )


def _module():
    import importlib

    try:
        return importlib.import_module("quant_robot.factors.daily_basic_public_risk_filter_bridge")
    except ModuleNotFoundError as exc:
        raise AssertionError("daily-basic public risk filter bridge module should exist") from exc


def _patched_components(module, component_values):
    public_values, smart_values = component_values
    return _PatchContext(
        patch.object(module, "compute_public_trend_volume_factors", return_value=public_values),
        patch.object(module, "compute_daily_basic_smart_money_quality_factors", return_value=smart_values),
    )


class _PatchContext:
    def __init__(self, *patches):
        self._patches = patches

    def __enter__(self):
        for item in self._patches:
            item.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        for item in reversed(self._patches):
            item.__exit__(exc_type, exc, tb)


def _component_values(*, day_count: int = 3, future_spike: bool = False):
    dates = pd.date_range("2024-01-01", periods=day_count, freq="D").date
    assets = ["CN_TEST_STRONG", "CN_TEST_MIXED", "CN_TEST_NEUTRAL", "CN_TEST_WEAK"]
    public_rows = []
    smart_rows = []
    for date_index, date in enumerate(dates):
        public_by_asset = {
            "CN_TEST_STRONG": 0.95 + date_index * 0.01,
            "CN_TEST_MIXED": 0.90 + date_index * 0.01,
            "CN_TEST_NEUTRAL": 0.50 + date_index * 0.01,
            "CN_TEST_WEAK": 0.10 + date_index * 0.01,
        }
        smart_by_asset = {
            "CN_TEST_STRONG": 0.85 + date_index * 0.01,
            "CN_TEST_MIXED": 0.20 + date_index * 0.01,
            "CN_TEST_NEUTRAL": 0.50 + date_index * 0.01,
            "CN_TEST_WEAK": 0.15 + date_index * 0.01,
        }
        if future_spike and date_index == day_count - 1:
            public_by_asset = {asset: value * 10.0 for asset, value in public_by_asset.items()}
            smart_by_asset = {asset: value * 10.0 for asset, value in smart_by_asset.items()}
        for asset in assets:
            public_rows.append(_factor_row(date, asset, "anti_obv_breakout_low_tail_20", public_by_asset[asset]))
            smart_rows.append(_factor_row(date, asset, "smart_money_reversal_value_20", smart_by_asset[asset]))
    return pd.DataFrame(public_rows), pd.DataFrame(smart_rows)


def _factor_row(date, asset_id: str, factor_name: str, value: float) -> dict[str, object]:
    return {
        "date": date,
        "asset_id": asset_id,
        "market": "CN",
        "factor_name": factor_name,
        "factor_value": value,
        "lookback_window": 20,
    }


def _bars(*, day_count: int = 3) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="D").date
    rows = []
    for asset_index, asset in enumerate(["CN_TEST_STRONG", "CN_TEST_MIXED", "CN_TEST_NEUTRAL", "CN_TEST_WEAK"]):
        for date_index, date in enumerate(dates):
            price = 10.0 + asset_index + date_index
            rows.append(
                {
                    "date": date,
                    "asset_id": asset,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 10_000_000.0 + asset_index * 1_000_000.0,
                }
            )
    return pd.DataFrame(rows)


def _daily_basic_inputs(*, day_count: int = 3) -> pd.DataFrame:
    rows = []
    for row in _bars(day_count=day_count).to_dict(orient="records"):
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "market": row["market"],
                "turnover_rate": 1.0,
                "turnover_rate_f": 1.0,
                "volume_ratio": 1.0,
                "pe_ttm": 10.0,
                "pb": 1.0,
                "ps_ttm": 1.0,
                "dv_ttm": 2.0,
                "total_mv": 100_000_000.0,
                "circ_mv": 80_000_000.0,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
