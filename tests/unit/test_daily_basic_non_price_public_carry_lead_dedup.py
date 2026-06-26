import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_non_price_public_carry_lead_dedup import (
    DEFAULT_LEAD_FACTOR_NAME,
    NEXT_PORTFOLIO_PREFLIGHT_DIRECTION,
    NEXT_STABILITY_AUDIT_DIRECTION,
    ROTATE_AFTER_DEDUP_FAILURE_DIRECTION,
    build_daily_basic_non_price_public_carry_lead_dedup,
    summarize_daily_basic_non_price_public_carry_lead_dedup,
)
from quant_robot.storage.dataset_store import DatasetStore
from tests.unit.test_daily_basic_non_price_public_carry_prescreen import (
    _synthetic_bars,
    _synthetic_daily_basic,
)


def _lead_rows(
    dates: list[pd.Timestamp],
    *,
    implementation_locked: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    factor_rows = []
    reference_rows = []
    exposure_rows = []
    labels = []
    for signal_date in dates:
        for asset_idx in range(48):
            common = {
                "date": signal_date,
                "asset_id": f"{asset_idx:06d}.SZ",
                "market": "CN",
            }
            thesis_value = float(asset_idx)
            implementation_value = float(asset_idx if implementation_locked else (asset_idx * 17) % 48)
            lead_value = thesis_value if implementation_locked else thesis_value + implementation_value * 0.02
            forward_return = (thesis_value if not implementation_locked else implementation_value) / 1000.0
            factor_rows.append(
                common
                | {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "factor_value": lead_value,
                    "amount": 30_000_000.0,
                    "adv20_amount": 30_000_000.0,
                }
            )
            reference_rows.append(
                common
                | {
                    "factor_name": "daily_basic_duplicate_reference",
                    "factor_value": lead_value * 2.0,
                    "amount": 30_000_000.0,
                    "adv20_amount": 30_000_000.0,
                }
            )
            reference_rows.append(
                common
                | {
                    "factor_name": "daily_basic_independent_reference",
                    "factor_value": float((asset_idx * 11) % 48),
                    "amount": 30_000_000.0,
                    "adv20_amount": 30_000_000.0,
                }
            )
            exposure_rows.append(
                common
                | {
                    "free_share_to_total_share": thesis_value,
                    "float_share_to_total_share": thesis_value * 0.9,
                    "free_share_to_float_share": thesis_value * 0.8,
                    "inv_pb": implementation_value,
                    "dv_ttm": implementation_value * 0.5,
                    "log_circ_mv": implementation_value,
                    "log_total_mv": implementation_value * 0.7,
                    "log_adv20_amount": implementation_value * 0.4,
                }
            )
            labels.append(common | {"horizon": 20, "forward_return": forward_return})
    return pd.DataFrame(factor_rows), pd.DataFrame(labels), pd.DataFrame(reference_rows), pd.DataFrame(exposure_rows)


class DailyBasicNonPricePublicCarryLeadDedupTests(unittest.TestCase):
    def test_blocks_portfolio_conversion_when_lead_is_implementation_exposure_and_residual_collapses(self) -> None:
        dates = list(pd.bdate_range("2015-07-01", periods=4)) + list(pd.bdate_range("2016-01-04", periods=4))
        factor_frame, labels, reference_frame, exposure_frame = _lead_rows(dates, implementation_locked=True)
        prescreen_report = {
            "results": [
                {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "horizon": 20,
                    "research_lead": True,
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_daily_basic_non_price_public_carry_lead_dedup(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=2,
        )

        self.assertEqual(result["stage"], "daily_basic_non_price_public_carry_lead_dedup")
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_conversion_candidate"])
        self.assertEqual(result["next_direction"], ROTATE_AFTER_DEDUP_FAILURE_DIRECTION)
        self.assertIn("lead_highly_redundant_with_daily_basic_reference", result["gate"]["blockers"])
        self.assertIn("lead_high_implementation_exposure", result["gate"]["blockers"])
        self.assertIn("residual_ic_observations_below_threshold", result["gate"]["blockers"])
        self.assertNotIn("lead_high_share_structure_thesis_exposure", result["gate"]["blockers"])
        self.assertEqual(
            next(row for row in result["exposure_correlations"] if row["exposure_name"] == "free_share_to_total_share")[
                "exposure_role"
            ],
            "thesis",
        )
        self.assertEqual(
            next(row for row in result["exposure_correlations"] if row["exposure_name"] == "log_circ_mv")[
                "exposure_class"
            ],
            "high_exposure",
        )

    def test_allows_next_portfolio_preflight_when_residual_ic_survives_implementation_neutralization(self) -> None:
        dates = list(pd.bdate_range("2016-01-04", periods=8))
        factor_frame, labels, reference_frame, exposure_frame = _lead_rows(dates, implementation_locked=False)
        prescreen_report = {
            "results": [
                {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "horizon": 20,
                    "research_lead": True,
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_daily_basic_non_price_public_carry_lead_dedup(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame[reference_frame["factor_name"] == "daily_basic_independent_reference"],
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_mean_ic=0.02,
            min_residual_icir=0.0,
            min_residual_positive_ic_rate=0.55,
        )

        self.assertEqual(result["next_direction"], NEXT_PORTFOLIO_PREFLIGHT_DIRECTION)
        self.assertTrue(result["promotion_policy"]["portfolio_conversion_candidate"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertGreater(result["residual_ic_summary"]["mean_spearman_ic"], 0.02)
        self.assertGreaterEqual(result["residual_ic_summary"]["positive_ic_rate"], 0.55)
        self.assertNotIn("lead_high_implementation_exposure", result["gate"]["blockers"])

    def test_routes_promising_residual_with_yearly_instability_to_stability_audit_not_family_rotation(self) -> None:
        dates = list(pd.bdate_range("2023-07-03", periods=4)) + list(pd.bdate_range("2024-01-02", periods=10))
        factor_frame, labels, reference_frame, exposure_frame = _lead_rows(dates, implementation_locked=False)
        labels = labels.copy()
        labels.loc[pd.to_datetime(labels["date"]).dt.year == 2023, "forward_return"] *= -1.0
        prescreen_report = {
            "results": [
                {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "horizon": 20,
                    "research_lead": True,
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_daily_basic_non_price_public_carry_lead_dedup(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame[reference_frame["factor_name"] == "daily_basic_independent_reference"],
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_mean_ic=0.02,
            min_residual_icir=0.0,
            min_residual_positive_ic_rate=0.55,
        )

        self.assertIn("residual_yearly_ic_instability", result["gate"]["blockers"])
        self.assertEqual(result["next_direction"], NEXT_STABILITY_AUDIT_DIRECTION)
        self.assertFalse(result["promotion_policy"]["portfolio_conversion_candidate"])

    def test_build_excludes_final_holdout_and_produces_residual_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            store = DatasetStore(root)
            store.write_frame(
                _synthetic_bars(days=90, include_holdout=True),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                _synthetic_daily_basic(days=90, include_holdout=True),
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            prescreen_report = {
                "results": [
                    {
                        "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                        "horizon": 20,
                        "research_lead": True,
                    }
                ],
                "summary": {"research_lead_count": 1},
            }

            result = build_daily_basic_non_price_public_carry_lead_dedup(
                bars_roots=[root],
                daily_basic_roots=[root],
                prescreen_report=prescreen_report,
                analysis_end_date="2025-12-31",
                horizon=20,
                sample_every_n_dates=5,
                min_cross_section=20,
                min_ic_observations=4,
            )

        self.assertFalse(result["holdout_policy"]["final_holdout_included"])
        self.assertLessEqual(result["data_window"]["max_factor_date"], "2025-12-31")
        self.assertGreater(result["data_window"]["exposure_rows"], 0)
        self.assertIn("raw_ic_summary", result)
        self.assertIn("residual_ic_summary", result)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
