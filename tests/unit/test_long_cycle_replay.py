import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.long_cycle_replay import (
    build_candidate_registry,
    build_long_cycle_coverage,
    build_long_cycle_coverage_from_manifest,
    build_long_cycle_replay_pack,
    build_long_cycle_replay_pack_from_coverage,
    write_long_cycle_replay_pack,
)


class LongCycleReplayTests(unittest.TestCase):
    def test_registry_deduplicates_candidates_and_preserves_parameters(self):
        rows = [
            {
                "case_id": "case_a",
                "market": "CN",
                "factor_name": "factor_x",
                "top_n": 50,
                "cost_bps": 10,
                "forward_horizon": 20,
                "source_report": "report_a",
            },
            {
                "case_id": "case_a",
                "market": "CN",
                "factor_name": "factor_x",
                "top_n": 50,
                "cost_bps": 20,
                "forward_horizon": 20,
                "source_report": "report_b",
            },
        ]

        registry = build_candidate_registry(rows)

        self.assertEqual(len(registry), 1)
        self.assertEqual(registry[0]["case_id"], "case_a")
        self.assertEqual(registry[0]["market"], "CN")
        self.assertEqual(registry[0]["frozen_parameters"]["top_n"], 50)
        self.assertEqual(registry[0]["source_reports"], ["report_a", "report_b"])

    def test_coverage_blocks_when_available_history_starts_after_required_cycle(self):
        bars = pd.DataFrame(
            {
                "date": ["2023-07-03", "2024-01-02"],
                "asset_id": ["CN_A", "CN_B"],
                "market": ["CN", "CN"],
                "adj_close": [10.0, 11.0],
            }
        )

        coverage = build_long_cycle_coverage(bars, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "insufficient")
        self.assertIn("history_starts_after_required_cycle_start", coverage["blockers"])
        self.assertEqual(coverage["date_start"], "2023-07-03")

    def test_coverage_can_be_built_from_data_manifest_summary(self):
        manifest = {
            "summary": {
                "date_start": "2023-07-03",
                "date_end": "2026-06-15",
                "bar_rows": 8286202,
                "bar_asset_ids": 5634,
            }
        }

        coverage = build_long_cycle_coverage_from_manifest(manifest, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "insufficient")
        self.assertEqual(coverage["bar_rows"], 8286202)
        self.assertEqual(coverage["asset_ids"], 5634)
        self.assertIn("history_starts_after_required_cycle_start", coverage["blockers"])

    def test_coverage_blocks_discontinuous_or_thin_years(self):
        bars = pd.DataFrame(
            {
                "date": [
                    "2015-01-05",
                    "2015-01-06",
                    "2023-07-03",
                    "2024-01-02",
                    "2025-01-02",
                    "2026-06-15",
                ],
                "asset_id": ["CN_A"] * 6,
                "market": ["CN"] * 6,
                "adj_close": [10.0, 10.1, 11.0, 12.0, 13.0, 14.0],
            }
        )

        coverage = build_long_cycle_coverage(bars, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "insufficient")
        self.assertIn("missing_required_years", coverage["blockers"])
        self.assertIn("thin_required_years", coverage["blockers"])
        self.assertEqual(coverage["missing_years"], [2016, 2017, 2018, 2019, 2020, 2021, 2022])

    def test_manifest_coverage_blocks_missing_years_even_when_start_date_is_old(self):
        manifest = {
            "summary": {
                "date_start": "2015-01-05",
                "date_end": "2026-06-15",
                "bar_rows": 1200000,
                "bar_asset_ids": 5634,
                "bar_trade_dates_by_year": {
                    "2015": 20,
                    "2023": 120,
                    "2024": 242,
                    "2025": 242,
                    "2026": 110,
                },
            }
        }

        coverage = build_long_cycle_coverage_from_manifest(manifest, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "insufficient")
        self.assertIn("missing_required_years", coverage["blockers"])
        self.assertIn("thin_required_years", coverage["blockers"])
        self.assertEqual(coverage["missing_years"], [2016, 2017, 2018, 2019, 2020, 2021, 2022])

    def test_manifest_coverage_accepts_continuous_full_year_history(self):
        manifest = {
            "summary": {
                "date_start": "2015-01-05",
                "date_end": "2026-06-15",
                "bar_rows": 8000000,
                "bar_asset_ids": 5634,
                "bar_trade_dates_by_year": {str(year): 230 for year in range(2015, 2026)} | {"2026": 110},
            }
        }

        coverage = build_long_cycle_coverage_from_manifest(manifest, market="CN", required_start="2015-01-01")

        self.assertEqual(coverage["status"], "sufficient")
        self.assertEqual(coverage["blockers"], [])

    def test_replay_pack_marks_candidates_research_only_when_coverage_is_short(self):
        bars = pd.DataFrame(
            {
                "date": ["2023-07-03", "2024-01-02"],
                "asset_id": ["CN_A", "CN_B"],
                "market": ["CN", "CN"],
                "adj_close": [10.0, 11.0],
            }
        )
        candidates = [{"case_id": "case_a", "market": "CN", "factor_name": "factor_x", "sharpe": 4.2}]

        pack = build_long_cycle_replay_pack(candidates, bars, market="CN", required_start="2015-01-01")

        self.assertEqual(pack["stage"], "long_cycle_factor_replay")
        self.assertEqual(pack["coverage"]["status"], "insufficient")
        self.assertEqual(pack["summary"]["candidates"], 1)
        self.assertEqual(pack["candidate_decisions"][0]["decision_status"], "research_lead")
        self.assertIn("long_cycle_coverage_insufficient", pack["candidate_decisions"][0]["reasons"])
        self.assertIn("high_sharpe_overfit_warning", pack["candidate_decisions"][0]["reasons"])

    def test_replay_pack_audits_bias_cost_capacity_overlap_and_split_fields(self):
        coverage = {
            "status": "sufficient",
            "market": "CN",
            "required_start": "2015-01-01",
            "date_start": "2015-01-05",
            "date_end": "2025-12-31",
            "blockers": [],
        }
        candidates = [
            {
                "case_id": "clean_case",
                "market": "CN",
                "factor_name": "factor_x",
                "sharpe": 0.8,
                "cost_bps": 10,
                "execution_lag": 1,
                "max_participation_rate": 0.01,
                "overlap_autocorr_adjusted_sharpe": 0.7,
                "train_start_date": "2016-01-01",
                "test_start_date": "2017-01-01",
                "test_end_date": "2017-03-31",
            },
            {
                "case_id": "biased_case",
                "market": "CN",
                "factor_name": "factor_y",
                "sharpe": 1.2,
                "cost_bps": 0,
                "execution_lag": 0,
                "max_participation_rate": 0.08,
                "train_start_date": "2017-01-01",
                "test_start_date": "2016-12-01",
            },
        ]

        pack = build_long_cycle_replay_pack_from_coverage(
            candidates,
            coverage,
            market="CN",
            required_start="2015-01-01",
        )

        by_case = {row["case_id"]: row for row in pack["candidate_decisions"]}
        self.assertEqual(by_case["clean_case"]["lookahead_audit_status"], "pass")
        self.assertEqual(by_case["clean_case"]["cost_capacity_audit_status"], "pass")
        self.assertEqual(by_case["clean_case"]["overlap_audit_status"], "pass")
        self.assertEqual(by_case["clean_case"]["strict_split_status"], "pass")
        self.assertEqual(by_case["clean_case"]["overfit_audit_status"], "pass")

        biased = by_case["biased_case"]
        self.assertEqual(biased["decision_status"], "research_lead")
        self.assertEqual(biased["lookahead_audit_status"], "block")
        self.assertEqual(biased["cost_capacity_audit_status"], "block")
        self.assertEqual(biased["overlap_audit_status"], "warning")
        self.assertEqual(biased["strict_split_status"], "block")
        self.assertIn("same_day_execution_lag", biased["reasons"])
        self.assertIn("missing_positive_transaction_cost", biased["reasons"])
        self.assertIn("capacity_participation_too_high", biased["reasons"])
        self.assertIn("overlap_adjusted_sharpe_missing", biased["reasons"])
        self.assertIn("test_starts_before_train_end", biased["reasons"])

    def test_candidate_decisions_carry_source_performance_metrics_for_audit(self):
        coverage = {
            "status": "sufficient",
            "market": "CN",
            "required_start": "2015-01-01",
            "date_start": "2015-01-05",
            "date_end": "2025-12-31",
            "blockers": [],
        }
        candidates = [
            {
                "case_id": "metric_case",
                "market": "CN",
                "factor_name": "factor_metric",
                "source_kind": "prototype_leaderboard",
                "source_report": "report.csv",
                "mean_rank_ic": 0.041,
                "tail_mean_rank_ic": 0.018,
                "total_return": 0.234,
                "relative_return": 0.051,
                "sharpe": 1.23,
                "long_short_positive_rate": 0.57,
                "max_drawdown": -0.19,
                "turnover": 1.8,
                "trades": 120,
                "cost_bps": 10,
                "execution_lag": 1,
                "max_participation_rate": 0.006,
                "overlap_autocorr_adjusted_sharpe": 0.94,
                "train_end_date": "2019-12-31",
                "test_start_date": "2020-01-02",
            },
            {
                "case_id": "missing_metric_case",
                "market": "CN",
                "factor_name": "factor_missing_metric",
            },
        ]

        pack = build_long_cycle_replay_pack_from_coverage(
            candidates,
            coverage,
            market="CN",
            required_start="2015-01-01",
        )

        by_case = {row["case_id"]: row for row in pack["candidate_decisions"]}
        decision = by_case["metric_case"]
        self.assertEqual(decision["source_kind"], "prototype_leaderboard")
        self.assertEqual(decision["source_report"], "report.csv")
        self.assertAlmostEqual(decision["mean_rank_ic"], 0.041)
        self.assertAlmostEqual(decision["tail_mean_rank_ic"], 0.018)
        self.assertAlmostEqual(decision["total_return"], 0.234)
        self.assertAlmostEqual(decision["relative_return"], 0.051)
        self.assertAlmostEqual(decision["sharpe"], 1.23)
        self.assertAlmostEqual(decision["long_short_positive_rate"], 0.57)
        self.assertAlmostEqual(decision["max_drawdown"], -0.19)
        self.assertAlmostEqual(decision["turnover"], 1.8)
        self.assertEqual(decision["trades"], 120)
        self.assertEqual(decision["cost_bps"], 10)
        self.assertEqual(decision["execution_lag"], 1)
        self.assertAlmostEqual(decision["max_participation_rate"], 0.006)
        self.assertAlmostEqual(decision["overlap_autocorr_adjusted_sharpe"], 0.94)
        self.assertEqual(decision["train_end_date"], "2019-12-31")
        self.assertEqual(decision["test_start_date"], "2020-01-02")
        self.assertIsNone(by_case["missing_metric_case"]["sharpe"])
        self.assertIsNone(by_case["missing_metric_case"]["total_return"])

    def test_replay_pack_summary_counts_reasons_and_audit_statuses(self):
        coverage = {
            "status": "sufficient",
            "market": "CN",
            "required_start": "2015-01-01",
            "date_start": "2015-01-05",
            "date_end": "2025-12-31",
            "blockers": [],
        }
        candidates = [
            {
                "case_id": "clean_case",
                "market": "CN",
                "factor_name": "factor_clean",
                "sharpe": 0.8,
                "total_return": 0.2,
                "cost_bps": 10,
                "execution_lag": 1,
                "max_participation_rate": 0.006,
                "overlap_autocorr_adjusted_sharpe": 0.7,
                "train_end_date": "2019-12-31",
                "test_start_date": "2020-01-02",
            },
            {
                "case_id": "bad_case",
                "market": "CN",
                "factor_name": "factor_bad",
                "sharpe": 4.2,
                "total_return": -0.1,
                "cost_bps": 0,
                "execution_lag": 0,
                "max_participation_rate": 0.03,
                "train_end_date": "2020-01-02",
                "test_start_date": "2019-12-31",
            },
        ]

        pack = build_long_cycle_replay_pack_from_coverage(
            candidates,
            coverage,
            market="CN",
            required_start="2015-01-01",
        )

        summary = pack["summary"]
        self.assertEqual(summary["reason_counts"]["negative_return"], 1)
        self.assertEqual(summary["reason_counts"]["same_day_execution_lag"], 1)
        self.assertEqual(summary["reason_counts"]["capacity_participation_too_high"], 1)
        self.assertEqual(summary["audit_status_counts"]["lookahead_audit_status"]["pass"], 1)
        self.assertEqual(summary["audit_status_counts"]["lookahead_audit_status"]["block"], 1)
        self.assertEqual(summary["audit_status_counts"]["strict_split_status"]["pass"], 1)
        self.assertEqual(summary["audit_status_counts"]["strict_split_status"]["block"], 1)
        markdown = pack["markdown"]
        self.assertIn("## Decision Summary", markdown)
        self.assertIn("## Top Rejection Reasons", markdown)
        self.assertIn("negative_return", markdown)

    def test_replay_pack_summary_counts_missing_source_audit_fields(self):
        coverage = {
            "status": "sufficient",
            "market": "CN",
            "required_start": "2015-01-01",
            "date_start": "2015-01-05",
            "date_end": "2025-12-31",
            "blockers": [],
        }
        candidates = [
            {
                "case_id": "complete_case",
                "market": "CN",
                "factor_name": "factor_complete",
                "source_kind": "leaderboard",
                "source_report": "report.csv",
                "sharpe": 1.1,
                "total_return": 0.2,
                "cost_bps": 10,
                "execution_lag": 1,
                "max_participation_rate": 0.006,
                "overlap_autocorr_adjusted_sharpe": 0.7,
                "train_end_date": "2019-12-31",
                "test_start_date": "2020-01-02",
            },
            {
                "case_id": "missing_case",
                "market": "CN",
                "factor_name": "factor_missing",
                "sharpe": 0.5,
            },
        ]

        pack = build_long_cycle_replay_pack_from_coverage(
            candidates,
            coverage,
            market="CN",
            required_start="2015-01-01",
        )

        missing_counts = pack["summary"]["source_audit_missing_counts"]
        self.assertEqual(missing_counts["source_kind"], 1)
        self.assertEqual(missing_counts["source_report"], 1)
        self.assertEqual(missing_counts["total_return"], 1)
        self.assertEqual(missing_counts["execution_lag"], 1)
        self.assertEqual(missing_counts["overlap_autocorr_adjusted_sharpe"], 1)
        self.assertEqual(missing_counts["test_start_date"], 1)
        markdown = pack["markdown"]
        self.assertIn("## Source Audit Missing Counts", markdown)
        self.assertIn("execution_lag", markdown)

    def test_replay_pack_accepts_upstream_strict_split_audit_evidence(self):
        coverage = {
            "status": "sufficient",
            "market": "CN",
            "required_start": "2015-01-01",
            "date_start": "2015-01-05",
            "date_end": "2025-12-31",
            "blockers": [],
        }
        candidates = [
            {
                "case_id": "audited_split_case",
                "market": "CN",
                "factor_name": "factor_split",
                "sharpe": 0.9,
                "total_return": 0.2,
                "cost_bps": 10,
                "execution_lag": 1,
                "max_participation_rate": 0.006,
                "overlap_autocorr_adjusted_sharpe": 0.7,
                "strict_split_status": "pass",
                "strict_split_violations": 0,
                "strict_split_folds": 3,
            }
        ]

        pack = build_long_cycle_replay_pack_from_coverage(
            candidates,
            coverage,
            market="CN",
            required_start="2015-01-01",
        )

        decision = pack["candidate_decisions"][0]
        self.assertEqual(decision["strict_split_status"], "pass")
        self.assertNotIn("strict_split_dates_missing", decision["reasons"])

    def test_candidate_decisions_accept_walk_forward_test_metric_aliases(self):
        coverage = {
            "status": "sufficient",
            "market": "CN",
            "required_start": "2015-01-01",
            "date_start": "2015-01-05",
            "date_end": "2025-12-31",
            "blockers": [],
        }
        candidates = [
            {
                "case_id": "walk_forward_metric_case",
                "market": "CN",
                "factor_name": "factor_walk_forward",
                "test_mean_ic": 0.031,
                "test_mean_rank_ic": 0.029,
                "test_tail_mean_ic": 0.014,
                "test_tail_mean_rank_ic": 0.012,
                "test_long_short_mean_return": 0.006,
                "test_long_short_positive_rate": 0.61,
                "test_total_return": 0.27,
                "test_relative_return": 0.08,
                "test_sharpe": 1.42,
                "test_max_drawdown": -0.12,
                "test_turnover": 1.7,
                "test_avg_participation_rate": 0.004,
                "test_max_participation_rate": 0.007,
                "test_capacity_limited_trades": 0,
                "test_trades": 66,
                "cost_bps": 10,
                "execution_lag": 1,
                "test_overlap_autocorr_adjusted_sharpe": 1.05,
                "train_end_date": "2019-12-31",
                "test_start_date": "2020-01-02",
            }
        ]

        pack = build_long_cycle_replay_pack_from_coverage(
            candidates,
            coverage,
            market="CN",
            required_start="2015-01-01",
        )

        decision = pack["candidate_decisions"][0]
        self.assertAlmostEqual(decision["mean_ic"], 0.031)
        self.assertAlmostEqual(decision["mean_rank_ic"], 0.029)
        self.assertAlmostEqual(decision["tail_mean_ic"], 0.014)
        self.assertAlmostEqual(decision["tail_mean_rank_ic"], 0.012)
        self.assertAlmostEqual(decision["long_short_mean_return"], 0.006)
        self.assertAlmostEqual(decision["long_short_positive_rate"], 0.61)
        self.assertAlmostEqual(decision["total_return"], 0.27)
        self.assertAlmostEqual(decision["relative_return"], 0.08)
        self.assertAlmostEqual(decision["sharpe"], 1.42)
        self.assertAlmostEqual(decision["max_drawdown"], -0.12)
        self.assertAlmostEqual(decision["turnover"], 1.7)
        self.assertAlmostEqual(decision["avg_participation_rate"], 0.004)
        self.assertAlmostEqual(decision["max_participation_rate"], 0.007)
        self.assertEqual(decision["capacity_limited_trades"], 0)
        self.assertEqual(decision["trades"], 66)
        missing_counts = pack["summary"]["source_audit_missing_counts"]
        self.assertEqual(missing_counts["sharpe"], 0)
        self.assertEqual(missing_counts["total_return"], 0)
        self.assertEqual(missing_counts["relative_return"], 0)
        self.assertEqual(missing_counts["mean_rank_ic"], 0)
        self.assertEqual(missing_counts["long_short_mean_return"], 0)
        self.assertEqual(missing_counts["long_short_positive_rate"], 0)
        self.assertEqual(missing_counts["turnover"], 0)
        self.assertEqual(missing_counts["trades"], 0)

    def test_replay_pack_requires_actual_same_parameter_full_sample_replay(self):
        coverage = {
            "status": "sufficient",
            "market": "CN",
            "required_start": "2015-01-01",
            "date_start": "2015-01-05",
            "date_end": "2025-12-31",
            "blockers": [],
        }
        candidates = [
            {
                "case_id": "source_only_case",
                "market": "CN",
                "factor_name": "factor_source_only",
                "test_mean_rank_ic": 0.029,
                "test_long_short_mean_return": 0.006,
                "test_long_short_positive_rate": 0.61,
                "test_total_return": 0.27,
                "test_sharpe": 1.42,
                "test_max_drawdown": -0.12,
                "test_turnover": 1.7,
                "test_trades": 66,
                "cost_bps": 10,
                "execution_lag": 1,
                "test_max_participation_rate": 0.007,
                "test_overlap_autocorr_adjusted_sharpe": 1.05,
                "strict_split_status": "pass",
                "strict_split_violations": 0,
                "strict_split_folds": 3,
            },
            {
                "case_id": "full_sample_replayed_case",
                "market": "CN",
                "factor_name": "factor_replayed",
                "same_parameter_full_sample_status": "pass",
                "test_mean_rank_ic": 0.031,
                "test_long_short_mean_return": 0.007,
                "test_long_short_positive_rate": 0.63,
                "test_total_return": 0.31,
                "test_sharpe": 1.55,
                "test_max_drawdown": -0.10,
                "test_turnover": 1.4,
                "test_trades": 80,
                "cost_bps": 10,
                "execution_lag": 1,
                "test_max_participation_rate": 0.006,
                "test_overlap_autocorr_adjusted_sharpe": 0.92,
                "strict_split_status": "pass",
                "strict_split_violations": 0,
                "strict_split_folds": 3,
            },
        ]

        pack = build_long_cycle_replay_pack_from_coverage(
            candidates,
            coverage,
            market="CN",
            required_start="2015-01-01",
        )

        by_case = {row["case_id"]: row for row in pack["candidate_decisions"]}
        source_only = by_case["source_only_case"]
        self.assertEqual(source_only["decision_status"], "research_lead")
        self.assertEqual(source_only["replay_status"], "audit_only")
        self.assertIn("same_parameter_full_sample_replay_missing", source_only["reasons"])

        replayed = by_case["full_sample_replayed_case"]
        self.assertEqual(replayed["decision_status"], "validation_candidate")
        self.assertEqual(replayed["replay_status"], "pass")
        self.assertNotIn("same_parameter_full_sample_replay_missing", replayed["reasons"])

    def test_replay_pack_blocks_validation_when_core_source_metrics_are_missing(self):
        coverage = {
            "status": "sufficient",
            "market": "CN",
            "required_start": "2015-01-01",
            "date_start": "2015-01-05",
            "date_end": "2025-12-31",
            "blockers": [],
        }
        candidates = [
            {
                "case_id": "thin_evidence_case",
                "market": "CN",
                "factor_name": "factor_thin",
                "test_total_return": 0.12,
                "test_sharpe": 0.8,
                "cost_bps": 10,
                "execution_lag": 1,
                "test_max_participation_rate": 0.004,
                "test_overlap_autocorr_adjusted_sharpe": 0.7,
                "strict_split_status": "pass",
                "strict_split_violations": 0,
                "strict_split_folds": 2,
            }
        ]

        pack = build_long_cycle_replay_pack_from_coverage(
            candidates,
            coverage,
            market="CN",
            required_start="2015-01-01",
        )

        decision = pack["candidate_decisions"][0]
        self.assertEqual(decision["decision_status"], "research_lead")
        self.assertEqual(decision["source_evidence_status"], "block")
        self.assertIn("source_performance_evidence_missing", decision["reasons"])

    def test_writer_emits_json_markdown_and_csv_artifacts(self):
        pack = {
            "stage": "long_cycle_factor_replay",
            "summary": {"candidates": 1},
            "coverage": {"status": "insufficient"},
            "candidate_registry": [{"case_id": "case_a"}],
            "candidate_decisions": [{"case_id": "case_a", "decision_status": "research_lead"}],
            "markdown": "# Long-Cycle Factor Replay\n",
        }
        with tempfile.TemporaryDirectory() as tmp:
            write_long_cycle_replay_pack(tmp, pack)

            self.assertTrue((Path(tmp) / "long_cycle_replay_pack.json").exists())
            self.assertTrue((Path(tmp) / "long_cycle_replay_pack.md").exists())
            self.assertTrue((Path(tmp) / "candidate_registry.csv").exists())
            self.assertTrue((Path(tmp) / "candidate_decisions.csv").exists())


if __name__ == "__main__":
    unittest.main()
