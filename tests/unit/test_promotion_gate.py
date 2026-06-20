import tempfile
import unittest
from pathlib import Path

from quant_robot.promotion.gate import PromotionGateConfig, build_promotion_report, load_promotion_gate_config, run_promotion_gate


class PromotionGateTests(unittest.TestCase):
    def test_duplicate_paper_intent_signatures_block_redundant_candidates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first_manifest = _write_paper_manifest_with_intents(
                root,
                case_id="CN_ETF_liquidity_10_top1_cost5_reb5",
                factor_name="liquidity_10",
            )
            duplicate_manifest = _write_paper_manifest_with_intents(
                root,
                case_id="CN_ETF_liquidity_120_top1_cost5_reb5",
                factor_name="liquidity_120",
            )

            report = build_promotion_report(
                walk_forward_rows=[
                    _accepted_walk_forward_row("CN_ETF_liquidity_10_top1_cost5_reb5", "liquidity_10"),
                    _accepted_walk_forward_row("CN_ETF_liquidity_120_top1_cost5_reb5", "liquidity_120"),
                ],
                paper_manifests=[first_manifest, duplicate_manifest],
                config=PromotionGateConfig(min_oos_sharpe=0.5, min_paper_sharpe=0.5),
            )

        by_case = {row["case_id"]: row for row in report["candidates"]}
        primary = by_case["CN_ETF_liquidity_10_top1_cost5_reb5"]
        duplicate = by_case["CN_ETF_liquidity_120_top1_cost5_reb5"]
        self.assertEqual(primary["promotion_status"], "paper_ready")
        self.assertEqual(duplicate["promotion_status"], "blocked")
        self.assertIn("duplicate_signal_candidate", duplicate["blocking_reasons"])
        self.assertEqual(duplicate["duplicate_of"], primary["case_id"])
        self.assertEqual(duplicate["duplicate_similarity"], 1.0)
        self.assertEqual(report["summary"]["duplicates"], 1)

    def test_score_rewards_stronger_paper_sharpe_for_same_research_evidence(self):
        report = build_promotion_report(
            walk_forward_rows=[
                _accepted_walk_forward_row("CN_ETF_momentum_20_top1_cost5_reb5", "momentum_20"),
                _accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60"),
            ],
            paper_manifests=[
                _paper_manifest(
                    case_id="CN_ETF_momentum_20_top1_cost5_reb5",
                    factor_name="momentum_20",
                    sharpe=0.20,
                    total_return=0.20,
                ),
                _paper_manifest(
                    case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                    factor_name="momentum_60",
                    sharpe=0.90,
                    total_return=0.20,
                ),
            ],
            config=PromotionGateConfig(min_oos_sharpe=0.5, min_paper_sharpe=1.0),
        )

        by_case = {row["case_id"]: row for row in report["candidates"]}
        weak = by_case["CN_ETF_momentum_20_top1_cost5_reb5"]
        strong = by_case["CN_ETF_momentum_60_top1_cost5_reb5"]
        self.assertEqual(weak["promotion_status"], "research_only")
        self.assertEqual(strong["promotion_status"], "research_only")
        self.assertGreater(strong["score"], weak["score"])

    def test_paper_drawdown_breach_blocks_accepted_candidate(self):
        report = build_promotion_report(
            walk_forward_rows=[
                {
                    "case_id": "CN_ETF_momentum_20_top2_cost5_reb5",
                    "market": "CN_ETF",
                    "factor_name": "momentum_20",
                    "top_n": 2,
                    "cost_bps": 5,
                    "validation_status": "accepted",
                    "data_mode": "research",
                    "test_trades": 324,
                    "test_sharpe": 0.72,
                    "test_relative_return": 0.08,
                    "test_max_drawdown": -0.12,
                    "stability_score": 0.64,
                }
            ],
            paper_manifest={
                "data_mode": "research",
                "metrics": {
                    "max_equity_drawdown": -0.55,
                    "sharpe": 0.46,
                    "total_return": 1.92,
                },
                "request": {
                    "market": "CN_ETF",
                    "factor_name": "momentum_20",
                    "top_n": 2,
                    "cost_bps": 5,
                    "rebalance_interval": 5,
                },
            },
            config=PromotionGateConfig(max_paper_drawdown=0.25),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("paper_drawdown_above_limit", row["blocking_reasons"])

    def test_strong_candidate_without_ready_provider_stops_at_paper_ready(self):
        report = build_promotion_report(
            walk_forward_rows=[
                {
                    "case_id": "CN_ETF_momentum_60_top1_cost5_reb5",
                    "market": "CN_ETF",
                    "factor_name": "momentum_60",
                    "top_n": 1,
                    "cost_bps": 5,
                    "validation_status": "accepted",
                    "data_mode": "research",
                    "test_trades": 180,
                    "test_sharpe": 0.82,
                    "test_relative_return": 0.06,
                    "test_max_drawdown": -0.10,
                    "stability_score": 0.70,
                }
            ],
            paper_manifest={
                "data_mode": "research",
                "metrics": {
                    "max_equity_drawdown": -0.12,
                    "sharpe": 0.80,
                    "total_return": 0.18,
                },
                "request": {
                    "market": "CN_ETF",
                    "factor_name": "momentum_60",
                    "top_n": 1,
                    "cost_bps": 5,
                    "rebalance_interval": 5,
                },
            },
            provider_status={"providers": {"tushare": {"ready": False}}},
            config=PromotionGateConfig(min_oos_sharpe=0.5, min_paper_sharpe=0.5),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "paper_ready")
        self.assertIn("providers_not_ready_for_live_review", row["warnings"])
        self.assertGreater(row["score"], 0.0)

    def test_promotion_blocks_candidates_without_required_rolling_and_significance_evidence(self):
        report = build_promotion_report(
            walk_forward_rows=[
                {
                    "case_id": "CN_ETF_momentum_60_top1_cost5_reb5",
                    "market": "CN_ETF",
                    "factor_name": "momentum_60",
                    "top_n": 1,
                    "cost_bps": 5,
                    "validation_status": "accepted",
                    "data_mode": "research",
                    "test_trades": 180,
                    "test_sharpe": 0.82,
                    "test_relative_return": 0.06,
                    "test_max_drawdown": -0.10,
                    "stability_score": 0.70,
                    "folds": 1,
                    "accepted_folds": 1,
                    "test_ic_p_value": 0.40,
                    "test_positive_ic_rate": 0.50,
                }
            ],
            paper_manifest={
                "data_mode": "research",
                "metrics": {
                    "max_equity_drawdown": -0.12,
                    "sharpe": 0.80,
                    "total_return": 0.18,
                },
                "request": {
                    "market": "CN_ETF",
                    "factor_name": "momentum_60",
                    "top_n": 1,
                    "rebalance_interval": 5,
                },
            },
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                min_walk_forward_folds=3,
                min_accepted_folds=2,
                max_ic_p_value=0.05,
                min_positive_ic_rate=0.55,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("insufficient_walk_forward_folds", row["blocking_reasons"])
        self.assertIn("insufficient_accepted_folds", row["blocking_reasons"])
        self.assertIn("ic_significance_below_threshold", row["blocking_reasons"])
        self.assertIn("positive_ic_rate_below_threshold", row["blocking_reasons"])

    def test_promotion_blocks_candidate_without_required_factor_source(self):
        walk_forward = _accepted_walk_forward_row("CN_ETF_total_mv_log_top1_cost5_reb5", "total_mv_log")
        walk_forward.update(
            {
                "adjusted_ic_p_value": 0.01,
                "passes_adjusted_ic_p_value": True,
            }
        )

        report = build_promotion_report(
            walk_forward_rows=[walk_forward],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_total_mv_log_top1_cost5_reb5",
                factor_name="total_mv_log",
                sharpe=0.80,
                total_return=0.20,
            ),
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                required_factor_source="tushare_daily_basic",
                max_adjusted_ic_p_value=0.05,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("factor_source_mismatch", row["blocking_reasons"])

    def test_promotion_blocks_candidate_without_adjusted_ic_evidence(self):
        walk_forward = _accepted_walk_forward_row("CN_ETF_total_mv_log_top1_cost5_reb5", "total_mv_log")
        walk_forward.update(
            {
                "factor_source": "tushare_daily_basic",
                "adjusted_ic_p_value": 0.20,
                "passes_adjusted_ic_p_value": False,
            }
        )

        report = build_promotion_report(
            walk_forward_rows=[walk_forward],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_total_mv_log_top1_cost5_reb5",
                factor_name="total_mv_log",
                sharpe=0.80,
                total_return=0.20,
            ),
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                required_factor_source="tushare_daily_basic",
                max_adjusted_ic_p_value=0.05,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("adjusted_ic_p_value_above_threshold", row["blocking_reasons"])
        self.assertIn("adjusted_ic_significance_not_passed", row["blocking_reasons"])

    def test_promotion_blocks_candidate_without_tail_ic_evidence_when_required(self):
        walk_forward = _accepted_walk_forward_row("CN_ETF_total_mv_log_top1_cost5_reb5", "total_mv_log")
        walk_forward.update(
            {
                "test_tail_ic_p_value": 0.40,
                "test_tail_significance_status": "not_significant",
            }
        )

        report = build_promotion_report(
            walk_forward_rows=[walk_forward],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_total_mv_log_top1_cost5_reb5",
                factor_name="total_mv_log",
                sharpe=0.80,
                total_return=0.20,
            ),
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                max_tail_ic_p_value=0.05,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("tail_ic_significance_below_threshold", row["blocking_reasons"])
        self.assertEqual(row["walk_forward"]["test_tail_significance_status"], "not_significant")

    def test_promotion_blocks_implausibly_high_oos_sharpe_when_configured(self):
        walk_forward = _accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")
        walk_forward["test_sharpe"] = 3.5

        report = build_promotion_report(
            walk_forward_rows=[walk_forward],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                max_oos_sharpe_for_promotion=3.0,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("oos_sharpe_overfit_flag", row["blocking_reasons"])

    def test_promotion_blocks_candidate_without_required_market_regime_coverage(self):
        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            market_regime_coverage={
                "status": "insufficient",
                "summary": {"covered_regimes": 1},
                "decision": {"market_regime_coverage_cleared": False, "blockers": ["market_regimes_below_minimum"]},
            },
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                require_market_regime_coverage=True,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("market_regime_coverage_not_sufficient", row["blocking_reasons"])
        self.assertIn("market_regimes_below_minimum", row["blocking_reasons"])

    def test_promotion_blocks_candidate_with_required_progress_audit_case_blockers(self):
        case_id = "CN_ETF_momentum_60_top1_cost5_reb5"
        progress_audit = {
            "summary": {
                "is_complete": True,
                "claim_blockers": ["requires_formal_promotion_gate"],
                "completed_folds": 12,
                "expected_folds": 12,
                "no_trade_rows": 2,
                "regime_all_blocked_no_trade_rows": 2,
                "robust_case_candidates": 0,
            },
            "case_summary": [
                {
                    "case_id": case_id,
                    "blockers": ["case_no_trades_present", "case_regime_all_blocked_no_trades"],
                    "folds": 12,
                    "passing_rows": 3,
                    "required_passing_rows": 4,
                    "no_trade_rows": 2,
                    "regime_all_blocked_no_trade_rows": 2,
                    "robust_progress_candidate": False,
                }
            ],
        }

        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row(case_id, "momentum_60")],
            paper_manifest=_paper_manifest(
                case_id=case_id,
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            walk_forward_progress_audit=progress_audit,
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                require_walk_forward_progress_audit=True,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("walk_forward_progress_case_no_trades_present", row["blocking_reasons"])
        self.assertIn("walk_forward_progress_case_regime_all_blocked_no_trades", row["blocking_reasons"])
        self.assertNotIn("walk_forward_progress_requires_formal_promotion_gate", row["blocking_reasons"])
        self.assertEqual(row["walk_forward_progress"]["case"]["no_trade_rows"], 2)

    def test_run_promotion_gate_treats_missing_required_progress_audit_as_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaderboard = root / "walk_forward.csv"
            leaderboard.write_text(
                "case_id,market,factor_name,top_n,cost_bps,validation_status,data_mode,test_trades,test_sharpe,test_relative_return,test_max_drawdown,stability_score\n"
                "CN_ETF_momentum_60_top1_cost5_reb5,CN_ETF,momentum_60,1,5,accepted,research,80,0.8,0.06,-0.12,0.7\n",
                encoding="utf-8",
            )

            report = run_promotion_gate(
                PromotionGateConfig(
                    walk_forward_leaderboard=leaderboard,
                    walk_forward_progress_audit=root / "missing_progress_audit.json",
                    require_walk_forward_progress_audit=True,
                    min_oos_sharpe=0.5,
                    min_paper_sharpe=0.5,
                )
            )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("walk_forward_progress_audit_missing", row["blocking_reasons"])

    def test_promotion_blocks_candidate_without_required_long_cycle_replay(self):
        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                require_long_cycle_replay=True,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("long_cycle_replay_missing", row["blocking_reasons"])

    def test_promotion_blocks_candidate_with_failed_long_cycle_replay_audits(self):
        replay_pack = {
            "stage": "long_cycle_factor_replay",
            "coverage": {"status": "sufficient"},
            "candidate_decisions": [
                {
                    "case_id": "CN_ETF_momentum_60_top1_cost5_reb5",
                    "decision_status": "research_lead",
                    "reasons": ["same_day_execution_lag", "capacity_participation_too_high"],
                    "long_cycle_coverage_status": "sufficient",
                    "lookahead_audit_status": "block",
                    "overfit_audit_status": "pass",
                    "cost_capacity_audit_status": "block",
                    "overlap_audit_status": "pass",
                    "strict_split_status": "pass",
                }
            ],
        }

        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            long_cycle_replay=replay_pack,
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                require_long_cycle_replay=True,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("long_cycle_replay_not_validation_candidate", row["blocking_reasons"])
        self.assertIn("long_cycle_lookahead_audit_block", row["blocking_reasons"])
        self.assertIn("long_cycle_cost_capacity_audit_block", row["blocking_reasons"])
        self.assertIn("long_cycle_reason:same_day_execution_lag", row["warnings"])
        self.assertEqual(row["long_cycle_replay"]["decision_status"], "research_lead")

    def test_promotion_blocks_candidate_with_missing_long_cycle_source_evidence(self):
        replay_pack = {
            "stage": "long_cycle_factor_replay",
            "coverage": {"status": "sufficient"},
            "candidate_decisions": [
                {
                    "case_id": "CN_ETF_momentum_60_top1_cost5_reb5",
                    "decision_status": "validation_candidate",
                    "reasons": ["source_performance_evidence_missing"],
                    "long_cycle_coverage_status": "sufficient",
                    "lookahead_audit_status": "pass",
                    "overfit_audit_status": "pass",
                    "cost_capacity_audit_status": "pass",
                    "overlap_audit_status": "pass",
                    "strict_split_status": "pass",
                    "source_evidence_status": "block",
                }
            ],
        }

        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            long_cycle_replay=replay_pack,
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                require_long_cycle_replay=True,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("long_cycle_source_evidence_block", row["blocking_reasons"])
        self.assertIn("long_cycle_reason:source_performance_evidence_missing", row["warnings"])
        self.assertEqual(row["long_cycle_replay"]["source_evidence_status"], "block")

    def test_promotion_blocks_candidate_without_long_cycle_source_evidence_status(self):
        replay_pack = {
            "stage": "long_cycle_factor_replay",
            "coverage": {"status": "sufficient"},
            "candidate_decisions": [
                {
                    "case_id": "CN_ETF_momentum_60_top1_cost5_reb5",
                    "decision_status": "validation_candidate",
                    "reasons": [],
                    "long_cycle_coverage_status": "sufficient",
                    "lookahead_audit_status": "pass",
                    "overfit_audit_status": "pass",
                    "cost_capacity_audit_status": "pass",
                    "overlap_audit_status": "pass",
                    "strict_split_status": "pass",
                }
            ],
        }

        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            long_cycle_replay=replay_pack,
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                require_long_cycle_replay=True,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("long_cycle_source_evidence_missing", row["blocking_reasons"])
        self.assertIsNone(row["long_cycle_replay"]["source_evidence_status"])

    def test_promotion_blocks_audit_only_long_cycle_replay(self):
        replay_pack = {
            "stage": "long_cycle_factor_replay",
            "coverage": {"status": "sufficient"},
            "candidate_decisions": [
                {
                    "case_id": "CN_ETF_momentum_60_top1_cost5_reb5",
                    "decision_status": "validation_candidate",
                    "replay_status": "audit_only",
                    "reasons": [],
                    "long_cycle_coverage_status": "sufficient",
                    "lookahead_audit_status": "pass",
                    "overfit_audit_status": "pass",
                    "cost_capacity_audit_status": "pass",
                    "overlap_audit_status": "pass",
                    "strict_split_status": "pass",
                    "source_evidence_status": "pass",
                }
            ],
        }

        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            long_cycle_replay=replay_pack,
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                require_long_cycle_replay=True,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("long_cycle_replay_status_audit_only", row["blocking_reasons"])
        self.assertEqual(row["long_cycle_replay"]["replay_status"], "audit_only")

    def test_promotion_accepts_candidate_with_required_long_cycle_replay_audits(self):
        replay_pack = {
            "stage": "long_cycle_factor_replay",
            "coverage": {"status": "sufficient"},
            "candidate_decisions": [
                {
                    "case_id": "CN_ETF_momentum_60_top1_cost5_reb5",
                    "decision_status": "validation_candidate",
                    "replay_status": "pass",
                    "reasons": [],
                    "long_cycle_coverage_status": "sufficient",
                    "lookahead_audit_status": "pass",
                    "overfit_audit_status": "pass",
                    "cost_capacity_audit_status": "pass",
                    "overlap_audit_status": "pass",
                    "strict_split_status": "pass",
                    "source_evidence_status": "pass",
                }
            ],
        }

        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            long_cycle_replay=replay_pack,
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                require_long_cycle_replay=True,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "paper_ready")
        self.assertEqual(row["long_cycle_replay"]["decision_status"], "validation_candidate")
        self.assertEqual(row["long_cycle_replay"]["lookahead_audit_status"], "pass")

    def test_promotion_blocks_candidate_accepted_by_only_one_regime_lookback_when_required(self):
        accepted = _accepted_walk_forward_row("CN_momentum_60_top1_cost5_reb1_regime150", "momentum_60")
        accepted["regime_lookback"] = 150
        rejected_other_regime = _accepted_walk_forward_row("CN_momentum_60_top1_cost5_reb1_regime180", "momentum_60")
        rejected_other_regime["regime_lookback"] = 180
        rejected_other_regime["validation_status"] = "rejected"

        report = build_promotion_report(
            walk_forward_rows=[accepted, rejected_other_regime],
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                min_distinct_regime_lookbacks_for_family=2,
            ),
        )

        by_case = {row["case_id"]: row for row in report["candidates"]}
        self.assertEqual(by_case["CN_momentum_60_top1_cost5_reb1_regime150"]["promotion_status"], "blocked")
        self.assertIn(
            "insufficient_distinct_regime_lookbacks",
            by_case["CN_momentum_60_top1_cost5_reb1_regime150"]["blocking_reasons"],
        )

    def test_run_promotion_gate_treats_missing_required_market_regime_coverage_as_blocker(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            leaderboard = root / "walk_forward.csv"
            leaderboard.write_text(
                "case_id,market,factor_name,top_n,cost_bps,validation_status,data_mode,test_trades,test_sharpe,test_relative_return,test_max_drawdown,stability_score\n"
                "CN_ETF_momentum_60_top1_cost5_reb5,CN_ETF,momentum_60,1,5,accepted,research,80,0.8,0.06,-0.12,0.7\n",
                encoding="utf-8",
            )

            report = run_promotion_gate(
                PromotionGateConfig(
                    walk_forward_leaderboard=leaderboard,
                    market_regime_coverage=root / "missing_regime_pack.json",
                    require_market_regime_coverage=True,
                    min_oos_sharpe=0.5,
                    min_paper_sharpe=0.5,
                )
            )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("market_regime_coverage_missing", row["blocking_reasons"])

    def test_promotion_gate_reads_gap_audit_summary_quality_metrics(self):
        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")],
            quality_report={
                "stage": "phase_3_1_data_quality_gap_audit",
                "summary": {
                    "duplicate_bars": 1,
                    "missing_date_rows": 4,
                    "zero_volume_rows": 2,
                },
            },
            config=PromotionGateConfig(min_oos_sharpe=0.5, min_paper_sharpe=0.5),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("duplicate_bars_present", row["blocking_reasons"])
        self.assertIn("missing_dates_present", row["warnings"])
        self.assertIn("zero_volume_rows_present", row["warnings"])

    def test_promotion_accepts_candidate_with_factor_source_and_adjusted_ic_evidence(self):
        walk_forward = _accepted_walk_forward_row("CN_ETF_total_mv_log_top1_cost5_reb5", "total_mv_log")
        walk_forward.update(
            {
                "factor_source": "tushare_daily_basic",
                "adjusted_ic_p_value": 0.01,
                "passes_adjusted_ic_p_value": True,
                "hypothesis_count": 9,
            }
        )

        report = build_promotion_report(
            walk_forward_rows=[walk_forward],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_total_mv_log_top1_cost5_reb5",
                factor_name="total_mv_log",
                sharpe=0.80,
                total_return=0.20,
            ),
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                required_factor_source="tushare_daily_basic",
                max_adjusted_ic_p_value=0.05,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "paper_ready")
        self.assertEqual(row["walk_forward"]["factor_source"], "tushare_daily_basic")
        self.assertEqual(row["walk_forward"]["hypothesis_count"], 9)
        self.assertAlmostEqual(row["walk_forward"]["adjusted_ic_p_value"], 0.01)

    def test_load_promotion_gate_config_reads_factor_source_and_adjusted_ic_controls(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "promotion.json"
            config_path.write_text(
                """
                {
                  "walk_forward_leaderboard": "walk_forward.csv",
                  "required_factor_source": "tushare_daily_basic",
                  "max_adjusted_ic_p_value": 0.05,
                  "max_tail_ic_p_value": 0.05,
                  "walk_forward_progress_audit": "progress/walk_forward_progress_audit.json",
                  "require_walk_forward_progress_audit": true,
                  "long_cycle_replay": "long_cycle/long_cycle_replay_pack.json",
                  "require_long_cycle_replay": true
                }
                """,
                encoding="utf-8",
            )

            config = load_promotion_gate_config(config_path)

        self.assertEqual(config.required_factor_source, "tushare_daily_basic")
        self.assertAlmostEqual(config.max_adjusted_ic_p_value, 0.05)
        self.assertAlmostEqual(config.max_tail_ic_p_value, 0.05)
        self.assertEqual(config.walk_forward_progress_audit, Path("progress/walk_forward_progress_audit.json"))
        self.assertTrue(config.require_walk_forward_progress_audit)
        self.assertEqual(config.long_cycle_replay, Path("long_cycle/long_cycle_replay_pack.json"))
        self.assertTrue(config.require_long_cycle_replay)

    def test_residual_regime_promotion_config_uses_strict_moneyflow_combo_controls(self):
        config = load_promotion_gate_config("configs/promotion_gate_tushare_moneyflow_residual_regime.json")

        self.assertEqual(
            config.walk_forward_leaderboard,
            Path("data/reports/walk_forward_tushare_moneyflow_residual_regime/walk_forward_leaderboard.csv"),
        )
        self.assertEqual(config.required_factor_source, "moneyflow_technical_combo")
        self.assertEqual(config.min_walk_forward_folds, 2)
        self.assertEqual(config.min_accepted_folds, 2)
        self.assertEqual(config.min_distinct_regime_lookbacks_for_family, 2)
        self.assertAlmostEqual(config.max_adjusted_ic_p_value or 0.0, 0.05)
        self.assertAlmostEqual(config.max_tail_ic_p_value or 0.0, 0.05)
        self.assertFalse(config.allow_manual_live_review)
        self.assertAlmostEqual(config.max_oos_sharpe_for_promotion or 0.0, 3.0)
        self.assertEqual(
            config.market_regime_coverage,
            Path("data/reports/market_regime_coverage_tushare_moneyflow_residual_regime/market_regime_coverage_pack.json"),
        )
        self.assertEqual(
            config.quality_report,
            Path("data/reports/data_quality_gap_audit_tushare_moneyflow_residual_regime/data_quality_gap_audit.json"),
        )
        self.assertTrue(config.require_market_regime_coverage)
        self.assertEqual(
            config.walk_forward_progress_audit,
            Path("data/reports/walk_forward_progress_audit_tushare_moneyflow_residual_regime/walk_forward_progress_audit.json"),
        )
        self.assertTrue(config.require_walk_forward_progress_audit)
        self.assertEqual(
            config.long_cycle_replay,
            Path("data/reports/long_cycle_factor_replay_tushare_moneyflow_residual_regime/long_cycle_replay_pack.json"),
        )
        self.assertTrue(config.require_long_cycle_replay)

    def test_strict_cn_stock_promotion_configs_require_long_cycle_replay_and_progress_audit(self):
        config_paths = [
            "configs/promotion_gate_tushare_moneyflow_residual_regime.json",
            "configs/promotion_gate_cn_stock_daily_basic_value_low_turnover_bucket_20260620.json",
            "configs/promotion_gate_cn_stock_daily_basic_value_size_liquidity_20260620.json",
            "configs/promotion_gate_cn_stock_price_volume_technical_20260620.json",
        ]

        for config_path in config_paths:
            with self.subTest(config_path=config_path):
                config = load_promotion_gate_config(config_path)
                self.assertTrue(config.require_long_cycle_replay)
                self.assertIsNotNone(config.long_cycle_replay)
                self.assertTrue(config.require_walk_forward_progress_audit)
                self.assertIsNotNone(config.walk_forward_progress_audit)

    def test_promotion_blocks_stale_or_unready_provider_status_when_required(self):
        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_momentum_60_top1_cost5_reb5", "momentum_60")],
            paper_manifest=_paper_manifest(
                case_id="CN_ETF_momentum_60_top1_cost5_reb5",
                factor_name="momentum_60",
                sharpe=0.80,
                total_return=0.20,
            ),
            provider_status={
                "generated_at": "2020-01-01",
                "providers": {"tushare": {"ready": False}},
            },
            config=PromotionGateConfig(
                min_oos_sharpe=0.5,
                min_paper_sharpe=0.5,
                require_provider_ready_for_promotion=True,
                max_provider_status_age_days=1,
            ),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("providers_not_ready_for_promotion", row["blocking_reasons"])
        self.assertIn("provider_status_stale", row["blocking_reasons"])

    def test_promotion_report_surfaces_selected_paper_risk_profile(self):
        report = build_promotion_report(
            walk_forward_rows=[_accepted_walk_forward_row("CN_ETF_liquidity_10_top1_cost5_reb5", "liquidity_10")],
            paper_manifest={
                "data_mode": "research",
                "metrics": {
                    "max_equity_drawdown": -0.12,
                    "sharpe": 0.80,
                    "total_return": 0.18,
                },
                "request": {
                    "case_id": "CN_ETF_liquidity_10_top1_cost5_reb5",
                    "market": "CN_ETF",
                    "factor_name": "liquidity_10",
                    "top_n": 1,
                    "rebalance_interval": 5,
                    "risk_profile_id": "balanced_fast_guard",
                },
            },
            config=PromotionGateConfig(min_oos_sharpe=0.5, min_paper_sharpe=0.5),
        )

        row = report["candidates"][0]
        self.assertEqual(row["paper"]["risk_profile_id"], "balanced_fast_guard")

    def test_fixture_data_is_not_promotable(self):
        report = build_promotion_report(
            walk_forward_rows=[
                {
                    "case_id": "CN_momentum_2_top1_cost0_reb1",
                    "market": "CN",
                    "factor_name": "momentum_2",
                    "top_n": 1,
                    "validation_status": "accepted",
                    "data_mode": "fixture",
                    "test_trades": 5,
                    "test_sharpe": 8.0,
                    "test_relative_return": 0.20,
                    "test_max_drawdown": 0.0,
                    "stability_score": 8.0,
                }
            ],
            config=PromotionGateConfig(require_non_fixture_data=True),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("fixture_data_not_promotable", row["blocking_reasons"])

    def test_extreme_oos_trade_return_blocks_promotion_even_if_walk_forward_is_accepted(self):
        walk_forward = _accepted_walk_forward_row("CN_ETF_momentum_20_top1_cost5_reb5", "momentum_20")
        walk_forward["test_extreme_trade_return_flag"] = True
        walk_forward["test_max_abs_trade_gross_return"] = 6.0

        report = build_promotion_report(
            walk_forward_rows=[walk_forward],
            paper_manifest=_paper_manifest(
                "CN_ETF_momentum_20_top1_cost5_reb5",
                "momentum_20",
                sharpe=0.80,
                total_return=0.18,
            ),
            config=PromotionGateConfig(min_oos_sharpe=0.5, min_paper_sharpe=0.5),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("extreme_oos_trade_return", row["blocking_reasons"])
        self.assertTrue(row["walk_forward"]["test_extreme_trade_return_flag"])

    def test_missing_relative_return_blocks_candidate_when_relative_gate_is_enabled(self):
        report = build_promotion_report(
            walk_forward_rows=[
                {
                    "case_id": "CN_ETF_momentum_20_top1_cost5_reb5",
                    "market": "CN_ETF",
                    "factor_name": "momentum_20",
                    "top_n": 1,
                    "cost_bps": 5,
                    "validation_status": "accepted",
                    "data_mode": "research",
                    "test_trades": 180,
                    "test_sharpe": 0.82,
                    "test_max_drawdown": -0.10,
                    "stability_score": 0.70,
                }
            ],
            paper_manifest={
                "data_mode": "research",
                "metrics": {
                    "max_equity_drawdown": -0.12,
                    "sharpe": 0.80,
                    "total_return": 0.18,
                },
                "request": {
                    "market": "CN_ETF",
                    "factor_name": "momentum_20",
                    "top_n": 1,
                    "rebalance_interval": 5,
                },
            },
            config=PromotionGateConfig(min_oos_relative_return=0.0),
        )

        row = report["candidates"][0]
        self.assertEqual(row["promotion_status"], "blocked")
        self.assertIn("oos_relative_return_missing", row["blocking_reasons"])

    def test_multiple_paper_manifests_match_each_candidate_without_cross_matching_rebalance(self):
        report = build_promotion_report(
            walk_forward_rows=[
                {
                    "case_id": "CN_ETF_momentum_20_top2_cost5_reb5",
                    "market": "CN_ETF",
                    "factor_name": "momentum_20",
                    "top_n": 2,
                    "cost_bps": 5,
                    "validation_status": "accepted",
                    "data_mode": "research",
                    "test_trades": 324,
                    "test_sharpe": 0.72,
                    "test_relative_return": 0.08,
                    "test_max_drawdown": -0.12,
                    "stability_score": 0.64,
                },
                {
                    "case_id": "CN_ETF_momentum_20_top2_cost5_reb10",
                    "market": "CN_ETF",
                    "factor_name": "momentum_20",
                    "top_n": 2,
                    "cost_bps": 5,
                    "validation_status": "accepted",
                    "data_mode": "research",
                    "test_trades": 162,
                    "test_sharpe": 0.60,
                    "test_relative_return": 0.03,
                    "test_max_drawdown": -0.10,
                    "stability_score": 0.50,
                },
            ],
            paper_manifests=[
                {
                    "data_mode": "research",
                    "metrics": {
                        "max_equity_drawdown": -0.12,
                        "sharpe": 0.80,
                        "total_return": 0.20,
                    },
                    "request": {
                        "market": "CN_ETF",
                        "factor_name": "momentum_20",
                        "top_n": 2,
                        "rebalance_interval": 5,
                    },
                },
                {
                    "data_mode": "research",
                    "metrics": {
                        "max_equity_drawdown": -0.45,
                        "sharpe": 0.10,
                        "total_return": 0.05,
                    },
                    "request": {
                        "market": "CN_ETF",
                        "factor_name": "momentum_20",
                        "top_n": 2,
                        "rebalance_interval": 10,
                    },
                },
            ],
            config=PromotionGateConfig(min_oos_sharpe=0.5, min_paper_sharpe=0.5),
        )

        by_case = {row["case_id"]: row for row in report["candidates"]}
        self.assertEqual(by_case["CN_ETF_momentum_20_top2_cost5_reb5"]["promotion_status"], "paper_ready")
        self.assertEqual(by_case["CN_ETF_momentum_20_top2_cost5_reb10"]["promotion_status"], "blocked")
        self.assertIn("paper_drawdown_above_limit", by_case["CN_ETF_momentum_20_top2_cost5_reb10"]["blocking_reasons"])

def _accepted_walk_forward_row(case_id: str, factor_name: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "market": "CN_ETF",
        "factor_name": factor_name,
        "top_n": 1,
        "cost_bps": 5,
        "validation_status": "accepted",
        "data_mode": "research",
        "test_trades": 80,
        "test_sharpe": 0.80,
        "test_relative_return": 0.06,
        "test_max_drawdown": -0.12,
        "stability_score": 0.70,
    }


def _write_paper_manifest_with_intents(root: Path, case_id: str, factor_name: str) -> dict[str, object]:
    case_dir = root / case_id
    case_dir.mkdir()
    (case_dir / "intents.csv").write_text(
        "\n".join(
            [
                "intent_id,signal_date,execution_date,asset_id,market,side,intended_quantity,signed_quantity,reference_price,target_weight,executable,broker_order_id,intent_type",
                "a,2024-01-02,2024-01-03,CN_ETF_XSHG_510300,CN_ETF,buy,100,100,4.0,0.4,False,,paper_simulation_intent",
                "b,2024-01-09,2024-01-10,CN_ETF_XSHG_510300,CN_ETF,sell,100,-100,4.1,0.0,False,,paper_simulation_intent",
                "c,2024-01-16,2024-01-17,CN_ETF_XSHE_159915,CN_ETF,buy,100,100,2.1,0.4,False,,paper_simulation_intent",
            ]
        ),
        encoding="utf-8",
    )
    manifest = {
        "manifest_path": str(case_dir / "manifest.json"),
        "data_mode": "research",
        "metrics": {
            "max_equity_drawdown": -0.10,
            "sharpe": 0.80,
            "total_return": 0.20,
        },
        "request": {
            "case_id": case_id,
            "market": "CN_ETF",
            "factor_name": factor_name,
            "top_n": 1,
            "rebalance_interval": 5,
        },
    }
    (case_dir / "manifest.json").write_text("{}", encoding="utf-8")
    return manifest


def _paper_manifest(case_id: str, factor_name: str, sharpe: float, total_return: float) -> dict[str, object]:
    return {
        "data_mode": "research",
        "metrics": {
            "max_equity_drawdown": -0.10,
            "sharpe": sharpe,
            "total_return": total_return,
        },
        "request": {
            "case_id": case_id,
            "market": "CN_ETF",
            "factor_name": factor_name,
            "top_n": 1,
            "rebalance_interval": 5,
        },
    }


if __name__ == "__main__":
    unittest.main()
