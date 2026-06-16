from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.research.pipeline import ResearchPipelineConfig, run_research_pipeline


@dataclass(frozen=True)
class ExperimentGridConfig:
    markets: tuple[str, ...] = ("CN", "HK", "US", "CRYPTO")
    factor_source: str = "technical"
    factor_names: tuple[str, ...] = (
        "momentum_2",
        "reversal_2",
        "volatility_2",
        "volume_change_2",
        "liquidity_2",
    )
    factor_windows: tuple[int, ...] = (2, 3)
    factor_input_root: Path | None = None
    factor_input_required: bool = False
    moneyflow_input_root: Path | None = None
    top_n_values: tuple[int, ...] = (1, 2)
    cost_bps_values: tuple[float, ...] = (0.0, 5.0, 10.0)
    start_date: str | None = None
    end_date: str | None = None
    forward_horizon: int = 1
    execution_lag: int = 1
    rebalance_intervals: tuple[int, ...] = (1,)
    quantiles: int = 2
    portfolio_scope: str | None = None
    periods_per_year: float | None = None
    benchmark_asset_id: str | None = None
    cash_annual_return: float = 0.0
    regime_filter: bool = False
    regime_lookback: int = 20
    target_gross_exposure: float = 1.0
    commission_bps: float | None = None
    slippage_bps: float | None = None
    market_impact_bps: float = 0.0
    max_participation_rate: float | None = None
    portfolio_value: float = 1_000_000.0
    min_relative_return: float | None = None
    max_drawdown_limit: float | None = None
    signal_start_date: str | None = None
    signal_end_date: str | None = None
    output_dir: Path | None = None
    rank_by: str = "sharpe"
    min_trades: int = 1


@dataclass(frozen=True)
class ExperimentCase:
    case_id: str
    market: str
    factor_source: str
    factor_name: str
    factor_windows: tuple[int, ...]
    top_n: int
    cost_bps: float
    rebalance_interval: int


def build_experiment_cases(config: ExperimentGridConfig) -> list[ExperimentCase]:
    cases = []
    for market in config.markets:
        for factor_name in config.factor_names:
            for top_n in config.top_n_values:
                for cost_bps in config.cost_bps_values:
                    for rebalance_interval in config.rebalance_intervals:
                        cases.append(
                            ExperimentCase(
                                case_id=_case_id(market, factor_name, top_n, cost_bps, rebalance_interval),
                                market=market.upper(),
                                factor_source=config.factor_source,
                                factor_name=factor_name,
                                factor_windows=config.factor_windows,
                                top_n=int(top_n),
                                cost_bps=float(cost_bps),
                                rebalance_interval=int(rebalance_interval),
                            )
                        )
    return cases


def load_experiment_grid_config(path: str | Path) -> ExperimentGridConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    return ExperimentGridConfig(
        markets=tuple(data.get("markets", ExperimentGridConfig.markets)),
        factor_source=str(data.get("factor_source", ExperimentGridConfig.factor_source)),
        factor_names=tuple(data.get("factor_names", ExperimentGridConfig.factor_names)),
        factor_windows=tuple(int(value) for value in data.get("factor_windows", ExperimentGridConfig.factor_windows)),
        factor_input_root=Path(data["factor_input_root"]) if data.get("factor_input_root") else None,
        factor_input_required=bool(data.get("factor_input_required", ExperimentGridConfig.factor_input_required)),
        moneyflow_input_root=Path(data["moneyflow_input_root"]) if data.get("moneyflow_input_root") else None,
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
        output_dir=Path(data["output_dir"]) if data.get("output_dir") else None,
        rank_by=str(data.get("rank_by", ExperimentGridConfig.rank_by)),
        min_trades=int(data.get("min_trades", ExperimentGridConfig.min_trades)),
    )


def run_experiment_grid(bars: pd.DataFrame, config: ExperimentGridConfig) -> dict[str, Any]:
    _validate_config(config)
    rows = [_run_case(bars, config, case) for case in build_experiment_cases(config)]
    leaderboard = _rank_rows(rows, config.rank_by)
    result = {
        "config": _config_dict(config),
        "summary": _summary(leaderboard),
        "leaderboard": leaderboard,
    }
    if config.output_dir is not None:
        _write_grid_artifacts(config.output_dir, result, leaderboard)
    return result


