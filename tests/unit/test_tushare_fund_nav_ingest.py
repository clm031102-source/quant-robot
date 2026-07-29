import unittest

import pandas as pd

from quant_robot.data.ingest.tushare_fund_nav import (
    CANONICAL_COLUMNS,
    build_tushare_fund_nav_request_plan,
    canonicalize_tushare_fund_nav,
)


class TushareFundNavIngestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sessions = pd.to_datetime(
            [
                "2020-01-02",
                "2020-01-03",
                "2020-01-06",
                "2020-01-07",
                "2020-01-08",
            ]
        )

    def test_build_request_plan_clips_each_asset_to_its_lifetime(self):
        universe = pd.DataFrame(
            {
                "etf_code": ["510300.SH", "159901.SZ", "510999.SH"],
                "market_exchange": ["SSE", "SZSE", "SSE"],
                "list_date": ["2012-05-28", "2004-12-10", "2025-01-01"],
                "delist_date": [None, "2021-06-30", None],
            }
        )

        result = build_tushare_fund_nav_request_plan(
            universe,
            start_date="2020-01-02",
            end_date="2024-06-28",
        )

        self.assertEqual(result["symbol"].tolist(), ["159901.SZ", "510300.SH"])
        by_symbol = result.set_index("symbol")
        self.assertEqual(str(by_symbol.loc["159901.SZ", "request_end"]), "2021-06-30")
        self.assertEqual(str(by_symbol.loc["510300.SH", "request_start"]), "2020-01-02")
        self.assertEqual(by_symbol.loc["510300.SH", "asset_id"], "CN_ETF_XSHG_510300")

    def test_build_request_plan_rejects_invalid_exchange_suffix(self):
        universe = pd.DataFrame(
            {
                "etf_code": ["510300.SZ"],
                "market_exchange": ["SSE"],
                "list_date": ["2012-05-28"],
                "delist_date": [None],
            }
        )

        with self.assertRaisesRegex(ValueError, "exchange"):
            build_tushare_fund_nav_request_plan(
                universe,
                start_date="2020-01-02",
                end_date="2024-06-28",
            )

    def test_canonicalize_prefers_latest_announced_revision(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH", "510300.SH"],
                "nav_date": ["2020-01-02", "2020-01-02"],
                "ann_date": ["2020-01-03", "2020-01-06"],
                "unit_nav": [4.0, 4.1],
                "update_flag": [0.0, 1.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result.loc[0, "unit_nav"], 4.1)
        self.assertEqual(str(result.loc[0, "known_from"]), "2020-01-07")
        self.assertTrue(bool(result.loc[0, "is_pit_usable"]))

    def test_canonicalize_prefers_higher_update_flag_on_same_announcement(self):
        raw = pd.DataFrame(
            {
                "symbol": ["159901.SZ", "159901.SZ"],
                "nav_date": ["2020-01-02", "2020-01-02"],
                "ann_date": ["2020-01-03", "2020-01-03"],
                "unit_nav": [1.0, 1.01],
                "update_flag": [0.0, 1.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertAlmostEqual(result.loc[0, "unit_nav"], 1.01)

    def test_canonicalize_rejects_unresolved_value_conflict(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH", "510300.SH"],
                "nav_date": ["2020-01-02", "2020-01-02"],
                "ann_date": ["2020-01-03", "2020-01-03"],
                "unit_nav": [4.0, 4.1],
                "update_flag": [1.0, 1.0],
            }
        )

        with self.assertRaisesRegex(ValueError, "conflicting"):
            canonicalize_tushare_fund_nav(raw, self.sessions)

    def test_canonicalize_uses_first_official_session_strictly_after_both_dates(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH"],
                "nav_date": ["2020-01-02"],
                "ann_date": ["2020-01-03"],
                "unit_nav": [4.0],
                "update_flag": [0.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertEqual(str(result.loc[0, "known_from"]), "2020-01-06")

    def test_canonicalize_keeps_invalid_announcement_lag_as_unusable(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH"],
                "nav_date": ["2020-01-03"],
                "ann_date": ["2020-01-02"],
                "unit_nav": [4.0],
                "update_flag": [0.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertTrue(pd.isna(result.loc[0, "known_from"]))
        self.assertFalse(bool(result.loc[0, "is_pit_usable"]))

    def test_canonicalize_does_not_guess_when_no_later_session_exists(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH"],
                "nav_date": ["2020-01-08"],
                "ann_date": ["2020-01-08"],
                "unit_nav": [4.0],
                "update_flag": [0.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertTrue(pd.isna(result.loc[0, "known_from"]))
        self.assertFalse(bool(result.loc[0, "is_pit_usable"]))

    def test_canonicalize_has_only_source_fields(self):
        raw = pd.DataFrame(
            {
                "symbol": ["510300.SH"],
                "nav_date": ["2020-01-02"],
                "ann_date": ["2020-01-03"],
                "unit_nav": [4.0],
            }
        )

        result = canonicalize_tushare_fund_nav(raw, self.sessions)

        self.assertEqual(list(result.columns), CANONICAL_COLUMNS)
        forbidden_tokens = ("return", "label", "signal", "score", "rank", "portfolio")
        self.assertFalse(any(token in column for column in result.columns for token in forbidden_tokens))


if __name__ == "__main__":
    unittest.main()
