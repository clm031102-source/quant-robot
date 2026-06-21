import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_fina_indicator_backfill_plan import run_fina_indicator_backfill_plan_cli


class FinaIndicatorBackfillPlanCliTests(unittest.TestCase):
    def test_cli_writes_plan_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "report"

            result = run_fina_indicator_backfill_plan_cli(
                symbols=["000001.SZ", "600519.SH"],
                start_period="2015-03-31",
                end_period="2025-12-31",
                batch_size=20,
                max_requests=200,
                output_dir=output_dir,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertTrue((output_dir / "fina_indicator_backfill_plan.json").exists())
            self.assertTrue((output_dir / "fina_indicator_backfill_plan.md").exists())
            payload = json.loads((output_dir / "fina_indicator_backfill_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["request_count"], 88)

    def test_cli_reads_symbols_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            symbols_file = root / "symbols.csv"
            symbols_file.write_text("symbol\n000001.SZ\n600519.SH\n", encoding="utf-8")

            result = run_fina_indicator_backfill_plan_cli(
                symbols=[],
                symbols_file=symbols_file,
                start_period="2024-03-31",
                end_period="2024-06-30",
                batch_size=10,
                max_requests=10,
                output_dir=root / "report",
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["symbol_count"], 2)
            self.assertEqual(result["summary"]["period_count"], 2)


if __name__ == "__main__":
    unittest.main()
