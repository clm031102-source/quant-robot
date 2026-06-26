import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.ops.factor_mining_candidate_plan_gate import (
    build_factor_mining_candidate_plan_gate,
    default_cn_stock_pre_mining_control_plan,
    default_cn_stock_promotion_policy,
)
from quant_robot.ops.factor_mining_startup import build_factor_mining_startup_gate
from scripts.run_experiment_grid import assert_grid_succeeded, run_grid


class ExperimentGridCliTests(unittest.TestCase):
    def test_run_grid_uses_json_config_and_fixture_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "grid.json"
            output_dir = Path(tmp) / "reports"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_names": ["momentum_2"],
                        "factor_windows": [2],
                        "top_n_values": [1],
                        "cost_bps_values": [0],
                        "output_dir": str(output_dir),
                    }
                ),
                encoding="utf-8",
            )

            result = run_grid(config_path=config_path, source="fixture")

            self.assertEqual(result["summary"]["cases"], 1)
            self.assertTrue((output_dir / "leaderboard.csv").exists())

    def test_assert_grid_succeeded_fails_when_cases_failed(self):
        result = {
            "summary": {"cases": 1, "completed": 0, "failed": 1, "no_trades": 0},
            "leaderboard": [{"case_id": "bad_case", "status": "failed", "error": "top_n must be positive"}],
        }

        with self.assertRaisesRegex(RuntimeError, "experiment grid failed"):
            assert_grid_succeeded(result)

    def test_assert_grid_succeeded_fails_when_no_case_completed(self):
        result = {
            "summary": {"cases": 1, "completed": 0, "failed": 0, "no_trades": 1},
            "leaderboard": [{"case_id": "empty_case", "status": "no_trades", "error": None}],
        }

        with self.assertRaisesRegex(RuntimeError, "no completed experiment cases"):
            assert_grid_succeeded(result)

    def test_processed_cn_grid_requires_cleared_startup_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps({"markets": ["CN"], "factor_names": ["momentum_2"], "factor_windows": [2]}),
                encoding="utf-8",
            )

            with patch("scripts.run_experiment_grid.load_processed_bars") as load_bars:
                with self.assertRaisesRegex(ValueError, "startup gate"):
                    run_grid(
                        config_path=config_path,
                        source="processed-bars",
                        data_root=root,
                        startup_gate_packet=root / "missing_startup_gate.json",
                        data_manifest_packet=root / "missing_data_manifest.json",
                    )

            load_bars.assert_not_called()

    def test_processed_cn_grid_does_not_allow_startup_gate_bypass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps({"markets": ["CN"], "factor_names": ["momentum_2"], "factor_windows": [2]}),
                encoding="utf-8",
            )

            with patch("scripts.run_experiment_grid.load_processed_bars") as load_bars:
                with self.assertRaisesRegex(ValueError, "startup gate cannot be bypassed"):
                    run_grid(
                        config_path=config_path,
                        source="processed-bars",
                        data_root=root,
                        startup_gate_packet=root / "missing_startup_gate.json",
                        data_manifest_packet=root / "missing_data_manifest.json",
                        allow_missing_startup_gate=True,
                    )

            load_bars.assert_not_called()

    def test_processed_cn_grid_accepts_cleared_startup_gate_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps({"markets": ["CN"], "factor_names": ["momentum_2"], "factor_windows": [2]}),
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
            candidate_plan_gate = root / "factor_mining_candidate_plan_gate.json"
            candidate_plan_gate.write_text(_valid_candidate_plan_gate_packet_json(), encoding="utf-8")
            expected = {"summary": {"cases": 1, "completed": 1, "failed": 0}, "leaderboard": []}

            with patch("scripts.run_experiment_grid.load_processed_bars", return_value=pd.DataFrame({"market": ["CN"]})) as load_bars:
                with patch("scripts.run_experiment_grid.run_experiment_grid", return_value=expected) as runner:
                    result = run_grid(
                        config_path=config_path,
                        source="processed-bars",
                        data_root=root,
                        startup_gate_packet=gate_packet,
                        data_manifest_packet=data_manifest,
                        candidate_plan_gate_packet=candidate_plan_gate,
                    )

            self.assertEqual(result, expected)
            load_bars.assert_called_once()
            runner.assert_called_once()

    def test_authority_processed_cn_grid_uses_authority_loader(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps({"markets": ["CN"], "factor_names": ["momentum_2"], "factor_windows": [2]}),
                encoding="utf-8",
            )
            authority_config = root / "authority.json"
            authority_config.write_text(json.dumps({"market": "CN", "segments": []}), encoding="utf-8")
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
            candidate_plan_gate = root / "factor_mining_candidate_plan_gate.json"
            candidate_plan_gate.write_text(_valid_candidate_plan_gate_packet_json(), encoding="utf-8")
            expected = {"summary": {"cases": 1, "completed": 1, "failed": 0}, "leaderboard": []}

            with patch("scripts.run_experiment_grid.load_authority_processed_bars_from_config", return_value=pd.DataFrame({"market": ["CN"]})) as load_bars:
                with patch("scripts.run_experiment_grid.run_experiment_grid", return_value=expected) as runner:
                    result = run_grid(
                        config_path=config_path,
                        source="authority-processed-bars",
                        data_root=root,
                        authority_bars_config=authority_config,
                        startup_gate_packet=gate_packet,
                        data_manifest_packet=data_manifest,
                        candidate_plan_gate_packet=candidate_plan_gate,
                    )

            self.assertEqual(result, expected)
            load_bars.assert_called_once_with(authority_config, markets=("CN",))
            runner.assert_called_once()
            self.assertIsNone(runner.call_args.kwargs.get("progress"))

    def test_run_grid_passes_progress_callback_to_experiment_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps({"markets": ["CN"], "factor_names": ["momentum_2"], "factor_windows": [2]}),
                encoding="utf-8",
            )
            expected = {"summary": {"cases": 1, "completed": 1, "failed": 0}, "leaderboard": []}
            events = []

            with patch("scripts.run_experiment_grid.run_experiment_grid", return_value=expected) as runner:
                run_grid(config_path=config_path, source="fixture", progress=events.append)

            runner.call_args.kwargs["progress"]({"event": "probe"})
            self.assertEqual([event["event"] for event in events], ["load_bars_start", "load_bars_done", "probe"])
            self.assertEqual(events[0]["source"], "fixture")
            self.assertGreater(events[1]["bar_rows"], 0)

    def test_authority_processed_cn_grid_rejects_missing_year_coverage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_names": ["momentum_2"],
                        "factor_windows": [2],
                        "start_date": "2023-01-01",
                        "end_date": "2025-12-31",
                    }
                ),
                encoding="utf-8",
            )
            authority_config = root / "authority.json"
            authority_config.write_text(json.dumps({"market": "CN", "segments": []}), encoding="utf-8")
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
            candidate_plan_gate = root / "factor_mining_candidate_plan_gate.json"
            candidate_plan_gate.write_text(_valid_candidate_plan_gate_packet_json(), encoding="utf-8")
            bars = pd.DataFrame(
                {
                    "date": ["2023-01-03", "2025-01-02"],
                    "market": ["CN", "CN"],
                }
            )

            with patch("scripts.run_experiment_grid.load_authority_processed_bars_from_config", return_value=bars):
                with patch("scripts.run_experiment_grid.run_experiment_grid") as runner:
                    with self.assertRaisesRegex(ValueError, "missing required years: 2024"):
                        run_grid(
                            config_path=config_path,
                            source="authority-processed-bars",
                            data_root=root,
                            authority_bars_config=authority_config,
                            startup_gate_packet=gate_packet,
                            data_manifest_packet=data_manifest,
                            candidate_plan_gate_packet=candidate_plan_gate,
                        )

            runner.assert_not_called()

    def test_processed_cn_grid_requires_data_manifest_packet_after_startup_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps({"markets": ["CN"], "factor_names": ["momentum_2"], "factor_windows": [2]}),
                encoding="utf-8",
            )
            gate_packet = root / "factor_mining_startup_gate.json"
            gate_packet.write_text(_valid_startup_gate_packet_json(), encoding="utf-8")

            with patch("scripts.run_experiment_grid.load_processed_bars") as load_bars:
                with self.assertRaisesRegex(ValueError, "data manifest"):
                    run_grid(
                        config_path=config_path,
                        source="processed-bars",
                        data_root=root,
                        startup_gate_packet=gate_packet,
                    )

            load_bars.assert_not_called()

    def test_processed_cn_grid_requires_candidate_plan_gate_after_data_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps({"markets": ["CN"], "factor_names": ["momentum_2"], "factor_windows": [2]}),
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

            with patch("scripts.run_experiment_grid.load_processed_bars") as load_bars:
                with self.assertRaisesRegex(ValueError, "candidate plan gate"):
                    run_grid(
                        config_path=config_path,
                        source="processed-bars",
                        data_root=root,
                        startup_gate_packet=gate_packet,
                        data_manifest_packet=data_manifest,
                        candidate_plan_gate_packet=root / "missing_candidate_plan_gate.json",
                    )

            load_bars.assert_not_called()


