import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_lpr_macro_regime_state_conditioned_walk_forward_preflight import main


class LPRMacroRegimeStateConditionedWalkForwardPreflightCliTests(unittest.TestCase):
    def test_cli_passes_reference_dedup_and_smoke_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_lpr_macro_regime_state_conditioned_walk_forward_preflight.run_lpr_macro_regime_state_conditioned_walk_forward_preflight",
                return_value={"status": "cleared", "summary": {}, "decision": {}, "preflight_policy": {}},
            ) as run_preflight:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(root / "macro"),
                            "--reference-dedup",
                            str(root / "round735.json"),
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
                            "--allow-not-ready",
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_preflight.assert_called_once()
        self.assertEqual(run_preflight.call_args.kwargs["processed_root"], Path(root / "macro"))
        self.assertEqual(run_preflight.call_args.kwargs["reference_dedup_path"], Path(root / "round735.json"))
        self.assertEqual(run_preflight.call_args.kwargs["smoke_path"], Path(root / "round734.json"))
        self.assertEqual(run_preflight.call_args.kwargs["bars_roots"], [Path(root / "bars")])
        self.assertEqual(run_preflight.call_args.kwargs["daily_basic_roots"], [Path(root / "daily_basic")])
        self.assertEqual(run_preflight.call_args.kwargs["stock_basic"], Path(root / "stock_basic"))


if __name__ == "__main__":
    unittest.main()
