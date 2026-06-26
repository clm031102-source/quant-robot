from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.backtest.metrics import summarize_returns
from quant_robot.ops.clean_technical_portfolio_diagnostic import overlap_metrics, sanitize


STAGE = "turnover_low_overlay_walk_forward"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


@dataclass(frozen=True)
class OverlayPolicy:
    name: str
    kind: str
    warn_drawdown: float | None = None
    cut_drawdown: float | None = None
    warn_exposure: float = 0.50
    cut_exposure: float = 0.25
    recover_drawdown: float = -0.10
    target_annual_volatility: float | None = None
    lookback_periods: int = 63
    min_exposure: float = 0.25
    max_exposure: float = 1.0
    market_lookback_periods: int | None = None
    market_momentum_threshold: float = 0.0
    market_drawdown_threshold: float = -0.10
    market_cap_exposure: float = 0.25


DEFAULT_POLICIES = (
    OverlayPolicy(name="entry_cash_no_overlay", kind="none"),
    OverlayPolicy(name="entry_cash_dd_warn10_cut20", kind="drawdown", warn_drawdown=-0.10, cut_drawdown=-0.20),
    OverlayPolicy(name="entry_cash_dd_warn15_cut25", kind="drawdown", warn_drawdown=-0.15, cut_drawdown=-0.25),
    OverlayPolicy(name="entry_cash_dd_warn20_cut30", kind="drawdown", warn_drawdown=-0.20, cut_drawdown=-0.30),
    OverlayPolicy(name="entry_cash_vol_target_6", kind="vol_target", target_annual_volatility=0.06),
    OverlayPolicy(name="entry_cash_vol_target_8", kind="vol_target", target_annual_volatility=0.08),
)

MarketExposureCaps = pd.Series | Mapping[str, pd.Series]


def run_overlay_walk_forward_from_period_returns(
    period_returns: pd.DataFrame,
    *,
    output_dir: str | Path,
    return_column: str = "entry_cash_proxy_return",
    decision_date_column: str = "entry_date",
    market_exposure_caps: MarketExposureCaps | None = None,
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
    train_years: int = 3,
    test_years: int = 1,
    step_years: int = 1,
    policies: Sequence[OverlayPolicy] = DEFAULT_POLICIES,
) -> dict[str, Any]:
    events = prepare_period_return_events(
        period_returns,
        return_column=return_column,
        decision_date_column=decision_date_column,
    )
    cap_frame = period_returns.copy()
    if decision_date_column not in cap_frame:
        cap_frame[decision_date_column] = cap_frame["date"]
    aligned_market_caps = align_policy_market_caps_to_periods(
        cap_frame,
        market_exposure_caps,
        decision_date_column=decision_date_column,
    )
    result = calendar_walk_forward_overlay_events(
        events,
        periods_per_year=periods_per_year,
        holding_period=holding_period,
        train_years=train_years,
        test_years=test_years,
        step_years=step_years,
        policies=policies,
        market_exposure_caps=aligned_market_caps,
    )
    result.update(
        {
            "stage": STAGE,
            "safety": SAFETY,
            "thresholds": {
                "return_column": return_column,
                "decision_date_column": decision_date_column,
                "has_market_exposure_caps": bool(market_exposure_caps is not None),
                "periods_per_year": float(periods_per_year),
                "holding_period": int(holding_period),
                "train_years": int(train_years),
                "test_years": int(test_years),
                "step_years": int(step_years),
                "policy_names": [policy.name for policy in policies],
                "decision_aware_overlay": True,
            },
            "source_context": {
                "purpose": "walk-forward validation of fixed portfolio overlays for tradeability-aware low-turnover returns",
                "not_paper_ready": True,
                "promotion_allowed": False,
            },
        }
    )
    write_overlay_walk_forward(output_dir, result)
    return result


def prepare_period_returns(period_returns: pd.DataFrame, *, return_column: str) -> pd.Series:
    if "date" not in period_returns:
        raise ValueError("period_returns must contain a date column")
    if return_column not in period_returns:
        raise ValueError(f"period_returns missing return column: {return_column}")
    frame = period_returns[["date", return_column]].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    frame[return_column] = pd.to_numeric(frame[return_column], errors="coerce").fillna(0.0)
    frame = frame.sort_values("date").drop_duplicates("date", keep="last")
    return pd.Series(frame[return_column].to_numpy(dtype=float), index=pd.DatetimeIndex(frame["date"]))


