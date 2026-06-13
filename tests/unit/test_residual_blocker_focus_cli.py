import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_residual_blocker_focus import run_residual_blocker_focus


class ResidualBlockerFocusCliTests(unittest.TestCase):
    def test_cli_writes_focus_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            projection_path = root / "projection.json"
            worklist_path = root / "worklist.json"
            output_dir = root / "out"
            projection_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_4_12_pre_api_readiness_projection_pack",
                        "boundary": {"would_cross_live_boundary": False, "broker_connection": "disabled"},
                        "projection_items": [
                            {
                                "track_id": "data_gap_resolution",
                                "label": "Data gap resolution",
                                "current_status": "block",
                                "projected_status": "block",
                                "current_evidence": "blocking_gap_rows=6",
                                "projected_evidence": "blocking_gap_rows=4",
                            }
                        ],
                        "residual_rows": [
                            {
                                "track_id": "data_gap_resolution",
                                "remaining_blockers": 4,
                                "projected_status": "block",
                                "source_stage": "phase_4_6_data_gap_resolution_rehearsal",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            worklist_path.write_text(
                json.dumps(
                    {
                        "stage": "phase_4_1_blocker_resolution_worklist",
                        "boundary": {"would_cross_live_boundary": False, "broker_connection": "disabled"},
                        "work_items": [
                            {
                                "work_item_id": "WI-001",
                                "track_id": "data_gap_resolution",
                                "blocker_id": "data_gap_resolution_blocking_gaps",
                                "primary_command": "python scripts\\run_data_gap_resolution.py",
                            }
                        ],
                        "action_queue": [
                            {
                                "priority": 1,
                                "track_id": "data_gap_resolution",
                                "command": "python scripts\\run_data_gap_resolution.py",
                                "reason": "resolve gaps",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            pack = run_residual_blocker_focus(
                readiness_projection=projection_path,
                blocker_worklist=worklist_path,
                output_dir=output_dir,
            )

            self.assertEqual(pack["summary"]["root_focus_items"], 1)
            self.assertTrue((output_dir / "residual_blocker_focus_pack.json").exists())
            self.assertTrue((output_dir / "residual_blocker_focus_pack.md").exists())
            self.assertTrue((output_dir / "residual_focus_items.csv").exists())
            self.assertTrue((output_dir / "residual_downstream_waits.csv").exists())
            self.assertTrue((output_dir / "residual_focus_actions.csv").exists())


if __name__ == "__main__":
    unittest.main()
