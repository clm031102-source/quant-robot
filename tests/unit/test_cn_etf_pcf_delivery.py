import unittest

import pandas as pd

from quant_robot.ops.cn_etf_pcf_delivery import (
    CANONICAL_COLUMNS,
    audit_cn_etf_pcf_delivery,
    normalize_cn_etf_pcf_delivery,
)


class CnEtfPcfDeliveryTests(unittest.TestCase):
    def test_normalizes_sse_and_preserves_pre_open_next_session_boundary(self):
        frame = pd.DataFrame(
            {
                "trade_date": ["20240102"],
                "ts_code": ["510050.SH"],
                "con_code": ["600000.SH"],
                "con_name": ["Pudong Bank"],
                "qty": [1000],
                "sub_flag": ["allowed"],
                "cpr": [10.0],
                "rdr": [0.0],
                "sca": [12345.0],
                "exchange": ["SH"],
            }
        )

        result = normalize_cn_etf_pcf_delivery(
            frame,
            market_exchange="SSE",
            source_provider="vendor",
            source_file="sse.csv",
        )

        self.assertEqual(list(result.columns), list(CANONICAL_COLUMNS))
        self.assertEqual(result.loc[0, "etf_code"], "510050.SH")
        self.assertEqual(result.loc[0, "cash_substitution_amount_cny"], 12345.0)
        self.assertEqual(result.loc[0, "available_date"], result.loc[0, "trade_date"])
        self.assertEqual(result.loc[0, "earliest_research_use_session_offset"], 1)
        self.assertFalse(result.loc[0, "same_session_factor_use_allowed"])

    def test_normalizes_szse_directional_cash_amounts(self):
        frame = pd.DataFrame(
            {
                "trade_date": ["20240102"],
                "ts_code": ["159919.SZ"],
                "con_code": ["000001.SZ"],
                "qty": [1000],
                "sub_flag": ["allowed"],
                "cpr": [10.0],
                "rdr": [0.0],
                "sub_cc": [123.0],
                "red_cc": [45.0],
                "exchange": ["SZ"],
            }
        )

        result = normalize_cn_etf_pcf_delivery(
            frame,
            market_exchange="SZSE",
            source_provider="vendor",
            source_file="szse.csv",
        )

        self.assertEqual(result.loc[0, "subscription_cash_amount_cny"], 123.0)
        self.assertEqual(result.loc[0, "redemption_cash_amount_cny"], 45.0)
        self.assertTrue(pd.isna(result.loc[0, "cash_substitution_amount_cny"]))

    def test_rejects_duplicate_keys_and_invalid_quantity(self):
        duplicate = _minimal_frame()
        duplicate = pd.concat([duplicate, duplicate], ignore_index=True)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            normalize_cn_etf_pcf_delivery(
                duplicate,
                market_exchange="SSE",
                source_provider="vendor",
                source_file="duplicate.csv",
            )

        negative = _minimal_frame()
        negative.loc[0, "qty"] = -1
        with self.assertRaisesRegex(ValueError, "quantity"):
            normalize_cn_etf_pcf_delivery(
                negative,
                market_exchange="SSE",
                source_provider="vendor",
                source_file="negative.csv",
            )

        infinite = _minimal_frame()
        infinite["qty"] = infinite["qty"].astype(float)
        infinite.loc[0, "qty"] = float("inf")
        with self.assertRaisesRegex(ValueError, "finite"):
            normalize_cn_etf_pcf_delivery(
                infinite,
                market_exchange="SSE",
                source_provider="vendor",
                source_file="infinite.csv",
            )

    def test_audit_is_source_review_only_and_flags_date_bounds(self):
        normalized = normalize_cn_etf_pcf_delivery(
            _minimal_frame(),
            market_exchange="SSE",
            source_provider="vendor",
            source_file="sse.csv",
        )
        result = audit_cn_etf_pcf_delivery(
            normalized,
            analysis_start="2020-01-02",
            analysis_end="2023-12-31",
        )

        self.assertEqual(result["status"], "blocked_delivery_outside_frozen_window")
        self.assertFalse(result["decision"]["source_ready"])
        self.assertFalse(result["decision"]["factor_generation_allowed"])


def _minimal_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "trade_date": ["20240102"],
            "ts_code": ["510050.SH"],
            "con_code": ["600000.SH"],
            "qty": [1000],
            "sub_flag": ["allowed"],
            "cpr": [10.0],
            "rdr": [0.0],
            "sca": [12345.0],
            "exchange": ["SH"],
        }
    )


if __name__ == "__main__":
    unittest.main()
