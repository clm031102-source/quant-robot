import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_lpr_macro_regime_pairwise_residual_ic_prescreen import main


class LPRMacroRegimePairwiseResidualICPrescreenCliTests(unittest.TestCase):
    def test_cli_passes_paths_and_multiple_residual_ic_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_lpr_macro_regime_pairwise_residual_ic_prescreen.run_lpr_macro_regime_pairwise_residual_ic_prescreen",
                return_value={"summary": {"passes": True}, "decision": {}},
            ) as run_prescreen:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(root / "processed"),
                            "--state-prescreen",
                            str(root / "state.json"),
                            "--residual-ic",
                            str(root / "a.csv"),
                            "--residual-ic",
                            str(root / "b.csv"),
                            "--output-dir",
                            str(root / "out"),
                            "--min-state-ic-observations",
                            "10",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_prescreen.assert_called_once()
        self.assertEqual(run_prescreen.call_args.kwargs["processed_root"], Path(root / "processed"))
        self.assertEqual(run_prescreen.call_args.kwargs["state_prescreen_path"], Path(root / "state.json"))
        self.assertEqual(run_prescreen.call_args.kwargs["residual_ic_paths"], [Path(root / "a.csv"), Path(root / "b.csv")])
        self.assertEqual(run_prescreen.call_args.kwargs["min_state_ic_observations"], 10)


if __name__ == "__main__":
    unittest.main()
