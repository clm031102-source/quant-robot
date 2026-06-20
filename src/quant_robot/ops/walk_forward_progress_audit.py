from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from statistics import mean, median
from typing import Any


DEFAULT_EXPECTED_FOLDS = 38
DEFAULT_MIN_TRADES = 30
DEFAULT_MIN_CASE_PASSING_ROWS = 8
DEFAULT_MIN_CASE_PASSING_FRACTION = 0.25
DEFAULT_ROW_MIN_SHARPE = 1.0
DEFAULT_ROW_MAX_DRAWDOWN = 0.25
DEFAULT_ROW_MAX_PARTICIPATION = 0.01
DEFAULT_CASE_MIN_MEAN_SHARPE = 0.5
DEFAULT_CASE_MAX_DRAWDOWN = 0.35
DEFAULT_CASE_MIN_POSITIVE_RELATIVE_FRACTION = 0.55


def audit_walk_forward_progress(
    root: str | Path,
    *,
    expected_folds: int = DEFAULT_EXPECTED_FOLDS,
    min_trades: int = DEFAULT_MIN_TRADES,
    min_case_passing_rows: int = DEFAULT_MIN_CASE_PASSING_ROWS,
    min_case_passing_fraction: float = DEFAULT_MIN_CASE_PASSING_FRACTION,
    row_min_sharpe: float = DEFAULT_ROW_MIN_SHARPE,
    row_max_drawdown: float = DEFAULT_ROW_MAX_DRAWDOWN,
    row_max_participation: float = DEFAULT_ROW_MAX_PARTICIPATION,
    case_max_participation: float = DEFAULT_ROW_MAX_PARTICIPATION,
    case_min_mean_sharpe: float = DEFAULT_CASE_MIN_MEAN_SHARPE,
    case_max_drawdown: float = DEFAULT_CASE_MAX_DRAWDOWN,
    case_min_positive_relative_fraction: float = DEFAULT_CASE_MIN_POSITIVE_RELATIVE_FRACTION,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root_path = Path(root)
    fold_progress, rows = _read_fold_rows(root_path)
    completed_folds = [fold for fold in fold_progress if fold["test_leaderboard"]]
    is_complete = len(completed_folds) >= expected_folds
    for row in rows:
        row["regime_all_blocked_no_trade"] = (
            str(row.get("status")) == "no_trades" and _case_regime_all_blocked(root_path, row)
        )
    for row in rows:
        row["passes_progress_row_gate"] = _passes_row_gate(
            row,
            min_trades=min_trades,
            row_min_sharpe=row_min_sharpe,
            row_max_drawdown=row_max_drawdown,
            row_max_participation=row_max_participation,
        )
    case_summary = _case_summary(
        rows,
        completed_fold_count=len(completed_folds),
        min_case_passing_rows=min_case_passing_rows,
        min_case_passing_fraction=min_case_passing_fraction,
        case_min_mean_sharpe=case_min_mean_sharpe,
        case_max_drawdown=case_max_drawdown,
        case_max_participation=case_max_participation,
        case_min_positive_relative_fraction=case_min_positive_relative_fraction,
        allow_robust_candidates=is_complete,
    )
    robust_candidates = [row for row in case_summary if row["robust_progress_candidate"]]
    factor_summary = _factor_summary(rows)
    passing_fold_distribution = _passing_fold_distribution(rows)
    no_trade_fold_distribution = _no_trade_fold_distribution(rows, root_path)
    no_trade_rows = sum(int(row["no_trade_rows"]) for row in no_trade_fold_distribution)
    regime_all_blocked_no_trade_rows = sum(
        int(row["regime_all_blocked_no_trade_rows"]) for row in no_trade_fold_distribution
    )
    claim_blockers = _claim_blockers(
        is_complete=is_complete,
        robust_count=len(robust_candidates),
        no_trade_fold_count=len(no_trade_fold_distribution),
        regime_all_blocked_no_trade_count=regime_all_blocked_no_trade_rows,
    )
    return {
        "summary": {
            "generated_at": generated_at or datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
            "root": str(root_path),
            "expected_folds": expected_folds,
            "completed_folds": len(completed_folds),
            "is_complete": is_complete,
            "rows": len(rows),
            "unique_cases": len({str(row.get("case_id")) for row in rows if row.get("case_id")}),
            "unique_factors": len({str(row.get("factor_name")) for row in rows if row.get("factor_name")}),
            "passing_fold_rows": sum(1 for row in rows if row["passes_progress_row_gate"]),
            "passing_folds": len(passing_fold_distribution),
            "no_trade_rows": no_trade_rows,
            "no_trade_folds": len(no_trade_fold_distribution),
            "regime_all_blocked_no_trade_rows": regime_all_blocked_no_trade_rows,
            "regime_all_blocked_no_trade_folds": sum(
                1 for row in no_trade_fold_distribution if int(row["regime_all_blocked_no_trade_rows"]) > 0
            ),
            "robust_case_candidates": len(robust_candidates),
            "can_promote_from_progress_audit": False,
            "conclusion": _conclusion(is_complete=is_complete, robust_count=len(robust_candidates)),
            "claim_blockers": claim_blockers,
        },
        "fold_progress": fold_progress,
        "passing_fold_distribution": passing_fold_distribution,
        "no_trade_fold_distribution": no_trade_fold_distribution,
        "factor_summary": factor_summary,
        "case_summary": case_summary,
        "robust_case_candidates": robust_candidates,
        "top_case_rejections": [row for row in case_summary if not row["robust_progress_candidate"]][:20],
    }


def render_progress_markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    lines = [
        "# Walk-Forward Progress Audit",
        "",
        f"- Generated at: {summary.get('generated_at')}",
        f"- Completed folds: {summary.get('completed_folds')} / {summary.get('expected_folds')}",
        f"- Rows: {summary.get('rows')}",
        f"- Unique cases: {summary.get('unique_cases')}",
        f"- Unique factors: {summary.get('unique_factors')}",
        f"- Passing fold rows: {summary.get('passing_fold_rows')}",
        f"- Passing folds: {summary.get('passing_folds')}",
        f"- No-trade rows: {summary.get('no_trade_rows', 0)}",
        f"- No-trade folds: {summary.get('no_trade_folds', 0)}",
        f"- Regime all-blocked no-trade rows: {summary.get('regime_all_blocked_no_trade_rows', 0)}",
        f"- Regime all-blocked no-trade folds: {summary.get('regime_all_blocked_no_trade_folds', 0)}",
        f"- Robust progress candidates: {summary.get('robust_case_candidates')}",
        f"- Conclusion: `{summary.get('conclusion')}`",
        "- Boundary: this progress audit cannot promote a factor; promotion still requires the formal gate.",
        "",
        "## Claim Blockers",
        "",
    ]
    blockers = list(summary.get("claim_blockers") or [])
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- None for progress-audit handoff; formal promotion gate still required.")
    lines.extend(
        [
            "",
            "## Passing Fold Distribution",
            "",
            "| Fold | Passing Rows |",
            "| --- | --- |",
        ]
    )
    passing_distribution = audit.get("passing_fold_distribution", [])
    if passing_distribution:
        for row in passing_distribution[:20]:
            lines.append(f"| {_text(row.get('fold'))} | {_text(row.get('passing_rows'))} |")
    else:
        lines.append("| n/a | 0 |")
    lines.extend(
        [
            "",
            "## No-Trade Fold Distribution",
            "",
            "| Fold | No-Trade Rows | Rows | All Rows No-Trade | Regime All-Blocked No-Trade Rows |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    no_trade_distribution = audit.get("no_trade_fold_distribution", [])
    if no_trade_distribution:
        for row in no_trade_distribution[:20]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        _text(row.get("fold")),
                        _text(row.get("no_trade_rows")),
                        _text(row.get("rows")),
                        _text(row.get("all_rows_no_trade")),
                        _text(row.get("regime_all_blocked_no_trade_rows", 0)),
                    ]
                )
                + " |"
            )
    else:
        lines.append("| n/a | 0 | 0 | False | 0 |")
    lines.extend(
        [
            "",
            "## Factor Summary",
            "",
            "| Factor | Cases | Rows | Passing Rows | Mean Sharpe | Mean Ann Ret | Mean Relative | Mean Win Rate | Worst DD | Cap Trades | Max Part |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in audit.get("factor_summary", [])[:12]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _text(row.get("factor_name")),
                    _text(row.get("cases")),
                    _text(row.get("rows")),
                    _text(row.get("passing_rows")),
                    _metric(row.get("mean_sharpe")),
                    _metric(row.get("mean_annualized_return")),
                    _metric(row.get("mean_relative_return")),
                    _metric(row.get("mean_win_rate")),
                    _metric(row.get("worst_drawdown")),
                    _metric(row.get("capacity_limited_trades")),
                    _metric(row.get("max_participation_rate")),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Robust Progress Candidates",
            "",
        ]
    )
    robust = audit.get("robust_case_candidates", [])
    if not robust:
        lines.append("- None.")
    else:
        for row in robust[:10]:
            lines.append(
                "- "
                f"`{row['case_id']}` folds={row['folds']} passing={row['passing_rows']} "
                f"mean_sharpe={_metric(row['mean_sharpe'])} mean_relative={_metric(row['mean_relative_return'])}"
            )
    lines.extend(
        [
            "",
            "## Top Case Rejections",
            "",
        ]
    )
    rejections = audit.get("top_case_rejections", [])
    if not rejections:
        lines.append("- None.")
    else:
        for row in rejections[:12]:
            blockers_text = ", ".join(f"`{blocker}`" for blocker in row.get("blockers", [])) or "n/a"
            lines.append(
                "- "
                f"`{row['case_id']}` passing={row['passing_rows']}/{row['folds']} "
                f"no_trade={_text(row.get('no_trade_rows', 0))} "
                f"regime_all_blocked_no_trade={_text(row.get('regime_all_blocked_no_trade_rows', 0))} "
                f"mean_sharpe={_metric(row['mean_sharpe'])}: {blockers_text}"
            )
    lines.extend(["", "This audit cannot promote factors by itself."])
    return "\n".join(lines) + "\n"


