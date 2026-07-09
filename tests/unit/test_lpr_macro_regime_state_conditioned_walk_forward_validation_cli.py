import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_lpr_macro_regime_state_conditioned_walk_forward_validation import main


class LPRMacroRegimeStateConditionedWalkForwardValidationCliTests(unittest.TestCase):
    def test_cli_passes_preflight_and_smoke_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_lpr_macro_regime_state_conditioned_walk_forward_validation.run_lpr_macro_regime_state_conditioned_walk_forward_validation",
                return_value={"status": "accepted", "summary": {}, "decision": {}, "promotion_policy": {}},
            ) as run_validation:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(root / "macro"),
                            "--preflight",
                            str(root / "round736.json"),
                            "--smoke",
                            str(root / "round734.json"),
                            "--bars-root",
                            str(root / "bars"),
                            "--daily-basic-root",
                            str(root / "daily_basic"),
                            "--stock-basic",
                            str(root / "stock_basic"),
                            "--output-dir",
                            str(root / "out"),
                            "--allow-not-accepted",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_validation.assert_called_once()
        self.assertEqual(run_validation.call_args.kwargs["processed_root"], Path(root / "macro"))
        self.assertEqual(run_validation.call_args.kwargs["preflight_path"], Path(root / "round736.json"))
        self.assertEqual(run_validation.call_args.kwargs["smoke_path"], Path(root / "round734.json"))
        self.assertEqual(run_validation.call_args.kwargs["bars_roots"], [Path(root / "bars")])
        self.assertEqual(run_validation.call_args.kwargs["daily_basic_roots"], [Path(root / "daily_basic")])
        self.assertEqual(run_validation.call_args.kwargs["stock_basic"], Path(root / "stock_basic"))


if __name__ == "__main__":
    unittest.main()
