import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.financial_pit_post_announcement_gap_reversal_matrix_label_smoke import (
    build_financial_pit_post_announcement_gap_reversal_matrix_label_smoke,
    write_financial_pit_post_announcement_gap_reversal_matrix_label_smoke,
)
from quant_robot.ops.financial_pit_post_announcement_drift_matrix_label_smoke import (
    compute_financial_pit_post_announcement_drift_factor_frame,
)
from quant_robot.ops.financial_pit_post_announcement_gap_reversal_preregistration import (
    build_financial_pit_post_announcement_gap_reversal_preregistration,
    write_financial_pit_post_announcement_gap_reversal_preregistration,
)
from tests.unit.test_financial_pit_post_announcement_drift_matrix_label_smoke import _bar_rows_for_label_window
from tests.unit.test_financial_pit_post_announcement_drift_preregistration import (
    _financial_rows,
    _write_bars,
    _write_financial,
)
from tests.unit.test_financial_pit_post_announcement_gap_reversal_preregistration import _seed


class FinancialPitPostAnnouncementGapReversalMatrixLabelSmokeTests(unittest.TestCase):
    def test_builds_gap_reversal_matrix_and_labels_without_event_day_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_output = root / "prereg"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows_for_label_window())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")
            _write_preregistration(financial_root, bars_root, prereg_output, seed_path)

            result = build_financial_pit_post_announcement_gap_reversal_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_gap_reversal_preregistration.json",
                horizons=(5,),
                execution_lag=1,
                min_label_coverage=0.90,
            )

            self.assertEqual(result["stage"], "financial_pit_post_announcement_gap_reversal_matrix_label_smoke")
            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["active_candidate_count"], 5)
            self.assertEqual(result["summary"]["unknown_active_candidate_count"], 0)
            self.assertEqual(result["summary"]["alignment_violation_rows"], 0)
            self.assertGreater(result["summary"]["factor_value_rows"], 0)
            self.assertGreaterEqual(result["summary"]["label_coverage"], 0.90)
            self.assertEqual(
                result["summary"]["next_allowed_gate"],
                "round223_financial_pit_post_announcement_gap_reversal_residual_prescreen",
            )
            self.assertFalse(result["alignment_policy"]["same_day_event_reaction_trading_allowed"])
            self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed"])
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_write_outputs_gap_reversal_matrix_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_output = root / "prereg"
            output_dir = root / "output"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows_for_label_window())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")
            _write_preregistration(financial_root, bars_root, prereg_output, seed_path)

            result = build_financial_pit_post_announcement_gap_reversal_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_gap_reversal_preregistration.json",
            )
            write_financial_pit_post_announcement_gap_reversal_matrix_label_smoke(output_dir, result)

            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_matrix_label_smoke.json").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_matrix_label_smoke.md").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_matrix_candidate_summary.csv").exists())

    def test_size_neutral_candidate_is_not_duplicate_of_base_gap_reversal(self) -> None:
        factors = compute_financial_pit_post_announcement_drift_factor_frame(
            _financial_rows(),
            [
                {"factor_name": "pead_gap_overreaction_reversal_1_5"},
                {"factor_name": "pead_gap_overreaction_reversal_size_neutral_candidate_1_5"},
            ],
            _bar_rows_for_label_window(),
        )

        pivot = factors.pivot_table(
            index=["date", "asset_id"],
            columns="factor_name",
            values="factor_value",
            aggfunc="last",
        ).dropna()

        self.assertFalse(pivot.empty)
        self.assertFalse(
            pd.Series.equals(
                pivot["pead_gap_overreaction_reversal_1_5"],
                pivot["pead_gap_overreaction_reversal_size_neutral_candidate_1_5"],
            )
        )


def _write_preregistration(financial_root: Path, bars_root: Path, output_dir: Path, seed_path: Path) -> None:
    result = build_financial_pit_post_announcement_gap_reversal_preregistration(
        financial_root=financial_root,
        bars_roots=[bars_root],
        candidate_seed_json=seed_path,
        min_assets=3,
        min_signal_dates=2,
        min_event_reaction_coverage=0.80,
    )
    write_financial_pit_post_announcement_gap_reversal_preregistration(output_dir, result)


if __name__ == "__main__":
    unittest.main()
