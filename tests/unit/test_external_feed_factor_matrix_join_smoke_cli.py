import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_external_feed_factor_matrix_join_smoke import main


class ExternalFeedFactorMatrixJoinSmokeCliTests(unittest.TestCase):
    def test_cli_passes_paths_and_optional_signal_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch(
                "scripts.run_external_feed_factor_matrix_join_smoke.run_external_feed_factor_matrix_join_smoke",
                return_value={"summary": {"seed_count": 1}},
            ) as run_smoke:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(Path(tmp) / "processed"),
                            "--seed-config",
                            str(Path(tmp) / "seeds.json"),
                            "--output-dir",
                            str(Path(tmp) / "out"),
                            "--signal-start-date",
                            "2024-01-02",
                            "--signal-end-date",
                            "2024-01-03",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_smoke.assert_called_once()
        self.assertEqual(run_smoke.call_args.kwargs["processed_root"], Path(tmp) / "processed")
        self.assertEqual(run_smoke.call_args.kwargs["signal_start_date"], "2024-01-02")
        self.assertEqual(run_smoke.call_args.kwargs["signal_end_date"], "2024-01-03")


if __name__ == "__main__":
    unittest.main()
