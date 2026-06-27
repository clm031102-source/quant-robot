from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_return_block_audit import (
    load_candidate_period_returns,
    summarize_return_blocks,
)


STAGE = "simulation_paper_handoff"
SAFETY = "research-to-paper only; no broker, account, order, or live-trading access"
ROLE_PRIORITY = {
    "default_10bps": 0,
    "heavier_cost_20bps": 1,
    "stress_fallback_30bps": 2,
    "diagnostic": 3,
    "research_reference": 9,
}


def build_simulation_paper_handoff(
    config: dict[str, Any],
    *,
    repo_root: str | Path = ".",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    max_user_drawdown: float = -0.30,
    min_oos_strict_pass_rate: float = 0.75,
    require_event_files: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root)
    rows = [
        _candidate_row(
            _dict(candidate),
            repo_root=root,
            periods_per_year=periods_per_year,
            holding_period=holding_period,
            max_user_drawdown=-abs(_number(max_user_drawdown, -0.30)),
            min_oos_strict_pass_rate=min_oos_strict_pass_rate,
            require_event_files=require_event_files,
        )
        for candidate in _handoff_candidates(config)
    ]
    rows = sorted(rows, key=lambda row: (_role_priority(row), row["handoff_status"] == "blocked", str(row["candidate_id"])))
    ready_rows = [row for row in rows if row["handoff_status"] == "ready_for_paper_simulation"]
    blocked_rows = [row for row in rows if row["handoff_status"] == "blocked"]
    default_row = next((row for row in ready_rows if row.get("role") == "default_10bps"), ready_rows[0] if ready_rows else None)
    high_return_row = max(ready_rows, key=_high_return_priority, default=None)
    return _sanitize(
        {
            "stage": STAGE,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "safety": SAFETY,
            "thresholds": {
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "max_user_drawdown": -abs(_number(max_user_drawdown, -0.30)),
                "min_oos_strict_pass_rate": float(min_oos_strict_pass_rate),
                "require_event_files": bool(require_event_files),
                "eligibility": [
                    "evidence.paper_ready must be true",
                    "status/id must identify a cohort entry-timed candidate",
                    "event source must exist and replay into positive full-sample metrics",
                    "max drawdown must stay within user limit",
                    "OOS strict pass rate must meet the minimum",
                ],
            },
            "summary": {
                "candidate_count": len(rows),
                "ready_candidate_count": len(ready_rows),
                "blocked_candidate_count": len(blocked_rows),
                "default_candidate_id": default_row["candidate_id"] if default_row else None,
                "primary_high_return_candidate_id": high_return_row["candidate_id"] if high_return_row else None,
                "primary_high_return_annualized_return": _row_metric(
                    high_return_row,
                    "computed_annualized_return",
                    "evidence_annualized_return",
                ),
                "primary_high_return_total_return": _row_metric(high_return_row, "computed_total_return"),
                "primary_high_return_max_drawdown": _row_metric(
                    high_return_row,
                    "computed_max_drawdown",
                    "evidence_max_drawdown",
                ),
            },
            "candidates": rows,
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "This is a paper-simulation handoff only; 2026 final holdout remains sealed.",
            },
        }
    )


