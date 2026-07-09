import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_analyst_report_source_extension_priority_gate import main


class AnalystReportSourceExtensionPriorityGateCliTests(unittest.TestCase):
    def test_cli_passes_input_paths_and_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_analyst_report_source_extension_priority_gate.run_analyst_report_source_extension_priority_gate",
                return_value={"status": "blocked_waiting_for_quota", "summary": {}, "decision": {"blockers": []}},
            ) as run_gate:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--source-gate",
                            str(root / "source_gate.json"),
                            "--analyst-prescreen",
                            str(root / "prescreen.json"),
                            "--output-dir",
                            str(root / "out"),
                            "--allow-blocked",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_gate.assert_called_once()
        self.assertEqual(run_gate.call_args.kwargs["source_gate_path"], Path(root / "source_gate.json"))
        self.assertEqual(run_gate.call_args.kwargs["analyst_prescreen_path"], Path(root / "prescreen.json"))
        self.assertEqual(run_gate.call_args.kwargs["output_dir"], Path(root / "out"))

    def test_cli_raises_when_blocked_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_analyst_report_source_extension_priority_gate.run_analyst_report_source_extension_priority_gate",
                return_value={
                    "status": "blocked_waiting_for_quota",
                    "summary": {},
                    "decision": {"blockers": ["provider_quota_preflight_blocked"]},
                },
            ):
                with self.assertRaisesRegex(RuntimeError, "not ready"):
                    main(
                        [
                            "--source-gate",
                            str(root / "source_gate.json"),
                            "--analyst-prescreen",
                            str(root / "prescreen.json"),
                            "--output-dir",
                            str(root / "out"),
                        ]
                    )


if __name__ == "__main__":
    unittest.main()
