import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.external_feed_northbound_prescreen import (
    build_external_feed_northbound_prescreen,
    compute_external_feed_northbound_factors,
    write_external_feed_northbound_prescreen,
)


class ExternalFeedNorthboundPrescreenTests(unittest.TestCase):
    def test_compute_factors_uses_available_date_and_excludes_same_day_raw_observation(self) -> None:
        bars = _synthetic_bars(days=34, assets=6, start="2024-01-02")
        hk_hold = _synthetic_hk_hold(bars, raw_dates=pd.bdate_range("2024-01-02", periods=28))
        hsgt_flow = _synthetic_hsgt_flow(pd.bdate_range("2024-01-02", periods=28))

        factors = compute_external_feed_northbound_factors(
            bars=bars,
            hk_hold=hk_hold,
            hsgt_flow=hsgt_flow,
            lookback=5,
            min_signal_date_amount=1_000_000,
        )

        self.assertEqual(
            set(factors["factor_name"]),
            {
                "northbound_hold_ratio_accumulation_20",
                "northbound_hold_accumulation_flow_regime_20",
                "northbound_hold_crowding_reversal_20",
                "northbound_hold_crowding_exhaustion_reversal_20",
                "northbound_hold_decrowding_resilience_20",
            },
        )
        self.assertTrue((pd.to_datetime(factors["raw_date"]) < pd.to_datetime(factors["date"])).all())
        self.assertTrue((pd.to_datetime(factors["available_date"]) <= pd.to_datetime(factors["date"])).all())
        self.assertGreater(factors["date"].nunique(), 0)
        self.assertGreater(factors["asset_id"].nunique(), 0)

    def test_compute_crowding_reversal_factors_from_preregistered_specs(self) -> None:
        bars = _synthetic_bars(days=44, assets=6, start="2024-01-02")
        raw_dates = pd.bdate_range("2024-01-02", periods=38)
        specs = [
            {"factor_name": "northbound_hold_crowding_reversal_20"},
            {"factor_name": "northbound_hold_crowding_exhaustion_reversal_20"},
            {"factor_name": "northbound_hold_decrowding_resilience_20"},
        ]

        factors = compute_external_feed_northbound_factors(
            bars=bars,
            hk_hold=_synthetic_hk_hold(bars, raw_dates=raw_dates),
            hsgt_flow=_synthetic_hsgt_flow(raw_dates),
            candidate_specs=specs,
            lookback=5,
            min_signal_date_amount=1_000_000,
        )

        self.assertEqual({row["factor_name"] for row in specs}, set(factors["factor_name"]))
        self.assertTrue(factors["factor_value"].notna().all())
        self.assertTrue((pd.to_datetime(factors["raw_date"]) < pd.to_datetime(factors["date"])).all())
        self.assertTrue((pd.to_datetime(factors["available_date"]) <= pd.to_datetime(factors["date"])).all())

    def test_build_prescreen_blocks_final_holdout_and_promotion(self) -> None:
        bars = _synthetic_bars(days=44, assets=8, start="2025-11-03", include_holdout=True)
        raw_dates = pd.bdate_range("2025-11-03", periods=40)
        hk_hold = _synthetic_hk_hold(bars, raw_dates=raw_dates)
        hsgt_flow = _synthetic_hsgt_flow(raw_dates)

        result = build_external_feed_northbound_prescreen(
            bars=bars,
            hk_hold=hk_hold,
            hsgt_flow=hsgt_flow,
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

        self.assertEqual(result["stage"], "external_feed_northbound_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 2)
        self.assertEqual(result["summary"]["test_count"], 2)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertIn("lpr_still_blocked", result["promotion_policy"]["blockers"])

    def test_writer_emits_json_markdown_results_and_ic_observations(self) -> None:
        bars = _synthetic_bars(days=34, assets=6, start="2024-01-02")
        raw_dates = pd.bdate_range("2024-01-02", periods=28)
        result = build_external_feed_northbound_prescreen(
            bars=bars,
            hk_hold=_synthetic_hk_hold(bars, raw_dates=raw_dates),
            hsgt_flow=_synthetic_hsgt_flow(raw_dates),
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
            write_external_feed_northbound_prescreen(output, result)

            self.assertTrue((output / "external_feed_northbound_prescreen.json").exists())
            self.assertTrue((output / "external_feed_northbound_prescreen.md").exists())
            self.assertTrue((output / "external_feed_northbound_prescreen_results.csv").exists())
            self.assertTrue((output / "external_feed_northbound_prescreen_ic_observations.csv").exists())


def _synthetic_bars(
    *,
    days: int,
    assets: int,
    start: str,
    include_holdout: bool = False,
) -> pd.DataFrame:
    dates = pd.bdate_range(start, periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=6))
    rows = []
    for asset_idx in range(assets):
        price = 10.0 + asset_idx
        for day_idx, date_value in enumerate(dates):
            signal_component = (asset_idx % 3) * 0.002
            price = price * (1.0 + signal_component + (day_idx % 5) * 0.0002)
            rows.append(
                {
                    "date": date_value,
                    "asset_id": f"CN_XSHE_{asset_idx:06d}",
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 20_000_000.0 + asset_idx * 100_000.0 + day_idx,
                }
            )
    return pd.DataFrame(rows)


def _synthetic_hk_hold(bars: pd.DataFrame, *, raw_dates: pd.DatetimeIndex) -> pd.DataFrame:
    symbols = bars[["asset_id", "symbol"]].drop_duplicates().sort_values("asset_id")
    rows = []
    for date_idx, raw_date in enumerate(raw_dates):
        for asset_idx, row in enumerate(symbols.itertuples(index=False)):
            rows.append(
                {
                    "date": raw_date.date(),
                    "available_date": (raw_date + pd.offsets.BDay(1)).date(),
                    "asset_id": row.asset_id,
                    "symbol": row.symbol,
                    "market": "CN",
                    "hold_ratio": 1.0 + asset_idx * 0.01 + date_idx * (asset_idx + 1) * 0.001,
                    "hold_vol": 1000.0 + asset_idx * 10.0 + date_idx,
                }
            )
    return pd.DataFrame(rows)


def _synthetic_hsgt_flow(raw_dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for date_idx, raw_date in enumerate(raw_dates):
        rows.append(
            {
                "date": raw_date.date(),
                "available_date": (raw_date + pd.offsets.BDay(1)).date(),
                "market": "CN",
                "north_money": 1000.0 if date_idx % 7 < 5 else -500.0,
                "hgt": 600.0,
                "sgt": 400.0,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
