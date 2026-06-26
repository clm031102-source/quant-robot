import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.ops.turnover_continuous_capacity_repair_prescreen import (
    build_turnover_continuous_capacity_repair_prescreen,
    compute_turnover_continuous_capacity_repair_factors,
    summarize_turnover_continuous_capacity_repair_prescreen,
)


def _synthetic_bars_and_daily_basic(
    *,
    days: int = 90,
    assets: int = 40,
    include_holdout: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    bar_rows = []
    input_rows = []
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        price = 10.0 + asset_idx * 0.02
        for day_idx, trade_date in enumerate(dates):
            price *= 1.0 + ((asset_idx % 9) - 4) * 0.0006 + ((day_idx % 13) - 6) * 0.0002
            amount = 15_000_000 + asset_idx * 250_000 + (day_idx % 5) * 100_000
            turnover = 0.3 + (assets - asset_idx) * 0.01 + (day_idx % 7) * 0.001
            bar_rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": amount,
                }
            )
            input_rows.append(
                {
                    "date": trade_date,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "source": "tushare",
                    "turnover_rate": turnover,
                    "turnover_rate_f": turnover * 0.9,
                    "volume_ratio": 1.0,
                    "pe_ttm": 10.0,
                    "pb": 2.0,
                    "ps_ttm": 5.0,
                    "dv_ttm": 2.0,
                    "total_mv": 100_000.0 + asset_idx * 100.0,
                    "circ_mv": 50_000.0 + asset_idx * 200.0,
                }
            )
    return pd.DataFrame(bar_rows), pd.DataFrame(input_rows)


class TurnoverContinuousCapacityRepairPrescreenTests(unittest.TestCase):
    def test_computes_all_preregistered_continuous_repair_factor_names(self) -> None:
        bars, daily_basic = _synthetic_bars_and_daily_basic()

        factors = compute_turnover_continuous_capacity_repair_factors(
            bars,
            daily_basic,
            min_signal_date_amount=10_000_000,
        )

        self.assertEqual(factors["factor_name"].nunique(), 6)
        self.assertIn("turnover_rate_low_adv_soft_rank_20", set(factors["factor_name"]))
        self.assertIn("turnover_rate_f_low_participation_budget_100k_20", set(factors["factor_name"]))
        self.assertIn("raw_factor_value", factors.columns)
        self.assertIn("estimated_participation_100k_top100_adv20", factors.columns)
        self.assertTrue((factors["amount"] >= 10_000_000).all())
        self.assertFalse(factors["factor_name"].str.contains("large_mv").any())

    def test_summarizer_adds_capacity_extreme_return_and_raw_correlation_diagnostics(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=8)
        factor_rows = []
        labels = []
        for date in dates:
            for asset_idx in range(40):
                signal = float(asset_idx)
                asset_id = f"CN_XSHE_{asset_idx:06d}"
                factor_rows.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "turnover_rate_low_adv_mv_soft_blend_20",
                        "factor_value": signal,
                        "raw_factor_value": signal,
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                        "estimated_participation_100k_top100_adv20": 0.005,
                    }
                )
                labels.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": signal / 10_000.0,
                        "entry_date": date + pd.Timedelta(days=1),
                        "exit_date": date + pd.Timedelta(days=6),
                    }
                )

        result = summarize_turnover_continuous_capacity_repair_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(labels),
            min_cross_section=20,
            min_ic_observations=4,
        )

        self.assertEqual(result["stage"], "turnover_continuous_capacity_repair_prescreen")
        self.assertEqual(result["summary"]["research_lead_count"], 1)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        row = result["results"][0]
        self.assertEqual(row["capacity_limited_top_quantile_trades"], 0)
        self.assertEqual(row["extreme_forward_return_count"], 0)
        self.assertLessEqual(row["max_estimated_participation"], 0.01)
        self.assertGreater(row["raw_factor_spearman_corr"], 0.99)
        self.assertTrue(row["research_lead"])

    def test_capacity_dirty_candidate_is_not_research_lead_even_with_good_ic(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=8)
        factor_rows = []
        labels = []
        for date in dates:
            for asset_idx in range(40):
                signal = float(asset_idx)
                asset_id = f"CN_XSHE_{asset_idx:06d}"
                factor_rows.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "turnover_rate_low_adv_soft_rank_20",
                        "factor_value": signal,
                        "raw_factor_value": signal,
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                        "estimated_participation_100k_top100_adv20": 0.02 if asset_idx >= 32 else 0.005,
                    }
                )
                labels.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": signal / 10_000.0,
                        "entry_date": date + pd.Timedelta(days=1),
                        "exit_date": date + pd.Timedelta(days=6),
                    }
                )

        result = summarize_turnover_continuous_capacity_repair_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(labels),
            min_cross_section=20,
            min_ic_observations=4,
        )

        self.assertEqual(result["summary"]["research_lead_count"], 0)
        row = result["results"][0]
        self.assertGreater(row["capacity_limited_top_quantile_trades"], 0)
        self.assertIn("capacity_limited_top_quantile_trades_present", row["blockers"])

    def test_low_extreme_return_rate_is_diagnostic_not_automatic_rejection(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=8)
        factor_rows = []
        labels = []
        for date_idx, date in enumerate(dates):
            for asset_idx in range(40):
                signal = float(asset_idx)
                asset_id = f"CN_XSHE_{asset_idx:06d}"
                factor_rows.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "factor_name": "turnover_rate_f_low_participation_budget_100k_20",
                        "factor_value": signal,
                        "raw_factor_value": signal,
                        "amount": 20_000_000.0,
                        "adv20_amount": 20_000_000.0,
                        "estimated_participation_100k_top100_adv20": 0.005,
                    }
                )
                forward_return = signal / 10_000.0
                if date_idx == 0 and asset_idx == 39:
                    forward_return = 0.60
                labels.append(
                    {
                        "date": date,
                        "asset_id": asset_id,
                        "market": "CN",
                        "horizon": 20,
                        "execution_lag": 1,
                        "forward_return": forward_return,
                        "entry_date": date + pd.Timedelta(days=1),
                        "exit_date": date + pd.Timedelta(days=21),
                    }
                )

        result = summarize_turnover_continuous_capacity_repair_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(labels),
            horizons=(20,),
            min_cross_section=20,
            min_ic_observations=4,
        )

        row = result["results"][0]
        self.assertEqual(row["extreme_forward_return_count"], 1)
        self.assertLess(row["extreme_forward_return_rate"], 0.10)
        self.assertTrue(row["research_lead"])
        self.assertNotIn("extreme_forward_return_count_present", row["blockers"])

    def test_builds_prescreen_from_bars_and_daily_basic_without_final_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            factor_root = Path(tmp) / "daily_basic"
            bars, daily_basic = _synthetic_bars_and_daily_basic(include_holdout=True)
            store = DatasetStore(root)
            input_store = DatasetStore(factor_root)
            for year in [2025, 2026]:
                year_bars = bars[bars["date"].dt.year == year]
                year_inputs = daily_basic[daily_basic["date"].dt.year == year]
                store.write_frame(year_bars, "bars", {"frequency": "1d", "market": "CN", "year": str(year)})
                input_store.write_frame(
                    year_inputs,
                    "processed/factor_inputs",
                    {"frequency": "1d", "market": "CN", "year": str(year)},
                )

            result = build_turnover_continuous_capacity_repair_prescreen(
                bars_roots=[root],
                factor_input_root=factor_root,
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=10_000_000,
            )

        self.assertEqual(result["summary"]["candidate_count"], 6)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
