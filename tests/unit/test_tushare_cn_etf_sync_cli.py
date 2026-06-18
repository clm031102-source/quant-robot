import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_tushare_cn_etf_sync import DEFAULT_OUTPUT_DIR, run_tushare_cn_etf_sync_cli


class TushareCnEtfSyncCliTests(unittest.TestCase):
    def test_default_output_dir_matches_full_history_research_docs(self):
        self.assertEqual(DEFAULT_OUTPUT_DIR, Path("data/processed/tushare_etf_full"))

    def test_function_writes_fixture_sync_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            pack = run_tushare_cn_etf_sync_cli(
                source="tushare-fixture",
                start_date="2024-01-02",
                end_date="2024-01-03",
                as_of="2024-01-03",
                output_dir=root / "processed",
                report_dir=root / "reports",
                execute=True,
                min_rotation_history_rows=2,
                min_rotation_median_amount=100000.0,
            )

            self.assertEqual(pack["status"], "completed")
            self.assertEqual(pack["universe"]["eligible_symbols"], ["159915.SZ", "510300.SH"])
            self.assertTrue((root / "reports" / "tushare_cn_etf_sync_pack.json").exists())
            self.assertTrue((root / "reports" / "tushare_cn_etf_sync_pack.md").exists())
            self.assertTrue((root / "reports" / "cn_etf_universe.csv").exists())
            self.assertEqual(pack["rotation_pool"]["thresholds"]["min_history_rows"], 2)
            self.assertEqual(pack["rotation_pool"]["thresholds"]["min_median_amount"], 100000.0)
            self.assertGreater(pack["rotation_membership"]["rows"], 0)
            self.assertEqual(pack["etf_share_size"]["processed_rows"], 4)
            self.assertEqual(pack["auxiliary_datasets"]["etf_share_size"], "enabled")
            report_text = (root / "reports" / "tushare_cn_etf_sync_pack.md").read_text(encoding="utf-8")
            self.assertIn("Rotation membership rows", report_text)

    def test_function_resolves_auto_start_and_latest_end_for_fixture_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            pack = run_tushare_cn_etf_sync_cli(
                source="tushare-fixture",
                start_date="auto",
                end_date="latest",
                output_dir=root / "processed",
                report_dir=root / "reports",
                execute=True,
                full_history_start_date="2024-01-02",
                latest_today="2024-01-05",
                min_rotation_history_rows=2,
            )

            self.assertEqual(pack["status"], "completed")
            self.assertEqual(pack["start_date"], "2024-01-02")
            self.assertEqual(pack["end_date"], "2024-01-05")
            self.assertEqual(pack["as_of"], "2024-01-05")
            self.assertEqual(pack["ingest"]["processed_rows"], 8)
            self.assertEqual(pack["date_resolution"]["start_date"]["method"], "full_history_start_date")
            self.assertEqual(pack["date_resolution"]["end_date"]["method"], "tushare_trade_calendar_latest_open")

    def test_function_resolves_incremental_start_after_existing_processed_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_existing_cn_etf_bars(root / "processed", end_date="2024-01-03")

            pack = run_tushare_cn_etf_sync_cli(
                source="tushare-fixture",
                start_date="incremental",
                end_date="latest",
                output_dir=root / "processed",
                report_dir=root / "reports",
                execute=True,
                latest_today="2024-01-05",
                min_rotation_history_rows=2,
            )

            self.assertEqual(pack["status"], "completed")
            self.assertEqual(pack["start_date"], "2024-01-04")
            self.assertEqual(pack["end_date"], "2024-01-05")
            self.assertEqual(pack["date_resolution"]["start_date"]["method"], "incremental_after_last_processed_bar")
            self.assertEqual(pack["date_resolution"]["start_date"]["last_processed_date"], "2024-01-03")
            self.assertEqual(pack["ingest"]["downloaded_trade_dates"], ["20240104", "20240105"])

    def test_function_skips_incremental_sync_when_processed_bars_are_current(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_existing_cn_etf_bars(root / "processed", end_date="2024-01-05")

            pack = run_tushare_cn_etf_sync_cli(
                source="tushare-fixture",
                start_date="incremental",
                end_date="latest",
                output_dir=root / "processed",
                report_dir=root / "reports",
                execute=True,
                latest_today="2024-01-05",
                min_rotation_history_rows=2,
            )

            self.assertEqual(pack["status"], "up_to_date")
            self.assertEqual(pack["start_date"], "2024-01-06")
            self.assertEqual(pack["end_date"], "2024-01-05")
            self.assertEqual(pack["blockers"], [])
            self.assertEqual(pack["ingest"]["processed_rows"], 0)
            self.assertEqual(pack["date_resolution"]["start_date"]["method"], "incremental_after_last_processed_bar")
            self.assertEqual(pack["date_resolution"]["incremental"]["last_processed_date"], "2024-01-05")

    def test_function_blocks_real_tushare_execute_when_readiness_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            pack = run_tushare_cn_etf_sync_cli(
                source="tushare",
                start_date="2024-01-02",
                end_date="2024-01-03",
                output_dir=root / "processed",
                report_dir=root / "reports",
                execute=True,
                readiness={"source": "tushare", "ready": False, "missing": ["TUSHARE_TOKEN is not set"]},
            )

            self.assertEqual(pack["status"], "blocked_missing_readiness")
            self.assertIn("TUSHARE_TOKEN is not set", pack["blockers"])
            self.assertTrue((root / "reports" / "tushare_cn_etf_sync_pack.json").exists())
            self.assertFalse((root / "processed" / "manifest.json").exists())

    def test_function_blocks_real_tushare_latest_when_readiness_missing_without_date_parse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            pack = run_tushare_cn_etf_sync_cli(
                source="tushare",
                start_date="auto",
                end_date="latest",
                output_dir=root / "processed",
                report_dir=root / "reports",
                execute=True,
                readiness={"source": "tushare", "ready": False, "missing": ["TUSHARE_TOKEN is not set"]},
                full_history_start_date="2005-01-01",
                latest_today="2024-01-05",
            )

            self.assertEqual(pack["status"], "blocked_missing_readiness")
            self.assertIn("TUSHARE_TOKEN is not set", pack["blockers"])
            self.assertEqual(pack["start_date"], "2005-01-01")
            self.assertEqual(pack["end_date"], "2024-01-05")
            self.assertEqual(
                pack["date_resolution"]["end_date"]["method"],
                "local_cutoff_provider_unavailable",
            )

    def test_script_entrypoint_runs_fixture_sync_from_repo_root(self):
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_tushare_cn_etf_sync.py",
                    "--source",
                    "tushare-fixture",
                    "--start-date",
                    "2024-01-02",
                    "--end-date",
                    "2024-01-03",
                    "--as-of",
                    "2024-01-03",
                    "--output-dir",
                    str(root / "processed"),
                    "--report-dir",
                    str(root / "reports"),
                    "--execute",
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )

            payload = json.loads((root / "reports" / "tushare_cn_etf_sync_pack.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tushare_cn_etf_sync", result.stdout)
        self.assertIn("rotation_membership", result.stdout)
        self.assertEqual(payload["status"], "completed")

def _write_existing_cn_etf_bars(root: Path, end_date: str) -> None:
    bars = load_demo_market_bars()
    dates = pd.to_datetime(bars["date"]).dt.date
    cutoff = pd.to_datetime(end_date).date()
    frame = bars[(bars["market"] == "CN_ETF") & (dates <= cutoff)].reset_index(drop=True)
    DatasetStore(root).write_frame(
        frame,
        "processed/bars",
        {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
    )


if __name__ == "__main__":
    unittest.main()
