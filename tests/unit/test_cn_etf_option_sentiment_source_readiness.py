import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.cn_etf_option_sentiment_source_readiness import (
    build_cn_etf_option_sentiment_source_readiness,
    write_cn_etf_option_sentiment_source_readiness,
)


class CnEtfOptionSentimentSourceReadinessTests(unittest.TestCase):
    def test_blocks_primary_family_when_underlying_breadth_is_too_narrow(self):
        result = build_cn_etf_option_sentiment_source_readiness(
            contracts=_contracts(9),
            daily_probes=_daily_probes(9),
            config=_config(),
            config_sha256="a" * 64,
        )

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["summary"]["underlying_count"], 9)
        self.assertIn("etf_option_underlying_count_below_minimum", result["gate"]["blockers"])
        self.assertFalse(result["factor_generation_allowed"])
        self.assertFalse(result["forward_return_read"])

    def test_clears_source_gate_with_thirty_clean_underlyings(self):
        result = build_cn_etf_option_sentiment_source_readiness(
            contracts=_contracts(30),
            daily_probes=_daily_probes(30),
            config=_config(),
            config_sha256="a" * 64,
        )

        self.assertEqual(result["status"], "ready_for_option_sentiment_preregistration")
        self.assertTrue(result["gate"]["cleared"])
        self.assertEqual(result["summary"]["probe_count"], 2)

    def test_writer_is_deterministic(self):
        result = build_cn_etf_option_sentiment_source_readiness(
            contracts=_contracts(9),
            daily_probes=_daily_probes(9),
            config=_config(),
            config_sha256="a" * 64,
        )
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_paths = write_cn_etf_option_sentiment_source_readiness(first, result)
            second_paths = write_cn_etf_option_sentiment_source_readiness(second, result)
            for name in first_paths:
                self.assertEqual(
                    Path(first_paths[name]).read_bytes(),
                    Path(second_paths[name]).read_bytes(),
                )


def _contracts(count: int) -> pd.DataFrame:
    rows = []
    for index in range(count):
        suffix = "SH" if index % 2 == 0 else "SZ"
        exchange = "SSE" if suffix == "SH" else "SZSE"
        underlying = f"{510000 + index:06d}"
        for call_put in ("C", "P"):
            rows.append(
                {
                    "ts_code": f"10{index:06d}{call_put}.{suffix}",
                    "exchange": exchange,
                    "opt_code": f"OP{underlying}.{suffix}",
                    "call_put": call_put,
                    "list_date": "20191201",
                    "delist_date": "20241231",
                }
            )
    return pd.DataFrame(rows)


def _daily_probes(count: int) -> dict[str, pd.DataFrame]:
    contracts = _contracts(count)
    frames = {}
    for date in ("20200102", "20240628"):
        frame = contracts[["ts_code", "exchange"]].copy()
        frame["trade_date"] = date
        frame["close"] = 1.0
        frame["vol"] = 100.0
        frame["amount"] = 10.0
        frame["oi"] = 200.0
        frames[date] = frame
    return frames


def _config() -> dict:
    return {
        "analysis": {
            "start_date": "2020-01-02",
            "end_date": "2024-06-28",
        },
        "thresholds": {
            "minimum_etf_underlyings": 30,
            "minimum_positive_close_ratio_per_probe": 0.95,
        },
        "probes": {"dates": ["2020-01-02", "2024-06-28"]},
    }


if __name__ == "__main__":
    unittest.main()
