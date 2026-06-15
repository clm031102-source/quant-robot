import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_iterative_observation_expansion import run_iterative_observation_expansion


class IterativeObservationExpansionTests(unittest.TestCase):
    def test_iterative_expansion_runs_until_sample_gate_clears(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initial_sufficiency = root / "observation_sufficiency_pack.json"
            initial_sufficiency.write_text(
                json.dumps(_sufficiency_pack(2, 20, "2025-12-26", "2026-06-13")),
                encoding="utf-8",
            )
            calls: list[dict] = []

            def expanded_runner(**kwargs):
                calls.append(kwargs)
                if len(calls) == 1:
                    return {
                        "stage": "phase_5_10_expanded_observation_replay",
                        "status": "expanded_replay_blocked",
                        "window": {"start_date": "2025-12-26", "end_date": "2026-06-13"},
                        "decision": {"expanded_observation_cleared": False, "blockers": ["minimum_fills_observed"]},
                        "final_observation_sufficiency": _sufficiency_pack(15, 20, "2025-11-07", "2026-06-10"),
                        "live_boundary_allowed": False,
                    }
                return {
                    "stage": "phase_5_10_expanded_observation_replay",
                    "status": "completed",
                    "window": {"start_date": "2025-11-07", "end_date": "2026-06-10"},
                    "decision": {"expanded_observation_cleared": True, "blockers": []},
                    "final_observation_sufficiency": {
                        "stage": "phase_5_9_observation_sufficiency",
                        "status": "sufficient",
                        "fills": {"observed_fills": 29, "required_fills": 20, "fill_deficit": 0},
                        "decision": {"observation_sufficiency_cleared": True, "blockers": []},
                    },
                    "live_boundary_allowed": False,
                }

            report_dir = root / "iterative"
            pack = run_iterative_observation_expansion(
                observation_sufficiency_pack=initial_sufficiency,
                report_dir=report_dir,
                max_rounds=3,
                expanded_observation_runner=expanded_runner,
            )

            artifact_exists = (report_dir / "iterative_observation_expansion_pack.json").exists()

        self.assertEqual(pack["stage"], "phase_5_11_iterative_observation_expansion")
        self.assertEqual(pack["status"], "completed")
        self.assertEqual(pack["round_count"], 2)
        self.assertTrue(pack["decision"]["iterative_observation_cleared"])
        self.assertEqual(pack["final_observation_sufficiency"]["fills"]["observed_fills"], 29)
        self.assertEqual(calls[0]["observation_sufficiency_pack"], initial_sufficiency)
        self.assertEqual(calls[1]["observation_sufficiency_pack"], report_dir / "round_01" / "observation_sufficiency_pack.json")
        self.assertFalse(pack["live_boundary_allowed"])
        self.assertTrue(artifact_exists)

    def test_iterative_expansion_blocks_without_running_when_initial_pack_is_not_extendable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initial_sufficiency = root / "observation_sufficiency_pack.json"
            initial_sufficiency.write_text(
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

            pack = run_iterative_observation_expansion(
                observation_sufficiency_pack=initial_sufficiency,
                report_dir=root / "iterative",
                expanded_observation_runner=lambda **_: calls.append("expanded") or {},
            )

        self.assertEqual(pack["status"], "blocked")
        self.assertFalse(pack["decision"]["iterative_observation_cleared"])
        self.assertEqual(pack["decision"]["blockers"], ["profile_observation_artifact_missing"])
        self.assertEqual(calls, [])


def _sufficiency_pack(observed_fills: int, required_fills: int, start_date: str, end_date: str) -> dict:
    return {
        "stage": "phase_5_9_observation_sufficiency",
        "status": "needs_more_observation_data",
        "fills": {
            "observed_fills": observed_fills,
            "required_fills": required_fills,
            "fill_deficit": max(0, required_fills - observed_fills),
        },
        "recommendation": {
            "priority": "extend_recent_data_window",
            "suggested_start_date": start_date,
            "suggested_end_date": end_date,
            "threshold_relaxation_allowed": observed_fills >= 10,
        },
        "decision": {
            "observation_sufficiency_cleared": False,
            "blockers": ["minimum_fills_observed"],
        },
    }


if __name__ == "__main__":
    unittest.main()
