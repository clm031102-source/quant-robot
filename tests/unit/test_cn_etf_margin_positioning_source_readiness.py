import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_etf_margin_positioning_source_readiness import (
    STATUS_READY,
    build_cn_etf_margin_positioning_source_readiness,
    write_cn_etf_margin_positioning_source_readiness,
)


class CnEtfMarginPositioningSourceReadinessTests(unittest.TestCase):
    def test_ready_source_requires_exact_next_session_and_breadth(self):
        result = build_cn_etf_margin_positioning_source_readiness(
            margin=_margin(),
            bars=_bars(),
            trading_sessions=["2024-01-02", "2024-01-03", "2024-01-04"],
            config=_config(),
            config_sha256="a" * 64,
        )

        self.assertEqual(result["status"], STATUS_READY)
        self.assertTrue(result["gate"]["cleared"])
        self.assertEqual(result["summary"]["rows"], 4)
        self.assertEqual(result["summary"]["assets"], 2)
        self.assertEqual(result["summary"]["analysis_sessions"], 2)
        self.assertEqual(result["summary"]["qualifying_dates"], 2)
        self.assertEqual(result["integrity"]["same_date_bar_intersection_ratio"], 1.0)
        self.assertEqual(result["integrity"]["exact_next_session_ratio"], 1.0)
        self.assertFalse(result["factor_generation_allowed"])
        self.assertFalse(result["forward_return_read"])
        self.assertFalse(result["final_holdout_allowed"])

    def test_wrong_available_date_and_missing_session_block(self):
        margin = _margin().iloc[:2].copy()
        margin["available_date"] = margin["date"]
        result = build_cn_etf_margin_positioning_source_readiness(
            margin=margin,
            bars=_bars(),
            trading_sessions=["2024-01-02", "2024-01-03", "2024-01-04"],
            config=_config(),
            config_sha256="a" * 64,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertIn("available_date_not_exact_next_session", result["gate"]["blockers"])
        self.assertIn("qualifying_date_coverage_below_minimum", result["gate"]["blockers"])

    def test_duplicate_and_negative_values_block(self):
        margin = pd.concat([_margin(), _margin().iloc[[0]]], ignore_index=True)
        margin.loc[0, "rzye"] = -1.0
        config = _config()
        config["thresholds"]["minimum_valid_nonnegative_numeric_ratio"] = 1.0
        result = build_cn_etf_margin_positioning_source_readiness(
            margin=margin,
            bars=_bars(),
            trading_sessions=["2024-01-02", "2024-01-03", "2024-01-04"],
            config=config,
            config_sha256="a" * 64,
        )

        self.assertIn("duplicate_margin_positioning_keys", result["gate"]["blockers"])
        self.assertIn("valid_nonnegative_numeric_ratio_below_minimum", result["gate"]["blockers"])

    def test_writer_is_deterministic(self):
        result = build_cn_etf_margin_positioning_source_readiness(
            margin=_margin(),
            bars=_bars(),
            trading_sessions=["2024-01-02", "2024-01-03", "2024-01-04"],
            config=_config(),
            config_sha256="a" * 64,
        )
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_paths = write_cn_etf_margin_positioning_source_readiness(first, result)
            second_paths = write_cn_etf_margin_positioning_source_readiness(second, result)
            for name in first_paths:
                self.assertEqual(
                    Path(first_paths[name]).read_bytes(),
                    Path(second_paths[name]).read_bytes(),
                )


def _bars():
    return pd.DataFrame(
        [
            {"date": date, "symbol": symbol, "asset_id": f"CN_ETF_{symbol}"}
            for date in pd.to_datetime(["2024-01-02", "2024-01-03"])
            for symbol in ("510050.SH", "159919.SZ")
        ]
    )


def _margin():
    rows = []
    next_date = {"2024-01-02": "2024-01-03", "2024-01-03": "2024-01-04"}
    for date in ("2024-01-02", "2024-01-03"):
        for index, symbol in enumerate(("510050.SH", "159919.SZ"), start=1):
            rows.append(
                {
                    "date": pd.Timestamp(date),
                    "available_date": pd.Timestamp(next_date[date]),
                    "asset_id": f"CN_ETF_{symbol}",
                    "symbol": symbol,
                    "market": "CN_ETF",
                    "source": "tushare_margin_detail",
                    "rzye": float(100 * index),
                    "rqye": float(index),
                    "rzmre": float(10 * index),
                    "rqyl": float(index),
                    "rzche": float(5 * index),
                    "rqchl": 0.0,
                    "rqmcl": 0.0,
                    "rzrqye": float(101 * index),
                }
            )
    return pd.DataFrame(rows)


def _config():
    return {
        "review_date": "2026-07-28",
        "analysis": {
            "start_date": "2024-01-02",
            "end_date": "2024-01-03",
            "final_holdout_start": "2026-01-01",
        },
        "thresholds": {
            "minimum_assets_per_date": 2,
            "minimum_qualifying_date_coverage": 1.0,
            "minimum_positive_financing_balance_ratio": 1.0,
            "minimum_valid_nonnegative_numeric_ratio": 1.0,
        },
    }


if __name__ == "__main__":
    unittest.main()
