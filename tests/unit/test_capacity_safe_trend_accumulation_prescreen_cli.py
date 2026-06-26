import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_capacity_safe_trend_accumulation_prescreen import (
    run_capacity_safe_trend_accumulation_prescreen_cli,
)


class CapacitySafeTrendAccumulationPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_result_csv_and_ic_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            rows = []
            dates = pd.bdate_range("2025-01-02", periods=100)
            for asset_idx in range(42):
                price = 9.0 + asset_idx * 0.03
                for day_idx, signal_date in enumerate(dates):
                    price = price * (1.0 + ((day_idx % 13) - 6) * 0.0009 + (asset_idx % 6) * 0.0005)
                    rows.append(
                        {
                            "date": signal_date,
                            "asset_id": f"{asset_idx:06d}.SZ",
                            "symbol": f"{asset_idx:06d}.SZ",
                            "market": "CN",
                            "adj_close": price,
                            "high": price * 1.012,
                            "low": price * 0.988,
                            "amount": 18_000_000 + asset_idx * 100_000 + (day_idx % 5) * 60_000,
                        }
                    )
            DatasetStore(root).write_frame(
                pd.DataFrame(rows),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_capacity_safe_trend_accumulation_prescreen_cli(
                bars_roots=[root],
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

            self.assertEqual(result["stage"], "capacity_safe_trend_accumulation_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 10)
            self.assertTrue((output / "capacity_safe_trend_accumulation_prescreen.json").exists())
            self.assertTrue((output / "capacity_safe_trend_accumulation_prescreen.md").exists())
            self.assertTrue((output / "capacity_safe_trend_accumulation_prescreen_results.csv").exists())
            self.assertTrue((output / "capacity_safe_trend_accumulation_prescreen_ic_observations.csv").exists())
            payload = json.loads(
                (output / "capacity_safe_trend_accumulation_prescreen.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
