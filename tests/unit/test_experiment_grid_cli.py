import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

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
            expected = {"summary": {"cases": 1, "completed": 1, "failed": 0}, "leaderboard": []}

            with patch("scripts.run_experiment_grid.load_processed_bars", return_value=pd.DataFrame({"market": ["CN"]})) as load_bars:
                with patch("scripts.run_experiment_grid.run_experiment_grid", return_value=expected) as runner:
                    result = run_grid(
                        config_path=config_path,
                        source="processed-bars",
                        data_root=root,
                        startup_gate_packet=gate_packet,
                        data_manifest_packet=data_manifest,
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
                    )

            self.assertEqual(result, expected)
            load_bars.assert_called_once_with(authority_config, markets=("CN",))
            runner.assert_called_once()

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


def _valid_startup_gate_packet_json() -> str:
    return json.dumps(
        {
            "generated_at": date.today().isoformat(),
            "status": "cleared",
            "summary": {"market": "CN", "asset_type": "stock"},
            "research_direction": {
                "objective": "cn_stock_cross_sectional_alpha",
                "allowed_factor_families": ["price_volume", "daily_basic", "moneyflow", "composite"],
                "forbidden_directions": ["cn_etf_rotation", "single_family_lockin", "oos_tuning"],
                "stage_policy": {
                    "discovery": "Design and filter candidates only.",
                    "validation": "Run OOS only after discovery evidence clears.",
                    "final_holdout": "Read once; never tune after reading.",
                },
                "factor_family_rotation": {
                    "max_failed_batches_before_rotation": 1,
                    "max_single_family_share": 0.5,
                    "record_rejected_families": True,
                },
            },
            "repeatable_mining_protocol": {
                "source_audit": "data/reports/cn_stock_factor_mining_20260617_batch_audit.md",
                "next_direction": "two_stage_portfolio_construction_and_holding_sensitivity",
                "recently_rejected_directions": ["single_factor_top50_daily_long_only"],
                "required_experiment_design": [
                    "rank_band_vs_topn_comparison",
                    "holding_period_and_rebalance_sensitivity",
                ],
                "confirm_before_each_run": [
                    "previous_audit_read",
                    "next_direction_pre_registered",
                    "oos_holdout_not_touched",
                ],
            },
            "decision": {"startup_gate_cleared": True, "blockers": []},
        }
    )


if __name__ == "__main__":
    unittest.main()
