import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from scripts.run_fina_indicator_shard_backfill_smoke import run_fina_indicator_shard_backfill_smoke_cli


class FakeShardBackfillAdapter:
    def __init__(self) -> None:
        self.calls = []

    def fetch_fina_indicator(self, period: str, ts_code: str = "") -> pd.DataFrame:
        self.calls.append((ts_code, period))
        period_date = pd.to_datetime(period, format="%Y%m%d").date()
        ann_date = (pd.Timestamp(period_date) + pd.Timedelta(days=25)).date()
        return pd.DataFrame(
            {
                "symbol": [ts_code],
                "ann_date": [ann_date],
                "end_date": [period_date],
                "roe": [10.0],
                "roa": [1.0],
                "grossprofit_margin": [30.0],
                "netprofit_margin": [12.0],
                "netprofit_yoy": [8.0],
                "or_yoy": [6.0],
                "ocfps": [1.2],
                "cfps": [1.8],
            }
        )


class FinaIndicatorShardBackfillSmokeCliTests(unittest.TestCase):
    def test_shard_smoke_selects_first_symbols_and_runs_pit_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shard_plan_json = root / "fina_indicator_symbol_shard_plan.json"
            _write_shard_plan(shard_plan_json)
            adapter = FakeShardBackfillAdapter()

            result = run_fina_indicator_shard_backfill_smoke_cli(
                shard_plan_json=shard_plan_json,
                shard_id=1,
                max_symbols=2,
                batch_size=10,
                max_requests=4,
                output_dir=root / "processed",
                pit_readiness_output_dir=root / "pit_readiness",
                adapter=adapter,
            )

            self.assertEqual(result["summary"]["selected_symbol_count"], 2)
            self.assertEqual(result["summary"]["request_count"], 4)
            self.assertEqual(result["summary"]["processed_rows"], 4)
            self.assertTrue(result["summary"]["pit_readiness_passes"])
            self.assertEqual(
                adapter.calls,
                [
                    ("000001.SZ", "20240331"),
                    ("000002.SZ", "20240331"),
                    ("000001.SZ", "20240630"),
                    ("000002.SZ", "20240630"),
                ],
            )
            self.assertTrue((root / "processed" / "shard_backfill_smoke.json").exists())
            self.assertTrue((root / "processed" / "shard_backfill_smoke.md").exists())
            self.assertTrue((root / "pit_readiness" / "tushare_financial_pit_readiness.json").exists())

    def test_shard_smoke_blocks_when_selected_requests_exceed_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            shard_plan_json = root / "fina_indicator_symbol_shard_plan.json"
            _write_shard_plan(shard_plan_json)

            with self.assertRaisesRegex(RuntimeError, "request budget"):
                run_fina_indicator_shard_backfill_smoke_cli(
                    shard_plan_json=shard_plan_json,
                    shard_id=1,
                    max_symbols=3,
                    max_requests=2,
                    output_dir=root / "processed",
                    pit_readiness_output_dir=root / "pit_readiness",
                    adapter=FakeShardBackfillAdapter(),
                )


def _write_shard_plan(path: Path) -> None:
    payload = {
        "periods": ["20240331", "20240630"],
        "shards": [
            {
                "shard_id": 1,
                "symbol_count": 3,
                "period_count": 2,
                "request_count": 6,
                "first_symbol": "000001.SZ",
                "last_symbol": "000003.SZ",
                "symbols": ["000001.SZ", "000002.SZ", "000003.SZ"],
            }
        ],
        "summary": {"passes": True},
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
