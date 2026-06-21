import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.bottom_exclusion_overlay_audit import (
    build_bottom_exclusion_overlay_audit,
    render_bottom_exclusion_overlay_markdown,
    write_bottom_exclusion_overlay_audit,
)


class BottomExclusionOverlayAuditTests(unittest.TestCase):
    def test_classifies_factor_as_bottom_exclusion_candidate_when_bottom_bucket_drags_returns(self):
        factors, labels = _bottom_drag_inputs()

        audit = build_bottom_exclusion_overlay_audit(
            factors,
            labels,
            source_report="synthetic_bottom_drag",
            bottom_quantile=0.2,
            min_dates=4,
            min_overlay_t_stat=2.0,
            min_positive_overlay_rate=0.75,
        )

        self.assertEqual(audit["summary"]["factors"], 1)
        self.assertEqual(audit["summary"]["bottom_exclusion_candidate_factors"], 1)
        self.assertIn("test_bottom_exclusion_as_risk_filter_in_portfolio", audit["recommended_next_actions"])

        row = audit["factor_summary"][0]
        self.assertEqual(row["factor_name"], "known_tail_risk_factor")
        self.assertEqual(row["classification"], "bottom_exclusion_candidate")
        self.assertAlmostEqual(row["mean_full_return"], -0.002)
        self.assertAlmostEqual(row["mean_kept_return"], 0.01)
        self.assertAlmostEqual(row["mean_bottom_return"], -0.05)
        self.assertAlmostEqual(row["mean_overlay_excess_return"], 0.012)
        self.assertEqual(row["positive_overlay_rate"], 1.0)

    def test_rejects_factor_when_bottom_bucket_does_not_underperform(self):
        factors, labels = _bottom_leads_inputs()

        audit = build_bottom_exclusion_overlay_audit(
            factors,
            labels,
            source_report="synthetic_bottom_leads",
            bottom_quantile=0.2,
            min_dates=4,
        )

        self.assertEqual(audit["summary"]["bottom_exclusion_candidate_factors"], 0)
        self.assertEqual(audit["summary"]["weak_or_unproven_exclusion_factors"], 1)
        self.assertIn("rotate_factor_family_with_public_hypothesis", audit["recommended_next_actions"])

        row = audit["factor_summary"][0]
        self.assertEqual(row["classification"], "weak_or_unproven_exclusion")
        self.assertLess(row["mean_overlay_excess_return"], 0.0)

    def test_writer_emits_json_markdown_and_csvs(self):
        factors, labels = _bottom_drag_inputs()
        audit = build_bottom_exclusion_overlay_audit(factors, labels, source_report="synthetic")

        markdown = render_bottom_exclusion_overlay_markdown(audit)

        self.assertIn("Bottom-Exclusion Overlay Audit", markdown)
        self.assertIn("bottom_exclusion_candidate", markdown)
        with tempfile.TemporaryDirectory() as tmp:
            write_bottom_exclusion_overlay_audit(tmp, audit)

            self.assertTrue((Path(tmp) / "bottom_exclusion_overlay_audit.json").exists())
            self.assertTrue((Path(tmp) / "bottom_exclusion_overlay_audit.md").exists())
            self.assertTrue((Path(tmp) / "date_audits.csv").exists())
            self.assertTrue((Path(tmp) / "factor_summary.csv").exists())

    def test_rebalance_interval_samples_signal_dates_before_overlay_summary(self):
        factors, labels = _bottom_drag_inputs()

        audit = build_bottom_exclusion_overlay_audit(
            factors,
            labels,
            source_report="synthetic_rebalance_interval",
            rebalance_interval=2,
            min_dates=4,
        )

        self.assertEqual(audit["summary"]["date_factor_rows"], 4)
        self.assertEqual(audit["factor_summary"][0]["dates"], 4)


def _bottom_drag_inputs():
    return _inputs(bottom_return=-0.05, kept_return=0.01)


def _bottom_leads_inputs():
    return _inputs(bottom_return=0.05, kept_return=0.0)


def _inputs(*, bottom_return: float, kept_return: float):
    factor_rows = []
    label_rows = []
    for day in pd.date_range("2024-01-02", periods=8, freq="D"):
        for asset_index in range(5):
            asset_id = f"asset_{asset_index}"
            factor_value = float(asset_index + 1)
            forward_return = bottom_return if asset_index == 0 else kept_return
            factor_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "known_tail_risk_factor",
                    "factor_value": factor_value,
                }
            )
            label_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 20,
                    "execution_lag": 1,
                    "forward_return": forward_return,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows)


if __name__ == "__main__":
    unittest.main()