def prepare_period_return_events(
    period_returns: pd.DataFrame,
    *,
    return_column: str,
    decision_date_column: str,
) -> pd.DataFrame:
    if "date" not in period_returns:
        raise ValueError("period_returns must contain a date column")
    if return_column not in period_returns:
        raise ValueError(f"period_returns missing return column: {return_column}")
    frame = period_returns[["date", return_column]].copy()
    if decision_date_column in period_returns:
        frame["decision_date"] = period_returns[decision_date_column]
    else:
        frame["decision_date"] = period_returns["date"]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["decision_date"] = pd.to_datetime(frame["decision_date"], errors="coerce")
    frame["period_return"] = pd.to_numeric(frame[return_column], errors="coerce").fillna(0.0)
    frame = frame.dropna(subset=["date", "decision_date"])
    return (
        frame[["date", "decision_date", "period_return"]]
        .sort_values(["decision_date", "date"])
        .reset_index(drop=True)
    )


def market_state_cap_from_returns(
    market_returns: pd.Series,
    *,
    lookback_periods: int,
    momentum_threshold: float = 0.0,
    drawdown_threshold: float = -0.10,
    cap_exposure: float = 0.25,
    default_exposure: float = 1.0,
    lag_periods: int = 1,
) -> pd.Series:
    if int(lookback_periods) < 1:
        raise ValueError("lookback_periods must be positive")
    if int(lag_periods) < 0:
        raise ValueError("lag_periods must be non-negative")
    returns = pd.Series(market_returns).copy()
    returns.index = pd.to_datetime(returns.index)
    returns = pd.to_numeric(returns.sort_index(), errors="coerce").fillna(0.0)
    if returns.empty:
        return pd.Series(dtype=float)
    equity = (1.0 + returns).cumprod()
    lookback = int(lookback_periods)
    momentum = equity / equity.shift(lookback) - 1.0
    rolling_peak = equity.rolling(lookback, min_periods=lookback).max()
    drawdown = equity / rolling_peak - 1.0
    stress = (momentum <= float(momentum_threshold)) | (drawdown <= float(drawdown_threshold))
    cap = pd.Series(float(default_exposure), index=returns.index)
    cap.loc[stress.fillna(False)] = float(cap_exposure)
    cap = cap.shift(int(lag_periods)).fillna(float(default_exposure))
    return cap.clip(0.0, 1.0)


def market_state_policy_grid_from_returns(
    market_returns: pd.Series,
    *,
    lookback_periods: Sequence[int] = (60, 120, 180),
    momentum_thresholds: Sequence[float] = (0.0, -0.05),
    drawdown_threshold: float = -0.10,
    cap_exposures: Sequence[float] = (0.50, 0.25),
    warn_drawdown: float = -0.15,
    cut_drawdown: float = -0.25,
    lag_periods: int = 1,
) -> tuple[list[OverlayPolicy], dict[str, pd.Series]]:
    policies: list[OverlayPolicy] = []
    caps: dict[str, pd.Series] = {}
    for lookback in lookback_periods:
        for momentum_threshold in momentum_thresholds:
            for cap_exposure in cap_exposures:
                policy = OverlayPolicy(
                    name=_market_policy_name(
                        lookback=int(lookback),
                        momentum_threshold=float(momentum_threshold),
                        drawdown_threshold=float(drawdown_threshold),
                        cap_exposure=float(cap_exposure),
                    ),
                    kind="drawdown_market_state",
                    warn_drawdown=float(warn_drawdown),
                    cut_drawdown=float(cut_drawdown),
                    market_lookback_periods=int(lookback),
                    market_momentum_threshold=float(momentum_threshold),
                    market_drawdown_threshold=float(drawdown_threshold),
                    market_cap_exposure=float(cap_exposure),
                )
                policies.append(policy)
                caps[policy.name] = market_state_cap_from_returns(
                    market_returns,
                    lookback_periods=int(lookback),
                    momentum_threshold=float(momentum_threshold),
                    drawdown_threshold=float(drawdown_threshold),
                    cap_exposure=float(cap_exposure),
                    lag_periods=int(lag_periods),
                )
    return policies, caps


