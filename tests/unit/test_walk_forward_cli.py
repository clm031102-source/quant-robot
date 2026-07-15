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
from scripts.run_walk_forward import _load_bars, assert_walk_forward_succeeded, run_walk_forward


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

    def test_authority_bars_source_uses_authority_loader(self):
        expected = object()
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "authority.json"
            config_path.write_text("{}", encoding="utf-8")
            with patch(
                "scripts.run_walk_forward.load_authority_processed_bars_from_config",
                return_value=expected,
            ) as loader:
                result = _load_bars("authority-bars", config_path, ("CN",))

        self.assertIs(result, expected)
        loader.assert_called_once_with(config_path, ("CN",))

    def test_authority_cn_validation_requires_matching_validation_readiness(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "walk_forward.json"
            config_path.write_text(
                json.dumps(
                    {
                        "split_date": "2024-01-08",
                        "bar_start_date": "2024-01-01",
                        "bar_end_date": "2025-12-31",
                        "experiment_grid": {
                            "markets": ["CN"],
                            "moneyflow_input_root": str(root / "moneyflow.json"),
                            "factor_names": ["momentum_2"],
                            "factor_windows": [2],
                            "top_n_values": [1],
                            "cost_bps_values": [0],
                        },
                    }
                ),
                encoding="utf-8",
            )
            data_root = root / "authority.json"
            data_root.write_text("{}", encoding="utf-8")
            result = {"summary": {"cases": 0}, "leaderboard": []}
            with (
                patch("scripts.run_walk_forward.validate_cleared_startup_gate_packet"),
                patch("scripts.run_walk_forward.validate_cn_stock_data_manifest_packet") as manifest,
                patch("scripts.run_walk_forward.validate_factor_batch_readiness_gate_packet") as batch_gate,
                patch("scripts.run_walk_forward.validate_factor_validation_readiness_packet") as validation_gate,
                patch("scripts.run_walk_forward.load_authority_processed_bars_from_config", return_value=object()),
                patch("scripts.run_walk_forward.run_walk_forward_validation", return_value=result),
            ):
                returned = run_walk_forward(
                    config_path=config_path,
                    source="authority-bars",
                    data_root=data_root,
                    startup_gate_packet=root / "startup.json",
                    data_manifest_packet=root / "manifest.json",
                    factor_batch_readiness_gate_packet=None,
                    factor_validation_readiness_packet=root / "validation_readiness.json",
                    allow_review_required_data_manifest=True,
                )

            self.assertIs(returned, result)
            batch_gate.assert_not_called()
            validation_gate.assert_called_once_with(
                root / "validation_readiness.json",
                expected_config_path=config_path,
                expected_source="authority-bars",
                expected_data_root=data_root,
                expected_factor_names=["momentum_2"],
                context="CN walk-forward validation",
            )
            self.assertEqual(manifest.call_args.kwargs["expected_moneyflow_source_root"], root / "moneyflow.json")
            self.assertTrue(manifest.call_args.kwargs["verify_source_fingerprint"])

    def test_cn_walk_forward_rejects_two_readiness_gate_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "walk_forward.json"
            config_path.write_text(
                json.dumps(
                    {
                        "split_date": "2024-01-08",
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
            with (
                patch("scripts.run_walk_forward.validate_cleared_startup_gate_packet"),
                patch("scripts.run_walk_forward.validate_cn_stock_data_manifest_packet"),
                self.assertRaisesRegex(ValueError, "exactly one readiness gate"),
            ):
                run_walk_forward(
                    config_path=config_path,
                    source="processed-bars",
                    data_root=root,
                    startup_gate_packet=root / "startup.json",
                    data_manifest_packet=root / "manifest.json",
                    factor_batch_readiness_gate_packet=root / "batch.json",
                    factor_validation_readiness_packet=root / "validation.json",
                )


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
