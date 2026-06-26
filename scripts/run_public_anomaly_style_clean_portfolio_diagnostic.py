from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Sequence

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.backtest.engine import run_factor_backtest  # noqa: E402
from quant_robot.backtest.metrics import summarize_returns  # noqa: E402
from quant_robot.ops.daily_basic_non_price_public_carry_prescreen import (  # noqa: E402
    load_daily_basic_non_price_public_carry_inputs,
)
from quant_robot.ops.public_anomaly_residual_ensemble_prescreen import (  # noqa: E402
    build_public_anomaly_residual_ensemble_factor_frame,
    build_public_anomaly_style_clean_signal_frame,
    style_clean_public_anomaly_factor_name,
)
from quant_robot.ops.public_reference_multi_family_prescreen import (  # noqa: E402
    _sanitize,
    load_public_reference_multi_family_bars,
)
from quant_robot.ops.public_trend_strength_state_residual_prescreen import (  # noqa: E402
    _stock_basic_frame,
    build_public_trend_strength_state_bar_features,
    build_public_trend_strength_state_exposure_frame,
)


DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_DAILY_BASIC_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260617_daily_basic_factor_inputs"),
)
DEFAULT_STOCK_BASIC = Path("data/processed/cn_stock_metadata")
DEFAULT_OUTPUT_DIR = Path("data/reports/public_anomaly_style_clean_portfolio_diagnostic")
DEFAULT_CANDIDATES = ("public_anomaly_residual_regime_conditioned_20",)


