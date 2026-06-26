import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.daily_basic_free_float_supply_quality_event_adjusted_clean_rerun import (
    NEXT_CLEAN_WALK_FORWARD,
    STAGE,
    apply_event_path_exclusion_to_factor_frame,
    event_paths_from_round139_audit,
    summarize_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun,
)
from tests.unit.test_daily_basic_free_float_supply_quality_price_basis_repair_preflight_rerun import (
    _mixed_basis_portfolio_frames,
)


def _round139_audit_payload() -> dict[str, object]:
    return {
        "stage": "daily_basic_free_float_supply_quality_true_close_extreme_trade_liquidity_limit_audit",
        "trade_path_audit": [
            {
                "asset_id": "CN_XSHE_TEST1",
                "signal_date": "2025-06-26",
                "entry_date": "2025-06-27",
                "exit_date": "2025-07-01",
                "tradeability_class": "no_obvious_tradeability_blocker",
                "blockers": [],
                "reported_gross_return_max": 0.65,
            },
            {
                "asset_id": "CN_XSHE_TEST2",
                "signal_date": "2025-06-27",
                "entry_date": "2025-06-30",
                "exit_date": "2025-07-02",
                "tradeability_class": "bse_extreme_trade_risk",
                "blockers": ["bse_execution_permission_and_limit_regime_risk"],
                "reported_gross_return_max": 0.58,
            },
        ],
        "summary": {
            "raw_extreme_trade_count": 8,
            "unique_trade_path_count": 2,
            "no_obvious_tradeability_blocker_unique_paths": 1,
            "blocked_unique_paths": 1,
        },
    }


class DailyBasicFreeFloatSupplyQualityEventAdjustedCleanRerunTests(unittest.TestCase):
    def test_event_path_selection_and_factor_exclusion_are_scope_aware(self) -> None:
        factors, _, _ = _mixed_basis_portfolio_frames()
        audit = _round139_audit_payload()

        no_obvious_paths = event_paths_from_round139_audit(audit, exclusion_scope="no_obvious")
        filtered, summary = apply_event_path_exclusion_to_factor_frame(factors, no_obvious_paths)

        self.assertEqual(len(no_obvious_paths), 1)
        self.assertEqual(summary["requested_event_path_count"], 1)
        self.assertEqual(summary["excluded_factor_rows"], 1)
        self.assertFalse(
            (
                (filtered["asset_id"] == "CN_XSHE_TEST1")
                & (pd.to_datetime(filtered["date"]) == pd.Timestamp("2025-06-26"))
            ).any()
        )

        all_paths = event_paths_from_round139_audit(audit, exclusion_scope="all")
        _, all_summary = apply_event_path_exclusion_to_factor_frame(factors, all_paths)
        self.assertEqual(all_summary["requested_event_path_count"], 2)
        self.assertEqual(all_summary["excluded_factor_rows"], 2)

    def test_clean_rerun_keeps_hard_gates_after_excluding_event_paths(self) -> None:
        factors, bars, market_state = _mixed_basis_portfolio_frames()

        result = summarize_daily_basic_free_float_supply_quality_event_adjusted_clean_rerun(
            factors,
            bars,
            round139_audit=_round139_audit_payload(),
            market_state_frame=market_state,
            exclusion_scope="all",
            guard_modes=("none",),
            cost_bps_values=(10.0,),
            portfolio_values=(100_000.0,),
            top_n=1,
            holding_period=2,
            rebalance_interval=1,
            min_signal_amount=0.0,
            max_participation_rate=0.01,
            market_impact_bps=0.0,
            max_calendar_holding_days=10,
            min_overlap_adjusted_sharpe=10.0,
            min_oos_overlap_adjusted_sharpe=10.0,
            max_drawdown_floor=-1.0,
            train_end_date="2025-06-30",
            test_start_date="2025-07-01",
        )

        self.assertEqual(result["stage"], STAGE)
        self.assertEqual(result["event_exclusion_summary"]["requested_event_path_count"], 2)
        self.assertEqual(result["event_exclusion_summary"]["excluded_factor_rows"], 2)
        self.assertFalse(result["promotion_policy"]["promotion_allowed"])
        self.assertIn("event_adjusted_clean_rerun_is_preflight_only", result["promotion_policy"]["blockers"])
        self.assertEqual(result["next_direction"], NEXT_CLEAN_WALK_FORWARD)


if __name__ == "__main__":
    unittest.main()
