import unittest

import pandas as pd

from quant_robot.ops.cn_etf_pcf_target_universe import (
    build_cn_etf_pcf_target_universe,
)


class CnEtfPcfTargetUniverseTests(unittest.TestCase):
    def test_builds_survivorship_safe_window_universe(self):
        target, result = build_cn_etf_pcf_target_universe(
            fund_basic=_fund_basic(),
            bars=_bars(),
            analysis_start="2024-01-02",
            analysis_end="2024-01-03",
            minimum_target_etfs=2,
        )

        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["gate"]["cleared"])
        self.assertEqual(target["etf_code"].tolist(), ["159919.SZ", "510050.SH"])
        self.assertEqual(result["summary"]["target_etfs"], 2)
        self.assertEqual(result["summary"]["delisted_target_etfs"], 1)
        self.assertEqual(result["integrity"]["missing_list_date_without_bar_rows"], 1)
        self.assertFalse(result["decision"]["factor_generation_allowed"])

    def test_missing_listing_date_with_analysis_bar_blocks(self):
        bars = pd.concat(
            [
                _bars(),
                pd.DataFrame(
                    {
                        "symbol": ["159999.SZ"],
                        "date": [pd.Timestamp("2024-01-02")],
                    }
                ),
            ],
            ignore_index=True,
        )

        _, result = build_cn_etf_pcf_target_universe(
            fund_basic=_fund_basic(),
            bars=bars,
            analysis_start="2024-01-02",
            analysis_end="2024-01-03",
            minimum_target_etfs=2,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn(
            "missing_list_date_for_bar_observed_etf",
            result["gate"]["blockers"],
        )

    def test_current_active_only_snapshot_blocks(self):
        active_only = _fund_basic()
        active_only["status"] = "L"

        _, result = build_cn_etf_pcf_target_universe(
            fund_basic=active_only,
            bars=_bars(),
            analysis_start="2024-01-02",
            analysis_end="2024-01-03",
            minimum_target_etfs=2,
        )

        self.assertIn(
            "current_active_only_fund_snapshot",
            result["gate"]["blockers"],
        )


def _fund_basic() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["510050.SH", "159919.SZ", "159999.SZ"],
            "name": ["SSE ETF", "SZSE ETF", "Future ETF"],
            "is_etf": [True, True, True],
            "status": ["L", "D", "L"],
            "list_date": [
                pd.Timestamp("2004-12-30").date(),
                pd.Timestamp("2012-12-25").date(),
                None,
            ],
            "delist_date": [
                None,
                pd.Timestamp("2024-01-03").date(),
                None,
            ],
        }
    )


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": [
                "510050.SH",
                "159919.SZ",
                "510050.SH",
                "159919.SZ",
            ],
            "date": pd.to_datetime(
                ["2024-01-02", "2024-01-02", "2024-01-03", "2024-01-03"]
            ),
        }
    )


if __name__ == "__main__":
    unittest.main()
