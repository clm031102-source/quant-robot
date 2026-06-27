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


STAGE = "simulation_shortlist_ranker"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


def build_simulation_shortlist_ranking(
    config: dict[str, Any],
    *,
    repo_root: str | Path = ".",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    max_user_drawdown: float = -0.30,
    min_oos_strict_pass_rate: float = 0.75,
    duplicate_correlation: float = 0.98,
) -> dict[str, Any]:
    root = Path(repo_root)
    rows: list[dict[str, Any]] = []
    return_streams: dict[str, pd.Series] = {}
    for candidate in _list(config.get("simulation_candidates")):
        row, returns = _candidate_row(
            _dict(candidate),
            repo_root=root,
            periods_per_year=periods_per_year,
            holding_period=holding_period,
            max_user_drawdown=-abs(_number(max_user_drawdown, -0.30)),
            min_oos_strict_pass_rate=min_oos_strict_pass_rate,
        )
        rows.append(row)
        if returns is not None and row["selection_status"] != "blocked":
            return_streams[row["candidate_id"]] = returns

    rows = _apply_duplicate_marks(rows, return_streams, duplicate_correlation=duplicate_correlation)
    rows = sorted(
        rows,
        key=lambda row: (
            row["selection_status"] not in {"simulation_observation_candidate"},
            row["selection_status"] == "duplicate",
            -_number(row.get("score")),
            str(row.get("candidate_id")),
        ),
    )
    eligible_rows = [row for row in rows if row["selection_status"] == "simulation_observation_candidate"]
    duplicate_rows = [row for row in rows if row["selection_status"] == "duplicate"]
    blocked_rows = [row for row in rows if row["selection_status"] == "blocked"]
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
                "duplicate_correlation": float(duplicate_correlation),
            },
            "summary": {
                "candidate_count": len(rows),
                "eligible_candidate_count": len(eligible_rows),
                "duplicate_candidate_count": len(duplicate_rows),
                "blocked_candidate_count": len(blocked_rows),
                "best_candidate": eligible_rows[0]["candidate_id"] if eligible_rows else None,
            },
            "rows": rows,
            "correlations": _pairwise_correlations(return_streams),
            "promotion_policy": {
                "promotion_allowed": False,
                "reason": "Ranking is a simulation-readiness audit; final holdout remains sealed and no live boundary is crossed.",
            },
        }
    )