def align_market_caps_to_periods(
    period_returns: pd.DataFrame,
    market_exposure_cap: pd.Series,
    *,
    decision_date_column: str = "entry_date",
) -> pd.Series:
    if "date" not in period_returns:
        raise ValueError("period_returns must contain a date column")
    if decision_date_column not in period_returns:
        raise ValueError(f"period_returns missing decision date column: {decision_date_column}")
    caps = pd.Series(market_exposure_cap).copy()
    if caps.empty:
        raise ValueError("market_exposure_cap is empty")
    caps.index = pd.to_datetime(caps.index)
    caps = pd.to_numeric(caps.sort_index(), errors="coerce").dropna().clip(0.0, 1.0)
    if caps.empty:
        raise ValueError("market_exposure_cap has no numeric values")
    frame = period_returns[["date", decision_date_column]].copy()
    frame["_row_order"] = np.arange(len(frame))
    frame["date"] = pd.to_datetime(frame["date"])
    frame["_decision_date"] = pd.to_datetime(frame[decision_date_column])
    frame = frame.sort_values("_decision_date")
    cap_frame = caps.rename("_market_exposure_cap").rename_axis("_decision_date").reset_index()
    merged = pd.merge_asof(
        frame,
        cap_frame.sort_values("_decision_date"),
        on="_decision_date",
        direction="backward",
    )
    merged["_market_exposure_cap"] = merged["_market_exposure_cap"].fillna(1.0).clip(0.0, 1.0)
    merged = merged.sort_values("_row_order")
    return pd.Series(
        merged["_market_exposure_cap"].to_numpy(dtype=float),
        index=pd.DatetimeIndex(merged["date"]),
    )


def align_policy_market_caps_to_periods(
    period_returns: pd.DataFrame,
    market_exposure_caps: MarketExposureCaps | None,
    *,
    decision_date_column: str,
) -> MarketExposureCaps | None:
    if market_exposure_caps is None:
        return None
    if isinstance(market_exposure_caps, Mapping):
        return {
            name: align_market_caps_to_periods(
                period_returns,
                cap,
                decision_date_column=decision_date_column,
            )
            for name, cap in market_exposure_caps.items()
        }
    return align_market_caps_to_periods(
        period_returns,
        market_exposure_caps,
        decision_date_column=decision_date_column,
    )


def calendar_walk_forward_overlay(
    returns: pd.Series,
    *,
    periods_per_year: float,
    holding_period: int,
    train_years: int,
    test_years: int,
    step_years: int,
    policies: Sequence[OverlayPolicy] = DEFAULT_POLICIES,
    market_exposure_caps: MarketExposureCaps | None = None,
) -> dict[str, Any]:
    returns = returns.sort_index().dropna()
    rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    fold = 0
    if returns.empty:
        return _empty_result()
    start = pd.Timestamp(returns.index.min()).normalize()
    final_date = pd.Timestamp(returns.index.max()).normalize()
    while start + pd.DateOffset(years=train_years + test_years) <= final_date + pd.Timedelta(days=1):
        train_start = start
        train_end = start + pd.DateOffset(years=train_years) - pd.Timedelta(days=1)
        test_start = start + pd.DateOffset(years=train_years)
        test_end = start + pd.DateOffset(years=train_years + test_years) - pd.Timedelta(days=1)
        train = returns[(returns.index >= train_start) & (returns.index <= train_end)]
        test = returns[(returns.index >= test_start) & (returns.index <= test_end)]
        start = start + pd.DateOffset(years=step_years)
        if len(train) < 30 or len(test) < 10:
            continue
        fold += 1
        scored: list[tuple[tuple[float, ...], dict[str, Any]]] = []
        for policy in policies:
            policy_caps = _cap_for_policy(market_exposure_caps, policy)
            row = evaluate_policy_fold(
                train,
                test,
                policy,
                train_market_exposure_cap=_slice_cap(policy_caps, train.index),
                test_market_exposure_cap=_slice_cap(policy_caps, test.index),
                fold=fold,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            )
            rows.append(row)
            scored.append((policy_score(row, prefix="train"), row))
        selected = dict(max(scored, key=lambda item: item[0])[1])
        selected["selected_by_train"] = True
        selected_rows.append(selected)
    return summarize_walk_forward(rows, selected_rows)


