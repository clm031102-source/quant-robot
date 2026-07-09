import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.ops.factor_batch_readiness_gate import (
    build_factor_batch_readiness_gate,
    write_factor_batch_readiness_gate,
)
from quant_robot.ops.factor_mining_startup import build_factor_mining_startup_gate
from scripts.run_extreme_trade_diagnostic import run_extreme_trade_diagnostic_from_config


class ExtremeTradeDiagnosticCliTests(unittest.TestCase):
    def test_cli_runner_writes_lightweight_diagnostic_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            output_dir = root / "diagnostic"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_source": "daily_basic_value_liquidity_tail",
                        "factor_names": ["value_low_turnover_low_tail_20"],
                        "factor_windows": [20],
                        "factor_input_root": "daily-basic-root",
                        "factor_input_required": True,
                        "top_n_values": [100],
                        "cost_bps_values": [10],
                        "forward_horizon": 20,
                        "execution_lag": 1,
                        "rebalance_intervals": [5],
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch("scripts.run_extreme_trade_diagnostic._load_bars", return_value=_bars()) as load_bars,
                patch("scripts.run_extreme_trade_diagnostic.run_research_pipeline", return_value={"trades": _trades()}) as pipeline,
            ):
                diagnostic = run_extreme_trade_diagnostic_from_config(
                    config_path=config_path,
                    factor_name="value_low_turnover_low_tail_20",
                    source="fixture",
                    data_root=Path("data/processed"),
                    output_dir=output_dir,
                    threshold=5.0,
                )

            self.assertEqual(diagnostic["summary"]["extreme_trades"], 1)
            self.assertEqual(diagnostic["summary"]["capacity_limited_trades"], 1)
            load_bars.assert_called_once()
            passed_config = pipeline.call_args.args[1]
            self.assertEqual(passed_config.factor_source, "daily_basic_value_liquidity_tail")
            self.assertEqual(passed_config.factor_name, "value_low_turnover_low_tail_20")
            self.assertEqual(passed_config.top_n, 100)
            self.assertEqual(passed_config.cost_bps, 10.0)
            self.assertTrue((output_dir / "extreme_trade_diagnostic.json").exists())
            self.assertTrue((output_dir / "extreme_trade_diagnostic.csv").exists())
            self.assertTrue((output_dir / "capacity_limited_trades.csv").exists())
            self.assertTrue((output_dir / "top_weighted_return_trades.csv").exists())
            self.assertTrue((output_dir / "extreme_trade_diagnostic.md").exists())

    def test_processed_cn_diagnostic_requires_ready_factor_batch_readiness_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_source": "daily_basic_value_liquidity_tail",
                        "factor_names": ["value_low_turnover_low_tail_20"],
                        "factor_windows": [20],
                        "top_n_values": [100],
                        "cost_bps_values": [10],
                        "forward_horizon": 20,
                        "execution_lag": 1,
                        "rebalance_intervals": [5],
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

            with patch("scripts.run_extreme_trade_diagnostic._load_bars") as load_bars:
                with self.assertRaisesRegex(ValueError, "factor batch readiness gate is not ready"):
                    run_extreme_trade_diagnostic_from_config(
                        config_path=config_path,
                        factor_name="value_low_turnover_low_tail_20",
                        source="processed-bars",
                        data_root=root,
                        output_dir=root / "diagnostic",
                        startup_gate_packet=gate_packet,
                        data_manifest_packet=data_manifest,
                        factor_batch_readiness_gate_packet=readiness_dir / "factor_batch_readiness_gate.json",
                    )

            load_bars.assert_not_called()


def _trades() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "signal_date": pd.Timestamp("2024-01-01").date(),
                "entry_date": pd.Timestamp("2024-01-02").date(),
                "exit_date": pd.Timestamp("2024-01-22").date(),
                "asset_id": "CN_XSHE_000001",
                "market": "CN",
                "factor_name": "value_low_turnover_low_tail_20",
                "gross_return": 6.0,
                "weighted_return": 0.03,
                "target_weight": 0.01,
                "entry_amount": 50000.0,
                "participation_rate": 0.20,
                "capacity_limited": True,
            }
        ]
    )


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": pd.Timestamp("2024-01-02").date(),
                "asset_id": "CN_XSHE_000001",
                "symbol": "000001.SZ",
                "market": "CN",
                "adj_close": 10.0,
                "source": "fixture",
            },
            {
                "date": pd.Timestamp("2024-01-22").date(),
                "asset_id": "CN_XSHE_000001",
                "symbol": "000001.SZ",
                "market": "CN",
                "adj_close": 70.0,
                "source": "fixture",
            },
        ]
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
