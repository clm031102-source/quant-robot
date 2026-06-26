import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_factor_statistical_reality_check import run_factor_statistical_reality_check


class FactorStatisticalRealityCheckCliTests(unittest.TestCase):
    def test_cli_writes_reality_check_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiments_path = root / "experiments.csv"
            output_dir = root / "report"
            pd.DataFrame(
                [
                    {
                        "case_id": "case_a",
                        "factor_name": "quality_value",
                        "date": "2024-01-01",
                        "test_overlap_autocorr_adjusted_sharpe": 1.1,
                        "test_overlap_effective_sample_size": 180,
                        "p_value": 0.002,
                        "lookback": 20,
                        "top_n": 50,
                    },
                    {
                        "case_id": "case_b",
                        "factor_name": "quality_value",
                        "date": "2024-01-02",
                        "test_overlap_autocorr_adjusted_sharpe": 0.9,
                        "test_overlap_effective_sample_size": 180,
                        "p_value": 0.01,
                        "lookback": 40,
                        "top_n": 50,
                    },
                ]
            ).to_csv(experiments_path, index=False)

            report = run_factor_statistical_reality_check(
                experiments_path=experiments_path,
                output_dir=output_dir,
                date_column="date",
                x_param="lookback",
                y_param="top_n",
                sensitivity_metric="test_overlap_autocorr_adjusted_sharpe",
                cpcv_groups=2,
                cpcv_test_group_count=1,
                min_deflated_sharpe_probability=0.5,
            )

            self.assertEqual(report["summary"]["rows"], 2)
            self.assertTrue((output_dir / "factor_statistical_reality_check.json").exists())
            self.assertTrue((output_dir / "factor_statistical_reality_check.md").exists())
            self.assertTrue((output_dir / "factor_statistical_reality_check_rows.csv").exists())
            payload = json.loads(
                (output_dir / "factor_statistical_reality_check.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["cpcv_split_count"], 2)


if __name__ == "__main__":
    unittest.main()