def _read_fold_rows(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    fold_progress: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for fold_dir in sorted(root.glob("fold_*")):
        if not fold_dir.is_dir():
            continue
        test_leaderboard = fold_dir / "test" / "leaderboard.csv"
        train_leaderboard = fold_dir / "train" / "leaderboard.csv"
        partial_rows = _count_partial_rows(fold_dir / "test")
        fold_progress.append(
            {
                "fold": fold_dir.name,
                "train_leaderboard": train_leaderboard.exists(),
                "test_leaderboard": test_leaderboard.exists(),
                "test_partial_rows": partial_rows,
            }
        )
        if test_leaderboard.exists():
            for row in _read_csv_records(test_leaderboard):
                row["fold"] = fold_dir.name
                rows.append(row)
    return fold_progress, rows


def _count_partial_rows(path: Path) -> int:
    total = 0
    for partial in path.rglob("partial_leaderboard.jsonl") if path.exists() else []:
        total += sum(1 for line in partial.read_text(encoding="utf-8").splitlines() if line.strip())
    return total


def _read_csv_records(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _passes_row_gate(
    row: dict[str, Any],
    *,
    min_trades: int,
    row_min_sharpe: float,
    row_max_drawdown: float,
    row_max_participation: float,
) -> bool:
    return (
        str(row.get("decision_status")) == "approved"
        and str(row.get("status")) == "completed"
        and _float(row.get("trades")) >= min_trades
        and _float(row.get("sharpe")) >= row_min_sharpe
        and _float(row.get("relative_return")) > 0
        and _float(row.get("max_drawdown")) >= -row_max_drawdown
        and _float(row.get("capacity_limited_trades")) == 0
        and _float(row.get("max_participation_rate"), default=float("inf")) <= row_max_participation
    )


def _case_summary(
    rows: list[dict[str, Any]],
    *,
    completed_fold_count: int,
    min_case_passing_rows: int,
    min_case_passing_fraction: float,
    case_min_mean_sharpe: float,
    case_max_drawdown: float,
    case_max_participation: float,
    case_min_positive_relative_fraction: float,
    allow_robust_candidates: bool,
) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[_case_key(row)].append(row)
    summaries: list[dict[str, Any]] = []
    for key, case_rows in grouped.items():
        passing_rows = sum(1 for row in case_rows if row["passes_progress_row_gate"])
        folds = len({str(row.get("fold")) for row in case_rows if row.get("fold")})
        required_rows = max(min_case_passing_rows, int(completed_fold_count * min_case_passing_fraction))
        relative_returns = [_float(row.get("relative_return")) for row in case_rows]
        capacity_limited_trades = sum(_float(row.get("capacity_limited_trades")) for row in case_rows)
        max_participation = max((_float(row.get("max_participation_rate")) for row in case_rows), default=0.0)
        no_trade_rows = sum(1 for row in case_rows if str(row.get("status")) == "no_trades")
        regime_all_blocked_no_trade_rows = sum(1 for row in case_rows if row.get("regime_all_blocked_no_trade"))
        summary = {
            "case_id": str(key[0]),
            "factor_name": str(key[1]),
            "factor_windows": str(key[2]),
            "top_n": str(key[3]),
            "cost_bps": str(key[4]),
            "rebalance_interval": str(key[5]),
            "regime_lookback": str(key[6]),
            "folds": folds,
            "passing_rows": passing_rows,
            "required_passing_rows": required_rows,
            "no_trade_rows": no_trade_rows,
            "regime_all_blocked_no_trade_rows": regime_all_blocked_no_trade_rows,
            "mean_sharpe": _mean_float(case_rows, "sharpe"),
            "median_sharpe": _median_float(case_rows, "sharpe"),
            "positive_sharpe_fraction": _positive_fraction(case_rows, "sharpe"),
            "mean_annualized_return": _mean_float(case_rows, "annualized_return"),
            "mean_relative_return": mean(relative_returns) if relative_returns else 0.0,
            "positive_relative_fraction": sum(1 for value in relative_returns if value > 0) / len(relative_returns)
            if relative_returns
            else 0.0,
            "mean_win_rate": _mean_float(case_rows, "win_rate"),
            "worst_drawdown": min((_float(row.get("max_drawdown")) for row in case_rows), default=0.0),
            "capacity_limited_trades": capacity_limited_trades,
            "max_participation_rate": max_participation,
            "mean_tail_rank_ic_t_stat": _mean_float(case_rows, "tail_rank_ic_t_stat"),
            "mean_rank_ic_t_stat": _mean_float(case_rows, "rank_ic_t_stat"),
            "mean_overlap_adjusted_sharpe": _mean_float(case_rows, "overlap_autocorr_adjusted_sharpe"),
        }
        blockers = _case_blockers(
            summary,
            allow_robust_candidates=allow_robust_candidates,
            case_min_mean_sharpe=case_min_mean_sharpe,
            case_max_drawdown=case_max_drawdown,
            case_max_participation=case_max_participation,
            case_min_positive_relative_fraction=case_min_positive_relative_fraction,
        )
        summary["blockers"] = blockers
        summary["robust_progress_candidate"] = not blockers
        summaries.append(summary)
    return sorted(summaries, key=_case_sort_key)


def _case_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("case_id"),
        row.get("factor_name"),
        row.get("factor_windows"),
        row.get("top_n"),
        row.get("cost_bps"),
        row.get("rebalance_interval"),
        row.get("regime_lookback"),
    )


def _case_blockers(
    row: dict[str, Any],
    *,
    allow_robust_candidates: bool,
    case_min_mean_sharpe: float,
    case_max_drawdown: float,
    case_max_participation: float,
    case_min_positive_relative_fraction: float,
) -> list[str]:
    blockers: list[str] = []
    if not allow_robust_candidates:
        blockers.append("walk_forward_incomplete")
    if int(row["passing_rows"]) < int(row["required_passing_rows"]):
        blockers.append("insufficient_passing_fold_coverage")
    if int(row.get("no_trade_rows", 0)) > 0:
        blockers.append("case_no_trades_present")
    if int(row.get("regime_all_blocked_no_trade_rows", 0)) > 0:
        blockers.append("case_regime_all_blocked_no_trades")
    if float(row["mean_sharpe"]) < case_min_mean_sharpe:
        blockers.append("mean_sharpe_below_progress_floor")
    if float(row["median_sharpe"]) < 0:
        blockers.append("negative_median_sharpe")
    if float(row["mean_relative_return"]) <= 0:
        blockers.append("non_positive_mean_relative_return")
    if float(row["positive_relative_fraction"]) < case_min_positive_relative_fraction:
        blockers.append("relative_return_not_consistent")
    if float(row["worst_drawdown"]) < -case_max_drawdown:
        blockers.append("drawdown_breach")
    if float(row["capacity_limited_trades"]) > 0:
        blockers.append("capacity_limited_trades_present")
    if float(row["max_participation_rate"]) > case_max_participation:
        blockers.append("participation_rate_above_progress_limit")
    return blockers


def _factor_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("factor_name"))].append(row)
    summaries = []
    for factor_name, factor_rows in grouped.items():
        summaries.append(
            {
                "factor_name": factor_name,
                "cases": len({str(row.get("case_id")) for row in factor_rows}),
                "rows": len(factor_rows),
                "passing_rows": sum(1 for row in factor_rows if row["passes_progress_row_gate"]),
                "mean_sharpe": _mean_float(factor_rows, "sharpe"),
                "mean_annualized_return": _mean_float(factor_rows, "annualized_return"),
                "mean_relative_return": _mean_float(factor_rows, "relative_return"),
                "mean_win_rate": _mean_float(factor_rows, "win_rate"),
                "worst_drawdown": min((_float(row.get("max_drawdown")) for row in factor_rows), default=0.0),
                "capacity_limited_trades": sum(_float(row.get("capacity_limited_trades")) for row in factor_rows),
                "max_participation_rate": max(
                    (_float(row.get("max_participation_rate")) for row in factor_rows), default=0.0
                ),
                "mean_tail_rank_ic_t_stat": _mean_float(factor_rows, "tail_rank_ic_t_stat"),
            }
        )
    return sorted(summaries, key=lambda row: (-int(row["passing_rows"]), -float(row["mean_sharpe"]), row["factor_name"]))


