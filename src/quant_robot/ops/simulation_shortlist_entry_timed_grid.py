from __future__ import annotations

import copy
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from quant_robot.ops.simulation_shortlist_entry_timed_overlay import (
    SAFETY,
    build_simulation_shortlist_entry_timed_overlay,
)


STAGE = "simulation_shortlist_entry_timed_grid"
DEFAULT_PATTERN = "*_official_template_period_returns.csv"


def discover_entry_timed_period_event_sources(
    source_dir: str | Path,
    *,
    pattern: str = DEFAULT_PATTERN,
    limit: int | None = None,
) -> tuple[Path, ...]:
    sources = sorted(Path(source_dir).glob(pattern))
    if limit is not None:
        sources = sources[: int(limit)]
    return tuple(sources)


def build_simulation_shortlist_entry_timed_grid(
    period_event_sources: Iterable[str | Path],
    *,
    candidate_prefix: str = "entry_timed",
    return_column: str = "period_return",
    date_column: str = "date",
    decision_date_column: str = "entry_date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    target_annual_vol: float = 0.06,
    lookback_events: int = 84,
    min_exposure: float = 0.25,
    max_exposure: float = 1.0,
    self_risk_window: int = 21,
    self_risk_threshold: float = 0.0,
    self_risk_exposure: float = 0.5,
    max_drawdown_limit: float = -0.30,
) -> dict[str, Any]:
    sources = tuple(Path(source) for source in period_event_sources)
    if not sources:
        raise ValueError("period_event_sources must not be empty")

    rows: list[dict[str, Any]] = []
    candidate_event_rows: dict[str, list[dict[str, Any]]] = {}
    for source in sources:
        candidate_name = _candidate_name(source, prefix=candidate_prefix)
        result = build_simulation_shortlist_entry_timed_overlay(
            source,
            candidate_name=candidate_name,
            return_column=return_column,
            date_column=date_column,
            decision_date_column=decision_date_column,
            periods_per_year=periods_per_year,
            holding_period=holding_period,
            target_annual_vol=target_annual_vol,
            lookback_events=lookback_events,
            min_exposure=min_exposure,
            max_exposure=max_exposure,
            self_risk_window=self_risk_window,
            self_risk_threshold=self_risk_threshold,
            self_risk_exposure=self_risk_exposure,
        )
        metrics = result["metrics"]
        summary = result["summary"]
        blockers = list(metrics.get("blockers", []))
        blockers.extend(result["paper_readiness"].get("blockers", []))
        if float(metrics.get("max_drawdown", 0.0)) < float(max_drawdown_limit):
            blockers.append("max_drawdown_below_limit")
        blockers = sorted(set(str(blocker) for blocker in blockers))
        row = {
            "candidate_name": candidate_name,
            "source_path": str(source),
            "paper_ready": bool(result["paper_readiness"].get("paper_ready")) and not blockers,
            "blockers": blockers,
            "period_count": int(metrics.get("period_count", 0)),
            "date_start": metrics.get("date_start"),
            "date_end": metrics.get("date_end"),
            "total_return": _number(metrics.get("total_return")),
            "annualized_return": _number(metrics.get("annualized_return")),
            "annualized_volatility": _number(metrics.get("annualized_volatility")),
            "sharpe": _number(metrics.get("sharpe")),
            "overlap_autocorr_adjusted_sharpe": _number(metrics.get("overlap_autocorr_adjusted_sharpe")),
            "max_drawdown": _number(metrics.get("max_drawdown")),
            "win_rate": _number(metrics.get("win_rate")),
            "leave_one_year_min_annualized_return": _number(
                metrics.get("leave_one_year_min_annualized_return")
            ),
            "leave_one_year_min_overlap_sharpe": _number(
                metrics.get("leave_one_year_min_overlap_sharpe")
            ),
            "best_month_log_share_of_total": _number(metrics.get("best_month_log_share_of_total")),
            "average_vol_target_exposure": _number(summary.get("average_vol_target_exposure")),
            "average_self_risk_exposure": _number(summary.get("average_self_risk_exposure")),
            "average_final_exposure": _number(summary.get("average_final_exposure")),
            "self_risk_guard_event_share": _number(summary.get("self_risk_guard_event_share")),
        }
        row["score"] = _score(row)
        rows.append(row)
        candidate_event_rows[candidate_name] = list(result.get("event_rows", []))

    rows.sort(
        key=lambda row: (
            bool(row["blockers"]),
            -float(row["score"]),
            -float(row["annualized_return"]),
            float(row["max_drawdown"]),
        )
    )
    return _sanitize(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "summary": {
                "candidate_count": len(rows),
                "paper_ready_count": sum(bool(row["paper_ready"]) for row in rows),
                "blocked_candidate_count": sum(bool(row["blockers"]) for row in rows),
                "best_candidate": rows[0]["candidate_name"] if rows else None,
            },
            "parameters": {
                "candidate_prefix": candidate_prefix,
                "return_column": return_column,
                "date_column": date_column,
                "decision_date_column": decision_date_column,
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "target_annual_vol": float(target_annual_vol),
                "lookback_events": int(lookback_events),
                "min_exposure": float(min_exposure),
                "max_exposure": float(max_exposure),
                "self_risk_window": int(self_risk_window),
                "self_risk_threshold": float(self_risk_threshold),
                "self_risk_exposure": float(self_risk_exposure),
                "max_drawdown_limit": float(max_drawdown_limit),
            },
            "rows": rows,
            "candidate_event_rows": candidate_event_rows,
        }
    )


def write_simulation_shortlist_entry_timed_grid(output_dir: str | Path, result: dict[str, Any]) -> dict[str, Any]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    events_dir = output / "events"
    events_dir.mkdir(parents=True, exist_ok=True)

    summary_result = copy.deepcopy(result)
    event_rows_by_candidate = summary_result.pop("candidate_event_rows", {})
    rows = summary_result.get("rows", [])
    for row in rows:
        candidate_name = str(row["candidate_name"])
        event_path = events_dir / f"{_safe_name(candidate_name)}_events.csv"
        row["event_output_path"] = str(event_path)
        pd.DataFrame(event_rows_by_candidate.get(candidate_name, [])).to_csv(event_path, index=False)

    (output / "simulation_shortlist_entry_timed_grid.json").write_text(
        json.dumps(_sanitize(summary_result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    csv_rows = []
    for row in rows:
        csv_row = dict(row)
        csv_row["blockers"] = ";".join(str(item) for item in row.get("blockers", []))
        csv_rows.append(csv_row)
    pd.DataFrame(csv_rows).to_csv(output / "simulation_shortlist_entry_timed_grid_rows.csv", index=False)
    return summary_result


def _candidate_name(source: Path, *, prefix: str) -> str:
    base = source.stem
    for suffix in (
        "_official_template_period_returns",
        "_period_returns",
    ):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    if prefix:
        return f"{prefix}_{base}"
    return base


def _score(row: dict[str, Any]) -> float:
    drawdown_penalty = max(0.0, abs(float(row["max_drawdown"])) - 0.30) * 10.0
    concentration_penalty = max(0.0, float(row["best_month_log_share_of_total"]) - 0.60) * 5.0
    return (
        float(row["annualized_return"]) * 100.0
        + float(row["overlap_autocorr_adjusted_sharpe"]) * 1.5
        + float(row["sharpe"]) * 0.5
        + float(row["leave_one_year_min_annualized_return"]) * 25.0
        - drawdown_penalty
        - concentration_penalty
    )


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._")
    return safe or "candidate"


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.generic):
        return _sanitize(value.item())
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
