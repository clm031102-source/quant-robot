"""Causal built-in strategies: fixed allocation, passive drift, dual momentum, risk-parity trend."""
from __future__ import annotations

from datetime import date
import math

import numpy as np
import pandas as pd

from quant_robot.config.settings import RiskConfig, StrategySpec


def is_rebalance_day(
    dates: list[date],
    idx: int,
    frequency: str,
    *,
    has_positions: bool,
) -> bool:
    """Return True if day `idx` should trigger a strategy decision (executed on idx + 1)."""
    if not has_positions:
        return True
    freq = frequency.lower()
    if freq == "never":
        return False
    if freq == "daily":
        return True
    if idx == 0:
        return True
    cur = dates[idx]
    prev = dates[idx - 1]
    if freq == "weekly":
        return cur.isocalendar()[:2] != prev.isocalendar()[:2]
    if freq == "monthly":
        return (cur.year, cur.month) != (prev.year, prev.month)
    if freq == "quarterly":
        return (cur.year, (cur.month - 1) // 3) != (prev.year, (prev.month - 1) // 3)
    raise ValueError(f"Unsupported rebalance frequency: {frequency}")


def should_rebalance_by_band(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    band: float,
) -> bool:
    """Return True if any asset deviates from target by >= band, or enters/exits zero."""
    if band <= 0.0:
        return True
    keys = set(current_weights) | set(target_weights)
    for sym in keys:
        cur = float(current_weights.get(sym, 0.0))
        tgt = float(target_weights.get(sym, 0.0))
        if (cur == 0.0 and tgt > 0.0) or (cur > 0.0 and tgt == 0.0):
            return True
        if abs(cur - tgt) >= band:
            return True
    return False


def compute_target_weights(
    adj_close_panel: pd.DataFrame,
    symbols: list[str],
    spec: StrategySpec,
    risk: RiskConfig,
) -> tuple[dict[str, float], dict[str, object]]:
    """Compute strictly causal target weights using ONLY rows in `adj_close_panel` (<= asof_date)."""
    available = [s for s in symbols if s in adj_close_panel.columns and adj_close_panel[s].dropna().shape[0] > 0]
    if not available:
        return {}, {"reason": "no_available_symbols"}

    kind = spec.kind
    diagnostics: dict[str, object] = {"strategy": kind}

    if kind in {"fixed_allocation", "passive_drift"}:
        raw = _fixed_weights(available, spec.target_weights)
    elif kind == "dual_momentum":
        raw, extra = _dual_momentum_weights(adj_close_panel, available, spec)
        diagnostics.update(extra)
    elif kind == "risk_parity_trend":
        raw, extra = _risk_parity_trend_weights(adj_close_panel, available, spec)
        diagnostics.update(extra)
    else:
        raise ValueError(f"Unsupported strategy kind: {kind}")

    constrained = _apply_risk_caps(raw, risk)
    return constrained, diagnostics


def _fixed_weights(symbols: list[str], configured: dict[str, float]) -> dict[str, float]:
    if configured:
        selected = {s: float(configured[s]) for s in symbols if s in configured and float(configured[s]) > 0}
        total = sum(selected.values())
        if total > 0:
            return {s: w / total for s, w in selected.items()}
    equal = 1.0 / len(symbols)
    return {s: equal for s in symbols}


def _dual_momentum_weights(
    panel: pd.DataFrame,
    symbols: list[str],
    spec: StrategySpec,
) -> tuple[dict[str, float], dict[str, object]]:
    defensive = spec.defensive_symbol.upper() if spec.defensive_symbol else None
    risky = [s for s in symbols if s != defensive]
    if not risky:
        risky = list(symbols)

    lookback = max(5, int(spec.lookback_days))
    ma_days = int(spec.trend_ma_days)
    scores: dict[str, float] = {}
    trend_ok: dict[str, bool] = {}

    for sym in risky:
        series = panel[sym].dropna()
        if len(series) <= lookback:
            continue
        p_now = float(series.iloc[-1])
        p_prev = float(series.iloc[-1 - lookback])
        if p_prev <= 0 or not math.isfinite(p_now / p_prev):
            continue
        mom = p_now / p_prev - 1.0
        # Blend 1-horizon and half-horizon momentum for smoother signal stability.
        half = max(5, lookback // 2)
        if len(series) > half and float(series.iloc[-1 - half]) > 0:
            mom_half = p_now / float(series.iloc[-1 - half]) - 1.0
            score = 0.5 * mom + 0.5 * mom_half
        else:
            score = mom
        above_ma = True
        if ma_days > 0 and len(series) >= ma_days:
            ma_val = float(series.iloc[-ma_days:].mean())
            above_ma = p_now >= ma_val
        scores[sym] = score
        trend_ok[sym] = above_ma

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    slots = min(spec.top_n, len(risky))
    slot_weight = 1.0 / slots if slots > 0 else 0.0
    weights: dict[str, float] = {}
    defensive_weight = 0.0

    for sym, sc in ranked[:slots]:
        if sc > 0.0 and trend_ok.get(sym, True):
            weights[sym] = slot_weight
        else:
            defensive_weight += slot_weight

    # Allocate uninvested slots (including warmup period) to defensive asset if available.
    allocated = sum(weights.values()) + defensive_weight
    if allocated < 1.0 - 1e-9:
        defensive_weight += 1.0 - allocated

    if defensive_weight > 1e-9 and defensive and defensive in symbols:
        weights[defensive] = weights.get(defensive, 0.0) + defensive_weight

    return weights, {"momentum_scores": {k: round(v, 5) for k, v in ranked}, "trend_ok": trend_ok}


def _risk_parity_trend_weights(
    panel: pd.DataFrame,
    symbols: list[str],
    spec: StrategySpec,
) -> tuple[dict[str, float], dict[str, object]]:
    vol_win = max(5, int(spec.vol_lookback_days))
    ma_days = int(spec.trend_ma_days)
    defensive = spec.defensive_symbol.upper() if spec.defensive_symbol else None

    inv_vols: dict[str, float] = {}
    vols_diag: dict[str, float] = {}
    for sym in symbols:
        series = panel[sym].dropna()
        if len(series) <= vol_win:
            continue
        rets = series.pct_change().dropna().iloc[-vol_win:]
        vol = float(rets.std(ddof=0)) * math.sqrt(252.0)
        if not math.isfinite(vol) or vol <= 1e-6:
            continue
        vols_diag[sym] = round(vol, 5)
        inv_vols[sym] = 1.0 / vol

    if not inv_vols:
        return _fixed_weights(symbols, spec.target_weights), {"vols": vols_diag, "fallback": "equal_warmup"}

    total_inv = sum(inv_vols.values())
    raw = {sym: v / total_inv for sym, v in inv_vols.items()}

    if ma_days > 0:
        shifted_to_def = 0.0
        filtered: dict[str, float] = {}
        for sym, w in raw.items():
            series = panel[sym].dropna()
            if sym != defensive and len(series) >= ma_days and float(series.iloc[-1]) < float(series.iloc[-ma_days:].mean()):
                shifted_to_def += w
            else:
                filtered[sym] = w
        if shifted_to_def > 1e-9 and defensive and defensive in symbols:
            filtered[defensive] = filtered.get(defensive, 0.0) + shifted_to_def
        raw = filtered

    return raw, {"vols": vols_diag}


def _apply_risk_caps(weights: dict[str, float], risk: RiskConfig) -> dict[str, float]:
    cleaned = {sym: min(float(w), risk.max_single_weight) for sym, w in weights.items() if float(w) > 1e-9}
    max_invested = max(0.0, 1.0 - risk.min_cash_weight)
    total = sum(cleaned.values())
    if total > max_invested and total > 0:
        scale = max_invested / total
        cleaned = {sym: w * scale for sym, w in cleaned.items()}
    return cleaned
