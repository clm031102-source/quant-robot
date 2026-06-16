import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.archive_replay import replay_tushare_archive_to_processed
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_tushare_archive_replay import run_archive_replay_cli


class TushareArchiveReplayTests(unittest.TestCase):
    def test_replay_tushare_archive_writes_processed_bars_and_moneyflow_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            daily_archive = root / "daily_archive"
            moneyflow_archive = root / "moneyflow_archive"
            output_dir = root / "processed_replay"
            _write_daily_raw_archive(daily_archive)
            _write_moneyflow_raw_archive(moneyflow_archive)

            result = replay_tushare_archive_to_processed(
                daily_roots=[daily_archive],
                moneyflow_roots=[moneyflow_archive],
                output_dir=output_dir,
                market="CN",
            )

            self.assertEqual(result["daily"]["raw_rows"], 2)
            self.assertEqual(result["daily"]["processed_rows"], 2)
            self.assertEqual(result["moneyflow"]["raw_rows"], 2)
            self.assertEqual(result["moneyflow"]["processed_rows"], 2)
            bars = DatasetStore(output_dir).read_frame(
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            moneyflow = DatasetStore(output_dir).read_frame(
                "processed/moneyflow_inputs",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            self.assertEqual(set(bars["asset_id"]), {"CN_XSHE_000001", "CN_XSHG_600519"})
            self.assertEqual(set(moneyflow["asset_id"]), {"CN_XSHE_000001", "CN_XSHG_600519"})
            manifest = json.loads((output_dir / "archive_replay_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["market"], "CN")

    def test_archive_replay_cli_helper_accepts_semicolon_separated_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            daily_archive = root / "daily_archive"
            moneyflow_archive = root / "moneyflow_archive"
            output_dir = root / "processed_replay"
            _write_daily_raw_archive(daily_archive)
            _write_moneyflow_raw_archive(moneyflow_archive)

            result = run_archive_replay_cli(
                daily_roots=str(daily_archive),
                moneyflow_roots=str(moneyflow_archive),
                output_dir=output_dir,
                market="CN",
            )

            self.assertEqual(result["daily"]["processed_rows"], 2)
            self.assertEqual(result["moneyflow"]["processed_rows"], 2)


def _write_daily_raw_archive(root: Path) -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["000001.SZ", "600519.SH"],
            "date": [pd.Timestamp("2024-01-02").date()] * 2,
            "open": [10.0, 20.0],
            "high": [11.0, 21.0],
            "low": [9.0, 19.0],
            "close": [10.5, 20.5],
            "volume": [1000.0, 2000.0],
            "amount": [10500.0, 41000.0],
        }
    )
    DatasetStore(root).write_frame(frame, "raw/tushare/daily", {"trade_date": "20240102"})


def _write_moneyflow_raw_archive(root: Path) -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["000001.SZ", "600519.SH"],
            "date": [pd.Timestamp("2024-01-02").date()] * 2,
            "buy_sm_vol": [10.0, 11.0],
            "buy_sm_amount": [100.0, 110.0],
            "sell_sm_vol": [8.0, 9.0],
            "sell_sm_amount": [80.0, 90.0],
            "buy_md_vol": [30.0, 31.0],
            "buy_md_amount": [300.0, 310.0],
            "sell_md_vol": [25.0, 26.0],
            "sell_md_amount": [250.0, 260.0],
            "buy_lg_vol": [50.0, 51.0],
            "buy_lg_amount": [500.0, 510.0],
            "sell_lg_vol": [45.0, 46.0],
            "sell_lg_amount": [450.0, 460.0],
            "buy_elg_vol": [70.0, 71.0],
            "buy_elg_amount": [700.0, 710.0],
            "sell_elg_vol": [65.0, 66.0],
            "sell_elg_amount": [650.0, 660.0],
            "net_mf_vol": [12.0, 13.0],
            "net_mf_amount": [120.0, 130.0],
        }
    )
    DatasetStore(root).write_frame(frame, "raw/tushare/moneyflow", {"trade_date": "20240102"})


if __name__ == "__main__":
    unittest.main()
