import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.batch12_oos_validation import (
    _row_from_result,
    build_batch12_oos_case_specs,
    run_batch12_oos_validation,
    validate_batch12_oos_contract,
)


class Batch12OosValidationTests(unittest.TestCase):
    def test_contract_blocks_uncleared_preflight_or_final_holdout_touch(self):
        handoff = _handoff()
        preflight = _preflight(status="blocked")

        with self.assertRaisesRegex(ValueError, "preflight is not cleared"):
            validate_batch12_oos_contract(handoff, preflight)

        with self.assertRaisesRegex(ValueError, "final holdout"):
            validate_batch12_oos_contract(handoff, _preflight(), final_holdout_touched=True)

    def test_case_specs_lock_frozen_candidates_and_add_every2_every3_controls(self):
        cases = build_batch12_oos_case_specs(_handoff())

        frozen = [case for case in cases if case["role"] == "frozen_candidate"]
        diagnostics = [case for case in cases if case["role"] == "diagnostic_control"]
        self.assertEqual([case["case_id"] for case in frozen], [
            "rankic_neg1_downside_range_blend_hold20_top50_every1_offset0_cost10_prev_month_ret_gt_neg1",
            "rankic_neg1_downside_range_blend_hold20_top50_every1_offset0_cost20_prev_month_ret_gt_neg1",
        ])
        self.assertEqual({case["schedule_interval"] for case in diagnostics}, {2, 3})
        self.assertEqual({case["holding_period"] for case in cases}, {20})
        self.assertEqual({case["top_n"] for case in cases}, {50})

    def test_run_oos_validation_writes_required_metrics_without_2026_exit_dates(self):
        bars = _synthetic_bars(asset_count=65)
        inputs = _synthetic_daily_basic(bars)
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "batch12_oos"
            packet = run_batch12_oos_validation(
                bars=bars,
                daily_basic_inputs=inputs,
                handoff=_handoff(),
                preflight=_preflight(),
                output_dir=output_dir,
            )

            self.assertEqual(packet["status"], "completed")
            self.assertEqual(packet["validation_window"], {"start": "2025-01-01", "end": "2025-12-31"})
            self.assertEqual(packet["feature_window_start"], "2024-10-01")
            self.assertFalse(packet["final_holdout_touched"])
            self.assertGreaterEqual(packet["summary"]["cases"], 2)
            rows = json.loads((output_dir / "batch12_oos_leaderboard.json").read_text(encoding="utf-8"))
            self.assertTrue(rows)
            for field in [
                "total_return",
                "sharpe",
                "win_rate",
                "max_drawdown",
                "cumulative_hypothesis_count",
                "cumulative_bonferroni_alpha",
                "overlap_autocorr_adjusted_sharpe",
                "overlap_newey_west_t_stat_mean",
                "capacity_limited_trades",
                "monthly_positive_rate",
            ]:
                self.assertIn(field, rows[0])
            self.assertEqual(rows[0]["cumulative_hypothesis_count"], 137 + packet["summary"]["cases"])
            self.assertAlmostEqual(rows[0]["cumulative_bonferroni_alpha"], 0.05 / (137 + packet["summary"]["cases"]))
            trades = pd.read_csv(output_dir / rows[0]["case_id"] / "trades.csv")
            self.assertLessEqual(pd.to_datetime(trades["exit_date"]).max(), pd.Timestamp("2025-12-31"))

    def test_negative_tail_rank_ic_blocks_research_lead_and_paper_ready_even_when_p_value_is_small(self):
        spec = {
            "case_id": "candidate",
            "role": "frozen_candidate",
            "factor_name": "rankic_neg1_downside_range_blend",
            "schedule_interval": 1,
            "schedule_offset": 0,
            "holding_period": 20,
            "top_n": 50,
            "cost_bps": 10.0,
            "cumulative_hypothesis_count": 149,
            "cumulative_bonferroni_alpha": 0.00033557046979865775,
        }
        result = {
            "metrics": {
                "total_return": 0.2,
                "annualized_return": 0.2,
                "sharpe": 1.5,
                "win_rate": 0.6,
                "max_drawdown": -0.03,
                "capacity_limited_trades": 0,
                "overlap_autocorr_adjusted_sharpe": 0.8,
            },
            "factor_summary": {
                "mean_rank_ic": 0.05,
                "tail_mean_rank_ic": -0.04,
                "rank_ic_p_value": 0.0001,
                "tail_rank_ic_p_value": 0.0001,
            },
            "benchmark_metrics": {"relative_return": 0.1},
            "monthly_positive_rate": 0.75,
            "artifact_rows": {"scheduled_factors": 100, "signal_dates": 40, "trades": 200},
        }

        row = _row_from_result(spec, result)

        self.assertFalse(row["research_lead"])
        self.assertFalse(row["paper_ready"])

    def test_extreme_trade_return_blocks_research_lead_and_paper_ready(self):
        spec = {
            "case_id": "candidate",
            "role": "frozen_candidate",
            "factor_name": "rankic_neg1_downside_range_blend",
            "schedule_interval": 1,
            "schedule_offset": 0,
            "holding_period": 20,
            "top_n": 50,
            "cost_bps": 10.0,
            "cumulative_hypothesis_count": 149,
            "cumulative_bonferroni_alpha": 0.00033557046979865775,
        }
        result = {
            "metrics": {
                "total_return": 0.2,
                "annualized_return": 0.2,
                "sharpe": 1.5,
                "win_rate": 0.6,
                "max_drawdown": -0.03,
                "capacity_limited_trades": 0,
                "overlap_autocorr_adjusted_sharpe": 0.8,
                "max_trade_gross_return": 6.0,
            },
            "factor_summary": {
                "mean_rank_ic": 0.05,
                "tail_mean_rank_ic": 0.04,
                "rank_ic_p_value": 0.0001,
                "tail_rank_ic_p_value": 0.0001,
            },
            "benchmark_metrics": {"relative_return": 0.1},
            "monthly_positive_rate": 0.75,
            "artifact_rows": {"scheduled_factors": 100, "signal_dates": 40, "trades": 200},
        }

        row = _row_from_result(spec, result)

        self.assertTrue(row["extreme_trade_return_flag"])
        self.assertFalse(row["research_lead"])
        self.assertFalse(row["paper_ready"])


