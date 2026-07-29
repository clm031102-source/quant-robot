from __future__ import annotations

import unittest

import pandas as pd

from quant_robot.factors.etf_delayed_nav_premium_innovation import (
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
    compute_etf_delayed_nav_premium_innovation,
)


class EtfDelayedNavPremiumInnovationTests(unittest.TestCase):
    def test_nav_is_unavailable_before_known_from(self):
        dates = pd.date_range("2024-01-02", periods=4, freq="B")
        bars = _bars(dates, closes=[2.0, 2.0, 2.0, 2.0])
        nav = pd.DataFrame(
            {
                "nav_date": [dates[0].date()],
                "ann_date": [dates[1].date()],
                "known_from": [dates[2].date()],
                "asset_id": ["CN_ETF_XSHG_510300"],
                "symbol": ["510300.SH"],
                "exchange": ["XSHG"],
                "unit_nav": [2.0],
                "accum_nav": [2.0],
                "total_netasset": [100.0],
                "update_flag": [1.0],
                "is_pit_usable": [True],
                "source": ["tushare_fund_nav"],
            }
        )

        result = compute_etf_delayed_nav_premium_innovation(
            bars,
            nav,
            eligible_keys=_eligible(bars),
            official_sessions=dates,
            premium_lookback=2,
            return_windows=(1, 2),
            volatility_window=2,
            adv_window=2,
        )

        diagnostics = result.diagnostics.set_index("date")
        self.assertTrue(pd.isna(diagnostics.loc[dates[1], "latest_unit_nav"]))
        self.assertEqual(diagnostics.loc[dates[2], "latest_unit_nav"], 2.0)
        self.assertEqual(diagnostics.loc[dates[2], "nav_date"], dates[0])

    def test_rolling_median_excludes_current_premium(self):
        dates = pd.date_range("2024-01-02", periods=4, freq="B")
        bars = _bars(dates, closes=[1.0, 1.0, 1.0, 1.10])
        nav = _constant_nav(dates, unit_nav=1.0)

        result = compute_etf_delayed_nav_premium_innovation(
            bars,
            nav,
            eligible_keys=_eligible(bars),
            official_sessions=dates,
            premium_lookback=2,
            return_windows=(1, 2),
            volatility_window=2,
            adv_window=2,
        )

        final = result.diagnostics.iloc[-1]
        self.assertAlmostEqual(final["nav_premium"], 0.10)
        self.assertAlmostEqual(final["prior_premium_median"], 0.0)
        self.assertAlmostEqual(final["premium_innovation"], 0.10)
        self.assertAlmostEqual(final["factor_value"], -0.10)

    def test_late_old_nav_cannot_replace_a_newer_available_nav(self):
        dates = pd.date_range("2024-01-02", periods=5, freq="B")
        bars = _bars(dates, closes=[1.0] * len(dates))
        nav = pd.DataFrame(
            {
                "nav_date": [dates[1].date(), dates[0].date()],
                "ann_date": [dates[1].date(), dates[3].date()],
                "known_from": [dates[2].date(), dates[4].date()],
                "asset_id": ["CN_ETF_XSHG_510300"] * 2,
                "symbol": ["510300.SH"] * 2,
                "exchange": ["XSHG"] * 2,
                "unit_nav": [1.1, 0.9],
                "accum_nav": [1.1, 0.9],
                "total_netasset": [100.0, 100.0],
                "update_flag": [1.0, 1.0],
                "is_pit_usable": [True, True],
                "source": ["tushare_fund_nav"] * 2,
            }
        )

        result = compute_etf_delayed_nav_premium_innovation(
            bars,
            nav,
            eligible_keys=_eligible(bars),
            official_sessions=dates,
            premium_lookback=2,
            return_windows=(1, 2),
            volatility_window=2,
            adv_window=2,
        )

        final = result.diagnostics.set_index("date").loc[dates[4]]
        self.assertEqual(final["nav_date"], dates[1])
        self.assertEqual(final["latest_unit_nav"], 1.1)

    def test_missing_official_session_prevents_compressed_lookback(self):
        dates = pd.date_range("2024-01-02", periods=5, freq="B")
        bars = _bars(dates, closes=[1.0] * len(dates))
        bars = bars[bars["date"] != dates[2].date()].reset_index(drop=True)
        nav = _constant_nav(dates, unit_nav=1.0)

        result = compute_etf_delayed_nav_premium_innovation(
            bars,
            nav,
            eligible_keys=_eligible(bars),
            official_sessions=dates,
            premium_lookback=2,
            return_windows=(1, 2),
            volatility_window=2,
            adv_window=2,
        )

        final = result.diagnostics.iloc[-1]
        self.assertTrue(pd.isna(final["factor_value"]))

    def test_outputs_one_candidate_and_frozen_direct_exposures(self):
        dates = pd.date_range("2024-01-02", periods=5, freq="B")
        bars = _bars(dates, closes=[1.0, 1.0, 1.0, 1.01, 1.02])
        nav = _constant_nav(dates, unit_nav=1.0)

        result = compute_etf_delayed_nav_premium_innovation(
            bars,
            nav,
            eligible_keys=_eligible(bars),
            official_sessions=dates,
            premium_lookback=2,
            return_windows=(1, 2),
            volatility_window=2,
            adv_window=2,
        )

        self.assertEqual(set(result.factors["factor_name"]), {FACTOR_NAME})
        self.assertEqual(
            set(result.direct_exposures["factor_name"]),
            set(DIRECT_EXPOSURE_NAMES),
        )
        self.assertFalse(
            any(
                token in column
                for column in result.diagnostics.columns
                for token in ("peer_name", "product_name", "theme_name")
            )
        )


def _bars(dates, closes):
    return pd.DataFrame(
        {
            "date": pd.to_datetime(dates).date,
            "asset_id": ["CN_ETF_XSHG_510300"] * len(dates),
            "market": ["CN_ETF"] * len(dates),
            "close": closes,
            "adj_close": closes,
            "amount": [1_000_000.0] * len(dates),
        }
    )


def _eligible(bars):
    return bars[["date", "asset_id", "market"]].copy()


def _constant_nav(dates, unit_nav):
    known_from = pd.to_datetime(dates)
    nav_dates = known_from - pd.offsets.BDay()
    return pd.DataFrame(
        {
            "nav_date": nav_dates.date,
            "ann_date": nav_dates.date,
            "known_from": known_from.date,
            "asset_id": ["CN_ETF_XSHG_510300"] * len(dates),
            "symbol": ["510300.SH"] * len(dates),
            "exchange": ["XSHG"] * len(dates),
            "unit_nav": [unit_nav] * len(dates),
            "accum_nav": [unit_nav] * len(dates),
            "total_netasset": [100.0] * len(dates),
            "update_flag": [1.0] * len(dates),
            "is_pit_usable": [True] * len(dates),
            "source": ["tushare_fund_nav"] * len(dates),
        }
    )


if __name__ == "__main__":
    unittest.main()
