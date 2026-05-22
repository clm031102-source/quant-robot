import tempfile
import unittest
from pathlib import Path

from quant_robot.data.tushare_smoke import build_tushare_smoke_plan, run_tushare_smoke


class TushareSmokeTests(unittest.TestCase):
    def test_dry_run_never_downloads_and_reports_missing_readiness(self):
        result = run_tushare_smoke(
            "2024-01-02",
            "2024-01-03",
            Path("data/raw/tushare_smoke"),
            execute=False,
            readiness={"ready": False, "missing": ["TUSHARE_TOKEN is not set"]},
        )

        self.assertEqual(result["mode"], "dry_run")
        self.assertFalse(result["will_download"])
        self.assertEqual(result["status"], "blocked")

    def test_execute_requires_ready_dependencies_before_ingest(self):
        result = run_tushare_smoke(
            "2024-01-02",
            "2024-01-03",
            Path("data/raw/tushare_smoke"),
            execute=True,
            readiness={"ready": False, "missing": ["tushare package is not installed"]},
        )

        self.assertEqual(result["mode"], "execute")
        self.assertFalse(result["will_download"])
        self.assertEqual(result["status"], "blocked")

    def test_execute_calls_ingest_when_ready(self):
        calls = []

        def fake_ingest(start_date, end_date, output_dir):
            calls.append((start_date, end_date, output_dir))
            return {"processed_rows": 2}

        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_smoke(
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
                execute=True,
                readiness={"ready": True, "missing": []},
                ingest_runner=fake_ingest,
            )

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["will_download"])
        self.assertEqual(len(calls), 1)

    def test_plan_marks_execute_as_download_intent(self):
        dry = build_tushare_smoke_plan("2024-01-02", "2024-01-03", Path("out"), execute=False)
        live = build_tushare_smoke_plan("2024-01-02", "2024-01-03", Path("out"), execute=True)

        self.assertFalse(dry["will_download"])
        self.assertTrue(live["will_download"])


if __name__ == "__main__":
    unittest.main()
