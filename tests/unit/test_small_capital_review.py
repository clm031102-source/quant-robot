import unittest

from quant_robot.ops.small_capital_review import (
    SmallCapitalReviewPolicy,
    build_small_capital_review_gate,
)


class SmallCapitalReviewGateTests(unittest.TestCase):
    def test_ready_review_packet_preserves_no_order_boundary(self):
        gate = build_small_capital_review_gate(
            _review_packet(),
            manual_rehearsal=_manual_rehearsal(),
            paper_observation=_paper_observation(fills=32, max_drawdown=-0.06, observation_days=45),
            pre_api_readiness=_pre_api_board(),
            observation_sufficiency={"status": "sufficient", "decision": {"observation_sufficiency_cleared": True}},
            market_regime_coverage=_market_regime_coverage(),
            reviewer="operator",
        )

        self.assertEqual(gate["stage"], "phase_6_1_small_capital_review_gate")
        self.assertEqual(gate["status"], "ready_for_manual_small_capital_review")
        self.assertTrue(gate["decision"]["manual_small_capital_review_ready"])
        self.assertFalse(gate["decision"]["live_boundary_allowed"])
        self.assertFalse(gate["decision"]["executable"])
        self.assertFalse(gate["boundary"]["live_order_allowed"])
        self.assertEqual(gate["boundary"]["broker_connection"], "disabled")
        self.assertTrue(gate["manual_approval_packet"]["requires_manual_approval"])
        self.assertFalse(gate["manual_approval_packet"]["executable"])
        self.assertEqual(gate["risk_limits"]["max_initial_capital"], 10000.0)
        self.assertEqual(gate["summary"]["blockers"], 0)
        self.assertIn("No broker", gate["markdown"])

    def test_manual_rehearsal_blocker_keeps_gate_blocked_and_non_executable(self):
        rehearsal = _manual_rehearsal(status="blocked", blockers=["manual_live_review_not_enabled"])

        gate = build_small_capital_review_gate(
            _review_packet(manual_allowed=False),
            manual_rehearsal=rehearsal,
            paper_observation=_paper_observation(fills=32, max_drawdown=-0.06, observation_days=45),
            pre_api_readiness=_pre_api_board(),
            market_regime_coverage=_market_regime_coverage(),
        )

        self.assertEqual(gate["status"], "blocked")
        self.assertFalse(gate["decision"]["manual_small_capital_review_ready"])
        self.assertFalse(gate["decision"]["live_boundary_allowed"])
        self.assertFalse(gate["manual_approval_packet"]["executable"])
        self.assertIn("manual_live_review_not_enabled", gate["decision"]["blockers"])
        requirements = {row["requirement_id"]: row for row in gate["requirements"]}
        self.assertEqual(requirements["manual_review_rehearsal"]["status"], "block")

    def test_insufficient_paper_or_drawdown_blocks_small_capital_review(self):
        policy = SmallCapitalReviewPolicy(min_paper_fills=30, min_observation_days=20, max_paper_drawdown=0.08)

        low_fills = build_small_capital_review_gate(
            _review_packet(),
            manual_rehearsal=_manual_rehearsal(),
            paper_observation=_paper_observation(fills=12, max_drawdown=-0.04, observation_days=45),
            pre_api_readiness=_pre_api_board(),
            market_regime_coverage=_market_regime_coverage(),
            policy=policy,
        )
        high_drawdown = build_small_capital_review_gate(
            _review_packet(),
            manual_rehearsal=_manual_rehearsal(),
            paper_observation=_paper_observation(fills=34, max_drawdown=-0.13, observation_days=45),
            pre_api_readiness=_pre_api_board(),
            market_regime_coverage=_market_regime_coverage(),
            policy=policy,
        )

        self.assertEqual(low_fills["status"], "blocked")
        self.assertIn("paper_fills_below_minimum", low_fills["decision"]["blockers"])
        self.assertEqual(high_drawdown["status"], "blocked")
        self.assertIn("paper_drawdown_above_limit", high_drawdown["decision"]["blockers"])
        self.assertFalse(low_fills["decision"]["live_boundary_allowed"])
        self.assertFalse(high_drawdown["decision"]["live_boundary_allowed"])

    def test_missing_or_insufficient_market_regime_coverage_blocks_review(self):
        policy = SmallCapitalReviewPolicy(min_market_regimes=2)

        missing = build_small_capital_review_gate(
            _review_packet(),
            manual_rehearsal=_manual_rehearsal(),
            paper_observation=_paper_observation(fills=34, max_drawdown=-0.04, observation_days=45),
            pre_api_readiness=_pre_api_board(),
            observation_sufficiency={"status": "sufficient", "decision": {"observation_sufficiency_cleared": True}},
            policy=policy,
        )
        thin = build_small_capital_review_gate(
            _review_packet(),
            manual_rehearsal=_manual_rehearsal(),
            paper_observation=_paper_observation(fills=34, max_drawdown=-0.04, observation_days=45),
            pre_api_readiness=_pre_api_board(),
            observation_sufficiency={"status": "sufficient", "decision": {"observation_sufficiency_cleared": True}},
            market_regime_coverage=_market_regime_coverage(covered_regimes=1),
            policy=policy,
        )

        self.assertEqual(missing["status"], "blocked")
        self.assertIn("market_regime_coverage_missing", missing["decision"]["blockers"])
        self.assertEqual(thin["status"], "blocked")
        self.assertIn("market_regimes_below_minimum", thin["decision"]["blockers"])
        requirements = {row["requirement_id"]: row for row in thin["requirements"]}
        self.assertEqual(requirements["market_regime_coverage"]["status"], "block")


