import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_expanded_observation_replay import run_expanded_observation_replay


class ExpandedObservationReplayTests(unittest.TestCase):
    def test_expanded_replay_uses_sufficiency_window_and_reruns_replay_chain(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sufficiency_pack = root / "observation_sufficiency_pack.json"
            sufficiency_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_9_observation_sufficiency",
                        "status": "needs_more_observation_data",
                        "recommendation": {
                            "priority": "extend_recent_data_window",
                            "suggested_start_date": "2025-12-26",
                            "suggested_end_date": "2026-06-13",
                            "threshold_relaxation_allowed": False,
                        },
                        "decision": {"blockers": ["minimum_fills_observed"]},
                    }
                ),
                encoding="utf-8",
            )
            calls: dict[str, dict] = {}

            def recent_runner(**kwargs):
                calls["recent"] = kwargs
                return {
                    "stage": "phase_5_7_tushare_recent_data_refresh",
                    "status": "completed",
                    "source": "tushare-fixture",
                    "output_dir": str(kwargs["output_dir"]),
                    "decision": {"recent_data_ready": True, "signal_data_stale_cleared": True, "blockers": []},
                    "coverage": {"coverage_status": "pass", "processed_rows": 340},
                }

            def post_replay_runner(**kwargs):
                calls["post"] = kwargs
                return {
                    "stage": "phase_5_8_post_refresh_replay",
                    "status": "completed",
                    "decision": {"post_refresh_replay_allowed": True, "blockers": []},
                    "profile_observation_output_dir": str(root / "replay" / "profile_observation"),
                }

            def sufficiency_runner(**kwargs):
                calls["sufficiency"] = kwargs
                return {
                    "stage": "phase_5_9_observation_sufficiency",
                    "status": "sufficient",
                    "decision": {"observation_sufficiency_cleared": True, "blockers": []},
                    "fills": {"observed_fills": 24, "required_fills": 20, "fill_deficit": 0},
                    "recommendation": {"priority": "continue_paper_observation"},
                }

            report_dir = root / "expanded"
            pack = run_expanded_observation_replay(
                observation_sufficiency_pack=sufficiency_pack,
                report_dir=report_dir,
                source="tushare-fixture",
                recent_data_refresh_runner=recent_runner,
                post_refresh_replay_runner=post_replay_runner,
                observation_sufficiency_runner=sufficiency_runner,
            )

            artifact_exists = (report_dir / "expanded_observation_replay_pack.json").exists()

        self.assertEqual(pack["stage"], "phase_5_10_expanded_observation_replay")
        self.assertEqual(pack["status"], "completed")
        self.assertTrue(pack["decision"]["expanded_observation_cleared"])
        self.assertEqual(calls["recent"]["start_date"], "2025-12-26")
        self.assertEqual(calls["recent"]["end_date"], "2026-06-13")
        self.assertTrue(calls["recent"]["execute"])
        self.assertEqual(calls["recent"]["source"], "tushare-fixture")
        self.assertEqual(calls["post"]["recent_data_refresh_pack"], report_dir / "recent_data_refresh" / "recent_data_refresh_pack.json")
        self.assertEqual(calls["post"]["run_date"], "2026-06-13")
        self.assertEqual(calls["sufficiency"]["post_refresh_replay_pack"], report_dir / "post_refresh_replay" / "post_refresh_replay_pack.json")
        self.assertFalse(pack["live_boundary_allowed"])
        self.assertTrue(artifact_exists)

    def test_expanded_replay_blocks_without_running_when_sufficiency_is_not_extendable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sufficiency_pack = root / "observation_sufficiency_pack.json"
            sufficiency_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_9_observation_sufficiency",
                        "status": "blocked_missing_observation",
                        "recommendation": {"priority": "rerun_post_refresh_replay"},
                        "decision": {"blockers": ["profile_observation_artifact_missing"]},
                    }
                ),
                encoding="utf-8",
            )
            calls: list[str] = []

            pack = run_expanded_observation_replay(
                observation_sufficiency_pack=sufficiency_pack,
                report_dir=root / "expanded",
                recent_data_refresh_runner=lambda **_: calls.append("recent") or {},
                post_refresh_replay_runner=lambda **_: calls.append("post") or {},
                observation_sufficiency_runner=lambda **_: calls.append("sufficiency") or {},
            )

        self.assertEqual(pack["status"], "blocked")
        self.assertFalse(pack["decision"]["expanded_observation_cleared"])
        self.assertEqual(pack["decision"]["blockers"], ["profile_observation_artifact_missing"])
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
