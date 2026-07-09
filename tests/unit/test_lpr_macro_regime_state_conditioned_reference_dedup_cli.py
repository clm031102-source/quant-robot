import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from scripts.run_lpr_macro_regime_state_conditioned_reference_dedup import main


class LPRMacroRegimeStateConditionedReferenceDedupCliTests(unittest.TestCase):
    def test_cli_passes_roots_and_smoke_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch(
                "scripts.run_lpr_macro_regime_state_conditioned_reference_dedup.run_lpr_macro_regime_state_conditioned_reference_dedup",
                return_value={"summary": {"passes": True}, "decision": {}},
            ) as run_dedup:
                with redirect_stdout(StringIO()):
                    exit_code = main(
                        [
                            "--processed-root",
                            str(root / "macro"),
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
                        ]
                    )

        self.assertEqual(exit_code, 0)
        run_dedup.assert_called_once()
        self.assertEqual(run_dedup.call_args.kwargs["processed_root"], Path(root / "macro"))
        self.assertEqual(run_dedup.call_args.kwargs["smoke_path"], Path(root / "round734.json"))
        self.assertEqual(run_dedup.call_args.kwargs["bars_roots"], [Path(root / "bars")])
        self.assertEqual(run_dedup.call_args.kwargs["daily_basic_roots"], [Path(root / "daily_basic")])
        self.assertEqual(run_dedup.call_args.kwargs["stock_basic"], Path(root / "stock_basic"))


if __name__ == "__main__":
    unittest.main()
