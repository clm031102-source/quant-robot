from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import median
from typing import Any

import pandas as pd

from quant_robot.research.decision import regime_allowed_dates
from quant_robot.validation.walk_forward import (
    WalkForwardConfig,
    _rolling_enabled,
    _rolling_folds,
    _split_bars,
)


@dataclass(frozen=True)
class ETFValidationPreflightPolicy:
    min_assets: int = 12
    min_rebalance_opportunities_per_fold: int = 20
    min_median_allowed_rebalance_dates: int = 20
    max_zero_allowed_fold_rate: float = 0.10


def build_etf_validation_preflight(
    bars: pd.DataFrame,
    config: WalkForwardConfig,
    *,
    policy: ETFValidationPreflightPolicy | None = None,
) -> dict[str, Any]:
    policy = policy or ETFValidationPreflightPolicy()
    frame = _market_bars(bars, config)
    fold_summaries = _fold_summaries(frame, config)
    blockers = _blockers(frame, fold_summaries, policy)
    summary = _summary(frame, fold_summaries, config, policy)
    packet = {
        "stage": "cn_etf_validation_preflight",
        "generated_at": date.today().isoformat(),
        "status": "cleared" if not blockers else "blocked",
        "summary": summary,
        "policy": {
            "min_assets": policy.min_assets,
            "min_rebalance_opportunities_per_fold": policy.min_rebalance_opportunities_per_fold,
            "min_median_allowed_rebalance_dates": policy.min_median_allowed_rebalance_dates,
            "max_zero_allowed_fold_rate": policy.max_zero_allowed_fold_rate,
        },
        "folds": fold_summaries,
        "decision": {
            "preflight_cleared": not blockers,
            "blockers": blockers,
        },
        "safety": "Research-to-review only. No broker connection, no account reads, no order placement, no live trading.",
        "live_boundary_allowed": False,
    }
    packet["markdown"] = render_etf_validation_preflight_markdown(packet)
    return packet


