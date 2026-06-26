import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.share_unlock_bottom_exclusion_overlay import (
    FACTOR_NAME,
    build_share_unlock_bottom_exclusion_overlay_audit,
    write_share_unlock_bottom_exclusion_overlay_audit,
)


class ShareUnlockBottomExclusionOverlayTests(unittest.TestCase):
    def test_unlock_pressure_can_be_a_bottom_exclusion_overlay(self) -> None:
        factors, labels = _unlock_factor_and_labels(bottom_return=-0.05, kept_return=0.01)

        audit = build_share_unlock_bottom_exclusion_overlay_audit(
            factor_frame=factors,
            label_frame=labels,
            min_dates=4,
            rebalance_interval=1,
            min_overlay_t_stat=2.0,
            min_positive_overlay_rate=0.75,
        )

        self.assertEqual(audit["stage"], "share_unlock_bottom_exclusion_overlay_audit")
        self.assertFalse(audit["promotion_policy"]["promotion_allowed"])
        self.assertFalse(audit["promotion_policy"]["portfolio_grid_allowed"])
        self.assertEqual(audit["summary"]["bottom_exclusion_candidate_factors"], 1)
        row = audit["factor_summary"][0]
        self.assertEqual(row["factor_name"], FACTOR_NAME)
        self.assertEqual(row["classification"], "bottom_exclusion_candidate")
        self.assertAlmostEqual(row["mean_overlay_excess_return"], 0.012)

    def test_writer_emits_overlay_artifacts(self) -> None:
        factors, labels = _unlock_factor_and_labels(bottom_return=-0.05, kept_return=0.01)
        audit = build_share_unlock_bottom_exclusion_overlay_audit(
            factor_frame=factors,
            label_frame=labels,
            rebalance_interval=1,
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_share_unlock_bottom_exclusion_overlay_audit(tmp, audit)

            self.assertTrue((Path(tmp) / "share_unlock_bottom_exclusion_overlay_audit.json").exists())
            self.assertTrue((Path(tmp) / "share_unlock_bottom_exclusion_overlay_audit.md").exists())
            self.assertTrue((Path(tmp) / "date_audits.csv").exists())
            self.assertTrue((Path(tmp) / "factor_summary.csv").exists())


def _unlock_factor_and_labels(*, bottom_return: float, kept_return: float):
    factor_rows = []
    label_rows = []
    for day in pd.date_range("2024-01-02", periods=8, freq="D"):
        for asset_index in range(5):
            asset_id = f"asset_{asset_index}"
            factor_value = float(asset_index + 1)
            forward_return = bottom_return if asset_index == 0 else kept_return
            factor_rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": FACTOR_NAME,
                    "factor_value": factor_value,
                }
            )
            label_rows.append(
                {
                    "date": day,
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
