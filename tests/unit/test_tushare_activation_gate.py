import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_tushare_activation_gate import run_tushare_activation_gate


class TushareActivationGateTests(unittest.TestCase):
    def test_activation_gate_blocks_before_running_when_tushare_readiness_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(json.dumps(_profile_observation_pack()), encoding="utf-8")
            calls: list[str] = []

            pack = run_tushare_activation_gate(
                profile_observation_pack=profile_pack,
                report_dir=root / "activation",
                source="tushare",
                execute=True,
                readiness={"source": "tushare", "ready": False, "missing": ["TUSHARE_TOKEN is not set"]},
                recent_data_refresh_runner=lambda **_: calls.append("recent") or {},
            )

            artifact_exists = (root / "activation" / "tushare_activation_gate_pack.json").exists()
            serialized = json.dumps(pack, ensure_ascii=False)

        self.assertEqual(pack["stage"], "phase_5_12_tushare_activation_gate")
        self.assertEqual(pack["status"], "blocked_missing_readiness")
        self.assertFalse(pack["decision"]["activation_chain_allowed"])
        self.assertFalse(pack["decision"]["paper_continuation_allowed"])
        self.assertIn("TUSHARE_TOKEN is not set", pack["decision"]["blockers"])
        self.assertEqual(pack["next_actions"][0]["action"], "set_tushare_token_env")
        self.assertEqual(calls, [])
        self.assertTrue(artifact_exists)
        self.assertNotIn(("f" * 64), serialized)
        self.assertFalse(pack["live_boundary_allowed"])

    def test_activation_gate_runs_fixture_chain_until_iterative_sample_gate_clears(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(json.dumps(_profile_observation_pack()), encoding="utf-8")
            calls: list[str] = []

            pack = run_tushare_activation_gate(
                profile_observation_pack=profile_pack,
                report_dir=root / "activation",
                source="tushare-fixture",
                execute=True,
                readiness={"source": "tushare-fixture", "ready": True, "missing": []},
                recent_data_refresh_runner=lambda **kwargs: calls.append("recent") or _recent_pack(kwargs["output_dir"]),
                post_refresh_replay_runner=lambda **_: calls.append("post") or _post_refresh_pack(),
                observation_sufficiency_runner=lambda **_: calls.append("sufficiency") or _sufficiency_pack(15, 20),
                iterative_observation_expansion_runner=lambda **_: calls.append("iterative") or _iterative_pack(),
            )

        self.assertEqual(pack["status"], "paper_observation_ready")
        self.assertEqual(calls, ["recent", "post", "sufficiency", "iterative"])
        self.assertTrue(pack["decision"]["recent_data_ready"])
        self.assertTrue(pack["decision"]["post_refresh_replay_allowed"])
        self.assertFalse(pack["decision"]["observation_sufficiency_cleared"])
        self.assertTrue(pack["decision"]["iterative_observation_cleared"])
        self.assertTrue(pack["decision"]["paper_continuation_allowed"])
        self.assertEqual(pack["final_observation_sufficiency"]["fills"]["observed_fills"], 29)
        self.assertEqual([row["stage"] for row in pack["stage_ledger"]], ["recent_data_refresh", "post_refresh_replay", "observation_sufficiency", "iterative_observation_expansion"])
        self.assertEqual(pack["next_actions"][0]["action"], "continue_paper_observation_on_validated_window")
        self.assertFalse(pack["live_boundary_allowed"])

    def test_iterative_clear_overrides_initial_minimum_fills_post_refresh_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_pack = root / "profile_observation_pack.json"
            profile_pack.write_text(json.dumps(_profile_observation_pack()), encoding="utf-8")

            pack = run_tushare_activation_gate(
                profile_observation_pack=profile_pack,
                report_dir=root / "activation",
                source="tushare-fixture",
                execute=True,
                readiness={"source": "tushare-fixture", "ready": True, "missing": []},
                recent_data_refresh_runner=lambda **kwargs: _recent_pack(kwargs["output_dir"]),
                post_refresh_replay_runner=lambda **_: _post_refresh_minimum_fills_blocked_pack(),
                observation_sufficiency_runner=lambda **_: _sufficiency_pack(15, 20),
                iterative_observation_expansion_runner=lambda **_: _iterative_pack(),
            )

        self.assertEqual(pack["status"], "paper_observation_ready")
        self.assertFalse(pack["decision"]["post_refresh_replay_allowed"])
        self.assertTrue(pack["decision"]["iterative_observation_cleared"])
        self.assertTrue(pack["decision"]["paper_continuation_allowed"])
        self.assertNotIn("minimum_fills_observed", pack["decision"]["blockers"])


def _profile_observation_pack() -> dict:
    return {
        "stage": "phase_5_6_profile_observation_ledger",
        "run_date": "2026-06-14",
        "decision": {
            "observation_status": "stopped",
            "paper_observation_allowed": False,
            "stop_reasons": ["signal_data_stale"],
        },
        "ledger": [
            {
                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                "signal_date": "2026-05-22",
                "profile_id": "cap60_guard12_cd3",
                "risk_tier": "aggressive_growth",
            }
        ],
    }


def _recent_pack(output_dir: Path) -> dict:
    return {
        "stage": "phase_5_7_tushare_recent_data_refresh",
        "status": "completed",
        "source": "tushare-fixture",
        "market": "CN_ETF",
        "output_dir": str(output_dir),
        "coverage": {"coverage_status": "pass", "processed_rows": 46},
        "decision": {
            "signal_data_stale_cleared": True,
            "recent_data_ready": True,
            "blockers": [],
        },
        "live_boundary_allowed": False,
    }


def _post_refresh_pack() -> dict:
    return {
        "stage": "phase_5_8_post_refresh_replay",
        "status": "completed",
        "profile_observation_output_dir": "data/reports/post_refresh_replay_fixture/profile_observation",
        "decision": {
            "recent_data_ready": True,
            "daily_ops_paper_allowed": True,
            "profile_observation_allowed": True,
            "post_refresh_replay_allowed": True,
            "blockers": [],
        },
        "live_boundary_allowed": False,
    }


def _post_refresh_minimum_fills_blocked_pack() -> dict:
    return {
        "stage": "phase_5_8_post_refresh_replay",
        "status": "replay_blocked",
        "profile_observation_output_dir": "data/reports/post_refresh_replay_fixture/profile_observation",
        "decision": {
            "recent_data_ready": True,
            "daily_ops_paper_allowed": True,
            "profile_observation_allowed": False,
            "post_refresh_replay_allowed": False,
            "blockers": ["minimum_fills_observed"],
        },
        "live_boundary_allowed": False,
    }


def _sufficiency_pack(observed_fills: int, required_fills: int) -> dict:
    return {
        "stage": "phase_5_9_observation_sufficiency",
        "status": "needs_more_observation_data",
        "fills": {
            "observed_fills": observed_fills,
            "required_fills": required_fills,
            "fill_deficit": required_fills - observed_fills,
        },
        "recommendation": {
            "priority": "extend_recent_data_window",
            "suggested_start_date": "2025-12-26",
            "suggested_end_date": "2026-06-13",
        },
        "decision": {
            "observation_sufficiency_cleared": False,
            "blockers": ["minimum_fills_observed"],
        },
        "live_boundary_allowed": False,
    }


def _iterative_pack() -> dict:
    return {
        "stage": "phase_5_11_iterative_observation_expansion",
        "status": "completed",
        "round_count": 2,
        "max_rounds": 3,
        "rounds": [
            {"round": 1, "expanded_observation_replay": {"status": "expanded_replay_blocked"}},
            {"round": 2, "expanded_observation_replay": {"status": "completed"}},
        ],
        "final_observation_sufficiency": {
            "stage": "phase_5_9_observation_sufficiency",
            "status": "sufficient",
            "fills": {"observed_fills": 29, "required_fills": 20, "fill_deficit": 0},
            "decision": {"observation_sufficiency_cleared": True, "blockers": []},
        },
        "decision": {"iterative_observation_cleared": True, "blockers": []},
        "live_boundary_allowed": False,
    }


if __name__ == "__main__":
    unittest.main()
