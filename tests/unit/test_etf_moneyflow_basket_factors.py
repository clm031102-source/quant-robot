import unittest

import pandas as pd

from quant_robot.factors.etf_moneyflow_basket import (
    ETF_MONEYFLOW_BASKET_FACTOR_NAMES,
    aggregate_etf_moneyflow_basket_inputs,
    compute_etf_moneyflow_basket_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class EtfMoneyflowBasketFactorTests(unittest.TestCase):
    def test_aggregate_uses_only_basket_rows_known_on_signal_date(self):
        aggregated = aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs(), _basket_mapping())

        first = aggregated[aggregated["date"] == pd.Timestamp("2024-01-02").date()]
        second = aggregated[aggregated["date"] == pd.Timestamp("2024-01-03").date()]

        self.assertEqual(first["asset_id"].tolist(), ["CN_ETF_XSHG_510300"])
        self.assertAlmostEqual(first.iloc[0]["basket_weight_sum"], 0.6)
        self.assertAlmostEqual(first.iloc[0]["etf_net_mf_amount_ratio"], 120.0 / 3030.0)
        self.assertAlmostEqual(first.iloc[0]["etf_net_mf_positive_weight"], 1.0)
        self.assertAlmostEqual(second.iloc[0]["basket_weight_sum"], 1.0)
        expected = 0.6 * (130.0 / 3030.0) + 0.4 * (-50.0 / 1515.0)
        self.assertAlmostEqual(second.iloc[0]["etf_net_mf_amount_ratio"], expected)

    def test_factor_builder_emits_etf_schema_and_low_variants(self):
        aggregated = aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs(), _basket_mapping())

        factors = compute_etf_moneyflow_basket_factors(aggregated)

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(ETF_MONEYFLOW_BASKET_FACTOR_NAMES))
        self.assertEqual(set(factors["market"]), {"CN_ETF"})
        second = factors[factors["date"] == pd.Timestamp("2024-01-03").date()]
        values = dict(zip(second["factor_name"], second["factor_value"], strict=True))
        self.assertAlmostEqual(values["etf_net_mf_amount_ratio_low"], -values["etf_net_mf_amount_ratio"])
        self.assertAlmostEqual(values["etf_small_order_sell_pressure_low"], -values["etf_small_order_sell_pressure"])
        self.assertAlmostEqual(values["etf_net_mf_positive_weight_low"], -values["etf_net_mf_positive_weight"])

    def test_aggregate_requires_point_in_time_known_date(self):
        baskets = _basket_mapping().drop(columns=["known_date"])

        with self.assertRaisesRegex(ValueError, "known_date"):
            aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs(), baskets)

    def test_aggregate_allows_optional_etf_symbol(self):
        baskets = _basket_mapping().drop(columns=["etf_symbol"])

        aggregated = aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs(), baskets)

        self.assertEqual(aggregated["asset_id"].unique().tolist(), ["CN_ETF_XSHG_510300"])
        self.assertEqual(aggregated["symbol"].unique().tolist(), ["CN_ETF_XSHG_510300"])


def _moneyflow_inputs() -> pd.DataFrame:
    rows = []
    for date, first_net, second_net in [
        (pd.Timestamp("2024-01-02").date(), 120.0, -40.0),
        (pd.Timestamp("2024-01-03").date(), 130.0, -50.0),
    ]:
        rows.extend(
            [
                _moneyflow_row(date, "CN_XSHG_600519", "600519.SH", first_net, 100.0),
                _moneyflow_row(date, "CN_XSHE_000001", "000001.SZ", second_net, 50.0),
            ]
        )
    return pd.DataFrame(rows)


def _moneyflow_row(date, asset_id, symbol, net_mf_amount, scale):
    return {
        "date": date,
        "asset_id": asset_id,
        "symbol": symbol,
        "market": "CN",
        "buy_sm_amount": 1.0 * scale,
        "sell_sm_amount": 0.8 * scale,
        "buy_md_amount": 3.0 * scale,
        "sell_md_amount": 2.5 * scale,
        "buy_lg_amount": 5.0 * scale,
        "sell_lg_amount": 4.5 * scale,
        "buy_elg_amount": 7.0 * scale,
        "sell_elg_amount": 6.5 * scale,
        "net_mf_amount": net_mf_amount,
    }


def _basket_mapping() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "etf_asset_id": ["CN_ETF_XSHG_510300", "CN_ETF_XSHG_510300"],
            "etf_symbol": ["510300.SH", "510300.SH"],
            "stock_asset_id": ["CN_XSHG_600519", "CN_XSHE_000001"],
            "stock_symbol": ["600519.SH", "000001.SZ"],
            "weight": [0.6, 0.4],
            "known_date": [pd.Timestamp("2024-01-01").date(), pd.Timestamp("2024-01-03").date()],
            "end_date": [pd.NaT, pd.NaT],
            "source": ["fixture_basket", "fixture_basket"],
        }
    )


if __name__ == "__main__":
    unittest.main()