def _handoff() -> dict:
    return {
        "stage": "cn_stock_batch12_validation_handoff",
        "market": "CN",
        "asset_type": "stock",
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
                "previous_month_return_threshold": -0.01,
            },
            {
                "case_id": "rankic_neg1_downside_range_blend_hold20_top50_every1_offset0_cost20_prev_month_ret_gt_neg1",
                "cost_bps": 20,
                "schedule_interval": 1,
                "schedule_offset": 0,
                "holding_period": 20,
                "top_n": 50,
                "previous_month_return_threshold": -0.01,
            },
        ],
        "diagnostic_controls": [
            {"case_family": "daily_vs_every2_control", "schedule_interval": 2, "role": "diagnostic_only"},
            {"case_family": "daily_vs_every3_control", "schedule_interval": 3, "role": "diagnostic_only"},
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


def _preflight(*, status: str = "cleared") -> dict:
    return {
        "status": status,
        "decision": {"validation_preflight_cleared": status == "cleared", "blockers": [] if status == "cleared" else ["x"]},
        "validation_window": {"start": "2025-01-01", "end": "2025-12-31"},
        "final_holdout_allowed": False,
        "live_boundary_allowed": False,
        "frozen_candidates": [{"case_id": "a"}, {"case_id": "b"}],
    }


def _synthetic_bars(*, asset_count: int) -> pd.DataFrame:
    dates = pd.date_range("2024-10-01", "2025-12-31", freq="B")
    rows = []
    for asset_index in range(asset_count):
        asset_id = f"CN_XSHG_{asset_index:06d}"
        for day_index, date in enumerate(dates):
            seasonal = ((day_index + asset_index) % 11 - 5) * 0.003
            price = 10 + asset_index * 0.05 + day_index * (0.0005 + asset_index * 0.00001) + seasonal
            rows.append(
                {
                    "date": date.date(),
                    "asset_id": asset_id,
                    "market": "CN",
                    "amount": 80_000_000 + asset_index * 1_000_000,
                    "adj_close": price,
                    "high": price * 1.01,
                    "low": price * 0.99,
                    "volume": 1_000_000 + asset_index * 10_000,
                }
            )
    return pd.DataFrame(rows)


def _synthetic_daily_basic(bars: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for row in bars.itertuples(index=False):
        asset_number = int(str(row.asset_id).split("_")[-1])
        rows.append(
            {
                "date": row.date,
                "asset_id": row.asset_id,
                "market": row.market,
                "turnover_rate": 0.5 + (asset_number % 30) * 0.03,
                "turnover_rate_f": 0.6 + (asset_number % 30) * 0.03,
                "volume_ratio": 0.7 + (asset_number % 20) * 0.02,
                "pe_ttm": 6.0 + (asset_number % 25) * 0.5,
                "pb": 0.7 + (asset_number % 20) * 0.08,
                "dv_ttm": 1.0 + (asset_number % 6) * 0.2,
                "total_mv": 2_000_000_000 + asset_number * 30_000_000,
                "circ_mv": 1_500_000_000 + asset_number * 25_000_000,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