def calendar_walk_forward_overlay_events(
    events: pd.DataFrame,
    *,
    periods_per_year: float,
    holding_period: int,
    train_years: int,
    test_years: int,
    step_years: int,
    policies: Sequence[OverlayPolicy] = DEFAULT_POLICIES,
    market_exposure_caps: MarketExposureCaps | None = None,
) -> dict[str, Any]:
    events = _normalise_period_events(events)
    rows: list[dict[str, Any]] = []
    selected_rows: list[dict[str, Any]] = []
    fold = 0
    if events.empty:
        return _empty_result()
    start = pd.Timestamp(events["decision_date"].min()).normalize()
    final_date = pd.Timestamp(events["decision_date"].max()).normalize()
    while start + pd.DateOffset(years=train_years + test_years) <= final_date + pd.Timedelta(days=1):
        train_start = start
        train_end = start + pd.DateOffset(years=train_years) - pd.Timedelta(days=1)
        test_start = start + pd.DateOffset(years=train_years)
        test_end = start + pd.DateOffset(years=train_years + test_years) - pd.Timedelta(days=1)
        train = events[(events["decision_date"] >= train_start) & (events["decision_date"] <= train_end)]
        test = events[(events["decision_date"] >= test_start) & (events["decision_date"] <= test_end)]
        start = start + pd.DateOffset(years=step_years)
        if len(train) < 30 or len(test) < 10:
            continue
        fold += 1
        scored: list[tuple[tuple[float, ...], dict[str, Any]]] = []
        for policy in policies:
            policy_caps = _cap_for_policy(market_exposure_caps, policy)
            row = evaluate_policy_fold_events(
                train,
                test,
                policy,
                market_exposure_cap=policy_caps,
                fold=fold,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            )
            rows.append(row)
            scored.append((policy_score(row, prefix="train"), row))
        selected = dict(max(scored, key=lambda item: item[0])[1])
        selected["selected_by_train"] = True
        selected_rows.append(selected)
    return summarize_walk_forward(rows, selected_rows)


def evaluate_policy_fold(
    train: pd.Series,
    test: pd.Series,
    policy: OverlayPolicy,
    *,
    train_market_exposure_cap: pd.Series | None = None,
    test_market_exposure_cap: pd.Series | None = None,
    fold: int,
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
    periods_per_year: float,
    holding_period: int,
) -> dict[str, Any]:
    train_overlay = apply_overlay_policy(
        train,
        policy,
        periods_per_year=periods_per_year,
        market_exposure_cap=train_market_exposure_cap,
    )
    test_overlay = apply_overlay_policy(
        test,
        policy,
        periods_per_year=periods_per_year,
        market_exposure_cap=test_market_exposure_cap,
    )
    train_metrics = metric_pack(train_overlay["period_return"], periods_per_year=periods_per_year, holding_period=holding_period)
    test_metrics = metric_pack(test_overlay["period_return"], periods_per_year=periods_per_year, holding_period=holding_period)
    row: dict[str, Any] = {
        "fold": int(fold),
        "policy": policy.name,
        "train_start": train_start.date().isoformat(),
        "train_end": train_end.date().isoformat(),
        "test_start": test_start.date().isoformat(),
        "test_end": test_end.date().isoformat(),
        "train_periods": int(len(train)),
        "test_periods": int(len(test)),
        "train_avg_exposure": float(train_overlay["exposure"].mean()),
        "test_avg_exposure": float(test_overlay["exposure"].mean()),
        "train_min_exposure": float(train_overlay["exposure"].min()),
        "test_min_exposure": float(test_overlay["exposure"].min()),
    }
    row.update({f"train_{key}": value for key, value in train_metrics.items()})
    row.update({f"test_{key}": value for key, value in test_metrics.items()})
    row["test_pass_loose"] = bool(
        row["test_annualized_return"] > 0.0
        and row["test_max_drawdown"] >= -0.35
        and row["test_overlap_autocorr_adjusted_sharpe"] > 0.0
    )
    row["test_pass_strict"] = bool(
        row["test_annualized_return"] > 0.0
        and row["test_max_drawdown"] >= -0.30
        and row["test_overlap_autocorr_adjusted_sharpe"] >= 0.30
    )
    return sanitize(row)


