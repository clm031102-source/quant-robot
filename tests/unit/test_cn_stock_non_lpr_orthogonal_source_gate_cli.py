import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_cn_stock_non_lpr_orthogonal_source_gate import main


class CNStockNonLPROrthogonalSourceGateCliTests(unittest.TestCase):
    def test_cli_defaults_to_latest_post_lpr_rejection_readiness_gate(self) -> None:
        with patch(
            "scripts.run_cn_stock_non_lpr_orthogonal_source_gate.run_cn_stock_non_lpr_orthogonal_source_gate",
            return_value={"status": "blocked", "summary": {}, "decision": {"blockers": []}},
        ) as run_gate:
            with redirect_stdout(StringIO()):
                exit_code = main(["--allow-blocked"])

        self.assertEqual(exit_code, 0)
        self.assertIn(
            "round748_factor_batch_readiness_after_source_queue_hibernation_20260709",
            str(run_gate.call_args.kwargs["readiness_gate_path"]),
        )
        self.assertIn(
            "round748_non_lpr_source_gate_after_source_queue_hibernation_20260709",
            str(run_gate.call_args.kwargs["output_dir"]),
        )

    def test_cli_passes_input_paths_and_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_cn_stock_non_lpr_orthogonal_source_gate.run_cn_stock_non_lpr_orthogonal_source_gate",
                return_value={"status": "blocked", "summary": {}, "decision": {"blockers": []}},
            ) as run_gate:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--round738-rotation-gate",
                            str(root / "round738.json"),
                            "--readiness-gate",
                            str(root / "round729_readiness.json"),
                            "--analyst-prescreen",
                            str(root / "round729_prescreen.json"),
                            "--output-dir",
                            str(root / "out"),
                            "--allow-blocked",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_gate.assert_called_once()
        self.assertEqual(run_gate.call_args.kwargs["round738_rotation_gate_path"], Path(root / "round738.json"))
        self.assertEqual(run_gate.call_args.kwargs["readiness_gate_path"], Path(root / "round729_readiness.json"))
        self.assertEqual(run_gate.call_args.kwargs["analyst_prescreen_path"], Path(root / "round729_prescreen.json"))
        self.assertEqual(run_gate.call_args.kwargs["output_dir"], Path(root / "out"))

    def test_cli_raises_on_blocked_without_override(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_cn_stock_non_lpr_orthogonal_source_gate.run_cn_stock_non_lpr_orthogonal_source_gate",
                return_value={"status": "blocked", "summary": {}, "decision": {"blockers": ["provider_quota_preflight_blocked"]}},
            ):
                with self.assertRaisesRegex(RuntimeError, "not ready"):
                    main(
                        [
                            "--round738-rotation-gate",
                            str(root / "round738.json"),
                            "--readiness-gate",
                            str(root / "round729_readiness.json"),
                            "--analyst-prescreen",
                            str(root / "round729_prescreen.json"),
                            "--output-dir",
                            str(root / "out"),
                        ]
                    )


if __name__ == "__main__":
    unittest.main()
