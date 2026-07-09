import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.tushare_hk_hold_source_audit import (
    build_tushare_hk_hold_source_audit,
    write_tushare_hk_hold_source_audit,
)


class FakeHkHoldAuditAdapter:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def fetch_hk_hold_by_trade_date(self, trade_date: str) -> pd.DataFrame:
        self.calls.append(trade_date)
        if trade_date == "20240816":
            return pd.DataFrame(
                {
                    "ts_code": ["000001.SZ", "600000.SH", "920001.BJ", "00700.HK", "AAPL.US"],
                    "trade_date": [trade_date] * 5,
                    "vol": [1, 2, 3, 4, 5],
                    "ratio": [0.1, 0.2, 0.3, 0.4, 0.5],
                }
            )
        if trade_date == "20240819":
            return pd.DataFrame(
                {
                    "ts_code": ["00700.HK", "AAPL.US"],
                    "trade_date": [trade_date, trade_date],
                    "vol": [4, 5],
                    "ratio": [0.4, 0.5],
                }
            )
        return pd.DataFrame(columns=["ts_code", "trade_date", "vol", "ratio"])


class TushareHkHoldSourceAuditTests(unittest.TestCase):
    def test_counts_cn_and_non_cn_rows_by_trade_date(self) -> None:
        adapter = FakeHkHoldAuditAdapter()

        packet = build_tushare_hk_hold_source_audit(
            adapter,
            trade_dates=["20240816", "20240819", "20240820"],
        )

        self.assertEqual(adapter.calls, ["20240816", "20240819", "20240820"])
        self.assertEqual(packet["summary"]["requested_date_count"], 3)
        self.assertEqual(packet["summary"]["raw_row_count"], 7)
        self.assertEqual(packet["summary"]["cn_row_count"], 3)
        self.assertEqual(packet["summary"]["non_cn_row_count"], 4)
        self.assertEqual(packet["summary"]["usable_cn_date_count"], 1)
        self.assertEqual(packet["summary"]["empty_after_cn_filter_date_count"], 1)
        self.assertEqual(packet["summary"]["empty_raw_date_count"], 1)
        rows = {row["trade_date"]: row for row in packet["date_rows"]}
        self.assertEqual(rows["20240816"]["status"], "usable_cn_rows")
        self.assertEqual(rows["20240816"]["suffix_counts"]["SZ"], 1)
        self.assertEqual(rows["20240816"]["suffix_counts"]["SH"], 1)
        self.assertEqual(rows["20240816"]["suffix_counts"]["BJ"], 1)
        self.assertEqual(rows["20240816"]["suffix_counts"]["HK"], 1)
        self.assertEqual(rows["20240819"]["status"], "empty_after_cn_filter")
        self.assertEqual(rows["20240820"]["status"], "empty_raw_response")

    def test_writes_json_markdown_and_csv_outputs(self) -> None:
        packet = build_tushare_hk_hold_source_audit(
            FakeHkHoldAuditAdapter(),
            trade_dates=["20240816", "20240819"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_tushare_hk_hold_source_audit(Path(tmp), packet)

            json_path = Path(tmp) / "tushare_hk_hold_source_audit.json"
            self.assertTrue(json_path.exists())
            self.assertTrue((Path(tmp) / "tushare_hk_hold_source_audit.md").exists())
            self.assertTrue((Path(tmp) / "tushare_hk_hold_source_audit_rows.csv").exists())
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["summary"]["requested_date_count"], 2)


if __name__ == "__main__":
    unittest.main()
