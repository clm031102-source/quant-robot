from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.experiments.runner import ExperimentGridConfig, run_experiment_grid


@dataclass(frozen=True)
class WalkForwardConfig:
    split_date: str
    experiment_grid: ExperimentGridConfig
    output_dir: Path | None = None
    rank_by: str = "stability_score"
    min_test_trades: int = 1
    min_test_sharpe: float = 0.0
    min_test_relative_return: float | None = None
    max_test_drawdown: float | None = None


def load_walk_forward_config(path: str | Path) -> WalkForwardConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return WalkForwardConfig(
        split_date=str(data["split_date"]),
        experiment_grid=_grid_from_mapping(data.get("experiment_grid", {})),
        output_dir=Path(data["output_dir"]) if data.get("output_dir") else None,
        rank_by=str(data.get("rank_by", WalkForwardConfig.rank_by)),
        min_test_trades=int(data.get("min_test_trades", WalkForwardConfig.min_test_trades)),
        min_test_sharpe=float(data.get("min_test_sharpe", WalkForwardConfig.min_test_sharpe)),
        min_test_relative_return=(
            float(data["min_test_relative_return"]) if data.get("min_test_relative_return") is not None else None
        ),
        max_test_drawdown=float(data["max_test_drawdown"]) if data.get("max_test_drawdown") is not None else None,
    )


def run_walk_forward_validation(bars: pd.DataFrame, config: WalkForwardConfig) -> dict[str, Any]:
    train_bars, post_split_bars = _split_bars(bars, config.split_date)
    test_signal_start = str(pd.to_datetime(post_split_bars["date"]).dt.date.min())
    test_bars = _with_warmup_bars(train_bars, post_split_bars, max(config.experiment_grid.factor_windows))
    train_dir = config.output_dir / "train" if config.output_dir is not None else None
    test_dir = config.output_dir / "test" if config.output_dir is not None else None
    train_config = replace(config.experiment_grid, output_dir=train_dir, signal_end_date=config.split_date)
    test_config = replace(config.experiment_grid, output_dir=test_dir, signal_start_date=test_signal_start)
    train = run_experiment_grid(train_bars, train_config)
    test = run_experiment_grid(test_bars, test_config)
    rows = _merge_leaderboards(train["leaderboard"], test["leaderboard"], config)
    leaderboard = _rank_rows(rows, config.rank_by)
    result = {
        "config": _config_dict(config),
        "summary": _summary(leaderboard),
        "leaderboard": leaderboard,
    }
    if config.output_dir is not None:
        _write_artifacts(config.output_dir, result, leaderboard)
    return result


