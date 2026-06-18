import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from quant_robot.factors.technical import compute_basic_factors
from quant_robot.factors.tushare_moneyflow import compute_moneyflow_factors
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

    def test_combo_builder_computes_only_dependencies_for_requested_factors(self):
        with (
            patch(
                "quant_robot.factors.moneyflow_technical.compute_moneyflow_factors",
                wraps=compute_moneyflow_factors,
            ) as moneyflow_builder,
            patch(
                "quant_robot.factors.moneyflow_technical.compute_basic_factors",
                wraps=compute_basic_factors,
            ) as technical_builder,
        ):
            factors = compute_moneyflow_technical_combo_factors(
                _liquidity_framework_bars(),
                _liquidity_framework_moneyflow_inputs(),
                factor_names=("large_resid_liquidity_gate_20",),
            )

        self.assertEqual(set(factors["factor_name"]), {"large_resid_liquidity_gate_20"})
        self.assertEqual(moneyflow_builder.call_args.kwargs["factor_names"], ("large_order_net_amount_ratio",))
        self.assertEqual(technical_builder.call_args.kwargs["factor_names"], ("liquidity_20",))

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

    def test_liquidity_gate_can_use_separate_gate_factor(self):
        bars = _liquidity_framework_bars()
        factors = compute_moneyflow_technical_combo_factors(
            bars,
            _liquidity_framework_moneyflow_inputs(),
            factor_names=("mf_low_minus_volatility_liquidity_gate_20",),
        )
        last_date = pd.Timestamp("2024-01-25").date()

        selected = factors[
            (factors["date"] == last_date)
            & (factors["factor_name"] == "mf_low_minus_volatility_liquidity_gate_20")
        ]
        values = dict(zip(selected["asset_id"], selected["factor_value"], strict=True))

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

    def test_residualized_liquidity_volatility_amount_factor_removes_multiple_exposures(self):
        bars = _multi_exposure_framework_bars()
        factors = compute_moneyflow_technical_combo_factors(
            bars,
            _multi_exposure_framework_moneyflow_inputs(),
            factor_names=("large_resid_liq_vol_amt_20",),
        )
        last_date = pd.Timestamp("2024-01-25").date()

        selected = factors[
            (factors["date"] == last_date) & (factors["factor_name"] == "large_resid_liq_vol_amt_20")
        ].set_index("asset_id")
        technical = compute_basic_factors(bars, windows=(20,))
        liquidity = technical[
            (technical["date"] == last_date) & (technical["factor_name"] == "liquidity_20")
        ].set_index("asset_id")["factor_value"]
        volatility = technical[
            (technical["date"] == last_date) & (technical["factor_name"] == "volatility_20")
        ].set_index("asset_id")["factor_value"]
        last_bars = bars[pd.to_datetime(bars["date"]).dt.date == last_date].set_index("asset_id")
        log_amount = pd.Series(np.log1p(last_bars["amount"].astype(float)), index=last_bars.index)
        aligned = pd.concat(
            [
                selected["factor_value"],
                _zscore(liquidity),
                _zscore(volatility),
                _zscore(log_amount),
            ],
            axis=1,
            keys=["residual", "liquidity", "volatility", "log_amount"],
        ).dropna()

        self.assertEqual(len(aligned), 6)
        self.assertAlmostEqual(float(aligned["residual"].mean()), 0.0, places=12)
        self.assertAlmostEqual(float(aligned["residual"].corr(aligned["liquidity"])), 0.0, places=12)
        self.assertAlmostEqual(float(aligned["residual"].corr(aligned["volatility"])), 0.0, places=12)
        self.assertAlmostEqual(float(aligned["residual"].corr(aligned["log_amount"])), 0.0, places=12)

    def test_residualized_liquidity_volatility_amount_gate_blocks_thin_signal_amounts(self):
        bars = _multi_exposure_framework_bars()
        factors = compute_moneyflow_technical_combo_factors(
            bars,
            _multi_exposure_framework_moneyflow_inputs(),
            factor_names=("large_resid_liq_vol_amt_gate_20",),
        )
        last_date = pd.Timestamp("2024-01-25").date()

        selected = factors[
            (factors["date"] == last_date) & (factors["factor_name"] == "large_resid_liq_vol_amt_gate_20")
        ]
        values = dict(zip(selected["asset_id"], selected["factor_value"], strict=True))

        self.assertTrue(pd.notna(values["CN_XSHE_000001"]))
        self.assertTrue(pd.notna(values["CN_XSHE_000002"]))
        self.assertTrue(pd.notna(values["CN_XSHG_600519"]))
        self.assertTrue(pd.notna(values["CN_XSHG_600000"]))
        self.assertTrue(pd.isna(values["CN_XSHG_601398"]))

    def test_residualized_liquidity_volatility_amount_gate_does_not_use_future_rows(self):
        bars = _multi_exposure_framework_bars()
        moneyflow = _multi_exposure_framework_moneyflow_inputs()
        future_bars = _future_spike_bars(bars)
        future_moneyflow = _future_spike_moneyflow_inputs(moneyflow)

        baseline = compute_moneyflow_technical_combo_factors(
            bars,
            moneyflow,
            factor_names=("large_resid_liq_vol_amt_gate_20",),
        )
        with_future = compute_moneyflow_technical_combo_factors(
            pd.concat([bars, future_bars], ignore_index=True),
            pd.concat([moneyflow, future_moneyflow], ignore_index=True),
            factor_names=("large_resid_liq_vol_amt_gate_20",),
        )

        original_last_date = pd.Timestamp("2024-01-25").date()
        before_future = with_future[pd.to_datetime(with_future["date"]).dt.date <= original_last_date]
        pd.testing.assert_frame_equal(
            baseline.reset_index(drop=True),
            before_future.reset_index(drop=True),
            check_like=True,
        )


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


