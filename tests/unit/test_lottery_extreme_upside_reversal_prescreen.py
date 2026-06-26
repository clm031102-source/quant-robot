import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.lottery_extreme_upside_reversal_preregistration import (
    default_lottery_extreme_upside_candidate_specs,
)
from quant_robot.ops.lottery_extreme_upside_reversal_prescreen import (
    build_lottery_extreme_upside_reversal_prescreen,
    compute_lottery_extreme_upside_reversal_factors,
    summarize_lottery_extreme_upside_reversal_prescreen,
    write_lottery_extreme_upside_reversal_prescreen,
)


class LotteryExtremeUpsideReversalPrescreenTests(unittest.TestCase):
    def test_computes_all_pre_registered_lottery_factor_names(self) -> None:
        factors = compute_lottery_extreme_upside_reversal_factors(
            _synthetic_bars(days=100, assets=40),
            min_signal_date_amount=10_000_000,
        )

        self.assertEqual(factors["factor_name"].nunique(), 6)
        self.assertEqual(
            set(factors["factor_name"].unique()),
            {spec.factor_name for spec in default_lottery_extreme_upside_candidate_specs()},
        )
        self.assertTrue((factors["amount"] >= 10_000_000).all())
        self.assertTrue((factors["adv20_amount"] >= 10_000_000).all())
        self.assertTrue(factors["log_adv20"].notna().all())

    def test_flat_high_low_days_do_not_make_upper_shadow_object_dtype(self) -> None:
        bars = _synthetic_bars(days=80, assets=35)
        bars.loc[bars.index[::9], "high"] = bars.loc[bars.index[::9], "adj_close"]
        bars.loc[bars.index[::9], "low"] = bars.loc[bars.index[::9], "adj_close"]

        factors = compute_lottery_extreme_upside_reversal_factors(
            bars,
            min_signal_date_amount=10_000_000,
        )

        self.assertIn("lottery_upper_shadow_reversal_20", set(factors["factor_name"]))
        self.assertGreater(len(factors), 0)

    def test_summarize_requires_neutral_ic_and_reference_dedup_before_lead(self) -> None:
        factor_rows, labels, stock_basic = _rank_signal_inputs(reference_duplicate=False)
        reference_frame = _reference_frame(factor_rows, duplicate=False)

        result = summarize_lottery_extreme_upside_reversal_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(labels),
            stock_basic,
            reference_frame=reference_frame,
            horizons=(5,),
            min_cross_section=10,
            min_ic_observations=4,
            min_industries=2,
            min_assets_per_industry=5,
            min_neutral_ic_t_stat=2.0,
        )

        self.assertEqual(result["stage"], "lottery_extreme_upside_reversal_prescreen")
        self.assertEqual(result["summary"]["research_lead_count"], 1)
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        row = result["results"][0]
        self.assertTrue(row["research_lead"])
        self.assertGreater(row["mean_spearman_ic"], 0.9)
        self.assertGreater(row["mean_industry_neutral_rank_ic"], 0.9)
        self.assertGreater(row["mean_size_neutral_rank_ic"], 0.9)
        self.assertLess(row["max_reference_corr_abs"], 0.85)
        self.assertNotIn("public_reference_redundancy_too_high", row["blockers"])

    def test_public_reference_duplicate_blocks_research_lead(self) -> None:
        factor_rows, labels, stock_basic = _rank_signal_inputs(reference_duplicate=True)
        reference_frame = _reference_frame(factor_rows, duplicate=True)

        result = summarize_lottery_extreme_upside_reversal_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(labels),
            stock_basic,
            reference_frame=reference_frame,
            horizons=(5,),
            min_cross_section=10,
            min_ic_observations=4,
            min_industries=2,
            min_assets_per_industry=5,
            min_neutral_ic_t_stat=2.0,
        )

        row = result["results"][0]
        self.assertFalse(row["research_lead"])
        self.assertGreaterEqual(row["max_reference_corr_abs"], 0.99)
        self.assertIn("public_reference_redundancy_too_high", row["blockers"])
        self.assertEqual(result["summary"]["research_lead_count"], 0)

    def test_build_and_writer_keep_final_holdout_and_promotion_blocked(self) -> None:
        bars = _synthetic_bars(days=100, assets=40)
        stock_basic = _stock_basic(40)

        result = build_lottery_extreme_upside_reversal_prescreen(
            bars=bars,
            stock_basic=stock_basic,
            horizons=(5,),
            execution_lag=1,
            min_cross_section=20,
            min_ic_observations=4,
            min_industries=2,
            min_assets_per_industry=5,
        )

        self.assertEqual(result["stage"], "lottery_extreme_upside_reversal_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 6)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed_before_prescreen"])
        self.assertFalse(result["live_boundary_allowed"])
        self.assertIn("reference_dedup_policy", result)

        with tempfile.TemporaryDirectory() as tmp:
            write_lottery_extreme_upside_reversal_prescreen(tmp, result)
            output_dir = Path(tmp)
            self.assertTrue((output_dir / "lottery_extreme_upside_reversal_prescreen.json").exists())
            self.assertTrue((output_dir / "lottery_extreme_upside_reversal_prescreen.md").exists())
            self.assertTrue((output_dir / "lottery_extreme_upside_reversal_prescreen_results.csv").exists())
            self.assertTrue((output_dir / "lottery_extreme_upside_reversal_prescreen_ic_observations.csv").exists())
            self.assertTrue((output_dir / "lottery_extreme_upside_reversal_prescreen_neutral_observations.csv").exists())


