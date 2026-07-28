import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.cn_trading_calendar import (
    build_cn_trading_calendar,
    write_cn_trading_calendar,
)
from scripts.run_cn_etf_pcf_source_readiness import (
    run_cn_etf_pcf_source_readiness_cli,
)


class RunCnEtfPcfSourceReadinessTests(unittest.TestCase):
    def test_reviews_partitioned_cross_exchange_delivery_without_market_data_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sse = root / "sse"
            szse = root / "szse"
            sse.mkdir()
            szse.mkdir()
            for index, date in enumerate(("20240102", "20240103")):
                _raw("510050.SH", "600000.SH", date, "SSE").to_csv(
                    sse / f"part-{index}.csv",
                    index=False,
                )
                _raw("159919.SZ", "000001.SZ", date, "SZSE").to_parquet(
                    szse / f"part-{index}.parquet",
                    index=False,
                )
            target = root / "target.csv"
            pd.DataFrame(
                {
                    "symbol": ["510050.SH", "159919.SZ"],
                    "list_date": ["20041230", "20121225"],
                    "delist_date": [None, None],
                    "is_etf": [True, True],
                }
            ).to_csv(target, index=False)
            calendar_dir = root / "calendar"
            calendar, manifest = build_cn_trading_calendar(
                {
                    "SSE": _calendar_frame("SSE"),
                    "SZSE": _calendar_frame("SZSE"),
                },
                start_date="2024-01-02",
                end_date="2024-01-03",
            )
            written = write_cn_trading_calendar(calendar_dir, calendar, manifest)
            output = root / "report"

            result = run_cn_etf_pcf_source_readiness_cli(
                sse_input=sse,
                szse_input=szse,
                target_universe_path=target,
                trading_calendar_path=written["calendar_path"],
                trading_calendar_manifest_path=written["manifest_path"],
                source_provider="vendor",
                analysis_start="2024-01-02",
                analysis_end="2024-01-03",
                final_holdout_start="2026-01-01",
                minimum_target_etfs=2,
                output_dir=output,
            )

            self.assertEqual(result["status"], "ready_for_pcf_source_preregistration")
            self.assertEqual(len(result["source_evidence"]["pcf_files"]), 4)
            self.assertTrue((output / "cn_etf_pcf_source_readiness.json").is_file())
            self.assertTrue((output / "date_coverage.csv").is_file())
            self.assertTrue((output / "etf_coverage.csv").is_file())
            self.assertFalse(any(output.glob("*.parquet")))
            self.assertFalse(result["decision"]["factor_generation_allowed"])


def _raw(etf_code: str, constituent: str, date: str, exchange: str) -> pd.DataFrame:
    base = {
        "trade_date": [date],
        "ts_code": [etf_code],
        "con_code": [constituent],
        "qty": [1000],
        "sub_flag": ["allowed"],
        "cpr": [10.0],
        "rdr": [0.0],
        "exchange": ["SH" if exchange == "SSE" else "SZ"],
    }
    if exchange == "SSE":
        base["sca"] = [12345.0]
    else:
        base["sub_cc"] = [123.0]
        base["red_cc"] = [45.0]
    return pd.DataFrame(base)


def _calendar_frame(exchange: str) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "exchange": [exchange, exchange],
            "date": ["2024-01-02", "2024-01-03"],
            "is_open": [1, 1],
        }
    )


if __name__ == "__main__":
    unittest.main()
