from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.shortlist_return_block_audit import (
    load_candidate_period_returns,
    summarize_return_blocks,
)


STAGE = "simulation_shortlist_replay"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"
EVIDENCE_METRIC_MAP = {
    "full_sample_total_return": "total_return",
    "full_sample_annualized_return": "annualized_return",
    "full_sample_sharpe": "sharpe",
    "full_sample_overlap_sharpe": "overlap_autocorr_adjusted_sharpe",
    "full_sample_max_drawdown": "max_drawdown",
}


def build_simulation_shortlist_replay(
    config: dict[str, Any],
    *,
    repo_root: str | Path = ".",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    metric_tolerance: float = 0.005,
) -> dict[str, Any]:
    root = Path(repo_root)
    rows = []
    blockers: list[str] = []
    for candidate in _list(config.get("simulation_candidates")):
        row, candidate_blockers = _candidate_replay_row(
            _dict(candidate),
            repo_root=root,
            periods_per_year=periods_per_year,
            holding_period=holding_period,
            metric_tolerance=metric_tolerance,
        )
        rows.append(row)
        blockers.extend(candidate_blockers)
    return {
        "stage": STAGE,
        "safety": SAFETY,
        "thresholds": {
            "periods_per_year": float(periods_per_year),
            "holding_period": int(holding_period),
            "metric_tolerance": float(metric_tolerance),
        },
        "status": "passed" if not blockers else "blocked",
        "blockers": blockers,
        "summary": {
            "candidate_count": int(len(rows)),
            "blocked_candidate_count": int(sum(bool(row.get("blockers")) for row in rows)),
            "replayed_candidate_count": int(sum(row.get("source_exists") for row in rows)),
        },
        "rows": rows,
        "promotion_policy": {
            "promotion_allowed": False,
            "reason": "Replay verifies packaged evidence consistency only; it is not final holdout validation.",
        },
    }


