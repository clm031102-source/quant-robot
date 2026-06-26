import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_turnover_repair_dedup_sensitivity import (
    run_turnover_repair_dedup_sensitivity_cli,
)


class TurnoverRepairDedupSensitivityCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_csv_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "round124.csv"
            output_dir = root / "output"
            pd.DataFrame(
                [
                    {
                        "factor_name": "turnover_rate_f_low_participation_budget_100k_20",
                        "horizon": 20,
                        "mean_spearman_ic": 0.1033,
                        "icir": 0.6485,
                        "ic_t_stat": 33.35,
                        "ic_positive_rate": 0.753,
                        "quantile_spread": 0.0673,
                        "quantile_monotonicity": 0.9,
                        "avg_top_quantile_turnover": 0.278,
                        "max_estimated_participation": 0.0001,
                        "median_estimated_participation": 0.000015,
                        "extreme_forward_return_rate": 0.0203,
                        "raw_factor_spearman_corr": 1.0,
                        "capacity_clean": True,
                        "research_lead": True,
                        "blockers": "promotion_requires_later_walk_forward_cost_capacity_regime_gates",
                    }
                ]
            ).to_csv(input_path, index=False)

            result = run_turnover_repair_dedup_sensitivity_cli(
                round124_results=input_path,
                output_dir=output_dir,
                capital_grid=[100_000, 500_000],
            )

            self.assertEqual(result["stage"], "turnover_repair_dedup_sensitivity")
            self.assertTrue((output_dir / "turnover_repair_dedup_sensitivity.json").exists())
            self.assertTrue((output_dir / "turnover_repair_dedup_sensitivity.md").exists())
            self.assertTrue((output_dir / "turnover_repair_dedup_rows.csv").exists())
            self.assertTrue((output_dir / "turnover_repair_capital_sensitivity.csv").exists())
            payload = json.loads(
                (output_dir / "turnover_repair_dedup_sensitivity.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["input_research_lead_rows"], 1)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
