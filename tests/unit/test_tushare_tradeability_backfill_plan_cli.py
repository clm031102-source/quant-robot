import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_tushare_tradeability_backfill_plan import main


class TushareTradeabilityBackfillPlanCliTests(unittest.TestCase):
    def test_cli_plan_only_writes_outputs_without_adapter(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "plan"
            with patch("scripts.run_tushare_tradeability_backfill_plan.TushareAdapter") as adapter_cls:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--start-date",
                            "2024-01-02",
                            "--end-date",
                            "2024-01-31",
                            "--processed-root",
                            str(Path(tmp) / "processed"),
                            "--output-dir",
                            str(output_dir),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            adapter_cls.assert_not_called()
            self.assertTrue((output_dir / "tushare_tradeability_long_cycle_backfill_plan.json").exists())
            self.assertTrue((output_dir / "tushare_tradeability_long_cycle_backfill_plan.md").exists())

    def test_cli_execute_passes_processed_root_to_ingest(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "plan"
            processed_dir = Path(tmp) / "processed"
            with patch("scripts.run_tushare_tradeability_backfill_plan.TushareAdapter") as adapter_cls:
                with patch(
                    "scripts.run_tushare_tradeability_backfill_plan.run_tushare_tradeability_feed_ingest",
                    return_value={
                        "summary": {"status": "pass", "warn_count": 0, "fail_count": 0},
                        "processed_writes_enabled": True,
                    },
                ) as run_ingest:
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--start-date",
                                "2024-01-02",
                                "--end-date",
                                "2024-01-31",
                                "--processed-root",
                                str(processed_dir),
                                "--output-dir",
                                str(output_dir),
                                "--max-shards",
                                "1",
                                "--snapshot",
                                "2026-06-23",
                                "--execute",
                                "--execute-write-processed",
                            ]
                        )

            self.assertEqual(exit_code, 0)
            adapter_cls.assert_called_once()
            run_ingest.assert_called_once()
            kwargs = run_ingest.call_args.kwargs
            self.assertEqual(kwargs["processed_output_dir"], processed_dir)
            self.assertEqual(kwargs["snapshot"], "2026-06-23")
            self.assertTrue(kwargs["execute_write_processed"])

    def test_cli_passes_skip_covered_to_backfill_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "plan"
            processed_dir = Path(tmp) / "processed"
            with patch("scripts.run_tushare_tradeability_backfill_plan.TushareAdapter") as adapter_cls:
                with patch(
                    "scripts.run_tushare_tradeability_backfill_plan.run_tushare_tradeability_backfill",
                    return_value={
                        "status": "ready",
                        "summary": {"planned_shards": 1, "covered_shards": 0, "selected_shards": 1},
                        "execution_summary": {"executed_shards": 0, "failed_shards": 0},
                        "blockers": [],
                    },
                ) as run_backfill:
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--start-date",
                                "2024-01-02",
                                "--end-date",
                                "2024-01-31",
                                "--processed-root",
                                str(processed_dir),
                                "--output-dir",
                                str(output_dir),
                                "--skip-covered",
                            ]
                        )

            self.assertEqual(exit_code, 0)
            adapter_cls.assert_not_called()
            self.assertTrue(run_backfill.call_args.kwargs["skip_covered"])


if __name__ == "__main__":
    unittest.main()
