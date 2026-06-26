import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_public_alpha101_capacity_safe_prescreen import (
    run_public_alpha101_capacity_safe_prescreen_cli,
)


class PublicAlpha101CapacitySafePrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_results_and_ic_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            rows = []
            dates = pd.bdate_range("2025-01-02", periods=100)
            for asset_idx in range(40):
                price = 10.0 + asset_idx * 0.03
                for day_idx, date in enumerate(dates):
                    open_price = price * (1.0 + ((day_idx % 9) - 4) * 0.0005)
                    close = open_price * (1.0 + (asset_idx % 5) * 0.0006)
                    high = max(open_price, close) * 1.01
                    low = min(open_price, close) * 0.99
                    volume = 900_000 + asset_idx * 20_000
                    amount = volume * close
                    rows.append(
                        {
                            "date": date,
                            "asset_id": f"CN_XSHE_{asset_idx:06d}",
                            "symbol": f"{asset_idx:06d}.SZ",
                            "market": "CN",
                            "open": open_price,
                            "high": high,
                            "low": low,
                            "close": close,
                            "adj_close": close,
                            "volume": volume,
                            "amount": amount,
                            "vwap": amount / volume,
                        }
                    )
                    price = close
            DatasetStore(root).write_frame(
                pd.DataFrame(rows),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_public_alpha101_capacity_safe_prescreen_cli(
                bars_roots=[root],
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
            )

            self.assertEqual(result["summary"]["candidate_count"], 10)
            self.assertTrue((output / "public_alpha101_capacity_safe_prescreen.json").exists())
            self.assertTrue((output / "public_alpha101_capacity_safe_prescreen.md").exists())
            self.assertTrue((output / "public_alpha101_capacity_safe_prescreen_results.csv").exists())
            self.assertTrue((output / "public_alpha101_capacity_safe_prescreen_ic_observations.csv").exists())
            payload = json.loads(
                (output / "public_alpha101_capacity_safe_prescreen.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
