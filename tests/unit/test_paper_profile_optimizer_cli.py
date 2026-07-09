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
from scripts.run_paper_profile_optimizer import run_paper_profile_optimizer


class PaperProfileOptimizerCliTests(unittest.TestCase):
    def test_run_paper_profile_optimizer_selects_profile_that_passes_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            constrained_pack = root / "constrained_candidate_search_pack.json"
            output_dir = root / "paper_profile_optimizer"
            constrained_pack.write_text(
                json.dumps(
                    {
                        "frontier_candidates": [
                            {
                                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                                "market": "CN_ETF",
                                "factor_name": "liquidity_10",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config_path = root / "paper_profile_optimizer.json"
            config_path.write_text(
                json.dumps(
                    {
                        "constrained_search_pack": str(constrained_pack),
                        "source": "processed-bars",
                        "data_root": str(root / "bars"),
                        "output_dir": str(output_dir),
                        "factor_windows": [5, 10, 20, 60, 120],
                        "min_paper_sharpe": 0.5,
                        "max_drawdown_limit": 0.2,
                        "risk_profiles": [
                            {
                                "profile_id": "too_soft",
                                "max_asset_weight": 0.35,
                                "max_gross_exposure": 0.7,
                                "min_cash_weight": 0.3,
                                "max_drawdown_guard": 0.1,
                                "guard_cooldown_periods": 5,
                            },
                            {
                                "profile_id": "candidate",
                                "max_asset_weight": 0.47,
                                "max_gross_exposure": 1.0,
                                "min_cash_weight": 0.0,
                                "max_drawdown_guard": 0.1,
                                "guard_cooldown_periods": 3,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            def fake_run_simulation(**kwargs):
                sharpe = 0.52 if kwargs["max_asset_weight"] == 0.47 else 0.48
                drawdown = -0.19 if kwargs["max_asset_weight"] == 0.47 else -0.15
                return {
                    "data_mode": "research",
                    "request": {"market": kwargs["market"], "factor_name": kwargs["factor_name"]},
                    "metrics": {
                        "sharpe": sharpe,
                        "total_return": 0.4,
                        "max_equity_drawdown": drawdown,
                    },
                    "fills": [{"fill_id": 1}],
                    "guard_events": [],
                }

            with patch("scripts.run_paper_profile_optimizer.run_simulation", side_effect=fake_run_simulation) as run_mock:
                pack = run_paper_profile_optimizer(config_path)

            self.assertEqual(run_mock.call_count, 2)
            self.assertEqual(pack["stage"], "phase_5_3_paper_profile_optimizer")
            self.assertEqual(pack["selection_status"], "paper_profile_selected")
            self.assertFalse(pack["live_boundary_allowed"])
            self.assertEqual(pack["selected_profile"]["profile_id"], "candidate")
            self.assertEqual(pack["summary"]["eligible_profiles"], 1)
            self.assertTrue((output_dir / "paper_profile_optimizer_pack.json").exists())
            self.assertTrue((output_dir / "paper_profile_attempts.csv").exists())

    def test_run_paper_profile_optimizer_selects_aggressive_growth_profile_by_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            constrained_pack = root / "constrained_candidate_search_pack.json"
            output_dir = root / "paper_profile_optimizer"
            constrained_pack.write_text(
                json.dumps(
                    {
                        "frontier_candidates": [
                            {
                                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                                "market": "CN_ETF",
                                "factor_name": "liquidity_10",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config_path = root / "paper_profile_optimizer.json"
            config_path.write_text(
                json.dumps(
                    {
                        "constrained_search_pack": str(constrained_pack),
                        "source": "processed-bars",
                        "data_root": str(root / "bars"),
                        "output_dir": str(output_dir),
                        "factor_windows": [5, 10, 20, 60, 120],
                        "min_paper_sharpe": 0.5,
                        "max_drawdown_limit": 0.2,
                        "risk_tiers": [
                            {
                                "tier_id": "capital_preservation",
                                "label": "Capital Preservation",
                                "max_drawdown_limit": 0.20,
                                "min_paper_sharpe": 0.5,
                                "min_paper_calmar": 1.0,
                                "priority": 1,
                            },
                            {
                                "tier_id": "aggressive_growth",
                                "label": "Aggressive Growth",
                                "max_drawdown_limit": 0.30,
                                "min_paper_sharpe": 0.5,
                                "min_paper_calmar": 1.0,
                                "priority": 3,
                            },
                        ],
                        "primary_risk_tier": "capital_preservation",
                        "risk_profiles": [
                            {
                                "profile_id": "strict_low_return",
                                "max_asset_weight": 0.40,
                                "max_gross_exposure": 0.8,
                                "min_cash_weight": 0.2,
                                "max_drawdown_guard": 0.08,
                                "guard_cooldown_periods": 5,
                            },
                            {
                                "profile_id": "aggressive_high_return",
                                "max_asset_weight": 0.58,
                                "max_gross_exposure": 1.0,
                                "min_cash_weight": 0.0,
                                "max_drawdown_guard": 0.12,
                                "guard_cooldown_periods": 3,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            def fake_run_simulation(**kwargs):
                if kwargs["max_asset_weight"] == 0.58:
                    metrics = {"sharpe": 0.64, "total_return": 1.05, "max_equity_drawdown": -0.28}
                else:
                    metrics = {"sharpe": 0.56, "total_return": 0.16, "max_equity_drawdown": -0.12}
                return {
                    "data_mode": "research",
                    "request": {"market": kwargs["market"], "factor_name": kwargs["factor_name"]},
                    "metrics": metrics,
                    "fills": [{"fill_id": value} for value in range(30)],
                    "guard_events": [],
                }

            with patch("scripts.run_paper_profile_optimizer.run_simulation", side_effect=fake_run_simulation):
                pack = run_paper_profile_optimizer(config_path)

            self.assertEqual(pack["stage"], "phase_5_4_risk_tier_policy")
            self.assertEqual(pack["selection_status"], "risk_tier_profile_selected")
            self.assertEqual(pack["selected_profile"]["profile_id"], "aggressive_high_return")
            self.assertEqual(pack["selected_profile"]["risk_tier"], "aggressive_growth")
            self.assertEqual(pack["policy"]["risk_tiers"][0]["min_trades"], 20)
            self.assertEqual(pack["summary"]["risk_tier_counts"]["aggressive_growth"], 1)
            self.assertGreater(pack["selected_profile"]["paper_calmar"], 1.0)
            self.assertFalse(pack["selected_profile"]["live_order_allowed"])

    def test_run_paper_profile_optimizer_rejects_profile_below_min_trades(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            constrained_pack = root / "constrained_candidate_search_pack.json"
            output_dir = root / "paper_profile_optimizer"
            constrained_pack.write_text(
                json.dumps(
                    {
                        "frontier_candidates": [
                            {
                                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                                "market": "CN_ETF",
                                "factor_name": "liquidity_10",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config_path = root / "paper_profile_optimizer.json"
            config_path.write_text(
                json.dumps(
                    {
                        "constrained_search_pack": str(constrained_pack),
                        "source": "processed-bars",
                        "data_root": str(root / "bars"),
                        "output_dir": str(output_dir),
                        "factor_windows": [5, 10, 20, 60, 120],
                        "min_paper_sharpe": 0.5,
                        "max_drawdown_limit": 0.2,
                        "risk_tiers": [
                            {
                                "tier_id": "aggressive_growth",
                                "label": "Aggressive Growth",
                                "max_drawdown_limit": 0.30,
                                "min_paper_sharpe": 0.5,
                                "min_paper_calmar": 1.0,
                                "min_trades": 20,
                                "priority": 1,
                            }
                        ],
                        "primary_risk_tier": "aggressive_growth",
                        "risk_profiles": [
                            {
                                "profile_id": "too_few_fills",
                                "max_asset_weight": 0.58,
                                "max_gross_exposure": 1.0,
                                "min_cash_weight": 0.0,
                                "max_drawdown_guard": 0.12,
                                "guard_cooldown_periods": 3,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            def fake_run_simulation(**kwargs):
                return {
                    "data_mode": "research",
                    "request": {"market": kwargs["market"], "factor_name": kwargs["factor_name"]},
                    "metrics": {"sharpe": 0.64, "total_return": 1.05, "max_equity_drawdown": -0.28},
                    "fills": [{"fill_id": 1}, {"fill_id": 2}],
                    "guard_events": [],
                }

            with patch("scripts.run_paper_profile_optimizer.run_simulation", side_effect=fake_run_simulation):
                pack = run_paper_profile_optimizer(config_path)

        self.assertEqual(pack["selection_status"], "no_paper_profile_candidate")
        self.assertIsNone(pack["selected_profile"])
        self.assertEqual(pack["policy"]["risk_tiers"][0]["min_trades"], 20)
        self.assertIn("paper_trades_below_min", pack["attempts"][0]["rejection_reasons"])

    def test_run_paper_profile_optimizer_reports_missing_frontier(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            constrained_pack = root / "constrained_candidate_search_pack.json"
            constrained_pack.write_text(json.dumps({"frontier_candidates": []}), encoding="utf-8")
            config_path = root / "paper_profile_optimizer.json"
            config_path.write_text(
                json.dumps(
                    {
                        "constrained_search_pack": str(constrained_pack),
                        "output_dir": str(root / "out"),
                    }
                ),
                encoding="utf-8",
            )

            pack = run_paper_profile_optimizer(config_path)

        self.assertEqual(pack["selection_status"], "no_frontier_candidate")
        self.assertEqual(pack["summary"]["frontier_candidates"], 0)
        self.assertEqual(pack["attempts"], [])

    def test_processed_cn_profile_optimizer_blocks_before_output_when_readiness_gate_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            constrained_pack = root / "constrained_candidate_search_pack.json"
            output_dir = root / "paper_profile_optimizer"
            data_root = root / "data"
            constrained_pack.write_text(
                json.dumps(
                    {
                        "frontier_candidates": [
                            {
                                "case_id": "CN_total_mv_log_top1_cost5_reb1",
                                "market": "CN",
                                "factor_name": "total_mv_log",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            config_path = root / "paper_profile_optimizer.json"
            config_path.write_text(
                json.dumps(
                    {
                        "constrained_search_pack": str(constrained_pack),
                        "source": "processed-bars",
                        "data_root": str(data_root),
                        "startup_gate_packet": str(_write_startup_gate(root)),
                        "data_manifest_packet": str(_write_data_manifest(root, data_root)),
                        "factor_batch_readiness_gate_packet": str(_write_factor_batch_readiness_gate(root, ready=False)),
                        "allow_review_required_data_manifest": True,
                        "output_dir": str(output_dir),
                    }
                ),
                encoding="utf-8",
            )

            with patch("scripts.run_paper_profile_optimizer.run_simulation") as run_mock:
                with self.assertRaisesRegex(ValueError, "factor batch readiness gate is not ready"):
                    run_paper_profile_optimizer(config_path)

            run_mock.assert_not_called()
            self.assertFalse(output_dir.exists())


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
