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
    bar_start_date: str | None = None
    bar_end_date: str | None = None
    rank_by: str = "stability_score"
    min_test_trades: int = 1
    min_test_sharpe: float = 0.0
    min_test_relative_return: float | None = None
    max_test_drawdown: float | None = None
    rolling_train_days: int | None = None
    rolling_test_days: int | None = None
    rolling_step_days: int | None = None
    min_accepted_folds: int = 1
    multiple_testing_alpha: float = 0.05


def load_walk_forward_config(path: str | Path) -> WalkForwardConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return WalkForwardConfig(
        split_date=str(data["split_date"]),
        experiment_grid=_grid_from_mapping(data.get("experiment_grid", {})),
        output_dir=Path(data["output_dir"]) if data.get("output_dir") else None,
        bar_start_date=data.get("bar_start_date"),
        bar_end_date=data.get("bar_end_date"),
        rank_by=str(data.get("rank_by", WalkForwardConfig.rank_by)),
        min_test_trades=int(data.get("min_test_trades", WalkForwardConfig.min_test_trades)),
        min_test_sharpe=float(data.get("min_test_sharpe", WalkForwardConfig.min_test_sharpe)),
        min_test_relative_return=(
            float(data["min_test_relative_return"]) if data.get("min_test_relative_return") is not None else None
        ),
        max_test_drawdown=float(data["max_test_drawdown"]) if data.get("max_test_drawdown") is not None else None,
        rolling_train_days=int(data["rolling_train_days"]) if data.get("rolling_train_days") is not None else None,
        rolling_test_days=int(data["rolling_test_days"]) if data.get("rolling_test_days") is not None else None,
        rolling_step_days=int(data["rolling_step_days"]) if data.get("rolling_step_days") is not None else None,
        min_accepted_folds=int(data.get("min_accepted_folds", WalkForwardConfig.min_accepted_folds)),
        multiple_testing_alpha=float(data.get("multiple_testing_alpha", WalkForwardConfig.multiple_testing_alpha)),
    )


def run_walk_forward_validation(bars: pd.DataFrame, config: WalkForwardConfig) -> dict[str, Any]:
    bars = _filter_validation_bars(bars, config)
    if _rolling_enabled(config):
        return _run_rolling_walk_forward_validation(bars, config)
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
    leaderboard = _rank_rows(_with_multiple_testing_evidence(rows, config), config.rank_by)
    result = {
        "config": _config_dict(config),
        "summary": _summary(leaderboard),
        "leaderboard": leaderboard,
    }
    if config.output_dir is not None:
        _write_artifacts(config.output_dir, result, leaderboard)
    return result


def _run_rolling_walk_forward_validation(bars: pd.DataFrame, config: WalkForwardConfig) -> dict[str, Any]:
    folds = _rolling_folds(bars, config)
    if not folds:
        raise ValueError("Rolling walk-forward requires enough dates for at least one fold")
    fold_rows: list[dict[str, Any]] = []
    max_window = max(config.experiment_grid.factor_windows)
    for fold in folds:
        fold_dir = config.output_dir / f"fold_{fold['fold']:02d}" if config.output_dir is not None else None
        train_dir = fold_dir / "train" if fold_dir is not None else None
        test_dir = fold_dir / "test" if fold_dir is not None else None
        train_config = replace(
            config.experiment_grid,
            output_dir=train_dir,
            signal_start_date=str(fold["train_start_date"]),
            signal_end_date=str(fold["train_end_date"]),
        )
        test_config = replace(
            config.experiment_grid,
            output_dir=test_dir,
            signal_start_date=str(fold["test_start_date"]),
            signal_end_date=str(fold["test_end_date"]),
        )
        test_bars = _with_warmup_bars(fold["train_bars"], fold["test_bars"], max_window)
        train = run_experiment_grid(fold["train_bars"], train_config)
        test = run_experiment_grid(test_bars, test_config)
        merged = _merge_leaderboards(train["leaderboard"], test["leaderboard"], config)
        for row in merged:
            fold_rows.append(
                _sanitize(
                    {
                        **row,
                        "fold": fold["fold"],
                        "train_start_date": fold["train_start_date"],
                        "train_end_date": fold["train_end_date"],
                        "test_start_date": fold["test_start_date"],
                        "test_end_date": fold["test_end_date"],
                    }
                )
            )
    rows = _aggregate_fold_rows(fold_rows, config)
    leaderboard = _rank_rows(_with_multiple_testing_evidence(rows, config), config.rank_by)
    result = {
        "config": _config_dict(config),
        "summary": _summary(leaderboard),
        "leaderboard": leaderboard,
        "folds": fold_rows,
    }
    if config.output_dir is not None:
        _write_artifacts(config.output_dir, result, leaderboard)
    return result


