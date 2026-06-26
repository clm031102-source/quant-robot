import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.external_feed_margin_credit_prescreen import (
    build_external_feed_margin_credit_prescreen,
    compute_external_feed_margin_credit_factors,
    write_external_feed_margin_credit_prescreen,
)
from tests.unit.test_external_feed_northbound_prescreen import _synthetic_bars


class ExternalFeedMarginCreditPrescreenTests(unittest.TestCase):
    def test_compute_factors_uses_available_date_and_excludes_same_day_raw_observation(self) -> None:
        bars = _synthetic_bars(days=36, assets=7, start="2024-01-02")
        margin = _synthetic_margin_detail(bars, raw_dates=pd.bdate_range("2024-01-02", periods=30))

        factors = compute_external_feed_margin_credit_factors(
            bars=bars,
            margin_detail=margin,
            lookback=5,
            min_signal_date_amount=1_000_000,
        )

        self.assertEqual(
            set(factors["factor_name"]),
            {"margin_financing_acceleration_exhaustion_20", "margin_balance_crowding_reversal_20"},
        )
        self.assertTrue((pd.to_datetime(factors["raw_date"]) < pd.to_datetime(factors["date"])).all())
        self.assertTrue((pd.to_datetime(factors["available_date"]) <= pd.to_datetime(factors["date"])).all())
        self.assertGreater(factors["date"].nunique(), 0)
        self.assertGreater(factors["asset_id"].nunique(), 0)

    def test_build_prescreen_blocks_final_holdout_and_promotion(self) -> None:
        bars = _synthetic_bars(days=48, assets=8, start="2025-11-03", include_holdout=True)
        margin = _synthetic_margin_detail(bars, raw_dates=pd.bdate_range("2025-11-03", periods=42))

        result = build_external_feed_margin_credit_prescreen(
            bars=bars,
            margin_detail=margin,
            analysis_start_date="2025-11-01",
            analysis_end_date="2025-12-31",
            include_final_holdout=False,
            horizons=(1,),
            execution_lag=0,
            lookback=5,
            min_cross_section=6,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
        )

        self.assertEqual(result["stage"], "external_feed_margin_credit_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 2)
        self.assertEqual(result["summary"]["test_count"], 2)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertIn("prescreen_is_not_portfolio_evidence", result["promotion_policy"]["blockers"])

    def test_writer_emits_json_markdown_results_and_ic_observations(self) -> None:
        bars = _synthetic_bars(days=36, assets=7, start="2024-01-02")
        result = build_external_feed_margin_credit_prescreen(
            bars=bars,
            margin_detail=_synthetic_margin_detail(bars, raw_dates=pd.bdate_range("2024-01-02", periods=30)),
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-12-31",
            horizons=(1,),
            execution_lag=0,
            lookback=5,
            min_cross_section=6,
            min_ic_observations=4,
            min_signal_date_amount=1_000_000,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_external_feed_margin_credit_prescreen(output, result)

            self.assertTrue((output / "external_feed_margin_credit_prescreen.json").exists())
            self.assertTrue((output / "external_feed_margin_credit_prescreen.md").exists())
            self.assertTrue((output / "external_feed_margin_credit_prescreen_results.csv").exists())
            self.assertTrue((output / "external_feed_margin_credit_prescreen_ic_observations.csv").exists())


def _synthetic_margin_detail(bars: pd.DataFrame, *, raw_dates: pd.DatetimeIndex) -> pd.DataFrame:
    symbols = bars[["asset_id", "symbol"]].drop_duplicates().sort_values("asset_id")
    rows = []
    for date_idx, raw_date in enumerate(raw_dates):
        for asset_idx, row in enumerate(symbols.itertuples(index=False)):
            crowding = 1.0 + (asset_idx % 4) * 0.02 + date_idx * (asset_idx + 1) * 0.001
            financing_buy = 100_000.0 + asset_idx * 5_000.0 + date_idx * (asset_idx + 1) * 1_000.0
            rows.append(
                {
                    "date": raw_date.date(),
                    "available_date": (raw_date + pd.offsets.BDay(1)).date(),
                    "asset_id": row.asset_id,
                    "symbol": row.symbol,
                    "market": "CN",
                    "rzye": 10_000_000.0 * crowding,
                    "rzmre": financing_buy,
                    "rqye": 100_000.0 + asset_idx,
                    "rzrqye": 10_100_000.0 * crowding,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
