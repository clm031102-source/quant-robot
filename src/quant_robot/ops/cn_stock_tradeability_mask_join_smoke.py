from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.backtest.engine import run_factor_backtest
from quant_robot.ops.cn_stock_tradeability_gate import (
    CNStockTradeabilityPolicy,
    build_cn_stock_tradeability_frame,
)


STAGE = "cn_stock_tradeability_mask_join_smoke"
MASK_COLUMNS = [
    "entry_tradeable",
    "exit_tradeable",
    "suspended_official",
    "limit_up_official",
    "limit_down_official",
    "st_flag_official",
    "blocked_reasons",
]


def run_cn_stock_tradeability_mask_join_smoke(
    *,
    factors: pd.DataFrame,
    bars: pd.DataFrame,
    stock_basic: pd.DataFrame | None = None,
    stk_limit: pd.DataFrame | None = None,
    suspension: pd.DataFrame | None = None,
    namechange: pd.DataFrame | None = None,
    output_dir: str | Path,
    top_n: int = 10,
    holding_period: int = 1,
    execution_lag: int = 1,
    cost_bps: float = 0.0,
    portfolio_scope: str = "market",
    policy: CNStockTradeabilityPolicy | None = None,
) -> dict[str, Any]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    factor_frame = _normalize_keys(factors)
    bar_frame = _normalize_keys(bars)
    tradeability = build_cn_stock_tradeability_frame(
        bar_frame,
        stock_basic,
        policy=policy,
        stk_limit=stk_limit,
        suspension=suspension,
        namechange=namechange,
    )
    masks = tradeability[["date", "asset_id", "market", *MASK_COLUMNS]].copy()
    enriched_bars = bar_frame.merge(masks, on=["date", "asset_id", "market"], how="left")
    factor_mask_join = factor_frame.merge(
        masks,
        on=["date", "asset_id", "market"],
        how="left",
        indicator=True,
    )

    backtest = run_factor_backtest(
        factor_frame,
        enriched_bars,
        top_n=top_n,
        cost_bps=cost_bps,
        portfolio_scope=portfolio_scope,
        holding_period=holding_period,
        execution_lag=execution_lag,
    )
    summary = _summary(factor_frame, factor_mask_join, tradeability, backtest.metrics, backtest.trades)
    report: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": summary,
        "backtest_metrics": _json_safe_dict(backtest.metrics),
        "promotion_allowed": False,
        "promotion_blockers": [
            "mask_join_smoke_is_not_profitability_evidence",
            "no_long_cycle_same_parameter_replay",
            "no_cost_capacity_walk_forward",
            "no_regime_or_final_holdout_audit",
        ],
    }
    (output_path / f"{STAGE}.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    (output_path / f"{STAGE}.md").write_text(render_markdown(report), encoding="utf-8")
    return report


def render_markdown(report: dict[str, Any]) -> str:
    summary = report.get("summary", {})
    lines = [
        "# CN Stock Tradeability Mask Join Smoke",
        "",
        f"- Stage: {report.get('stage', STAGE)}",
        f"- Generated at: {report.get('generated_at', '')}",
        f"- Factor matrix join status: {summary.get('factor_matrix_join_status', '')}",
        f"- Portfolio execution mask status: {summary.get('portfolio_execution_mask_status', '')}",
        f"- Factor rows: {summary.get('factor_rows', 0)}",
        f"- Factor rows with tradeability mask: {summary.get('factor_rows_with_tradeability_mask', 0)}",
        f"- Official mask hit rows: {summary.get('official_mask_hit_rows', 0)}",
        f"- Backtest trades: {summary.get('backtest_trades', 0)}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in report.get("promotion_blockers", []))
    lines.append("")
    return "\n".join(lines)


def _summary(
    factors: pd.DataFrame,
    factor_mask_join: pd.DataFrame,
    tradeability: pd.DataFrame,
    backtest_metrics: dict[str, Any],
    trades: pd.DataFrame,
) -> dict[str, Any]:
    factor_rows = int(len(factors))
    joined_rows = int((factor_mask_join["_merge"] == "both").sum()) if "_merge" in factor_mask_join else 0
    official_mask_hit_rows = int(
        tradeability[["suspended_official", "limit_up_official", "limit_down_official", "st_flag_official"]]
        .fillna(False)
        .any(axis=1)
        .sum()
    )
    factor_join_status = "pass" if factor_rows > 0 and joined_rows == factor_rows else "fail"
    metric_keys = {
        "trades_filtered_entry_tradeability",
        "trades_filtered_exit_tradeability",
        "trades_delayed_exit_tradeability",
        "tradeability_filtered_trades",
    }
    portfolio_status = "pass" if metric_keys.issubset(backtest_metrics.keys()) else "fail"
    return {
        "factor_rows": factor_rows,
        "factor_rows_with_tradeability_mask": joined_rows,
        "factor_matrix_join_status": factor_join_status,
        "portfolio_execution_mask_status": portfolio_status,
        "official_mask_hit_rows": official_mask_hit_rows,
        "backtest_trades": int(len(trades)),
        "trades_filtered_entry_tradeability": int(backtest_metrics.get("trades_filtered_entry_tradeability", 0)),
        "trades_filtered_exit_tradeability": int(backtest_metrics.get("trades_filtered_exit_tradeability", 0)),
        "trades_delayed_exit_tradeability": int(backtest_metrics.get("trades_delayed_exit_tradeability", 0)),
        "tradeability_filtered_trades": int(backtest_metrics.get("tradeability_filtered_trades", 0)),
    }


def _normalize_keys(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["date"] = pd.to_datetime(result["date"]).dt.date
    result["asset_id"] = result["asset_id"].astype(str)
    result["market"] = result["market"].astype(str).str.upper()
    return result


def _json_safe_dict(values: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in values.items():
        if hasattr(value, "item"):
            value = value.item()
        if hasattr(value, "isoformat"):
            value = value.isoformat()
        safe[key] = value
    return safe