def _synthetic_bars(days: int = 100, assets: int = 40) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        price = 10.0 + asset_idx * 0.05
        for day_idx, date_value in enumerate(dates):
            seasonal = ((day_idx % 13) - 6) * 0.002
            lottery_burst = 0.10 if (day_idx + asset_idx) % 37 == 0 else 0.0
            price = max(1.0, price * (1.0 + seasonal + lottery_burst))
            high = price * (1.01 + (0.02 if (day_idx + asset_idx) % 11 == 0 else 0.0))
            low = price * 0.985
            amount = 20_000_000 + asset_idx * 100_000 + (day_idx % 7) * 50_000
            rows.append(
                {
                    "date": date_value,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "adj_close": price,
                    "high": high,
                    "low": low,
                    "amount": amount,
                }
            )
    return pd.DataFrame(rows)


def _rank_signal_inputs(*, reference_duplicate: bool) -> tuple[list[dict], list[dict], pd.DataFrame]:
    dates = pd.bdate_range("2024-01-03", periods=8)
    factor_rows = []
    label_rows = []
    for date_value in dates:
        for asset_idx in range(10):
            asset_id = f"CN_XSHE_{asset_idx:06d}"
            within_industry_rank = asset_idx % 5
            signal = float(within_industry_rank)
            if reference_duplicate:
                signal = float(within_industry_rank)
            factor_rows.append(
                {
                    "date": date_value,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "lottery_test_signal",
                    "factor_value": signal,
                    "amount": 20_000_000.0,
                    "adv20_amount": 20_000_000.0 + (asset_idx // 5) * 5_000_000.0,
                    "log_adv20": 1.0 + (asset_idx // 5),
                }
            )
            label_rows.append(
                {
                    "date": date_value,
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 5,
                    "execution_lag": 1,
                    "forward_return": 0.01 + within_industry_rank * 0.02,
                }
            )
    return factor_rows, label_rows, _stock_basic(10)


def _reference_frame(factor_rows: list[dict], *, duplicate: bool) -> pd.DataFrame:
    rows = []
    for row in factor_rows:
        asset_idx = int(str(row["asset_id"]).rsplit("_", 1)[-1])
        rows.append(
            {
                "date": row["date"],
                "asset_id": row["asset_id"],
                "market": row["market"],
                "reference_name": "public_short_reversal_5",
                "reference_value": row["factor_value"] if duplicate else float((asset_idx * 2) % 5),
            }
        )
    return pd.DataFrame(rows)


def _stock_basic(assets: int) -> pd.DataFrame:
    rows = []
    for asset_idx in range(assets):
        rows.append(
            {
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "symbol": f"{asset_idx:06d}.SZ",
                "market": "CN",
                "exchange": "XSHE",
                "industry": "Tech" if asset_idx < assets // 2 else "Bank",
                "name": f"Stock {asset_idx}",
                "list_date": "2020-01-01",
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
