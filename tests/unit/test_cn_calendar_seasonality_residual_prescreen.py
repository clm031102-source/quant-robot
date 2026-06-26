import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_calendar_seasonality_preregistration import (
    build_cn_calendar_seasonality_preregistration,
)
from quant_robot.ops.cn_calendar_seasonality_residual_prescreen import (
    NEXT_DIRECTION_WITH_LEADS,
    NEXT_DIRECTION_WITHOUT_LEADS,
    build_cn_calendar_seasonality_feature_frame,
    summarize_cn_calendar_seasonality_residual_prescreen_from_features,
    write_cn_calendar_seasonality_residual_prescreen,
)


def _calendar_bars(days: int = 170, assets: int = 36) -> pd.DataFrame:
    dates = pd.bdate_range("2020-01-02", periods=days)
    dates = dates[~((dates >= pd.Timestamp("2020-02-03")) & (dates <= pd.Timestamp("2020-02-07")))]
    rows = []
    for asset_idx in range(assets):
        asset_id = f"CN_CAL_{asset_idx:03d}"
        price = 10.0 + asset_idx * 0.05
        for day_idx, dt in enumerate(dates):
            drift = 0.0003 * (asset_idx % 9) + 0.001 * ((day_idx % 13) - 6)
            open_price = max(1.0, price * (1.0 + drift * 0.25))
            close = max(1.0, open_price * (1.0 + drift))
            high = max(open_price, close) * 1.012
            low = min(open_price, close) * 0.988
            volume = 900_000 + asset_idx * 11_000 + (day_idx % 7) * 3_000
            amount = volume * close
            rows.append(
                {
                    "date": dt,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "adj_close": close,
                    "volume": volume,
                    "amount": amount,
                    "vwap": amount / volume,
                }
            )
            price = close
    return pd.DataFrame(rows)


def _stock_basic(assets: int = 36) -> pd.DataFrame:
    rows = []
    industries = ("bank", "tech", "industrial")
    for asset_idx in range(assets):
        rows.append(
            {
                "asset_id": f"CN_CAL_{asset_idx:03d}",
                "symbol": f"{asset_idx:06d}.SZ",
                "industry": industries[asset_idx % len(industries)],
                "list_date": "20100101",
            }
        )
    return pd.DataFrame(rows)


class CNCalendarSeasonalityResidualPrescreenTests(unittest.TestCase):
    def test_feature_frame_builds_ex_ante_calendar_states(self) -> None:
        features = build_cn_calendar_seasonality_feature_frame(
            _calendar_bars(days=90, assets=6),
            horizons=(5,),
            execution_lag=1,
        )

        calendar = features.drop_duplicates("date").set_index("date").sort_index()

        self.assertTrue(calendar.loc[pd.Timestamp("2020-01-31"), "ex_ante_pre_holiday_1_to_3_trading_days"])
        self.assertTrue(calendar.loc[pd.Timestamp("2020-02-10"), "ex_ante_first_3_sessions_after_holiday"])
        self.assertTrue(calendar.loc[pd.Timestamp("2020-02-03") : pd.Timestamp("2020-02-07")].empty)
        self.assertTrue(calendar.loc[pd.Timestamp("2020-01-06"), "ex_ante_weekday_monday"])
        self.assertTrue(calendar.loc[pd.Timestamp("2020-01-02"), "ex_ante_turn_of_month_window"])

    def test_residual_prescreen_evaluates_all_calendar_candidates_without_promotion(self) -> None:
        bars = _calendar_bars()
        features = build_cn_calendar_seasonality_feature_frame(bars, horizons=(5,), execution_lag=1)
        prereg = build_cn_calendar_seasonality_preregistration()

        result = summarize_cn_calendar_seasonality_residual_prescreen_from_features(
            features,
            stock_basic=_stock_basic(),
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            sample_every_n_dates=5,
            min_cross_section=18,
            min_ic_observations=4,
            min_signal_date_amount=0,
            min_industries=2,
            min_assets_per_industry=2,
            min_calendar_dates=3,
        )

        self.assertEqual(result["stage"], "cn_calendar_seasonality_residual_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 8)
        self.assertEqual(result["summary"]["test_count"], 8)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["industry_neutral_rows"], 0)
        self.assertGreater(result["summary"]["residual_rows"], 0)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertEqual(result["summary"]["portfolio_grid_allowed_candidates"], 0)
        self.assertEqual(result["multiple_testing_policy"]["round163_candidate_count"], 8)
        self.assertIn(result["summary"]["next_direction"], {NEXT_DIRECTION_WITH_LEADS, NEXT_DIRECTION_WITHOUT_LEADS})
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertEqual(len(result["calendar_coverage"]), 8)
        for row in result["results"]:
            self.assertIn("raw_mean_spearman_ic", row)
            self.assertIn("industry_neutral_mean_spearman_ic", row)
            self.assertIn("residual_mean_spearman_ic", row)
            self.assertIn("calendar_coverage_ok", row)
            self.assertFalse(row["promotion_allowed"])
            self.assertFalse(row["portfolio_grid_allowed"])

    def test_high_residual_threshold_blocks_and_rotates(self) -> None:
        bars = _calendar_bars(days=120, assets=30)
        features = build_cn_calendar_seasonality_feature_frame(bars, horizons=(5,), execution_lag=1)
        prereg = build_cn_calendar_seasonality_preregistration()

        result = summarize_cn_calendar_seasonality_residual_prescreen_from_features(
            features,
            stock_basic=_stock_basic(30),
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            sample_every_n_dates=5,
            min_cross_section=15,
            min_ic_observations=4,
            min_signal_date_amount=0,
            min_industries=2,
            min_assets_per_industry=2,
            min_calendar_dates=3,
            min_residual_mean_ic=0.99,
            min_residual_icir=99.0,
        )

        self.assertEqual(result["summary"]["residual_research_lead_count"], 0)
        self.assertEqual(result["summary"]["next_direction"], NEXT_DIRECTION_WITHOUT_LEADS)
        self.assertTrue(
            all("residual_mean_ic_below_threshold" in row["blockers"] for row in result["results"])
        )

    def test_write_outputs(self) -> None:
        bars = _calendar_bars(days=100, assets=30)
        features = build_cn_calendar_seasonality_feature_frame(bars, horizons=(5,), execution_lag=1)
        prereg = build_cn_calendar_seasonality_preregistration()
        result = summarize_cn_calendar_seasonality_residual_prescreen_from_features(
            features,
            stock_basic=_stock_basic(30),
            candidate_specs=prereg["candidates"],
            horizons=(5,),
            sample_every_n_dates=5,
            min_cross_section=15,
            min_ic_observations=4,
            min_signal_date_amount=0,
            min_industries=2,
            min_assets_per_industry=2,
            min_calendar_dates=3,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_cn_calendar_seasonality_residual_prescreen(output, result)
            self.assertTrue((output / "cn_calendar_seasonality_residual_prescreen.json").exists())
            self.assertTrue((output / "cn_calendar_seasonality_residual_prescreen.md").exists())
            self.assertTrue((output / "cn_calendar_seasonality_residual_prescreen_results.csv").exists())
            self.assertTrue((output / "cn_calendar_seasonality_calendar_coverage.csv").exists())


if __name__ == "__main__":
    unittest.main()
