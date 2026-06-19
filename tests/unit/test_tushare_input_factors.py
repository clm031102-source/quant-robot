import unittest

import pandas as pd

from quant_robot.factors.tushare_inputs import DAILY_BASIC_FACTOR_NAMES, compute_daily_basic_factors
from quant_robot.schema.factors import FACTOR_COLUMNS


class TushareInputFactorTests(unittest.TestCase):
    def test_daily_basic_factor_builder_emits_schema_columns(self):
        factors = compute_daily_basic_factors(_daily_basic_inputs())

        self.assertEqual(list(factors.columns), FACTOR_COLUMNS)
        self.assertEqual(set(factors["factor_name"]), set(DAILY_BASIC_FACTOR_NAMES))
        self.assertTrue((factors["lookback_window"] == 1).all())

    def test_daily_basic_factor_builder_computes_raw_inverse_and_log_factors(self):
        factors = compute_daily_basic_factors(_daily_basic_inputs())

        first = factors[factors["date"] == pd.Timestamp("2024-01-02").date()]
        values = dict(zip(first["factor_name"], first["factor_value"], strict=True))

        self.assertAlmostEqual(values["turnover_rate"], 1.0)
        self.assertAlmostEqual(values["turnover_rate_f"], 1.1)
        self.assertAlmostEqual(values["volume_ratio"], 0.9)
        self.assertAlmostEqual(values["turnover_rate_low"], -1.0)
        self.assertAlmostEqual(values["turnover_rate_f_low"], -1.1)
        self.assertAlmostEqual(values["volume_ratio_low"], -0.9)
        self.assertAlmostEqual(values["dv_ttm"], 3.0)
        self.assertAlmostEqual(values["pe_ttm_inverse"], 0.1)
        self.assertAlmostEqual(values["pb_inverse"], 0.5)
        self.assertAlmostEqual(values["ps_ttm_inverse"], 0.2)
        self.assertAlmostEqual(values["total_mv_log"], 11.512925464970229)
        self.assertAlmostEqual(values["circ_mv_log"], 10.819778284410283)

    def test_daily_basic_factor_builder_treats_invalid_denominators_as_missing(self):
        factors = compute_daily_basic_factors(_daily_basic_inputs())

        second = factors[factors["date"] == pd.Timestamp("2024-01-03").date()]
        values = dict(zip(second["factor_name"], second["factor_value"], strict=True))

        self.assertTrue(pd.isna(values["pe_ttm_inverse"]))
        self.assertTrue(pd.isna(values["pb_inverse"]))
        self.assertTrue(pd.isna(values["ps_ttm_inverse"]))
        self.assertTrue(pd.isna(values["total_mv_log"]))
        self.assertTrue(pd.isna(values["circ_mv_log"]))

    def test_daily_basic_factor_builder_normalizes_string_dates(self):
        inputs = _daily_basic_inputs()
        inputs["date"] = inputs["date"].astype(str)

        factors = compute_daily_basic_factors(inputs)

        self.assertEqual(set(type(value) for value in factors["date"]), {type(pd.Timestamp("2024-01-02").date())})

    def test_daily_basic_factor_builder_can_compute_only_requested_factor_names(self):
        factors = compute_daily_basic_factors(_daily_basic_inputs(), factor_names=("pb_inverse", "dv_ttm"))

        self.assertEqual(set(factors["factor_name"]), {"pb_inverse", "dv_ttm"})

    def test_daily_basic_factor_builder_computes_capacity_aware_composites(self):
        factors = compute_daily_basic_factors(
            _daily_basic_cross_section_inputs(),
            factor_names=(
                "turnover_rate_low_large_mv",
                "turnover_rate_f_low_large_mv",
                "dv_ttm_large_mv",
                "ps_ttm_inverse_large_mv",
            ),
        )

        for factor_name in (
            "turnover_rate_low_large_mv",
            "turnover_rate_f_low_large_mv",
            "dv_ttm_large_mv",
            "ps_ttm_inverse_large_mv",
        ):
            rows = factors[factors["factor_name"] == factor_name]
            scores = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))
            self.assertGreater(scores["CN_XSHE_000001"], scores["CN_XSHE_000002"])
            self.assertGreater(scores["CN_XSHE_000002"], scores["CN_XSHE_000003"])

    def test_daily_basic_factor_builder_computes_size_bucket_neutral_ranks(self):
        factors = compute_daily_basic_factors(
            _daily_basic_size_bucket_inputs(),
            factor_names=(
                "turnover_rate_low_mv_bucket_rank",
                "turnover_rate_f_low_mv_bucket_rank",
                "dv_ttm_mv_bucket_rank",
                "ps_ttm_inverse_mv_bucket_rank",
            ),
        )

        for factor_name in (
            "turnover_rate_low_mv_bucket_rank",
            "turnover_rate_f_low_mv_bucket_rank",
            "dv_ttm_mv_bucket_rank",
            "ps_ttm_inverse_mv_bucket_rank",
        ):
            rows = factors[factors["factor_name"] == factor_name]
            scores = dict(zip(rows["asset_id"], rows["factor_value"], strict=True))
            for bucket in range(5):
                winner = f"CN_TEST_WIN_{bucket}"
                loser = f"CN_TEST_LOSE_{bucket}"
                self.assertGreater(scores[winner], scores[loser])
            self.assertAlmostEqual(scores["CN_TEST_WIN_0"], scores["CN_TEST_WIN_4"])
            self.assertAlmostEqual(scores["CN_TEST_LOSE_0"], scores["CN_TEST_LOSE_4"])

    def test_daily_basic_factor_builder_rejects_unknown_requested_factor_names(self):
        with self.assertRaisesRegex(ValueError, "Unsupported daily-basic factor_names"):
            compute_daily_basic_factors(_daily_basic_inputs(), factor_names=("pb_inverse", "missing_daily_basic"))


