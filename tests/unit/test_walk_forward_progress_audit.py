import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.walk_forward_progress_audit import audit_walk_forward_progress, render_progress_markdown


class WalkForwardProgressAuditTests(unittest.TestCase):
    def test_incomplete_run_blocks_promotion_claim_even_when_rows_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fold_leaderboard(
                root,
                "fold_01",
                [
                    _row(
                        case_id="case_a",
                        factor_name="factor_a",
                        decision_status="approved",
                        sharpe=1.4,
                        relative_return=0.2,
                        max_drawdown=-0.1,
                    )
                ],
            )
            _write_fold_leaderboard(
                root,
                "fold_02",
                [
                    _row(
                        case_id="case_a",
                        factor_name="factor_a",
                        decision_status="approved",
                        sharpe=1.2,
                        relative_return=0.1,
                        max_drawdown=-0.12,
                    )
                ],
            )

            audit = audit_walk_forward_progress(root, expected_folds=3, min_case_passing_rows=1)

            self.assertEqual(audit["summary"]["completed_folds"], 2)
            self.assertFalse(audit["summary"]["is_complete"])
            self.assertEqual(audit["summary"]["passing_fold_rows"], 2)
            self.assertEqual(audit["summary"]["robust_case_candidates"], 0)
            self.assertEqual(audit["summary"]["conclusion"], "incomplete")
            self.assertIn("walk_forward_incomplete", audit["summary"]["claim_blockers"])

    def test_complete_run_flags_robust_case_but_still_requires_promotion_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for fold, sharpe in [("fold_01", 1.5), ("fold_02", 1.1)]:
                _write_fold_leaderboard(
                    root,
                    fold,
                    [
                        _row(
                            case_id="case_a",
                            factor_name="factor_a",
                            decision_status="approved",
                            sharpe=sharpe,
                            relative_return=0.15,
                            max_drawdown=-0.09,
                        )
                    ],
                )

            audit = audit_walk_forward_progress(root, expected_folds=2, min_case_passing_rows=1)

            self.assertTrue(audit["summary"]["is_complete"])
            self.assertEqual(audit["summary"]["robust_case_candidates"], 1)
            self.assertFalse(audit["summary"]["can_promote_from_progress_audit"])
            self.assertEqual(audit["summary"]["conclusion"], "robust_case_requires_promotion_gate")
            self.assertEqual(audit["robust_case_candidates"][0]["case_id"], "case_a")

    def test_local_fold_cluster_is_rejected_as_unstable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fold_leaderboard(
                root,
                "fold_01",
                [
                    _row(
                        case_id="case_a",
                        factor_name="factor_a",
                        decision_status="approved",
                        sharpe=2.0,
                        relative_return=0.2,
                        max_drawdown=-0.08,
                    )
                ],
            )
            for fold in ["fold_02", "fold_03", "fold_04"]:
                _write_fold_leaderboard(
                    root,
                    fold,
                    [
                        _row(
                            case_id="case_a",
                            factor_name="factor_a",
                            decision_status="rejected",
                            sharpe=-1.0,
                            relative_return=-0.2,
                            max_drawdown=-0.3,
                        )
                    ],
                )

            audit = audit_walk_forward_progress(root, expected_folds=4, min_case_passing_rows=2)

            self.assertEqual(audit["summary"]["passing_fold_rows"], 1)
            self.assertEqual(audit["summary"]["passing_folds"], 1)
            self.assertEqual(
                audit["passing_fold_distribution"],
                [{"fold": "fold_01", "passing_rows": 1}],
            )
            self.assertEqual(audit["summary"]["robust_case_candidates"], 0)
            self.assertIn("insufficient_passing_fold_coverage", audit["top_case_rejections"][0]["blockers"])

    def test_case_level_high_participation_blocks_otherwise_good_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fold_leaderboard(
                root,
                "fold_01",
                [
                    _row(
                        case_id="case_a",
                        factor_name="factor_a",
                        decision_status="approved",
                        sharpe=1.5,
                        relative_return=0.2,
                        max_drawdown=-0.1,
                    )
                ],
            )
            high_participation = _row(
                case_id="case_a",
                factor_name="factor_a",
                decision_status="approved",
                sharpe=1.4,
                relative_return=0.2,
                max_drawdown=-0.1,
            )
            high_participation["max_participation_rate"] = "0.25"
            _write_fold_leaderboard(root, "fold_02", [high_participation])

            audit = audit_walk_forward_progress(root, expected_folds=2, min_case_passing_rows=1)

            self.assertEqual(audit["summary"]["robust_case_candidates"], 0)
            self.assertIn("participation_rate_above_progress_limit", audit["top_case_rejections"][0]["blockers"])

    def test_extreme_trade_return_blocks_progress_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            safe = _row(
                case_id="case_a",
                factor_name="factor_a",
                decision_status="approved",
                sharpe=1.5,
                relative_return=0.2,
                max_drawdown=-0.1,
            )
            extreme = _row(
                case_id="case_a",
                factor_name="factor_a",
                decision_status="approved",
                sharpe=1.4,
                relative_return=0.2,
                max_drawdown=-0.1,
            )
            extreme["max_abs_trade_gross_return"] = "6.0"
            extreme["extreme_trade_return_flag"] = "True"
            _write_fold_leaderboard(root, "fold_01", [safe])
            _write_fold_leaderboard(root, "fold_02", [extreme])

            audit = audit_walk_forward_progress(root, expected_folds=2, min_case_passing_rows=1)

            self.assertEqual(audit["summary"]["passing_fold_rows"], 1)
            self.assertEqual(audit["summary"]["robust_case_candidates"], 0)
            self.assertIn("extreme_oos_trade_return", audit["top_case_rejections"][0]["blockers"])

    def test_no_trade_fold_is_summarized_and_blocks_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fold_leaderboard(
                root,
                "fold_01",
                [
                    _row(
                        case_id="case_a",
                        factor_name="factor_a",
                        decision_status="approved",
                        sharpe=1.3,
                        relative_return=0.2,
                        max_drawdown=-0.08,
                    )
                ],
            )
            _write_fold_leaderboard(
                root,
                "fold_02",
                [
                    _no_trade_row(case_id="case_a", factor_name="factor_a"),
                    _no_trade_row(case_id="case_b", factor_name="factor_b"),
                ],
            )

            audit = audit_walk_forward_progress(root, expected_folds=2, min_case_passing_rows=1)

            self.assertEqual(audit["summary"]["no_trade_rows"], 2)
            self.assertEqual(audit["summary"]["no_trade_folds"], 1)
            self.assertEqual(
                audit["no_trade_fold_distribution"],
                [
                    {
                        "fold": "fold_02",
                        "no_trade_rows": 2,
                        "rows": 2,
                        "all_rows_no_trade": True,
                        "regime_all_blocked_no_trade_rows": 0,
                    }
                ],
            )
            self.assertIn("no_trade_folds_present", audit["summary"]["claim_blockers"])

    def test_no_trade_regime_all_blocked_cases_are_diagnosed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fold_leaderboard(
                root,
                "fold_01",
                [
                    _no_trade_row(case_id="case_all_blocked", factor_name="factor_a"),
                    _no_trade_row(case_id="case_partly_allowed", factor_name="factor_b"),
                ],
            )
            _write_regime_curve(root, "fold_01", "case_all_blocked", [False, False, False])
            _write_regime_curve(root, "fold_01", "case_partly_allowed", [False, True, False])

            audit = audit_walk_forward_progress(root, expected_folds=1, min_case_passing_rows=1)

            self.assertEqual(audit["summary"]["regime_all_blocked_no_trade_rows"], 1)
            self.assertEqual(audit["summary"]["regime_all_blocked_no_trade_folds"], 1)
            self.assertIn("regime_filter_all_blocked_no_trade_cases", audit["summary"]["claim_blockers"])
            self.assertEqual(
                audit["no_trade_fold_distribution"],
                [
                    {
                        "fold": "fold_01",
                        "no_trade_rows": 2,
                        "rows": 2,
                        "all_rows_no_trade": True,
                        "regime_all_blocked_no_trade_rows": 1,
                    }
                ],
            )

    def test_no_trade_regime_blocked_uses_signal_window_from_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fold_leaderboard(
                root,
                "fold_01",
                [_no_trade_row(case_id="case_window_blocked", factor_name="factor_a")],
            )
            _write_manifest(root, "fold_01", signal_start_date="2026-01-02", signal_end_date="2026-01-03")
            _write_regime_curve(
                root,
                "fold_01",
                "case_window_blocked",
                [
                    ("2026-01-01", True),
                    ("2026-01-02", False),
                    ("2026-01-03", False),
                    ("2026-01-04", True),
                ],
            )

            audit = audit_walk_forward_progress(root, expected_folds=1, min_case_passing_rows=1)

            self.assertEqual(audit["summary"]["regime_all_blocked_no_trade_rows"], 1)
            self.assertIn("regime_filter_all_blocked_no_trade_cases", audit["summary"]["claim_blockers"])

    def test_case_summary_names_no_trade_and_regime_all_blocked_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_fold_leaderboard(
                root,
                "fold_01",
                [_no_trade_row(case_id="case_window_blocked", factor_name="factor_a")],
            )
            _write_manifest(root, "fold_01", signal_start_date="2026-01-02", signal_end_date="2026-01-03")
            _write_regime_curve(
                root,
                "fold_01",
                "case_window_blocked",
                [
                    ("2026-01-01", True),
                    ("2026-01-02", False),
                    ("2026-01-03", False),
                ],
            )

            audit = audit_walk_forward_progress(root, expected_folds=1, min_case_passing_rows=1)

            rejection = audit["top_case_rejections"][0]
            self.assertEqual(rejection["case_id"], "case_window_blocked")
            self.assertEqual(rejection["no_trade_rows"], 1)
            self.assertEqual(rejection["regime_all_blocked_no_trade_rows"], 1)
            self.assertIn("case_no_trades_present", rejection["blockers"])
            self.assertIn("case_regime_all_blocked_no_trades", rejection["blockers"])

            markdown = render_progress_markdown(audit)
            self.assertIn("no_trade=1", markdown)
            self.assertIn("regime_all_blocked_no_trade=1", markdown)

    def test_markdown_includes_passing_fold_distribution(self):
        audit = {
            "summary": {
                "generated_at": "2026-06-20 15:20:00 +08:00",
                "completed_folds": 4,
                "expected_folds": 4,
                "rows": 4,
                "unique_cases": 1,
                "unique_factors": 1,
                "passing_fold_rows": 2,
                "passing_folds": 2,
                "no_trade_rows": 0,
                "no_trade_folds": 0,
                "robust_case_candidates": 0,
                "conclusion": "no_robust_case",
                "claim_blockers": ["no_robust_progress_candidate"],
                "can_promote_from_progress_audit": False,
            },
            "passing_fold_distribution": [
                {"fold": "fold_22", "passing_rows": 1},
                {"fold": "fold_23", "passing_rows": 1},
            ],
            "no_trade_fold_distribution": [],
            "factor_summary": [],
            "robust_case_candidates": [],
            "top_case_rejections": [],
        }

        markdown = render_progress_markdown(audit)

        self.assertIn("Passing Fold Distribution", markdown)
        self.assertIn("fold_22", markdown)
        self.assertIn("fold_23", markdown)

    def test_markdown_names_incomplete_and_gate_boundary(self):
        audit = {
            "summary": {
                "generated_at": "2026-06-20 15:20:00 +08:00",
                "completed_folds": 1,
                "expected_folds": 2,
                "rows": 1,
                "unique_cases": 1,
                "unique_factors": 1,
                "passing_fold_rows": 1,
                "passing_folds": 1,
                "no_trade_rows": 0,
                "no_trade_folds": 0,
                "robust_case_candidates": 0,
                "conclusion": "incomplete",
                "claim_blockers": ["walk_forward_incomplete"],
                "can_promote_from_progress_audit": False,
            },
            "passing_fold_distribution": [{"fold": "fold_01", "passing_rows": 1}],
            "no_trade_fold_distribution": [],
            "factor_summary": [],
            "robust_case_candidates": [],
            "top_case_rejections": [],
        }

        markdown = render_progress_markdown(audit)

        self.assertIn("Walk-Forward Progress Audit", markdown)
        self.assertIn("walk_forward_incomplete", markdown)
        self.assertIn("cannot promote", markdown)

    def test_markdown_includes_no_trade_fold_distribution(self):
        audit = {
            "summary": {
                "generated_at": "2026-06-20 15:20:00 +08:00",
                "completed_folds": 2,
                "expected_folds": 2,
                "rows": 3,
                "unique_cases": 2,
                "unique_factors": 2,
                "passing_fold_rows": 1,
                "passing_folds": 1,
                "no_trade_rows": 2,
                "no_trade_folds": 1,
                "regime_all_blocked_no_trade_rows": 1,
                "regime_all_blocked_no_trade_folds": 1,
                "robust_case_candidates": 0,
                "conclusion": "no_robust_case",
                "claim_blockers": [
                    "no_trade_folds_present",
                    "regime_filter_all_blocked_no_trade_cases",
                    "no_robust_progress_candidate",
                ],
                "can_promote_from_progress_audit": False,
            },
            "passing_fold_distribution": [{"fold": "fold_01", "passing_rows": 1}],
            "no_trade_fold_distribution": [
                {
                    "fold": "fold_02",
                    "no_trade_rows": 2,
                    "rows": 2,
                    "all_rows_no_trade": True,
                    "regime_all_blocked_no_trade_rows": 1,
                }
            ],
            "factor_summary": [],
            "robust_case_candidates": [],
            "top_case_rejections": [],
        }

        markdown = render_progress_markdown(audit)

        self.assertIn("No-Trade Fold Distribution", markdown)
        self.assertIn("No-trade rows: 2", markdown)
        self.assertIn("Regime all-blocked no-trade rows: 1", markdown)
        self.assertIn("fold_02", markdown)