def evaluate_policy_fold_events(
    train_events: pd.DataFrame,
    test_events: pd.DataFrame,
    policy: OverlayPolicy,
    *,
    market_exposure_cap: pd.Series | None = None,
    fold: int,
    train_start: pd.Timestamp,
    train_end: pd.Timestamp,
    test_start: pd.Timestamp,
    test_end: pd.Timestamp,
    periods_per_year: float,
    holding_period: int,
) -> dict[str, Any]:
    train_overlay = apply_overlay_policy_to_period_events(
        train_events,
        policy,
        periods_per_year=periods_per_year,
        market_exposure_cap=market_exposure_cap,
    )
    test_overlay = apply_overlay_policy_to_period_events(
        test_events,
        policy,
        periods_per_year=periods_per_year,
        market_exposure_cap=market_exposure_cap,
    )
    train_returns = _event_return_series(train_overlay)
    test_returns = _event_return_series(test_overlay)
    train_metrics = metric_pack(train_returns, periods_per_year=periods_per_year, holding_period=holding_period)
    test_metrics = metric_pack(test_returns, periods_per_year=periods_per_year, holding_period=holding_period)
    row: dict[str, Any] = {
        "fold": int(fold),
        "policy": policy.name,
        "train_start": train_start.date().isoformat(),
        "train_end": train_end.date().isoformat(),
        "test_start": test_start.date().isoformat(),
        "test_end": test_end.date().isoformat(),
        "train_periods": int(len(train_returns)),
        "test_periods": int(len(test_returns)),
        "train_avg_exposure": float(train_overlay["exposure"].mean()) if not train_overlay.empty else 0.0,
        "test_avg_exposure": float(test_overlay["exposure"].mean()) if not test_overlay.empty else 0.0,
        "train_min_exposure": float(train_overlay["exposure"].min()) if not train_overlay.empty else 0.0,
        "test_min_exposure": float(test_overlay["exposure"].min()) if not test_overlay.empty else 0.0,
    }
    row.update({f"train_{key}": value for key, value in train_metrics.items()})
    row.update({f"test_{key}": value for key, value in test_metrics.items()})
    row["test_pass_loose"] = bool(
        row["test_annualized_return"] > 0.0
        and row["test_max_drawdown"] >= -0.35
        and row["test_overlap_autocorr_adjusted_sharpe"] > 0.0
    )
    row["test_pass_strict"] = bool(
        row["test_annualized_return"] > 0.0
        and row["test_max_drawdown"] >= -0.30
        and row["test_overlap_autocorr_adjusted_sharpe"] >= 0.30
    )
    return sanitize(row)


def apply_overlay_policy(
    returns: pd.Series,
    policy: OverlayPolicy,
    *,
    periods_per_year: float,
    market_exposure_cap: pd.Series | None = None,
) -> pd.DataFrame:
    if policy.kind == "none":
        exposure = pd.Series(1.0, index=returns.index)
        adjusted = returns.astype(float).copy()
    elif policy.kind == "market_state_cap":
        cap = _required_market_cap(returns, policy, market_exposure_cap)
        exposure = cap
        adjusted = returns.astype(float) * exposure
    elif policy.kind == "drawdown":
        adjusted, exposure = _apply_drawdown_policy(returns, policy)
    elif policy.kind == "drawdown_market_state":
        cap = _required_market_cap(returns, policy, market_exposure_cap)
        adjusted, exposure = _apply_drawdown_policy(returns, policy, market_exposure_cap=cap)
    elif policy.kind == "vol_target":
        adjusted, exposure = _apply_vol_target_policy(returns, policy, periods_per_year=periods_per_year)
    else:
        raise ValueError(f"Unsupported overlay policy kind: {policy.kind}")
    output = pd.DataFrame({"period_return": adjusted, "exposure": exposure}, index=returns.index)
    output["equity"] = (1.0 + output["period_return"]).cumprod()
    output["drawdown"] = output["equity"] / output["equity"].cummax() - 1.0
    return output


def apply_overlay_policy_to_period_events(
    events: pd.DataFrame,
    policy: OverlayPolicy,
    *,
    periods_per_year: float,
    market_exposure_cap: pd.Series | None = None,
) -> pd.DataFrame:
    frame = _normalise_period_events(events)
    if frame.empty:
        return frame.assign(exposure=pd.Series(dtype=float))
    cap = _event_market_cap(frame, market_exposure_cap) if market_exposure_cap is not None else None
    if policy.kind in {"none", "market_state_cap"}:
        if policy.kind == "market_state_cap" and cap is None:
            raise ValueError(f"policy {policy.name} requires market_exposure_cap")
        output = frame.copy()
        output["exposure"] = (cap if cap is not None else pd.Series(1.0, index=frame.index)).to_numpy(dtype=float)
        output["period_return"] = output["period_return"] * output["exposure"]
        return _add_event_equity(output)
    if policy.kind not in {"drawdown", "drawdown_market_state", "vol_target"}:
        raise ValueError(f"Unsupported overlay policy kind: {policy.kind}")
    if policy.kind == "drawdown_market_state" and cap is None:
        raise ValueError(f"policy {policy.name} requires market_exposure_cap")

    working = frame.sort_values(["decision_date", "date"]).copy()
    exposures = pd.Series(1.0, index=working.index, dtype=float)
    adjusted = pd.Series(0.0, index=working.index, dtype=float)
    pending: list[tuple[pd.Timestamp, int, float]] = []
    closed_returns: list[float] = []
    equity = 1.0
    peak = 1.0

    for decision_date, group in working.groupby("decision_date", sort=True):
        pending.sort(key=lambda item: (item[0], item[1]))
        still_pending: list[tuple[pd.Timestamp, int, float]] = []
        for exit_date, row_index, return_value in pending:
            if exit_date <= decision_date:
                equity *= 1.0 + float(return_value)
                peak = max(peak, equity)
                closed_returns.append(float(return_value))
            else:
                still_pending.append((exit_date, row_index, return_value))
        pending = still_pending

        if policy.kind in {"drawdown", "drawdown_market_state"}:
            base_exposure = _drawdown_exposure(equity=equity, peak=peak, policy=policy)
        else:
            base_exposure = _closed_return_vol_target_exposure(
                closed_returns,
                policy=policy,
                periods_per_year=periods_per_year,
            )
        for row_index, row in group.iterrows():
            exposure = float(base_exposure)
            if cap is not None:
                exposure = min(exposure, float(cap.loc[row_index]))
            return_value = float(row["period_return"]) * exposure
            exposures.loc[row_index] = exposure
            adjusted.loc[row_index] = return_value
            pending.append((pd.Timestamp(row["date"]), int(row_index), return_value))

    output = working.copy()
    output["exposure"] = exposures
    output["period_return"] = adjusted
    return _add_event_equity(output)


