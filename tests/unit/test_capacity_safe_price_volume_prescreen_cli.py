import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_capacity_safe_price_volume_prescreen import (
    run_capacity_safe_price_volume_prescreen_cli,
)


class CapacitySafePriceVolumePrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_result_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            rows = []
            dates = pd.bdate_range("2025-01-02", periods=90)
            for asset_idx in range(40):
                price = 10.0 + asset_idx * 0.02
                for day_idx, date in enumerate(dates):
                    price = price * (1.0 + ((day_idx % 11) - 5) * 0.001 + (asset_idx % 4) * 0.0007)
                    rows.append(
                        {
                            "date": date,
                            "asset_id": f"{asset_idx:06d}.SZ",
                            "symbol": f"{asset_idx:06d}.SZ",
                            "market": "CN",
                            "adj_close": price,
                            "high": price * 1.01,
                            "low": price * 0.99,
                            "amount": 20_000_000 + asset_idx * 100_000,
                        }
                    )
            DatasetStore(root).write_frame(
                pd.DataFrame(rows),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_capacity_safe_price_volume_prescreen_cli(
                bars_roots=[root],
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

            self.assertEqual(result["summary"]["candidate_count"], 10)
            self.assertTrue((output / "capacity_safe_price_volume_prescreen.json").exists())
            self.assertTrue((output / "capacity_safe_price_volume_prescreen.md").exists())
            self.assertTrue((output / "capacity_safe_price_volume_prescreen_results.csv").exists())
            payload = json.loads(
                (output / "capacity_safe_price_volume_prescreen.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