def _passing_fold_distribution(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        if row.get("passes_progress_row_gate"):
            counts[str(row.get("fold"))] += 1
    return [
        {"fold": fold, "passing_rows": count}
        for fold, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _no_trade_fold_distribution(rows: list[dict[str, Any]], root: Path) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("fold"))].append(row)
    distribution: list[dict[str, Any]] = []
    for fold, fold_rows in grouped.items():
        no_trade_case_rows = [row for row in fold_rows if str(row.get("status")) == "no_trades"]
        no_trade_rows = len(no_trade_case_rows)
        if no_trade_rows:
            regime_all_blocked_no_trade_rows = sum(
                1
                for row in no_trade_case_rows
                if row.get("regime_all_blocked_no_trade") or _case_regime_all_blocked(root, row)
            )
            distribution.append(
                {
                    "fold": fold,
                    "no_trade_rows": no_trade_rows,
                    "rows": len(fold_rows),
                    "all_rows_no_trade": no_trade_rows == len(fold_rows),
                    "regime_all_blocked_no_trade_rows": regime_all_blocked_no_trade_rows,
                }
            )
    return sorted(distribution, key=lambda row: (-int(row["no_trade_rows"]), str(row["fold"])))


def _case_regime_all_blocked(root: Path, row: dict[str, Any]) -> bool:
    fold = str(row.get("fold") or "")
    case_id = str(row.get("case_id") or "")
    if not fold or not case_id:
        return False
    path = root / fold / "test" / case_id / "regime_curve.csv"
    if not path.exists():
        return False
    records = _read_csv_records(path)
    if not records:
        return False
    start_date, end_date = _fold_signal_window(root, fold)
    scoped_records = records
    if start_date and end_date:
        scoped_records = [
            record
            for record in records
            if start_date <= str(record.get("date") or "") <= end_date
        ]
        if not scoped_records:
            return False
    return all(not _truthy(record.get("regime_allowed")) for record in scoped_records)


