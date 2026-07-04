import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.analyst_report_quota_preflight import (
    build_analyst_report_quota_preflight,
    write_analyst_report_quota_preflight,
)
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


if __name__ == "__main__":
    unittest.main()
