import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.public_technical_failure_reversal_neutral_dedup import (
    DEFAULT_LEAD_FACTOR_NAME,
    NEXT_PORTFOLIO_PREFLIGHT_DIRECTION,
    ROTATE_AFTER_NEUTRAL_DEDUP_FAILURE_DIRECTION,
    summarize_public_technical_failure_reversal_neutral_dedup,
    write_public_technical_failure_reversal_neutral_dedup,
)


def _synthetic_round156_frames(
    *,
    implementation_locked: bool,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    dates = list(pd.bdate_range("2018-01-02", periods=6)) + list(pd.bdate_range("2019-01-02", periods=6))
    lead_rows = []
    label_rows = []
    reference_rows = []
    exposure_rows = []
    for signal_date in dates:
        for asset_idx in range(48):
            industry = "bank" if asset_idx < 16 else "tech" if asset_idx < 32 else "industrial"
            common = {
                "date": signal_date,
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "market": "CN",
            }
            true_signal = float(asset_idx)
            implementation_value = float(asset_idx if implementation_locked else (asset_idx * 17) % 48)
            lead_value = implementation_value if implementation_locked else true_signal + implementation_value * 0.02
            forward_return = (implementation_value if implementation_locked else true_signal) / 1000.0
            lead_rows.append(
                common
                | {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "factor_value": lead_value,
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0 + implementation_value * 10_000.0,
                    "industry": industry,
                }
            )
            label_rows.append(common | {"horizon": 5, "forward_return": forward_return})
            reference_rows.append(
                common
                | {
                    "factor_name": "rsrs_slope_acceleration_quality_18_60",
                    "factor_value": implementation_value,
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0,
                }
            )
            reference_rows.append(
                common
                | {
                    "factor_name": "independent_public_reference",
                    "factor_value": float((asset_idx * 11) % 48),
                    "amount": 50_000_000.0,
                    "adv20_amount": 50_000_000.0,
                }
            )
            exposure_rows.append(
                common
                | {
                    "industry": industry,
                    "log_adv20_amount": implementation_value,
                    "log_amount": implementation_value * 0.8,
                    "realized_vol_20": implementation_value * 0.5,
                }
            )
    return pd.DataFrame(lead_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows), pd.DataFrame(exposure_rows)


class PublicTechnicalFailureReversalNeutralDedupTests(unittest.TestCase):
    def test_blocks_portfolio_preflight_when_rsrs_lead_is_reference_and_exposure_locked(self) -> None:
        lead_frame, labels, reference_frame, exposure_frame = _synthetic_round156_frames(
            implementation_locked=True,
        )
        prescreen_report = {
            "results": [
                {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "horizon": 5,
                    "research_lead": True,
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_public_technical_failure_reversal_neutral_dedup(
            lead_frame,
            labels,
            reference_factor_frame=reference_frame,
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_icir=0.0,
        )

        self.assertEqual(result["stage"], "public_technical_failure_reversal_neutral_dedup")
        self.assertEqual(result["next_direction"], ROTATE_AFTER_NEUTRAL_DEDUP_FAILURE_DIRECTION)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertFalse(result["promotion_policy"]["portfolio_preflight_candidate"])
        self.assertIn("lead_highly_redundant_with_public_technical_reference", result["gate"]["blockers"])
        self.assertIn("lead_high_size_liquidity_or_volatility_exposure", result["gate"]["blockers"])
        self.assertGreater(result["raw_ic_summary"]["mean_spearman_ic"], 0.90)
        self.assertEqual(
            next(row for row in result["reference_correlations"] if row["factor_name"] == "rsrs_slope_acceleration_quality_18_60")[
                "redundancy_class"
            ],
            "highly_redundant",
        )
        self.assertEqual(
            next(row for row in result["exposure_correlations"] if row["exposure_name"] == "log_adv20_amount")[
                "exposure_class"
            ],
            "high_exposure",
        )

    def test_allows_preflight_candidate_when_residual_ic_survives_neutral_dedup(self) -> None:
        lead_frame, labels, reference_frame, exposure_frame = _synthetic_round156_frames(
            implementation_locked=False,
        )
        prescreen_report = {
            "results": [
                {
                    "factor_name": DEFAULT_LEAD_FACTOR_NAME,
                    "horizon": 5,
                    "research_lead": True,
                }
            ],
            "summary": {"research_lead_count": 1},
        }

        result = summarize_public_technical_failure_reversal_neutral_dedup(
            lead_frame,
            labels,
            reference_factor_frame=reference_frame[reference_frame["factor_name"] == "independent_public_reference"],
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_mean_ic=0.02,
            min_industry_neutral_icir=0.0,
            min_residual_icir=0.0,
            min_residual_positive_ic_rate=0.55,
        )

        self.assertEqual(result["next_direction"], NEXT_PORTFOLIO_PREFLIGHT_DIRECTION)
        self.assertTrue(result["promotion_policy"]["portfolio_preflight_candidate"])
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertGreater(result["industry_neutral_ic_summary"]["mean_spearman_ic"], 0.02)
        self.assertGreater(result["residual_ic_summary"]["mean_spearman_ic"], 0.02)
        self.assertGreaterEqual(result["residual_ic_summary"]["positive_ic_rate"], 0.55)
        self.assertNotIn("lead_high_size_liquidity_or_volatility_exposure", result["gate"]["blockers"])

    def test_writer_outputs_structured_audit_files(self) -> None:
        lead_frame, labels, reference_frame, exposure_frame = _synthetic_round156_frames(
            implementation_locked=False,
        )
        prescreen_report = {
            "results": [{"factor_name": DEFAULT_LEAD_FACTOR_NAME, "horizon": 5, "research_lead": True}],
            "summary": {"research_lead_count": 1},
        }
        result = summarize_public_technical_failure_reversal_neutral_dedup(
            lead_frame,
            labels,
            reference_factor_frame=reference_frame[reference_frame["factor_name"] == "independent_public_reference"],
            exposure_frame=exposure_frame,
            prescreen_report=prescreen_report,
            min_cross_section=20,
            min_ic_observations=4,
            min_residual_icir=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_public_technical_failure_reversal_neutral_dedup(output, result)
            self.assertTrue((output / "public_technical_failure_reversal_neutral_dedup.json").exists())
            self.assertTrue((output / "public_technical_failure_reversal_neutral_dedup.md").exists())
            self.assertTrue((output / "public_technical_failure_reversal_reference_correlations.csv").exists())
            self.assertTrue((output / "public_technical_failure_reversal_residual_ic_observations.csv").exists())


if __name__ == "__main__":
    unittest.main()
