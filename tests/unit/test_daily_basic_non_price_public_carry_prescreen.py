import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (
    build_daily_basic_non_price_public_carry_prescreen,
    compute_daily_basic_non_price_public_carry_factors,
    summarize_daily_basic_non_price_public_carry_prescreen,
)
from quant_robot.ops.daily_basic_non_price_public_carry_preregistration import (
    DailyBasicNonPricePublicCarryCandidateSpec,
)
from quant_robot.storage.dataset_store import DatasetStore


def _synthetic_daily_basic(days: int = 90, assets: int = 40, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        for day_idx, date in enumerate(dates):
            value_rank = asset_idx + 1
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "source": "synthetic",
                    "pe": 8.0 + (assets - value_rank) * 0.10 + (day_idx % 3) * 0.01,
                    "pe_ttm": 9.0 + (assets - value_rank) * 0.12 + (day_idx % 5) * 0.01,
                    "pb": 0.7 + (assets - value_rank) * 0.015,
                    "ps": 0.8 + (assets - value_rank) * 0.02,
                    "ps_ttm": 0.9 + (assets - value_rank) * 0.018,
                    "dv_ratio": 0.5 + value_rank * 0.02,
                    "dv_ttm": 0.6 + value_rank * 0.025,
                    "total_share": 1_000_000_000 + asset_idx * 1_000_000,
                    "float_share": 700_000_000 + asset_idx * 800_000,
                    "free_share": 500_000_000 + asset_idx * 600_000,
                    "total_mv": 8_000_000_000 + asset_idx * 40_000_000,
                    "circ_mv": 5_000_000_000 + asset_idx * 30_000_000,
                    "volume_ratio": 0.8 + (asset_idx % 9) * 0.05 + (day_idx % 7) * 0.01,
                }
            )
    return pd.DataFrame(rows)


def _synthetic_bars(days: int = 90, assets: int = 40, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        price = 10.0 + asset_idx * 0.03
        for day_idx, date in enumerate(dates):
            price = price * (1.0 + ((day_idx % 11) - 5) * 0.0008 + asset_idx * 0.00003)
            rows.append(
                {
                    "date": date,
                    "asset_id": f"{asset_idx:06d}.SZ",
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 30_000_000 + asset_idx * 200_000 + (day_idx % 5) * 50_000,
                }
            )
    return pd.DataFrame(rows)


class DailyBasicNonPricePublicCarryPrescreenTests(unittest.TestCase):
    def test_computes_all_pre_registered_daily_basic_factor_names_with_coverage_columns(self) -> None:
        factors = compute_daily_basic_non_price_public_carry_factors(_synthetic_daily_basic())

        self.assertEqual(factors["factor_name"].nunique(), 10)
        self.assertIn("daily_basic_dividend_value_stability_carry_20", set(factors["factor_name"]))
        self.assertIn("daily_basic_size_quality_value_stability_60", set(factors["factor_name"]))
        self.assertTrue((factors["required_field_count"] > 0).all())
        self.assertTrue((factors["field_coverage_ratio"] >= 0.99).all())
        self.assertFalse(factors["factor_name"].str.contains("turnover_rate|moneyflow|alpha101", regex=True).any())

    def test_computes_round211_coverage_repaired_valuation_candidate_only_when_registered(self) -> None:
        spec = DailyBasicNonPricePublicCarryCandidateSpec(
            factor_name="daily_basic_valuation_reversion_dvratio_quality_60",
            family="valuation_stability_coverage_repair",
            formula_template="0.45*cs_z(-pb_z_60)+0.30*cs_z(-ps_ttm_z_60)+0.25*cs_z(dv_ratio)",
            direction="higher_is_better",
            windows=(60,),
            required_fields=("pb", "ps_ttm", "dv_ratio"),
            economic_rationale="Coverage-repaired version of the Round132 valuation reversion signal.",
            public_reference_tags=("value_reversion", "fama_french_value", "coverage_repair"),
            expected_failure_modes=("field_substitution_changes_economics", "coverage_repair_overfit"),
        )

        factors = compute_daily_basic_non_price_public_carry_factors(_synthetic_daily_basic(), candidate_specs=[spec])

        self.assertEqual(set(factors["factor_name"]), {"daily_basic_valuation_reversion_dvratio_quality_60"})
        self.assertTrue((factors["field_coverage_ratio"] >= 0.99).all())

    def test_summarizes_daily_basic_coverage_and_blocks_low_coverage_from_research_lead(self) -> None:
        dates = pd.bdate_range("2025-01-02", periods=8)
        factor_rows = []
        labels = []
        for factor_name, coverage_ratio in [
            ("daily_basic_good_signal", 1.0),
            ("daily_basic_sparse_signal", 0.5),
        ]:
            for date in dates:
                for asset_idx in range(40):
                    asset_id = f"{asset_idx:06d}.SZ"
                    signal = float(asset_idx)
                    factor_rows.append(
                        {
                            "date": date,
                            "asset_id": asset_id,
                            "market": "CN",
                            "factor_name": factor_name,
                            "factor_value": signal,
                            "required_field_count": 4,
                            "available_field_count": int(4 * coverage_ratio),
                            "field_coverage_ratio": coverage_ratio,
                            "amount": 30_000_000.0,
                            "adv20_amount": 30_000_000.0,
                        }
                    )
        for date in dates:
            for asset_idx in range(40):
                asset_id = f"{asset_idx:06d}.SZ"
                signal = float(asset_idx)
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

        result = summarize_daily_basic_non_price_public_carry_prescreen(
            pd.DataFrame(factor_rows),
            pd.DataFrame(labels),
            expected_candidate_count=2,
            horizons=(5,),
            min_cross_section=20,
            min_ic_observations=4,
            min_field_coverage_ratio=0.80,
        )

        rows = {row["factor_name"]: row for row in result["results"]}
        self.assertTrue(rows["daily_basic_good_signal"]["research_lead"])
        self.assertFalse(rows["daily_basic_sparse_signal"]["research_lead"])
        self.assertIn("daily_basic_field_coverage_below_minimum", rows["daily_basic_sparse_signal"]["blockers"])
        self.assertEqual(result["summary"]["promotion_allowed_candidates"], 0)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertGreater(result["coverage_preflight"]["factor_coverage_rows"], 0)

    def test_builds_prescreen_from_bars_and_daily_basic_without_reading_final_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            store = DatasetStore(root)
            bars = _synthetic_bars(include_holdout=True)
            daily_basic = _synthetic_daily_basic(include_holdout=True)
            store.write_frame(
                bars[bars["date"].dt.year == 2025],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                bars[bars["date"].dt.year == 2026],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2026"},
            )
            store.write_frame(
                daily_basic[daily_basic["date"].dt.year == 2025],
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                daily_basic[daily_basic["date"].dt.year == 2026],
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2026"},
            )

            result = build_daily_basic_non_price_public_carry_prescreen(
                bars_roots=[root],
                daily_basic_roots=[root],
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

        self.assertEqual(result["stage"], "daily_basic_non_price_public_carry_prescreen")
        self.assertEqual(result["summary"]["candidate_count"], 10)
        self.assertGreater(result["summary"]["factor_rows"], 0)
        self.assertGreater(result["summary"]["label_rows"], 0)
        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
        self.assertEqual(set(result["summary"]["horizons"]), {5})
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
