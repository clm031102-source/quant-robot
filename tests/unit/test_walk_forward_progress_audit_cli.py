import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_walk_forward_progress_audit import run_walk_forward_progress_audit


class WalkForwardProgressAuditCliTests(unittest.TestCase):
    def test_run_walk_forward_progress_audit_writes_json_and_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_root = root / "walk_forward"
            _write_leaderboard(walk_forward_root / "fold_01" / "test" / "leaderboard.csv")
            output_dir = root / "audit"

            result = run_walk_forward_progress_audit(
                walk_forward_root=walk_forward_root,
                output_dir=output_dir,
                expected_folds=2,
                generated_at="2026-06-20 15:30:00 +08:00",
            )

            self.assertEqual(result["summary"]["conclusion"], "incomplete")
            json_path = output_dir / "walk_forward_progress_audit.json"
            markdown_path = output_dir / "walk_forward_progress_audit.md"
            self.assertTrue(json_path.exists())
            self.assertTrue(markdown_path.exists())
            saved = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["summary"]["completed_folds"], 1)
            self.assertIn("Walk-Forward Progress Audit", markdown_path.read_text(encoding="utf-8"))


def _write_leaderboard(path: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(
        "case_id,factor_name,factor_windows,top_n,cost_bps,rebalance_interval,regime_lookback,"
        "status,trades,annualized_return,sharpe,max_drawdown,win_rate,relative_return,"
        "capacity_limited_trades,max_participation_rate,decision_status\n"
        "case_a,factor_a,[20],5,20,1,120,completed,40,0.2,1.2,-0.1,0.6,0.2,0,0.005,approved\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
