import unittest

import pandas as pd

from quant_robot.factors.technical import compute_basic_factors
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

    def test_liquidity_gate_factor_keeps_only_lower_amihud_half(self):
        bars = _liquidity_framework_bars()
        factors = compute_moneyflow_technical_combo_factors(
            bars,
            _liquidity_framework_moneyflow_inputs(),
            factor_names=("large_liquidity_gate_20",),
        )
        last_date = pd.Timestamp("2024-01-25").date()

        selected = factors[(factors["date"] == last_date) & (factors["factor_name"] == "large_liquidity_gate_20")]
        values = dict(zip(selected["asset_id"], selected["factor_value"], strict=True))
        liquidity = compute_basic_factors(bars, windows=(20,))
        last_liquidity = liquidity[(liquidity["date"] == last_date) & (liquidity["factor_name"] == "liquidity_20")]
        threshold = last_liquidity["factor_value"].quantile(0.5)
        liquid_assets = set(last_liquidity.loc[last_liquidity["factor_value"] <= threshold, "asset_id"])

        self.assertEqual(liquid_assets, {"CN_XSHE_000001", "CN_XSHE_000002"})
        self.assertTrue(pd.notna(values["CN_XSHE_000001"]))
        self.assertTrue(pd.notna(values["CN_XSHE_000002"]))
        self.assertTrue(pd.isna(values["CN_XSHG_600519"]))
        self.assertTrue(pd.isna(values["CN_XSHG_601398"]))

    def test_residualized_factor_removes_same_day_liquidity_exposure(self):
        bars = _liquidity_framework_bars()
        factors = compute_moneyflow_technical_combo_factors(
            bars,
            _liquidity_framework_moneyflow_inputs(),
            factor_names=("large_resid_liquidity_20",),
        )
        last_date = pd.Timestamp("2024-01-25").date()

        selected = factors[
            (factors["date"] == last_date) & (factors["factor_name"] == "large_resid_liquidity_20")
        ].set_index("asset_id")
        liquidity = compute_basic_factors(bars, windows=(20,))
        last_liquidity = liquidity[
            (liquidity["date"] == last_date) & (liquidity["factor_name"] == "liquidity_20")
        ].set_index("asset_id")
        aligned = pd.concat(
            [selected["factor_value"], last_liquidity["factor_value"]],
            axis=1,
            keys=["residual", "liquidity"],
        ).dropna()

        self.assertEqual(len(aligned), 4)
        self.assertAlmostEqual(float(aligned["residual"].mean()), 0.0, places=12)
        self.assertAlmostEqual(float(aligned["residual"].corr(aligned["liquidity"])), 0.0, places=12)


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


def _liquidity_framework_bars() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=25).date
    amount_by_asset = {
        "CN_XSHE_000001": 1_000_000.0,
        "CN_XSHE_000002": 500_000.0,
        "CN_XSHG_600519": 100_000.0,
        "CN_XSHG_601398": 50_000.0,
    }
    symbols = {
        "CN_XSHE_000001": "000001.SZ",
        "CN_XSHE_000002": "000002.SZ",
        "CN_XSHG_600519": "600519.SH",
        "CN_XSHG_601398": "601398.SH",
    }
    for asset_index, (asset_id, amount) in enumerate(amount_by_asset.items()):
        for day_index, date in enumerate(dates):
            price = 10.0 + asset_index + day_index * 0.1
            rows.append(
                {
                    "asset_id": asset_id,
                    "symbol": symbols[asset_id],
                    "market": "CN",
                    "exchange": "XSHE" if asset_id.startswith("CN_XSHE") else "XSHG",
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
                    "volume": amount / price,
                    "amount": amount,
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


def _liquidity_framework_moneyflow_inputs() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=25).date
    offsets = {
        "CN_XSHE_000001": 80.0,
        "CN_XSHE_000002": 40.0,
        "CN_XSHG_600519": -20.0,
        "CN_XSHG_601398": -60.0,
    }
    symbols = {
        "CN_XSHE_000001": "000001.SZ",
        "CN_XSHE_000002": "000002.SZ",
        "CN_XSHG_600519": "600519.SH",
        "CN_XSHG_601398": "601398.SH",
    }
    for date in dates:
        for asset_id, offset in offsets.items():
            positive = max(offset, 0.0)
            negative = abs(min(offset, 0.0))
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": symbols[asset_id],
                    "market": "CN",
                    "source": "tushare_moneyflow",
                    "buy_sm_amount": 100.0,
                    "sell_sm_amount": 100.0,
                    "buy_md_amount": 100.0,
                    "sell_md_amount": 100.0,
                    "buy_lg_amount": 100.0 + positive,
                    "sell_lg_amount": 100.0 + negative,
                    "buy_elg_amount": 100.0 + positive,
                    "sell_elg_amount": 100.0 + negative,
                    "net_mf_amount": offset,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
