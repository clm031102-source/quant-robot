import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.event_contextual_underreaction_prescreen import (
    build_event_contextual_underreaction_prescreen,
    compute_event_contextual_underreaction_factor_frame,
    default_event_contextual_underreaction_candidate_specs,
    write_event_contextual_underreaction_prescreen,
)
from tests.unit.test_event_factor_pit_ic_prescreen import _stock_basic, _synthetic_bars


class EventContextualUnderreactionPrescreenTests(unittest.TestCase):
    def test_compute_contextual_factors_use_post_event_signal_date_and_context(self) -> None:
        bars = _synthetic_bars(days=45, assets=6)
        stock_basic = _stock_basic(6)
        events = _event_frames(assets=6, dates=("2024-01-30", "2024-02-15"))

        factors = compute_event_contextual_underreaction_factor_frame(
            events,
            bars,
            stock_basic,
            pit_lag_trade_days=1,
        )

        self.assertEqual(
            set(factors["factor_name"]),
            {
                "event_repurchase_underreaction_20",
                "event_repurchase_quiet_volume_20",
                "event_holder_contraction_underreaction_20",
                "event_holder_contraction_low_vol_20",
            },
        )
        self.assertTrue((pd.to_datetime(factors["date"]) > pd.to_datetime(factors["event_date"])).all())
        self.assertTrue(factors["factor_value"].notna().all())
        self.assertTrue(factors["pre_signal_return_20"].notna().all())
        self.assertTrue(factors["amount_trend_5_20"].notna().all())
        self.assertTrue((factors["pit_lag_trade_days"] == 1).all())

    def test_build_prescreen_blocks_promotion_and_records_round248_policy(self) -> None:
        bars = _predictive_bars(days=55, assets=8)
        stock_basic = _stock_basic(8)
        events = _event_frames(assets=8, dates=("2024-01-30", "2024-02-13", "2024-02-27", "2024-03-12"))

        result = build_event_contextual_underreaction_prescreen(
            bars=bars,
            stock_basic=stock_basic,
            event_frames=events,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-12-31",
            horizons=(5,),
            execution_lag=0,
            min_cross_section=4,
            min_ic_observations=2,
            min_industries=2,
            min_assets_per_industry=2,
            min_neutral_rank_ic=-1.0,
            min_neutral_ic_t_stat=-10.0,
            min_neutral_retention=0.0,
        )

        self.assertEqual(result["stage"], "event_contextual_underreaction_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], len(default_event_contextual_underreaction_candidate_specs()))
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertIn("round248", result["round_context"]["round"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])

    def test_write_outputs_contextual_underreaction_artifacts(self) -> None:
        bars = _predictive_bars(days=55, assets=8)
        stock_basic = _stock_basic(8)
        events = _event_frames(assets=8, dates=("2024-01-30", "2024-02-13", "2024-02-27", "2024-03-12"))
        result = build_event_contextual_underreaction_prescreen(
            bars=bars,
            stock_basic=stock_basic,
            event_frames=events,
            analysis_start_date="2024-01-01",
            analysis_end_date="2024-12-31",
            horizons=(5,),
            execution_lag=0,
            min_cross_section=4,
            min_ic_observations=2,
            min_industries=2,
            min_assets_per_industry=2,
            min_neutral_rank_ic=-1.0,
            min_neutral_ic_t_stat=-10.0,
            min_neutral_retention=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_event_contextual_underreaction_prescreen(output_dir, result)
            self.assertTrue((output_dir / "event_contextual_underreaction_prescreen.json").exists())
            self.assertTrue((output_dir / "event_contextual_underreaction_prescreen.md").exists())
            self.assertTrue((output_dir / "event_contextual_underreaction_results.csv").exists())
            self.assertTrue((output_dir / "event_contextual_underreaction_ic_observations.csv").exists())


def _event_frames(*, assets: int, dates: tuple[str, ...]) -> dict[str, pd.DataFrame]:
    repurchase_rows = []
    holder_rows = []
    for event_idx, date_value in enumerate(dates):
        end_date = (pd.Timestamp(date_value) - pd.offsets.QuarterEnd(0)).strftime("%Y%m%d")
        for asset_idx in range(assets):
            ts_code = f"{asset_idx:06d}.SZ"
            ann_date = pd.Timestamp(date_value).strftime("%Y%m%d")
            strength = 1.0 + asset_idx / max(assets - 1, 1)
            repurchase_rows.append(
                {
                    "ts_code": ts_code,
                    "ann_date": ann_date,
                    "amount": 10_000_000.0 * strength * (1.0 + event_idx * 0.1),
                }
            )
            holder_rows.append(
                {
                    "ts_code": ts_code,
                    "ann_date": ann_date,
                    "end_date": end_date,
                    "holder_num": 10_000.0 - event_idx * 250.0 * strength,
                }
            )
    return {
        "repurchase": pd.DataFrame(repurchase_rows),
        "stk_holdernumber": pd.DataFrame(holder_rows),
    }


def _predictive_bars(*, days: int, assets: int) -> pd.DataFrame:
    bars = _synthetic_bars(days=days, assets=assets)
    bars = bars.sort_values(["asset_id", "date"]).reset_index(drop=True)
    for asset_id, group in bars.groupby("asset_id", sort=False):
        asset_idx = int(asset_id.rsplit("_", 1)[-1])
        mask = bars["asset_id"] == asset_id
        trend = 1.0 + asset_idx * 0.0005
        bars.loc[mask, "adj_close"] = (10.0 + asset_idx) * (trend ** pd.Series(range(mask.sum())).to_numpy())
        bars.loc[mask, "high"] = bars.loc[mask, "adj_close"] * 1.01
        bars.loc[mask, "low"] = bars.loc[mask, "adj_close"] * 0.99
        bars.loc[mask, "amount"] = 20_000_000.0 + asset_idx * 1_000_000.0
    return bars


if __name__ == "__main__":
    unittest.main()
