import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_post_refresh_replay import run_post_refresh_replay


class PostRefreshReplayTests(unittest.TestCase):
    def test_replay_blocks_without_running_downstream_when_recent_refresh_is_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            recent_pack = root / "recent_data_refresh_pack.json"
            recent_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_7_tushare_recent_data_refresh",
                        "status": "blocked",
                        "mode": "dry_run",
                        "output_dir": str(root / "processed"),
                        "decision": {
                            "recent_data_ready": False,
                            "signal_data_stale_cleared": False,
                            "blockers": ["TUSHARE_TOKEN is not set"],
                        },
                        "next_actions": [{"action": "set_tushare_token_env", "reason": "token"}],
                    }
                ),
                encoding="utf-8",
            )
            calls: list[str] = []

            pack = run_post_refresh_replay(
                recent_data_refresh_pack=recent_pack,
                report_dir=root / "report",
                daily_ops_runner=lambda **_: calls.append("daily") or {},
                profile_observation_runner=lambda **_: calls.append("observation") or {},
            )

        self.assertEqual(pack["stage"], "phase_5_8_post_refresh_replay")
        self.assertEqual(pack["status"], "blocked")
        self.assertFalse(pack["decision"]["post_refresh_replay_allowed"])
        self.assertEqual(pack["decision"]["blockers"], ["TUSHARE_TOKEN is not set"])
        self.assertEqual(pack["next_actions"][0]["action"], "set_tushare_token_env")
        self.assertEqual(calls, [])

    def test_replay_runs_daily_ops_and_observation_after_ready_recent_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            recent_pack = root / "recent_data_refresh_pack.json"
            recent_pack.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_7_tushare_recent_data_refresh",
                        "status": "completed",
                        "mode": "execute",
                        "source": "tushare-fixture",
                        "market": "CN_ETF",
                        "output_dir": str(processed),
                        "decision": {
                            "recent_data_ready": True,
                            "signal_data_stale_cleared": True,
                            "blockers": [],
                        },
                        "coverage": {"coverage_status": "pass", "processed_rows": 46},
                    }
                ),
                encoding="utf-8",
            )
            calls: dict[str, dict] = {}

            def daily_ops_runner(**kwargs):
                calls["daily"] = kwargs
                return {
                    "stage": "phase_5_0_daily_ops",
                    "run_date": "2026-06-14",
                    "decision": {
                        "status": "paper_ready",
                        "paper_trading_allowed": True,
                        "blocking_reasons": [],
                    },
                    "candidate": {"case_id": "case_a", "market": "CN_ETF"},
                    "risk": {"max_equity_drawdown": -0.25},
                }

            def profile_observation_runner(**kwargs):
                calls["observation"] = kwargs
                return {
                    "stage": "phase_5_6_profile_observation_ledger",
                    "run_date": "2026-06-14",
                    "decision": {
                        "observation_status": "observing",
                        "paper_observation_allowed": True,
                        "stop_reasons": [],
                    },
                    "summary": {"stop_count": 0, "warning_count": 0},
                }

            report_dir = root / "report"
            pack = run_post_refresh_replay(
                recent_data_refresh_pack=recent_pack,
                report_dir=report_dir,
                daily_ops_runner=daily_ops_runner,
                profile_observation_runner=profile_observation_runner,
            )
            artifact_exists = (report_dir / "post_refresh_replay_pack.json").exists()
            markdown_exists = (report_dir / "post_refresh_replay_pack.md").exists()
            actions_exists = (report_dir / "post_refresh_replay_next_actions.csv").exists()

        self.assertEqual(pack["status"], "completed")
        self.assertTrue(pack["decision"]["post_refresh_replay_allowed"])
        self.assertEqual(pack["decision"]["blockers"], [])
        self.assertEqual(calls["daily"]["data_root"], processed)
        self.assertEqual(calls["daily"]["source"], "processed-bars")
        self.assertEqual(calls["observation"]["daily_ops_pack"], report_dir / "daily_ops" / "daily_ops_pack.json")
        self.assertEqual(calls["observation"]["simulation_dir"], report_dir / "daily_ops" / "paper_simulation")
        self.assertTrue(artifact_exists)
        self.assertTrue(markdown_exists)
        self.assertTrue(actions_exists)


if __name__ == "__main__":
    unittest.main()
