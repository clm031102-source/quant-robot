from __future__ import annotations


def round_trip_cost(cost_bps: float) -> float:
    return 2.0 * cost_bps / 10000.0
