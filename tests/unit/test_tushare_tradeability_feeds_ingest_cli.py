import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_tushare_tradeability_feed_ingest import main


class TushareTradeabilityFeedIngestCliTests(unittest.TestCase):
    def test_cli_passes_report_only_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch("scripts.run_tushare_tradeability_feed_ingest.TushareAdapter") as adapter_cls:
                with patch(
                    "scripts.run_tushare_tradeability_feed_ingest.run_tushare_tradeability_feed_ingest",
                    return_value={"summary": {"feed_count": 4}},
                ) as run_ingest:
                    exit_code = main(
                        [
                            "--start-date",
                            "2024-01-02",
                            "--end-date",
                            "2024-01-03",
                            "--output-dir",
                            tmp,
                            "--processed-output-dir",
                            str(Path(tmp) / "processed"),
                            "--snapshot",
                            "2026-06-23",
                        ]
                    )

            self.assertEqual(exit_code, 0)
            run_ingest.assert_called_once()
            kwargs = run_ingest.call_args.kwargs
            self.assertEqual(kwargs["start_date"], "2024-01-02")
            self.assertEqual(kwargs["end_date"], "2024-01-03")
            self.assertEqual(kwargs["output_dir"], Path(tmp))
            self.assertEqual(kwargs["processed_output_dir"], Path(tmp) / "processed")
            self.assertFalse(kwargs["execute_write_processed"])
            self.assertEqual(kwargs["snapshot"], "2026-06-23")
            adapter_cls.assert_called_once()


if __name__ == "__main__":
    unittest.main()
