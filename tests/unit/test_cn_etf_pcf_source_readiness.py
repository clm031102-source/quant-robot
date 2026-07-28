import unittest

import pandas as pd

from quant_robot.ops.cn_etf_pcf_delivery import (
    audit_cn_etf_pcf_history,
    normalize_cn_etf_pcf_delivery,
    normalize_cn_etf_pcf_target_universe,
)


class CnEtfPcfSourceReadinessTests(unittest.TestCase):
    def test_complete_cross_exchange_history_is_ready_for_preregistration(self):
        result = audit_cn_etf_pcf_history(
            _pcf(),
            target_universe=_target_universe(),
            trading_sessions=["2024-01-02", "2024-01-03"],
            analysis_start="2024-01-02",
            analysis_end="2024-01-03",
            final_holdout_start="2026-01-01",
            minimum_target_etfs=2,
        )

        self.assertEqual(result["status"], "ready_for_pcf_source_preregistration")
        self.assertTrue(result["gate"]["cleared"])
        self.assertTrue(result["decision"]["source_ready"])
        self.assertEqual(result["summary"]["expected_etf_sessions"], 4)
        self.assertEqual(result["summary"]["observed_etf_sessions"], 4)
        self.assertEqual(result["summary"]["coverage_ratio"], 1.0)
        self.assertFalse(result["decision"]["factor_generation_allowed"])
        self.assertFalse(result["decision"]["forward_return_read_allowed"])

    def test_missing_basket_blocks_and_is_reported_by_etf_and_date(self):
        pcf = _pcf()
        pcf = pcf[
            ~(
                pcf["etf_code"].eq("159919.SZ")
                & pcf["trade_date"].eq(pd.Timestamp("2024-01-03"))
            )
        ].reset_index(drop=True)

        result = audit_cn_etf_pcf_history(
            pcf,
            target_universe=_target_universe(),
            trading_sessions=["2024-01-02", "2024-01-03"],
            analysis_start="2024-01-02",
            analysis_end="2024-01-03",
            final_holdout_start="2026-01-01",
            minimum_target_etfs=2,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("missing_target_etf_sessions", result["gate"]["blockers"])
        self.assertEqual(result["summary"]["missing_etf_sessions"], 1)
        sz = next(
            row
            for row in result["etf_coverage"]
            if row["etf_code"] == "159919.SZ"
        )
        self.assertEqual(sz["coverage_ratio"], 0.5)
        last_date = next(
            row for row in result["date_coverage"] if row["date"] == "2024-01-03"
        )
        self.assertEqual(last_date["coverage_ratio"], 0.5)

    def test_duplicate_and_point_in_time_violations_block(self):
        pcf = _pcf()
        pcf.loc[0, "available_date"] = pd.Timestamp("2024-01-03")
        pcf.loc[0, "same_session_factor_use_allowed"] = True
        pcf = pd.concat([pcf, pcf.iloc[[1]]], ignore_index=True)

        result = audit_cn_etf_pcf_history(
            pcf,
            target_universe=_target_universe(),
            trading_sessions=["2024-01-02", "2024-01-03"],
            analysis_start="2024-01-02",
            analysis_end="2024-01-03",
            final_holdout_start="2026-01-01",
            minimum_target_etfs=2,
        )

        self.assertIn("duplicate_pcf_keys", result["gate"]["blockers"])
        self.assertIn("point_in_time_contract_mismatch", result["gate"]["blockers"])
        self.assertFalse(result["decision"]["source_ready"])

    def test_target_universe_normalizes_fund_basic_aliases_and_filters_non_etfs(self):
        frame = pd.DataFrame(
            {
                "symbol": ["510050.SH", "159919.SZ", "160000.SZ"],
                "list_date": ["20041230", "20121225", "20100101"],
                "delist_date": [None, None, None],
                "is_etf": [True, True, False],
            }
        )

        result = normalize_cn_etf_pcf_target_universe(frame)

        self.assertEqual(result["etf_code"].tolist(), ["159919.SZ", "510050.SH"])
        self.assertEqual(result["market_exchange"].tolist(), ["SZSE", "SSE"])


def _pcf() -> pd.DataFrame:
    frames = []
    for date in ("20240102", "20240103"):
        frames.append(
            normalize_cn_etf_pcf_delivery(
                pd.DataFrame(
                    {
                        "trade_date": [date],
                        "ts_code": ["510050.SH"],
                        "con_code": ["600000.SH"],
                        "qty": [1000],
                        "sub_flag": ["allowed"],
                        "cpr": [10.0],
                        "rdr": [0.0],
                        "sca": [12345.0],
                        "exchange": ["SH"],
                    }
                ),
                market_exchange="SSE",
                source_provider="vendor",
                source_file="sse.csv",
            )
        )
        frames.append(
            normalize_cn_etf_pcf_delivery(
                pd.DataFrame(
                    {
                        "trade_date": [date],
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
                ),
                market_exchange="SZSE",
                source_provider="vendor",
                source_file="szse.csv",
            )
        )
    return pd.concat(frames, ignore_index=True)


def _target_universe() -> pd.DataFrame:
    return normalize_cn_etf_pcf_target_universe(
        pd.DataFrame(
            {
                "etf_code": ["510050.SH", "159919.SZ"],
                "list_date": ["2004-12-30", "2012-12-25"],
                "delist_date": [None, None],
            }
        )
    )


if __name__ == "__main__":
    unittest.main()
