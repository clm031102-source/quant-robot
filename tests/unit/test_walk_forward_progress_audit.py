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
                "robust_case_candidates": 0,
                "conclusion": "no_robust_case",
                "claim_blockers": ["no_robust_progress_candidate"],
                "can_promote_from_progress_audit": False,
            },
            "passing_fold_distribution": [
                {"fold": "fold_22", "passing_rows": 1},
                {"fold": "fold_23", "passing_rows": 1},
            ],
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
                "robust_case_candidates": 0,
                "conclusion": "incomplete",
                "claim_blockers": ["walk_forward_incomplete"],
                "can_promote_from_progress_audit": False,
            },
            "passing_fold_distribution": [{"fold": "fold_01", "passing_rows": 1}],
            "factor_summary": [],
            "robust_case_candidates": [],
            "top_case_rejections": [],
        }

        markdown = render_progress_markdown(audit)

        self.assertIn("Walk-Forward Progress Audit", markdown)
        self.assertIn("walk_forward_incomplete", markdown)
        self.assertIn("cannot promote", markdown)


def _write_fold_leaderboard(root: Path, fold: str, rows: list[dict[str, str]]) -> None:
    path = root / fold / "test" / "leaderboard.csv"
    path.parent.mkdir(parents=True)
    headers = list(rows[0])
    lines = [",".join(headers)]
    lines.extend(",".join(str(row.get(header, "")) for header in headers) for row in rows)
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


if __name__ == "__main__":
    unittest.main()
