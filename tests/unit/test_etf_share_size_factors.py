import unittest

import pandas as pd

from quant_robot.factors.etf_share_size import ETF_SHARE_SIZE_FACTOR_NAMES, compute_etf_share_size_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


class EtfShareSizeFactorTests(unittest.TestCase):
    def test_etf_share_size_factor_builder_emits_schema_columns(self):
        factors = compute_etf_share_size_factors(_share_size_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(ETF_SHARE_SIZE_FACTOR_NAMES))
        self.assertTrue((factors["lookback_window"] == 1).all())

    def test_etf_share_size_factor_builder_computes_demand_pressure_proxies(self):
        factors = compute_etf_share_size_factors(_share_size_inputs())

        second = factors[factors["date"] == pd.Timestamp("2024-01-03").date()]
        values = dict(zip(second["factor_name"], second["factor_value"], strict=True))

        self.assertAlmostEqual(values["share_change_1d"], 0.01)
        self.assertAlmostEqual(values["share_change_1d_low"], -0.01)
        self.assertAlmostEqual(values["size_change_1d"], 0.02)
        self.assertAlmostEqual(values["size_change_1d_low"], -0.02)
        self.assertAlmostEqual(values["nav_premium_discount"], 0.01)
        self.assertAlmostEqual(values["nav_premium_discount_low"], -0.01)
        self.assertAlmostEqual(values["total_share_log"], 16.128045968954253)
        self.assertAlmostEqual(values["total_size_log"], 17.7473361906886)

    def test_etf_share_size_factor_builder_falls_back_to_total_share_changes(self):
        inputs = _share_size_inputs().drop(columns=["share_change_1d", "size_change_1d"])

        factors = compute_etf_share_size_factors(inputs)
        second = factors[factors["date"] == pd.Timestamp("2024-01-03").date()]
        values = dict(zip(second["factor_name"], second["factor_value"], strict=True))

        self.assertAlmostEqual(values["share_change_1d"], 0.01)
        self.assertAlmostEqual(values["size_change_1d"], 0.02)

    def test_etf_share_size_factor_builder_treats_invalid_denominators_as_missing(self):
        factors = compute_etf_share_size_factors(_invalid_inputs())

        first = factors[factors["date"] == pd.Timestamp("2024-01-02").date()]
        values = dict(zip(first["factor_name"], first["factor_value"], strict=True))

        self.assertTrue(pd.isna(values["nav_premium_discount"]))
        self.assertTrue(pd.isna(values["total_share_log"]))
        self.assertTrue(pd.isna(values["total_size_log"]))


def _share_size_inputs() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
            "asset_id": ["CN_ETF_XSHG_510300", "CN_ETF_XSHG_510300"],
            "market": ["CN_ETF", "CN_ETF"],
            "total_share": [10_000_000.0, 10_100_000.0],
            "total_size": [50_000_000.0, 51_000_000.0],
            "nav": [5.0, 5.0],
            "close": [5.0, 5.05],
            "share_change_1d": [pd.NA, 0.01],
            "size_change_1d": [pd.NA, 0.02],
            "nav_premium_discount": [0.0, 0.01],
        }
    )


def _invalid_inputs() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-02").date()],
            "asset_id": ["CN_ETF_XSHG_510300"],
            "market": ["CN_ETF"],
            "total_share": [0.0],
            "total_size": [0.0],
            "nav": [0.0],
            "close": [5.0],
        }
    )


if __name__ == "__main__":
    unittest.main()