def _rolling_enabled(config: WalkForwardConfig) -> bool:
    values = [config.rolling_train_days, config.rolling_test_days, config.rolling_step_days]
    if all(value is None for value in values):
        return False
    if any(value is None for value in values):
        raise ValueError("rolling_train_days, rolling_test_days, and rolling_step_days must be set together")
    if any(int(value) < 1 for value in values if value is not None):
        raise ValueError("rolling walk-forward day counts must be positive")
    return True


def _filter_validation_bars(bars: pd.DataFrame, config: WalkForwardConfig) -> pd.DataFrame:
    if not config.bar_start_date and not config.bar_end_date:
        return bars
    frame = bars.copy()
    dates = pd.to_datetime(frame["date"]).dt.date
    if config.bar_start_date:
        dates_start = pd.to_datetime(config.bar_start_date).date()
        frame = frame[dates >= dates_start]
        dates = pd.to_datetime(frame["date"]).dt.date
    if config.bar_end_date:
        dates_end = pd.to_datetime(config.bar_end_date).date()
        frame = frame[dates <= dates_end]
    if frame.empty:
        raise ValueError("Walk-forward bar window requires non-empty bars")
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _rolling_folds(bars: pd.DataFrame, config: WalkForwardConfig) -> list[dict[str, Any]]:
    train_days = int(config.rolling_train_days or 0)
    test_days = int(config.rolling_test_days or 0)
    step_days = int(config.rolling_step_days or 0)
    dates = sorted(pd.to_datetime(bars["date"]).dt.date.unique())
    limit = len(dates) - train_days - test_days + 1
    if limit <= 0:
        return []
    date_values = pd.to_datetime(bars["date"]).dt.date
    folds = []
    for fold_number, start in enumerate(range(0, limit, step_days), start=1):
        train_dates = dates[start : start + train_days]
        test_dates = dates[start + train_days : start + train_days + test_days]
        train_bars = bars[date_values.isin(train_dates)].sort_values(["asset_id", "date"]).reset_index(drop=True)
        test_bars = bars[date_values.isin(test_dates)].sort_values(["asset_id", "date"]).reset_index(drop=True)
        if train_bars.empty or test_bars.empty:
            continue
        folds.append(
            {
                "fold": fold_number,
                "train_start_date": train_dates[0],
                "train_end_date": train_dates[-1],
                "test_start_date": test_dates[0],
                "test_end_date": test_dates[-1],
                "train_bars": train_bars,
                "test_bars": test_bars,
            }
        )
    return folds


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
            "factor_source": source.get("factor_source", config.experiment_grid.factor_source),
            "factor_name": source.get("factor_name"),
            "factor_windows": source.get("factor_windows", []),
            "top_n": source.get("top_n"),
            "cost_bps": source.get("cost_bps"),
            "regime_lookback": source.get("regime_lookback"),
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
            "train_ic_observations": int(_metric(train, "ic_observations")),
            "test_ic_observations": int(_metric(test, "ic_observations")),
            "train_ic_t_stat": _metric(train, "ic_t_stat"),
            "test_ic_t_stat": _metric(test, "ic_t_stat"),
            "train_ic_p_value": _metric_or(train, "ic_p_value", 1.0),
            "test_ic_p_value": _metric_or(test, "ic_p_value", 1.0),
            "train_positive_ic_rate": _metric(train, "positive_ic_rate"),
            "test_positive_ic_rate": _metric(test, "positive_ic_rate"),
            "test_significance_status": test.get("significance_status") if test else "missing",
            "train_tail_mean_ic": _metric(train, "tail_mean_ic"),
            "test_tail_mean_ic": _metric(test, "tail_mean_ic"),
            "train_tail_ic_observations": int(_metric(train, "tail_ic_observations")),
            "test_tail_ic_observations": int(_metric(test, "tail_ic_observations")),
            "train_tail_ic_t_stat": _metric(train, "tail_ic_t_stat"),
            "test_tail_ic_t_stat": _metric(test, "tail_ic_t_stat"),
            "train_tail_ic_p_value": _metric_or(train, "tail_ic_p_value", 1.0),
            "test_tail_ic_p_value": _metric_or(test, "tail_ic_p_value", 1.0),
            "train_tail_positive_ic_rate": _metric(train, "tail_positive_ic_rate"),
            "test_tail_positive_ic_rate": _metric(test, "tail_positive_ic_rate"),
            "test_tail_significance_status": test.get("tail_significance_status") if test else "missing",
            "test_avg_cost_rate": _metric(test, "avg_cost_rate"),
            "test_max_cost_rate": _metric(test, "max_cost_rate"),
            "test_avg_participation_rate": _metric(test, "avg_participation_rate"),
            "test_max_participation_rate": _metric(test, "max_participation_rate"),
            "test_capacity_limited_trades": int(_metric(test, "capacity_limited_trades")),
            "folds": 1,
            "accepted_folds": 0 if reasons else 1,
            "rejected_folds": 1 if reasons else 0,
            "mean_test_sharpe": test_sharpe,
            "mean_test_relative_return": test_relative_return,
            "worst_test_max_drawdown": test_max_drawdown,
            "total_test_trades": test_trades,
            "mean_stability_score": stability_score,
            "fold_rejection_reasons": reasons,
            "sharpe_degradation": degradation,
            "stability_score": stability_score,
        }
    )