def write_simulation_shortlist_ranking(output_dir: str | Path, ranking: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize(ranking)
    (output / "simulation_shortlist_ranking.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized.get("rows", [])).to_csv(output / "simulation_shortlist_ranking_rows.csv", index=False)
    pd.DataFrame(sanitized.get("correlations", [])).to_csv(
        output / "simulation_shortlist_return_correlations.csv",
        index=False,
    )


def _candidate_row(
    candidate: dict[str, Any],
    *,
    repo_root: Path,
    periods_per_year: float,
    holding_period: int,
    max_user_drawdown: float,
    min_oos_strict_pass_rate: float,
) -> tuple[dict[str, Any], pd.Series | None]:
    candidate_id = str(candidate.get("id") or "<unknown>")
    source = _dict(candidate.get("event_return_source"))
    evidence = _dict(candidate.get("evidence"))
    blockers: list[str] = []
    path_text = str(source.get("path") or "")
    if not path_text:
        blockers.append("event_return_source_missing")
        return _blocked_row(candidate_id, candidate, evidence, blockers), None
    path = Path(path_text)
    if not path.is_absolute():
        path = repo_root / path_text
    if not path.exists():
        blockers.append("event_return_source_missing")
        return _blocked_row(candidate_id, candidate, evidence, blockers, source_path=path_text), None

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
    actual_drawdown = _number(metrics.get("max_drawdown"))
    actual_ann = _number(metrics.get("annualized_return"))
    total_return = _number(metrics.get("total_return"))
    mean_oos_ann = _number(evidence.get("mean_oos_annualized_return"))
    oos_strict_pass = _optional_number(evidence.get("oos_strict_pass_rate"))
    beta_hedged_ann = _optional_number(evidence.get("csi500_beta_hedged_annualized_return"))
    beta_hedged_drawdown = _optional_number(evidence.get("csi500_beta_hedged_max_drawdown"))
    explicit_paper_ready = evidence.get("paper_ready")

    if explicit_paper_ready is False and "not_paper_ready" in str(candidate.get("status") or ""):
        blockers.append("not_paper_ready")
    if total_return <= 0.0:
        blockers.append("non_positive_total_return")
    if actual_ann <= 0.0:
        blockers.append("non_positive_annualized_return")
    if actual_drawdown < max_user_drawdown:
        blockers.append("drawdown_below_user_limit")
    if "mean_oos_annualized_return" in evidence and mean_oos_ann <= 0.0:
        blockers.append("mean_oos_annualized_return_non_positive")
    if oos_strict_pass is not None and oos_strict_pass < min_oos_strict_pass_rate:
        blockers.append("oos_strict_pass_rate_below_min")
    if beta_hedged_ann is not None and beta_hedged_ann <= 0.0:
        blockers.append("beta_hedged_annualized_return_non_positive")
    if beta_hedged_drawdown is not None and beta_hedged_drawdown < max_user_drawdown:
        blockers.append("beta_hedged_drawdown_below_user_limit")

    score_components = _score_components(metrics, evidence)
    row = {
        "candidate_id": candidate_id,
        "status": candidate.get("status"),
        "source_path": path_text,
        "return_column": resolved_column,
        "paper_ready": bool(explicit_paper_ready) if explicit_paper_ready is not None else None,
        "selection_status": "blocked" if blockers else "simulation_observation_candidate",
        "duplicate_of": None,
        "blockers": blockers,
        "score": sum(score_components.values()),
        "score_components": score_components,
        "period_count": metrics.get("period_count"),
        "date_start": metrics.get("date_start"),
        "date_end": metrics.get("date_end"),
        "total_return": total_return,
        "annualized_return": actual_ann,
        "sharpe": _number(metrics.get("sharpe")),
        "overlap_autocorr_adjusted_sharpe": _number(metrics.get("overlap_autocorr_adjusted_sharpe")),
        "max_drawdown": actual_drawdown,
        "win_rate": _number(metrics.get("win_rate")),
        "leave_one_year_min_annualized_return": _number(metrics.get("leave_one_year_min_annualized_return")),
        "best_month_log_share_of_total": _number(metrics.get("best_month_log_share_of_total")),
        "mean_oos_annualized_return": mean_oos_ann,
        "mean_oos_overlap_sharpe": _optional_number(evidence.get("mean_oos_overlap_sharpe")),
        "worst_oos_drawdown": _optional_number(evidence.get("worst_oos_drawdown")),
        "oos_strict_pass_rate": oos_strict_pass,
        "csi500_beta": _optional_number(evidence.get("csi500_beta")),
        "csi500_beta_hedged_annualized_return": beta_hedged_ann,
        "csi500_beta_hedged_overlap_sharpe": _optional_number(evidence.get("csi500_beta_hedged_overlap_sharpe")),
        "csi500_beta_hedged_max_drawdown": beta_hedged_drawdown,
    }
    return _sanitize(row), _return_series(returns_frame)


def _blocked_row(
    candidate_id: str,
    candidate: dict[str, Any],
    evidence: dict[str, Any],
    blockers: list[str],
    *,
    source_path: str = "",
) -> dict[str, Any]:
    return _sanitize(
        {
            "candidate_id": candidate_id,
            "status": candidate.get("status"),
            "source_path": source_path,
            "selection_status": "blocked",
            "duplicate_of": None,
            "blockers": blockers,
            "score": -999.0,
            "score_components": {},
            "mean_oos_annualized_return": _optional_number(evidence.get("mean_oos_annualized_return")),
            "oos_strict_pass_rate": _optional_number(evidence.get("oos_strict_pass_rate")),
        }
    )


def _score_components(metrics: dict[str, Any], evidence: dict[str, Any]) -> dict[str, float]:
    annualized = _number(metrics.get("annualized_return"))
    total = _number(metrics.get("total_return"))
    overlap = _number(metrics.get("overlap_autocorr_adjusted_sharpe"))
    sharpe = _number(metrics.get("sharpe"))
    drawdown = _number(metrics.get("max_drawdown"))
    mean_oos = _number(evidence.get("mean_oos_annualized_return"))
    strict_pass = _number(evidence.get("oos_strict_pass_rate"))
    hedged_ann = _number(evidence.get("csi500_beta_hedged_annualized_return"))
    hedged_overlap = _number(evidence.get("csi500_beta_hedged_overlap_sharpe"))
    hedged_drawdown = _number(evidence.get("csi500_beta_hedged_max_drawdown"))
    return {
        "annualized_return": annualized * 100.0,
        "mean_oos_annualized_return": mean_oos * 80.0,
        "beta_hedged_annualized_return": hedged_ann * 70.0,
        "overlap_autocorr_adjusted_sharpe": overlap * 1.5,
        "beta_hedged_overlap_sharpe": hedged_overlap * 1.0,
        "sharpe": sharpe * 0.5,
        "oos_strict_pass_rate": strict_pass * 2.0,
        "total_return": total * 0.5,
        "max_drawdown": drawdown * 2.0,
        "beta_hedged_max_drawdown": hedged_drawdown * 1.0,
    }


def _apply_duplicate_marks(
    rows: list[dict[str, Any]],
    return_streams: dict[str, pd.Series],
    *,
    duplicate_correlation: float,
) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda row: (_duplicate_priority(row), -_number(row.get("score"))))
    canonical_ids: list[str] = []
    by_id = {str(row.get("candidate_id")): row for row in ranked}
    for row in ranked:
        candidate_id = str(row.get("candidate_id"))
        if row.get("selection_status") == "blocked":
            continue
        duplicate_of = None
        for canonical_id in canonical_ids:
            corr = _correlation(return_streams.get(candidate_id), return_streams.get(canonical_id))
            if corr is not None and corr >= float(duplicate_correlation):
                duplicate_of = canonical_id
                break
        if duplicate_of:
            row["selection_status"] = "duplicate"
            row["duplicate_of"] = duplicate_of
            blockers = list(row.get("blockers") or [])
            blockers.append("near_duplicate_return_stream")
            row["blockers"] = blockers
        else:
            canonical_ids.append(candidate_id)
    return [_sanitize(by_id[str(row.get("candidate_id"))]) for row in rows]


def _duplicate_priority(row: dict[str, Any]) -> int:
    status = str(row.get("status") or "")
    if row.get("paper_ready") is True or status.startswith("paper_simulation"):
        return 0
    if "not_paper_ready" in status:
        return 2
    return 1


def _pairwise_correlations(return_streams: dict[str, pd.Series]) -> list[dict[str, Any]]:
    ids = sorted(return_streams)
    rows = []
    for left_index, left_id in enumerate(ids):
        for right_id in ids[left_index + 1 :]:
            corr = _correlation(return_streams.get(left_id), return_streams.get(right_id))
            if corr is not None:
                rows.append({"left_candidate_id": left_id, "right_candidate_id": right_id, "correlation": corr})
    return sorted(rows, key=lambda row: -abs(float(row["correlation"])))


def _correlation(left: pd.Series | None, right: pd.Series | None) -> float | None:
    if left is None or right is None:
        return None
    joined = pd.concat([left.rename("left"), right.rename("right")], axis=1, join="inner").dropna()
    if len(joined) < 3:
        return None
    if joined["left"].std() == 0.0 or joined["right"].std() == 0.0:
        return None
    return _number(joined["left"].corr(joined["right"]))


def _return_series(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        return pd.Series(dtype=float)
    working = frame[["date", "period_return"]].copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working["period_return"] = pd.to_numeric(working["period_return"], errors="coerce").fillna(0.0)
    working = working.dropna(subset=["date"]).sort_values("date")
    return pd.Series(working["period_return"].to_numpy(dtype=float), index=pd.DatetimeIndex(working["date"]))


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
