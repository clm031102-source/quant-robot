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
from scripts.run_bottom_exclusion_portfolio_backtest import run_bottom_exclusion_portfolio_backtest_cli


class BottomExclusionPortfolioBacktestCliTests(unittest.TestCase):
    def test_run_bottom_exclusion_portfolio_backtest_accepts_factor_label_and_bar_files(self):
        factors, labels, bars = _inputs()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            factors_path = root / "factors.csv"
            labels_path = root / "labels.csv"
            bars_path = root / "bars.csv"
            output_dir = root / "backtest"
            factors.to_csv(factors_path, index=False)
            labels.to_csv(labels_path, index=False)
            bars.to_csv(bars_path, index=False)

            result = run_bottom_exclusion_portfolio_backtest_cli(
                factors=factors_path,
                labels=labels_path,
                bars=bars_path,
                output_dir=output_dir,
                bottom_quantile=0.2,
                rebalance_interval=1,
                holding_period=1,
                cost_bps=0.0,
                market_impact_bps=0.0,
                min_positive_relative_fold_rate=0.5,
            )

            self.assertEqual(result["summary"]["cases"], 1)
            self.assertEqual(result["leaderboard"][0]["classification"], "costed_risk_filter_candidate")
            self.assertTrue((output_dir / "bottom_exclusion_portfolio_backtest.json").exists())
            self.assertTrue((output_dir / "leaderboard.csv").exists())

    def test_grid_source_requires_ready_factor_batch_readiness_gate_before_loading_authority_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config_path = root / "grid.json"
            config_path.write_text(
                json.dumps(
                    {
                        "markets": ["CN"],
                        "factor_names": ["momentum_2"],
                        "factor_windows": [2],
                        "top_n_values": [1],
                        "cost_bps_values": [0],
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

            with patch("scripts.run_bottom_exclusion_portfolio_backtest.load_authority_processed_bars_from_config") as load_bars:
                with self.assertRaisesRegex(ValueError, "factor batch readiness gate is not ready"):
                    run_bottom_exclusion_portfolio_backtest_cli(
                        grid_config=config_path,
                        source="authority-processed-bars",
                        data_root=root,
                        authority_bars_config=root / "authority_bars.json",
                        output_dir=root / "out",
                        startup_gate_packet=gate_packet,
                        data_manifest_packet=data_manifest,
                        factor_batch_readiness_gate_packet=readiness_dir / "factor_batch_readiness_gate.json",
                    )

            load_bars.assert_not_called()


def _inputs():
    factor_rows = []
    label_rows = []
    bar_rows = []
    for day_index, day in enumerate(pd.date_range("2024-01-02", periods=6, freq="D")):
        for asset_index in range(5):
            asset_id = f"asset_{asset_index}"
            factor_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "tail_filter",
                    "factor_value": float(asset_index + 1),
                }
            )
            label_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 1,
                    "execution_lag": 1,
                    "forward_return": (-0.05 - 0.001 * day_index)
                    if asset_index == 0
                    else (0.02 + 0.001 * (day_index % 2)),
                    "entry_date": day.date(),
                    "exit_date": day.date(),
                }
            )
            bar_rows.append(
                {
                    "date": day.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "adj_close": 10.0,
                    "amount": 1_000_000_000.0,
                }
            )
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(bar_rows)


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