def metric_pack(returns: pd.Series, *, periods_per_year: float, holding_period: int) -> dict[str, float]:
    metrics = summarize_returns(returns.reset_index(drop=True), periods_per_year=periods_per_year)
    metrics.update(overlap_metrics(returns.reset_index(drop=True), periods_per_year=periods_per_year, holding_period=holding_period))
    keys = (
        "total_return",
        "annualized_return",
        "sharpe",
        "overlap_autocorr_adjusted_sharpe",
        "max_drawdown",
        "win_rate",
        "overlap_newey_west_t_stat_mean",
    )
    return {key: _number(metrics.get(key)) for key in keys}


def policy_score(row: dict[str, Any], *, prefix: str) -> tuple[float, ...]:
    annualized = _number(row.get(f"{prefix}_annualized_return"))
    drawdown = _number(row.get(f"{prefix}_max_drawdown"))
    overlap = _number(row.get(f"{prefix}_overlap_autocorr_adjusted_sharpe"))
    drawdown_ok = 1.0 if drawdown >= -0.30 else 0.0
    return_ok = 1.0 if annualized > 0.0 else 0.0
    return (drawdown_ok, return_ok, overlap, annualized, drawdown)


def summarize_walk_forward(rows: list[dict[str, Any]], selected_rows: list[dict[str, Any]]) -> dict[str, Any]:
    all_df = pd.DataFrame(rows)
    selected_df = pd.DataFrame(selected_rows)
    policy_summary = _policy_summary(all_df)
    summary = {
        "folds": int(selected_df["fold"].nunique()) if not selected_df.empty else 0,
        "policy_count": int(all_df["policy"].nunique()) if not all_df.empty else 0,
        "selected_policy_counts": selected_df["policy"].value_counts().to_dict() if not selected_df.empty else {},
        "selected_avg_test_annualized_return": _mean(selected_df, "test_annualized_return"),
        "selected_avg_test_sharpe": _mean(selected_df, "test_sharpe"),
        "selected_avg_test_overlap_sharpe": _mean(selected_df, "test_overlap_autocorr_adjusted_sharpe"),
        "selected_worst_test_drawdown": _min(selected_df, "test_max_drawdown"),
        "selected_positive_test_rate": _rate(selected_df, "test_annualized_return", lambda value: value > 0.0),
        "selected_loose_pass_rate": _mean(selected_df, "test_pass_loose"),
        "selected_strict_pass_rate": _mean(selected_df, "test_pass_strict"),
        "best_fixed_policy": policy_summary[0]["policy"] if policy_summary else None,
    }
    return {
        "summary": sanitize(summary),
        "policy_summary": policy_summary,
        "all_policy_folds": sanitize(rows),
        "selected_by_train": sanitize(selected_rows),
    }


