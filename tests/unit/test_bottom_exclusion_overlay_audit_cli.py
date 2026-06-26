import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_bottom_exclusion_overlay_audit import run_bottom_exclusion_overlay_audit


class BottomExclusionOverlayAuditCliTests(unittest.TestCase):
    def test_run_bottom_exclusion_overlay_audit_accepts_factor_and_label_files(self):
        factors, labels = _inputs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factors_path = root / "factors.csv"
            labels_path = root / "labels.csv"
            output_dir = root / "audit"
            factors.to_csv(factors_path, index=False)
            labels.to_csv(labels_path, index=False)

            audit = run_bottom_exclusion_overlay_audit(
                factors=factors_path,
                labels=labels_path,
                output_dir=output_dir,
                bottom_quantile=0.2,
                min_dates=4,
            )

            self.assertEqual(audit["summary"]["bottom_exclusion_candidate_factors"], 1)
            self.assertTrue((output_dir / "bottom_exclusion_overlay_audit.json").exists())
            self.assertTrue((output_dir / "factor_summary.csv").exists())


def _inputs():
    factor_rows = []
    label_rows = []
    for day in pd.date_range("2024-01-02", periods=6, freq="D"):
        for asset_index in range(5):
            asset_id = f"asset_{asset_index}"
            factor_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "tail_filter",
                    "factor_value": float(asset_index + 1),
                }
            )
            label_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 20,
                    "execution_lag": 1,
                    "forward_return": -0.05 if asset_index == 0 else 0.01,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows)


if __name__ == "__main__":
    unittest.main()
