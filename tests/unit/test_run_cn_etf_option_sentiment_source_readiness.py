import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_cn_etf_option_sentiment_source_readiness import (
    run_cn_etf_option_sentiment_source_readiness_cli,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/cn_etf_option_sentiment_source_readiness_20260728.json"


class RunCnEtfOptionSentimentSourceReadinessTests(unittest.TestCase):
    def test_cli_writes_blocked_source_packet_from_bounded_probes(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_cn_etf_option_sentiment_source_readiness_cli(
                config_path=CONFIG,
                output_dir=Path(tmp),
                client=_Client(),
            )

            self.assertEqual(result["status"], "blocked")
            self.assertEqual(result["summary"]["underlying_count"], 9)
            self.assertEqual(result["summary"]["probe_count"], 5)
            self.assertIn("contracts", result["artifacts"])
            self.assertIn("daily_rows", result["artifacts"])
            self.assertFalse(result["factor_generation_allowed"])

    def test_cli_rejects_boundary_mutation_before_fetch(self):
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["boundaries"]["factor_generation_allowed"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            client = _Client()
            with self.assertRaisesRegex(ValueError, "factor_generation_allowed"):
                run_cn_etf_option_sentiment_source_readiness_cli(
                    config_path=path,
                    output_dir=Path(tmp) / "out",
                    client=client,
                )
            self.assertEqual(client.calls, [])


class _Client:
    def __init__(self):
        self.calls = []

    def opt_basic(self, *, exchange, fields):
        self.calls.append(("opt_basic", exchange))
        start = 0 if exchange == "SSE" else 5
        count = 5 if exchange == "SSE" else 4
        rows = []
        suffix = "SH" if exchange == "SSE" else "SZ"
        for index in range(start, start + count):
            for call_put in ("C", "P"):
                rows.append(
                    {
                        "ts_code": f"10{index:06d}{call_put}.{suffix}",
                        "exchange": exchange,
                        "opt_code": f"OP{510000 + index:06d}.{suffix}",
                        "call_put": call_put,
                        "list_date": "20191201",
                        "delist_date": "20241231",
                    }
                )
        return pd.DataFrame(rows)

    def opt_daily(self, *, trade_date, exchange, fields):
        self.calls.append(("opt_daily", exchange, trade_date))
        contracts = self.opt_basic(
            exchange=exchange,
            fields="ts_code,exchange,opt_code,call_put,list_date,delist_date",
        )
        frame = contracts[["ts_code", "exchange"]].copy()
        frame["trade_date"] = trade_date
        frame["close"] = 1.0
        frame["vol"] = 100.0
        frame["amount"] = 10.0
        frame["oi"] = 200.0
        return frame


if __name__ == "__main__":
    unittest.main()
