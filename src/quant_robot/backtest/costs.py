from __future__ import annotations


def round_trip_cost(cost_bps: float) -> float:
    return 2.0 * cost_bps / 10000.0


def estimate_trade_cost_rate(
    cost_bps: float,
    *,
    commission_bps: float | None = None,
    slippage_bps: float | None = None,
    market_impact_bps: float = 0.0,
    participation_rate: float = 0.0,
    max_participation_rate: float | None = None,
) -> float:
    base_bps = _base_one_way_bps(cost_bps, commission_bps, slippage_bps)
    impact_bps = _market_impact_bps(market_impact_bps, participation_rate, max_participation_rate)
    return round_trip_cost(base_bps + impact_bps)


def capacity_limited(participation_rate: float, max_participation_rate: float | None) -> bool:
    return max_participation_rate is not None and participation_rate > max_participation_rate


def market_impact_cost_bps(
    market_impact_bps: float,
    participation_rate: float,
    max_participation_rate: float | None = None,
) -> float:
    return _market_impact_bps(market_impact_bps, participation_rate, max_participation_rate)


def _base_one_way_bps(cost_bps: float, commission_bps: float | None, slippage_bps: float | None) -> float:
    if commission_bps is None and slippage_bps is None:
        return float(cost_bps)
    return float(commission_bps or 0.0) + float(slippage_bps or 0.0)


def _market_impact_bps(
    market_impact_bps: float,
    participation_rate: float,
    max_participation_rate: float | None,
) -> float:
    if market_impact_bps <= 0.0 or participation_rate <= 0.0:
        return 0.0
    if max_participation_rate is not None and max_participation_rate > 0.0:
        return float(market_impact_bps) * min(participation_rate / max_participation_rate, 1.0)
    return float(market_impact_bps) * min(participation_rate, 1.0)
