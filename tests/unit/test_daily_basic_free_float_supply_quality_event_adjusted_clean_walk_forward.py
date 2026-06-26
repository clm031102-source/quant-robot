import unittest

from quant_robot.ops.daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward import (
    NEXT_FINAL_HOLDOUT_OR_PAPER_GATE,
    NEXT_HIBERNATE_OR_ROTATE,
    STAGE,
    summarize_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward,
)
from tests.unit.test_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun import (
    _round139_audit_payload,
)
from tests.unit.test_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun import (
    _mixed_basis_portfolio_frames,
)


class DailyBasicFreeFloatSupplyQualityEventAdjustedCleanWalkForwardTests(unittest.TestCase):
    def test_walk_forward_aggregates_clean_event_adjusted_folds_without_promoting(self) -> None:
        factors, bars, market_state = _mixed_basis_portfolio_frames()

        result = summarize_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward(
            factors,
            bars,
            round139_audit=_round139_audit_payload(),
            market_state_frame=market_state,
            exclusion_scope="all",
            guard_modes=("none",),
            cost_bps_values=(10.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=1,
            rebalance_interval=2,
            min_signal_amount=0.0,
            max_participation_rate=0.01,
            market_impact_bps=0.0,
            max_calendar_holding_days=10,
            min_overlap_adjusted_sharpe=-10.0,
            min_oos_overlap_adjusted_sharpe=-10.0,
            max_drawdown_floor=-1.0,
            rolling_train_days=2,
            rolling_test_days=1,
            rolling_step_days=1,
            min_test_trades=0,
            min_accepted_folds=1,
            min_test_total_return=-1.0,
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["event_exclusion_summary"]["requested_event_path_count"], 2)
        self.assertEqual(result["event_exclusion_summary"]["excluded_factor_rows"], 2)
        self.assertGreaterEqual(result["summary"]["fold_count"], 1)
        self.assertEqual(result["thresholds"]["rebalance_interval"], 2)
        self.assertEqual(result["summary"]["case_count"], 1)
        self.assertEqual(result["summary"]["walk_forward_accepted_candidates"], 1)
        self.assertEqual(result["leaderboard"][0]["validation_status"], "accepted")
        self.assertEqual(result["leaderboard"][0]["rebalance_interval"], 2)
        self.assertIn("_reb2_", result["leaderboard"][0]["case_id"])
        self.assertTrue(result["walk_forward_policy"]["fixed_global_rebalance_calendar"])
        self.assertGreaterEqual(result["leaderboard"][0]["accepted_folds"], 1)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertIn("final_holdout_not_read", result["promotion_policy"]["blockers"])
        self.assertEqual(result["next_direction"], NEXT_FINAL_HOLDOUT_OR_PAPER_GATE)

    def test_walk_forward_rejects_when_required_fold_count_is_not_met(self) -> None:
        factors, bars, market_state = _mixed_basis_portfolio_frames()

        result = summarize_daily_basic_free_float_supply_quality_event_adjusted_clean_walk_forward(
            factors,
            bars,
            round139_audit=_round139_audit_payload(),
            market_state_frame=market_state,
            exclusion_scope="all",
            guard_modes=("none",),
            cost_bps_values=(10.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=1,
            rebalance_interval=1,
            min_signal_amount=0.0,
            max_participation_rate=0.01,
            market_impact_bps=0.0,
            max_calendar_holding_days=10,
            min_overlap_adjusted_sharpe=-10.0,
            min_oos_overlap_adjusted_sharpe=999.0,
            max_drawdown_floor=-1.0,
            rolling_train_days=2,
            rolling_test_days=1,
            rolling_step_days=1,
            min_test_trades=0,
            min_accepted_folds=2,
            min_test_total_return=-1.0,
        )

        self.assertEqual(result["summary"]["walk_forward_accepted_candidates"], 0)
        self.assertEqual(result["leaderboard"][0]["validation_status"], "rejected")
        self.assertIn("accepted_folds_below_minimum", result["leaderboard"][0]["validation_blockers"])
        self.assertEqual(result["next_direction"], NEXT_HIBERNATE_OR_ROTATE)


if __name__ == "__main__":
    unittest.main()
