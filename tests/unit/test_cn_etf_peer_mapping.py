import unittest

import pandas as pd

from quant_robot.storage.cn_etf_peer_mapping import (
    CN_ETF_PEER_MAPPING_COLUMNS,
    build_cn_etf_peer_mapping_history,
    build_cn_etf_peer_mapping_history_from_fund_basic,
)


class CnEtfPeerMappingTests(unittest.TestCase):
    def test_official_snapshots_become_non_overlapping_as_known_intervals(self):
        snapshots = {
            "2026-07-16": _etf_basic("000300.SH"),
            "2026-08-01": _etf_basic("000905.SH"),
        }

        result = build_cn_etf_peer_mapping_history(snapshots)

        self.assertEqual(list(result.columns), CN_ETF_PEER_MAPPING_COLUMNS)
        self.assertEqual(len(result), 2)
        self.assertEqual(result.loc[0, "peer_id"], "000300.SH")
        self.assertEqual(str(result.loc[0, "known_from"]), "2026-07-16")
        self.assertEqual(str(result.loc[0, "valid_from"]), "2026-07-16")
        self.assertEqual(str(result.loc[0, "valid_to"]), "2026-07-31")
        self.assertEqual(result.loc[1, "peer_id"], "000905.SH")
        self.assertTrue(pd.isna(result.loc[1, "valid_to"]))
        self.assertEqual(set(result["mapping_method"]), {"official_index_code"})

    def test_snapshot_knowledge_date_never_backfills_to_listing_date(self):
        result = build_cn_etf_peer_mapping_history({"2026-07-16": _etf_basic("000300.SH")})

        self.assertEqual(str(result.loc[0, "list_date"]), "2012-05-28")
        self.assertEqual(str(result.loc[0, "valid_from"]), "2026-07-16")
        self.assertEqual(str(result.loc[0, "known_from"]), "2026-07-16")

    def test_missing_index_code_is_not_mapped(self):
        result = build_cn_etf_peer_mapping_history({"2026-07-16": _etf_basic("")})

        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), CN_ETF_PEER_MAPPING_COLUMNS)

    def test_assignment_withdrawn_before_future_listing_has_no_valid_interval(self):
        announced = _etf_basic("000300.SH")
        announced["list_date"] = pd.Timestamp("2026-08-10").date()
        withdrawn = pd.DataFrame(columns=announced.columns)

        result = build_cn_etf_peer_mapping_history(
            {
                "2026-07-16": announced,
                "2026-08-01": withdrawn,
            }
        )

        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), CN_ETF_PEER_MAPPING_COLUMNS)

    def test_official_benchmark_text_is_exact_matched_without_historical_backfill(self):
        fund_basic = pd.DataFrame(
            [
                {
                    "symbol": "510300.SH",
                    "name": "300ETF",
                    "benchmark": "沪深300指数收益率 × 100%",
                    "list_date": pd.Timestamp("2012-05-28").date(),
                    "is_etf": True,
                },
                {
                    "symbol": "159919.SZ",
                    "name": "300ETF",
                    "benchmark": "沪深300指数收益率×100%",
                    "list_date": pd.Timestamp("2012-05-28").date(),
                    "is_etf": True,
                },
            ]
        )

        result = build_cn_etf_peer_mapping_history_from_fund_basic({"2026-07-16": fund_basic})

        self.assertEqual(len(result), 2)
        self.assertEqual(result["peer_id"].nunique(), 1)
        self.assertEqual(set(result["mapping_method"]), {"official_benchmark_text"})
        self.assertEqual(set(result["known_from"].astype(str)), {"2026-07-16"})
        self.assertEqual(set(result["valid_from"].astype(str)), {"2026-07-16"})


def _etf_basic(index_code: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "symbol": "510300.SH",
                "name": "300ETF",
                "index_code": index_code,
                "index_name": "Index",
                "list_date": pd.Timestamp("2012-05-28").date(),
                "list_status": "L",
                "exchange": "SH",
            }
        ]
    )


if __name__ == "__main__":
    unittest.main()
