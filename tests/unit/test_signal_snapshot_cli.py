import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.ops.factor_batch_readiness_gate import (
    build_factor_batch_readiness_gate,
    write_factor_batch_readiness_gate,
)
from quant_robot.ops.factor_mining_startup import build_factor_mining_startup_gate
from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_signal_snapshot import run_signal_snapshot


class SignalSnapshotCliTests(unittest.TestCase):
    def test_run_signal_snapshot_writes_research_only_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_signal_snapshot(
                source="fixture",
                market="CN",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=1,
                output_dir=Path(tmp),
            )

            self.assertEqual(result["data_mode"], "fixture")
            self.assertFalse(result["rebalance_plan"][0]["executable"])
            self.assertTrue((Path(tmp) / "targets.csv").exists())
            self.assertTrue((Path(tmp) / "rebalance_plan.csv").exists())
            self.assertTrue((Path(tmp) / "manifest.json").exists())

    def test_run_signal_snapshot_loads_all_processed_markets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "store"
            bars = load_demo_market_bars()
            for market, group in bars.groupby("market"):
                DatasetStore(root).write_frame(
                    group.reset_index(drop=True),
                    "processed/bars",
                    {"frequency": "1d", "market": market, "year": "2024"},
                )

            result = run_signal_snapshot(
                source="processed-bars",
                data_root=root,
                market="ALL",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=2,
                startup_gate_packet=_write_startup_gate(Path(tmp)),
                data_manifest_packet=_write_data_manifest(Path(tmp), root),
                factor_batch_readiness_gate_packet=_write_factor_batch_readiness_gate(Path(tmp), ready=True),
            )

            self.assertEqual(result["request"]["portfolio_scope"], "global")
            self.assertGreaterEqual(len({row["market"] for row in result["targets"]}), 1)

    def test_processed_cn_etf_snapshot_auto_uses_rotation_membership(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "store"
            bars = load_demo_market_bars()
            cn_etf = bars[bars["market"] == "CN_ETF"].reset_index(drop=True)
            DatasetStore(root).write_frame(
                cn_etf,
                "processed/bars",
                {"frequency": "1d", "market": "CN_ETF", "year": "2024"},
            )
            membership = cn_etf[["date", "asset_id", "market"]].copy()
            membership["symbol"] = membership["asset_id"].astype(str)
            membership["is_rotation_member"] = membership["asset_id"].eq("CN_ETF_XSHG_510300")
            DatasetStore(root).write_frame(
                membership,
                "metadata/cn_etf_rotation_membership",
                {"market": "CN_ETF"},
            )

            result = run_signal_snapshot(
                source="processed-bars",
                data_root=root,
                market="CN_ETF",
                factor_name="momentum_2",
                factor_windows=(2,),
                top_n=4,
                as_of_date="2024-01-08",
            )

            self.assertEqual({row["asset_id"] for row in result["targets"]}, {"CN_ETF_XSHG_510300"})
            self.assertEqual(result["request"]["rotation_membership_root"], str(root))
            self.assertTrue(result["request"]["rotation_membership_required"])

    def test_processed_cn_snapshot_requires_ready_factor_batch_readiness_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            readiness_packet = _write_factor_batch_readiness_gate(root, ready=False)

            with patch("scripts.run_signal_snapshot.load_processed_bars") as load_bars:
                with self.assertRaisesRegex(ValueError, "factor batch readiness gate is not ready"):
                    run_signal_snapshot(
                        source="processed-bars",
                        data_root=root,
                        market="CN",
                        factor_name="momentum_2",
                        factor_windows=(2,),
                        top_n=1,
                        startup_gate_packet=_write_startup_gate(root),
                        data_manifest_packet=_write_data_manifest(root, root),
                        factor_batch_readiness_gate_packet=readiness_packet,
                    )

            load_bars.assert_not_called()


def _write_startup_gate(root: Path) -> Path:
    packet_path = root / "factor_mining_startup_gate.json"
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
    packet_path.write_text(json.dumps(packet), encoding="utf-8")
    return packet_path


def _write_data_manifest(root: Path, source_root: Path) -> Path:
    packet_path = root / "cn_stock_data_manifest.json"
    packet_path.write_text(
        json.dumps(
            {
                "generated_at": date.today().isoformat(),
                "status": "cleared",
                "summary": {"source_root": source_root.as_posix(), "bar_rows": 10, "bar_symbols": 2},
                "decision": {"data_manifest_cleared": True, "blockers": [], "warnings": []},
                "live_boundary_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    return packet_path


def _write_factor_batch_readiness_gate(root: Path, *, ready: bool) -> Path:
    output_dir = root / ("ready_readiness_gate" if ready else "blocked_readiness_gate")
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
    return output_dir / "factor_batch_readiness_gate.json"


if __name__ == "__main__":
    unittest.main()