def write_simulation_paper_handoff(output_dir: str | Path, handoff: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(handoff)
    (output / "simulation_paper_handoff.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("candidates", [])).to_csv(
        output / "simulation_paper_handoff_candidates.csv",
        index=False,
    )
    (output / "simulation_paper_handoff.md").write_text(_render_markdown(sanitized), encoding="utf-8")


def _handoff_candidates(config: dict[str, Any]) -> list[Any]:
    explicit = _list(config.get("paper_simulation_handoff_candidates"))
    if explicit:
        return explicit
    return [
        candidate
        for candidate in _list(config.get("simulation_candidates"))
        if "cohort" in str(_dict(candidate).get("id") or "").lower()
        or "cohort" in str(_dict(candidate).get("status") or "").lower()
    ]


def _candidate_row(
    candidate: dict[str, Any],
    *,
    repo_root: Path,
    periods_per_year: float,
    holding_period: int,
    max_user_drawdown: float,
    min_oos_strict_pass_rate: float,
    require_event_files: bool,
) -> dict[str, Any]:
    candidate_id = str(candidate.get("id") or "<unknown>")
    source = _dict(candidate.get("event_return_source"))
    evidence = _dict(candidate.get("evidence"))
    status = str(candidate.get("status") or "")
    source_path = str(source.get("path") or "")
    blockers: list[str] = []
    metrics: dict[str, Any] = {}
    resolved_column: str | None = None

    if not _is_true_cohort_candidate(candidate_id, status):
        blockers.append("not_true_cohort_entry_timed_candidate")
    if evidence.get("paper_ready") is not True:
        blockers.append("not_paper_ready")
    if not source_path:
        blockers.append("event_return_source_missing")
    else:
        path = Path(source_path)
        if not path.is_absolute():
            path = repo_root / source_path
        if not path.exists():
            blockers.append("event_return_source_missing")
        elif require_event_files:
            try:
                returns_frame, resolved_column = load_candidate_period_returns(
                    path,
                    return_column=str(source.get("return_column")) if source.get("return_column") else None,
                    date_column=str(source.get("date_column") or "date"),
                )
                metrics = summarize_return_blocks(
                    returns_frame,
                    candidate_name=candidate_id,
                    return_column=resolved_column,
                    periods_per_year=periods_per_year,
                    holding_period=holding_period,
                )
            except (OSError, ValueError, pd.errors.ParserError) as exc:
                blockers.append(f"event_return_source_unreadable:{type(exc).__name__}")

    actual_total = _optional_number(metrics.get("total_return"))
    actual_ann = _optional_number(metrics.get("annualized_return"))
    actual_drawdown = _optional_number(metrics.get("max_drawdown"))
    evidence_ann = _optional_number(evidence.get("full_sample_annualized_return"))
    evidence_drawdown = _optional_number(evidence.get("full_sample_max_drawdown"))
    oos_ann = _optional_number(evidence.get("mean_oos_annualized_return"))
    strict_pass = _optional_number(evidence.get("oos_strict_pass_rate"))
    hedged_ann = _optional_number(evidence.get("csi500_beta_hedged_annualized_return"))
    hedged_drawdown = _optional_number(evidence.get("csi500_beta_hedged_max_drawdown"))

    annualized_for_gate = actual_ann if actual_ann is not None else evidence_ann
    drawdown_for_gate = actual_drawdown if actual_drawdown is not None else evidence_drawdown
    if actual_total is not None and actual_total <= 0.0:
        blockers.append("non_positive_total_return")
    if annualized_for_gate is None or annualized_for_gate <= 0.0:
        blockers.append("non_positive_annualized_return")
    if drawdown_for_gate is None:
        blockers.append("max_drawdown_missing")
    elif drawdown_for_gate < max_user_drawdown:
        blockers.append("drawdown_below_user_limit")
    if oos_ann is not None and oos_ann <= 0.0:
        blockers.append("mean_oos_annualized_return_non_positive")
    if strict_pass is None:
        blockers.append("oos_strict_pass_rate_missing")
    elif strict_pass < min_oos_strict_pass_rate:
        blockers.append("oos_strict_pass_rate_below_min")
    if hedged_ann is not None and hedged_ann <= 0.0:
        blockers.append("beta_hedged_annualized_return_non_positive")
    if hedged_drawdown is not None and hedged_drawdown < max_user_drawdown:
        blockers.append("beta_hedged_drawdown_below_user_limit")

    return _sanitize(
        {
            "candidate_id": candidate_id,
            "role": str(candidate.get("role") or "diagnostic"),
            "status": status,
            "handoff_status": "blocked" if blockers else "ready_for_paper_simulation",
            "blockers": sorted(set(blockers)),
            "cost_rate": _optional_number(candidate.get("cost_rate")),
            "formula": candidate.get("formula"),
            "source_path": source_path,
            "return_column": resolved_column or source.get("return_column"),
            "period_count": metrics.get("period_count"),
            "date_start": metrics.get("date_start"),
            "date_end": metrics.get("date_end"),
            "computed_total_return": actual_total,
            "computed_annualized_return": actual_ann,
            "computed_sharpe": _optional_number(metrics.get("sharpe")),
            "computed_overlap_sharpe": _optional_number(metrics.get("overlap_autocorr_adjusted_sharpe")),
            "computed_max_drawdown": actual_drawdown,
            "computed_win_rate": _optional_number(metrics.get("win_rate")),
            "evidence_annualized_return": evidence_ann,
            "evidence_max_drawdown": evidence_drawdown,
            "mean_oos_annualized_return": oos_ann,
            "oos_strict_pass_rate": strict_pass,
            "csi500_beta_hedged_annualized_return": hedged_ann,
            "csi500_beta_hedged_max_drawdown": hedged_drawdown,
        }
    )


def _is_true_cohort_candidate(candidate_id: str, status: str) -> bool:
    text = f"{candidate_id} {status}".lower()
    return "cohort" in text and "entry_timed" in text and "not_paper_ready" not in text


def _render_markdown(handoff: dict[str, Any]) -> str:
    summary = _dict(handoff.get("summary"))
    lines = [
        "# Simulation Paper Handoff",
        "",
        f"Stage: `{handoff.get('stage')}`",
        "",
        f"Default candidate: `{summary.get('default_candidate_id')}`",
        "",
        f"Primary high-return candidate: `{summary.get('primary_high_return_candidate_id')}`",
        "",
        "| Candidate | Role | Status | Ann | MaxDD | OOS pass | Blockers |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in _list(handoff.get("candidates")):
        item = _dict(row)
        ann = _optional_number(item.get("computed_annualized_return"))
        if ann is None:
            ann = _optional_number(item.get("evidence_annualized_return"))
        drawdown = _optional_number(item.get("computed_max_drawdown"))
        if drawdown is None:
            drawdown = _optional_number(item.get("evidence_max_drawdown"))
        blockers = ", ".join(str(value) for value in _list(item.get("blockers"))) or "-"
        lines.append(
            "| `{}` | `{}` | `{}` | {} | {} | {} | {} |".format(
                item.get("candidate_id"),
                item.get("role"),
                item.get("handoff_status"),
                _fmt_pct(ann),
                _fmt_pct(drawdown),
                _fmt_pct(_optional_number(item.get("oos_strict_pass_rate"))),
                blockers,
            )
        )
    lines.extend(
        [
            "",
            "Policy: research-to-paper only. Final holdout remains sealed; no broker, account, order, or live-trading boundary is crossed.",
            "",
        ]
    )
    return "\n".join(lines)


def _role_priority(row: dict[str, Any]) -> tuple[int, str]:
    role = str(row.get("role") or "")
    return ROLE_PRIORITY.get(role, 5), str(row.get("candidate_id") or "")


def _high_return_priority(row: dict[str, Any]) -> tuple[float, float, float]:
    return (
        _row_metric(row, "computed_annualized_return", "evidence_annualized_return") or -math.inf,
        _row_metric(row, "computed_total_return") or -math.inf,
        _row_metric(row, "computed_overlap_sharpe") or -math.inf,
    )


def _row_metric(row: dict[str, Any] | None, *keys: str) -> float | None:
    if row is None:
        return None
    for key in keys:
        value = _optional_number(row.get(key))
        if value is not None:
            return value
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _optional_number(value: Any) -> float | None:
    if value is None:
        return None
    number = _number(value, default=math.nan)
    return number if math.isfinite(number) else None


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value * 100:.2f}%"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _number(value)
    if isinstance(value, float):
        return _number(value)
    return value
