import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_capacity_safe_price_volume_lead_dedup import (
    run_capacity_safe_price_volume_lead_dedup_cli,
)


def _synthetic_bars(days: int = 90, assets: int = 40) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 10.0 + asset_idx * 0.03
        for day_idx, date in enumerate(dates):
            price = max(1.0, price * (1.0 + ((day_idx % 13) - 6) * 0.001 + (asset_idx % 5) * 0.0006))
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.015,
                    "low": price * 0.985,
                    "amount": 20_000_000 + asset_idx * 100_000,
                }
            )
    return pd.DataFrame(rows)


class CapacitySafePriceVolumeLeadDedupCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_correlation_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            prescreen_path = Path(tmp) / "prescreen.json"
            DatasetStore(root).write_frame(
                _synthetic_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            prescreen_path.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "factor_name": "bollinger_reversal_lowvol_liquid_20",
                                "horizon": 20,
                                "research_lead": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_capacity_safe_price_volume_lead_dedup_cli(
                bars_roots=[root],
                prescreen_report=prescreen_path,
                output_dir=output,
                analysis_end_date="2025-12-31",
                sample_every_n_dates=2,
                min_cross_section=20,
            )

            self.assertEqual(result["stage"], "capacity_safe_price_volume_lead_dedup")
            self.assertTrue((output / "capacity_safe_price_volume_lead_dedup.json").exists())
            self.assertTrue((output / "capacity_safe_price_volume_lead_dedup.md").exists())
            self.assertTrue((output / "capacity_safe_price_volume_lead_correlations.csv").exists())
            payload = json.loads((output / "capacity_safe_price_volume_lead_dedup.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
