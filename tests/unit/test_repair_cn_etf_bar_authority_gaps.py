import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.cn_trading_calendar import (
    build_cn_trading_calendar,
    write_cn_trading_calendar,
)
from quant_robot.storage.dataset_store import DatasetStore
from quant_robot.storage.processed_bars import load_processed_bars
from scripts.repair_cn_etf_bar_authority_gaps import (
    repair_cn_etf_bar_authority_gaps,
)


class RepairCnEtfBarAuthorityGapsTests(unittest.TestCase):
    def test_repairs_exact_official_sessions_and_rebuilds_year_quality_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data_root = root / "data"
            DatasetStore(data_root).write_frame(
                _processed_neighbor(),
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2020"},
            )
            calendar_dir = root / "calendar"
            calendar, manifest = build_cn_trading_calendar(
                {
                    "SSE": _calendar_frame("SSE"),
                    "SZSE": _calendar_frame("SZSE"),
                },
                start_date="2020-05-27",
                end_date="2020-06-03",
            )
            written = write_cn_trading_calendar(calendar_dir, calendar, manifest)
            report_dir = root / "report"

            result = repair_cn_etf_bar_authority_gaps(
                adapter=_Adapter(),
                data_root=data_root,
                trading_calendar_path=written["calendar_path"],
                trading_calendar_manifest_path=written["manifest_path"],
                gap_dates=("2020-05-28", "2020-06-03"),
                report_dir=report_dir,
                execute=True,
            )

            self.assertEqual(result["status"], "repaired")
            self.assertTrue(result["gate"]["cleared"])
            self.assertEqual(result["inserted_rows_by_date"]["2020-05-28"], 1)
            self.assertEqual(result["inserted_rows_by_date"]["2020-06-03"], 1)
            bars = load_processed_bars(data_root, "CN_ETF")
            self.assertEqual(len(bars), 3)
            self.assertTrue((data_root / "quality_report.json").is_file())
            self.assertTrue(
                (report_dir / "cn_etf_bar_authority_gap_repair.json").is_file()
            )
            self.assertFalse(result["decision"]["factor_generation_allowed"])

            repeated = repair_cn_etf_bar_authority_gaps(
                adapter=_Adapter(),
                data_root=data_root,
                trading_calendar_path=written["calendar_path"],
                trading_calendar_manifest_path=written["manifest_path"],
                gap_dates=("2020-05-28", "2020-06-03"),
                report_dir=report_dir,
                execute=True,
            )
            self.assertEqual(repeated["status"], "already_repaired")
            self.assertEqual(repeated["rows_before"], repeated["rows_after"])
            self.assertEqual(
                repeated["artifacts"]["processed_partition_sha256_before"],
                repeated["artifacts"]["processed_partition_sha256_after"],
            )


class _Adapter:
    def fetch_trade_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "exchange": ["SSE", "SSE"],
                "date": [pd.Timestamp("2020-05-28").date(), pd.Timestamp("2020-06-03").date()],
                "is_open": [1, 1],
            }
        )

    def fetch_etf_daily_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        date = pd.to_datetime(trade_date).date()
        return pd.DataFrame(
            {
                "symbol": ["510050.SH"],
                "date": [date],
                "open": [3.0],
                "high": [3.1],
                "low": [2.9],
                "close": [3.05],
                "volume": [1000.0],
                "amount": [3050.0],
            }
        )


def _processed_neighbor() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": ["CN_ETF_XSHG_510050"],
            "symbol": ["510050.SH"],
            "market": ["CN_ETF"],
            "exchange": ["XSHG"],
            "asset_type": ["etf"],
            "currency": ["CNY"],
            "timezone": ["Asia/Shanghai"],
            "calendar": ["XSHG"],
            "timestamp": [pd.Timestamp("2020-05-27", tz="UTC")],
            "date": [pd.Timestamp("2020-05-27").date()],
            "frequency": ["1d"],
            "open": [3.0],
            "high": [3.1],
            "low": [2.9],
            "close": [3.05],
            "adj_close": [3.05],
            "volume": [1000.0],
            "amount": [3050.0],
            "vwap": [3.05],
            "adjusted": [False],
            "source": ["tushare"],
            "ingested_at": [pd.Timestamp("2026-07-28", tz="UTC")],
        }
    )


def _calendar_frame(exchange: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "exchange": [exchange, exchange, exchange],
            "date": ["2020-05-27", "2020-05-28", "2020-06-03"],
            "is_open": [1, 1, 1],
        }
    )


if __name__ == "__main__":
    unittest.main()
