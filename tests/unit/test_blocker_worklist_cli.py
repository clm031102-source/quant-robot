import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_blocker_worklist import run_blocker_worklist


class BlockerWorklistCliTests(unittest.TestCase):
    def test_run_blocker_worklist_writes_worklist_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            board_path = root / "pre_api_readiness_board.json"
            board_path.write_text(
                json.dumps(
                    {
                        "overall_status": "blocked",
                        "boundary": {"would_cross_live_boundary": False, "order_placement": "disabled"},
                        "blocker_register": [
                            {
                                "blocker_id": "manual_review_gate_blocked",
                                "track_id": "manual_review_gate",
                                "severity": "block",
                                "evidence": "manual_live_review_not_enabled",
                                "recommended_command": "python scripts\\run_manual_review_rehearsal.py",
                            }
                        ],
                        "next_local_actions": [
                            {
                                "priority": 1,
                                "track_id": "manual_review_gate",
                                "command": "python scripts\\run_manual_review_rehearsal.py",
                                "reason": "dry run gate",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            output_dir = root / "blocker_worklist"

            worklist = run_blocker_worklist(readiness_board=board_path, output_dir=output_dir)

            self.assertEqual(worklist["stage"], "phase_4_1_blocker_resolution_worklist")
            self.assertTrue((output_dir / "blocker_resolution_worklist.json").exists())
            self.assertTrue((output_dir / "blocker_resolution_worklist.md").exists())
            self.assertTrue((output_dir / "blocker_work_items.csv").exists())
            self.assertTrue((output_dir / "blocker_action_queue.csv").exists())
            payload = json.loads((output_dir / "blocker_resolution_worklist.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["open_work_items"], 1)


if __name__ == "__main__":
    unittest.main()
