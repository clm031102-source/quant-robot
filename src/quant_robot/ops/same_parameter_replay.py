from __future__ import annotations

import json
import re
from dataclasses import replace
from datetime import date
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.experiments.runner import ExperimentGridConfig, run_experiment_grid


STAGE = "same_parameter_full_sample_replay"


def build_same_parameter_replay_config(
    candidate_row: dict[str, Any],
    base_config: ExperimentGridConfig,
    *,
    output_root: str | Path,
    start_date: str,
    end_date: str,
) -> ExperimentGridConfig:
    case_id = _text(candidate_row.get("case_id"), "candidate")
    market = _text(candidate_row.get("market"), base_config.markets[0] if base_config.markets else "CN").upper()
    factor_name = _text(
        candidate_row.get("factor_name"),
        base_config.factor_names[0] if base_config.factor_names else "",
    )
    factor_source = _text(candidate_row.get("factor_source"), base_config.factor_source)
    top_n = _int(candidate_row.get("top_n"), base_config.top_n_values[0])
    cost_bps = _float(candidate_row.get("cost_bps"), base_config.cost_bps_values[0])
    forward_horizon = _int(candidate_row.get("forward_horizon"), base_config.forward_horizon)
    execution_lag = _int(candidate_row.get("execution_lag", candidate_row.get("lag")), base_config.execution_lag)
    rebalance_interval = _int(
        candidate_row.get("rebalance_interval", candidate_row.get("schedule_interval")),
        base_config.rebalance_intervals[0],
    )
    regime_lookback = _int(candidate_row.get("regime_lookback"), base_config.regime_lookback)
    regime_lookback_values = (
        (regime_lookback,)
        if _present(candidate_row.get("regime_lookback")) or base_config.regime_lookback_values is not None
        else None
    )

    return replace(
        base_config,
        markets=(market,),
        factor_source=factor_source,
        factor_names=(factor_name,),
        top_n_values=(top_n,),
        cost_bps_values=(cost_bps,),
        start_date=start_date,
        end_date=end_date,
        signal_start_date=start_date,
        signal_end_date=end_date,
        forward_horizon=forward_horizon,
        execution_lag=execution_lag,
        rebalance_intervals=(rebalance_interval,),
        regime_lookback=regime_lookback,
        regime_lookback_values=regime_lookback_values,
        output_dir=Path(output_root) / _safe_path_token(case_id),
        write_case_artifacts=False,
    )


def replay_leaderboard_row(
    candidate_row: dict[str, Any],
    grid_row: dict[str, Any],
    *,
    source_report: str,
) -> dict[str, Any]:
    original_case_id = _text(candidate_row.get("case_id"), _text(grid_row.get("case_id"), "unknown_case"))
    replay_case_id = _text(grid_row.get("case_id"), original_case_id)
    status = "pass" if str(grid_row.get("status") or "").strip().lower() == "completed" else "block"

    row = dict(candidate_row)
    for key, value in grid_row.items():
        if key != "case_id":
            row[key] = value
    row.update(
        {
            "case_id": original_case_id,
            "replay_case_id": replay_case_id,
            "source_kind": "same_parameter_full_sample_replay",
            "source_report": source_report,
            "same_parameter_full_sample_status": status,
            "replay_status": status,
            "replay_grid_status": grid_row.get("status"),
        }
    )
    return row


def run_same_parameter_full_sample_replay(
    candidate_rows: list[dict[str, Any]] | pd.DataFrame,
    bars: pd.DataFrame,
    base_config: ExperimentGridConfig,
    *,
    output_dir: str | Path,
    start_date: str,
    end_date: str,
    max_candidates: int | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    candidates = _records(candidate_rows)
    if max_candidates is not None:
        candidates = candidates[:max_candidates]

    replay_rows: list[dict[str, Any]] = []
    for batch_index, batch in enumerate(_compatible_batches(candidates, base_config), start=1):
        config = _build_batch_replay_config(
            batch,
            base_config,
            output_root=output_path / "cases",
            batch_index=batch_index,
            start_date=start_date,
            end_date=end_date,
        )
        _emit(progress, "batch_start", batch_index=batch_index, candidates=len(batch))
        result = run_experiment_grid(bars, config, progress=progress)
        leaderboard = result.get("leaderboard", [])
        source_report = str((config.output_dir or output_path) / "leaderboard.csv")
        for candidate in batch:
            grid_row = _selected_grid_row(leaderboard, candidate)
            replay_rows.append(replay_leaderboard_row(candidate, grid_row, source_report=source_report))
            _emit(
                progress,
                "candidate_done",
                case_id=candidate.get("case_id"),
                replay_status=replay_rows[-1]["replay_status"],
            )
        _emit(progress, "batch_done", batch_index=batch_index, candidates=len(batch))

    pack = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "start_date": start_date,
        "end_date": end_date,
        "summary": {
            "candidates": len(replay_rows),
            "pass": sum(1 for row in replay_rows if row.get("same_parameter_full_sample_status") == "pass"),
            "block": sum(1 for row in replay_rows if row.get("same_parameter_full_sample_status") == "block"),
        },
        "replay_rows": replay_rows,
    }
    write_same_parameter_full_sample_replay_pack(output_path, pack)
    return pack


def _compatible_batches(candidates: list[dict[str, Any]], base_config: ExperimentGridConfig) -> list[list[dict[str, Any]]]:
    batches: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    order: list[tuple[Any, ...]] = []
    for candidate in candidates:
        key = _batch_key(candidate, base_config)
        if key not in batches:
            batches[key] = []
            order.append(key)
        batches[key].append(candidate)
    return [batches[key] for key in order]


