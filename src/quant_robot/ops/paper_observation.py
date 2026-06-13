from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_3_3_paper_observation_extension"


def build_paper_observation_pack(
    paper_batch: dict[str, Any],
    candidate_artifacts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    artifacts = candidate_artifacts or {}
    candidates = [
        _candidate_observation(index + 1, row, artifacts.get(str(row.get("case_id")), {}))
        for index, row in enumerate(_list(paper_batch.get("candidates", [])))
        if isinstance(row, dict)
    ]
    pack = {
        "stage": STAGE,
        "safety": _research_only_safety(),
        "summary": _summary(candidates, paper_batch.get("summary", {})),
        "candidates": candidates,
        "risk_profile_comparison": _risk_profile_comparison(candidates),
        "metric_trend": _metric_trend(candidates),
    }
    pack["markdown"] = render_paper_observation_markdown(pack)
    return pack


def write_paper_observation_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "paper_observation_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "paper_observation_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("candidates", [])).to_csv(output_path / "paper_observation_candidates.csv", index=False)
    pd.DataFrame(pack.get("risk_profile_comparison", [])).to_csv(output_path / "paper_observation_risk_profiles.csv", index=False)
    pd.DataFrame(pack.get("metric_trend", [])).to_csv(output_path / "paper_observation_trend.csv", index=False)


