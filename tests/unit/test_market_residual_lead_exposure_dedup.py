import tempfile
import unittest
import warnings
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.ops.market_residual_lead_exposure_dedup import (
    _spearman,
    build_market_residual_lead_exposure_dedup,
    summarize_market_residual_lead_exposure_dedup,
)


def _synthetic_factor_and_labels() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = list(pd.bdate_range("2015-07-01", periods=4)) + list(pd.bdate_range("2016-01-04", periods=4))
    factor_rows = []
    label_rows = []
    reference_rows = []
    for signal_date in dates:
        is_failure_year = signal_date.year == 2015
        for asset_idx in range(40):
            asset_id = f"{asset_idx:06d}.SZ"
            lead_value = float(asset_idx)
            forward_return = (-lead_value if is_failure_year else lead_value) / 1000.0
            factor_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "beta_adjusted_range_contraction_60",
                    "factor_value": lead_value,
                    "amount": 25_000_000.0,
                    "adv20_amount": 25_000_000.0 + asset_idx * 100_000.0,
                    "market_equal_weight_return": 0.001,
                    "beta_120": lead_value,
                    "downside_beta_120": lead_value * 0.8,
                    "market_corr_60": lead_value * 0.7,
                    "residual_vol_60": lead_value * 0.6,
                }
            )
            label_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 20,
                    "forward_return": forward_return,
                }
            )
            reference_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "range_contraction_lowvol_reversal_20",
                    "factor_value": lead_value * 2.0,
                    "amount": 25_000_000.0,
                    "adv20_amount": 25_000_000.0,
                }
            )
            reference_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "independent_reference",
                    "factor_value": float((asset_idx * 7) % 40),
                    "amount": 25_000_000.0,
                    "adv20_amount": 25_000_000.0,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows)


def _synthetic_bars(days: int = 220, assets: int = 45, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 10.0 + asset_idx * 0.03
        for day_idx, signal_date in enumerate(dates):
            market_wave = ((day_idx % 19) - 9) * 0.0009
            beta_load = 0.30 + (asset_idx % 7) * 0.09
            idio = ((asset_idx + day_idx * 2) % 11 - 5) * 0.0005
            price = max(1.0, price * (1.0 + beta_load * market_wave + idio))
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * (1.01 + (asset_idx % 5) * 0.001),
                    "low": price * 0.985,
                    "amount": 25_000_000 + asset_idx * 100_000 + (day_idx % 5) * 50_000,
                }
            )
    return pd.DataFrame(rows)


class MarketResidualLeadExposureDedupTests(unittest.TestCase):
    def test_spearman_returns_nan_without_warning_for_constant_series(self) -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            value = _spearman(pd.Series([1.0, 1.0, 1.0]), pd.Series([1.0, 2.0, 3.0]))

        self.assertTrue(pd.isna(value))
        self.assertEqual(caught, [])

    def test_summarizes_redundancy_exposure_and_yearly_failure(self) -> None:
        factor_frame, labels, reference_frame = _synthetic_factor_and_labels()
        prescreen_report = {
            "results": [
                {
                    "factor_name": "beta_adjusted_range_contraction_60",
                    "horizon": 20,
                    "research_lead": True,
                    "blockers": ["promotion_requires_later_walk_forward_cost_capacity_regime_gates"],
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_market_residual_lead_exposure_dedup(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=2,
        )

        self.assertEqual(result["stage"], "market_residual_lead_exposure_dedup")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed"])
        self.assertEqual(result["next_direction"], "round113_round110_112_three_round_review_before_next_action")
        self.assertIn("lead_highly_redundant_with_reference_factor", result["gate"]["blockers"])
        self.assertIn("twenty_fifteen_regime_failure_unexplained", result["gate"]["blockers"])
        self.assertIn("yearly_ic_instability", result["gate"]["blockers"])
        self.assertIn("lead_high_exposure_to_market_or_liquidity_proxy", result["gate"]["blockers"])

        year_2015 = next(row for row in result["yearly_ic"] if row["year"] == 2015)
        self.assertLess(year_2015["mean_spearman_ic"], 0.0)
        self.assertTrue(year_2015["failure"])

        reference_classes = {row["factor_name"]: row["redundancy_class"] for row in result["reference_correlations"]}
        self.assertEqual(reference_classes["range_contraction_lowvol_reversal_20"], "highly_redundant")
        self.assertEqual(reference_classes["independent_reference"], "unique")

        beta_row = next(row for row in result["exposure_correlations"] if row["exposure_name"] == "beta_120")
        self.assertEqual(beta_row["exposure_class"], "high_exposure")

    def test_reference_sampling_uses_lead_dates_to_preserve_overlap(self) -> None:
        factor_frame, labels, reference_frame = _synthetic_factor_and_labels()
        earlier_reference = reference_frame[reference_frame["factor_name"] == "range_contraction_lowvol_reversal_20"].copy()
        earlier_reference["date"] = pd.Timestamp("2015-06-30")
        shifted_reference_frame = pd.concat([earlier_reference, reference_frame], ignore_index=True)
        prescreen_report = {
            "results": [
                {
                    "factor_name": "beta_adjusted_range_contraction_60",
                    "horizon": 20,
                    "research_lead": True,
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_market_residual_lead_exposure_dedup(
            factor_frame,
            labels,
            reference_factor_frame=shifted_reference_frame,
            prescreen_report=prescreen_report,
            sample_every_n_dates=2,
            min_cross_section=20,
            min_ic_observations=2,
        )

        duplicate = next(
            row for row in result["reference_correlations"] if row["factor_name"] == "range_contraction_lowvol_reversal_20"
        )
        self.assertGreater(duplicate["correlation_observations"], 0)
        self.assertEqual(duplicate["redundancy_class"], "highly_redundant")

    def test_build_excludes_final_holdout_and_creates_reference_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            bars = _synthetic_bars(include_holdout=True)
            store = DatasetStore(root)
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
            prescreen_report = {
                "results": [
                    {
                        "factor_name": "beta_adjusted_range_contraction_60",
                        "horizon": 20,
                        "research_lead": True,
                    }
                ],
                "summary": {"research_lead_count": 1},
            }

            result = build_market_residual_lead_exposure_dedup(
                bars_roots=[root],
                prescreen_report=prescreen_report,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
                horizon=20,
                execution_lag=1,
                sample_every_n_dates=5,
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=10_000_000,
            )

            self.assertFalse(result["holdout_policy"]["final_holdout_included"])
            self.assertLessEqual(result["data_window"]["max_factor_date"], "2025-12-31")
            self.assertTrue(result["reference_correlations"])
            self.assertTrue(result["exposure_correlations"])
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
