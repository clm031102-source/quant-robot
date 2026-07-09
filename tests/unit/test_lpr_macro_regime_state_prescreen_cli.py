import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_lpr_macro_regime_state_prescreen import main


class LPRMacroRegimeStatePrescreenCliTests(unittest.TestCase):
    def test_cli_passes_paths_and_thresholds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_lpr_macro_regime_state_prescreen.run_lpr_macro_regime_state_prescreen",
                return_value={"summary": {"passes": True}, "data_window": {}},
            ) as run_prescreen:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(root / "processed"),
                            "--readiness-gate",
                            str(root / "ready.json"),
                            "--candidate-plan",
                            str(root / "plan.json"),
                            "--output-dir",
                            str(root / "out"),
                            "--analysis-start-date",
                            "2024-07-01",
                            "--analysis-end-date",
                            "2025-12-31",
                            "--lookback-days",
                            "60",
                            "--min-abs-gap-change",
                            "0.01",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_prescreen.assert_called_once()
        self.assertEqual(run_prescreen.call_args.kwargs["processed_root"], Path(root / "processed"))
        self.assertEqual(run_prescreen.call_args.kwargs["readiness_gate_path"], Path(root / "ready.json"))
        self.assertEqual(run_prescreen.call_args.kwargs["candidate_plan_path"], Path(root / "plan.json"))
        self.assertEqual(run_prescreen.call_args.kwargs["lookback_days"], 60)
        self.assertEqual(run_prescreen.call_args.kwargs["min_abs_gap_change"], 0.01)


if __name__ == "__main__":
    unittest.main()