def render_paper_observation_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    lines = [
        "# Phase 3.3 Paper Observation Extension",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Safety: {pack.get('safety', _research_only_safety())}",
        f"- Completed candidates: {summary.get('completed_candidates', 0)}",
        f"- Observed candidates: {summary.get('observed_candidates', 0)}",
        f"- Observation window: {summary.get('observation_start', 'none')} to {summary.get('observation_end', 'none')}",
        "",
        "## Candidate Observation",
        "",
        "| Rank | Case | Status | Risk Profile | Sharpe | Max Drawdown | Guard Events | Window |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in pack.get("candidates", []):
        if isinstance(row, dict):
            window = row.get("observation_window", {}) if isinstance(row.get("observation_window"), dict) else {}
            lines.append(
                "| "
                f"{row.get('observation_rank', '')} | "
                f"{row.get('case_id', 'unknown')} | "
                f"{row.get('observation_status', 'unknown')} | "
                f"{row.get('risk_profile_id', 'none')} | "
                f"{_round(row.get('sharpe'))} | "
                f"{_round(row.get('max_equity_drawdown'))} | "
                f"{row.get('guard_summary', {}).get('guard_events', 0) if isinstance(row.get('guard_summary'), dict) else 0} | "
                f"{window.get('start_date', 'none')} to {window.get('end_date', 'none')} |"
            )
    lines.extend(
        [
            "",
            "## Risk Profiles",
            "",
            "| Risk Profile | Completed | Observed | Avg Sharpe | Worst Drawdown | Guard Events |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in pack.get("risk_profile_comparison", []):
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('risk_profile_id', 'none')} | "
                f"{row.get('completed_candidates', 0)} | "
                f"{row.get('observed_candidates', 0)} | "
                f"{_round(row.get('average_sharpe'))} | "
                f"{_round(row.get('worst_drawdown'))} | "
                f"{row.get('total_guard_events', 0)} |"
            )
    return "\n".join(lines) + "\n"


def _candidate_observation(rank: int, row: dict[str, Any], artifacts: dict[str, Any]) -> dict[str, Any]:
    manifest = artifacts.get("manifest", {}) if isinstance(artifacts.get("manifest"), dict) else {}
    metrics = manifest.get("metrics", {}) if isinstance(manifest.get("metrics"), dict) else {}
    request = manifest.get("request", {}) if isinstance(manifest.get("request"), dict) else {}
    equity_curve = _records(artifacts.get("equity_curve", []))
    guard_events = _records(artifacts.get("guard_events", []))
    execution_events = _records(artifacts.get("execution_events", []))
    status = str(row.get("status", "unknown"))
    window = _observation_window(equity_curve)
    observation_status = _observation_status(status, window)
    return {
        "observation_rank": rank,
        "case_id": str(row.get("case_id", "unknown")),
        "market": row.get("market") or request.get("market"),
        "factor_name": row.get("factor_name") or request.get("factor_name"),
        "status": status,
        "observation_status": observation_status,
        "risk_profile_id": row.get("risk_profile_id") or request.get("risk_profile_id"),
        "attempted_profiles": _int(row.get("attempted_profiles"), 0),
        "data_mode": manifest.get("data_mode"),
        "manifest_path": row.get("manifest_path"),
        "output_dir": row.get("output_dir"),
        "total_return": _metric(metrics, row, "total_return"),
        "sharpe": _metric(metrics, row, "sharpe"),
        "max_equity_drawdown": _metric(metrics, row, "max_equity_drawdown", fallback_key="max_drawdown"),
        "fills": _int(row.get("fills"), 0),
        "observation_window": window,
        "guard_summary": _guard_summary(guard_events, row),
        "execution_summary": _execution_summary(execution_events),
    }


def _summary(candidates: list[dict[str, Any]], batch_summary: Any) -> dict[str, Any]:
    status_counts = Counter(str(row.get("status", "unknown")) for row in candidates)
    windows = [
        row.get("observation_window", {})
        for row in candidates
        if isinstance(row.get("observation_window"), dict) and row.get("observation_window", {}).get("start_date")
    ]
    starts = [str(window["start_date"]) for window in windows]
    ends = [str(window["end_date"]) for window in windows if window.get("end_date")]
    source = batch_summary if isinstance(batch_summary, dict) else {}
    return {
        "candidates": len(candidates) or _int(source.get("cases"), 0),
        "completed_candidates": status_counts.get("completed", _int(source.get("completed"), 0)),
        "failed_candidates": status_counts.get("failed", _int(source.get("failed"), 0)),
        "skipped_candidates": status_counts.get("skipped", _int(source.get("skipped"), 0)),
        "observed_candidates": sum(1 for row in candidates if row.get("observation_status") == "observed"),
        "risk_profiles": len({row.get("risk_profile_id") for row in candidates if row.get("risk_profile_id")}),
        "observation_start": min(starts) if starts else None,
        "observation_end": max(ends) if ends else None,
        "total_guard_events": sum(_int(row.get("guard_summary", {}).get("guard_events"), 0) for row in candidates if isinstance(row.get("guard_summary"), dict)),
        "total_execution_events": sum(_int(row.get("execution_summary", {}).get("execution_events"), 0) for row in candidates if isinstance(row.get("execution_summary"), dict)),
    }


def _risk_profile_comparison(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        if row.get("status") == "completed" and row.get("risk_profile_id"):
            groups[str(row["risk_profile_id"])].append(row)
    rows = []
    for profile_id, items in groups.items():
        rows.append(
            {
                "risk_profile_id": profile_id,
                "completed_candidates": len(items),
                "observed_candidates": sum(1 for row in items if row.get("observation_status") == "observed"),
                "average_sharpe": _average(row.get("sharpe") for row in items),
                "average_total_return": _average(row.get("total_return") for row in items),
                "worst_drawdown": min((_float(row.get("max_equity_drawdown")) for row in items), default=0.0),
                "total_guard_events": sum(_int(row.get("guard_summary", {}).get("guard_events"), 0) for row in items if isinstance(row.get("guard_summary"), dict)),
                "total_execution_events": sum(_int(row.get("execution_summary", {}).get("execution_events"), 0) for row in items if isinstance(row.get("execution_summary"), dict)),
            }
        )
    return sorted(rows, key=lambda row: (-row["completed_candidates"], str(row["risk_profile_id"])))


def _metric_trend(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in candidates:
        if row.get("status") != "completed":
            continue
        window = row.get("observation_window", {}) if isinstance(row.get("observation_window"), dict) else {}
        guard = row.get("guard_summary", {}) if isinstance(row.get("guard_summary"), dict) else {}
        execution = row.get("execution_summary", {}) if isinstance(row.get("execution_summary"), dict) else {}
        rows.append(
            {
                "observation_rank": row.get("observation_rank"),
                "case_id": row.get("case_id"),
                "risk_profile_id": row.get("risk_profile_id"),
                "sharpe": row.get("sharpe"),
                "total_return": row.get("total_return"),
                "max_equity_drawdown": row.get("max_equity_drawdown"),
                "guard_events": guard.get("guard_events", 0),
                "execution_events": execution.get("execution_events", 0),
                "equity_points": window.get("equity_points", 0),
                "observation_start": window.get("start_date"),
                "observation_end": window.get("end_date"),
                "observation_status": row.get("observation_status"),
            }
        )
    return rows


def _observation_window(equity_curve: list[dict[str, Any]]) -> dict[str, Any]:
    dates = sorted(str(row.get("date")) for row in equity_curve if row.get("date"))
    if not dates:
        return {"start_date": None, "end_date": None, "equity_points": 0, "calendar_days": 0}
    return {
        "start_date": dates[0],
        "end_date": dates[-1],
        "equity_points": len(dates),
        "calendar_days": _calendar_days(dates[0], dates[-1]),
    }


def _guard_summary(guard_events: list[dict[str, Any]], row: dict[str, Any]) -> dict[str, Any]:
    count = len(guard_events) if guard_events else _int(row.get("guard_events"), 0)
    return {
        "guard_events": count,
        "trigger_events": sum(1 for event in guard_events if str(event.get("event_type")) == "drawdown_guard_triggered"),
        "blocked_buy_events": sum(1 for event in guard_events if str(event.get("event_type")) == "drawdown_guard_blocked_buys"),
        "total_blocked_buy_intents": sum(_int(event.get("blocked_buy_intents"), 0) for event in guard_events),
    }


def _execution_summary(execution_events: list[dict[str, Any]]) -> dict[str, Any]:
    reasons = Counter(str(event.get("blocked_reason") or event.get("reason") or "unknown") for event in execution_events)
    return {"execution_events": len(execution_events), "by_reason": dict(sorted(reasons.items()))}


def _observation_status(status: str, window: dict[str, Any]) -> str:
    if status != "completed":
        return status
    if _int(window.get("equity_points"), 0) > 0:
        return "observed"
    return "missing_observation_artifacts"


def _metric(metrics: dict[str, Any], row: dict[str, Any], key: str, fallback_key: str | None = None) -> float:
    if key in metrics:
        return _float(metrics.get(key))
    if fallback_key is not None and fallback_key in metrics:
        return _float(metrics.get(fallback_key))
    if key in row:
        return _float(row.get(key))
    if fallback_key is not None and fallback_key in row:
        return _float(row.get(fallback_key))
    return 0.0


def _records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _average(values: Any) -> float:
    numbers = [_float(value) for value in values]
    return sum(numbers) / len(numbers) if numbers else 0.0


def _calendar_days(start: str, end: str) -> int:
    try:
        left = date.fromisoformat(start[:10])
        right = date.fromisoformat(end[:10])
    except ValueError:
        return 0
    return (right - left).days + 1


def _float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _round(value: Any) -> str:
    return f"{_float(value):.4f}"


def _research_only_safety() -> str:
    return "Research only. No broker connection, no account reads, no order placement, no live trading."
