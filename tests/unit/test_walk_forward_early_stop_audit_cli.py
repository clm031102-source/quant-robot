import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_walk_forward_early_stop_audit import run_walk_forward_early_stop_audit_cli


class WalkForwardEarlyStopAuditCliTests(unittest.TestCase):
    def test_cli_writes_json_and_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_root = root / "wf"
            output_dir = root / "audit"
            for fold in range(1, 4):
                _write_fold(walk_forward_root, fold)

            result = run_walk_forward_early_stop_audit_cli(
                walk_forward_root=walk_forward_root,
                output_dir=output_dir,
                min_completed_folds=3,
                expected_rows_per_fold=1,
            )

            self.assertTrue(result["summary"]["early_stop_recommended"])
            self.assertTrue((output_dir / "walk_forward_early_stop_audit.json").exists())
            self.assertTrue((output_dir / "walk_forward_early_stop_audit.md").exists())
            payload = json.loads((output_dir / "walk_forward_early_stop_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["decision"]["next_action"], "stop_validation_and_rotate")


def _write_fold(root: Path, fold: int) -> None:
    path = root / f"fold_{fold:02d}" / "test" / "partial_leaderboard.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "case_id": f"case_{fold}",
                "decision_status": "rejected",
                "relative_return": -0.01,
                "capacity_limited_trades": 0,
            }
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