def _aggregate_fold_rows(rows: list[dict[str, Any]], config: WalkForwardConfig) -> list[dict[str, Any]]:
    case_ids = sorted({str(row["case_id"]) for row in rows})
    return [_aggregate_case_rows(case_id, [row for row in rows if str(row["case_id"]) == case_id], config) for case_id in case_ids]


def _aggregate_case_rows(case_id: str, rows: list[dict[str, Any]], config: WalkForwardConfig) -> dict[str, Any]:
    source = rows[0] if rows else {}
    folds = len(rows)
    accepted_folds = sum(1 for row in rows if row.get("validation_status") == "accepted")
    rejected_folds = folds - accepted_folds
    fold_reasons = _dedupe_reason_list(rows)
    if accepted_folds < config.min_accepted_folds:
        fold_reasons.append("insufficient_accepted_folds")
    test_trades = sum(int(_metric(row, "test_trades")) for row in rows)
    train_trades = sum(int(_metric(row, "train_trades")) for row in rows)
    mean_test_sharpe = _mean_metric(rows, "test_sharpe")
    mean_test_relative_return = _mean_metric(rows, "test_relative_return")
    worst_test_max_drawdown = _min_metric(rows, "test_max_drawdown")
    mean_stability_score = _mean_metric(rows, "stability_score")
    return _sanitize(
        {
            "case_id": case_id,
            "market": source.get("market"),
            "factor_source": source.get("factor_source", config.experiment_grid.factor_source),
            "factor_name": source.get("factor_name"),
            "factor_windows": source.get("factor_windows", []),
            "top_n": source.get("top_n"),
            "cost_bps": source.get("cost_bps"),
            "regime_lookback": source.get("regime_lookback"),
            "data_mode": _aggregate_data_mode(rows),
            "train_status": _aggregate_status(rows, "train_status"),
            "test_status": _aggregate_status(rows, "test_status"),
            "validation_status": "accepted" if not fold_reasons else "rejected",
            "rejection_reasons": fold_reasons,
            "fold_rejection_reasons": fold_reasons,
            "folds": folds,
            "accepted_folds": accepted_folds,
            "rejected_folds": rejected_folds,
            "train_trades": train_trades,
            "test_trades": test_trades,
            "total_test_trades": test_trades,
            "train_total_return": _mean_metric(rows, "train_total_return"),
            "test_total_return": _mean_metric(rows, "test_total_return"),
            "train_benchmark_total_return": _mean_metric(rows, "train_benchmark_total_return"),
            "test_benchmark_total_return": _mean_metric(rows, "test_benchmark_total_return"),
            "train_relative_return": _mean_metric(rows, "train_relative_return"),
            "test_relative_return": mean_test_relative_return,
            "mean_test_relative_return": mean_test_relative_return,
            "train_decision_status": _aggregate_status(rows, "train_decision_status"),
            "test_decision_status": _aggregate_status(rows, "test_decision_status"),
            "train_sharpe": _mean_metric(rows, "train_sharpe"),
            "test_sharpe": mean_test_sharpe,
            "mean_test_sharpe": mean_test_sharpe,
            "train_max_drawdown": _min_metric(rows, "train_max_drawdown"),
            "test_max_drawdown": worst_test_max_drawdown,
            "worst_test_max_drawdown": worst_test_max_drawdown,
            "train_mean_ic": _mean_metric(rows, "train_mean_ic"),
            "test_mean_ic": _mean_metric(rows, "test_mean_ic"),
            "train_ic_observations": sum(int(_metric(row, "train_ic_observations")) for row in rows),
            "test_ic_observations": sum(int(_metric(row, "test_ic_observations")) for row in rows),
            "train_ic_t_stat": _mean_metric(rows, "train_ic_t_stat"),
            "test_ic_t_stat": _mean_metric(rows, "test_ic_t_stat"),
            "train_ic_p_value": _max_metric(rows, "train_ic_p_value", default=1.0),
            "test_ic_p_value": _max_metric(rows, "test_ic_p_value", default=1.0),
            "train_positive_ic_rate": _min_metric(rows, "train_positive_ic_rate"),
            "test_positive_ic_rate": _min_metric(rows, "test_positive_ic_rate"),
            "test_significance_status": _aggregate_status(rows, "test_significance_status"),
            "train_tail_mean_ic": _mean_metric(rows, "train_tail_mean_ic"),
            "test_tail_mean_ic": _mean_metric(rows, "test_tail_mean_ic"),
            "train_tail_ic_observations": sum(int(_metric(row, "train_tail_ic_observations")) for row in rows),
            "test_tail_ic_observations": sum(int(_metric(row, "test_tail_ic_observations")) for row in rows),
            "train_tail_ic_t_stat": _mean_metric(rows, "train_tail_ic_t_stat"),
            "test_tail_ic_t_stat": _mean_metric(rows, "test_tail_ic_t_stat"),
            "train_tail_ic_p_value": _max_metric(rows, "train_tail_ic_p_value", default=1.0),
            "test_tail_ic_p_value": _max_metric(rows, "test_tail_ic_p_value", default=1.0),
            "train_tail_positive_ic_rate": _min_metric(rows, "train_tail_positive_ic_rate"),
            "test_tail_positive_ic_rate": _min_metric(rows, "test_tail_positive_ic_rate"),
            "test_tail_significance_status": _aggregate_status(rows, "test_tail_significance_status"),
            "test_avg_cost_rate": _mean_metric(rows, "test_avg_cost_rate"),
            "test_max_cost_rate": _max_metric(rows, "test_max_cost_rate"),
            "test_avg_participation_rate": _mean_metric(rows, "test_avg_participation_rate"),
            "test_max_participation_rate": _max_metric(rows, "test_max_participation_rate"),
            "test_capacity_limited_trades": sum(int(_metric(row, "test_capacity_limited_trades")) for row in rows),
            "sharpe_degradation": _mean_metric(rows, "sharpe_degradation"),
            "stability_score": mean_stability_score,
            "mean_stability_score": mean_stability_score,
        }
    )


