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
DEFAULT_MARKET_REGIME_COVERAGE = Path(
    "data/reports/market_regime_coverage_tushare_moneyflow_residual_regime/market_regime_coverage_pack.json"
)
DEFAULT_DATA_QUALITY_AUDIT = Path(
    "data/reports/data_quality_gap_audit_tushare_moneyflow_residual_regime/data_quality_gap_audit.json"
)
DEFAULT_OUTPUT = Path("docs/research/desktop_residual_regime_validation_latest.md")


def run_desktop_validation_summary(
    *,
    walk_forward_leaderboard: str | Path = DEFAULT_WALK_FORWARD_LEADERBOARD,
    walk_forward_manifest: str | Path | None = None,
    promotion_report: str | Path | None = DEFAULT_PROMOTION_REPORT,
    data_quality_audit: str | Path | None = DEFAULT_DATA_QUALITY_AUDIT,
    market_regime_coverage: str | Path | None = DEFAULT_MARKET_REGIME_COVERAGE,
    output: str | Path = DEFAULT_OUTPUT,
    generated_at: str | None = None,
) -> Path:
    leaderboard_path = Path(walk_forward_leaderboard)
    rows = _read_csv_records(leaderboard_path)
    manifest_path = Path(walk_forward_manifest) if walk_forward_manifest is not None else leaderboard_path.with_name("manifest.json")
    manifest = _read_optional_json(manifest_path)
    manifest_summary = _validate_manifest_summary(rows, manifest) if manifest is not None else None
    promotion = _read_optional_json(Path(promotion_report)) if promotion_report is not None else None
    if promotion is not None:
        _validate_promotion_alignment(rows, promotion)
    data_quality = _read_optional_json(Path(data_quality_audit)) if data_quality_audit is not None else None
    regime_coverage = _read_optional_json(Path(market_regime_coverage)) if market_regime_coverage is not None else None
    markdown = build_desktop_validation_summary(
        rows,
        walk_forward_manifest_summary=manifest_summary,
        promotion_report=promotion,
        data_quality_audit=data_quality,
        market_regime_coverage=regime_coverage,
        generated_at=generated_at,
    )
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    return output_path


def build_desktop_validation_summary(
    rows: list[dict[str, str]],
    *,
    walk_forward_manifest_summary: dict[str, int] | None = None,
    promotion_report: dict[str, Any] | None = None,
    data_quality_audit: dict[str, Any] | None = None,
    market_regime_coverage: dict[str, Any] | None = None,
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
        f"- Walk-forward manifest: {'verified' if walk_forward_manifest_summary is not None else 'missing'}",
        "",
        "## Top Walk-Forward Rows",
        "",
        "| Case | Status | Factor | Regime | Top N | Cost | Sharpe | Adj Sharpe | Eff N | Overlap | Relative | Drawdown | Folds | Adj IC p | Tail IC p | Tail IC status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
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
                    _text(row.get("test_overlap_autocorr_adjusted_sharpe")),
                    _text(row.get("test_overlap_effective_sample_size")),
                    _text(row.get("test_overlap_risk_flag")),
                    _metric_text(row, "mean_test_relative_return", "test_relative_return"),
                    _metric_text(row, "worst_test_max_drawdown", "test_max_drawdown"),
                    f"{_text(row.get('accepted_folds'))}/{_text(row.get('folds'))}",
                    _text(row.get("adjusted_ic_p_value")),
                    _text(row.get("test_tail_ic_p_value")),
                    _text(row.get("test_tail_significance_status")),
                ]
            )
            + " |"
        )
    if promotion_report is not None:
        lines.extend(_promotion_lines(promotion_report))
    else:
        lines.extend(["", "## Promotion Gate", "", "- Promotion report: missing."])
    lines.extend(_data_quality_lines(data_quality_audit))
    lines.extend(_market_regime_lines(market_regime_coverage))
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


