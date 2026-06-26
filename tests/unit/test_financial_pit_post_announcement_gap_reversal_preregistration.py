import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.financial_pit_post_announcement_gap_reversal_preregistration import (
    build_financial_pit_post_announcement_gap_reversal_preregistration,
    write_financial_pit_post_announcement_gap_reversal_preregistration,
)
from tests.unit.test_financial_pit_post_announcement_drift_preregistration import (
    _bar_rows,
    _financial_rows,
    _write_bars,
    _write_financial,
)


class FinancialPitPostAnnouncementGapReversalPreregistrationTests(unittest.TestCase):
    def test_builds_gap_reversal_preregistration_from_seed_without_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")

            result = build_financial_pit_post_announcement_gap_reversal_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                candidate_seed_json=seed_path,
                min_assets=3,
                min_signal_dates=2,
                min_event_reaction_coverage=0.80,
            )

            self.assertEqual(result["stage"], "financial_pit_post_announcement_gap_reversal_preregistration")
            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["candidate_count"], 5)
            self.assertEqual(
                result["summary"]["next_allowed_gate"],
                "round223_financial_pit_post_announcement_gap_reversal_matrix_label_smoke",
            )
            self.assertEqual(
                {candidate["family"] for candidate in result["candidates"]},
                {"financial_pit_post_announcement_gap_reversal"},
            )
            self.assertFalse(result["promotion_policy"]["portfolio_grid_allowed_before_residual_prescreen"])
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])

    def test_write_outputs_gap_reversal_named_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            output_dir = root / "output"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")

            result = build_financial_pit_post_announcement_gap_reversal_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                candidate_seed_json=seed_path,
                min_assets=3,
                min_signal_dates=2,
                min_event_reaction_coverage=0.80,
            )
            write_financial_pit_post_announcement_gap_reversal_preregistration(output_dir, result)

            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_preregistration.json").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_preregistration.md").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_candidates.csv").exists())


def _seed() -> dict:
    return {
        "family": "financial_pit_post_announcement_gap_reversal",
        "candidate_ideas": [
            "pead_gap_overreaction_reversal_1_5",
            "pead_gap_overreaction_reversal_volume_confirmed_1_5",
            "pead_gap_overreaction_reversal_low_liquidity_penalized_1_5",
            "pead_gap_overreaction_reversal_size_neutral_candidate_1_5",
            "pead_gap_overreaction_reversal_quality_conditioned_1_5",
        ],
        "mandatory_controls": ["inverse_sign_requires_fresh_preregistration"],
    }


if __name__ == "__main__":
    unittest.main()
