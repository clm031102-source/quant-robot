import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_fina_indicator_symbol_shard_plan import run_fina_indicator_symbol_shard_plan_cli


class FinaIndicatorSymbolShardPlanCliTests(unittest.TestCase):
    def test_cli_writes_symbol_file_plan_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            symbols_file = root / "symbols.csv"
            symbols_file.write_text("symbol\n000001.SZ\n000002.SZ\n600519.SH\n", encoding="utf-8")
            output_dir = root / "report"

            result = run_fina_indicator_symbol_shard_plan_cli(
                symbols_file=symbols_file,
                output_dir=output_dir,
                start_period="2024-03-31",
                end_period="2024-06-30",
                symbols_per_shard=2,
                max_requests_per_shard=4,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["symbol_count"], 3)
            self.assertEqual(result["summary"]["shard_count"], 2)
            self.assertTrue((output_dir / "fina_indicator_symbol_shard_plan.json").exists())
            self.assertTrue((output_dir / "fina_indicator_symbol_shard_plan.md").exists())
            payload = json.loads((output_dir / "fina_indicator_symbol_shard_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["total_request_count"], 6)


if __name__ == "__main__":
    unittest.main()
