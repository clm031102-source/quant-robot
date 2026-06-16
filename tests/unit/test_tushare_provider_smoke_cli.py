import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_tushare_provider_smoke import run_tushare_provider_smoke


class TushareProviderSmokeCliTests(unittest.TestCase):
    def test_fixture_provider_smoke_writes_compact_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_provider_smoke(
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
                source="tushare-fixture",
                execute=True,
            )

            summary_path = Path(tmp) / "provider_smoke_summary.json"
            saved = json.loads(summary_path.read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "completed")
            self.assertEqual(saved["status"], "completed")
            self.assertEqual([row["interface"] for row in saved["interfaces"]], ["daily", "daily_basic", "moneyflow"])
            self.assertEqual(saved["interfaces"][0]["rows"], 4)
            self.assertEqual(saved["interfaces"][1]["missing_numeric_rows"], 0)
            self.assertEqual(saved["interfaces"][1]["missing_numeric_by_column"], {})
            self.assertIn("adjustment_report", saved["interfaces"][0])

    def test_live_provider_smoke_dry_run_does_not_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_tushare_provider_smoke(
                "2024-01-02",
                "2024-01-03",
                Path(tmp),
                source="tushare",
                execute=False,
                readiness={"source": "tushare", "ready": True, "missing": []},
            )

            self.assertEqual(result["status"], "ready")
            self.assertEqual(result["mode"], "dry_run")
            self.assertEqual(result["interfaces"], [])
            self.assertFalse((Path(tmp) / "daily").exists())


if __name__ == "__main__":
    unittest.main()
