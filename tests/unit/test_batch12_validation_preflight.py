import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from quant_robot.ops.batch12_validation_preflight import (
    build_batch12_validation_preflight,
    validate_batch12_validation_preflight_packet,
    write_batch12_validation_preflight,
)


def _handoff() -> dict:
    return {
        "stage": "cn_stock_batch12_validation_handoff",
        "market": "CN",
        "asset_type": "stock",
        "source_discovery_report": "data/reports/cn_stock_champion_staggered_schedule_20260617",
        "validation_window": {"start": "2025-01-01", "end": "2025-12-31"},
        "final_holdout_window": {"start": "2026-01-01", "end": "2026-06-15", "allowed_next": False},
        "prior_related_hypotheses": 137,
        "frozen_candidates": [
            {
                "case_id": "rankic_neg1_downside_range_blend_hold20_top50_every1_offset0_cost10_prev_month_ret_gt_neg1",
                "cost_bps": 10,
                "schedule_interval": 1,
                "schedule_offset": 0,
                "holding_period": 20,
                "top_n": 50,
            },
            {
                "case_id": "rankic_neg1_downside_range_blend_hold20_top50_every1_offset0_cost20_prev_month_ret_gt_neg1",
                "cost_bps": 20,
                "schedule_interval": 1,
                "schedule_offset": 0,
                "holding_period": 20,
                "top_n": 50,
            },
        ],
        "required_controls": [
            "twenty_twenty_five_oos_only",
            "overlap_aware_return_statistics",
            "daily_vs_every2_every3_controls",
            "cost_capacity_turnover_stress",
            "cumulative_multiple_testing_accounting",
            "no_parameter_tuning_during_oos",
            "final_holdout_only_after_oos_clearance",
        ],
        "required_overlap_statistics": [
            "naive_sharpe",
            "autocorr_adjusted_sharpe",
            "newey_west_standard_error_mean",
            "newey_west_t_stat_mean",
            "variance_inflation",
            "effective_sample_size",
            "autocorrelations",
            "overlap_risk_flag",
        ],
    }


def _startup_gate() -> dict:
    return {
        "generated_at": date.today().isoformat(),
        "status": "cleared",
        "summary": {"market": "CN", "asset_type": "stock"},
        "decision": {"startup_gate_cleared": True, "blockers": []},
        "research_direction": {
            "objective": "cn_stock_cross_sectional_alpha",
            "allowed_factor_families": ["price_volume", "daily_basic", "moneyflow", "composite"],
            "stage_policy": {
                "discovery": "Design only.",
                "validation": "2025 only.",
                "final_holdout": "Read once later.",
            },
            "factor_family_rotation": {"max_failed_batches_before_rotation": 1},
        },
        "repeatable_mining_protocol": {
            "source_audit": "data/reports/cn_stock_factor_mining_20260617_batch_audit.md",
            "next_direction": "factor_validation_required_for_daily_champion_oos_candidates",
            "recently_rejected_directions": ["overlapping_holdings_as_independent_returns"],
            "required_experiment_design": ["overlap_aware_return_statistics"],
            "confirm_before_each_run": ["batch12_validation_handoff_read"],
        },
        "live_boundary_allowed": False,
    }


class Batch12ValidationPreflightTests(unittest.TestCase):
    def test_clears_only_for_factor_validation_branch_and_frozen_2025_plan(self) -> None:
        packet = build_batch12_validation_preflight(
            handoff=_handoff(),
            startup_gate=_startup_gate(),
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260617",
                "current_branch": "codex/factor-validation-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
                "final_holdout_touched": False,
            },
        )

        self.assertEqual(packet["status"], "cleared")
        self.assertTrue(packet["decision"]["validation_preflight_cleared"])
        self.assertEqual(packet["validation_window"], {"start": "2025-01-01", "end": "2025-12-31"})
        self.assertEqual(len(packet["frozen_candidates"]), 2)
        self.assertIn("overlap_aware_return_statistics", packet["required_controls"])
        self.assertIn("autocorr_adjusted_sharpe", packet["required_overlap_statistics"])
        self.assertFalse(packet["final_holdout_allowed"])
        self.assertFalse(packet["live_boundary_allowed"])

    def test_blocks_batch_branch_final_holdout_or_missing_overlap_control(self) -> None:
        handoff = _handoff()
        handoff["required_controls"] = [
            item for item in handoff["required_controls"] if item != "overlap_aware_return_statistics"
        ]
        packet = build_batch12_validation_preflight(
            handoff=handoff,
            startup_gate=_startup_gate(),
            request={
                "machine": "office_desktop",
                "task": "factor_batch",
                "branch": "codex/factor-batch-cn-stock-20260617",
                "current_branch": "codex/factor-batch-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
                "final_holdout_touched": True,
            },
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertIn("task_not_factor_validation", packet["decision"]["blockers"])
        self.assertIn("branch_not_factor_validation", packet["decision"]["blockers"])
        self.assertIn("final_holdout_touched", packet["decision"]["blockers"])
        self.assertIn("missing_required_control:overlap_aware_return_statistics", packet["decision"]["blockers"])

    def test_blocks_missing_required_overlap_statistic_fields(self) -> None:
        handoff = _handoff()
        handoff["required_overlap_statistics"] = ["naive_sharpe"]

        packet = build_batch12_validation_preflight(
            handoff=handoff,
            startup_gate=_startup_gate(),
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260617",
                "current_branch": "codex/factor-validation-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
            },
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertIn(
            "missing_required_overlap_statistic:autocorr_adjusted_sharpe",
            packet["decision"]["blockers"],
        )

    def test_blocks_wrong_validation_window_or_startup_gate_direction(self) -> None:
        handoff = _handoff()
        handoff["validation_window"] = {"start": "2024-10-01", "end": "2025-12-31"}
        startup_gate = _startup_gate()
        startup_gate["repeatable_mining_protocol"]["next_direction"] = "keep_mining_discovery"

        packet = build_batch12_validation_preflight(
            handoff=handoff,
            startup_gate=startup_gate,
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260617",
                "current_branch": "codex/factor-validation-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
            },
        )

        self.assertEqual(packet["status"], "blocked")
        self.assertIn("validation_window_not_2025_only", packet["decision"]["blockers"])
        self.assertIn("startup_gate_next_direction_mismatch", packet["decision"]["blockers"])

    def test_write_and_validate_preflight_packet(self) -> None:
        packet = build_batch12_validation_preflight(
            handoff=_handoff(),
            startup_gate=_startup_gate(),
            request={
                "machine": "office_desktop",
                "task": "factor_validation",
                "branch": "codex/factor-validation-cn-stock-20260617",
                "current_branch": "codex/factor-validation-cn-stock-20260617",
                "market": "CN",
                "asset_type": "stock",
            },
        )

        with tempfile.TemporaryDirectory() as tmp:
            write_batch12_validation_preflight(Path(tmp), packet)
            path = Path(tmp) / "batch12_validation_preflight.json"
            loaded = validate_batch12_validation_preflight_packet(path)

        self.assertEqual(loaded["status"], "cleared")

    def test_validate_rejects_stale_or_blocked_packet(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "batch12_validation_preflight.json"
            path.write_text(
                json.dumps(
                    {
                        "generated_at": (date.today() - timedelta(days=1)).isoformat(),
                        "status": "cleared",
                        "decision": {"validation_preflight_cleared": True, "blockers": []},
                        "validation_window": {"start": "2025-01-01", "end": "2025-12-31"},
                        "live_boundary_allowed": False,
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "generated today"):
                validate_batch12_validation_preflight_packet(path)


if __name__ == "__main__":
    unittest.main()