def _split_bars(bars: pd.DataFrame, split_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    split = pd.to_datetime(split_date).date()
    dates = pd.to_datetime(bars["date"]).dt.date
    train = bars[dates <= split].sort_values(["asset_id", "date"]).reset_index(drop=True)
    test = bars[dates > split].sort_values(["asset_id", "date"]).reset_index(drop=True)
    if train.empty or test.empty:
        raise ValueError("Walk-forward split requires non-empty train and test bars")
    return train, test


def _with_warmup_bars(train_bars: pd.DataFrame, post_split_bars: pd.DataFrame, warmup_rows: int) -> pd.DataFrame:
    warmup = (
        train_bars.sort_values(["asset_id", "date"])
        .groupby("asset_id", as_index=False, group_keys=False)
        .tail(max(warmup_rows, 0))
    )
    return pd.concat([warmup, post_split_bars], ignore_index=True).sort_values(["asset_id", "date"]).reset_index(drop=True)


def _merge_leaderboards(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    config: WalkForwardConfig,
) -> list[dict[str, Any]]:
    train_by_case = {str(row["case_id"]): row for row in train_rows}
    test_by_case = {str(row["case_id"]): row for row in test_rows}
    case_ids = sorted(set(train_by_case) | set(test_by_case))
    return [_merged_row(case_id, train_by_case.get(case_id), test_by_case.get(case_id), config) for case_id in case_ids]


def _merged_row(
    case_id: str,
    train: dict[str, Any] | None,
    test: dict[str, Any] | None,
    config: WalkForwardConfig,
) -> dict[str, Any]:
    source = test or train or {}
    train_sharpe = _metric(train, "sharpe")
    test_sharpe = _metric(test, "sharpe")
    test_relative_return = _metric(test, "relative_return")
    test_max_drawdown = _metric(test, "max_drawdown")
    degradation = max(train_sharpe - test_sharpe, 0.0)
    stability_score = test_sharpe - degradation
    test_trades = int(_metric(test, "trades"))
    reasons = _rejection_reasons(train, test, test_trades, test_sharpe, test_relative_return, test_max_drawdown, config)
    return _sanitize(
        {
            "case_id": case_id,
            "market": source.get("market"),
            "factor_name": source.get("factor_name"),
            "factor_windows": source.get("factor_windows", []),
            "top_n": source.get("top_n"),
            "cost_bps": source.get("cost_bps"),
            "data_mode": _data_mode(train, test),
            "train_status": train.get("status") if train else "missing",
            "test_status": test.get("status") if test else "missing",
            "validation_status": "accepted" if not reasons else "rejected",
            "rejection_reasons": reasons,
            "train_trades": int(_metric(train, "trades")),
            "test_trades": test_trades,
            "train_total_return": _metric(train, "total_return"),
            "test_total_return": _metric(test, "total_return"),
            "train_benchmark_total_return": _metric(train, "benchmark_total_return"),
            "test_benchmark_total_return": _metric(test, "benchmark_total_return"),
            "train_relative_return": _metric(train, "relative_return"),
            "test_relative_return": test_relative_return,
            "train_decision_status": train.get("decision_status") if train else "missing",
            "test_decision_status": test.get("decision_status") if test else "missing",
            "train_sharpe": train_sharpe,
            "test_sharpe": test_sharpe,
            "train_max_drawdown": _metric(train, "max_drawdown"),
            "test_max_drawdown": test_max_drawdown,
            "train_mean_ic": _metric(train, "mean_ic"),
            "test_mean_ic": _metric(test, "mean_ic"),
            "sharpe_degradation": degradation,
            "stability_score": stability_score,
        }
    )


def _rejection_reasons(
    train: dict[str, Any] | None,
    test: dict[str, Any] | None,
    test_trades: int,
    test_sharpe: float,
    test_relative_return: float,
    test_max_drawdown: float,
    config: WalkForwardConfig,
) -> list[str]:
    reasons = []
    if train is None or train.get("status") != "completed":
        reasons.append("train_not_completed")
    if test is None or test.get("status") != "completed":
        reasons.append("test_not_completed")
    if test_trades < config.min_test_trades:
        reasons.append("insufficient_oos_trades")
    if test_sharpe < config.min_test_sharpe:
        reasons.append("oos_sharpe_below_threshold")
    if config.min_test_relative_return is not None and test_relative_return < config.min_test_relative_return:
        reasons.append("relative_return_below_threshold")
    if config.max_test_drawdown is not None and test_max_drawdown < -abs(config.max_test_drawdown):
        reasons.append("drawdown_above_limit")
    return reasons


def _rank_rows(rows: list[dict[str, Any]], rank_by: str) -> list[dict[str, Any]]:
    ranked = sorted(
        rows,
        key=lambda row: (
            0 if row["validation_status"] == "accepted" else 1,
            -_metric(row, rank_by),
            str(row["case_id"]),
        ),
    )
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _summary(leaderboard: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "cases": len(leaderboard),
        "accepted": sum(1 for row in leaderboard if row["validation_status"] == "accepted"),
        "rejected": sum(1 for row in leaderboard if row["validation_status"] == "rejected"),
    }


def _write_artifacts(output_dir: Path, result: dict[str, Any], leaderboard: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(leaderboard).to_csv(output_dir / "walk_forward_leaderboard.csv", index=False)
    (output_dir / "walk_forward_leaderboard.json").write_text(json.dumps(leaderboard, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "config": result["config"],
        "summary": result["summary"],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _grid_from_mapping(data: dict[str, Any]) -> ExperimentGridConfig:
    return ExperimentGridConfig(
        markets=tuple(data.get("markets", ExperimentGridConfig.markets)),
        factor_names=tuple(data.get("factor_names", ExperimentGridConfig.factor_names)),
        factor_windows=tuple(int(value) for value in data.get("factor_windows", ExperimentGridConfig.factor_windows)),
        top_n_values=tuple(int(value) for value in data.get("top_n_values", ExperimentGridConfig.top_n_values)),
        cost_bps_values=tuple(float(value) for value in data.get("cost_bps_values", ExperimentGridConfig.cost_bps_values)),
        start_date=data.get("start_date"),
        end_date=data.get("end_date"),
        forward_horizon=int(data.get("forward_horizon", ExperimentGridConfig.forward_horizon)),
        execution_lag=int(data.get("execution_lag", ExperimentGridConfig.execution_lag)),
        rebalance_intervals=tuple(int(value) for value in data.get("rebalance_intervals", ExperimentGridConfig.rebalance_intervals)),
        quantiles=int(data.get("quantiles", ExperimentGridConfig.quantiles)),
        portfolio_scope=data.get("portfolio_scope"),
        periods_per_year=float(data["periods_per_year"]) if data.get("periods_per_year") is not None else None,
        benchmark_asset_id=data.get("benchmark_asset_id"),
        cash_annual_return=float(data.get("cash_annual_return", ExperimentGridConfig.cash_annual_return)),
        regime_filter=bool(data.get("regime_filter", ExperimentGridConfig.regime_filter)),
        regime_lookback=int(data.get("regime_lookback", ExperimentGridConfig.regime_lookback)),
        min_relative_return=float(data["min_relative_return"]) if data.get("min_relative_return") is not None else None,
        max_drawdown_limit=float(data["max_drawdown_limit"]) if data.get("max_drawdown_limit") is not None else None,
        signal_start_date=data.get("signal_start_date"),
        signal_end_date=data.get("signal_end_date"),
        output_dir=None,
        rank_by=str(data.get("rank_by", ExperimentGridConfig.rank_by)),
        min_trades=int(data.get("min_trades", ExperimentGridConfig.min_trades)),
    )


def _config_dict(config: WalkForwardConfig) -> dict[str, Any]:
    data = asdict(config)
    data["output_dir"] = str(config.output_dir) if config.output_dir is not None else None
    data["experiment_grid"]["output_dir"] = None
    data["experiment_grid"]["markets"] = list(config.experiment_grid.markets)
    data["experiment_grid"]["factor_names"] = list(config.experiment_grid.factor_names)
    data["experiment_grid"]["factor_windows"] = list(config.experiment_grid.factor_windows)
    data["experiment_grid"]["top_n_values"] = list(config.experiment_grid.top_n_values)
    data["experiment_grid"]["cost_bps_values"] = list(config.experiment_grid.cost_bps_values)
    data["experiment_grid"]["rebalance_intervals"] = list(config.experiment_grid.rebalance_intervals)
    return data


def _metric(row: dict[str, Any] | None, key: str) -> float:
    if row is None:
        return 0.0
    try:
        value = float(row.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) else 0.0


def _data_mode(train: dict[str, Any] | None, test: dict[str, Any] | None) -> str:
    modes = {str(row.get("data_mode", "unknown")) for row in [train, test] if row is not None}
    if not modes:
        return "unknown"
    if len(modes) == 1:
        return next(iter(modes))
    return "mixed"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