def _with_multiple_testing_evidence(rows: list[dict[str, Any]], config: WalkForwardConfig) -> list[dict[str, Any]]:
    hypothesis_count = len(rows)
    corrected = []
    for row in rows:
        p_value = _metric_or(row, "test_ic_p_value", 1.0)
        adjusted = min(max(p_value, 0.0) * max(hypothesis_count, 1), 1.0)
        passes = adjusted <= config.multiple_testing_alpha
        reasons = list(row.get("rejection_reasons", []) or [])
        validation_status = row.get("validation_status")
        if not passes:
            if "adjusted_ic_significance_not_passed" not in reasons:
                reasons.append("adjusted_ic_significance_not_passed")
            validation_status = "rejected"
        corrected.append(
            {
                **row,
                "validation_status": validation_status,
                "rejection_reasons": reasons,
                "hypothesis_count": hypothesis_count,
                "adjusted_ic_p_value": adjusted,
                "passes_adjusted_ic_p_value": passes,
            }
        )
    return corrected


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
    summary = {
        "cases": len(leaderboard),
        "accepted": sum(1 for row in leaderboard if row["validation_status"] == "accepted"),
        "rejected": sum(1 for row in leaderboard if row["validation_status"] == "rejected"),
    }
    if leaderboard and any("folds" in row for row in leaderboard):
        summary["folds"] = max(int(_metric(row, "folds")) for row in leaderboard)
    return summary


