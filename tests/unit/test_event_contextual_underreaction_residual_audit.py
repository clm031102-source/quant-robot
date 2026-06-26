import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.event_contextual_underreaction_residual_audit import (
    NEXT_HIBERNATE_OR_ROTATE_DIRECTION,
    NEXT_RESIDUAL_WALK_FORWARD_PREFLIGHT_DIRECTION,
    summarize_event_contextual_underreaction_residual_audit,
    write_event_contextual_underreaction_residual_audit,
)


class EventContextualUnderreactionResidualAuditTests(unittest.TestCase):
    def test_blocks_lead_when_high_reference_explains_all_signal_variance(self) -> None:
        factor_frame, labels, reference_frame, report = _frames(independent_residual=False)

        result = summarize_event_contextual_underreaction_residual_audit(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            reference_dedup_report=report,
            min_cross_section=30,
            min_ic_observations=5,
        )

        lead = result["lead_results"][0]
        self.assertEqual(result["stage"], "event_contextual_underreaction_residual_audit")
        self.assertEqual(result["summary"]["residual_pass_count"], 0)
        self.assertEqual(lead["next_direction"], NEXT_HIBERNATE_OR_ROTATE_DIRECTION)
        self.assertIn("residual_signal_variance_too_low", lead["gate"]["blockers"])
        self.assertFalse(lead["promotion_policy"]["promotion_allowed"])

    def test_allows_lead_when_independent_residual_ic_survives_reference_regression(self) -> None:
        factor_frame, labels, reference_frame, report = _frames(independent_residual=True)

        result = summarize_event_contextual_underreaction_residual_audit(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            reference_dedup_report=report,
            min_cross_section=30,
            min_ic_observations=5,
            min_residual_icir=0.0,
            min_residual_t_stat=0.0,
        )

        lead = result["lead_results"][0]
        self.assertEqual(lead["gate"]["blockers"], [])
        self.assertGreater(lead["residual_ic_summary"]["mean_spearman_ic"], 0.50)
        self.assertEqual(lead["next_direction"], NEXT_RESIDUAL_WALK_FORWARD_PREFLIGHT_DIRECTION)
        self.assertEqual(result["summary"]["residual_pass_count"], 1)
        self.assertEqual(result["next_direction"], NEXT_RESIDUAL_WALK_FORWARD_PREFLIGHT_DIRECTION)

    def test_write_outputs_residual_audit_artifacts(self) -> None:
        factor_frame, labels, reference_frame, report = _frames(independent_residual=True)
        result = summarize_event_contextual_underreaction_residual_audit(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            reference_dedup_report=report,
            min_cross_section=30,
            min_ic_observations=5,
            min_residual_icir=0.0,
            min_residual_t_stat=0.0,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_event_contextual_underreaction_residual_audit(output_dir, result)
            self.assertTrue((output_dir / "event_contextual_underreaction_residual_audit.json").exists())
            self.assertTrue((output_dir / "event_contextual_underreaction_residual_audit.md").exists())
            self.assertTrue((output_dir / "event_contextual_underreaction_residual_ic_observations.csv").exists())
            self.assertTrue((output_dir / "event_contextual_underreaction_residual_diagnostics.csv").exists())


def _frames(*, independent_residual: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    dates = pd.bdate_range("2024-01-02", periods=8)
    factor_rows = []
    label_rows = []
    reference_rows = []
    for date_idx, signal_date in enumerate(dates):
        for asset_idx in range(36):
            asset_id = f"CN_XSHE_{asset_idx:06d}"
            reference_value = float(asset_idx)
            residual_component = float(((asset_idx * 11 + date_idx * 3) % 36) - 18)
            lead_value = reference_value + (0.05 * residual_component if independent_residual else 0.0)
            forward_return = (residual_component if independent_residual else lead_value) * 0.001
            factor_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "event_holder_contraction_low_vol_20",
                    "factor_value": lead_value,
                    "adv20_amount": 50_000_000.0 + asset_idx,
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
                    "factor_name": "raw_event_holder_number_contraction_2q",
                    "factor_value": reference_value,
                }
            )
    report = {
        "lead_results": [
            {
                "lead_factor_name": "event_holder_contraction_low_vol_20",
                "horizon": 20,
                "reference_correlations": [
                    {
                        "factor_name": "raw_event_holder_number_contraction_2q",
                        "correlation_observations": 8,
                        "mean_abs_correlation": 0.99,
                        "max_abs_correlation": 1.0,
                        "redundancy_class": "highly_redundant",
                    }
                ],
                "gate": {"blockers": ["lead_highly_redundant_with_reference_factor"]},
            }
        ],
        "summary": {"lead_count": 1, "dedup_pass_count": 0},
    }
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows), report


if __name__ == "__main__":
    unittest.main()
