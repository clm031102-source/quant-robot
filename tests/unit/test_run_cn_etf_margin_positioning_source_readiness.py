import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_cn_etf_margin_positioning_source_readiness import (
    run_cn_etf_margin_positioning_source_readiness_cli,
)


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "configs/cn_etf_margin_positioning_source_readiness_20260728.json"


class RunCnEtfMarginPositioningSourceReadinessTests(unittest.TestCase):
    def test_cli_fetches_missing_shards_and_reuses_them(self):
        bars = _bars()
        sessions = ["2024-06-27", "2024-06-28", "2024-07-01"]
        with tempfile.TemporaryDirectory() as tmp:
            first_client = _Adapter()
            first = run_cn_etf_margin_positioning_source_readiness_cli(
                config_path=CONFIG,
                output_dir=Path(tmp) / "reports",
                data_dir=Path(tmp) / "data",
                execute=True,
                adapter=first_client,
                bars=bars,
                trading_sessions=sessions,
            )
            self.assertEqual(first["status"], "ready_for_margin_positioning_preregistration")
            self.assertEqual(first["summary"]["rows"], 120)
            self.assertEqual(first["runtime_cache"]["fetched_shards"], 2)
            self.assertEqual(len(first_client.calls), 2)

            second_client = _Adapter()
            second = run_cn_etf_margin_positioning_source_readiness_cli(
                config_path=CONFIG,
                output_dir=Path(tmp) / "reports",
                data_dir=Path(tmp) / "data",
                execute=False,
                adapter=second_client,
                bars=bars,
                trading_sessions=sessions,
            )
            self.assertEqual(second["runtime_cache"]["reused_shards"], 2)
            self.assertEqual(second_client.calls, [])
            self.assertEqual(
                first["source_evidence"]["canonical_sha256"],
                second["source_evidence"]["canonical_sha256"],
            )

    def test_boundary_mutation_is_rejected_before_fetch(self):
        payload = json.loads(CONFIG.read_text(encoding="utf-8"))
        payload["boundaries"]["forward_return_read"] = True
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            adapter = _Adapter()
            with self.assertRaisesRegex(ValueError, "forward_return_read"):
                run_cn_etf_margin_positioning_source_readiness_cli(
                    config_path=path,
                    execute=True,
                    adapter=adapter,
                    bars=_bars(),
                    trading_sessions=["2024-06-27", "2024-06-28", "2024-07-01"],
                )
            self.assertEqual(adapter.calls, [])


class _Adapter:
    def __init__(self):
        self.calls = []

    def fetch_margin_detail_by_trade_date(self, trade_date):
        self.calls.append(trade_date)
        return pd.DataFrame(
            [
                {
                    "trade_date": trade_date,
                    "ts_code": f"{510000 + index:06d}.SH",
                    "rzye": 100.0 + index,
                    "rqye": 1.0,
                    "rzmre": 10.0,
                    "rqyl": 1.0,
                    "rzche": 5.0,
                    "rqchl": 0.0,
                    "rqmcl": 0.0,
                    "rzrqye": 101.0 + index,
                }
                for index in range(60)
            ]
        )


def _bars():
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp(date),
                "symbol": f"{510000 + index:06d}.SH",
                "asset_id": f"CN_ETF_XSHG_{510000 + index:06d}",
            }
            for date in ("2024-06-27", "2024-06-28")
            for index in range(60)
        ]
    )


if __name__ == "__main__":
    unittest.main()