def _review_packet(manual_allowed: bool = True) -> dict:
    return {
        "safety": "Research only. No broker connection, no account reads, no order placement, no live trading.",
        "manual_review_gate": {"allowed": manual_allowed, "reasons": [] if manual_allowed else ["manual_live_review_not_enabled"]},
        "selected_candidate": {
            "case_id": "CN_TUSHARE_pe_ttm_rank_top20",
            "market": "CN",
            "factor_name": "pe_ttm_rank",
            "promotion_status": "manual_live_review" if manual_allowed else "paper_ready",
        },
    }


def _manual_rehearsal(status: str = "ready_for_manual_review_rehearsal", blockers: list[str] | None = None) -> dict:
    return {
        "gate_status": status,
        "blockers": blockers or [],
        "dry_run": {
            "would_cross_live_boundary": False,
            "broker_connection": "disabled",
            "account_reads": "disabled",
            "order_placement": "disabled",
            "live_trading": "disabled",
            "executable": False,
        },
    }


def _paper_observation(fills: int, max_drawdown: float, observation_days: int) -> dict:
    return {
        "summary": {
            "observed_candidates": 1,
            "completed_candidates": 1,
            "total_guard_events": 0,
            "total_execution_events": 0,
        },
        "candidates": [
            {
                "case_id": "CN_TUSHARE_pe_ttm_rank_top20",
                "status": "completed",
                "observation_status": "observed",
                "fills": fills,
                "max_equity_drawdown": max_drawdown,
                "observation_window": {"start_date": "2026-01-01", "end_date": f"2026-01-{min(observation_days, 31):02d}"},
                "guard_summary": {"guard_events": 0},
                "execution_summary": {"execution_events": 0},
            }
        ],
    }


def _pre_api_board(status: str = "ready_for_api_boundary_planning") -> dict:
    return {
        "overall_status": status,
        "blocker_register": [] if status != "blocked" else [{"blocker_id": "provider_readiness_not_ready"}],
        "boundary": {
            "would_cross_live_boundary": False,
            "broker_connection": "disabled",
            "account_reads": "disabled",
            "order_placement": "disabled",
            "live_trading": "disabled",
        },
    }


def _market_regime_coverage(covered_regimes: int = 3) -> dict:
    regimes = ["bull", "bear", "sideways"][:covered_regimes]
    return {
        "status": "sufficient",
        "summary": {
            "covered_regimes": covered_regimes,
            "required_regimes": 2,
            "regimes": regimes,
            "observation_days": 45,
        },
        "decision": {"market_regime_coverage_cleared": covered_regimes >= 2, "blockers": [] if covered_regimes >= 2 else ["market_regimes_below_minimum"]},
    }


if __name__ == "__main__":
    unittest.main()
