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
        if (abs(cur) < 1e-9 and abs(tgt) > 1e-9) or (abs(cur) > 1e-9 and abs(tgt) < 1e-9) or (cur * tgt < 0.0):
            return True
        if abs(cur - tgt) >= band:
            return True
    return False


def compute_target_weights(
    adj_close_panel: pd.DataFrame,
    symbols: list[str],
    spec: StrategySpec,
    risk: RiskConfig,
    *,
    periods_per_year: float = 252.0,
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
        raw, extra = _risk_parity_trend_weights(adj_close_panel, available, spec, periods_per_year=periods_per_year)
        diagnostics.update(extra)
    elif kind == "crypto_trend_vol":
        raw, extra = _crypto_trend_vol_weights(adj_close_panel, available, spec, periods_per_year=periods_per_year)
        diagnostics.update(extra)
    elif kind == "crypto_trend_ls":
        raw, extra = _crypto_trend_ls_weights(
            adj_close_panel,
            available,
            spec,
            allow_short=risk.allow_short,
            periods_per_year=periods_per_year,
        )
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
    *,
    periods_per_year: float = 252.0,
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
        vol = float(rets.std(ddof=0)) * math.sqrt(periods_per_year)
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


def _crypto_trend_vol_weights(
    panel: pd.DataFrame,
    symbols: list[str],
    spec: StrategySpec,
    *,
    periods_per_year: float = 365.0,
) -> tuple[dict[str, float], dict[str, object]]:
    """Trend-filtered, volatility-targeted momentum allocation built for 24/7 high-vol crypto.

    1. Only coins trading above their trend moving average AND with positive blended momentum qualify.
    2. Top `top_n` qualifying coins are inverse-volatility weighted.
    3. Total exposure scales by `min(1.0, target_volatility / realized_vol)` so crashes/spikes
       shrink position size automatically; bear markets stay 100% in cash (USD/USDT).
    """
    lookback = max(5, int(spec.lookback_days))
    half = max(5, lookback // 2)
    ma_days = max(10, int(spec.trend_ma_days)) if int(spec.trend_ma_days) > 0 else 0
    vol_win = max(10, int(spec.vol_lookback_days))
    target_vol = float(spec.target_volatility)

    candidates: list[tuple[str, float, float]] = []  # (symbol, momentum_score, annualized_vol)
    diag_scores: dict[str, float] = {}
    diag_vols: dict[str, float] = {}
    diag_trend: dict[str, bool] = {}

    for sym in symbols:
        series = panel[sym].dropna()
        if len(series) <= max(lookback, vol_win):
            continue
        p_now = float(series.iloc[-1])
        p_lb = float(series.iloc[-1 - lookback])
        p_half = float(series.iloc[-1 - half])
        if p_lb <= 0 or p_half <= 0:
            continue
        score = 0.5 * (p_now / p_lb - 1.0) + 0.5 * (p_now / p_half - 1.0)
        rets = series.pct_change().dropna().iloc[-vol_win:]
        vol = float(rets.std(ddof=0)) * math.sqrt(periods_per_year)
        above_ma = True if ma_days == 0 or len(series) < ma_days else (p_now >= float(series.iloc[-ma_days:].mean()))
        diag_scores[sym] = round(score, 4)
        diag_vols[sym] = round(vol, 4)
        diag_trend[sym] = above_ma
        if score > 0.0 and above_ma and math.isfinite(vol) and vol > 1e-6:
            candidates.append((sym, score, vol))

    if not candidates:
        return {}, {
            "momentum_scores": diag_scores,
            "vols": diag_vols,
            "trend_ok": diag_trend,
            "regime": "defensive_cash",
        }

    candidates.sort(key=lambda item: item[1], reverse=True)
    selected = candidates[: min(spec.top_n, len(candidates))]
    inv_sum = sum(1.0 / vol for _, _, vol in selected)
    base_weights = {sym: (1.0 / vol) / inv_sum for sym, _, vol in selected}
    # Approximate weighted average vol (conservative upper bound assuming high crypto correlation)
    avg_vol = sum(base_weights[sym] * vol for sym, _, vol in selected)
    gross_scale = min(1.0, target_vol / max(avg_vol, 1e-6))
    # Also scale down partially if fewer than top_n coins are trending up (breadth scaling)
    breadth_scale = len(selected) / float(min(spec.top_n, len(symbols)))
    final_scale = min(gross_scale, breadth_scale)
    weights = {sym: w * final_scale for sym, w in base_weights.items()}
    return weights, {
        "momentum_scores": diag_scores,
        "vols": diag_vols,
        "trend_ok": diag_trend,
        "gross_exposure": round(sum(weights.values()), 4),
        "regime": "trending",
    }


def _crypto_trend_ls_weights(
    panel: pd.DataFrame,
    symbols: list[str],
    spec: StrategySpec,
    *,
    allow_short: bool,
    periods_per_year: float = 365.0,
) -> tuple[dict[str, float], dict[str, object]]:
    """Asymmetric Long/Short Trend-Following CTA designed for 24/7 perpetual crypto markets.

    - Long entry: price > slow MA, price > fast MA, and fast momentum > 0.
    - Short entry (only when `allow_short=True`): structural death-cross (fast MA < slow MA),
      price < slow MA, price < fast short-exit MA (for quick short-squeeze protection),
      momentum < short_momentum_threshold, and optional BTC macro bear confirmation.
    - Risk-budget inverse-volatility sizing per slot so high-vol altcoins get smaller notional.
    """
    fast_ma = max(2, int(spec.fast_ma_days))
    slow_ma = max(fast_ma + 5, int(spec.trend_ma_days) if int(spec.trend_ma_days) > 0 else 60)
    short_exit = max(2, int(spec.short_exit_ma_days))
    vol_win = max(10, int(spec.vol_lookback_days))
    target_vol = float(spec.target_volatility)
    short_scale = float(spec.short_exposure_scale) if allow_short else 0.0
    short_thresh = float(spec.short_momentum_threshold)

    btc_bear = True
    if spec.require_btc_bear_for_short and "BTC-USD" in panel.columns:
        btc_ser = panel["BTC-USD"].dropna()
        if len(btc_ser) >= slow_ma:
            btc_p = float(btc_ser.iloc[-1])
            btc_fast = float(btc_ser.iloc[-fast_ma:].mean())
            btc_slow = float(btc_ser.iloc[-slow_ma:].mean())
            btc_bear = (btc_p < btc_slow) and (btc_fast < btc_slow)
        else:
            btc_bear = False

    n_slots = max(len(symbols), 1)
    weights: dict[str, float] = {}
    diag_signals: dict[str, str] = {}
    diag_vols: dict[str, float] = {}
    diag_mom: dict[str, float] = {}

    for sym in symbols:
        series = panel[sym].dropna()
        if len(series) <= max(slow_ma, vol_win) + 1:
            continue
        p = float(series.iloc[-1])
        ma_f = float(series.iloc[-fast_ma:].mean())
        ma_s = float(series.iloc[-slow_ma:].mean())
        ma_exit = float(series.iloc[-short_exit:].mean())
        p_fast = float(series.iloc[-1 - fast_ma])
        if p_fast <= 0:
            continue
        mom = p / p_fast - 1.0
        rets = series.pct_change().dropna().iloc[-vol_win:]
        vol = float(rets.std(ddof=0)) * math.sqrt(periods_per_year)
        if not math.isfinite(vol) or vol <= 1e-6:
            continue
        diag_vols[sym] = round(vol, 4)
        diag_mom[sym] = round(mom, 4)

        sig = 0.0
        if p > ma_s and p > ma_f and mom > 0.0:
            sig = 1.0
            diag_signals[sym] = "LONG"
        elif (
            short_scale > 0.0
            and btc_bear
            and ma_f < ma_s
            and p < ma_s
            and p < ma_exit
            and mom < short_thresh
        ):
            sig = -short_scale
            diag_signals[sym] = "SHORT"
        else:
            diag_signals[sym] = "FLAT"

        if abs(sig) > 1e-9:
            w_raw = sig * (target_vol / (n_slots * vol))
            weights[sym] = w_raw

    long_cnt = sum(1 for v in weights.values() if v > 0)
    short_cnt = sum(1 for v in weights.values() if v < 0)
    regime = "mixed_ls" if (long_cnt and short_cnt) else ("long_trend" if long_cnt else ("short_bear" if short_cnt else "flat_cash"))
    return weights, {
        "signals": diag_signals,
        "momentum_fast": diag_mom,
        "vols": diag_vols,
        "btc_bear_regime": btc_bear,
        "regime": regime,
        "net_exposure": round(sum(weights.values()), 4),
        "gross_exposure": round(sum(abs(v) for v in weights.values()), 4),
    }


def _apply_risk_caps(weights: dict[str, float], risk: RiskConfig) -> dict[str, float]:
    max_gross = max(0.0, risk.max_gross_leverage * (1.0 - risk.min_cash_weight))
    if risk.allow_short:
        cleaned: dict[str, float] = {}
        for sym, raw_w in weights.items():
            w = float(raw_w)
            if abs(w) <= 1e-9:
                continue
            cleaned[sym] = max(-risk.max_single_weight, min(risk.max_single_weight, w))
        gross = sum(abs(v) for v in cleaned.values())
        if gross > max_gross and gross > 0:
            scale = max_gross / gross
            cleaned = {sym: w * scale for sym, w in cleaned.items()}
        return cleaned

    cleaned = {sym: min(float(w), risk.max_single_weight) for sym, w in weights.items() if float(w) > 1e-9}
    total = sum(cleaned.values())
    if total > max_gross and total > 0:
        scale = max_gross / total
        cleaned = {sym: w * scale for sym, w in cleaned.items()}
    return cleaned
