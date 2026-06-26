import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_lottery_extreme_upside_reversal_prescreen import (
    run_lottery_extreme_upside_reversal_prescreen_cli,
)


class LotteryExtremeUpsideReversalPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_round150_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output_dir = Path(tmp) / "reports"
            stock_basic = Path(tmp) / "stock_basic.csv"
            bars = _synthetic_bars(days=90, assets=35)
            DatasetStore(root).write_frame(
                bars,
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            _stock_basic(35).to_csv(stock_basic, index=False)

            result = run_lottery_extreme_upside_reversal_prescreen_cli(
                bars_roots=(root,),
                stock_basic_path=stock_basic,
                output_dir=output_dir,
                analysis_start_date="2024-01-01",
                analysis_end_date="2024-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
                min_industries=2,
                min_assets_per_industry=5,
            )

            self.assertEqual(result["stage"], "lottery_extreme_upside_reversal_prescreen")
            self.assertTrue((output_dir / "lottery_extreme_upside_reversal_prescreen.json").exists())
            self.assertTrue((output_dir / "lottery_extreme_upside_reversal_prescreen.md").exists())
            payload = json.loads((output_dir / "lottery_extreme_upside_reversal_prescreen.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["candidate_count"], 6)
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])
            self.assertFalse(payload["live_boundary_allowed"])


def _synthetic_bars(days: int = 90, assets: int = 35) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        asset_id = f"CN_XSHE_{asset_idx:06d}"
        price = 10.0 + asset_idx * 0.05
        for day_idx, date_value in enumerate(dates):
            burst = 0.09 if (day_idx + asset_idx) % 31 == 0 else 0.0
            price = max(1.0, price * (1.0 + ((day_idx % 11) - 5) * 0.0015 + burst))
            rows.append(
                {
                    "date": date_value,
                    "asset_id": asset_id,
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.02,
                    "low": price * 0.98,
                    "amount": 25_000_000.0 + asset_idx * 100_000.0,
                }
            )
    return pd.DataFrame(rows)


def _stock_basic(assets: int) -> pd.DataFrame:
    rows = []
    for asset_idx in range(assets):
        rows.append(
            {
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "symbol": f"{asset_idx:06d}.SZ",
                "market": "CN",
                "exchange": "XSHE",
                "industry": "Tech" if asset_idx < assets // 2 else "Bank",
                "name": f"Stock {asset_idx}",
                "list_date": "2020-01-01",
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
