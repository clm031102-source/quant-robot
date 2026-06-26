import unittest

import pandas as pd

from quant_robot.factors.public_technical_liquidity import (
    PUBLIC_TECHNICAL_LIQUIDITY_FACTOR_NAMES,
    compute_public_technical_liquidity_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class PublicTechnicalLiquidityFactorTests(unittest.TestCase):
    def test_liquidity_combo_exports_schema_and_registered_names(self):
        factors = compute_public_technical_liquidity_factors(_bars(day_count=35))

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(PUBLIC_TECHNICAL_LIQUIDITY_FACTOR_NAMES))
        self.assertEqual(
            PUBLIC_TECHNICAL_LIQUIDITY_FACTOR_NAMES,
            (
                "rsi_reversal_liquid_14_20",
                "bollinger_reversal_liquid_20",
            ),
        )

    def test_liquidity_combo_excludes_low_adv_assets_before_ranking(self):
        factors = compute_public_technical_liquidity_factors(
            _bars(day_count=35),
            factor_names=("rsi_reversal_liquid_14_20",),
        )
        last_date = pd.Timestamp("2024-02-16").date()
        rows = factors[factors["date"] == last_date]
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertFalse(pd.isna(values["CN_TEST_LIQUID_OVERSOLD"]))
        self.assertFalse(pd.isna(values["CN_TEST_LIQUID_STABLE"]))
        self.assertTrue(pd.isna(values["CN_TEST_ILLIQUID_OVERSOLD"]))

    def test_liquidity_combo_prefers_liquid_oversold_peer(self):
        factors = compute_public_technical_liquidity_factors(
            _bars(day_count=35),
            factor_names=("bollinger_reversal_liquid_20",),
        )
        last_date = pd.Timestamp("2024-02-16").date()
        rows = factors[factors["date"] == last_date].dropna(subset=["factor_value"])
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        self.assertGreater(values["CN_TEST_LIQUID_OVERSOLD"], values["CN_TEST_LIQUID_STABLE"])

    def test_liquidity_combo_filters_extreme_one_day_return_rows(self):
        factors = compute_public_technical_liquidity_factors(
            _bars(day_count=35, liquid_oversold_final_price=1.0),
            factor_names=("rsi_reversal_liquid_14_20",),
        )
        last = factors[
            (factors["asset_id"] == "CN_TEST_LIQUID_OVERSOLD")
            & (factors["date"] == pd.Timestamp("2024-02-16").date())
        ].iloc[0]

        self.assertTrue(pd.isna(last["factor_value"]))

    def test_liquidity_combo_uses_only_current_and_past_rows(self):
        baseline = compute_public_technical_liquidity_factors(_bars(day_count=30))
        with_future = compute_public_technical_liquidity_factors(_bars(day_count=31, future_spike=True))

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-02-09").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_liquidity_combo_rejects_unknown_requested_names(self):
        with self.assertRaisesRegex(ValueError, "Unsupported public technical liquidity factor_names"):
            compute_public_technical_liquidity_factors(_bars(day_count=25), factor_names=("missing",))


def _bars(
    *,
    day_count: int,
    liquid_oversold_final_price: float = 8.0,
    future_spike: bool = False,
) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    rows = []
    assets = {
        "CN_TEST_LIQUID_OVERSOLD": {
            "base": 12.0,
            "amount": 5_000_000.0,
            "final": liquid_oversold_final_price,
        },
        "CN_TEST_LIQUID_STABLE": {
            "base": 10.0,
            "amount": 4_500_000.0,
            "final": 10.2,
        },
        "CN_TEST_ILLIQUID_OVERSOLD": {
            "base": 12.0,
            "amount": 20_000.0,
            "final": 8.0,
        },
    }
    for asset_id, spec in assets.items():
        for index, date in enumerate(dates):
            if index == day_count - 1 and future_spike:
                price = 1000.0
            elif index == day_count - 2 and future_spike:
                price = spec["final"]
            elif index == day_count - 1:
                price = spec["final"]
            else:
                price = spec["base"] + 0.02 * index
            rows.append(
                {
                    "date": date.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price,
                    "low": price,
                    "amount": spec["amount"],
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
