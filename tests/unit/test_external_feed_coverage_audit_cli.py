import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_external_feed_coverage_audit import main


class ExternalFeedCoverageAuditCliTests(unittest.TestCase):
    def test_cli_passes_thresholds_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "scripts.run_external_feed_coverage_audit.run_external_feed_coverage_audit",
                return_value={"summary": {"blocked_count": 0}},
            ) as run_audit:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(Path(tmp) / "processed"),
                            "--output-dir",
                            str(Path(tmp) / "out"),
                            "--min-hk-hold-observation-dates",
                            "40",
                            "--max-hk-hold-median-gap-days",
                            "7",
                            "--min-macro-observation-dates",
                            "90",
                            "--min-lpr-non-null-ratio",
                            "0.9",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_audit.assert_called_once()
        self.assertEqual(run_audit.call_args.kwargs["processed_root"], Path(tmp) / "processed")
        self.assertEqual(run_audit.call_args.kwargs["output_dir"], Path(tmp) / "out")
        self.assertEqual(run_audit.call_args.kwargs["min_hk_hold_observation_dates"], 40)
        self.assertEqual(run_audit.call_args.kwargs["max_hk_hold_median_gap_days"], 7)
        self.assertEqual(run_audit.call_args.kwargs["min_macro_observation_dates"], 90)
        self.assertEqual(run_audit.call_args.kwargs["min_lpr_non_null_ratio"], 0.9)


if __name__ == "__main__":
    unittest.main()