def _daily_basic_inputs() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-02").date(), pd.Timestamp("2024-01-03").date()],
            "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
            "market": ["CN", "CN"],
            "turnover_rate": [1.0, 2.0],
            "turnover_rate_f": [1.1, 2.1],
            "volume_ratio": [0.9, 1.2],
            "pe_ttm": [10.0, 0.0],
            "pb": [2.0, -1.0],
            "ps_ttm": [5.0, 0.0],
            "dv_ttm": [3.0, 4.0],
            "total_mv": [100000.0, 0.0],
            "circ_mv": [50000.0, -1.0],
        }
    )


def _daily_basic_cross_section_inputs() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-01-02").date()] * 3,
            "asset_id": ["CN_XSHE_000001", "CN_XSHE_000002", "CN_XSHE_000003"],
            "market": ["CN", "CN", "CN"],
            "turnover_rate": [1.0, 3.0, 2.0],
            "turnover_rate_f": [1.1, 3.1, 2.1],
            "volume_ratio": [0.9, 1.2, 1.0],
            "pe_ttm": [10.0, 12.0, 11.0],
            "pb": [2.0, 2.5, 2.2],
            "ps_ttm": [5.0, 20.0, 10.0],
            "dv_ttm": [3.0, 1.0, 2.0],
            "total_mv": [100000.0, 1000000.0, 10000.0],
            "circ_mv": [100000.0, 1000000.0, 10000.0],
        }
    )


def _daily_basic_size_bucket_inputs() -> pd.DataFrame:
    rows = []
    for bucket in range(5):
        for side, signal_is_better in (("WIN", True), ("LOSE", False)):
            rows.append(
                {
                    "date": pd.Timestamp("2024-01-02").date(),
                    "asset_id": f"CN_TEST_{side}_{bucket}",
                    "market": "CN",
                    "turnover_rate": 1.0 if signal_is_better else 3.0,
                    "turnover_rate_f": 1.1 if signal_is_better else 3.1,
                    "volume_ratio": 1.0,
                    "pe_ttm": 10.0,
                    "pb": 2.0,
                    "ps_ttm": 5.0 if signal_is_better else 20.0,
                    "dv_ttm": 4.0 if signal_is_better else 1.0,
                    "total_mv": 10000.0 * (10 ** bucket) * (1.0 if signal_is_better else 1.1),
                    "circ_mv": 10000.0 * (10 ** bucket) * (1.0 if signal_is_better else 1.1),
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
