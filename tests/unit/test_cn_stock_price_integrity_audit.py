import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_stock_price_integrity_audit import (
    build_cn_stock_price_integrity_audit,
    write_cn_stock_price_integrity_audit,
)


class CNStockPriceIntegrityAuditTests(unittest.TestCase):
    def test_adjustment_ratio_discontinuity_is_blocking(self):
        packet, rows = build_cn_stock_price_integrity_audit(
            bars=_bars(close=[10.0, 10.1], adj_close=[10.0, 20.2]),
            stock_basic=_stock_basic(),
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertEqual(rows.loc[0, "classification"], "adjustment_ratio_discontinuity")
        self.assertIn("adjustment_ratio_discontinuity_rows:1", packet["decision"]["blockers"])

    def test_official_post_suspension_repricing_requires_review(self):
        packet, rows = build_cn_stock_price_integrity_audit(
            bars=_bars(dates=["2024-01-02", "2024-01-05"], close=[10.0, 20.0]),
            stock_basic=_stock_basic(),
            daily_suspension=pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000001", "CN_XSHE_000001"],
                    "date": ["2024-01-03", "2024-01-04"],
                    "source": ["tushare_suspend_d", "tushare_suspend_d"],
                }
            ),
        )

        self.assertEqual(packet["status"], "review_required")
        self.assertEqual(rows.loc[0, "classification"], "official_post_suspension_repricing")
        self.assertEqual(rows.loc[0, "evidence_source"], "tushare_suspend_d")
        self.assertEqual(packet["decision"]["blockers"], [])

    def test_raw_and_combined_price_moves_are_blocking(self):
        raw_packet, raw_rows = build_cn_stock_price_integrity_audit(
            bars=_bars(close=[10.0, 20.0]),
            stock_basic=_stock_basic(),
        )
        combined_packet, combined_rows = build_cn_stock_price_integrity_audit(
            bars=_bars(close=[10.0, 20.0], adj_close=[10.0, 40.0]),
            stock_basic=_stock_basic(),
        )

        self.assertEqual(raw_rows.loc[0, "classification"], "raw_price_discontinuity")
        self.assertEqual(combined_rows.loc[0, "classification"], "combined_price_adjustment_move")
        self.assertEqual(raw_packet["status"], "blocked")
        self.assertEqual(combined_packet["status"], "blocked")

    def test_official_initial_price_discovery_requires_review(self):
        packet, rows = build_cn_stock_price_integrity_audit(
            bars=_bars(close=[10.0, 20.0]),
            stock_basic=_stock_basic(list_date="2024-01-02"),
        )

        self.assertEqual(packet["status"], "review_required")
        self.assertEqual(rows.loc[0, "classification"], "official_initial_price_discovery")
        self.assertEqual(rows.loc[0, "evidence_source"], "tushare_stock_basic")
        self.assertEqual(rows.loc[0, "observed_session_number"], 2)

    def test_outside_lifecycle_transition_is_blocking(self):
        packet, rows = build_cn_stock_price_integrity_audit(
            bars=_bars(dates=["2024-01-02", "2024-01-04"], close=[10.0, 20.0]),
            stock_basic=_stock_basic(list_date="2024-01-03"),
        )

        self.assertEqual(rows.loc[0, "classification"], "outside_official_lifecycle")
        self.assertEqual(rows.loc[0, "outside_lifecycle_reason"], "previous_bar_before_list_date")
        self.assertIn("outside_official_lifecycle_rows:1", packet["decision"]["blockers"])

    def test_legacy_interval_can_explain_post_suspension_repricing(self):
        packet, rows = build_cn_stock_price_integrity_audit(
            bars=_bars(dates=["2024-01-02", "2024-01-05"], close=[10.0, 20.0]),
            stock_basic=_stock_basic(),
            legacy_suspension=pd.DataFrame(
                {
                    "asset_id": ["CN_XSHE_000001"],
                    "suspend_date": ["2024-01-03"],
                    "resume_date": ["2024-01-05"],
                    "source": ["tushare_suspend"],
                }
            ),
        )

        self.assertEqual(packet["status"], "review_required")
        self.assertEqual(rows.loc[0, "classification"], "official_post_suspension_repricing")
        self.assertEqual(rows.loc[0, "evidence_source"], "tushare_suspend")

    def test_writer_emits_packet_and_row_level_evidence(self):
        packet, rows = build_cn_stock_price_integrity_audit(
            bars=_bars(close=[10.0, 20.0]),
            stock_basic=_stock_basic(),
        )

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            write_cn_stock_price_integrity_audit(output, packet, rows)

            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "cn_stock_price_integrity_audit.json",
                    "cn_stock_price_integrity_audit.md",
                    "extreme_return_rows.csv",
                    "blocking_extreme_return_rows.csv",
                    "review_extreme_return_rows.csv",
                },
            )
            payload = json.loads(
                (output / "cn_stock_price_integrity_audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["extreme_return_rows"], 1)


def _bars(
    *,
    dates: list[str] | None = None,
    close: list[float],
    adj_close: list[float] | None = None,
) -> pd.DataFrame:
    dates = dates or ["2024-01-02", "2024-01-03"]
    adjusted = adj_close or close
    return pd.DataFrame(
        {
            "asset_id": ["CN_XSHE_000001"] * len(dates),
            "symbol": ["000001.SZ"] * len(dates),
            "exchange": ["XSHE"] * len(dates),
            "market": ["CN"] * len(dates),
            "date": dates,
            "close": close,
            "adj_close": adjusted,
        }
    )


def _stock_basic(*, list_date: str = "2020-01-01") -> pd.DataFrame:
    return pd.DataFrame(
        {
            "asset_id": ["CN_XSHE_000001"],
            "symbol": ["000001.SZ"],
            "list_date": [list_date],
            "delist_date": [None],
        }
    )


if __name__ == "__main__":
    unittest.main()
