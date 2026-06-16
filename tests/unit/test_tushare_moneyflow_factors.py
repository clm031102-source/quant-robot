import unittest

import pandas as pd

from quant_robot.factors.tushare_moneyflow import MONEYFLOW_FACTOR_NAMES, compute_moneyflow_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


class TushareMoneyflowFactorTests(unittest.TestCase):
    def test_moneyflow_factor_builder_emits_schema_columns(self):
        factors = compute_moneyflow_factors(_moneyflow_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(MONEYFLOW_FACTOR_NAMES))
        self.assertTrue((factors["lookback_window"] == 1).all())

    def test_moneyflow_factor_builder_computes_signed_ratios_and_low_variants(self):
        factors = compute_moneyflow_factors(_moneyflow_inputs())

        first = factors[factors["date"] == pd.Timestamp("2024-01-02").date()]
        values = dict(zip(first["factor_name"], first["factor_value"], strict=True))

        total_amount = 100.0 + 80.0 + 300.0 + 250.0 + 500.0 + 450.0 + 700.0 + 650.0
        self.assertAlmostEqual(values["net_mf_amount_ratio"], 120.0 / total_amount)
        self.assertAlmostEqual(values["net_mf_amount_ratio_low"], -120.0 / total_amount)
        self.assertAlmostEqual(values["large_order_net_amount_ratio"], 100.0 / total_amount)
        self.assertAlmostEqual(values["large_order_net_amount_ratio_low"], -100.0 / total_amount)
        self.assertAlmostEqual(values["extra_large_order_net_amount_ratio"], 50.0 / total_amount)
        self.assertAlmostEqual(values["extra_large_order_net_amount_ratio_low"], -50.0 / total_amount)
        self.assertAlmostEqual(values["small_order_sell_pressure"], -20.0 / total_amount)
        self.assertAlmostEqual(values["small_order_sell_pressure_low"], 20.0 / total_amount)

    def test_moneyflow_factor_builder_treats_zero_denominators_as_missing(self):
        factors = compute_moneyflow_factors(_moneyflow_inputs())

        second = factors[factors["date"] == pd.Timestamp("2024-01-03").date()]
        values = dict(zip(second["factor_name"], second["factor_value"], strict=True))

        self.assertTrue(all(pd.isna(value) for value in values.values()))


def _moneyflow_inputs() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
            "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
            "market": ["CN", "CN"],
            "buy_sm_amount": [100.0, 0.0],
            "sell_sm_amount": [80.0, 0.0],
            "buy_md_amount": [300.0, 0.0],
            "sell_md_amount": [250.0, 0.0],
            "buy_lg_amount": [500.0, 0.0],
            "sell_lg_amount": [450.0, 0.0],
            "buy_elg_amount": [700.0, 0.0],
            "sell_elg_amount": [650.0, 0.0],
            "net_mf_amount": [120.0, 0.0],
        }
    )


if __name__ == "__main__":
    unittest.main()
