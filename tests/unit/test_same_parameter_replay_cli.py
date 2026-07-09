import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.ops.factor_batch_readiness_gate import (
    build_factor_batch_readiness_gate,
    write_factor_batch_readiness_gate,
)
from quant_robot.ops.factor_mining_startup import build_factor_mining_startup_gate
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_same_parameter_full_sample_replay import _load_bars, run_same_parameter_full_sample_replay_from_files


class SameParameterReplayCliTests(unittest.TestCase):
    def test_cli_runner_loads_fixture_candidates_and_writes_replay_pack(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            _write_candidate_csv(candidates)
            base_config = root / "base_config.json"
            _write_base_config(base_config)

            pack = run_same_parameter_full_sample_replay_from_files(
                candidates_csv=candidates,
                base_config_path=base_config,
                source="fixture",
                data_root=root / "unused",
                output_dir=root / "out",
                start_date="2024-01-02",
                end_date="2024-01-14",
            )

            self.assertEqual(pack["stage"], "same_parameter_full_sample_replay")
            self.assertEqual(pack["summary"]["candidates"], 1)
            self.assertTrue((root / "out" / "same_parameter_full_sample_replay.csv").exists())

    def test_processed_bars_source_accepts_authority_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_root = root / "store"
            bars = load_demo_market_bars()
            cn_bars = bars[bars["market"] == "CN"].copy()
            DatasetStore(store_root).write_frame(
                cn_bars,
                "processed/bars",
                {"frequency": "1d", "market": "CN", "year": "2024"},
            )
            config_path = root / "authority_bars.json"
            config_path.write_text(
                json.dumps(
                    {
                        "market": "CN",
                        "segments": [
                            {
                                "root": str(store_root),
                                "start_date": "2024-01-02",
                                "end_date": "2024-01-14",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            loaded = _load_bars(
                source="processed-bars",
                data_root=config_path,
                markets=("CN",),
                authority_bars_config=None,
            )

            self.assertFalse(loaded.empty)
            self.assertEqual(set(loaded["market"]), {"CN"})

    def test_processed_cn_replay_requires_ready_factor_batch_readiness_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidates = root / "candidates.csv"
            _write_candidate_csv(candidates)
            base_config = root / "base_config.json"
            _write_base_config(base_config)
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

            with patch("scripts.run_same_parameter_full_sample_replay.load_processed_bars") as load_bars:
                with self.assertRaisesRegex(ValueError, "factor batch readiness gate is not ready"):
                    run_same_parameter_full_sample_replay_from_files(
                        candidates_csv=candidates,
                        base_config_path=base_config,
                        source="processed-bars",
                        data_root=root,
                        output_dir=root / "out",
                        startup_gate_packet=gate_packet,
                        data_manifest_packet=data_manifest,
                        factor_batch_readiness_gate_packet=readiness_dir / "factor_batch_readiness_gate.json",
                    )

            load_bars.assert_not_called()


def _write_candidate_csv(path: Path) -> None:
    pd.DataFrame(
        [
            {
                "case_id": "CN_momentum_2_top1_cost0_reb1",
                "market": "CN",
                "factor_source": "technical",
                "factor_name": "momentum_2",
                "top_n": 1,
                "cost_bps": 0.0,
                "forward_horizon": 1,
                "execution_lag": 1,
                "rebalance_interval": 1,
                "strict_split_status": "pass",
                "strict_split_violations": 0,
                "strict_split_folds": 1,
            }
        ]
    ).to_csv(path, index=False)


def _write_base_config(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "markets": ["CN"],
                "factor_source": "technical",
                "factor_names": ["momentum_2"],
                "factor_windows": [2],
                "top_n_values": [1],
                "cost_bps_values": [0],
                "forward_horizon": 1,
                "execution_lag": 1,
                "rebalance_intervals": [1],
                "min_trades": 1,
                "write_case_artifacts": False,
            }
        ),
        encoding="utf-8",
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
