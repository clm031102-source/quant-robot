import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_lpr_macro_regime_reference_dedup_preflight import main


class LPRMacroRegimeReferenceDedupPreflightCliTests(unittest.TestCase):
    def test_cli_passes_pairwise_residual_reference_and_exposure_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_lpr_macro_regime_reference_dedup_preflight.run_lpr_macro_regime_reference_dedup_preflight",
                return_value={"summary": {"passes": True}, "decision": {}},
            ) as run_preflight:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(root / "processed"),
                            "--pairwise-prescreen",
                            str(root / "pairwise.json"),
                            "--residual-ic",
                            str(root / "a.csv"),
                            "--reference-correlation",
                            str(root / "reference.csv"),
                            "--exposure-correlation",
                            str(root / "exposure.csv"),
                            "--output-dir",
                            str(root / "out"),
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_preflight.assert_called_once()
        self.assertEqual(run_preflight.call_args.kwargs["processed_root"], Path(root / "processed"))
        self.assertEqual(run_preflight.call_args.kwargs["pairwise_prescreen_path"], Path(root / "pairwise.json"))
        self.assertEqual(run_preflight.call_args.kwargs["residual_ic_paths"], [Path(root / "a.csv")])
        self.assertEqual(run_preflight.call_args.kwargs["reference_correlation_paths"], [Path(root / "reference.csv")])
        self.assertEqual(run_preflight.call_args.kwargs["exposure_correlation_paths"], [Path(root / "exposure.csv")])


if __name__ == "__main__":
    unittest.main()