def write_etf_validation_preflight(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_packet = {key: value for key, value in packet.items() if key != "markdown"}
    (output_path / "etf_validation_preflight.json").write_text(
        json.dumps(json_packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "etf_validation_preflight.md").write_text(
        str(packet.get("markdown", "")),
        encoding="utf-8",
    )


def render_etf_validation_preflight_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    lines = [
        "# CN ETF Validation Preflight",
        "",
        f"- Status: {packet.get('status', 'unknown')}",
        f"- Markets: {', '.join(_list(summary.get('markets')))}",
        f"- Asset count: {summary.get('asset_count')}",
        f"- Fold count: {summary.get('fold_count')}",
        f"- Rebalance interval: {summary.get('rebalance_interval')}",
        f"- Min rebalance opportunities per fold: {summary.get('min_rebalance_opportunities')}",
        f"- Median regime-allowed rebalance dates: {summary.get('median_allowed_rebalance_dates')}",
        f"- Zero allowed fold rate: {summary.get('zero_allowed_fold_rate')}",
        f"- Live boundary allowed: {packet.get('live_boundary_allowed', False)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = _list(decision.get("blockers"))
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.extend(["", f"Safety: {packet.get('safety', '')}", ""])
    return "\n".join(lines)


def _market_bars(bars: pd.DataFrame, config: WalkForwardConfig) -> pd.DataFrame:
    _require_columns(bars, ["date", "asset_id", "market", "adj_close"])
    markets = {str(market).upper() for market in config.experiment_grid.markets if str(market).upper() != "ALL"}
    frame = bars.copy()
    if markets:
        frame = frame[frame["market"].astype(str).str.upper().isin(markets)].copy()
    if config.experiment_grid.asset_universe_path is not None:
        selected_asset_ids = _load_asset_universe_ids(config.experiment_grid.asset_universe_path)
        frame = frame[frame["asset_id"].astype(str).isin(selected_asset_ids)].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _load_asset_universe_ids(path: str | Path) -> set[str]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        values = payload.get("selected_asset_ids", [])
    elif isinstance(payload, list):
        values = payload
    else:
        raise ValueError("asset_universe_path must contain a JSON list or selected_asset_ids")
    selected = {str(value) for value in values if str(value)}
    if not selected:
        raise ValueError("asset_universe_path contains no selected_asset_ids")
    return selected


def _fold_summaries(bars: pd.DataFrame, config: WalkForwardConfig) -> list[dict[str, Any]]:
    folds = _raw_folds(bars, config)
    rebalance_interval = min(int(value) for value in config.experiment_grid.rebalance_intervals)
    regime_dates_by_lookback = _regime_dates_by_lookback(bars, config)
    summaries: list[dict[str, Any]] = []
    for index, fold in enumerate(folds, start=1):
        test_dates = sorted(pd.to_datetime(fold["test_bars"]["date"]).dt.date.unique())
        signal_dates = test_dates[::rebalance_interval]
        allowed_counts = []
        for allowed_dates in regime_dates_by_lookback.values():
            allowed_counts.append(sum(1 for signal_date in signal_dates if signal_date in allowed_dates))
        allowed_rebalance_dates = min(allowed_counts) if allowed_counts else len(signal_dates)
        summaries.append(
            {
                "fold": int(fold.get("fold", index)),
                "test_start_date": str(test_dates[0]) if test_dates else None,
                "test_end_date": str(test_dates[-1]) if test_dates else None,
                "rebalance_opportunities": len(signal_dates),
                "allowed_rebalance_dates": int(allowed_rebalance_dates),
                "allowed_rebalance_rate": (
                    float(allowed_rebalance_dates) / float(len(signal_dates)) if signal_dates else 0.0
                ),
            }
        )
    return summaries


def _raw_folds(bars: pd.DataFrame, config: WalkForwardConfig) -> list[dict[str, Any]]:
    if _rolling_enabled(config):
        return _rolling_folds(bars, config)
    train_bars, test_bars = _split_bars(bars, config.split_date)
    return [
        {
            "fold": 1,
            "train_bars": train_bars,
            "test_bars": test_bars,
        }
    ]


def _regime_dates_by_lookback(bars: pd.DataFrame, config: WalkForwardConfig) -> dict[int, set[Any]]:
    if not config.experiment_grid.regime_filter:
        return {}
    lookbacks = (
        config.experiment_grid.regime_lookback_values
        if config.experiment_grid.regime_lookback_values is not None
        else (config.experiment_grid.regime_lookback,)
    )
    dates_by_lookback: dict[int, set[Any]] = {}
    for lookback in lookbacks:
        rows = regime_allowed_dates(
            bars,
            benchmark_asset_id=config.experiment_grid.benchmark_asset_id,
            lookback=int(lookback),
        )
        dates_by_lookback[int(lookback)] = set(rows.loc[rows["regime_allowed"], "date"])
    return dates_by_lookback


def _summary(
    bars: pd.DataFrame,
    fold_summaries: list[dict[str, Any]],
    config: WalkForwardConfig,
    policy: ETFValidationPreflightPolicy,
) -> dict[str, Any]:
    allowed_values = [int(item["allowed_rebalance_dates"]) for item in fold_summaries]
    opportunity_values = [int(item["rebalance_opportunities"]) for item in fold_summaries]
    zero_allowed = sum(1 for value in allowed_values if value == 0)
    return {
        "markets": list(config.experiment_grid.markets),
        "asset_count": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "date_count": int(pd.to_datetime(bars["date"]).dt.date.nunique()) if "date" in bars else 0,
        "fold_count": len(fold_summaries),
        "rebalance_interval": min(int(value) for value in config.experiment_grid.rebalance_intervals),
        "min_test_trades": int(config.min_test_trades),
        "min_rebalance_opportunities": min(opportunity_values) if opportunity_values else 0,
        "median_allowed_rebalance_dates": float(median(allowed_values)) if allowed_values else 0.0,
        "min_allowed_rebalance_dates": min(allowed_values) if allowed_values else 0,
        "zero_allowed_fold_count": zero_allowed,
        "zero_allowed_fold_rate": float(zero_allowed) / float(len(allowed_values)) if allowed_values else 1.0,
        "policy_min_assets": policy.min_assets,
        "policy_min_rebalance_opportunities_per_fold": policy.min_rebalance_opportunities_per_fold,
        "policy_min_median_allowed_rebalance_dates": policy.min_median_allowed_rebalance_dates,
    }


def _blockers(
    bars: pd.DataFrame,
    fold_summaries: list[dict[str, Any]],
    policy: ETFValidationPreflightPolicy,
) -> list[str]:
    blockers: list[str] = []
    asset_count = int(bars["asset_id"].nunique()) if "asset_id" in bars else 0
    opportunities = [int(item["rebalance_opportunities"]) for item in fold_summaries]
    allowed_values = [int(item["allowed_rebalance_dates"]) for item in fold_summaries]
    if not fold_summaries:
        blockers.append("no_walk_forward_folds")
    if asset_count < policy.min_assets:
        blockers.append("asset_count_below_minimum")
    if opportunities and min(opportunities) < policy.min_rebalance_opportunities_per_fold:
        blockers.append("rebalance_opportunities_below_minimum")
    if allowed_values and median(allowed_values) < policy.min_median_allowed_rebalance_dates:
        blockers.append("median_regime_allowed_rebalance_dates_below_minimum")
    zero_rate = float(sum(1 for value in allowed_values if value == 0)) / float(len(allowed_values)) if allowed_values else 1.0
    if zero_rate > policy.max_zero_allowed_fold_rate:
        blockers.append("zero_allowed_fold_rate_above_limit")
    return blockers


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"ETF validation preflight missing columns: {', '.join(missing)}")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value is None:
        return []
    return [str(value)]
