import unittest

from quant_robot.ops.profile_observation import build_profile_observation_pack


class ProfileObservationTests(unittest.TestCase):
    def test_pack_stops_observation_when_signal_data_is_stale(self):
        daily_ops = {
            "stage": "phase_5_5_profile_daily_ops_activation",
            "run_date": "2026-06-14",
            "candidate": {
                "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                "market": "CN_ETF",
                "factor_name": "liquidity_10",
            },
            "decision": {
                "status": "paper_ready",
                "paper_trading_allowed": True,
                "live_boundary_allowed": False,
                "non_manual_blocking_reasons": [],
            },
            "paper_profile": {
                "profile_id": "cap60_guard12_cd3",
                "risk_tier": "aggressive_growth",
                "max_asset_weight": 0.6,
                "max_gross_exposure": 1.0,
                "min_cash_weight": 0.0,
                "max_drawdown_guard": 0.12,
                "guard_cooldown_periods": 3,
            },
            "risk": {
                "total_return": 0.939358,
                "max_equity_drawdown": -0.252031,
                "guard_events": 712,
                "execution_blocks": 0,
            },
            "risk_policy": {"max_drawdown_limit": -0.3},
            "signal": {"signal_date": "2026-05-22", "target_gross_exposure": 0.6, "cash_weight": 0.4},
            "simulation": {"fills": 171, "guard_events": 712, "execution_events": 0},
        }
        simulation_manifest = {
            "request": {
                "max_asset_weight": 0.6,
                "max_gross_exposure": 1.0,
                "min_cash_weight": 0.0,
                "max_drawdown_guard": 0.12,
                "guard_cooldown_periods": 3,
            }
        }
        equity_curve = [
            {"date": "2026-05-20", "equity": 100000.0, "gross_exposure": 0.6},
            {"date": "2026-05-22", "equity": 193935.8, "gross_exposure": 0.0},
        ]

        pack = build_profile_observation_pack(
            daily_ops,
            simulation_manifest=simulation_manifest,
            equity_curve=equity_curve,
            run_date="2026-06-14",
            max_signal_age_days=7,
        )

        self.assertEqual(pack["stage"], "phase_5_6_profile_observation_ledger")
        self.assertEqual(pack["decision"]["observation_status"], "stopped")
        self.assertFalse(pack["decision"]["paper_observation_allowed"])
        self.assertIn("signal_data_stale", pack["decision"]["stop_reasons"])
        stale_rule = {row["rule_id"]: row for row in pack["stop_rules"]}["signal_data_stale"]
        self.assertEqual(stale_rule["status"], "stop")
        self.assertEqual(stale_rule["observed_value"], 23)
        drawdown_rule = {row["rule_id"]: row for row in pack["stop_rules"]}["drawdown_policy_breach"]
        self.assertEqual(drawdown_rule["status"], "pass")
        self.assertEqual(drawdown_rule["reason"], "Paper drawdown must remain within the active risk tier limit.")
        self.assertEqual(pack["ledger"][0]["profile_id"], "cap60_guard12_cd3")
        self.assertEqual(pack["ledger"][0]["risk_tier"], "aggressive_growth")
        self.assertEqual(pack["ledger"][0]["signal_age_days"], 23)
        self.assertEqual(pack["next_actions"][0]["action"], "refresh_tushare_recent_data")
        self.assertFalse(pack["live_boundary_allowed"])


if __name__ == "__main__":
    unittest.main()
