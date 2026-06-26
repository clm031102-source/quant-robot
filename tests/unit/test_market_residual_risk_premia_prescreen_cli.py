import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_market_residual_risk_premia_prescreen import (
    run_market_residual_risk_premia_prescreen_cli,
)


class MarketResidualRiskPremiaPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_candidates_results_and_ic_csv(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            rows = []
            dates = pd.bdate_range("2025-01-02", periods=180)
            for asset_idx in range(45):
                asset_id = f"{asset_idx:06d}.SZ"
                price = 10.0 + asset_idx * 0.03
                for day_idx, date in enumerate(dates):
                    market_wave = ((day_idx % 19) - 9) * 0.0009
                    beta_load = 0.30 + (asset_idx % 7) * 0.09
                    idio = ((asset_idx + day_idx * 2) % 11 - 5) * 0.0005
                    price = max(1.0, price * (1.0 + beta_load * market_wave + idio))
                    rows.append(
                        {
                            "date": date,
                            "asset_id": asset_id,
                            "symbol": asset_id,
                            "market": "CN",
                            "adj_close": price,
                            "high": price * 1.015,
                            "low": price * 0.985,
                            "amount": 21_000_000 + asset_idx * 100_000,
                        }
                    )
            DatasetStore(root).write_frame(
                pd.DataFrame(rows),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_market_residual_risk_premia_prescreen_cli(
                bars_roots=[root],
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=10_000_000,
            )

            self.assertEqual(result["summary"]["candidate_count"], 10)
            self.assertTrue((output / "market_residual_risk_premia_prescreen.json").exists())
            self.assertTrue((output / "market_residual_risk_premia_prescreen.md").exists())
            self.assertTrue((output / "market_residual_risk_premia_candidates.csv").exists())
            self.assertTrue((output / "market_residual_risk_premia_results.csv").exists())
            self.assertTrue((output / "market_residual_risk_premia_ic_observations.csv").exists())
            payload = json.loads(
                (output / "market_residual_risk_premia_prescreen.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()