def _run_case(bars: pd.DataFrame, grid_config: ExperimentGridConfig, case: ExperimentCase) -> dict[str, Any]:
    try:
        output_dir = grid_config.output_dir / case.case_id if grid_config.output_dir is not None else None
        result = run_research_pipeline(
            bars,
            ResearchPipelineConfig(
                factor_name=case.factor_name,
                factor_source=grid_config.factor_source,
                factor_windows=case.factor_windows,
                factor_input_root=grid_config.factor_input_root,
                factor_input_required=grid_config.factor_input_required,
                moneyflow_input_root=grid_config.moneyflow_input_root,
                market=case.market,
                start_date=grid_config.start_date,
                end_date=grid_config.end_date,
                forward_horizon=grid_config.forward_horizon,
                execution_lag=grid_config.execution_lag,
                rebalance_interval=case.rebalance_interval,
                quantiles=grid_config.quantiles,
                top_n=case.top_n,
                cost_bps=case.cost_bps,
                portfolio_scope=grid_config.portfolio_scope,
                periods_per_year=grid_config.periods_per_year,
                benchmark_asset_id=grid_config.benchmark_asset_id,
                cash_annual_return=grid_config.cash_annual_return,
                regime_filter=grid_config.regime_filter,
                regime_lookback=grid_config.regime_lookback,
                target_gross_exposure=grid_config.target_gross_exposure,
                commission_bps=grid_config.commission_bps,
                slippage_bps=grid_config.slippage_bps,
                market_impact_bps=grid_config.market_impact_bps,
                max_participation_rate=grid_config.max_participation_rate,
                portfolio_value=grid_config.portfolio_value,
                min_relative_return=grid_config.min_relative_return,
                max_drawdown_limit=grid_config.max_drawdown_limit,
                signal_start_date=grid_config.signal_start_date,
                signal_end_date=grid_config.signal_end_date,
                output_dir=output_dir,
            ),
        )
        trades = int(result["artifact_rows"]["trades"])
        status = "completed" if trades >= grid_config.min_trades else "no_trades"
        return _row(case, status, None, trades, result)
    except Exception as exc:
        return _row(case, "failed", str(exc), 0, None)


def _row(case: ExperimentCase, status: str, error: str | None, trades: int, result: dict[str, Any] | None) -> dict[str, Any]:
    metrics = result["metrics"] if result is not None else {}
    benchmark_metrics = result["benchmark_metrics"] if result is not None else {}
    decision = result["decision"] if result is not None else {}
    factor_summary = result["factor_summary"] if result is not None else {}
    artifact_rows = result["artifact_rows"] if result is not None else {}
    group_summary = _group_return_summary(result.get("group_returns", []) if result is not None else [])
    long_short_summary = _long_short_summary(result.get("long_short", []) if result is not None else [])
    return _sanitize(
        {
            "case_id": case.case_id,
            "market": case.market,
            "factor_source": case.factor_source,
            "factor_name": case.factor_name,
            "factor_windows": list(case.factor_windows),
            "top_n": case.top_n,
            "cost_bps": case.cost_bps,
            "rebalance_interval": case.rebalance_interval,
            "status": status,
            "error": error,
            "data_mode": result["data_mode"] if result is not None else "unknown",
            "trades": trades,
            "holdings": int(_number(artifact_rows.get("holdings"), 0.0)),
            "total_return": _number(metrics.get("total_return"), 0.0),
            "annualized_return": _number(metrics.get("annualized_return"), 0.0),
            "annualized_volatility": _number(metrics.get("annualized_volatility"), 0.0),
            "sharpe": _number(metrics.get("sharpe"), 0.0),
            "max_drawdown": _number(metrics.get("max_drawdown"), 0.0),
            "win_rate": _number(metrics.get("win_rate"), 0.0),
            "turnover": _number(metrics.get("turnover"), 0.0),
            "average_holdings": _number(metrics.get("average_holdings"), 0.0),
            "avg_cost_rate": _number(metrics.get("avg_cost_rate"), 0.0),
            "max_cost_rate": _number(metrics.get("max_cost_rate"), 0.0),
            "avg_participation_rate": _number(metrics.get("avg_participation_rate"), 0.0),
            "max_participation_rate": _number(metrics.get("max_participation_rate"), 0.0),
            "capacity_limited_trades": int(_number(metrics.get("capacity_limited_trades"), 0.0)),
            "benchmark_total_return": _number(benchmark_metrics.get("benchmark_total_return"), 0.0),
            "relative_return": _number(benchmark_metrics.get("relative_return"), 0.0),
            "excess_over_cash": _number(benchmark_metrics.get("excess_over_cash"), 0.0),
            "decision_status": str(decision.get("decision_status", "unknown")),
            "decision_reasons": decision.get("rejection_reasons", []),
            "mean_ic": _number(factor_summary.get("mean_ic"), 0.0),
            "mean_rank_ic": _number(factor_summary.get("mean_rank_ic"), 0.0),
            "icir": _number(factor_summary.get("icir"), 0.0),
            "ic_observations": int(_number(factor_summary.get("ic_observations"), 0.0)),
            "positive_ic_rate": _number(factor_summary.get("positive_ic_rate"), 0.0),
            "ic_t_stat": _number(factor_summary.get("ic_t_stat"), 0.0),
            "ic_p_value": _number(factor_summary.get("ic_p_value"), 1.0),
            "rank_ic_t_stat": _number(factor_summary.get("rank_ic_t_stat"), 0.0),
            "rank_ic_p_value": _number(factor_summary.get("rank_ic_p_value"), 1.0),
            "significance_status": str(factor_summary.get("significance_status", "unknown")),
            "long_short_mean_return": long_short_summary["mean_return"],
            "long_short_positive_rate": long_short_summary["positive_rate"],
            "long_short_observations": long_short_summary["observations"],
            "quantile_bottom_mean_return": group_summary["bottom_mean_return"],
            "quantile_top_mean_return": group_summary["top_mean_return"],
            "quantile_spread_mean_return": group_summary["spread_mean_return"],
        }
    )


