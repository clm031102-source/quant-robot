import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_daily_ops import run_daily_ops


class DailyOpsCliTests(unittest.TestCase):
    def test_run_daily_ops_writes_pack_from_existing_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promotion = root / "promotion_review_packet.json"
            readiness = root / "pre_api_readiness_board.json"
            signal = root / "signal_snapshot.json"
            simulation = root / "paper_simulation.json"
            output_dir = root / "daily_ops"
            promotion.write_text(
                json.dumps(
                    {
                        "selected_candidate": {
                            "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                            "market": "CN_ETF",
                            "factor_name": "liquidity_10",
                            "rank": 1,
                        }
                    }
                ),
                encoding="utf-8",
            )
            readiness.write_text(
                json.dumps(
                    {
                        "readiness_items": [{"track_id": "manual_review_gate", "status": "block"}],
                        "blocker_register": [{"blocker_id": "manual_live_review_not_enabled", "track_id": "manual_review_gate"}],
                    }
                ),
                encoding="utf-8",
            )
            signal.write_text(
                json.dumps(
                    {
                        "as_of_date": "2026-06-12",
                        "signal_date": "2026-06-12",
                        "targets": [{"asset_id": "asset_a", "target_weight": 1.0}],
                        "rebalance_plan": [{"asset_id": "asset_a", "market": "CN_ETF", "estimated_quantity_delta": 100.0, "delta_value": 1000.0}],
                    }
                ),
                encoding="utf-8",
            )
            simulation.write_text(
                json.dumps(
                    {
                        "metrics": {"total_return": 0.1, "max_equity_drawdown": -0.05},
                        "fills": [],
                        "guard_events": [],
                        "execution_events": [],
                    }
                ),
                encoding="utf-8",
            )

            with patch("scripts.run_daily_ops.DEFAULT_PAPER_PROFILE_PACK", root / "missing_profile.json"):
                pack = run_daily_ops(
                    promotion_review=promotion,
                    readiness_board=readiness,
                    signal_snapshot=signal,
                    paper_simulation=simulation,
                    output_dir=output_dir,
                    run_date="2026-06-13",
                )

            self.assertEqual(pack["stage"], "phase_5_0_daily_ops")
            self.assertEqual(pack["decision"]["status"], "paper_ready")
            self.assertTrue((output_dir / "daily_ops_pack.json").exists())
            self.assertTrue((output_dir / "daily_ops_pack.md").exists())
            self.assertTrue((output_dir / "daily_ops_tickets.csv").exists())
            self.assertTrue((output_dir / "daily_ops_summary.csv").exists())
            payload = json.loads((output_dir / "daily_ops_pack.json").read_text(encoding="utf-8"))
            self.assertFalse(payload["decision"]["live_boundary_allowed"])

    def test_run_daily_ops_applies_configured_drawdown_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promotion = root / "promotion_review_packet.json"
            readiness = root / "pre_api_readiness_board.json"
            signal = root / "signal_snapshot.json"
            simulation = root / "paper_simulation.json"
            output_dir = root / "daily_ops"
            promotion.write_text(
                json.dumps({"selected_candidate": {"case_id": "case_a", "market": "CN_ETF", "factor_name": "liquidity_10"}}),
                encoding="utf-8",
            )
            readiness.write_text(
                json.dumps({"blocker_register": [{"blocker_id": "manual_live_review_not_enabled", "track_id": "manual_review_gate"}]}),
                encoding="utf-8",
            )
            signal.write_text(
                json.dumps(
                    {
                        "targets": [{"asset_id": "asset_a", "target_weight": 1.0}],
                        "rebalance_plan": [{"asset_id": "asset_a", "market": "CN_ETF", "estimated_quantity_delta": 100.0}],
                    }
                ),
                encoding="utf-8",
            )
            simulation.write_text(
                json.dumps({"metrics": {"max_equity_drawdown": -0.05}, "fills": [], "guard_events": [], "execution_events": []}),
                encoding="utf-8",
            )

            with patch("scripts.run_daily_ops.DEFAULT_PAPER_PROFILE_PACK", root / "missing_profile.json"):
                pack = run_daily_ops(
                    promotion_review=promotion,
                    readiness_board=readiness,
                    signal_snapshot=signal,
                    paper_simulation=simulation,
                    output_dir=output_dir,
                    run_date="2026-06-13",
                    max_drawdown_limit=0.04,
                )

            self.assertEqual(pack["decision"]["status"], "blocked")
            self.assertEqual(pack["decision"]["non_manual_blocking_reasons"], ["risk_max_drawdown_breach"])
            self.assertEqual(pack["risk_policy"]["max_drawdown_limit"], -0.04)

    def test_run_daily_ops_uses_selected_paper_profile_parameters_and_tier_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promotion = root / "promotion_review_packet.json"
            readiness = root / "pre_api_readiness_board.json"
            paper_profile = root / "paper_profile_optimizer_pack.json"
            output_dir = root / "daily_ops"
            promotion.write_text(
                json.dumps(
                    {
                        "selected_candidate": {
                            "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                            "market": "CN_ETF",
                            "factor_name": "liquidity_10",
                            "rank": 1,
                        }
                    }
                ),
                encoding="utf-8",
            )
            readiness.write_text(
                json.dumps(
                    {
                        "blocker_register": [
                            {"blocker_id": "manual_live_review_not_enabled", "track_id": "manual_review_gate"}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            paper_profile.write_text(
                json.dumps(
                    {
                        "stage": "phase_5_4_risk_tier_policy",
                        "selected_profile": {
                            "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                            "profile_id": "cap60_guard12_cd3",
                            "risk_tier": "aggressive_growth",
                            "risk_tier_label": "Aggressive Growth",
                            "max_asset_weight": 0.6,
                            "max_gross_exposure": 1.0,
                            "min_cash_weight": 0.0,
                            "max_drawdown_guard": 0.12,
                            "guard_cooldown_periods": 3,
                        },
                        "policy": {
                            "risk_tiers": [
                                {"tier_id": "aggressive_growth", "max_drawdown_limit": -0.3}
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )

            def fake_signal(**kwargs):
                return {
                    "as_of_date": "2026-06-13",
                    "signal_date": "2026-06-13",
                    "targets": [{"asset_id": "asset_a", "target_weight": 0.6}],
                    "rebalance_plan": [{"asset_id": "asset_a", "market": "CN_ETF", "estimated_quantity_delta": 100.0}],
                }

            def fake_simulation(**kwargs):
                return {
                    "metrics": {"total_return": 0.9, "max_equity_drawdown": -0.25, "ending_equity": 190000.0},
                    "fills": [{"fill_id": value} for value in range(30)],
                    "guard_events": [],
                    "execution_events": [],
                }

            with patch("scripts.run_daily_ops.run_signal_snapshot", side_effect=fake_signal) as signal_mock, patch(
                "scripts.run_daily_ops.run_simulation",
                side_effect=fake_simulation,
            ) as simulation_mock:
                pack = run_daily_ops(
                    promotion_review=promotion,
                    readiness_board=readiness,
                    paper_profile_pack=paper_profile,
                    output_dir=output_dir,
                    run_date="2026-06-13",
                )

            self.assertEqual(pack["stage"], "phase_5_5_profile_daily_ops_activation")
            self.assertEqual(pack["decision"]["status"], "paper_ready")
            self.assertEqual(pack["risk_policy"]["max_drawdown_limit"], -0.3)
            self.assertEqual(pack["paper_profile"]["profile_id"], "cap60_guard12_cd3")
            self.assertEqual(pack["paper_profile"]["risk_tier"], "aggressive_growth")
            self.assertEqual(signal_mock.call_args.kwargs["max_asset_weight"], 0.6)
            self.assertEqual(simulation_mock.call_args.kwargs["max_asset_weight"], 0.6)
            self.assertEqual(simulation_mock.call_args.kwargs["max_drawdown_guard"], 0.12)
            self.assertEqual(simulation_mock.call_args.kwargs["guard_cooldown_periods"], 3)

    def test_run_daily_ops_uses_default_paper_profile_pack_when_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            promotion = root / "promotion_review_packet.json"
            readiness = root / "pre_api_readiness_board.json"
            paper_profile = root / "paper_profile_optimizer_pack.json"
            output_dir = root / "daily_ops"
            promotion.write_text(
                json.dumps(
                    {
                        "selected_candidate": {
                            "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                            "market": "CN_ETF",
                            "factor_name": "liquidity_10",
                        }
                    }
                ),
                encoding="utf-8",
            )
            readiness.write_text(
                json.dumps(
                    {
                        "blocker_register": [
                            {"blocker_id": "manual_live_review_not_enabled", "track_id": "manual_review_gate"}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            paper_profile.write_text(
                json.dumps(
                    {
                        "selected_profile": {
                            "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                            "profile_id": "cap60_guard12_cd3",
                            "risk_tier": "aggressive_growth",
                            "max_asset_weight": 0.6,
                            "max_gross_exposure": 1.0,
                            "min_cash_weight": 0.0,
                            "max_drawdown_guard": 0.12,
                            "guard_cooldown_periods": 3,
                        },
                        "policy": {"risk_tiers": [{"tier_id": "aggressive_growth", "max_drawdown_limit": -0.3}]},
                    }
                ),
                encoding="utf-8",
            )

            def fake_signal(**kwargs):
                return {
                    "signal_date": "2026-06-13",
                    "targets": [{"asset_id": "asset_a", "target_weight": 0.6}],
                    "rebalance_plan": [{"asset_id": "asset_a", "market": "CN_ETF", "estimated_quantity_delta": 100.0}],
                }

            def fake_simulation(**kwargs):
                return {
                    "metrics": {"total_return": 0.9, "max_equity_drawdown": -0.25},
                    "fills": [{"fill_id": value} for value in range(30)],
                    "guard_events": [],
                    "execution_events": [],
                }

            with patch("scripts.run_daily_ops.DEFAULT_PAPER_PROFILE_PACK", paper_profile), patch(
                "scripts.run_daily_ops.run_signal_snapshot",
                side_effect=fake_signal,
            ) as signal_mock, patch("scripts.run_daily_ops.run_simulation", side_effect=fake_simulation):
                pack = run_daily_ops(
                    promotion_review=promotion,
                    readiness_board=readiness,
                    output_dir=output_dir,
                    run_date="2026-06-13",
                )

            self.assertEqual(pack["stage"], "phase_5_5_profile_daily_ops_activation")
            self.assertEqual(pack["decision"]["status"], "paper_ready")
            self.assertEqual(pack["paper_profile"]["profile_id"], "cap60_guard12_cd3")
            self.assertEqual(signal_mock.call_args.kwargs["max_asset_weight"], 0.6)


if __name__ == "__main__":
    unittest.main()
