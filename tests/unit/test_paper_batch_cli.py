import json
import os
import subprocess
import sys
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
from scripts.run_paper_batch import load_paper_batch_config, run_paper_batch


class PaperBatchCliTests(unittest.TestCase):
    def test_load_paper_batch_config_accepts_utf8_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "paper_batch.json"
            config_path.write_text(
                "\ufeff" + json.dumps({"source": "fixture", "output_dir": str(Path(tmp) / "paper")}),
                encoding="utf-8",
            )

            config = load_paper_batch_config(config_path)

            self.assertEqual(config.source, "fixture")
            self.assertEqual(config.output_dir, Path(tmp) / "paper")

    def test_run_paper_batch_reports_missing_candidate_leaderboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_path = root / "missing_candidate_leaderboard.csv"
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "candidate_leaderboard": str(missing_path),
                        "source": "fixture",
                        "output_dir": str(root / "paper_batch"),
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "candidate_leaderboard not found"):
                run_paper_batch(config_path)

    def test_run_paper_batch_reports_missing_walk_forward_leaderboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_path = root / "missing_walk_forward_leaderboard.csv"
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(missing_path),
                        "source": "fixture",
                        "output_dir": str(root / "paper_batch"),
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "walk_forward_leaderboard not found"):
                run_paper_batch(config_path)

    def test_run_paper_batch_writes_one_manifest_per_accepted_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_momentum_2_top1_cost5_reb2",
                        "market": "CN",
                        "factor_name": "momentum_2",
                        "factor_windows": "[2]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "accepted",
                        "rank": 1,
                    },
                    {
                        "case_id": "CN_reversal_2_top1_cost5_reb2",
                        "market": "CN",
                        "factor_name": "reversal_2",
                        "factor_windows": "[2]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "rejected",
                        "rank": 2,
                    },
                ]
            ).to_csv(walk_forward_path, index=False)
            output_dir = root / "paper_batch"
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "source": "fixture",
                        "output_dir": str(output_dir),
                        "max_candidates": 5,
                        "initial_cash": 100000,
                        "max_asset_weight": 0.4,
                        "min_cash_weight": 0.1,
                    }
                ),
                encoding="utf-8",
            )

            result = run_paper_batch(config_path)

            self.assertEqual(result["summary"]["completed"], 1)
            self.assertEqual(result["summary"]["skipped"], 1)
            manifest_path = output_dir / "CN_momentum_2_top1_cost5_reb2" / "manifest.json"
            self.assertTrue(manifest_path.exists())
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["request"]["case_id"], "CN_momentum_2_top1_cost5_reb2")
            self.assertEqual(manifest["request"]["rebalance_interval"], 2)
            self.assertTrue((output_dir / "paper_batch_summary.csv").exists())
            self.assertTrue((output_dir / "paper_batch_summary.json").exists())

    def test_run_paper_batch_removes_stale_candidate_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_momentum_2_top1_cost5_reb2",
                        "market": "CN",
                        "factor_name": "momentum_2",
                        "factor_windows": "[2]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "rejected",
                        "rank": 1,
                    }
                ]
            ).to_csv(walk_forward_path, index=False)
            output_dir = root / "paper_batch"
            stale_dir = output_dir / "CN_old_candidate"
            stale_dir.mkdir(parents=True)
            (stale_dir / "manifest.json").write_text("{}", encoding="utf-8")
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "source": "fixture",
                        "output_dir": str(output_dir),
                        "max_candidates": 5,
                    }
                ),
                encoding="utf-8",
            )

            result = run_paper_batch(config_path)

            self.assertEqual(result["summary"]["completed"], 0)
            self.assertFalse((stale_dir / "manifest.json").exists())

    def test_paper_batch_script_runs_when_executed_directly(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_momentum_2_top1_cost5_reb2",
                        "market": "CN",
                        "factor_name": "momentum_2",
                        "factor_windows": "[2]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "accepted",
                        "rank": 1,
                    }
                ]
            ).to_csv(walk_forward_path, index=False)
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "source": "fixture",
                        "output_dir": str(root / "paper_batch"),
                        "max_candidates": 1,
                        "max_asset_weight": 0.4,
                        "min_cash_weight": 0.1,
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["PYTHONPATH"] = "src"

            completed = subprocess.run(
                [sys.executable, "scripts/run_paper_batch.py", "--config", str(config_path)],
                cwd=Path(__file__).resolve().parents[2],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_run_paper_batch_sweeps_risk_profiles_and_writes_best_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            walk_forward_path = root / "walk_forward.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_liquidity_10_top1_cost5_reb5",
                        "market": "CN",
                        "factor_name": "liquidity_10",
                        "factor_windows": "[5, 10]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "validation_status": "accepted",
                        "rank": 1,
                    }
                ]
            ).to_csv(walk_forward_path, index=False)
            output_dir = root / "paper_batch"
            config_path = root / "paper_batch.json"
            config_path.write_text(
                json.dumps(
                    {
                        "walk_forward_leaderboard": str(walk_forward_path),
                        "source": "fixture",
                        "output_dir": str(output_dir),
                        "max_candidates": 1,
                        "profile_max_drawdown": 0.25,
                        "risk_profiles": [
                            {"profile_id": "defensive", "max_asset_weight": 0.3, "max_drawdown_guard": 0.1},
                            {
                                "profile_id": "balanced",
                                "max_asset_weight": 0.5,
                                "max_drawdown_guard": 0.1,
                                "guard_cooldown_periods": 3,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            def fake_run_simulation(**kwargs):
                profile_id = "balanced" if kwargs["max_asset_weight"] == 0.5 else "defensive"
                sharpe = 0.62 if profile_id == "balanced" else 0.44
                return {
                    "data_mode": "research",
                    "request": {
                        "market": kwargs["market"],
                        "factor_name": kwargs["factor_name"],
                        "top_n": kwargs["top_n"],
                        "rebalance_interval": kwargs["rebalance_interval"],
                        "max_asset_weight": kwargs["max_asset_weight"],
                    },
                    "metrics": {
                        "sharpe": sharpe,
                        "total_return": 0.30,
                        "max_equity_drawdown": -0.20,
                    },
                    "intents": [],
                    "fills": [],
                    "positions": [],
                    "equity_curve": [],
                    "snapshots": [],
                    "guard_events": [],
                }

            with patch("scripts.run_paper_batch.run_simulation", side_effect=fake_run_simulation) as run_mock:
                result = run_paper_batch(config_path)

            self.assertEqual(run_mock.call_count, 2)
            selected = result["candidates"][0]
            self.assertEqual(selected["status"], "completed")
            self.assertEqual(selected["risk_profile_id"], "balanced")
            self.assertEqual(selected["attempted_profiles"], 2)
            self.assertAlmostEqual(selected["sharpe"], 0.62)
            manifest = json.loads((output_dir / "CN_liquidity_10_top1_cost5_reb5" / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["request"]["risk_profile_id"], "balanced")
            self.assertEqual(manifest["request"]["max_asset_weight"], 0.5)

    def test_run_paper_batch_accepts_alpha_factory_candidate_leaderboard(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path = root / "candidate_leaderboard.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_total_mv_log_top1_cost5_reb1",
                        "market": "CN",
                        "factor_source": "tushare_daily_basic",
                        "factor_name": "total_mv_log",
                        "factor_windows": "[1]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "rebalance_interval": 1,
                        "status": "completed",
                        "passes_adjusted_ic_p_value": True,
                        "adjusted_ic_p_value": 0.01,
                        "significance_status": "significant_positive",
                        "paper_candidate_allowed": True,
                        "candidate_rank": 1,
                    },
                    {
                        "case_id": "CN_pb_inverse_top1_cost5_reb1",
                        "market": "CN",
                        "factor_source": "tushare_daily_basic",
                        "factor_name": "pb_inverse",
                        "factor_windows": "[1]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "rebalance_interval": 1,
                        "status": "completed",
                        "passes_adjusted_ic_p_value": False,
                        "adjusted_ic_p_value": 0.20,
                        "significance_status": "not_significant",
                        "paper_candidate_allowed": False,
                        "candidate_rank": 2,
                    },
                    {
                        "case_id": "CN_turnover_rate_top1_cost5_reb1",
                        "market": "CN",
                        "factor_source": "tushare_daily_basic",
                        "factor_name": "turnover_rate",
                        "factor_windows": "[1]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "rebalance_interval": 1,
                        "status": "completed",
                        "passes_adjusted_ic_p_value": True,
                        "adjusted_ic_p_value": 0.001,
                        "significance_status": "significant_negative",
                        "paper_candidate_allowed": False,
                        "candidate_rank": 3,
                    },
                ]
            ).to_csv(candidate_path, index=False)
            output_dir = root / "paper_batch"
            factor_input_root = root / "factor_inputs"
            data_root = root / "data"
            startup_gate = _write_startup_gate(root)
            data_manifest = _write_data_manifest(root, data_root)
            readiness_gate = _write_factor_batch_readiness_gate(root, ready=True)
            config_path = root / "paper_batch_alpha.json"
            config_path.write_text(
                json.dumps(
                    {
                        "candidate_leaderboard": str(candidate_path),
                        "source": "processed-bars",
                        "data_root": str(data_root),
                        "factor_input_root": str(factor_input_root),
                        "startup_gate_packet": str(startup_gate),
                        "data_manifest_packet": str(data_manifest),
                        "factor_batch_readiness_gate_packet": str(readiness_gate),
                        "allow_review_required_data_manifest": True,
                        "output_dir": str(output_dir),
                        "max_candidates": 5,
                        "min_paper_sharpe": 0.5,
                        "min_paper_total_return": 0.0,
                        "max_paper_drawdown": 0.12,
                    }
                ),
                encoding="utf-8",
            )

            def fake_run_simulation(**kwargs):
                return {
                    "data_mode": "research",
                    "request": {
                        "market": kwargs["market"],
                        "factor_source": kwargs["factor_source"],
                        "factor_input_root": str(kwargs["factor_input_root"]),
                        "factor_name": kwargs["factor_name"],
                        "top_n": kwargs["top_n"],
                        "rebalance_interval": kwargs["rebalance_interval"],
                    },
                    "metrics": {"sharpe": 0.7, "total_return": 0.12, "max_equity_drawdown": -0.08},
                    "intents": [],
                    "fills": [],
                    "positions": [],
                    "equity_curve": [],
                    "snapshots": [],
                    "guard_events": [],
                    "execution_events": [],
                }

            with patch("scripts.run_paper_batch.run_simulation", side_effect=fake_run_simulation) as run_mock:
                result = run_paper_batch(config_path)

        self.assertEqual(result["summary"]["completed"], 1)
        self.assertEqual(result["summary"]["skipped"], 2)
        self.assertEqual(result["summary"]["paper_passed"], 1)
        self.assertEqual(result["summary"]["paper_failed"], 0)
        self.assertEqual(run_mock.call_count, 1)
        kwargs = run_mock.call_args.kwargs
        self.assertEqual(kwargs["factor_source"], "tushare_daily_basic")
        self.assertEqual(kwargs["factor_input_root"], factor_input_root)
        self.assertEqual(kwargs["startup_gate_packet"], startup_gate)
        self.assertEqual(kwargs["data_manifest_packet"], data_manifest)
        self.assertEqual(kwargs["factor_batch_readiness_gate_packet"], readiness_gate)
        self.assertTrue(kwargs["allow_review_required_data_manifest"])
        self.assertEqual(result["candidates"][1]["error"], "adjusted_ic_significance_not_passed")
        self.assertEqual(result["candidates"][2]["error"], "paper_candidate_not_allowed")
        self.assertTrue(result["candidates"][0]["paper_passed"])

    def test_processed_cn_paper_batch_blocks_before_output_when_readiness_gate_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path = root / "candidate_leaderboard.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_total_mv_log_top1_cost5_reb1",
                        "market": "CN",
                        "factor_source": "tushare_daily_basic",
                        "factor_name": "total_mv_log",
                        "factor_windows": "[1]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "rebalance_interval": 1,
                        "status": "completed",
                        "passes_adjusted_ic_p_value": True,
                        "adjusted_ic_p_value": 0.01,
                        "significance_status": "significant_positive",
                        "paper_candidate_allowed": True,
                        "candidate_rank": 1,
                    }
                ]
            ).to_csv(candidate_path, index=False)
            output_dir = root / "paper_batch"
            config_path = root / "paper_batch_alpha.json"
            config_path.write_text(
                json.dumps(
                    {
                        "candidate_leaderboard": str(candidate_path),
                        "source": "processed-bars",
                        "data_root": str(root / "data"),
                        "factor_input_root": str(root / "factor_inputs"),
                        "startup_gate_packet": str(_write_startup_gate(root)),
                        "data_manifest_packet": str(_write_data_manifest(root, root / "data")),
                        "factor_batch_readiness_gate_packet": str(_write_factor_batch_readiness_gate(root, ready=False)),
                        "allow_review_required_data_manifest": True,
                        "output_dir": str(output_dir),
                    }
                ),
                encoding="utf-8",
            )

            with patch("scripts.run_paper_batch.run_simulation") as run_mock:
                with self.assertRaisesRegex(ValueError, "factor batch readiness gate is not ready"):
                    run_paper_batch(config_path)

            run_mock.assert_not_called()
            self.assertFalse(output_dir.exists())

    def test_run_paper_batch_passes_moneyflow_input_root_for_moneyflow_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path = root / "candidate_leaderboard.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_net_mf_amount_ratio_top1_cost5_reb1",
                        "market": "CN",
                        "factor_source": "tushare_moneyflow",
                        "factor_name": "net_mf_amount_ratio",
                        "factor_windows": "[1]",
                        "top_n": 1,
                        "cost_bps": 5,
                        "rebalance_interval": 1,
                        "status": "completed",
                        "passes_adjusted_ic_p_value": True,
                        "adjusted_ic_p_value": 0.001,
                        "significance_status": "significant_positive",
                        "paper_candidate_allowed": True,
                        "candidate_rank": 1,
                    },
                ]
            ).to_csv(candidate_path, index=False)
            output_dir = root / "paper_batch"
            moneyflow_root = root / "moneyflow_inputs"
            data_root = root / "data"
            config_path = root / "paper_batch_moneyflow.json"
            config_path.write_text(
                json.dumps(
                    {
                        "candidate_leaderboard": str(candidate_path),
                        "source": "processed-bars",
                        "data_root": str(data_root),
                        "moneyflow_input_root": str(moneyflow_root),
                        "startup_gate_packet": str(_write_startup_gate(root)),
                        "data_manifest_packet": str(_write_data_manifest(root, data_root)),
                        "factor_batch_readiness_gate_packet": str(_write_factor_batch_readiness_gate(root, ready=True)),
                        "allow_review_required_data_manifest": True,
                        "output_dir": str(output_dir),
                        "max_candidates": 5,
                        "min_paper_sharpe": 0.5,
                        "min_paper_total_return": 0.0,
                        "max_paper_drawdown": 0.12,
                    }
                ),
                encoding="utf-8",
            )

            def fake_run_simulation(**kwargs):
                return {
                    "data_mode": "research",
                    "request": {
                        "market": kwargs["market"],
                        "factor_source": kwargs["factor_source"],
                        "moneyflow_input_root": str(kwargs["moneyflow_input_root"]),
                        "factor_name": kwargs["factor_name"],
                        "top_n": kwargs["top_n"],
                        "rebalance_interval": kwargs["rebalance_interval"],
                    },
                    "metrics": {"sharpe": 0.7, "total_return": 0.12, "max_equity_drawdown": -0.08},
                    "intents": [],
                    "fills": [],
                    "positions": [],
                    "equity_curve": [],
                    "snapshots": [],
                    "guard_events": [],
                    "execution_events": [],
                }

            with patch("scripts.run_paper_batch.run_simulation", side_effect=fake_run_simulation) as run_mock:
                result = run_paper_batch(config_path)

        self.assertEqual(result["summary"]["completed"], 1)
        kwargs = run_mock.call_args.kwargs
        self.assertEqual(kwargs["factor_source"], "tushare_moneyflow")
        self.assertEqual(kwargs["moneyflow_input_root"], moneyflow_root)
        self.assertIsNone(kwargs["factor_input_root"])
        self.assertTrue(result["candidates"][0]["paper_passed"])

    def test_run_paper_batch_marks_completed_candidates_that_fail_paper_thresholds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            candidate_path = root / "candidate_leaderboard.csv"
            pd.DataFrame(
                [
                    {
                        "case_id": "CN_turnover_rate_low_top20_cost5_reb1",
                        "market": "CN",
                        "factor_source": "tushare_daily_basic",
                        "factor_name": "turnover_rate_low",
                        "factor_windows": "[1]",
                        "top_n": 20,
                        "cost_bps": 5,
                        "rebalance_interval": 1,
                        "status": "completed",
                        "passes_adjusted_ic_p_value": True,
                        "adjusted_ic_p_value": 0.001,
                        "significance_status": "significant_positive",
                        "paper_candidate_allowed": True,
                        "candidate_rank": 1,
                    },
                ]
            ).to_csv(candidate_path, index=False)
            data_root = root / "data"
            config_path = root / "paper_batch_alpha.json"
            config_path.write_text(
                json.dumps(
                    {
                        "candidate_leaderboard": str(candidate_path),
                        "source": "processed-bars",
                        "data_root": str(data_root),
                        "factor_input_root": str(root / "factor_inputs"),
                        "startup_gate_packet": str(_write_startup_gate(root)),
                        "data_manifest_packet": str(_write_data_manifest(root, data_root)),
                        "factor_batch_readiness_gate_packet": str(_write_factor_batch_readiness_gate(root, ready=True)),
                        "allow_review_required_data_manifest": True,
                        "output_dir": str(root / "paper_batch"),
                        "min_paper_sharpe": 0.5,
                        "min_paper_total_return": 0.0,
                        "max_paper_drawdown": 0.12,
                    }
                ),
                encoding="utf-8",
            )

            def fake_run_simulation(**kwargs):
                return {
                    "data_mode": "research",
                    "request": {
                        "market": kwargs["market"],
                        "factor_source": kwargs["factor_source"],
                        "factor_input_root": str(kwargs["factor_input_root"]),
                        "factor_name": kwargs["factor_name"],
                        "top_n": kwargs["top_n"],
                        "rebalance_interval": kwargs["rebalance_interval"],
                    },
                    "metrics": {"sharpe": -1.0, "total_return": -0.05, "max_equity_drawdown": -0.08},
                    "intents": [],
                    "fills": [],
                    "positions": [],
                    "equity_curve": [],
                    "snapshots": [],
                    "guard_events": [],
                    "execution_events": [],
                }

            with patch("scripts.run_paper_batch.run_simulation", side_effect=fake_run_simulation):
                result = run_paper_batch(config_path)

        self.assertEqual(result["summary"]["completed"], 1)
        self.assertEqual(result["summary"]["paper_passed"], 0)
        self.assertEqual(result["summary"]["paper_failed"], 1)
        self.assertFalse(result["candidates"][0]["paper_passed"])
        self.assertIn("paper_sharpe_below_min", result["candidates"][0]["paper_rejection_reasons"])
        self.assertIn("paper_total_return_below_min", result["candidates"][0]["paper_rejection_reasons"])


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