def _data_quality_lines(report: dict[str, Any] | None) -> list[str]:
    if report is None:
        return ["", "## Data Quality", "", "- Data-quality audit: missing."]
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    repair_actions = report.get("repair_actions", []) if isinstance(report.get("repair_actions"), list) else []
    actions = [
        str(action.get("action"))
        for action in repair_actions
        if isinstance(action, dict) and action.get("action")
    ]
    lines = [
        "",
        "## Data Quality",
        "",
        f"- Assets: {_text(summary.get('assets'))}",
        f"- Missing date rows: {_text(summary.get('missing_date_rows'))}",
        f"- Duplicate bars: {_text(summary.get('duplicate_bars'))}",
        f"- Zero-volume rows: {_text(summary.get('zero_volume_rows'))}",
        "",
        "### Repair Actions",
        "",
    ]
    if actions:
        lines.extend(f"- `{action}`" for action in actions[:10])
    else:
        lines.append("- None reported.")
    return lines


def _market_regime_lines(report: dict[str, Any] | None) -> list[str]:
    if report is None:
        return ["", "## Market Regime Coverage", "", "- Coverage report: missing."]
    summary = report.get("summary", {}) if isinstance(report.get("summary"), dict) else {}
    decision = report.get("decision", {}) if isinstance(report.get("decision"), dict) else {}
    blockers = [str(item) for item in decision.get("blockers", []) or []]
    regimes = [str(item) for item in summary.get("regimes", []) or []]
    lines = [
        "",
        "## Market Regime Coverage",
        "",
        f"- Status: {_text(report.get('status'))}",
        f"- Covered regimes: {_text(summary.get('covered_regimes'))}",
        f"- Allowed rows: {_text(summary.get('allowed_rows'))}",
        f"- Blocked rows: {_text(summary.get('blocked_rows'))}",
        f"- Regimes: {', '.join(regimes) if regimes else 'n/a'}",
        "",
        "### Regime Blockers",
        "",
    ]
    if blockers:
        lines.extend(f"- `{blocker}`" for blocker in blockers)
    else:
        lines.append("- None reported.")
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


def _validate_manifest_summary(rows: list[dict[str, str]], manifest: dict[str, Any]) -> dict[str, int]:
    summary = manifest.get("summary", {})
    if not isinstance(summary, dict):
        raise ValueError("walk-forward manifest must contain a summary object")
    actual = {
        "cases": len(rows),
        "accepted": sum(1 for row in rows if str(row.get("validation_status")) == "accepted"),
        "rejected": sum(1 for row in rows if str(row.get("validation_status")) == "rejected"),
    }
    expected = {key: int(summary.get(key, 0)) for key in actual}
    if actual != expected:
        raise ValueError(
            "walk-forward manifest summary does not match leaderboard: "
            f"manifest={expected}, leaderboard={actual}"
        )
    return expected


def _validate_promotion_alignment(rows: list[dict[str, str]], report: dict[str, Any]) -> None:
    candidates = report.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("promotion report candidates must be a list")
    leaderboard_cases = {str(row.get("case_id")) for row in rows if row.get("case_id")}
    promotion_cases = {
        str(candidate.get("case_id"))
        for candidate in candidates
        if isinstance(candidate, dict) and candidate.get("case_id")
    }
    if leaderboard_cases != promotion_cases:
        missing = sorted(leaderboard_cases - promotion_cases)[:10]
        extra = sorted(promotion_cases - leaderboard_cases)[:10]
        raise ValueError(
            "promotion report candidates do not match leaderboard: "
            f"missing={missing}, extra={extra}"
        )


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
    parser.add_argument("--walk-forward-manifest", default=None)
    parser.add_argument("--promotion-report", default=str(DEFAULT_PROMOTION_REPORT))
    parser.add_argument("--data-quality-audit", default=str(DEFAULT_DATA_QUALITY_AUDIT))
    parser.add_argument("--market-regime-coverage", default=str(DEFAULT_MARKET_REGIME_COVERAGE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = run_desktop_validation_summary(
        walk_forward_leaderboard=Path(args.walk_forward_leaderboard),
        walk_forward_manifest=Path(args.walk_forward_manifest) if args.walk_forward_manifest else None,
        promotion_report=Path(args.promotion_report) if args.promotion_report else None,
        data_quality_audit=Path(args.data_quality_audit) if args.data_quality_audit else None,
        market_regime_coverage=Path(args.market_regime_coverage) if args.market_regime_coverage else None,
        output=Path(args.output),
    )
    print(json.dumps({"summary": str(output)}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
