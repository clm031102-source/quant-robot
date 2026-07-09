import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_lpr_macro_regime_walk_forward_rejection_rotation_gate import main


class LPRMacroRegimeWalkForwardRejectionRotationGateCliTests(unittest.TestCase):
    def test_cli_passes_validation_path_and_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_lpr_macro_regime_walk_forward_rejection_rotation_gate.run_lpr_macro_regime_walk_forward_rejection_rotation_gate",
                return_value={"status": "cleared", "summary": {}, "decision": {}, "rotation_policy": {}},
            ) as run_gate:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--validation",
                            str(root / "round737.json"),
                            "--output-dir",
                            str(root / "out"),
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_gate.assert_called_once()
        self.assertEqual(run_gate.call_args.kwargs["validation_path"], Path(root / "round737.json"))
        self.assertEqual(run_gate.call_args.kwargs["output_dir"], Path(root / "out"))

    def test_cli_blocks_uncleared_gate_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_lpr_macro_regime_walk_forward_rejection_rotation_gate.run_lpr_macro_regime_walk_forward_rejection_rotation_gate",
                return_value={
                    "status": "blocked",
                    "summary": {},
                    "decision": {"blockers": ["walk_forward_validation_not_rejected"]},
                    "rotation_policy": {},
                },
            ):
                with self.assertRaisesRegex(RuntimeError, "not cleared"):
                    main(
                        [
                            "--validation",
                            str(root / "round737.json"),
                            "--output-dir",
                            str(root / "out"),
                        ]
                    )


if __name__ == "__main__":
    unittest.main()
