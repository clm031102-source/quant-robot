import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_negative_ic_trend_accumulation_lead_dedup import (
    run_negative_ic_trend_accumulation_lead_dedup_cli,
)


def _synthetic_bars(days: int = 110, assets: int = 42) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        price = 9.0 + asset_idx * 0.03
        for day_idx, signal_date in enumerate(dates):
            price = max(1.0, price * (1.0 + ((day_idx % 13) - 6) * 0.0009 + (asset_idx % 6) * 0.0005))
            rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.012,
                    "low": price * 0.988,
                    "amount": 18_000_000 + asset_idx * 100_000 + (day_idx % 5) * 60_000,
                }
            )
    return pd.DataFrame(rows)


class NegativeIcTrendAccumulationLeadDedupCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_audit_csvs(self) -> None:
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
                                "factor_name": "overheat_avoidance_relative_strength_60",
                                "horizon": 20,
                                "research_lead": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_negative_ic_trend_accumulation_lead_dedup_cli(
                bars_roots=[root],
                prescreen_report=prescreen_path,
                output_dir=output,
                analysis_end_date="2025-12-31",
                sample_every_n_dates=2,
                min_cross_section=20,
            )

            self.assertEqual(result["stage"], "negative_ic_trend_accumulation_lead_dedup")
            self.assertTrue((output / "negative_ic_trend_accumulation_lead_dedup.json").exists())
            self.assertTrue((output / "negative_ic_trend_accumulation_lead_dedup.md").exists())
            self.assertTrue((output / "negative_ic_trend_accumulation_lead_correlations.csv").exists())
            self.assertTrue((output / "negative_ic_trend_accumulation_lead_correlation_observations.csv").exists())
            self.assertTrue((output / "negative_ic_trend_accumulation_lead_capacity_observations.csv").exists())
            payload = json.loads((output / "negative_ic_trend_accumulation_lead_dedup.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
