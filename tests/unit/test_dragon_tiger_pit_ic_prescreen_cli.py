import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_dragon_tiger_pit_ic_prescreen import run_dragon_tiger_pit_ic_prescreen_cli
from quant_robot.storage.dataset_store import DatasetStore


class DragonTigerPitIcPrescreenCliTests(unittest.TestCase):
    def test_cli_loads_processed_stock_day_and_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed_root = root / "dragon_tiger"
            bars_root = root / "bars"
            stock_basic_root = root / "stock_basic"
            output_dir = root / "out"
            stock_day = _dragon_tiger_stock_day(assets=8, event_dates=pd.bdate_range("2024-01-02", periods=5))
            DatasetStore(processed_root).write_frame(
                stock_day,
                "processed/dragon_tiger_stock_day",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            DatasetStore(bars_root).write_frame(
                _bars(assets=8, days=12),
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            _write_stock_basic(stock_basic_root, assets=8)

            result = run_dragon_tiger_pit_ic_prescreen_cli(
                processed_root=processed_root,
                bars_roots=[bars_root],
                stock_basic_path=stock_basic_root,
                output_dir=output_dir,
                analysis_start_date="2024-01-01",
                analysis_end_date="2024-01-31",
                horizons=[1],
                execution_lag=0,
                min_cross_section=8,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
                allow_not_ready=True,
            )

            self.assertEqual(result["stage"], "dragon_tiger_pit_event_ic_prescreen")
            self.assertEqual(result["summary"]["candidate_count"], 5)
            self.assertTrue((output_dir / "dragon_tiger_pit_ic_prescreen.json").exists())
            self.assertTrue((output_dir / "dragon_tiger_pit_ic_prescreen.md").exists())


def _dragon_tiger_stock_day(assets: int, event_dates: pd.DatetimeIndex) -> pd.DataFrame:
    rows = []
    for event_date in event_dates:
        for asset_idx in range(assets):
            rows.append(
                {
                    "date": event_date,
                    "available_date": event_date + pd.offsets.BDay(1),
                    "asset_id": f"CN_XSHE_{asset_idx:06d}",
                    "symbol": f"{asset_idx:06d}.SZ",
                    "market": "CN",
                    "source": "fixture",
                    "top_list_event_count": 1.0,
                    "top_list_reason_count": 1.0,
                    "top_list_amount_sum": 100_000_000.0 + asset_idx,
                    "top_list_net_amount_sum": (asset_idx - 4) * 1_000_000.0,
                    "top_list_abs_pct_change_max": 3.0 + asset_idx,
                    "top_list_amount_rate_max": 5.0 + asset_idx,
                    "top_inst_event_count": 1.0,
                    "top_inst_reason_count": 1.0,
                    "top_inst_buy_sum": 30_000_000.0 + asset_idx,
                    "top_inst_sell_sum": 20_000_000.0 + asset_idx,
                    "top_inst_net_buy_sum": 10_000_000.0 + asset_idx,
                    "top_inst_abs_net_buy_sum": 10_000_000.0 + asset_idx,
                }
            )
    return pd.DataFrame(rows)


def _bars(assets: int, days: int) -> pd.DataFrame:
    dates = pd.bdate_range("2024-01-02", periods=days)
    rows = []
    for asset_idx in range(assets):
        price = 10.0 + asset_idx
        for day_idx, date_value in enumerate(dates):
            price += 0.01 + asset_idx * 0.001
            rows.append(
                {
                    "date": date_value,
                    "asset_id": f"CN_XSHE_{asset_idx:06d}",
                    "market": "CN",
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "amount": 30_000_000.0 + asset_idx * 1_000_000.0 + day_idx,
                }
            )
    return pd.DataFrame(rows)


def _write_stock_basic(root: Path, assets: int) -> None:
    root.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        [
            {
                "asset_id": f"CN_XSHE_{asset_idx:06d}",
                "symbol": f"{asset_idx:06d}.SZ",
                "market": "CN",
                "industry": "Tech" if asset_idx < assets // 2 else "Bank",
            }
            for asset_idx in range(assets)
        ]
    ).to_csv(root / "stock_basic.csv", index=False)


if __name__ == "__main__":
    unittest.main()