def write_simulation_shortlist_replay(output_dir: str | Path, replay: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(replay)
    (output / "simulation_shortlist_replay.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(
        output / "simulation_shortlist_replay_rows.csv",
        index=False,
    )


def _candidate_replay_row(
    candidate: dict[str, Any],
    *,
    repo_root: Path,
    periods_per_year: float,
    holding_period: int,
    metric_tolerance: float,
) -> tuple[dict[str, Any], list[str]]:
    candidate_id = str(candidate.get("id") or "<unknown>")
    source = _dict(candidate.get("event_return_source"))
    evidence = _dict(candidate.get("evidence"))
    row_blockers: list[str] = []
    if not source:
        row_blockers.append(f"event_return_source_missing:{candidate_id}")
        return _missing_row(candidate_id, source, row_blockers), row_blockers
    path_text = str(source.get("path") or "")
    if not path_text:
        row_blockers.append(f"event_return_source_missing:{candidate_id}")
        return _missing_row(candidate_id, source, row_blockers), row_blockers
    path = repo_root / path_text
    if not path.exists():
        row_blockers.append(f"event_return_source_missing:{candidate_id}")
        return _missing_row(candidate_id, source, row_blockers, path=path_text), row_blockers

    event_frame = pd.read_csv(path)
    returns, resolved_column = load_candidate_period_returns(
        event_frame,
        return_column=source.get("return_column"),
        date_column=str(source.get("date_column") or "date"),
    )
    schema = _event_schema_summary(
        event_frame,
        candidate=candidate,
        candidate_id=candidate_id,
        date_column=str(source.get("date_column") or "date"),
    )
    row_blockers.extend(schema["blockers"])
    metrics = summarize_return_blocks(
        returns,
        candidate_name=candidate_id,
        return_column=resolved_column,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
    )
    row: dict[str, Any] = {
        "candidate_id": candidate_id,
        "source_path": path_text,
        "return_column": resolved_column,
        "source_exists": True,
        "period_count": metrics["period_count"],
        "date_start": metrics["date_start"],
        "date_end": metrics["date_end"],
        "actual_total_return": metrics["total_return"],
        "actual_annualized_return": metrics["annualized_return"],
        "actual_sharpe": metrics["sharpe"],
        "actual_overlap_autocorr_adjusted_sharpe": metrics["overlap_autocorr_adjusted_sharpe"],
        "actual_max_drawdown": metrics["max_drawdown"],
        "event_schema": schema,
    }
    for evidence_key, actual_key in EVIDENCE_METRIC_MAP.items():
        if evidence_key not in evidence:
            continue
        expected = _number(evidence.get(evidence_key))
        actual = _number(metrics.get(actual_key))
        diff = abs(actual - expected)
        row[f"expected_{evidence_key}"] = expected
        row[f"diff_{evidence_key}"] = diff
        if diff > float(metric_tolerance):
            row_blockers.append(f"metric_mismatch:{candidate_id}:{evidence_key}")
    row["blockers"] = row_blockers
    return _sanitize(row), row_blockers


def _event_schema_summary(
    frame: pd.DataFrame,
    *,
    candidate: dict[str, Any],
    candidate_id: str,
    date_column: str,
) -> dict[str, Any]:
    blockers: list[str] = []
    structured = _requires_structured_event(candidate)
    columns = {str(column) for column in frame.columns}
    if structured and "decision_date" not in columns:
        blockers.append(f"event_schema_missing:{candidate_id}:decision_date")
    if (candidate.get("volatility_target") or candidate.get("external_regime_overlay")) and "final_exposure" not in columns:
        blockers.append(f"event_schema_missing:{candidate_id}:final_exposure")
    if candidate.get("external_regime_overlay") and not ({"regime_guard_exposure", "final_exposure"} & columns):
        blockers.append(f"event_schema_missing:{candidate_id}:regime_guard_exposure")

    date_order_violations = 0
    if date_column in columns and "decision_date" in columns:
        dates = pd.to_datetime(frame[date_column], errors="coerce")
        decision_dates = pd.to_datetime(frame["decision_date"], errors="coerce")
        date_order_violations = int((decision_dates > dates).fillna(False).sum())
        if date_order_violations:
            blockers.append(f"event_schema_date_order:{candidate_id}")

    riskoff_multiplier_mismatch = False
    expected_multiplier = _external_riskoff_multiplier(candidate)
    observed_multiplier = None
    if expected_multiplier is not None and "riskoff_multiplier" in columns:
        observed = pd.to_numeric(frame["riskoff_multiplier"], errors="coerce").dropna()
        if not observed.empty:
            observed_multiplier = float(observed.median())
            riskoff_multiplier_mismatch = bool((observed - float(expected_multiplier)).abs().max() > 1e-9)
            if riskoff_multiplier_mismatch:
                blockers.append(f"riskoff_multiplier_mismatch:{candidate_id}")

    final_exposure_min = None
    final_exposure_max = None
    final_exposure_out_of_range = 0
    if "final_exposure" in columns:
        exposure = pd.to_numeric(frame["final_exposure"], errors="coerce")
        if exposure.notna().any():
            final_exposure_min = _number(exposure.min())
            final_exposure_max = _number(exposure.max())
            final_exposure_out_of_range = int(((exposure < 0.0) | (exposure > 2.0)).fillna(False).sum())
            if final_exposure_out_of_range:
                blockers.append(f"event_schema_exposure_out_of_range:{candidate_id}")

    return {
        "structured_candidate": bool(structured),
        "has_decision_date": bool("decision_date" in columns),
        "has_final_exposure": bool("final_exposure" in columns),
        "has_regime_guard_exposure": bool("regime_guard_exposure" in columns),
        "expected_riskoff_multiplier": expected_multiplier,
        "observed_riskoff_multiplier_median": observed_multiplier,
        "riskoff_multiplier_mismatch": riskoff_multiplier_mismatch,
        "date_order_violations": date_order_violations,
        "final_exposure_min": final_exposure_min,
        "final_exposure_max": final_exposure_max,
        "final_exposure_out_of_range": final_exposure_out_of_range,
        "blockers": blockers,
    }


def _requires_structured_event(candidate: dict[str, Any]) -> bool:
    return bool(
        candidate.get("formula")
        or candidate.get("replacement_filter")
        or candidate.get("cash_filter")
        or candidate.get("secondary_filter")
        or candidate.get("volatility_target")
        or candidate.get("external_regime_overlay")
    )


def _external_riskoff_multiplier(candidate: dict[str, Any]) -> float | None:
    overlay = _dict(candidate.get("external_regime_overlay"))
    if not overlay:
        return None
    value = overlay.get("risk_off_exposure_multiplier")
    if value is None:
        return None
    number = _number(value)
    return number if math.isfinite(number) else None


def _missing_row(
    candidate_id: str,
    source: dict[str, Any],
    blockers: list[str],
    *,
    path: str | None = None,
) -> dict[str, Any]:
    return {
        "candidate_id": candidate_id,
        "source_path": path or str(source.get("path") or ""),
        "return_column": source.get("return_column"),
        "source_exists": False,
        "blockers": blockers,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, float):
        return _number(value)
    return value
