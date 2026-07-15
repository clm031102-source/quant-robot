import unittest

import pandas as pd

from quant_robot.data.asset_session_integrity import classify_asset_sessions


class AssetSessionIntegrityTests(unittest.TestCase):
    def test_classifies_daily_and_legacy_suspensions_with_daily_precedence(self):
        bars = _bars(
            "CN_XSHE_000001",
            "000001.SZ",
            "XSHE",
            ["2024-01-02", "2024-01-05"],
        )
        stock_basic = _stock_basic("CN_XSHE_000001", "000001.SZ", "2020-01-01")
        daily = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "date": ["2024-01-03"],
                "source": ["tushare_suspend_d"],
            }
        )
        legacy = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "symbol": ["000001.SZ"],
                "suspend_date": ["2024-01-03"],
                "resume_date": ["2024-01-05"],
                "source": ["tushare_suspend"],
            }
        )

        result = classify_asset_sessions(
            bars=bars,
            expected_sessions=_sessions("2024-01-02", "2024-01-05"),
            stock_basic=stock_basic,
            daily_suspension=daily,
            legacy_suspension=legacy,
        )

        rows = result.gaps.set_index("missing_date")
        self.assertEqual(rows.loc["2024-01-03", "classification"], "official_daily_suspension")
        self.assertEqual(rows.loc["2024-01-04", "classification"], "official_legacy_suspension")
        self.assertEqual(result.summary["raw_gap_rows"], 2)
        self.assertEqual(result.summary["unresolved_active_session_rows"], 0)

    def test_legacy_resume_date_is_not_classified_as_suspended(self):
        bars = _bars(
            "CN_XSHE_000001",
            "000001.SZ",
            "XSHE",
            ["2024-01-02", "2024-01-05"],
        )
        legacy = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "suspend_date": ["2024-01-03"],
                "resume_date": ["2024-01-04"],
            }
        )

        result = classify_asset_sessions(
            bars=bars,
            expected_sessions=_sessions("2024-01-02", "2024-01-05"),
            stock_basic=_stock_basic("CN_XSHE_000001", "000001.SZ", "2020-01-01"),
            legacy_suspension=legacy,
        )

        rows = result.gaps.set_index("missing_date")
        self.assertEqual(rows.loc["2024-01-03", "classification"], "official_legacy_suspension")
        self.assertEqual(rows.loc["2024-01-04", "classification"], "unresolved_active_session")

    def test_legacy_19000101_resume_date_is_open_ended(self):
        bars = _bars(
            "CN_XSHE_000001",
            "000001.SZ",
            "XSHE",
            ["2024-01-02", "2024-01-05"],
        )
        legacy = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001"],
                "suspend_date": ["2024-01-03"],
                "resume_date": ["19000101"],
            }
        )

        result = classify_asset_sessions(
            bars=bars,
            expected_sessions=_sessions("2024-01-02", "2024-01-05"),
            stock_basic=_stock_basic("CN_XSHE_000001", "000001.SZ", "2020-01-01"),
            legacy_suspension=legacy,
        )

        self.assertEqual(
            set(result.gaps["classification"]),
            {"official_legacy_suspension"},
        )

    def test_reports_prelisting_gap_and_observed_exchange_transition_bar(self):
        bars = _bars(
            "CN_XBEI_920001",
            "920001.BJ",
            "XBEI",
            ["2024-01-02", "2024-01-04", "2024-01-05"],
        )

        result = classify_asset_sessions(
            bars=bars,
            expected_sessions=_sessions("2024-01-02", "2024-01-05"),
            stock_basic=_stock_basic("CN_XBEI_920001", "920001.BJ", "2024-01-04"),
        )

        self.assertEqual(result.gaps.loc[0, "classification"], "before_official_list_date")
        self.assertEqual(result.gaps.loc[0, "missing_date"], "2024-01-03")
        self.assertEqual(len(result.observed_outside_lifecycle), 1)
        outside = result.observed_outside_lifecycle.iloc[0]
        self.assertEqual(outside["date"], "2024-01-02")
        self.assertEqual(outside["reason"], "exchange_transition_prelisting")

    def test_classifies_post_delist_gaps_and_observed_rows(self):
        bars = _bars(
            "CN_XSHG_600001",
            "600001.SH",
            "XSHG",
            ["2024-01-02", "2024-01-05"],
        )

        result = classify_asset_sessions(
            bars=bars,
            expected_sessions=_sessions("2024-01-02", "2024-01-05"),
            stock_basic=_stock_basic(
                "CN_XSHG_600001",
                "600001.SH",
                "2020-01-01",
                delist_date="2024-01-03",
            ),
        )

        rows = result.gaps.set_index("missing_date")
        self.assertEqual(rows.loc["2024-01-03", "classification"], "unresolved_active_session")
        self.assertEqual(rows.loc["2024-01-04", "classification"], "after_official_delist_date")
        self.assertEqual(result.observed_outside_lifecycle.loc[0, "reason"], "after_official_delist_date")

    def test_missing_stock_basic_is_fail_closed(self):
        bars = _bars(
            "CN_XSHE_000022",
            "000022.SZ",
            "XSHE",
            ["2024-01-02", "2024-01-04"],
        )

        result = classify_asset_sessions(
            bars=bars,
            expected_sessions=_sessions("2024-01-02", "2024-01-04"),
            stock_basic=pd.DataFrame(columns=["asset_id", "symbol", "list_date", "delist_date"]),
        )

        self.assertEqual(result.gaps.loc[0, "classification"], "missing_lifecycle_metadata")
        self.assertEqual(result.summary["missing_lifecycle_metadata_assets"], 1)

    def test_rejects_duplicate_evidence_keys(self):
        bars = _bars(
            "CN_XSHE_000001",
            "000001.SZ",
            "XSHE",
            ["2024-01-02", "2024-01-04"],
        )
        stock_basic = pd.concat(
            [
                _stock_basic("CN_XSHE_000001", "000001.SZ", "2020-01-01"),
                _stock_basic("CN_XSHE_000001", "000001.SZ", "2020-01-01"),
            ],
            ignore_index=True,
        )

        with self.assertRaisesRegex(ValueError, "duplicate asset_id"):
            classify_asset_sessions(
                bars=bars,
                expected_sessions=_sessions("2024-01-02", "2024-01-04"),
                stock_basic=stock_basic,
            )

        daily = pd.DataFrame(
            {
                "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
                "date": ["2024-01-03", "2024-01-03"],
            }
        )
        with self.assertRaisesRegex(ValueError, "duplicate asset-session"):
            classify_asset_sessions(
                bars=bars,
                expected_sessions=_sessions("2024-01-02", "2024-01-04"),
                stock_basic=_stock_basic("CN_XSHE_000001", "000001.SZ", "2020-01-01"),
                daily_suspension=daily,
            )


def _bars(asset_id: str, symbol: str, exchange: str, dates: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": [asset_id] * len(dates),
            "symbol": [symbol] * len(dates),
            "exchange": [exchange] * len(dates),
            "market": ["CN"] * len(dates),
            "date": dates,
        }
    )


def _sessions(start: str, end: str) -> pd.DataFrame:
    return pd.DataFrame({"date": pd.date_range(start, end, freq="B")})


def _stock_basic(
    asset_id: str,
    symbol: str,
    list_date: str,
    *,
    delist_date: str | None = None,
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": [asset_id],
            "symbol": [symbol],
            "list_date": [list_date],
            "delist_date": [delist_date],
        }
    )


if __name__ == "__main__":
    unittest.main()
