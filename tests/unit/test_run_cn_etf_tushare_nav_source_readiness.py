from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.data.cn_trading_calendar import (
    build_cn_trading_calendar,
    write_cn_trading_calendar,
)
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_cn_etf_tushare_nav_source_readiness import (
    _load_and_validate_config,
    run_cn_etf_tushare_nav_source_readiness_cli,
)


class FixtureFundNavAdapter:
    def __init__(self):
        self.calls = []

    def fetch_fund_nav(self, ts_code, start_date="", end_date="", market="E"):
        self.calls.append((ts_code, start_date, end_date, market))
        dates = pd.date_range("2024-01-02", "2024-01-08", freq="B")
        return pd.DataFrame(
            {
                "symbol": [ts_code] * len(dates),
                "ann_date": dates.date,
                "nav_date": dates.date,
                "unit_nav": [1.0 + int(ts_code[:6]) % 100 / 1000] * len(dates),
                "accum_nav": [1.0 + int(ts_code[:6]) % 100 / 1000] * len(dates),
                "accum_div": [0.0] * len(dates),
                "net_asset": [100_000_000.0] * len(dates),
                "total_netasset": [100_000_000.0] * len(dates),
                "adj_nav": [1.0 + int(ts_code[:6]) % 100 / 1000] * len(dates),
                "update_flag": [1.0] * len(dates),
            }
        )


class RunCnEtfTushareNavSourceReadinessTests(unittest.TestCase):
    def test_end_to_end_execute_then_local_audit_is_ready_and_deterministic(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = _fixture_config(root)
            adapter = FixtureFundNavAdapter()

            result = run_cn_etf_tushare_nav_source_readiness_cli(
                config_path=config_path,
                execute=True,
                adapter=adapter,
                current_branch="codex/test-nav-source",
            )

            self.assertEqual(result["status"], "ready_for_nav_premium_preregistration")
            self.assertEqual(len(adapter.calls), 30)
            self.assertEqual(result["ingest_result"]["request_summary"]["failed"], 0)
            self.assertTrue(result["gate"]["cleared"])
            first_json = Path(result["artifacts"]["json"])
            first_hash = hashlib.sha256(first_json.read_bytes()).hexdigest()

            repeated = run_cn_etf_tushare_nav_source_readiness_cli(
                config_path=config_path,
                execute=False,
                current_branch="codex/test-nav-source",
            )
            second_hash = hashlib.sha256(
                Path(repeated["artifacts"]["json"]).read_bytes()
            ).hexdigest()

            self.assertEqual(first_hash, second_hash)
            self.assertNotIn("ingest_result", repeated)
            all_output = "".join(
                path.read_text(encoding="utf-8", errors="ignore")
                for path in root.rglob("*")
                if path.is_file() and path.suffix in {".json", ".md", ".csv"}
            )
            self.assertNotIn("TUSHARE_TOKEN", all_output)

    def test_audit_only_requires_existing_local_dataset_without_calling_adapter(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = _fixture_config(root, write_authorities=False)
            adapter = FixtureFundNavAdapter()

            with self.assertRaisesRegex(FileNotFoundError, "canonical NAV"):
                run_cn_etf_tushare_nav_source_readiness_cli(
                    config_path=config_path,
                    execute=False,
                    adapter=adapter,
                    current_branch="codex/test-nav-source",
                )

            self.assertEqual(adapter.calls, [])

    def test_config_rejects_threshold_boundary_and_holdout_drift(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = _fixture_config(root)
            payload = json.loads(config_path.read_text(encoding="utf-8"))

            payload["thresholds"]["minimum_public_key_intersection_ratio"] = 0.5
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen readiness thresholds"):
                _load_and_validate_config(config_path)

            payload["thresholds"]["minimum_public_key_intersection_ratio"] = 0.9
            payload["boundaries"]["order_placement_allowed"] = True
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must be false"):
                _load_and_validate_config(config_path)

            payload["boundaries"]["order_placement_allowed"] = False
            payload["analysis"]["end_date"] = "2026-01-02"
            config_path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen analysis boundary"):
                _load_and_validate_config(config_path)

    def test_main_branch_is_rejected(self):
        with TemporaryDirectory() as directory:
            config_path = _fixture_config(Path(directory), write_authorities=False)

            with self.assertRaisesRegex(ValueError, "main"):
                run_cn_etf_tushare_nav_source_readiness_cli(
                    config_path=config_path,
                    execute=False,
                    current_branch="main",
                )


def _fixture_config(root: Path, write_authorities: bool = True) -> Path:
    payload = json.loads(
        Path("configs/cn_etf_tushare_nav_source_readiness_20260729.json").read_text(
            encoding="utf-8"
        )
    )
    payload["analysis"]["target_universe_path"] = str(root / "target_universe.csv")
    payload["analysis"]["public_nav_root"] = str(root / "public")
    payload["analysis"]["bar_root"] = str(root / "bars")
    payload["outputs"]["data_dir"] = str(root / "nav_source")
    payload["outputs"]["report_dir"] = str(root / "reports")
    calendar_path, manifest_path = _write_calendar(root)
    payload["analysis"]["trading_calendar_path"] = str(calendar_path)
    payload["analysis"]["trading_calendar_manifest_path"] = str(manifest_path)
    config_path = root / "config.json"
    config_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    if write_authorities:
        _write_target_universe(Path(payload["analysis"]["target_universe_path"]))
        _write_public_nav(Path(payload["analysis"]["public_nav_root"]))
    return config_path


def _write_calendar(root: Path):
    dates = pd.to_datetime(
        [
            "2024-01-02",
            "2024-01-03",
            "2024-01-04",
            "2024-01-05",
            "2024-01-08",
            "2024-01-09",
            "2024-07-01",
        ]
    )
    exchange_frames = {
        exchange: pd.DataFrame(
            {
                "date": dates.date,
                "is_open": [1] * len(dates),
                "exchange": [exchange] * len(dates),
            }
        )
        for exchange in ("SSE", "SZSE")
    }
    calendar, manifest = build_cn_trading_calendar(
        exchange_frames,
        start_date="2020-01-02",
        end_date="2024-07-05",
    )
    paths = write_cn_trading_calendar(root / "calendar", calendar, manifest)
    return Path(paths["calendar_path"]), Path(paths["manifest_path"])


def _write_target_universe(path: Path):
    symbols = [f"{510000 + index:06d}.SH" for index in range(30)]
    pd.DataFrame(
        {
            "etf_code": symbols,
            "market_exchange": ["SSE"] * len(symbols),
            "list_date": ["2010-01-01"] * len(symbols),
            "delist_date": [None] * len(symbols),
        }
    ).to_csv(path, index=False)


def _write_public_nav(root: Path):
    dates = pd.date_range("2024-01-02", "2024-01-08", freq="B")
    rows = []
    for date in dates:
        for index in range(30):
            code = f"{510000 + index:06d}"
            rows.append(
                {
                    "date": date.date(),
                    "known_from": (date + pd.offsets.BDay()).date(),
                    "asset_id": f"CN_ETF_XSHG_{code}",
                    "symbol": f"{code}.SH",
                    "exchange": "SSE",
                    "nav": 1.0 + index / 1000,
                    "nav_source": "eastmoney_fund_detail_history",
                }
            )
    DatasetStore(root).write_frame(
        pd.DataFrame(rows),
        "processed/etf_share_size",
        {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
