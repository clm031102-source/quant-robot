import json
import tempfile
import unittest
from pathlib import Path

from scripts.ingest_data import run_ingest


class IngestCliTests(unittest.TestCase):
    def test_fixture_ingest_writes_quality_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_ingest(source="fixture", market="CN", output_dir=Path(tmp))

            report_path = Path(tmp) / "quality_report.json"
            self.assertTrue(report_path.exists())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(result["market"], "CN")
            self.assertEqual(report["markets"], ["CN"])
            self.assertGreater(report["rows"], 0)

    def test_tushare_fixture_ingest_writes_manifest_and_processed_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_ingest(source="tushare-fixture", market="CN", output_dir=Path(tmp))

            self.assertEqual(result["source"], "tushare")
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "quality_report.json").exists())
            self.assertGreater(result["processed_rows"], 0)

    def test_tushare_factor_fixture_ingest_writes_factor_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_ingest(source="tushare-factor-fixture", market="CN", output_dir=Path(tmp))

            self.assertEqual(result["dataset"], "daily_basic")
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "factor_input_quality_report.json").exists())
            self.assertGreater(result["processed_rows"], 0)

    def test_tushare_moneyflow_fixture_ingest_writes_moneyflow_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_ingest(source="tushare-moneyflow-fixture", market="CN", output_dir=Path(tmp))

            self.assertEqual(result["dataset"], "moneyflow")
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "moneyflow_input_quality_report.json").exists())
            self.assertGreater(result["processed_rows"], 0)

    def test_tushare_fina_indicator_fixture_ingest_writes_financial_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_ingest(
                source="tushare-fina-indicator-fixture",
                market="CN",
                output_dir=Path(tmp),
                start_date="2024-03-31",
                end_date="2024-06-30",
            )

            self.assertEqual(result["dataset"], "fina_indicator")
            self.assertTrue((Path(tmp) / "manifest.json").exists())
            self.assertTrue((Path(tmp) / "financial_input_quality_report.json").exists())
            self.assertGreater(result["processed_rows"], 0)

    def test_tushare_fina_indicator_fixture_ingest_accepts_symbol_subset(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_ingest(
                source="tushare-fina-indicator-fixture",
                market="CN",
                output_dir=Path(tmp),
                start_date="2024-03-31",
                end_date="2024-03-31",
                symbols=["000001.SZ"],
            )

            self.assertEqual(result["dataset"], "fina_indicator")
            self.assertEqual(result["processed_rows"], 1)
            self.assertEqual(result["downloaded_requests"], ["000001.SZ:20240331"])


if __name__ == "__main__":
    unittest.main()
