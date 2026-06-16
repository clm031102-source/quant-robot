import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_desktop_factor_validation import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_DATA_ROOT,
    _preflight_desktop_inputs,
    run_desktop_factor_validation,
)


class DesktopFactorValidationTests(unittest.TestCase):
    def test_default_run_targets_residual_regime_validation_and_allows_rejected_candidates(self):
        result = {"summary": {"cases": 1, "accepted": 0, "rejected": 1}, "leaderboard": []}

        with (
            patch("scripts.run_desktop_factor_validation._preflight_desktop_inputs") as preflight,
            patch("scripts.run_desktop_factor_validation.run_walk_forward", return_value=result) as walk_forward,
            patch("scripts.run_desktop_factor_validation.assert_walk_forward_succeeded") as assert_succeeded,
        ):
            returned = run_desktop_factor_validation()

        self.assertIs(returned, result)
        preflight.assert_called_once_with(DEFAULT_CONFIG_PATH, "processed-bars", DEFAULT_DATA_ROOT)
        walk_forward.assert_called_once_with(
            config_path=DEFAULT_CONFIG_PATH,
            source="processed-bars",
            data_root=DEFAULT_DATA_ROOT,
            output_dir=None,
        )
        assert_succeeded.assert_called_once_with(result, allow_no_accepted=True)

    def test_require_accepted_turns_no_accepted_candidates_into_failure(self):
        result = {"summary": {"cases": 1, "accepted": 0, "rejected": 1}, "leaderboard": []}

        with (
            patch("scripts.run_desktop_factor_validation._preflight_desktop_inputs"),
            patch("scripts.run_desktop_factor_validation.run_walk_forward", return_value=result),
            patch("scripts.run_desktop_factor_validation.assert_walk_forward_succeeded") as assert_succeeded,
        ):
            run_desktop_factor_validation(require_accepted=True, output_dir=Path("data/reports/custom"))

        assert_succeeded.assert_called_once_with(result, allow_no_accepted=False)

    def test_preflight_blocks_missing_moneyflow_inputs_for_processed_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root = root / "data" / "processed"
            data_root.mkdir(parents=True)
            config_path = root / "walk_forward.json"
            config_path.write_text(
                """
                {
                  "split_date": "2024-01-08",
                  "experiment_grid": {
                    "markets": ["CN"],
                    "factor_source": "moneyflow_technical_combo",
                    "moneyflow_input_root": "missing_moneyflow_inputs",
                    "factor_names": ["large_resid_liq_vol_amt_gate_20"],
                    "factor_windows": [20]
                  }
                }
                """,
                encoding="utf-8",
            )

            with self.assertRaisesRegex(FileNotFoundError, "Tushare moneyflow inputs"):
                _preflight_desktop_inputs(config_path, "processed-bars", data_root)


if __name__ == "__main__":
    unittest.main()