def _write_artifacts(output_dir: Path, result: dict[str, Any], leaderboard: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(leaderboard).to_csv(output_dir / "walk_forward_leaderboard.csv", index=False)
    (output_dir / "walk_forward_leaderboard.json").write_text(json.dumps(leaderboard, indent=2, sort_keys=True), encoding="utf-8")
    if result.get("folds"):
        pd.DataFrame(result["folds"]).to_csv(output_dir / "walk_forward_folds.csv", index=False)
    manifest = {
        "config": result["config"],
        "summary": result["summary"],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _grid_from_mapping(data: dict[str, Any]) -> ExperimentGridConfig:
    return ExperimentGridConfig(
        markets=tuple(data.get("markets", ExperimentGridConfig.markets)),
        factor_source=str(data.get("factor_source", ExperimentGridConfig.factor_source)),
        factor_names=tuple(data.get("factor_names", ExperimentGridConfig.factor_names)),
        factor_windows=tuple(int(value) for value in data.get("factor_windows", ExperimentGridConfig.factor_windows)),
        factor_input_root=Path(data["factor_input_root"]) if data.get("factor_input_root") else None,
        factor_input_required=bool(data.get("factor_input_required", ExperimentGridConfig.factor_input_required)),
        moneyflow_input_root=Path(data["moneyflow_input_root"]) if data.get("moneyflow_input_root") else None,
        rotation_membership_root=(
            Path(data["rotation_membership_root"]) if data.get("rotation_membership_root") else None
        ),
        rotation_membership_required=bool(
            data.get("rotation_membership_required", ExperimentGridConfig.rotation_membership_required)
        ),
        min_rotation_history_rows=(
            int(data["min_rotation_history_rows"]) if data.get("min_rotation_history_rows") is not None else None
        ),
        min_rotation_live_members=(
            int(data["min_rotation_live_members"]) if data.get("min_rotation_live_members") is not None else None
        ),
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
        regime_lookback_values=(
            tuple(int(value) for value in data["regime_lookback_values"])
            if data.get("regime_lookback_values") is not None
            else None
        ),
        target_gross_exposure=float(data.get("target_gross_exposure", ExperimentGridConfig.target_gross_exposure)),
        commission_bps=float(data["commission_bps"]) if data.get("commission_bps") is not None else None,
        slippage_bps=float(data["slippage_bps"]) if data.get("slippage_bps") is not None else None,
        market_impact_bps=float(data.get("market_impact_bps", ExperimentGridConfig.market_impact_bps)),
        max_participation_rate=float(data["max_participation_rate"]) if data.get("max_participation_rate") is not None else None,
        portfolio_value=float(data.get("portfolio_value", ExperimentGridConfig.portfolio_value)),
        min_relative_return=float(data["min_relative_return"]) if data.get("min_relative_return") is not None else None,
        max_drawdown_limit=float(data["max_drawdown_limit"]) if data.get("max_drawdown_limit") is not None else None,
        signal_start_date=data.get("signal_start_date"),
        signal_end_date=data.get("signal_end_date"),
        min_signal_average_amount=(
            float(data["min_signal_average_amount"]) if data.get("min_signal_average_amount") is not None else None
        ),
        signal_amount_window=int(data.get("signal_amount_window", ExperimentGridConfig.signal_amount_window)),
        output_dir=None,
        rank_by=str(data.get("rank_by", ExperimentGridConfig.rank_by)),
        min_trades=int(data.get("min_trades", ExperimentGridConfig.min_trades)),
        precompute_factor_matrix=bool(data.get("precompute_factor_matrix", ExperimentGridConfig.precompute_factor_matrix)),
    )


def _config_dict(config: WalkForwardConfig) -> dict[str, Any]:
    data = asdict(config)
    data["output_dir"] = str(config.output_dir) if config.output_dir is not None else None
    data["experiment_grid"]["output_dir"] = None
    data["experiment_grid"]["factor_input_root"] = (
        str(config.experiment_grid.factor_input_root) if config.experiment_grid.factor_input_root is not None else None
    )
    data["experiment_grid"]["moneyflow_input_root"] = (
        str(config.experiment_grid.moneyflow_input_root) if config.experiment_grid.moneyflow_input_root is not None else None
    )
    data["experiment_grid"]["rotation_membership_root"] = (
        str(config.experiment_grid.rotation_membership_root)
        if config.experiment_grid.rotation_membership_root is not None
        else None
    )
    data["experiment_grid"]["markets"] = list(config.experiment_grid.markets)
    data["experiment_grid"]["factor_names"] = list(config.experiment_grid.factor_names)
    data["experiment_grid"]["factor_windows"] = list(config.experiment_grid.factor_windows)
    data["experiment_grid"]["top_n_values"] = list(config.experiment_grid.top_n_values)
    data["experiment_grid"]["cost_bps_values"] = list(config.experiment_grid.cost_bps_values)
    data["experiment_grid"]["rebalance_intervals"] = list(config.experiment_grid.rebalance_intervals)
    data["experiment_grid"]["regime_lookback_values"] = (
        list(config.experiment_grid.regime_lookback_values)
        if config.experiment_grid.regime_lookback_values is not None
        else None
    )
    return data


def _metric(row: dict[str, Any] | None, key: str) -> float:
    if row is None:
        return 0.0
    try:
        value = float(row.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) else 0.0


def _metric_or(row: dict[str, Any] | None, key: str, default: float) -> float:
    if row is None or key not in row:
        return default
    try:
        value = float(row.get(key))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) else default


def _mean_metric(rows: list[dict[str, Any]], key: str) -> float:
    values = [_metric(row, key) for row in rows]
    return sum(values) / len(values) if values else 0.0


def _min_metric(rows: list[dict[str, Any]], key: str) -> float:
    values = [_metric(row, key) for row in rows]
    return min(values) if values else 0.0


def _max_metric(rows: list[dict[str, Any]], key: str, default: float = 0.0) -> float:
    values = [_metric_or(row, key, default) for row in rows]
    return max(values) if values else default


def _dedupe_reason_list(rows: list[dict[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for row in rows:
        for reason in row.get("rejection_reasons", []) or []:
            text = str(reason)
            if text not in reasons:
                reasons.append(text)
    return reasons


def _aggregate_data_mode(rows: list[dict[str, Any]]) -> str:
    modes = {str(row.get("data_mode", "unknown")) for row in rows}
    if not modes:
        return "unknown"
    if len(modes) == 1:
        return next(iter(modes))
    return "mixed"


def _aggregate_status(rows: list[dict[str, Any]], key: str) -> str:
    statuses = {str(row.get(key, "unknown")) for row in rows}
    if not statuses:
        return "unknown"
    if len(statuses) == 1:
        return next(iter(statuses))
    if "failed" in statuses:
        return "failed"
    if "missing" in statuses:
        return "missing"
    return "mixed"


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
