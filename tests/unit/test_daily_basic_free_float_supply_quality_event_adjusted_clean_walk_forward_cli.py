import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward import (
    run_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_cli,
)


class DailyBasicFreeFloatSupplyQualityEventAdjustedCleanWalkForwardCliTests(unittest.TestCase):
    def test_cli_wrapper_writes_walk_forward_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "round141"
            with patch(
                "scripts.run_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward."
                "build_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward"
            ) as build:
                build.return_value = {
                    "stage": "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward",
                    "summary": {"fold_count": 2, "walk_forward_accepted_candidates": 0},
                    "leaderboard": [],
                    "folds": [],
                    "event_exclusion_summary": {"requested_event_path_count": 2, "excluded_factor_rows": 2},
                    "promotion_policy": {"promotion_allowed": False, "blockers": ["final_holdout_not_read"]},
                    "next_direction": "round142_daily_basic_free_float_supply_quality_hibernation_or_family_rotation",
                }

                result = run_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward_cli(
                    bars_roots=[Path(tmp) / "bars"],
                    daily_basic_roots=[Path(tmp) / "daily_basic"],
                    round139_audit_report=Path(tmp) / "round139.json",
                    output_dir=output_dir,
                    rolling_train_days=2,
                    rolling_test_days=1,
                    rolling_step_days=1,
                )

                self.assertEqual(result["summary"]["fold_count"], 2)
                self.assertTrue(
                    (
                        output_dir
                        / "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward.json"
                    ).exists()
                )
                self.assertTrue(
                    (
                        output_dir
                        / "daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward.md"
                    ).exists()
                )
                build.assert_called_once()


if __name__ == "__main__":
    unittest.main()