def _valid_startup_gate_packet_json() -> str:
    config = {
        "scope_id": "cn_stock_factor_mining",
        "market": "CN",
        "asset_type": "stock",
        "allowed_machines": ["office_desktop"],
        "allowed_tasks": ["factor_validation"],
        "recommended_branch_prefixes": ["codex/factor-validation-cn-stock-"],
        "required_confirmations": [
            "machine_confirmed",
            "task_confirmed",
            "branch_confirmed",
            "push_policy_confirmed",
            "cn_stock_scope_confirmed",
            "etf_scope_rejected",
        ],
    }
    branch = "codex/factor-validation-cn-stock-test"
    packet = build_factor_mining_startup_gate(
        config,
        request={
            "machine": "office_desktop",
            "task": "factor_validation",
            "branch": branch,
            "market": "CN",
            "asset_type": "stock",
            "confirmations": {name: True for name in config["required_confirmations"]},
        },
        current_branch=branch,
    )
    return json.dumps(packet)


def _valid_candidate_plan_gate_packet_json() -> str:
    packet = build_factor_mining_candidate_plan_gate(
        {
            "stage": "test_preregistration",
            "research_control_plan": default_cn_stock_pre_mining_control_plan(),
            "promotion_policy": default_cn_stock_promotion_policy(),
            "candidates": [
                {
                    "factor_name": "test_cn_stock_public_reference_factor",
                    "family": "public_reference",
                    "market": "CN",
                    "asset_type": "stock",
                    "registration_status": "pre_registered",
                    "hypothesis_source": "public_reference:test",
                    "economic_rationale": "A documented public anomaly adapted to CN stock controls.",
                    "portfolio_backtest_allowed": False,
                    "promotion_allowed": False,
                }
            ],
        },
        gate_stage="discovery",
    )
    return json.dumps(packet)


if __name__ == "__main__":
    unittest.main()
