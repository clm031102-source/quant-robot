from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()


DEFAULT_WALK_FORWARD_LEADERBOARD = Path(
    "data/reports/walk_forward_tushare_moneyflow_residual_regime/walk_forward_leaderboard.csv"
)
DEFAULT_PROMOTION_REPORT = Path(
    "data/reports/promotion_gate_tushare_moneyflow_residual_regime/promotion_report.json"
)
DEFAULT_OUTPUT = Path("docs/research/desktop_residual_regime_validation_latest.md")


def run_desktop_validation_summary(
    *,
    walk_forward_leaderboard: str | Path = DEFAULT_WALK_FORWARD_LEADERBOARD,
    promotion_report: str | Path | None = DEFAULT_PROMOTION_REPORT,
    output: str | Path = DEFAULT_OUTPUT,
    generated_at: str | None = None,
) -> Path:
    rows = _read_csv_records(Path(walk_forward_leaderboard))
    promotion = _read_optional_json(Path(promotion_report)) if promotion_report is not None else None
    markdown = build_desktop_validation_summary(rows, promotion_report=promotion, generated_at=generated_at)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def build_desktop_validation_summary(
    rows: list[dict[str, str]],
    *,
    promotion_report: dict[str, Any] | None = None,
    generated_at: str | None = None,
    max_rows: int = 10,
) -> str:
    generated = generated_at or datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    total = len(rows)
    accepted = sum(1 for row in rows if str(row.get("validation_status")) == "accepted")
    rejected = sum(1 for row in rows if str(row.get("validation_status")) == "rejected")
    lines = [
        "# Desktop Residual-Regime Validation Summary",
        "",
        f"- Generated at: {generated}",
        "- Scope: residualized moneyflow + liquidity/volatility/amount controls with regime-aware walk-forward.",
        "- Boundary: research-to-paper only; no broker connection, no account reads, no order placement.",
        f"- Cases: {total}",
        f"- Accepted: {accepted} / {total}",
        f"- Rejected: {rejected} / {total}",
        "",
        "## Top Walk-Forward Rows",
        "",
        "| Case | Status | Factor | Regime | Top N | Cost | Sharpe | Relative | Drawdown | Folds | Adj IC p |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in sorted(rows, key=_walk_forward_sort_key)[:max_rows]:
        lines.append(
            "| "
            + " | ".join(
                [
                    _text(row.get("case_id")),
                    _text(row.get("validation_status")),
                    _text(row.get("factor_name")),
                    f"regime={_text(row.get('regime_lookback'))}",
                    _text(row.get("top_n")),
                    _text(row.get("cost_bps")),
                    _metric_text(row, "mean_test_sharpe", "test_sharpe"),
                    _metric_text(row, "mean_test_relative_return", "test_relative_return"),
                    _metric_text(row, "worst_test_max_drawdown", "test_max_drawdown"),
                    f"{_text(row.get('accepted_folds'))}/{_text(row.get('folds'))}",
                    _text(row.get("adjusted_ic_p_value")),
                ]
            )
            + " |"
        )
    if promotion_report is not None:
        lines.extend(_promotion_lines(promotion_report))
    else:
        lines.extend(["", "## Promotion Gate", "", "- Promotion report: missing."])
    lines.extend(
        [
            "",
            "## Review Notes",
            "",
            "- Treat accepted rows as strict-validation evidence, not live-trading approval.",
            "- Prefer candidates that survive more than one regime lookback and do not collapse under higher cost.",
            "- Keep generated CSV/JSON reports out of Git; sync this lightweight Markdown only when it contains useful conclusions.",
        ]
    )
    return "\n".join(lines) + "\n"


def _promotion_lines(report: dict[str, Any]) -> list[str]:
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    candidates = report.get("candidates", []) if isinstance(report.get("candidates"), list) else []
    reasons = Counter(
        str(reason)
        for candidate in candidates
        if isinstance(candidate, dict)
        for reason in candidate.get("blocking_reasons", []) or []
    )
    lines = [
        "",
        "## Promotion Gate",
        "",
        f"- Blocked: {_text(summary.get('blocked'))}",
        f"- Research only: {_text(summary.get('research_only'))}",
        f"- Paper ready: {_text(summary.get('paper_ready'))}",
        f"- Manual live review: {_text(summary.get('manual_live_review'))}",
        "",
        "### Top Blocking Reasons",
        "",
    ]
    if not reasons:
        lines.append("- None reported.")
        return lines
    for reason, count in reasons.most_common(10):
        lines.append(f"- `{reason}`: {count}")
    return lines


def _read_csv_records(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _walk_forward_sort_key(row: dict[str, str]) -> tuple[int, float, str]:
    status_order = 0 if row.get("validation_status") == "accepted" else 1
    score = _float(row.get("mean_stability_score", row.get("stability_score", "")))
    sharpe = _float(row.get("mean_test_sharpe", row.get("test_sharpe", "")))
    return (status_order, -(score if score != 0.0 else sharpe), str(row.get("case_id", "")))


def _metric_text(row: dict[str, str], primary: str, fallback: str) -> str:
    return _text(row.get(primary) if row.get(primary) not in (None, "") else row.get(fallback))


def _text(value: Any) -> str:
    if value is None or value == "":
        return "n/a"
    return str(value)


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Write a lightweight desktop residual-regime validation summary.")
    parser.add_argument("--walk-forward-leaderboard", default=str(DEFAULT_WALK_FORWARD_LEADERBOARD))
    parser.add_argument("--promotion-report", default=str(DEFAULT_PROMOTION_REPORT))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = run_desktop_validation_summary(
        walk_forward_leaderboard=Path(args.walk_forward_leaderboard),
        promotion_report=Path(args.promotion_report) if args.promotion_report else None,
        output=Path(args.output),
    )
    print(json.dumps({"summary": str(output)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
