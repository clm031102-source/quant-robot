import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import scripts.run_tushare_analyst_report_cache as cache_cli
from quant_robot.ops.analyst_report_quota_preflight import (
    build_analyst_report_quota_preflight,
    write_analyst_report_quota_preflight,
)
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_analyst_report_quota_preflight import run_analyst_report_quota_preflight


class AnalystReportQuotaPreflightTests(unittest.TestCase):
    def test_blocks_after_two_same_day_provider_requests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_cache(root / "round_a", generated_at="2026-07-05", status="ok")
            _write_cache(root / "round_b", generated_at="2026-07-05", status="ok")

            packet = build_analyst_report_quota_preflight(
                report_roots=[root],
                target_date="2026-07-05",
                max_daily_requests=2,
            )

        self.assertFalse(packet["decision"]["request_allowed"])
        self.assertEqual(packet["summary"]["counted_provider_request_windows"], 2)
        self.assertIn("daily_provider_request_budget_exhausted", packet["decision"]["blockers"])

    def test_ignores_cached_windows_and_other_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_cache(root / "cached_today", generated_at="2026-07-05", status="cached")
            _write_cache(root / "ok_yesterday", generated_at="2026-07-04", status="ok")

            packet = build_analyst_report_quota_preflight(
                report_roots=[root],
                target_date="2026-07-05",
                max_daily_requests=2,
            )

        self.assertTrue(packet["decision"]["request_allowed"])
        self.assertEqual(packet["summary"]["counted_provider_request_windows"], 0)
        self.assertEqual(packet["decision"]["blockers"], [])

    def test_rate_limit_blocks_even_before_daily_budget_is_full(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_cache(
                root / "rate_limited",
                generated_at="2026-07-05",
                status="failed",
                provider_rate_limit="2_per_day",
                retry_after_seconds=86400,
            )

            packet = build_analyst_report_quota_preflight(
                report_roots=[root],
                target_date="2026-07-05",
                max_daily_requests=2,
            )

        self.assertFalse(packet["decision"]["request_allowed"])
        self.assertEqual(packet["summary"]["rate_limited_windows"], 1)
        self.assertEqual(packet["summary"]["next_retry_after_seconds"], 86400)
        self.assertIn("provider_rate_limit_observed", packet["decision"]["blockers"])

    def test_cli_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "out"
            _write_cache(root / "round_a", generated_at="2026-07-05", status="ok")

            packet = run_analyst_report_quota_preflight(
                report_root=[root],
                output_dir=output_dir,
                target_date="2026-07-05",
                max_daily_requests=2,
            )

            payload = json.loads((output_dir / "analyst_report_quota_preflight.json").read_text(encoding="utf-8"))
            markdown_exists = (output_dir / "analyst_report_quota_preflight.md").exists()

        self.assertTrue(packet["decision"]["request_allowed"])
        self.assertTrue(markdown_exists)
        self.assertEqual(payload["summary"]["counted_provider_request_windows"], 1)

    def test_packet_records_scanned_report_roots_and_local_scope_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_root_a = root / "reports_a"
            report_root_b = root / "reports_b"

            packet = build_analyst_report_quota_preflight(
                report_roots=[report_root_a, report_root_b],
                target_date="2026-07-05",
                max_daily_requests=2,
            )

        self.assertEqual(packet["quota_scope"], "local_report_roots_only")
        self.assertIn("local_report_roots_only", packet["warnings"])
        self.assertEqual(packet["summary"]["report_root_count"], 2)
        self.assertEqual(packet["summary"]["report_roots"], [str(report_root_a), str(report_root_b)])
        self.assertIn("## Report Roots", packet["markdown"])
        self.assertIn("local_report_roots_only", packet["markdown"])

    def test_standalone_cli_prints_quota_scope_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_root_a = root / "reports_a"
            report_root_b = root / "reports_b"
            output_dir = root / "out"

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_analyst_report_quota_preflight.py",
                    "--report-root",
                    str(report_root_a),
                    "--report-root",
                    str(report_root_b),
                    "--target-date",
                    "2026-07-05",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

            payload = json.loads((output_dir / "analyst_report_quota_preflight.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 0)
        self.assertIn('"quota_scope": "local_report_roots_only"', result.stdout)
        self.assertIn("local_report_roots_only", result.stdout)
        self.assertEqual(payload["summary"]["report_root_count"], 2)
        self.assertEqual(payload["quota_scope"], "local_report_roots_only")

    def test_packet_warns_when_target_date_differs_from_generated_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nonlocal_date = (date.today() + timedelta(days=1)).isoformat()

            packet = build_analyst_report_quota_preflight(
                report_roots=[root],
                target_date=nonlocal_date,
                max_daily_requests=2,
            )

        self.assertFalse(packet["summary"]["target_date_matches_generated_at"])
        self.assertIn("quota_target_date_differs_from_generated_at", packet["warnings"])
        self.assertIn("quota_target_date_differs_from_generated_at", packet["markdown"])

    def test_cli_fail_on_blocked_returns_nonzero_after_printing_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "out"
            _write_cache(root / "round_a", generated_at="2026-07-05", status="ok")
            _write_cache(root / "round_b", generated_at="2026-07-05", status="ok")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_analyst_report_quota_preflight.py",
                    "--report-root",
                    str(root),
                    "--target-date",
                    "2026-07-05",
                    "--max-daily-requests",
                    "2",
                    "--output-dir",
                    str(output_dir),
                    "--fail-on-blocked",
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 3)
        self.assertIn("daily_provider_request_budget_exhausted", result.stdout)
        self.assertIn('"status": "blocked"', result.stdout)

    def test_cache_cli_runs_default_preflight_and_blocks_before_fetching(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_root = root / "reports"
            output_dir = root / "cache"
            processed_output_dir = root / "processed"
            quota_output_dir = root / "preflight"
            _write_cache(report_root / "round_a", generated_at="2026-07-05", status="ok")
            _write_cache(report_root / "round_b", generated_at="2026-07-05", status="ok")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_tushare_analyst_report_cache.py",
                    "--start-date",
                    "2024-04-01",
                    "--end-date",
                    "2024-04-30",
                    "--output-dir",
                    str(output_dir),
                    "--processed-output-dir",
                    str(processed_output_dir),
                    "--request-sleep-seconds",
                    "0",
                    "--quota-report-root",
                    str(report_root),
                    "--quota-target-date",
                    "2026-07-05",
                    "--quota-output-dir",
                    str(quota_output_dir),
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 3)
            self.assertIn("daily_provider_request_budget_exhausted", result.stdout)
            self.assertIn('"status": "blocked"', result.stdout)
            self.assertIn('"quota_scope": "local_report_roots_only"', result.stdout)
            self.assertIn("local_report_roots_only", result.stdout)
            self.assertFalse((output_dir / "tushare_analyst_report_cache.json").exists())
            self.assertTrue((quota_output_dir / "analyst_report_quota_preflight.json").exists())

    def test_cache_cli_requires_reason_when_skipping_quota_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "cache"
            processed_output_dir = root / "processed"
            _write_processed_window(processed_output_dir, window_start="20240401", window_end="20240430")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_tushare_analyst_report_cache.py",
                    "--start-date",
                    "2024-04-01",
                    "--end-date",
                    "2024-04-30",
                    "--output-dir",
                    str(output_dir),
                    "--processed-output-dir",
                    str(processed_output_dir),
                    "--request-sleep-seconds",
                    "0",
                    "--skip-quota-preflight",
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("--skip-quota-preflight-reason", result.stderr)

    def test_cache_cli_records_skip_reason_before_cached_replay(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "cache"
            processed_output_dir = root / "processed"
            _write_processed_window(processed_output_dir, window_start="20240401", window_end="20240430")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_tushare_analyst_report_cache.py",
                    "--start-date",
                    "2024-04-01",
                    "--end-date",
                    "2024-04-30",
                    "--output-dir",
                    str(output_dir),
                    "--processed-output-dir",
                    str(processed_output_dir),
                    "--request-sleep-seconds",
                    "0",
                    "--skip-quota-preflight",
                    "--skip-quota-preflight-reason",
                    "offline cached replay",
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn('"status": "skipped"', result.stdout)
            self.assertIn("offline cached replay", result.stdout)
            skip_audit = json.loads((output_dir / "skip_quota_preflight_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(skip_audit["status"], "skipped")
            self.assertTrue((output_dir / "skip_quota_preflight_audit.md").exists())
            self.assertTrue((output_dir / "tushare_analyst_report_cache.json").exists())

    def test_cache_cli_skip_quota_preflight_blocks_when_cached_window_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "cache"
            processed_output_dir = root / "processed"
            argv = [
                "run_tushare_analyst_report_cache.py",
                "--start-date",
                "2024-04-01",
                "--end-date",
                "2024-04-30",
                "--output-dir",
                str(output_dir),
                "--processed-output-dir",
                str(processed_output_dir),
                "--request-sleep-seconds",
                "0",
                "--skip-quota-preflight",
                "--skip-quota-preflight-reason",
                "offline cached replay",
            ]

            stdout = io.StringIO()
            with (
                patch.object(sys, "argv", argv),
                patch("sys.stdout", stdout),
                patch.object(cache_cli, "run_tushare_analyst_report_cache") as run_cache,
            ):
                run_cache.return_value = {"summary": {}, "processed_output_dir": str(processed_output_dir), "safety": "test"}
                with self.assertRaises(SystemExit) as raised:
                    cache_cli.main()

            self.assertEqual(raised.exception.code, 3)
            self.assertIn("skip_quota_preflight_requires_cached_processed_windows", stdout.getvalue())
            run_cache.assert_not_called()
            skip_audit = json.loads((output_dir / "skip_quota_preflight_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(skip_audit["status"], "blocked")
            self.assertEqual(skip_audit["summary"]["missing_cached_window_count"], 1)
            self.assertTrue((output_dir / "skip_quota_preflight_audit.md").exists())
            self.assertFalse((output_dir / "tushare_analyst_report_cache.json").exists())

    def test_cache_cli_preflight_only_stops_after_allowed_quota_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_root = root / "reports"
            output_dir = root / "cache"
            processed_output_dir = root / "processed"
            quota_output_dir = root / "preflight"
            report_root.mkdir()

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_tushare_analyst_report_cache.py",
                    "--start-date",
                    "2024-04-01",
                    "--end-date",
                    "2024-04-30",
                    "--output-dir",
                    str(output_dir),
                    "--processed-output-dir",
                    str(processed_output_dir),
                    "--request-sleep-seconds",
                    "0",
                    "--quota-report-root",
                    str(report_root),
                    "--quota-target-date",
                    "2026-07-06",
                    "--quota-output-dir",
                    str(quota_output_dir),
                    "--quota-preflight-only",
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn('"status": "allowed"', result.stdout)
            self.assertIn('"status": "preflight_only"', result.stdout)
            self.assertFalse((output_dir / "tushare_analyst_report_cache.json").exists())
            self.assertTrue((quota_output_dir / "analyst_report_quota_preflight.json").exists())

    def test_cache_cli_preflight_only_cannot_skip_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_tushare_analyst_report_cache.py",
                    "--output-dir",
                    str(root / "cache"),
                    "--skip-quota-preflight",
                    "--skip-quota-preflight-reason",
                    "offline cached replay",
                    "--quota-preflight-only",
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot be combined", result.stderr)

    def test_cache_cli_help_explains_quota_safe_modes(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run_tushare_analyst_report_cache.py", "--help"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("does not call Tushare", result.stdout)
        self.assertIn("exits 3", result.stdout)
        self.assertIn("offline or controlled local replay", result.stdout)
        self.assertIn("provider-backed cache requires the local generated date", " ".join(result.stdout.split()))
        self.assertIn("requires existing processed windows", " ".join(result.stdout.split()))
        self.assertIn("quota-constrained analyst-report path", result.stdout)
        self.assertIn("single monthly window after quota preflight allows", result.stdout)
        self.assertIn("--quota-required-pack-machine", result.stdout)
        self.assertIn("--skip-quota-preflight-reason", result.stdout)

    def test_standalone_preflight_help_explains_exit_codes_and_scope(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/run_analyst_report_quota_preflight.py", "--help"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0)
        normalized = " ".join(result.stdout.split())
        self.assertIn("does not call Tushare", result.stdout)
        self.assertIn("local report roots only", result.stdout)
        self.assertIn("Without --fail-on-blocked", normalized)
        self.assertIn("blocked preflight still exits 0", normalized)
        self.assertIn("repeat to include quota packs", normalized)
        self.assertIn("--required-quota-pack-machine", result.stdout)

    def test_cache_cli_blocks_provider_cache_when_quota_target_date_is_not_local_date(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_root = root / "reports"
            output_dir = root / "cache"
            processed_output_dir = root / "processed"
            quota_output_dir = root / "preflight"
            report_root.mkdir()
            nonlocal_date = (date.today() + timedelta(days=1)).isoformat()

            argv = [
                "run_tushare_analyst_report_cache.py",
                "--start-date",
                "2024-04-01",
                "--end-date",
                "2024-04-30",
                "--output-dir",
                str(output_dir),
                "--processed-output-dir",
                str(processed_output_dir),
                "--request-sleep-seconds",
                "0",
                "--quota-report-root",
                str(report_root),
                "--quota-target-date",
                nonlocal_date,
                "--quota-output-dir",
                str(quota_output_dir),
            ]

            stdout = io.StringIO()
            with (
                patch.object(sys, "argv", argv),
                patch("sys.stdout", stdout),
                patch.object(cache_cli, "run_tushare_analyst_report_cache") as run_cache,
            ):
                with self.assertRaises(SystemExit) as raised:
                    cache_cli.main()

        self.assertEqual(raised.exception.code, 3)
        self.assertIn("quota_target_date_differs_from_generated_at", stdout.getvalue())
        run_cache.assert_not_called()

    def test_cache_cli_blocks_when_required_quota_pack_machine_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack = root / "quota_pack"
            quota_report_root = pack / "quota_report_roots" / "report_a"
            output_dir = root / "cache"
            processed_output_dir = root / "processed"
            quota_output_dir = root / "preflight"
            pack.mkdir(parents=True)
            (pack / "analyst_report_quota_pack_manifest.json").write_text(
                json.dumps(
                    {
                        "generated_at": "2026-07-05",
                        "provenance": {
                            "machine": "office_desktop",
                            "task": "factor_batch",
                            "branch": "codex/factor-batch-cn-stock-profit-mining-20260704",
                        },
                        "summary": {"exported_report_count": 1},
                    }
                ),
                encoding="utf-8",
            )
            _write_cache(quota_report_root, generated_at="2026-07-05", status="ok")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_tushare_analyst_report_cache.py",
                    "--start-date",
                    "2024-04-01",
                    "--end-date",
                    "2024-04-30",
                    "--output-dir",
                    str(output_dir),
                    "--processed-output-dir",
                    str(processed_output_dir),
                    "--request-sleep-seconds",
                    "0",
                    "--quota-report-root",
                    str(pack),
                    "--quota-target-date",
                    "2026-07-05",
                    "--quota-output-dir",
                    str(quota_output_dir),
                    "--quota-required-pack-machine",
                    "office_desktop",
                    "--quota-required-pack-machine",
                    "laptop",
                    "--quota-preflight-only",
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

            packet = json.loads((quota_output_dir / "analyst_report_quota_preflight.json").read_text(encoding="utf-8"))

        self.assertEqual(result.returncode, 3)
        self.assertIn("missing_required_quota_pack_machines", result.stdout)
        self.assertEqual(packet["summary"]["present_quota_pack_machines"], ["office_desktop"])
        self.assertEqual(packet["summary"]["missing_required_quota_pack_machines"], ["laptop"])
        self.assertFalse((output_dir / "tushare_analyst_report_cache.json").exists())


def _write_cache(
    root: Path,
    *,
    generated_at: str,
    status: str,
    provider_rate_limit: str | None = None,
    retry_after_seconds: int | None = None,
) -> None:
    root.mkdir(parents=True, exist_ok=True)
    row = {
        "window_start": "20240201",
        "window_end": "20240229",
        "rows": 100,
        "status": status,
    }
    if provider_rate_limit:
        row["provider_rate_limit"] = provider_rate_limit
    if retry_after_seconds is not None:
        row["retry_after_seconds"] = retry_after_seconds
    payload = {
        "stage": "tushare_analyst_report_cache",
        "source": "tushare_report_rc",
        "generated_at": generated_at,
        "start_date": "2024-02-01",
        "end_date": "2024-02-29",
        "summary": {
            "fetched_windows": 1 if status in {"ok", "cap_warning"} else 0,
            "rate_limited_windows": 1 if provider_rate_limit else 0,
            "next_retry_after_seconds": retry_after_seconds,
        },
        "rows_by_window": [row],
        "live_boundary_allowed": False,
    }
    (root / "tushare_analyst_report_cache.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_processed_window(root: Path, *, window_start: str, window_end: str) -> None:
    frame = pd.DataFrame(
        [
            {
                "report_date": "2024-04-15",
                "symbol": "000001.SZ",
                "name": "Ping An Bank",
                "org_name": "Local Fixture",
                "author_name": "Analyst",
                "report_title": "Cached analyst report",
                "report_type": "company",
                "rating": "buy",
                "quarter": "2024Q1",
                "eps": 1.0,
                "np": 100.0,
                "roe": 0.1,
                "tp": 10.0,
                "min_price": 9.0,
                "max_price": 11.0,
                "pe": 8.0,
                "op_rt": 0.1,
                "op_pr": 0.1,
                "ev_ebitda": 7.0,
            }
        ]
    )
    DatasetStore(root).write_frame(
        frame,
        "processed/analyst_report_rc_window",
        {"window_start": window_start, "window_end": window_end},
    )


if __name__ == "__main__":
    unittest.main()
