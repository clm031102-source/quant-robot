from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.data.quality import validate_market_data
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.reports.plots import write_line_svg
from quant_robot.research.groups import quantile_group_returns
from quant_robot.research.ic import compute_ic
from quant_robot.research.labels import make_forward_returns
from quant_robot.research.long_short import long_short_returns


@dataclass(frozen=True)
class ResearchPipelineConfig:
    factor_name: str = "momentum_2"
    factor_windows: tuple[int, ...] = (2, 3)
    market: str = "ALL"
    start_date: str | None = None
    end_date: str | None = None
    forward_horizon: int = 1
    execution_lag: int = 1
    quantiles: int = 2
    top_n: int = 2
    cost_bps: float = 5.0
    output_dir: Path | None = None


def run_research_pipeline(bars: pd.DataFrame, config: ResearchPipelineConfig) -> dict[str, Any]:
    filtered = _filter_bars(bars, config)
    validate_market_data(filtered)
    factors = compute_basic_factors(filtered, windows=config.factor_windows)
    labels = make_forward_returns(filtered, horizons=(config.forward_horizon,), execution_lag=config.execution_lag)
    selected = factors[factors["factor_name"] == config.factor_name].dropna(subset=["factor_value"]).reset_index(drop=True)
    ic = compute_ic(selected, labels)
    groups = quantile_group_returns(selected, labels, quantiles=config.quantiles)
    long_short = long_short_returns(selected, labels, quantiles=config.quantiles)
    backtest = run_factor_backtest(selected, filtered, top_n=config.top_n, cost_bps=config.cost_bps)
    drawdown = _drawdown_curve(backtest.equity_curve)
    summary = _factor_summary(ic)
    result = _sanitize(
        {
            "data_mode": "fixture" if set(filtered["source"].astype(str)) == {"fixture"} else "research",
            "request": _config_dict(config),
            "metrics": backtest.metrics,
            "factor_summary": summary,
            "artifact_rows": {
                "bars": len(filtered),
                "factors": len(selected),
                "labels": len(labels),
                "ic": len(ic),
                "group_returns": len(groups),
                "long_short": len(long_short),
                "trades": len(backtest.trades),
                "holdings": len(backtest.positions),
            },
            "equity_curve": _records(backtest.equity_curve),
            "drawdown_curve": _records(drawdown),
            "ic": _records(ic),
            "group_returns": _records(groups),
            "long_short": _records(long_short),
            "trades": _records(backtest.trades),
            "holdings": _records(backtest.positions),
        }
    )
    if config.output_dir is not None:
        _write_artifacts(config.output_dir, result, backtest.equity_curve, drawdown, ic, groups, long_short, backtest.trades, backtest.positions)
    return result


def _filter_bars(bars: pd.DataFrame, config: ResearchPipelineConfig) -> pd.DataFrame:
    frame = bars.copy()
    if config.market.upper() != "ALL":
        frame = frame[frame["market"] == config.market.upper()]
    if config.start_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date >= pd.to_datetime(config.start_date).date()]
    if config.end_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.end_date).date()]
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _factor_summary(ic: pd.DataFrame) -> dict[str, float]:
    if ic.empty:
        return {"mean_ic": 0.0, "mean_rank_ic": 0.0, "icir": 0.0}
    clean_ic = pd.to_numeric(ic["ic"], errors="coerce").dropna()
    clean_rank = pd.to_numeric(ic["rank_ic"], errors="coerce").dropna()
    mean_ic = float(clean_ic.mean()) if not clean_ic.empty else 0.0
    std_ic = float(clean_ic.std(ddof=0)) if not clean_ic.empty else 0.0
    return {
        "mean_ic": mean_ic,
        "mean_rank_ic": float(clean_rank.mean()) if not clean_rank.empty else 0.0,
        "icir": 0.0 if std_ic == 0.0 else float(mean_ic / std_ic),
    }


def _drawdown_curve(equity_curve: pd.DataFrame) -> pd.DataFrame:
    if equity_curve.empty:
        return pd.DataFrame(columns=["date", "drawdown"])
    frame = equity_curve[["date", "equity"]].copy()
    frame["drawdown"] = frame["equity"] / frame["equity"].cummax() - 1.0
    return frame[["date", "drawdown"]]


def _write_artifacts(
    output_dir: Path,
    result: dict[str, Any],
    equity_curve: pd.DataFrame,
    drawdown: pd.DataFrame,
    ic: pd.DataFrame,
    groups: pd.DataFrame,
    long_short: pd.DataFrame,
    trades: pd.DataFrame,
    holdings: pd.DataFrame,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "metrics.json").write_text(
        json.dumps({"data_mode": result["data_mode"], **result["metrics"]}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "factor_summary.json").write_text(json.dumps(result["factor_summary"], indent=2, sort_keys=True), encoding="utf-8")
    equity_curve.to_csv(output_dir / "equity_curve.csv", index=False)
    drawdown.to_csv(output_dir / "drawdown_curve.csv", index=False)
    ic.to_csv(output_dir / "ic.csv", index=False)
    groups.to_csv(output_dir / "group_returns.csv", index=False)
    long_short.to_csv(output_dir / "long_short.csv", index=False)
    trades.to_csv(output_dir / "trades.csv", index=False)
    holdings.to_csv(output_dir / "holdings.csv", index=False)
    write_line_svg(equity_curve, "date", "equity", output_dir / "equity_curve.svg", "Research Pipeline Equity")
    write_line_svg(drawdown, "date", "drawdown", output_dir / "drawdown_curve.svg", "Research Pipeline Drawdown")
    write_line_svg(ic, "date", "ic", output_dir / "ic.svg", "Research Pipeline IC")


def _config_dict(config: ResearchPipelineConfig) -> dict[str, Any]:
    data = asdict(config)
    data["factor_windows"] = list(config.factor_windows)
    data["output_dir"] = str(config.output_dir) if config.output_dir is not None else None
    return data


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.to_dict(orient="records")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and value.__class__.__module__ == "datetime":
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
