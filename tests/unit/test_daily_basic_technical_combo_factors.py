import unittest

import pandas as pd

from quant_robot.factors.daily_basic_technical_combo import (
    DAILY_BASIC_TECHNICAL_COMBO_FACTOR_NAMES,
    compute_daily_basic_technical_combo_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class DailyBasicTechnicalComboFactorTests(unittest.TestCase):
    def test_combo_factor_builder_emits_schema_columns(self):
        factors = compute_daily_basic_technical_combo_factors(_bars(), _daily_basic_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(DAILY_BASIC_TECHNICAL_COMBO_FACTOR_NAMES))
        self.assertTrue((factors["lookback_window"] == 20).all())

    def test_liquid_low_turnover_bucket_rank_excludes_illiquid_names(self):
        factors = compute_daily_basic_technical_combo_factors(
            _bars(),
            _daily_basic_inputs(),
            factor_names=("turnover_rate_low_liquid_mv_bucket_rank",),
        )

        rows = factors[factors["date"] == pd.Timestamp("2024-01-03").date()]
        values = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))

        for bucket in range(5):
            self.assertGreater(values[f"CN_TEST_LIQUID_LOW_TURN_{bucket}"], values[f"CN_TEST_LIQUID_HIGH_TURN_{bucket}"])
            self.assertTrue(pd.isna(values[f"CN_TEST_ILLIQUID_LOW_TURN_{bucket}"]))

    def test_unknown_combo_factor_name_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported daily-basic technical combo factor_names"):
            compute_daily_basic_technical_combo_factors(_bars(), _daily_basic_inputs(), factor_names=("missing",))


def _bars() -> pd.DataFrame:
    rows = []
    for date in (pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()):
        for bucket in range(5):
            rows.extend(
                [
                    _bar_row(date, f"CN_TEST_LIQUID_LOW_TURN_{bucket}", 2_000_000 + bucket),
                    _bar_row(date, f"CN_TEST_LIQUID_HIGH_TURN_{bucket}", 1_800_000 + bucket),
                    _bar_row(date, f"CN_TEST_ILLIQUID_LOW_TURN_{bucket}", 1_000 + bucket),
                ]
            )
    return pd.DataFrame(rows)


def _bar_row(date, asset_id: str, amount: float) -> dict:
    return {
        "date": date,
        "asset_id": asset_id,
        "market": "CN",
        "adj_close": 10.0,
        "volume": amount / 10.0,
        "amount": amount,
        "source": "fixture",
    }


def _daily_basic_inputs() -> pd.DataFrame:
    rows = []
    for date in (pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()):
        for bucket in range(5):
            circ_mv = 10_000.0 * (10 ** bucket)
            rows.extend(
                [
                    _daily_row(date, f"CN_TEST_LIQUID_LOW_TURN_{bucket}", 1.0, 1.1, circ_mv),
                    _daily_row(date, f"CN_TEST_LIQUID_HIGH_TURN_{bucket}", 3.0, 3.1, circ_mv * 1.1),
                    _daily_row(date, f"CN_TEST_ILLIQUID_LOW_TURN_{bucket}", 0.5, 0.6, circ_mv * 1.2),
                ]
            )
    return pd.DataFrame(rows)


def _daily_row(date, asset_id: str, turnover_rate: float, turnover_rate_f: float, circ_mv: float) -> dict:
    return {
        "date": date,
        "asset_id": asset_id,
        "market": "CN",
        "turnover_rate": turnover_rate,
        "turnover_rate_f": turnover_rate_f,
        "volume_ratio": 1.0,
        "pe_ttm": 10.0,
        "pb": 2.0,
        "ps_ttm": 5.0,
        "dv_ttm": 3.0,
        "total_mv": circ_mv * 1.2,
        "circ_mv": circ_mv,
    }


if __name__ == "__main__":
    unittest.main()
