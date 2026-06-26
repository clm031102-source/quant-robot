import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_market_residual_lead_exposure_dedup import (
    run_market_residual_lead_exposure_dedup_cli,
)


class MarketResidualLeadExposureDedupCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_audit_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            rows = []
            dates = pd.bdate_range("2025-01-02", periods=220)
            for asset_idx in range(45):
                asset_id = f"{asset_idx:06d}.SZ"
                price = 10.0 + asset_idx * 0.03
                for day_idx, signal_date in enumerate(dates):
                    market_wave = ((day_idx % 19) - 9) * 0.0009
                    beta_load = 0.30 + (asset_idx % 7) * 0.09
                    idio = ((asset_idx + day_idx * 2) % 11 - 5) * 0.0005
                    price = max(1.0, price * (1.0 + beta_load * market_wave + idio))
                    rows.append(
                        {
                            "date": signal_date,
                            "asset_id": asset_id,
                            "symbol": asset_id,
                            "market": "CN",
                            "adj_close": price,
                            "high": price * (1.01 + (asset_idx % 5) * 0.001),
                            "low": price * 0.985,
                            "amount": 25_000_000 + asset_idx * 100_000,
                        }
                    )
            DatasetStore(root).write_frame(
                pd.DataFrame(rows),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            prescreen_report = Path(tmp) / "prescreen.json"
            prescreen_report.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "factor_name": "beta_adjusted_range_contraction_60",
                                "horizon": 20,
                                "research_lead": True,
                            }
                        ],
                        "summary": {"research_lead_count": 1},
                    }
                ),
                encoding="utf-8",
            )

            result = run_market_residual_lead_exposure_dedup_cli(
                bars_roots=[root],
                prescreen_report=prescreen_report,
                output_dir=output,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
                horizon=20,
                execution_lag=1,
                sample_every_n_dates=5,
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=10_000_000,
            )

            self.assertEqual(result["stage"], "market_residual_lead_exposure_dedup")
            self.assertTrue((output / "market_residual_lead_exposure_dedup.json").exists())
            self.assertTrue((output / "market_residual_lead_exposure_dedup.md").exists())
            self.assertTrue((output / "market_residual_lead_reference_correlations.csv").exists())
            self.assertTrue((output / "market_residual_lead_exposure_correlations.csv").exists())
            self.assertTrue((output / "market_residual_lead_yearly_ic.csv").exists())
            self.assertTrue((output / "market_residual_lead_monthly_ic.csv").exists())
            self.assertTrue((output / "market_residual_lead_ic_observations.csv").exists())
            payload = json.loads(
                (output / "market_residual_lead_exposure_dedup.json").read_text(encoding="utf-8")
            )
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
