import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_external_macro_lpr_repair import main


class ExternalMacroLprRepairCliTests(unittest.TestCase):
    def test_cli_passes_paths_and_copy_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = Path(tmp) / "source"
            output_root = Path(tmp) / "out"
            report_dir = Path(tmp) / "report"
            lpr_cache = Path(tmp) / "lpr.json"
            with patch(
                "scripts.run_external_macro_lpr_repair.repair_external_macro_lpr",
                return_value={"status": "pass", "summary": {}},
            ) as repair:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(source_root),
                            "--lpr-cache-path",
                            str(lpr_cache),
                            "--output-root",
                            str(output_root),
                            "--report-dir",
                            str(report_dir),
                            "--copy-other-feeds",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        repair.assert_called_once()
        self.assertEqual(repair.call_args.kwargs["processed_root"], source_root)
        self.assertEqual(repair.call_args.kwargs["lpr_cache_path"], lpr_cache)
        self.assertEqual(repair.call_args.kwargs["output_root"], output_root)
        self.assertEqual(repair.call_args.kwargs["report_dir"], report_dir)
        self.assertTrue(repair.call_args.kwargs["copy_other_feeds"])


if __name__ == "__main__":
    unittest.main()