def _write_fold_leaderboard(root: Path, fold: str, rows: list[dict[str, str]]) -> None:
    path = root / fold / "test" / "leaderboard.csv"
    path.parent.mkdir(parents=True)
    headers = list(rows[0])
    lines = [",".join(headers)]
    lines.extend(",".join(str(row.get(header, "")) for header in headers) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest(root: Path, fold: str, *, signal_start_date: str, signal_end_date: str) -> None:
    path = root / fold / "test" / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            '{"config": {'
            f'"signal_start_date": "{signal_start_date}", '
            f'"signal_end_date": "{signal_end_date}"'
            '}}'
        ),
        encoding="utf-8",
    )


def _write_regime_curve(root: Path, fold: str, case_id: str, allowed_values: list[bool | tuple[str, bool]]) -> None:
    path = root / fold / "test" / case_id / "regime_curve.csv"
    path.parent.mkdir(parents=True)
    lines = ["date,regime_momentum,regime_allowed"]
    for idx, allowed in enumerate(allowed_values, start=1):
        if isinstance(allowed, tuple):
            date_text, allowed_value = allowed
        else:
            date_text, allowed_value = f"2026-01-{idx:02d}", allowed
        lines.append(f"{date_text},0.01,{allowed_value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _row(
    *,
    case_id: str,
    factor_name: str,
    decision_status: str,
    sharpe: float,
    relative_return: float,
    max_drawdown: float,
) -> dict[str, str]:
    return {
        "case_id": case_id,
        "market": "CN",
        "factor_source": "test",
        "factor_name": factor_name,
        "factor_windows": "[20]",
        "top_n": "5",
        "cost_bps": "20",
        "rebalance_interval": "1",
        "regime_lookback": "120",
        "status": "completed",
        "trades": "40",
        "annualized_return": "0.2",
        "sharpe": str(sharpe),
        "max_drawdown": str(max_drawdown),
        "win_rate": "0.6",
        "relative_return": str(relative_return),
        "capacity_limited_trades": "0",
        "max_participation_rate": "0.005",
        "decision_status": decision_status,
        "tail_rank_ic_t_stat": "2.1",
        "rank_ic_t_stat": "1.5",
        "overlap_autocorr_adjusted_sharpe": str(sharpe),
    }


def _no_trade_row(*, case_id: str, factor_name: str) -> dict[str, str]:
    row = _row(
        case_id=case_id,
        factor_name=factor_name,
        decision_status="rejected",
        sharpe=0.0,
        relative_return=0.0,
        max_drawdown=0.0,
    )
    row["status"] = "no_trades"
    row["trades"] = "0"
    row["annualized_return"] = "0"
    row["win_rate"] = "0"
    row["tail_rank_ic_t_stat"] = "0"
    row["rank_ic_t_stat"] = "0"
    row["overlap_autocorr_adjusted_sharpe"] = "0"
    return row


if __name__ == "__main__":
    unittest.main()
