import unittest

import pandas as pd

from quant_robot.factors.etf_moneyflow_basket import (
    ETF_MONEYFLOW_BASKET_FACTOR_NAMES,
    aggregate_etf_moneyflow_basket_inputs,
    compute_etf_moneyflow_basket_factors,
)
from quant_robot.schema.factors import FACTOR_COLUMNS


class EtfMoneyflowBasketFactorTests(unittest.TestCase):
    def test_missing_active_constituent_cannot_be_renormalized_away(self):
        inputs = _moneyflow_inputs().iloc[:-1].copy()
        with self.assertRaisesRegex(ValueError, "incomplete.*constituent"):
            aggregate_etf_moneyflow_basket_inputs(inputs, _basket_mapping())

    def test_entire_missing_etf_day_is_detected_even_when_join_is_empty(self):
        inputs = _moneyflow_inputs().copy()
        inputs["asset_id"] = inputs["asset_id"].map(lambda value: value + "_unrelated")
        with self.assertRaisesRegex(ValueError, "incomplete.*constituent"):
            aggregate_etf_moneyflow_basket_inputs(inputs, _basket_mapping())

    def test_duplicate_stock_days_or_overlapping_memberships_are_not_extra_weight(self):
        inputs = _moneyflow_inputs()
        with self.assertRaisesRegex(ValueError, "duplicate.*moneyflow"):
            aggregate_etf_moneyflow_basket_inputs(pd.concat([inputs, inputs.iloc[:1]]), _basket_mapping())
        baskets = _basket_mapping()
        for extra in (baskets.iloc[:1], baskets.iloc[:1].assign(known_date="2024-01-02")):
            with self.subTest(extra=extra.to_dict("records")):
                with self.assertRaisesRegex(ValueError, "overlapping.*membership"):
                    aggregate_etf_moneyflow_basket_inputs(inputs, pd.concat([baskets, extra]))

    def test_invalid_positive_weights_cannot_disappear_in_group_sum(self):
        for value in (float("nan"),float("inf"),-0.4,0,True):
            with self.subTest(value=value):
                baskets=_basket_mapping();baskets["weight"]=baskets["weight"].astype(object)
                baskets.loc[1,"weight"]=value
                with self.assertRaisesRegex(ValueError,"finite positive.*weight"):
                    aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs(),baskets)

    def test_missing_nonfinite_negative_or_zero_denominator_flow_is_not_neutral(self):
        for field,value in (("net_mf_amount",float("nan")),("buy_lg_amount",float("inf")),
                ("sell_sm_amount",-1.0)):
            with self.subTest(field=field,value=value):
                inputs=_moneyflow_inputs();inputs.loc[3,field]=value
                with self.assertRaisesRegex(ValueError,"invalid active constituent moneyflow"):
                    aggregate_etf_moneyflow_basket_inputs(inputs,_basket_mapping())
        inputs=_moneyflow_inputs()
        flow_columns=[c for c in inputs.columns if c.startswith(("buy_","sell_"))]
        inputs.loc[3,flow_columns]=0
        with self.assertRaisesRegex(ValueError,"invalid active constituent moneyflow"):
            aggregate_etf_moneyflow_basket_inputs(inputs,_basket_mapping())

    def test_expired_and_future_memberships_are_not_required_on_other_days(self):
        baskets=_basket_mapping();baskets.loc[0,"end_date"]="2024-01-02"
        inputs=_moneyflow_inputs().iloc[[0,3]].copy()
        result=aggregate_etf_moneyflow_basket_inputs(inputs,baskets)
        self.assertEqual(result["constituent_count"].tolist(),[1,1])
        self.assertEqual(result["basket_weight_sum"].tolist(),[0.6,0.4])

    def test_invalid_end_dates_cannot_silently_become_open_ended(self):
        for value in ("not-a-date","2023-12-31"):
            with self.subTest(value=value):
                baskets=_basket_mapping();baskets["end_date"]=baskets["end_date"].astype(object)
                baskets.loc[0,"end_date"]=value
                with self.assertRaisesRegex(ValueError,"end_date"):
                    aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs(),baskets)

    def test_nonoverlapping_replacement_keeps_original_known_date_boundary(self):
        baskets=_basket_mapping();baskets.loc[0,"end_date"]="2024-01-02"
        replacement=baskets.iloc[:1].copy();replacement["known_date"]="2024-01-03"
        replacement["end_date"]=pd.NaT
        baskets=pd.concat([baskets,replacement],ignore_index=True)
        result=aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs(),baskets)
        self.assertEqual(result["constituent_count"].tolist(),[1,2])
        self.assertEqual(result["basket_weight_sum"].tolist(),[0.6,1.0])

    def test_flow_total_overflow_and_nullable_missing_weight_are_rejected(self):
        inputs=_moneyflow_inputs()
        for column in [c for c in inputs.columns if c.startswith(("buy_","sell_"))]:
            inputs.loc[3,column]=1e308
        with self.assertRaisesRegex(ValueError,"invalid active constituent moneyflow"):
            aggregate_etf_moneyflow_basket_inputs(inputs,_basket_mapping())
        baskets=_basket_mapping();baskets["weight"]=pd.Series([0.6,pd.NA],dtype="Float64")
        with self.assertRaisesRegex(ValueError,"finite positive.*weight"):
            aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs(),baskets)

    def test_no_active_scope_is_empty_but_does_not_certify_missing_market_days(self):
        baskets=_basket_mapping();baskets["known_date"]="2025-01-01"
        self.assertTrue(aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs(),baskets).empty)
        self.assertTrue(aggregate_etf_moneyflow_basket_inputs(_moneyflow_inputs().iloc[:0],baskets).empty)

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