def _batch_key(candidate: dict[str, Any], base_config: ExperimentGridConfig) -> tuple[Any, ...]:
    return (
        _text(candidate.get("market"), base_config.markets[0] if base_config.markets else "CN").upper(),
        _text(candidate.get("factor_source"), base_config.factor_source),
        _int(candidate.get("forward_horizon"), base_config.forward_horizon),
        _int(candidate.get("execution_lag", candidate.get("lag")), base_config.execution_lag),
    )


def _build_batch_replay_config(
    candidates: list[dict[str, Any]],
    base_config: ExperimentGridConfig,
    *,
    output_root: str | Path,
    batch_index: int,
    start_date: str,
    end_date: str,
) -> ExperimentGridConfig:
    first = candidates[0]
    market = _text(first.get("market"), base_config.markets[0] if base_config.markets else "CN").upper()
    factor_source = _text(first.get("factor_source"), base_config.factor_source)
    regime_values = _unique_ints(
        candidate.get("regime_lookback")
        for candidate in candidates
        if _present(candidate.get("regime_lookback")) or base_config.regime_lookback_values is not None
    )
    return replace(
        base_config,
        markets=(market,),
        factor_source=factor_source,
        factor_names=_unique_texts(
            _text(candidate.get("factor_name"), base_config.factor_names[0] if base_config.factor_names else "")
            for candidate in candidates
        ),
        top_n_values=_unique_ints(_int(candidate.get("top_n"), base_config.top_n_values[0]) for candidate in candidates),
        cost_bps_values=_unique_floats(_float(candidate.get("cost_bps"), base_config.cost_bps_values[0]) for candidate in candidates),
        start_date=start_date,
        end_date=end_date,
        signal_start_date=start_date,
        signal_end_date=end_date,
        forward_horizon=_int(first.get("forward_horizon"), base_config.forward_horizon),
        execution_lag=_int(first.get("execution_lag", first.get("lag")), base_config.execution_lag),
        rebalance_intervals=_unique_ints(
            _int(
                candidate.get("rebalance_interval", candidate.get("schedule_interval")),
                base_config.rebalance_intervals[0],
            )
            for candidate in candidates
        ),
        regime_lookback=_int(first.get("regime_lookback"), base_config.regime_lookback),
        regime_lookback_values=regime_values or None,
        output_dir=Path(output_root) / f"batch_{batch_index:03d}",
        write_case_artifacts=False,
    )


def write_same_parameter_full_sample_replay_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    rows = pack.get("replay_rows", [])
    pd.DataFrame(rows).to_csv(output_path / "same_parameter_full_sample_replay.csv", index=False)
    (output_path / "same_parameter_full_sample_replay.json").write_text(
        json.dumps(_jsonable(pack), indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _text(value: Any, default: str) -> str:
    if not _present(value):
        return default
    return str(value).strip()


def _int(value: Any, default: int) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _safe_path_token(value: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return token or "candidate"


def _records(rows: list[dict[str, Any]] | pd.DataFrame) -> list[dict[str, Any]]:
    if isinstance(rows, pd.DataFrame):
        return rows.to_dict(orient="records")
    return [dict(row) for row in rows]


def _selected_grid_row(leaderboard: Any, candidate: dict[str, Any]) -> dict[str, Any]:
    rows = leaderboard if isinstance(leaderboard, list) else []
    original_case_id = _text(candidate.get("case_id"), "")
    for row in rows:
        if isinstance(row, dict) and _text(row.get("case_id"), "") == original_case_id:
            return row
    for row in rows:
        if isinstance(row, dict) and _row_matches_candidate(row, candidate):
            return row
    for row in rows:
        if isinstance(row, dict) and str(row.get("status")) == "completed":
            return row
    for row in rows:
        if isinstance(row, dict):
            return row
    return {
        "case_id": _text(candidate.get("case_id"), "unknown_case"),
        "status": "failed",
        "error": "same_parameter_full_sample_replay_no_leaderboard_rows",
        "trades": 0,
    }


def _row_matches_candidate(row: dict[str, Any], candidate: dict[str, Any]) -> bool:
    comparisons = [
        _text(row.get("market"), "").upper() == _text(candidate.get("market"), "").upper(),
        _text(row.get("factor_name"), "") == _text(candidate.get("factor_name"), ""),
        _int(row.get("top_n"), -1) == _int(candidate.get("top_n"), -2),
        _float(row.get("cost_bps"), float("nan")) == _float(candidate.get("cost_bps"), float("nan")),
        _int(row.get("rebalance_interval"), -1) == _int(
            candidate.get("rebalance_interval", candidate.get("schedule_interval")),
            -2,
        ),
    ]
    if _present(candidate.get("regime_lookback")):
        comparisons.append(_int(row.get("regime_lookback"), -1) == _int(candidate.get("regime_lookback"), -2))
    return all(comparisons)


def _unique_texts(values: Any) -> tuple[str, ...]:
    output: list[str] = []
    for value in values:
        text = str(value)
        if text not in output:
            output.append(text)
    return tuple(output)


def _unique_ints(values: Any) -> tuple[int, ...]:
    output: list[int] = []
    for value in values:
        number = int(value)
        if number not in output:
            output.append(number)
    return tuple(output)


def _unique_floats(values: Any) -> tuple[float, ...]:
    output: list[float] = []
    for value in values:
        number = float(value)
        if number not in output:
            output.append(number)
    return tuple(output)


def _emit(progress: Callable[[dict[str, Any]], None] | None, event: str, **fields: Any) -> None:
    if progress is not None:
        progress({"event": event, **fields})


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    return value