def _long_short_summary(rows: Any) -> dict[str, float | int]:
    frame = pd.DataFrame(rows)
    if frame.empty or "long_short_return" not in frame.columns:
        return {"mean_return": 0.0, "positive_rate": 0.0, "observations": 0}
    values = pd.to_numeric(frame["long_short_return"], errors="coerce").dropna()
    if values.empty:
        return {"mean_return": 0.0, "positive_rate": 0.0, "observations": 0}
    return {
        "mean_return": float(values.mean()),
        "positive_rate": float((values > 0.0).mean()),
        "observations": int(len(values)),
    }


def _group_return_summary(rows: Any) -> dict[str, float]:
    frame = pd.DataFrame(rows)
    if frame.empty or "quantile" not in frame.columns or "mean_forward_return" not in frame.columns:
        return {"bottom_mean_return": 0.0, "top_mean_return": 0.0, "spread_mean_return": 0.0}
    source = frame.copy()
    source["quantile"] = pd.to_numeric(source["quantile"], errors="coerce")
    source["mean_forward_return"] = pd.to_numeric(source["mean_forward_return"], errors="coerce")
    source = source.dropna(subset=["quantile", "mean_forward_return"])
    if source.empty:
        return {"bottom_mean_return": 0.0, "top_mean_return": 0.0, "spread_mean_return": 0.0}
    bottom = float(source.loc[source["quantile"] == source["quantile"].min(), "mean_forward_return"].mean())
    top = float(source.loc[source["quantile"] == source["quantile"].max(), "mean_forward_return"].mean())
    return {
        "bottom_mean_return": bottom,
        "top_mean_return": top,
        "spread_mean_return": top - bottom,
    }


def _rank_rows(rows: list[dict[str, Any]], rank_by: str) -> list[dict[str, Any]]:
    ranked = sorted(rows, key=lambda row: (_status_order(str(row["status"])), -_metric_value(row.get(rank_by)), str(row["case_id"])))
    return [{**row, "rank": index + 1} for index, row in enumerate(ranked)]


def _status_order(status: str) -> int:
    if status == "completed":
        return 0
    if status == "no_trades":
        return 1
    return 2


def _metric_value(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return float("-inf")
    return number if math.isfinite(number) else float("-inf")


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _summary(leaderboard: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "cases": len(leaderboard),
        "completed": sum(1 for row in leaderboard if row["status"] == "completed"),
        "no_trades": sum(1 for row in leaderboard if row["status"] == "no_trades"),
        "failed": sum(1 for row in leaderboard if row["status"] == "failed"),
    }


def _validate_config(config: ExperimentGridConfig) -> None:
    windows = set(config.factor_windows)
    mismatches = []
    for factor_name in config.factor_names:
        window = _parse_factor_window(factor_name)
        if window is not None and window not in windows:
            mismatches.append(factor_name)
    if mismatches:
        raise ValueError(
            "factor_names reference windows that are not in factor_windows: "
            + ", ".join(sorted(mismatches))
        )


def _parse_factor_window(factor_name: str) -> int | None:
    for prefix in ("risk_adjusted_momentum", "momentum", "reversal", "volatility", "volume_change", "liquidity"):
        marker = f"{prefix}_"
        if factor_name.startswith(marker):
            try:
                return int(factor_name.removeprefix(marker))
            except ValueError:
                return None
    return None


def _write_grid_artifacts(output_dir: Path, result: dict[str, Any], leaderboard: list[dict[str, Any]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(leaderboard).to_csv(output_dir / "leaderboard.csv", index=False)
    (output_dir / "leaderboard.json").write_text(json.dumps(leaderboard, indent=2, sort_keys=True), encoding="utf-8")
    manifest = {
        "config": result["config"],
        "summary": result["summary"],
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _config_dict(config: ExperimentGridConfig) -> dict[str, Any]:
    data = asdict(config)
    data["markets"] = list(config.markets)
    data["factor_input_root"] = str(config.factor_input_root) if config.factor_input_root is not None else None
    data["moneyflow_input_root"] = str(config.moneyflow_input_root) if config.moneyflow_input_root is not None else None
    data["factor_names"] = list(config.factor_names)
    data["factor_windows"] = list(config.factor_windows)
    data["top_n_values"] = list(config.top_n_values)
    data["cost_bps_values"] = list(config.cost_bps_values)
    data["rebalance_intervals"] = list(config.rebalance_intervals)
    data["output_dir"] = str(config.output_dir) if config.output_dir is not None else None
    return data


def _case_id(market: str, factor_name: str, top_n: int, cost_bps: float, rebalance_interval: int) -> str:
    cost = f"{cost_bps:g}".replace(".", "p")
    return f"{market.upper()}_{factor_name}_top{top_n}_cost{cost}_reb{rebalance_interval}"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
