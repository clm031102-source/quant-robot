import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from quant_robot.ops.factor_batch_readiness_gate import (
    build_factor_batch_readiness_gate,
    write_factor_batch_readiness_gate,
)
from quant_robot.ops.factor_mining_startup import build_factor_mining_startup_gate
from scripts.run_walk_forward import assert_walk_forward_succeeded, run_walk_forward


class WalkForwardCliTests(unittest.TestCase):
    def test_run_walk_forward_uses_config_and_fixture_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "wf"
            config_path = Path(tmp) / "walk_forward.json"
            config_path.write_text(
                json.dumps(
                    {
                        "split_date": "2024-01-08",
                        "output_dir": str(output_dir),
                        "experiment_grid": {
                            "markets": ["CN"],
                            "factor_names": ["momentum_2"],
                            "factor_windows": [2],
                            "top_n_values": [1],
                            "cost_bps_values": [0],
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = run_walk_forward(config_path=config_path, source="fixture")

            self.assertEqual(result["summary"]["cases"], 1)
            self.assertTrue((output_dir / "walk_forward_leaderboard.csv").exists())

    def test_assert_walk_forward_succeeded_fails_when_no_case_is_accepted(self):
        result = {
            "summary": {"cases": 1, "accepted": 0, "rejected": 1},
            "leaderboard": [{"case_id": "weak_case", "train_status": "completed", "test_status": "completed"}],
        }

        with self.assertRaisesRegex(RuntimeError, "no accepted walk-forward cases"):
            assert_walk_forward_succeeded(result)

    def test_assert_walk_forward_succeeded_allows_no_accepted_when_requested(self):
        result = {
            "summary": {"cases": 1, "accepted": 0, "rejected": 1},
            "leaderboard": [{"case_id": "weak_case", "train_status": "completed", "test_status": "completed"}],
        }

        assert_walk_forward_succeeded(result, allow_no_accepted=True)

    def test_assert_walk_forward_succeeded_fails_when_underlying_grid_failed(self):
        result = {
            "summary": {"cases": 1, "accepted": 0, "rejected": 1},
            "leaderboard": [{"case_id": "bad_case", "train_status": "completed", "test_status": "failed"}],
        }

        with self.assertRaisesRegex(RuntimeError, "walk-forward grid failures"):
            assert_walk_forward_succeeded(result)

    def test_processed_cn_walk_forward_requires_ready_factor_batch_readiness_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "walk_forward.json"
            config_path.write_text(
                json.dumps(
                    {
                        "split_date": "2024-01-08",
                        "output_dir": str(root / "wf"),
                        "experiment_grid": {
                            "markets": ["CN"],
                            "factor_names": ["momentum_2"],
                            "factor_windows": [2],
                            "top_n_values": [1],
                            "cost_bps_values": [0],
                        },
                    }
                ),
                encoding="utf-8",
            )
            gate_packet = root / "factor_mining_startup_gate.json"
            gate_packet.write_text(_valid_startup_gate_packet_json(), encoding="utf-8")
            data_manifest = root / "cn_stock_data_manifest.json"
            data_manifest.write_text(
                json.dumps(
                    {
                        "generated_at": date.today().isoformat(),
                        "status": "cleared",
                        "summary": {"source_root": root.as_posix(), "bar_rows": 10, "bar_symbols": 2},
                        "decision": {"data_manifest_cleared": True, "blockers": [], "warnings": []},
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )
            readiness_dir = root / "readiness_gate"
            _write_factor_batch_readiness_gate(readiness_dir, ready=False)

            with patch("scripts.run_walk_forward.load_processed_bars") as load_bars:
                with self.assertRaisesRegex(ValueError, "factor batch readiness gate is not ready"):
                    run_walk_forward(
                        config_path=config_path,
                        source="processed-bars",
                        data_root=root,
                        startup_gate_packet=gate_packet,
                        data_manifest_packet=data_manifest,
                        factor_batch_readiness_gate_packet=readiness_dir / "factor_batch_readiness_gate.json",
                    )

            load_bars.assert_not_called()


def _valid_startup_gate_packet_json() -> str:
    config = {
        "scope_id": "cn_stock_factor_mining",
        "market": "CN",
        "asset_type": "stock",
        "allowed_machines": ["office_desktop"],
        "allowed_tasks": ["factor_batch"],
        "recommended_branch_prefixes": ["codex/factor-batch-cn-stock-"],
        "required_confirmations": [
            "machine_confirmed",
            "task_confirmed",
            "branch_confirmed",
            "push_policy_confirmed",
            "cn_stock_scope_confirmed",
            "etf_scope_rejected",
        ],
    }
    branch = "codex/factor-batch-cn-stock-20260617"
    packet = build_factor_mining_startup_gate(
        config,
        request={
            "machine": "office_desktop",
            "task": "factor_batch",
            "branch": branch,
            "market": "CN",
            "asset_type": "stock",
            "confirmations": {name: True for name in config["required_confirmations"]},
        },
        current_branch=branch,
    )
    return json.dumps(packet)


def _write_factor_batch_readiness_gate(output_dir: Path, *, ready: bool) -> None:
    if ready:
        source_queue_packet = {
            "decision": {"status": "cleared", "blockers": []},
            "summary": {"active_source_count": 1},
        }
        candidate_plan_gate_packet = {
            "status": "research_ready",
            "decision": {
                "candidate_plan_gate_cleared": True,
                "research_screen_allowed": True,
                "blockers": [],
            },
            "summary": {"candidate_count": 1},
        }
    else:
        source_queue_packet = {
            "decision": {"status": "blocked", "blockers": ["report_rc_quota_blocked"]},
            "summary": {"active_source_count": 1},
        }
        candidate_plan_gate_packet = {
            "status": "blocked",
            "decision": {
                "candidate_plan_gate_cleared": False,
                "blockers": ["candidate_source_provider_not_allowed"],
            },
            "summary": {"candidate_count": 1},
        }
    packet = build_factor_batch_readiness_gate(
        source_queue_packet=source_queue_packet,
        candidate_plan_gate_packet=candidate_plan_gate_packet,
        candidate_plan_path="candidate_plan.json",
        source_queue_output_dir="source_queue",
        candidate_plan_gate_output_dir="candidate_gate",
    )
    write_factor_batch_readiness_gate(output_dir, packet)


if __name__ == "__main__":
    unittest.main()
