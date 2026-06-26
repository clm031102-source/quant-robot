import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_public_alpha101_reference_exposure_dedup import (
    run_public_alpha101_reference_exposure_dedup_cli,
)


class PublicAlpha101ReferenceExposureDedupCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_and_audit_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            prescreen = Path(tmp) / "prescreen.json"
            rows = []
            dates = pd.bdate_range("2025-01-02", periods=170)
            for asset_idx in range(45):
                price = 10.0 + asset_idx * 0.03
                for day_idx, date in enumerate(dates):
                    open_price = price * (1.0 + ((day_idx % 9) - 4) * 0.0005)
                    close = open_price * (1.0 + (asset_idx % 5) * 0.0006)
                    high = max(open_price, close) * 1.01
                    low = min(open_price, close) * 0.99
                    volume = 1_000_000 + asset_idx * 20_000
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
            prescreen.write_text(
                json.dumps(
                    {
                        "results": [
                            {
                                "factor_name": "qlib_alpha158_return_std_position_blend_20",
                                "horizon": 5,
                                "research_lead": True,
                            }
                        ],
                        "summary": {"research_lead_count": 1},
                    }
                ),
                encoding="utf-8",
            )

            result = run_public_alpha101_reference_exposure_dedup_cli(
                bars_roots=[root],
                prescreen_report=prescreen,
                output_dir=output,
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-12-31",
                horizon=5,
                sample_every_n_dates=5,
                min_cross_section=20,
                min_ic_observations=4,
                min_signal_date_amount=1_000_000,
            )

            self.assertEqual(result["stage"], "public_alpha101_reference_exposure_dedup")
            self.assertTrue((output / "public_alpha101_reference_exposure_dedup.json").exists())
            self.assertTrue((output / "public_alpha101_reference_exposure_dedup.md").exists())
            self.assertTrue((output / "public_alpha101_reference_correlations.csv").exists())
            self.assertTrue((output / "public_alpha101_exposure_correlations.csv").exists())
            payload = json.loads((output / "public_alpha101_reference_exposure_dedup.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["lead_factor_name"], "qlib_alpha158_return_std_position_blend_20")
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])


if __name__ == "__main__":
    unittest.main()
