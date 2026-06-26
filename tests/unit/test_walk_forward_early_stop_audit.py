import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.walk_forward_early_stop_audit import build_walk_forward_early_stop_audit


class WalkForwardEarlyStopAuditTests(unittest.TestCase):
    def test_stops_when_clean_capacity_folds_have_no_positive_relative_or_accepted_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for fold in range(1, 4):
                _write_fold(
                    root,
                    fold,
                    [
                        _row(f"case_{fold}_a", relative_return=-0.01, accepted=False),
                        _row(f"case_{fold}_b", relative_return=-0.20, accepted=False),
                    ],
                )

            result = build_walk_forward_early_stop_audit(
                root,
                min_completed_folds=3,
                expected_rows_per_fold=2,
                min_positive_relative_rows=1,
                min_accepted_rows=1,
            )

        self.assertEqual(result["stage"], "walk_forward_early_stop_audit")
        self.assertEqual(result["summary"]["completed_folds"], 3)
        self.assertEqual(result["summary"]["inspected_rows"], 6)
        self.assertEqual(result["summary"]["accepted_rows"], 0)
        self.assertEqual(result["summary"]["positive_relative_rows"], 0)
        self.assertEqual(result["summary"]["capacity_clean_rows"], 6)
        self.assertTrue(result["summary"]["early_stop_recommended"])
        self.assertEqual(result["decision"]["next_action"], "stop_validation_and_rotate")
        self.assertIn("no_positive_relative_rows", result["decision"]["reasons"])

    def test_does_not_stop_when_any_fold_has_positive_relative_or_accepted_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fold(root, 1, [_row("case_1", relative_return=-0.01, accepted=False)])
            _write_fold(root, 2, [_row("case_2", relative_return=0.03, accepted=False)])
            _write_fold(root, 3, [_row("case_3", relative_return=-0.02, accepted=True)])

            result = build_walk_forward_early_stop_audit(
                root,
                min_completed_folds=3,
                expected_rows_per_fold=1,
                min_positive_relative_rows=1,
                min_accepted_rows=1,
            )

        self.assertFalse(result["summary"]["early_stop_recommended"])
        self.assertEqual(result["decision"]["next_action"], "continue_validation")

    def test_incomplete_folds_are_not_used_for_stop_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fold(root, 1, [_row("case_1", relative_return=-0.01, accepted=False)])
            _write_fold(root, 2, [_row("case_2", relative_return=-0.02, accepted=False)])

            result = build_walk_forward_early_stop_audit(
                root,
                min_completed_folds=3,
                expected_rows_per_fold=1,
            )

        self.assertEqual(result["summary"]["completed_folds"], 2)
        self.assertFalse(result["summary"]["early_stop_recommended"])
        self.assertIn("insufficient_completed_folds", result["decision"]["reasons"])


def _write_fold(root: Path, fold: int, rows: list[dict]) -> None:
    path = root / f"fold_{fold:02d}" / "test" / "partial_leaderboard.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _row(case_id: str, *, relative_return: float, accepted: bool) -> dict:
    return {
        "case_id": case_id,
        "decision_status": "approved" if accepted else "rejected",
        "relative_return": relative_return,
        "capacity_limited_trades": 0,
        "overlap_autocorr_adjusted_sharpe": 1.0,
        "max_drawdown": -0.1,
    }


if __name__ == "__main__":
    unittest.main()
