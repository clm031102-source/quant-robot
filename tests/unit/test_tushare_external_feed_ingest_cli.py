import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_tushare_external_feed_ingest import main


class TushareExternalFeedIngestCliTests(unittest.TestCase):
    def test_cli_defaults_to_report_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.run_tushare_external_feed_ingest.TushareAdapter") as adapter_cls:
                adapter = adapter_cls.return_value
                with patch(
                    "scripts.run_tushare_external_feed_ingest.run_tushare_external_feed_ingest",
                    return_value={"summary": {"feed_count": 5}},
                ) as run_ingest:
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--start-date",
                                "2024-01-02",
                                "--end-date",
                                "2024-01-03",
                                "--output-dir",
                                tmp,
                            ]
                        )

            self.assertEqual(exit_code, 0)
            run_ingest.assert_called_once()
            self.assertIs(run_ingest.call_args.args[0], adapter)
            self.assertEqual(run_ingest.call_args.args[1], "2024-01-02")
            self.assertEqual(run_ingest.call_args.args[2], "2024-01-03")
            self.assertEqual(run_ingest.call_args.args[3], Path(tmp))
            self.assertFalse(run_ingest.call_args.kwargs["execute_write_processed"])

    def test_cli_requires_explicit_flag_for_processed_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.run_tushare_external_feed_ingest.TushareAdapter"):
                with patch(
                    "scripts.run_tushare_external_feed_ingest.run_tushare_external_feed_ingest",
                    return_value={"summary": {"feed_count": 5}},
                ) as run_ingest:
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--start-date",
                                "2024-01-02",
                                "--end-date",
                                "2024-01-03",
                                "--output-dir",
                                tmp,
                                "--execute-write-processed",
                            ]
                        )

            self.assertEqual(exit_code, 0)
            self.assertTrue(run_ingest.call_args.kwargs["execute_write_processed"])

    def test_cli_can_copy_report_to_separate_shard_report_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "processed_root"
            report_copy_dir = Path(tmp) / "reports" / "shard_202501"
            with patch("scripts.run_tushare_external_feed_ingest.TushareAdapter"):
                with patch(
                    "scripts.run_tushare_external_feed_ingest.run_tushare_external_feed_ingest",
                    return_value={"summary": {"feed_count": 5}, "processed_writes_enabled": True},
                ):
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--start-date",
                                "2024-01-02",
                                "--end-date",
                                "2024-01-03",
                                "--output-dir",
                                str(output_dir),
                                "--execute-write-processed",
                                "--report-copy-dir",
                                str(report_copy_dir),
                            ]
                        )

            self.assertEqual(exit_code, 0)
            copied = report_copy_dir / "external_feed_ingestion_report.json"
            self.assertTrue(copied.exists())

    def test_cli_can_write_progress_events_to_jsonl_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            progress_jsonl = Path(tmp) / "progress.jsonl"

            def fake_ingest(*args, **kwargs):
                kwargs["progress_callback"](
                    {"endpoint": "margin_detail", "trade_date": "20240102", "status": "start"}
                )
                return {"summary": {"feed_count": 5}, "processed_writes_enabled": True}

            with patch("scripts.run_tushare_external_feed_ingest.TushareAdapter"):
                with patch(
                    "scripts.run_tushare_external_feed_ingest.run_tushare_external_feed_ingest",
                    side_effect=fake_ingest,
                ):
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--start-date",
                                "2024-01-02",
                                "--end-date",
                                "2024-01-03",
                                "--output-dir",
                                str(Path(tmp) / "processed_root"),
                                "--execute-write-processed",
                                "--progress-jsonl",
                                str(progress_jsonl),
                            ]
                        )

            self.assertEqual(exit_code, 0)
            self.assertTrue(progress_jsonl.exists())
            self.assertIn('"endpoint": "margin_detail"', progress_jsonl.read_text(encoding="utf-8"))

    def test_cli_passes_explicit_lpr_cache_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            lpr_cache_path = Path(tmp) / "lpr" / "cache.json"
            with patch("scripts.run_tushare_external_feed_ingest.TushareAdapter"):
                with patch(
                    "scripts.run_tushare_external_feed_ingest.run_tushare_external_feed_ingest",
                    return_value={"summary": {"feed_count": 5}, "processed_writes_enabled": False},
                ) as run_ingest:
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--start-date",
                                "2024-01-02",
                                "--end-date",
                                "2024-01-03",
                                "--output-dir",
                                str(Path(tmp) / "report"),
                                "--lpr-cache-path",
                                str(lpr_cache_path),
                            ]
                        )

            self.assertEqual(exit_code, 0)
            self.assertEqual(run_ingest.call_args.kwargs["lpr_cache_path"], lpr_cache_path)


if __name__ == "__main__":
    unittest.main()
