import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_readiness_projection import run_readiness_projection


class ReadinessProjectionCliTests(unittest.TestCase):
    def test_run_readiness_projection_writes_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            board_path = root / "pre_api_readiness_board.json"
            board_path.write_text(
                json.dumps(
                    {
                        "summary": {"blockers": 1, "blocked": 1},
                        "boundary": {"would_cross_live_boundary": False},
                        "readiness_items": [
                            {"track_id": "data_gap_resolution", "label": "Data gap", "status": "block", "evidence": "blocking_gap_rows=1"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            data_gap_path = root / "data_gap_rehearsal.json"
            data_gap_path.write_text(
                json.dumps(
                    {
                        "summary": {"source_blocking_gap_rows": 1, "rehearsed_blocking_gap_rows": 0, "blocker_delta": 1},
                        "readiness_projection": {"track_id": "data_gap_resolution", "status": "pass", "evidence": "blocking_gap_rows=0"},
                    }
                ),
                encoding="utf-8",
            )
            provider_path = root / "provider_remediation_rehearsal.json"
            provider_path.write_text(json.dumps({"summary": {}, "readiness_projection": {}}), encoding="utf-8")
            output_dir = root / "readiness_projection"

            pack = run_readiness_projection(
                readiness_board=board_path,
                data_gap_rehearsal=data_gap_path,
                provider_remediation_rehearsal=provider_path,
                output_dir=output_dir,
            )

            self.assertEqual(pack["stage"], "phase_4_12_pre_api_readiness_projection_pack")
            self.assertTrue((output_dir / "readiness_projection_pack.json").exists())
            self.assertTrue((output_dir / "readiness_projection_pack.md").exists())
            self.assertTrue((output_dir / "readiness_projection_items.csv").exists())
            self.assertTrue((output_dir / "readiness_projection_deltas.csv").exists())
            self.assertTrue((output_dir / "readiness_projection_residuals.csv").exists())
            payload = json.loads((output_dir / "readiness_projection_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["total_rehearsal_delta"], 1)


if __name__ == "__main__":
    unittest.main()
