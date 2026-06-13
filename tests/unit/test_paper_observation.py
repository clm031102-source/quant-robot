import unittest

from quant_robot.ops.paper_observation import build_paper_observation_pack


class PaperObservationPackTests(unittest.TestCase):
    def test_pack_summarizes_observation_window_risk_profiles_and_events(self):
        paper_batch = {
            "summary": {"cases": 2, "completed": 1, "failed": 0, "skipped": 1},
            "candidates": [
                {
                    "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                    "status": "completed",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_10",
                    "risk_profile_id": "balanced",
                    "total_return": 0.2,
                    "sharpe": 0.7,
                    "max_equity_drawdown": -0.12,
                    "fills": 10,
                    "guard_events": 2,
                },
                {
                    "case_id": "CN_ETF_momentum_20_top2_cost5_reb5",
                    "status": "skipped",
                    "market": "CN_ETF",
                    "factor_name": "momentum_20",
                    "risk_profile_id": None,
                },
            ],
        }
        artifacts = {
            "CN_ETF_liquidity_10_top1_cost5_reb5": {
                "manifest": {
                    "data_mode": "research",
                    "request": {"risk_profile_id": "balanced", "market": "CN_ETF"},
                    "metrics": {"sharpe": 0.7, "total_return": 0.2, "max_equity_drawdown": -0.12},
                },
                "equity_curve": [
                    {"date": "2024-01-02", "equity": 100000.0},
                    {"date": "2024-02-01", "equity": 120000.0},
                ],
                "guard_events": [
                    {"date": "2024-01-10", "event_type": "drawdown_guard_triggered", "blocked_buy_intents": 0},
                    {"date": "2024-01-11", "event_type": "drawdown_guard_blocked_buys", "blocked_buy_intents": 2},
                ],
                "execution_events": [{"date": "2024-01-12", "blocked_reason": "zero_volume"}],
            }
        }

        pack = build_paper_observation_pack(paper_batch, artifacts)

        self.assertEqual(pack["stage"], "phase_3_3_paper_observation_extension")
        self.assertEqual(pack["summary"]["completed_candidates"], 1)
        self.assertEqual(pack["summary"]["observed_candidates"], 1)
        self.assertEqual(pack["summary"]["skipped_candidates"], 1)
        observed = pack["candidates"][0]
        self.assertEqual(observed["observation_window"]["start_date"], "2024-01-02")
        self.assertEqual(observed["observation_window"]["end_date"], "2024-02-01")
        self.assertEqual(observed["guard_summary"]["trigger_events"], 1)
        self.assertEqual(observed["guard_summary"]["blocked_buy_events"], 1)
        self.assertEqual(observed["guard_summary"]["total_blocked_buy_intents"], 2)
        self.assertEqual(observed["execution_summary"]["execution_events"], 1)
        self.assertEqual(pack["risk_profile_comparison"][0]["risk_profile_id"], "balanced")
        self.assertEqual(pack["risk_profile_comparison"][0]["completed_candidates"], 1)
        self.assertEqual(pack["metric_trend"][0]["case_id"], "CN_ETF_liquidity_10_top1_cost5_reb5")
        self.assertIn("Phase 3.3", pack["markdown"])
        self.assertIn("CN_ETF_liquidity_10_top1_cost5_reb5", pack["markdown"])


if __name__ == "__main__":
    unittest.main()