def run_public_anomaly_style_clean_portfolio_diagnostic(
    *,
    bars_roots: Iterable[str | Path] = DEFAULT_BARS_ROOTS,
    daily_basic_roots: Iterable[str | Path] = DEFAULT_DAILY_BASIC_ROOTS,
    stock_basic: str | Path | pd.DataFrame | None = DEFAULT_STOCK_BASIC,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    candidate_factor_names: Sequence[str] = DEFAULT_CANDIDATES,
    style_clean_passes: int = 1,
    top_n_values: Sequence[int] = (30, 50, 100),
    cost_bps_values: Sequence[float] = (5.0, 10.0),
    holding_period: int = 20,
    rebalance_intervals: Sequence[int] = (5, 10),
    execution_lag: int = 1,
    min_signal_date_amount: float = 10_000_000.0,
    portfolio_value: float = 1_000_000.0,
    max_participation_rate: float = 0.05,
    market_impact_bps: float = 0.0,
    backtest_price_column: str = "adj_close",
    exclude_asset_prefixes: Sequence[str] = (),
    max_abs_daily_return_quarantine: float | None = None,
    min_overlap_adjusted_sharpe: float = 0.50,
    max_drawdown_floor: float = -0.35,
    extreme_trade_abs_return: float = 0.50,
) -> dict[str, Any]:
    bars = load_public_reference_multi_family_bars(
        tuple(Path(path) for path in bars_roots),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=False,
    )
    bars, quarantine = _apply_data_quality_quarantine(
        bars,
        exclude_asset_prefixes=exclude_asset_prefixes,
        max_abs_daily_return_quarantine=max_abs_daily_return_quarantine,
    )
    daily_basic = load_daily_basic_non_price_public_carry_inputs(
        tuple(Path(path) for path in daily_basic_roots),
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=False,
    )
    features = build_public_trend_strength_state_bar_features(
        bars,
        horizons=(int(holding_period),),
        execution_lag=execution_lag,
    )
    exposure = build_public_trend_strength_state_exposure_frame(features, _stock_basic_frame(stock_basic))
    raw_factors = build_public_anomaly_residual_ensemble_factor_frame(
        bars,
        daily_basic,
        exposure,
        candidate_factor_names=tuple(candidate_factor_names),
        min_signal_date_amount=min_signal_date_amount,
    )
    factors = build_public_anomaly_style_clean_signal_frame(
        raw_factors,
        exposure,
        raw_candidate_factor_names=tuple(candidate_factor_names),
        min_cross_section=30,
        min_industries=2,
        min_assets_per_industry=2,
        style_clean_passes=style_clean_passes,
    )
    leaderboard: list[dict[str, Any]] = []
    for raw_name in candidate_factor_names:
        factor_name = style_clean_public_anomaly_factor_name(raw_name, style_clean_passes=style_clean_passes)
        factor_slice = factors[factors["factor_name"] == factor_name].reset_index(drop=True)
        for rebalance_interval in rebalance_intervals:
            rebalanced = _filter_rebalance_dates(factor_slice, int(rebalance_interval))
            for top_n in top_n_values:
                for cost_bps in cost_bps_values:
                    backtest = run_factor_backtest(
                        rebalanced,
                        _backtest_bars(bars, backtest_price_column),
                        top_n=int(top_n),
                        cost_bps=float(cost_bps),
                        portfolio_scope="market",
                        execution_lag=execution_lag,
                        holding_period=holding_period,
                        rebalance_interval=int(rebalance_interval),
                        target_gross_exposure=1.0,
                        periods_per_year=252.0 / float(max(int(rebalance_interval), 1)),
                        market_impact_bps=market_impact_bps,
                        max_participation_rate=max_participation_rate,
                        portfolio_value=portfolio_value,
                    )
                    leaderboard.append(
                        _case_row(
                            backtest.metrics,
                            backtest.trades,
                            factor_name=factor_name,
                            top_n=int(top_n),
                            cost_bps=float(cost_bps),
                            holding_period=holding_period,
                            rebalance_interval=int(rebalance_interval),
                            portfolio_value=portfolio_value,
                            max_participation_rate=max_participation_rate,
                            min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
                            max_drawdown_floor=max_drawdown_floor,
                            extreme_trade_abs_return=extreme_trade_abs_return,
                            periods_per_year=252.0 / float(max(int(rebalance_interval), 1)),
                        )
                    )
    leaderboard = sorted(
        leaderboard,
        key=lambda row: (
            not row["diagnostic_pass"],
            -float(row["overlap_autocorr_adjusted_sharpe"]),
            -float(row["annualized_return"]),
            float(row["max_drawdown"]),
        ),
    )
    result = {
        "stage": "public_anomaly_style_clean_portfolio_diagnostic",
        "safety": "research-to-review only; no broker, account, order, or live-trading access",
        "source_context": {
            "purpose": "diagnostic conversion of style-clean public anomaly near-miss IC into costed topN portfolio metrics",
            "not_paper_ready": True,
            "promotion_allowed": False,
        },
        "thresholds": {
            "analysis_start_date": analysis_start_date,
            "analysis_end_date": analysis_end_date,
            "candidate_factor_names": list(candidate_factor_names),
            "style_clean_passes": int(style_clean_passes),
            "top_n_values": [int(value) for value in top_n_values],
            "cost_bps_values": [float(value) for value in cost_bps_values],
            "holding_period": int(holding_period),
            "rebalance_intervals": [int(value) for value in rebalance_intervals],
            "execution_lag": int(execution_lag),
            "min_signal_date_amount": float(min_signal_date_amount),
            "portfolio_value": float(portfolio_value),
            "max_participation_rate": float(max_participation_rate),
            "market_impact_bps": float(market_impact_bps),
            "backtest_price_column": backtest_price_column,
            "exclude_asset_prefixes": list(exclude_asset_prefixes),
            "max_abs_daily_return_quarantine": (
                None if max_abs_daily_return_quarantine is None else float(max_abs_daily_return_quarantine)
            ),
            "min_overlap_adjusted_sharpe": float(min_overlap_adjusted_sharpe),
            "max_drawdown_floor": float(max_drawdown_floor),
            "extreme_trade_abs_return": float(extreme_trade_abs_return),
        },
        "data_window": _data_window(bars, daily_basic, raw_factors, factors),
        "data_quality_quarantine": quarantine,
        "summary": {
            "cases": int(len(leaderboard)),
            "diagnostic_pass_cases": int(sum(row["diagnostic_pass"] for row in leaderboard)),
            "best_case_id": leaderboard[0]["case_id"] if leaderboard else None,
            "portfolio_grid_is_diagnostic_only": True,
        },
        "leaderboard": leaderboard,
    }
    write_public_anomaly_style_clean_portfolio_diagnostic(output_dir, result)
    return result


