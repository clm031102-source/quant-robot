import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_lpr_macro_regime_factor_value_reconstruction_smoke import main


class LPRMacroRegimeFactorValueReconstructionSmokeCliTests(unittest.TestCase):
    def test_cli_passes_roots_and_preflight_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_lpr_macro_regime_factor_value_reconstruction_smoke.run_lpr_macro_regime_factor_value_reconstruction_smoke",
                return_value={"summary": {"passes": True}, "decision": {}},
            ) as run_smoke:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(root / "macro"),
                            "--preflight",
                            str(root / "round733.json"),
                            "--bars-root",
                            str(root / "bars"),
                            "--daily-basic-root",
                            str(root / "daily_basic"),
                            "--stock-basic",
                            str(root / "stock_basic"),
                            "--output-dir",
                            str(root / "out"),
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_smoke.assert_called_once()
        self.assertEqual(run_smoke.call_args.kwargs["processed_root"], Path(root / "macro"))
        self.assertEqual(run_smoke.call_args.kwargs["preflight_path"], Path(root / "round733.json"))
        self.assertEqual(run_smoke.call_args.kwargs["bars_roots"], [Path(root / "bars")])
        self.assertEqual(run_smoke.call_args.kwargs["daily_basic_roots"], [Path(root / "daily_basic")])
        self.assertEqual(run_smoke.call_args.kwargs["stock_basic"], Path(root / "stock_basic"))


if __name__ == "__main__":
    unittest.main()
