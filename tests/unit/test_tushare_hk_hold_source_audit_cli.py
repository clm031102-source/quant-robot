import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_tushare_hk_hold_source_audit import main


class TushareHkHoldSourceAuditCliTests(unittest.TestCase):
    def test_cli_passes_trade_dates_and_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "report"
            with patch("scripts.run_tushare_hk_hold_source_audit.TushareAdapter") as adapter_cls:
                adapter = adapter_cls.return_value
                with patch(
                    "scripts.run_tushare_hk_hold_source_audit.build_tushare_hk_hold_source_audit",
                    return_value={
                        "stage": "tushare_hk_hold_source_audit",
                        "summary": {"requested_date_count": 2},
                        "date_rows": [],
                    },
                ) as build_audit:
                    with redirect_stdout(StringIO()):
                        exit_code = main(
                            [
                                "--trade-date",
                                "2024-08-16",
                                "--trade-date",
                                "2024-08-19",
                                "--output-dir",
                                str(output_dir),
                            ]
                        )

            self.assertEqual(exit_code, 0)
            build_audit.assert_called_once()
            self.assertIs(build_audit.call_args.args[0], adapter)
            self.assertEqual(build_audit.call_args.kwargs["trade_dates"], ["2024-08-16", "2024-08-19"])
            self.assertTrue((output_dir / "tushare_hk_hold_source_audit.json").exists())


if __name__ == "__main__":
    unittest.main()