def write_public_anomaly_style_clean_portfolio_diagnostic(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "public_anomaly_style_clean_portfolio_diagnostic.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("leaderboard", [])).to_csv(
        output / "public_anomaly_style_clean_portfolio_diagnostic_leaderboard.csv",
        index=False,
    )


def _filter_rebalance_dates(factors: pd.DataFrame, rebalance_interval: int) -> pd.DataFrame:
    if factors.empty or rebalance_interval <= 1:
        return factors.copy()
    frame = factors.copy()
    frame["date"] = pd.to_datetime(frame["date"])
    dates = pd.Index(sorted(frame["date"].dropna().unique()))
    keep = set(dates[:: int(rebalance_interval)])
    return frame[frame["date"].isin(keep)].reset_index(drop=True)


def _apply_data_quality_quarantine(
    bars: pd.DataFrame,
    *,
    exclude_asset_prefixes: Sequence[str],
    max_abs_daily_return_quarantine: float | None,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    frame = bars.copy()
    excluded_by_prefix: set[str] = set()
    for prefix in exclude_asset_prefixes:
        prefix = str(prefix)
        if prefix:
            excluded_by_prefix.update(frame.loc[frame["asset_id"].astype(str).str.startswith(prefix), "asset_id"].astype(str))
    excluded_by_return: set[str] = set()
    if max_abs_daily_return_quarantine is not None:
        threshold = float(max_abs_daily_return_quarantine)
        for column in ("close", "adj_close"):
            if column not in frame:
                continue
            returns = frame.sort_values(["asset_id", "date"]).groupby("asset_id")[column].pct_change()
            excluded_by_return.update(frame.loc[returns.abs() > threshold, "asset_id"].astype(str))
    excluded = excluded_by_prefix | excluded_by_return
    if excluded:
        frame = frame[~frame["asset_id"].astype(str).isin(excluded)].reset_index(drop=True)
    return frame, {
        "excluded_assets": int(len(excluded)),
        "excluded_by_prefix_assets": int(len(excluded_by_prefix)),
        "excluded_by_extreme_daily_return_assets": int(len(excluded_by_return)),
        "remaining_assets": int(frame["asset_id"].nunique()) if "asset_id" in frame else 0,
        "remaining_rows": int(len(frame)),
    }


def _backtest_bars(bars: pd.DataFrame, price_column: str) -> pd.DataFrame:
    column = str(price_column)
    if column == "adj_close":
        return bars
    if column not in bars:
        raise ValueError(f"backtest price column is missing from bars: {column}")
    output = bars.copy()
    output["adj_close"] = pd.to_numeric(output[column], errors="coerce")
    return output


def _case_row(
    metrics: dict[str, Any],
    trades: pd.DataFrame,
    *,
    factor_name: str,
    top_n: int,
    cost_bps: float,
    holding_period: int,
    rebalance_interval: int,
    portfolio_value: float,
    max_participation_rate: float,
    min_overlap_adjusted_sharpe: float,
    max_drawdown_floor: float,
    extreme_trade_abs_return: float,
    periods_per_year: float,
) -> dict[str, Any]:
    max_abs_trade = float(trades["gross_return"].abs().max()) if not trades.empty else 0.0
    extreme_count = int((trades["gross_return"].abs() > extreme_trade_abs_return).sum()) if not trades.empty else 0
    trade_count = int(len(trades))
    extreme_rate = float(extreme_count / trade_count) if trade_count else 0.0
    stress = _extreme_excluded_metrics(
        trades,
        extreme_trade_abs_return=extreme_trade_abs_return,
        periods_per_year=periods_per_year,
    )
    blockers = []
    if _metric(metrics, "total_return") <= 0.0:
        blockers.append("non_positive_total_return")
    if _metric(metrics, "annualized_return") <= 0.0:
        blockers.append("non_positive_annualized_return")
    if _metric(metrics, "overlap_autocorr_adjusted_sharpe") < min_overlap_adjusted_sharpe:
        blockers.append("overlap_adjusted_sharpe_below_threshold")
    if _metric(metrics, "max_drawdown") < max_drawdown_floor:
        blockers.append("drawdown_below_user_tolerance_floor")
    if int(_metric(metrics, "capacity_limited_trades")) > 0:
        blockers.append("capacity_limited_trades_present")
    if extreme_rate > 0.01:
        blockers.append("extreme_trade_rate_above_one_percent")
    if stress["total_return"] <= 0.0:
        blockers.append("extreme_excluded_total_return_non_positive")
    if stress["annualized_return"] <= 0.0:
        blockers.append("extreme_excluded_annualized_return_non_positive")
    return {
        "case_id": f"{factor_name}_top{top_n}_hold{holding_period}_reb{rebalance_interval}_cost{cost_bps:g}_cap{portfolio_value:g}",
        "factor_name": factor_name,
        "top_n": int(top_n),
        "holding_period": int(holding_period),
        "rebalance_interval": int(rebalance_interval),
        "cost_bps": float(cost_bps),
        "portfolio_value": float(portfolio_value),
        "total_return": _metric(metrics, "total_return"),
        "annualized_return": _metric(metrics, "annualized_return"),
        "sharpe": _metric(metrics, "sharpe"),
        "overlap_autocorr_adjusted_sharpe": _metric(metrics, "overlap_autocorr_adjusted_sharpe"),
        "max_drawdown": _metric(metrics, "max_drawdown"),
        "win_rate": _metric(metrics, "win_rate"),
        "turnover": _metric(metrics, "turnover"),
        "average_holdings": _metric(metrics, "average_holdings"),
        "avg_participation_rate": _metric(metrics, "avg_participation_rate"),
        "max_participation_rate": _metric(metrics, "max_participation_rate"),
        "capacity_limited_trades": int(_metric(metrics, "capacity_limited_trades")),
        "max_abs_trade_gross_return": max_abs_trade,
        "extreme_trade_return_count": extreme_count,
        "extreme_trade_return_rate": extreme_rate,
        "extreme_excluded_total_return": stress["total_return"],
        "extreme_excluded_annualized_return": stress["annualized_return"],
        "extreme_excluded_sharpe": stress["sharpe"],
        "extreme_excluded_max_drawdown": stress["max_drawdown"],
        "extreme_excluded_win_rate": stress["win_rate"],
        "diagnostic_pass": not blockers,
        "blockers": blockers,
    }


def _extreme_excluded_metrics(
    trades: pd.DataFrame,
    *,
    extreme_trade_abs_return: float,
    periods_per_year: float,
) -> dict[str, float]:
    if trades.empty:
        return _empty_return_metrics()
    clean = trades[trades["gross_return"].abs() <= extreme_trade_abs_return].copy()
    if clean.empty:
        return _empty_return_metrics()
    returns = (
        clean.groupby("exit_date", as_index=False)
        .agg(period_return=("weighted_return", "sum"))
        .sort_values("exit_date")["period_return"]
    )
    return summarize_returns(returns, periods_per_year=periods_per_year)


def _empty_return_metrics() -> dict[str, float]:
    return {
        "total_return": 0.0,
        "annualized_return": 0.0,
        "sharpe": 0.0,
        "max_drawdown": 0.0,
        "win_rate": 0.0,
    }


def _metric(metrics: dict[str, Any], name: str) -> float:
    try:
        return float(metrics.get(name, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _data_window(
    bars: pd.DataFrame,
    daily_basic: pd.DataFrame,
    raw_factors: pd.DataFrame,
    clean_factors: pd.DataFrame,
) -> dict[str, Any]:
    return {
        "min_bar_date": _min_date(bars, "date"),
        "max_bar_date": _max_date(bars, "date"),
        "bar_rows": int(len(bars)),
        "bar_assets": int(bars["asset_id"].nunique()) if "asset_id" in bars else 0,
        "daily_basic_rows": int(len(daily_basic)),
        "raw_factor_rows": int(len(raw_factors)),
        "style_clean_factor_rows": int(len(clean_factors)),
    }


def _min_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].min()).date().isoformat()


def _max_date(frame: pd.DataFrame, column: str) -> str | None:
    if frame.empty or column not in frame:
        return None
    return pd.Timestamp(frame[column].max()).date().isoformat()


def _parse_int_list(value: str) -> tuple[int, ...]:
    return tuple(int(part.strip()) for part in value.split(",") if part.strip())


def _parse_float_list(value: str) -> tuple[float, ...]:
    return tuple(float(part.strip()) for part in value.split(",") if part.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a diagnostic topN portfolio conversion for style-clean public anomaly factors.")
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--daily-basic-root", action="append", default=None)
    parser.add_argument("--stock-basic", default=str(DEFAULT_STOCK_BASIC))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--candidate-factor-name", action="append", dest="candidate_factor_names")
    parser.add_argument("--style-clean-passes", type=int, default=1)
    parser.add_argument("--top-n-values", default="30,50,100")
    parser.add_argument("--cost-bps-values", default="5,10")
    parser.add_argument("--holding-period", type=int, default=20)
    parser.add_argument("--rebalance-intervals", default="5,10")
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--min-signal-date-amount", type=float, default=10_000_000.0)
    parser.add_argument("--portfolio-value", type=float, default=1_000_000.0)
    parser.add_argument("--max-participation-rate", type=float, default=0.05)
    parser.add_argument("--market-impact-bps", type=float, default=0.0)
    parser.add_argument("--backtest-price-column", default="adj_close")
    parser.add_argument("--exclude-asset-prefix", action="append", default=None)
    parser.add_argument("--max-abs-daily-return-quarantine", type=float)
    args = parser.parse_args()
    result = run_public_anomaly_style_clean_portfolio_diagnostic(
        bars_roots=tuple(Path(path) for path in (args.bars_root or DEFAULT_BARS_ROOTS)),
        daily_basic_roots=tuple(Path(path) for path in (args.daily_basic_root or DEFAULT_DAILY_BASIC_ROOTS)),
        stock_basic=Path(args.stock_basic) if args.stock_basic else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        candidate_factor_names=tuple(args.candidate_factor_names or DEFAULT_CANDIDATES),
        style_clean_passes=args.style_clean_passes,
        top_n_values=_parse_int_list(args.top_n_values),
        cost_bps_values=_parse_float_list(args.cost_bps_values),
        holding_period=args.holding_period,
        rebalance_intervals=_parse_int_list(args.rebalance_intervals),
        execution_lag=args.execution_lag,
        min_signal_date_amount=args.min_signal_date_amount,
        portfolio_value=args.portfolio_value,
        max_participation_rate=args.max_participation_rate,
        market_impact_bps=args.market_impact_bps,
        backtest_price_column=args.backtest_price_column,
        exclude_asset_prefixes=tuple(args.exclude_asset_prefix or ()),
        max_abs_daily_return_quarantine=args.max_abs_daily_return_quarantine,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "top": result["leaderboard"][:5],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
