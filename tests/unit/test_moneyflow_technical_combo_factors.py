import unittest

import pandas as pd

from quant_robot.factors.moneyflow_technical import (
    MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES,
    compute_moneyflow_technical_combo_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class MoneyflowTechnicalComboFactorTests(unittest.TestCase):
    def test_combo_builder_emits_registered_schema_factors(self):
        factors = compute_moneyflow_technical_combo_factors(_combo_bars(), _combo_moneyflow_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES))
        self.assertIn("mf_low_plus_reversal_5", set(factors["factor_name"]))
        self.assertIn("small_sell_plus_reversal_5", set(factors["factor_name"]))
        self.assertIn("mf_low_minus_volatility_20", set(factors["factor_name"]))

    def test_combo_builder_uses_cross_sectional_zscore_formula(self):
        factors = compute_moneyflow_technical_combo_factors(_combo_bars(), _combo_moneyflow_inputs())
        last_date = pd.Timestamp("2024-01-06").date()
        selected = factors[(factors["date"] == last_date) & (factors["factor_name"] == "mf_low_plus_reversal_5")]
        values = dict(zip(selected["asset_id"], selected["factor_value"], strict=True))

        self.assertAlmostEqual(values["CN_XSHE_000001"], -2.0)
        self.assertAlmostEqual(values["CN_XSHG_600519"], 2.0)


def _combo_bars() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=6).date
    paths = {
        "CN_XSHE_000001": [10.0, 11.0, 12.0, 14.0, 16.0, 20.0],
        "CN_XSHG_600519": [20.0, 18.0, 16.0, 14.0, 12.0, 10.0],
    }
    symbols = {"CN_XSHE_000001": "000001.SZ", "CN_XSHG_600519": "600519.SH"}
    for asset_id, prices in paths.items():
        for date, price in zip(dates, prices, strict=True):
            rows.append(
                {
                    "asset_id": asset_id,
                    "symbol": symbols[asset_id],
                    "market": "CN",
                    "exchange": "XSHE" if asset_id.endswith("000001") else "XSHG",
                    "asset_type": "stock",
                    "timestamp": pd.Timestamp(date).tz_localize("UTC"),
                    "date": date,
                    "timezone": "Asia/Shanghai",
                    "calendar": "XSHG",
                    "frequency": "1d",
                    "open": price,
                    "high": price,
                    "low": price,
                    "close": price,
                    "adj_close": price,
                    "volume": 1000.0,
                    "amount": price * 1000.0,
                    "vwap": price,
                    "currency": "CNY",
                    "source": "fixture",
                    "adjusted": True,
                    "ingested_at": pd.Timestamp("2024-01-01", tz="UTC"),
                }
            )
    return pd.DataFrame(rows)


def _combo_moneyflow_inputs() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=6).date
    for date in dates:
        for asset_id, symbol, net in [
            ("CN_XSHE_000001", "000001.SZ", 100.0),
            ("CN_XSHG_600519", "600519.SH", -100.0),
        ]:
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": symbol,
                    "market": "CN",
                    "source": "tushare_moneyflow",
                    "buy_sm_amount": 100.0,
                    "sell_sm_amount": 100.0,
                    "buy_md_amount": 100.0,
                    "sell_md_amount": 100.0,
                    "buy_lg_amount": 150.0,
                    "sell_lg_amount": 100.0,
                    "buy_elg_amount": 150.0,
                    "sell_elg_amount": 100.0,
                    "net_mf_amount": net,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
