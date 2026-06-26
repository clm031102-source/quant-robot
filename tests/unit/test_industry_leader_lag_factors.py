import unittest

import pandas as pd

from quant_robot.factors.industry_leader_lag import (
    INDUSTRY_LEADER_LAG_FACTOR_NAMES,
    compute_industry_leader_lag_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class IndustryLeaderLagFactorTests(unittest.TestCase):
    def test_industry_leader_lag_exports_schema_and_registered_names(self) -> None:
        factors = compute_industry_leader_lag_factors(_bars(day_count=55), stock_basic=_stock_basic())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(INDUSTRY_LEADER_LAG_FACTOR_NAMES))
        self.assertEqual(
            INDUSTRY_LEADER_LAG_FACTOR_NAMES,
            (
                "industry_leader_laggard_gap_reversion_5_20",
                "industry_leader_breakout_laggard_followthrough_10_5",
                "industry_leader_volume_confirmed_diffusion_5_20",
                "industry_peer_dispersion_compression_reversal_20_5",
                "industry_leader_pullback_resilience_10_5",
                "industry_laggard_lowvol_catchup_composite_20",
            ),
        )

    def test_leader_laggard_gap_prefers_laggard_behind_strong_liquid_leader(self) -> None:
        factors = compute_industry_leader_lag_factors(
            _bars(day_count=55),
            stock_basic=_stock_basic(),
            factor_names=("industry_leader_laggard_gap_reversion_5_20",),
        )
        values = _values_on(factors, "2024-03-15")

        self.assertGreater(values["CN_TECH_LAGGARD"], values["CN_TECH_LEADER"])
        self.assertGreater(values["CN_TECH_LAGGARD"], values["CN_BANK_LAGGARD"])

    def test_volume_confirmed_diffusion_prefers_leader_with_rising_amount(self) -> None:
        factors = compute_industry_leader_lag_factors(
            _bars(day_count=55),
            stock_basic=_stock_basic(),
            factor_names=("industry_leader_volume_confirmed_diffusion_5_20",),
        )
        values = _values_on(factors, "2024-03-15")

        self.assertGreater(values["CN_TECH_LAGGARD"], values["CN_BANK_LAGGARD"])

    def test_industry_leader_lag_uses_only_current_and_past_rows(self) -> None:
        baseline = compute_industry_leader_lag_factors(_bars(day_count=55), stock_basic=_stock_basic())
        with_future = compute_industry_leader_lag_factors(
            _bars(day_count=56, future_spike=True),
            stock_basic=_stock_basic(),
        )

        before_future = with_future[with_future["date"] <= pd.Timestamp("2024-03-15").date()]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )

    def test_industry_leader_lag_rejects_unknown_requested_names(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported industry leader-lag factor_names"):
            compute_industry_leader_lag_factors(_bars(day_count=55), stock_basic=_stock_basic(), factor_names=("missing",))


def _values_on(factors: pd.DataFrame, date: str) -> dict[str, float]:
    rows = factors[factors["date"] == pd.Timestamp(date).date()].dropna(subset=["factor_value"])
    return dict(zip(rows["asset_id"], rows["factor_value"], strict=True))


def _stock_basic() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"asset_id": "CN_TECH_LEADER", "industry": "tech"},
            {"asset_id": "CN_TECH_LAGGARD", "industry": "tech"},
            {"asset_id": "CN_TECH_PEER", "industry": "tech"},
            {"asset_id": "CN_BANK_LEADER", "industry": "bank"},
            {"asset_id": "CN_BANK_LAGGARD", "industry": "bank"},
            {"asset_id": "CN_BANK_PEER", "industry": "bank"},
        ]
    )


def _bars(*, day_count: int, future_spike: bool = False) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=day_count, freq="B")
    path_count = day_count - 1 if future_spike else day_count
    prices = {
        "CN_TECH_LEADER": _trend(path_count, start=20.0, step=0.28),
        "CN_TECH_LAGGARD": _flat_then_dip(path_count, start=10.0),
        "CN_TECH_PEER": _trend(path_count, start=12.0, step=0.04),
        "CN_BANK_LEADER": _trend(path_count, start=18.0, step=0.04),
        "CN_BANK_LAGGARD": _trend(path_count, start=11.0, step=0.03),
        "CN_BANK_PEER": _trend(path_count, start=13.0, step=0.02),
    }
    base_amount = {
        "CN_TECH_LEADER": 120_000_000.0,
        "CN_TECH_LAGGARD": 35_000_000.0,
        "CN_TECH_PEER": 30_000_000.0,
        "CN_BANK_LEADER": 110_000_000.0,
        "CN_BANK_LAGGARD": 36_000_000.0,
        "CN_BANK_PEER": 32_000_000.0,
    }
    rows = []
    for asset_id, path in prices.items():
        for index, signal_date in enumerate(dates):
            price = 1000.0 if future_spike and index == day_count - 1 else path[index]
            amount_growth = 1.0 + (0.012 * index if asset_id == "CN_TECH_LEADER" else 0.001 * index)
            rows.append(
                {
                    "date": signal_date.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": base_amount[asset_id] * amount_growth,
                }
            )
    return pd.DataFrame(rows)


def _trend(day_count: int, *, start: float, step: float) -> list[float]:
    return [start + step * index for index in range(day_count)]


def _flat_then_dip(day_count: int, *, start: float) -> list[float]:
    values = [start + 0.01 * index for index in range(day_count)]
    for offset, index in enumerate(range(max(0, day_count - 12), day_count)):
        values[index] = values[index - 1] * (0.985 if offset % 2 == 0 else 1.002)
    return values


if __name__ == "__main__":
    unittest.main()
