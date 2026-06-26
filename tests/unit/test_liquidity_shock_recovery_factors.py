import unittest

import pandas as pd

from quant_robot.factors.liquidity_shock_recovery import (
    LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES,
    compute_liquidity_shock_recovery_factors,
)


class LiquidityShockRecoveryFactorTests(unittest.TestCase):
    def test_factor_builder_emits_fixed_liquidity_recovery_names(self) -> None:
        factors = compute_liquidity_shock_recovery_factors(_bars())

        self.assertEqual(set(factors["factor_name"]), set(LIQUIDITY_SHOCK_RECOVERY_FACTOR_NAMES))
        self.assertEqual(list(factors.columns), ["date", "asset_id", "market", "factor_name", "factor_value", "lookback_window"])
        self.assertGreater(factors["factor_value"].notna().sum(), 0)

    def test_factor_builder_can_compute_only_requested_names(self) -> None:
        factors = compute_liquidity_shock_recovery_factors(
            _bars(),
            factor_names=("amihud_shock_reversal_recovery_20_5",),
        )

        self.assertEqual(set(factors["factor_name"]), {"amihud_shock_reversal_recovery_20_5"})

    def test_factor_builder_rejects_unknown_names(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported liquidity shock recovery factor_names"):
            compute_liquidity_shock_recovery_factors(_bars(), factor_names=("missing_factor",))

    def test_factor_builder_does_not_use_future_rows(self) -> None:
        base_bars = _bars()
        edited_bars = base_bars.copy()
        edit_start = pd.Timestamp("2024-03-20").date()
        edit_mask = pd.to_datetime(edited_bars["date"]).dt.date >= edit_start
        edited_bars.loc[edit_mask, "adj_close"] = edited_bars.loc[edit_mask, "adj_close"] * 9.0
        edited_bars.loc[edit_mask, "high"] = edited_bars.loc[edit_mask, "high"] * 9.0
        edited_bars.loc[edit_mask, "low"] = edited_bars.loc[edit_mask, "low"] * 9.0
        edited_bars.loc[edit_mask, "amount"] = edited_bars.loc[edit_mask, "amount"] * 11.0

        base = compute_liquidity_shock_recovery_factors(base_bars)
        edited = compute_liquidity_shock_recovery_factors(edited_bars)
        base_before = base[pd.to_datetime(base["date"]).dt.date < edit_start].reset_index(drop=True)
        edited_before = edited[pd.to_datetime(edited["date"]).dt.date < edit_start].reset_index(drop=True)

        pd.testing.assert_frame_equal(base_before, edited_before)


def _bars() -> pd.DataFrame:
    rows = []
    dates = pd.bdate_range("2024-01-02", periods=90)
    for asset_index in range(6):
        asset_id = f"CN_STOCK_{asset_index:03d}"
        price = 10.0 + asset_index
        for day_index, date_value in enumerate(dates):
            drift = 1.0 + 0.001 * day_index + 0.0005 * asset_index
            cycle = 1.0 + ((day_index % 13) - 6) * 0.002
            if asset_index % 2 == 0 and 35 <= day_index <= 40:
                cycle *= 0.96
            price = max(1.0, price * drift * cycle)
            amount = 20_000_000 + asset_index * 2_000_000 + day_index * 50_000
            if 35 <= day_index <= 40:
                amount *= 2.2 + asset_index * 0.1
            rows.append(
                {
                    "date": date_value.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * (1.0 + 0.01 + asset_index * 0.001),
                    "low": price * (1.0 - 0.012 - asset_index * 0.001),
                    "amount": amount,
                    "source": "fixture",
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