def write_overlay_walk_forward(output_dir: str | Path, result: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "turnover_low_overlay_walk_forward.json").write_text(
        json.dumps(sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(result.get("all_policy_folds", [])).to_csv(
        output / "turnover_low_overlay_walk_forward_all_policies.csv",
        index=False,
    )
    pd.DataFrame(result.get("selected_by_train", [])).to_csv(
        output / "turnover_low_overlay_walk_forward_selected_by_train.csv",
        index=False,
    )
    pd.DataFrame(result.get("policy_summary", [])).to_csv(
        output / "turnover_low_overlay_walk_forward_policy_summary.csv",
        index=False,
    )


def _apply_drawdown_policy(
    returns: pd.Series,
    policy: OverlayPolicy,
    *,
    market_exposure_cap: pd.Series | None = None,
) -> tuple[pd.Series, pd.Series]:
    equity = 1.0
    peak = 1.0
    adjusted: list[float] = []
    exposures: list[float] = []
    warn_drawdown = float(policy.warn_drawdown if policy.warn_drawdown is not None else -0.10)
    cut_drawdown = float(policy.cut_drawdown if policy.cut_drawdown is not None else -0.20)
    cap = _align_cap_to_returns(returns, market_exposure_cap) if market_exposure_cap is not None else None
    for date, value in returns.astype(float).items():
        drawdown = equity / peak - 1.0
        if drawdown <= cut_drawdown:
            exposure = float(policy.cut_exposure)
        elif drawdown <= warn_drawdown:
            exposure = float(policy.warn_exposure)
        elif drawdown >= float(policy.recover_drawdown):
            exposure = 1.0
        else:
            exposure = 1.0
        if cap is not None:
            exposure = min(exposure, float(cap.loc[date]))
        period_return = exposure * float(value)
        equity *= 1.0 + period_return
        peak = max(peak, equity)
        adjusted.append(period_return)
        exposures.append(exposure)
    return pd.Series(adjusted, index=returns.index), pd.Series(exposures, index=returns.index)


def _drawdown_exposure(*, equity: float, peak: float, policy: OverlayPolicy) -> float:
    drawdown = float(equity) / max(float(peak), 1e-12) - 1.0
    warn_drawdown = float(policy.warn_drawdown if policy.warn_drawdown is not None else -0.10)
    cut_drawdown = float(policy.cut_drawdown if policy.cut_drawdown is not None else -0.20)
    if drawdown <= cut_drawdown:
        return float(policy.cut_exposure)
    if drawdown <= warn_drawdown:
        return float(policy.warn_exposure)
    if drawdown >= float(policy.recover_drawdown):
        return 1.0
    return 1.0


def _apply_vol_target_policy(
    returns: pd.Series,
    policy: OverlayPolicy,
    *,
    periods_per_year: float,
) -> tuple[pd.Series, pd.Series]:
    target = float(policy.target_annual_volatility if policy.target_annual_volatility is not None else 0.08)
    target_period_vol = target / np.sqrt(float(periods_per_year))
    min_periods = max(10, int(policy.lookback_periods) // 3)
    rolling_vol = returns.astype(float).rolling(int(policy.lookback_periods), min_periods=min_periods).std().shift(1)
    exposure = (
        target_period_vol
        / rolling_vol.replace(0.0, np.nan)
    ).clip(float(policy.min_exposure), float(policy.max_exposure)).fillna(1.0)
    return returns.astype(float) * exposure, exposure


def _closed_return_vol_target_exposure(
    closed_returns: Sequence[float],
    *,
    policy: OverlayPolicy,
    periods_per_year: float,
) -> float:
    lookback = int(policy.lookback_periods)
    min_periods = max(10, lookback // 3)
    if len(closed_returns) < min_periods:
        return 1.0
    recent = pd.Series(list(closed_returns)[-lookback:], dtype=float)
    realized_vol = float(recent.std(ddof=1))
    if not np.isfinite(realized_vol) or realized_vol <= 1e-12:
        return 1.0
    target = float(policy.target_annual_volatility if policy.target_annual_volatility is not None else 0.08)
    target_period_vol = target / np.sqrt(float(periods_per_year))
    exposure = target_period_vol / realized_vol
    return float(np.clip(exposure, float(policy.min_exposure), float(policy.max_exposure)))


def _policy_summary(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    grouped = (
        frame.groupby("policy")
        .agg(
            folds=("fold", "count"),
            avg_test_ann=("test_annualized_return", "mean"),
            avg_test_sharpe=("test_sharpe", "mean"),
            avg_test_overlap=("test_overlap_autocorr_adjusted_sharpe", "mean"),
            worst_test_dd=("test_max_drawdown", "min"),
            positive_test_rate=("test_annualized_return", lambda series: float((series > 0.0).mean())),
            loose_pass_rate=("test_pass_loose", "mean"),
            strict_pass_rate=("test_pass_strict", "mean"),
        )
        .reset_index()
        .sort_values(["loose_pass_rate", "avg_test_overlap", "avg_test_ann"], ascending=False)
    )
    return sanitize(grouped.to_dict("records"))


def _empty_result() -> dict[str, Any]:
    return {"summary": {"folds": 0, "policy_count": 0}, "policy_summary": [], "all_policy_folds": [], "selected_by_train": []}


def _mean(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    return _number(pd.to_numeric(frame[column], errors="coerce").mean())


def _min(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    return _number(pd.to_numeric(frame[column], errors="coerce").min())


def _rate(frame: pd.DataFrame, column: str, predicate: Callable[[float], bool]) -> float:
    if frame.empty or column not in frame:
        return 0.0
    values = pd.to_numeric(frame[column], errors="coerce").dropna()
    if values.empty:
        return 0.0
    return float(values.map(predicate).mean())


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if np.isfinite(number) else 0.0


def _required_market_cap(returns: pd.Series, policy: OverlayPolicy, cap: pd.Series | None) -> pd.Series:
    if cap is None:
        raise ValueError(f"policy {policy.name} requires market_exposure_cap")
    return _align_cap_to_returns(returns, cap)


def _align_cap_to_returns(returns: pd.Series, cap: pd.Series | None) -> pd.Series:
    if cap is None:
        return pd.Series(1.0, index=returns.index)
    series = pd.Series(cap).copy()
    if series.empty:
        raise ValueError("market_exposure_cap is empty")
    series.index = pd.to_datetime(series.index)
    series = pd.to_numeric(series.sort_index(), errors="coerce").dropna().clip(0.0, 1.0)
    if series.empty:
        raise ValueError("market_exposure_cap has no numeric values")
    aligned = series.reindex(pd.DatetimeIndex(returns.index), method="ffill").fillna(1.0).clip(0.0, 1.0)
    return pd.Series(aligned.to_numpy(dtype=float), index=returns.index)


def _cap_for_policy(caps: MarketExposureCaps | None, policy: OverlayPolicy) -> pd.Series | None:
    if caps is None:
        return None
    if isinstance(caps, Mapping):
        return caps.get(policy.name)
    return caps


def _slice_cap(cap: pd.Series | None, index: pd.Index) -> pd.Series | None:
    if cap is None:
        return None
    return pd.Series(cap).reindex(index)


def _normalise_period_events(events: pd.DataFrame) -> pd.DataFrame:
    required = ["date", "decision_date", "period_return"]
    missing = [column for column in required if column not in events]
    if missing:
        raise ValueError(f"period events missing columns: {', '.join(missing)}")
    frame = events[required].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["decision_date"] = pd.to_datetime(frame["decision_date"], errors="coerce")
    frame["period_return"] = pd.to_numeric(frame["period_return"], errors="coerce").fillna(0.0)
    return frame.dropna(subset=["date", "decision_date"]).sort_values(["decision_date", "date"]).reset_index(drop=True)


def _event_market_cap(events: pd.DataFrame, cap: pd.Series | None) -> pd.Series:
    if cap is None:
        return pd.Series(1.0, index=events.index)
    series = pd.Series(cap).copy()
    if series.empty:
        raise ValueError("market_exposure_cap is empty")
    series.index = pd.to_datetime(series.index)
    series = pd.to_numeric(series.sort_index(), errors="coerce").dropna().clip(0.0, 1.0)
    if series.empty:
        raise ValueError("market_exposure_cap has no numeric values")
    aligned = series.reindex(pd.DatetimeIndex(events["date"]), method="ffill").fillna(1.0).clip(0.0, 1.0)
    return pd.Series(aligned.to_numpy(dtype=float), index=events.index)


def _event_return_series(events: pd.DataFrame) -> pd.Series:
    if events.empty:
        return pd.Series(dtype=float)
    frame = events[["date", "period_return"]].copy()
    frame["date"] = pd.to_datetime(frame["date"])
    return frame.groupby("date", sort=True)["period_return"].sum()


def _add_event_equity(events: pd.DataFrame) -> pd.DataFrame:
    output = events.sort_values("date").reset_index(drop=True)
    output["equity"] = (1.0 + output["period_return"]).cumprod()
    output["drawdown"] = output["equity"] / output["equity"].cummax() - 1.0
    return output


def _market_policy_name(
    *,
    lookback: int,
    momentum_threshold: float,
    drawdown_threshold: float,
    cap_exposure: float,
) -> str:
    return (
        f"dd15_cut25_market_lb{lookback}_"
        f"mom{_compact_number(momentum_threshold)}_"
        f"dd{_compact_number(abs(drawdown_threshold))}_"
        f"cap{_compact_number(cap_exposure)}"
    )


def _compact_number(value: float) -> str:
    text = f"{float(value):g}"
    return text.replace("-", "neg").replace(".", "p")
