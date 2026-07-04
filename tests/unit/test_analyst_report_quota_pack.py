import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.run_analyst_report_quota_preflight import run_analyst_report_quota_preflight


class AnalystReportQuotaPackTests(unittest.TestCase):
    def test_exports_cache_reports_into_portable_preflight_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "source_reports"
            output_dir = root / "quota_pack"
            _write_cache(source_root / "round_a", generated_at="2026-07-05", status="ok")
            _write_non_cache_report(source_root / "other")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/export_analyst_report_quota_pack.py",
                    "--report-root",
                    str(source_root),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

            manifest = json.loads((output_dir / "analyst_report_quota_pack_manifest.json").read_text(encoding="utf-8"))
            exported_reports = list(output_dir.rglob("tushare_analyst_report_cache.json"))
            preflight = run_analyst_report_quota_preflight(
                report_root=[output_dir],
                output_dir=root / "preflight",
                target_date="2026-07-05",
                max_daily_requests=2,
            )

        self.assertEqual(result.returncode, 0)
        self.assertIn('"exported_report_count": 1', result.stdout)
        self.assertEqual(manifest["summary"]["exported_report_count"], 1)
        self.assertEqual(len(exported_reports), 1)
        self.assertEqual(preflight["summary"]["counted_provider_request_windows"], 1)

    def test_output_inside_report_root_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "source_reports"
            output_dir = source_root / "quota_pack"
            _write_cache(source_root / "round_a", generated_at="2026-07-05", status="ok")

            for _ in range(2):
                result = subprocess.run(
                    [
                        sys.executable,
                        "scripts/export_analyst_report_quota_pack.py",
                        "--report-root",
                        str(source_root),
                        "--output-dir",
                        str(output_dir),
                    ],
                    cwd=Path(__file__).resolve().parents[2],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0)

            manifest = json.loads((output_dir / "analyst_report_quota_pack_manifest.json").read_text(encoding="utf-8"))
            exported_reports = list((output_dir / "quota_report_roots").rglob("tushare_analyst_report_cache.json"))
            preflight = run_analyst_report_quota_preflight(
                report_root=[output_dir],
                output_dir=root / "preflight",
                target_date="2026-07-05",
                max_daily_requests=2,
            )
            broad_preflight = run_analyst_report_quota_preflight(
                report_root=[source_root],
                output_dir=root / "broad_preflight",
                target_date="2026-07-05",
                max_daily_requests=2,
            )

        self.assertEqual(manifest["summary"]["exported_report_count"], 1)
        self.assertEqual(len(exported_reports), 1)
        self.assertEqual(preflight["summary"]["counted_provider_request_windows"], 1)
        self.assertEqual(broad_preflight["summary"]["counted_provider_request_windows"], 1)

    def test_duplicate_exported_pack_evidence_counts_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "source_reports"
            pack_a = root / "quota_pack_a"
            pack_b = root / "quota_pack_b"
            _write_cache(source_root / "round_a", generated_at="2026-07-05", status="ok")

            for output_dir in (pack_a, pack_b):
                result = subprocess.run(
                    [
                        sys.executable,
                        "scripts/export_analyst_report_quota_pack.py",
                        "--report-root",
                        str(source_root),
                        "--output-dir",
                        str(output_dir),
                    ],
                    cwd=Path(__file__).resolve().parents[2],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0)

            preflight = run_analyst_report_quota_preflight(
                report_root=[pack_a, pack_b],
                output_dir=root / "duplicate_pack_preflight",
                target_date="2026-07-05",
                max_daily_requests=2,
            )

        self.assertEqual(preflight["summary"]["counted_provider_request_windows"], 1)
        self.assertEqual(preflight["summary"]["duplicate_evidence_rows"], 1)

    def test_local_report_and_its_exported_pack_count_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "source_reports"
            pack = root / "quota_pack"
            _write_cache(source_root / "round_a", generated_at="2026-07-05", status="ok")

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/export_analyst_report_quota_pack.py",
                    "--report-root",
                    str(source_root),
                    "--output-dir",
                    str(pack),
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0)

            preflight = run_analyst_report_quota_preflight(
                report_root=[source_root, pack],
                output_dir=root / "local_and_pack_preflight",
                target_date="2026-07-05",
                max_daily_requests=2,
            )

        self.assertEqual(preflight["summary"]["counted_provider_request_windows"], 1)
        self.assertEqual(preflight["summary"]["duplicate_evidence_rows"], 1)

    def test_export_broad_scan_skips_existing_quota_pack_internals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "source_reports"
            existing_pack = source_root / "existing_quota_pack"
            fresh_pack = root / "fresh_quota_pack"
            _write_cache(source_root / "round_a", generated_at="2026-07-05", status="ok")

            first_export = subprocess.run(
                [
                    sys.executable,
                    "scripts/export_analyst_report_quota_pack.py",
                    "--report-root",
                    str(source_root),
                    "--output-dir",
                    str(existing_pack),
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(first_export.returncode, 0)

            second_export = subprocess.run(
                [
                    sys.executable,
                    "scripts/export_analyst_report_quota_pack.py",
                    "--report-root",
                    str(source_root),
                    "--output-dir",
                    str(fresh_pack),
                ],
                cwd=Path(__file__).resolve().parents[2],
                capture_output=True,
                text=True,
                check=False,
            )

            manifest = json.loads((fresh_pack / "analyst_report_quota_pack_manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(second_export.returncode, 0)
        self.assertEqual(manifest["summary"]["exported_report_count"], 1)


def _write_cache(root: Path, *, generated_at: str, status: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": "tushare_analyst_report_cache",
        "source": "tushare_report_rc",
        "generated_at": generated_at,
        "rows_by_window": [
            {
                "window_start": "20240401",
                "window_end": "20240430",
                "rows": 10,
                "status": status,
            }
        ],
    }
    (root / "tushare_analyst_report_cache.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_non_cache_report(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "tushare_analyst_report_cache.json").write_text(
        json.dumps({"stage": "other", "generated_at": "2026-07-05"}),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
