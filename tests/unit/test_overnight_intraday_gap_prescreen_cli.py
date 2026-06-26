import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_overnight_intraday_gap_prescreen import run_overnight_intraday_gap_prescreen_cli


def _synthetic_bars(days: int = 90, assets: int = 45, *, include_holdout: bool = False) -> pd.DataFrame:
    dates = pd.bdate_range("2025-01-02", periods=days)
    if include_holdout:
        dates = dates.append(pd.bdate_range("2026-01-02", periods=10))
    rows = []
    for asset_idx in range(assets):
        asset_id = f"{asset_idx:06d}.SZ"
        close = 10.0 + asset_idx * 0.03
        for day_idx, date in enumerate(dates):
            overnight = ((asset_idx % 7) - 3) * 0.001
            intraday = ((day_idx % 11) - 5) * 0.0004
            open_price = max(1.0, close * (1.0 + overnight))
            close = max(1.0, open_price * (1.0 + intraday))
            rows.append(
                {
                    "date": date,
                    "asset_id": asset_id,
                    "symbol": asset_id,
                    "market": "CN",
                    "open": open_price,
                    "high": max(open_price, close) * 1.01,
                    "low": min(open_price, close) * 0.99,
                    "close": close,
                    "adj_close": close,
                    "amount": 20_000_000.0 + asset_idx * 100_000.0,
                    "volume": 1_000_000.0 + asset_idx * 1_000.0,
                }
            )
    return pd.DataFrame(rows)


class OvernightIntradayGapPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_reports_and_excludes_final_holdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output_dir = Path(tmp) / "reports"
            bars = _synthetic_bars(include_holdout=True)
            store = DatasetStore(root)
            store.write_frame(
                bars[bars["date"].dt.year == 2025],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                bars[bars["date"].dt.year == 2026],
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2026"},
            )

            result = run_overnight_intraday_gap_prescreen_cli(
                bars_roots=[root],
                output_dir=output_dir,
                analysis_end_date="2025-12-31",
                include_final_holdout=False,
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

            self.assertEqual(result["stage"], "overnight_intraday_gap_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 10)
            self.assertFalse(result["holdout_policy"]["final_holdout_included"])
            self.assertLessEqual(result["data_window"]["max_signal_date"], "2025-12-31")
            self.assertTrue((output_dir / "overnight_intraday_gap_prescreen.json").exists())
            self.assertTrue((output_dir / "overnight_intraday_gap_prescreen.md").exists())
            self.assertTrue((output_dir / "overnight_intraday_gap_candidates.csv").exists())
            self.assertTrue((output_dir / "overnight_intraday_gap_results.csv").exists())
            self.assertTrue((output_dir / "overnight_intraday_gap_ic_observations.csv").exists())
            payload = json.loads((output_dir / "overnight_intraday_gap_prescreen.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["stage"], "overnight_intraday_gap_prescreen")


if __name__ == "__main__":
    unittest.main()