def _multi_exposure_framework_bars() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=25).date
    settings = {
        "CN_XSHE_000001": ("000001.SZ", 200_000_000.0, 0.10, 0.020),
        "CN_XSHE_000002": ("000002.SZ", 160_000_000.0, -0.05, 0.012),
        "CN_XSHG_600519": ("600519.SH", 120_000_000.0, 0.03, 0.018),
        "CN_XSHG_601398": ("601398.SH", 80_000_000.0, -0.02, 0.010),
        "CN_XSHE_000003": ("000003.SZ", 300_000_000.0, 0.08, 0.026),
        "CN_XSHG_600000": ("600000.SH", 220_000_000.0, -0.07, 0.015),
    }
    for asset_index, (asset_id, (symbol, amount, slope, wave)) in enumerate(settings.items()):
        for day_index, date in enumerate(dates):
            price = 10.0 + asset_index + slope * day_index + wave * ((day_index % 5) - 2) ** 2
            rows.append(
                {
                    "asset_id": asset_id,
                    "symbol": symbol,
                    "market": "CN",
                    "exchange": "XSHE" if asset_id.startswith("CN_XSHE") else "XSHG",
                    "asset_type": "stock",
                    "timestamp": pd.Timestamp(date).tz_localize("UTC"),
                    "date": date,
                    "timezone": "Asia/Shanghai",
                    "calendar": "XSHG",
                    "frequency": "1d",
                    "open": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
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


def _multi_exposure_framework_moneyflow_inputs() -> pd.DataFrame:
    rows = []
    dates = pd.date_range("2024-01-01", periods=25).date
    offsets = {
        "CN_XSHE_000001": ("000001.SZ", 120.0),
        "CN_XSHE_000002": ("000002.SZ", -35.0),
        "CN_XSHG_600519": ("600519.SH", 55.0),
        "CN_XSHG_601398": ("601398.SH", 15.0),
        "CN_XSHE_000003": ("000003.SZ", 95.0),
        "CN_XSHG_600000": ("600000.SH", -70.0),
    }
    for date in dates:
        for asset_id, (symbol, offset) in offsets.items():
            positive = max(offset, 0.0)
            negative = abs(min(offset, 0.0))
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
                    "buy_lg_amount": 100.0 + positive,
                    "sell_lg_amount": 100.0 + negative,
                    "buy_elg_amount": 100.0 + positive,
                    "sell_elg_amount": 100.0 + negative,
                    "net_mf_amount": offset,
                }
            )
    return pd.DataFrame(rows)


def _zscore(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return (numeric - numeric.mean()) / numeric.std(ddof=0)


def _future_spike_bars(bars: pd.DataFrame) -> pd.DataFrame:
    rows = bars[pd.to_datetime(bars["date"]).dt.date == pd.Timestamp("2024-01-25").date()].copy()
    rows["date"] = pd.Timestamp("2024-01-26").date()
    rows["timestamp"] = pd.Timestamp("2024-01-26", tz="UTC")
    rows["open"] = rows["open"].astype(float) * 100.0
    rows["high"] = rows["high"].astype(float) * 120.0
    rows["low"] = rows["low"].astype(float) * 80.0
    rows["close"] = rows["close"].astype(float) * 100.0
    rows["adj_close"] = rows["adj_close"].astype(float) * 100.0
    rows["amount"] = rows["amount"].astype(float) * 1_000.0
    rows["volume"] = rows["volume"].astype(float) * 1_000.0
    rows["vwap"] = rows["vwap"].astype(float) * 100.0
    return rows


def _future_spike_moneyflow_inputs(moneyflow: pd.DataFrame) -> pd.DataFrame:
    rows = moneyflow[pd.to_datetime(moneyflow["date"]).dt.date == pd.Timestamp("2024-01-25").date()].copy()
    rows["date"] = pd.Timestamp("2024-01-26").date()
    for column in [
        "buy_sm_amount",
        "sell_sm_amount",
        "buy_md_amount",
        "sell_md_amount",
        "buy_lg_amount",
        "sell_lg_amount",
        "buy_elg_amount",
        "sell_elg_amount",
        "net_mf_amount",
    ]:
        rows[column] = rows[column].astype(float) * 1_000.0
    return rows


if __name__ == "__main__":
    unittest.main()