def _fold_signal_window(root: Path, fold: str) -> tuple[str | None, str | None]:
    path = root / fold / "test" / "manifest.json"
    if not path.exists():
        return None, None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None, None
    config = manifest.get("config") if isinstance(manifest, dict) else {}
    if not isinstance(config, dict):
        return None, None
    start_date = config.get("signal_start_date")
    end_date = config.get("signal_end_date")
    if not start_date or not end_date:
        return None, None
    return str(start_date), str(end_date)


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _claim_blockers(
    *,
    is_complete: bool,
    robust_count: int,
    no_trade_fold_count: int,
    regime_all_blocked_no_trade_count: int,
) -> list[str]:
    blockers = ["requires_formal_promotion_gate"]
    if not is_complete:
        blockers.insert(0, "walk_forward_incomplete")
    if no_trade_fold_count > 0:
        blockers.append("no_trade_folds_present")
    if regime_all_blocked_no_trade_count > 0:
        blockers.append("regime_filter_all_blocked_no_trade_cases")
    if robust_count == 0:
        blockers.append("no_robust_progress_candidate")
    return blockers


def _conclusion(*, is_complete: bool, robust_count: int) -> str:
    if not is_complete:
        return "incomplete"
    if robust_count == 0:
        return "no_robust_case"
    return "robust_case_requires_promotion_gate"


def _case_sort_key(row: dict[str, Any]) -> tuple[int, int, float, float, str]:
    robust = 0 if row["robust_progress_candidate"] else 1
    return (
        robust,
        -int(row["passing_rows"]),
        -float(row["mean_sharpe"]),
        -float(row["mean_relative_return"]),
        str(row["case_id"]),
    )


def _mean_float(rows: list[dict[str, Any]], key: str) -> float:
    values = [_float(row.get(key)) for row in rows]
    return mean(values) if values else 0.0


def _median_float(rows: list[dict[str, Any]], key: str) -> float:
    values = [_float(row.get(key)) for row in rows]
    return median(values) if values else 0.0


def _positive_fraction(rows: list[dict[str, Any]], key: str) -> float:
    values = [_float(row.get(key)) for row in rows]
    return sum(1 for value in values if value > 0) / len(values) if values else 0.0


def _float(value: Any, *, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _metric(value: Any) -> str:
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return _text(value)


def _text(value: Any) -> str:
    if value is None or value == "":
        return "n/a"
    return str(value)
