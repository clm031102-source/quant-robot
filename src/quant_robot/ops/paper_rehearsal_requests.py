"""Encode the frozen inputs of a GUI paper rehearsal request."""
from __future__ import annotations

from typing import Any
from urllib.parse import urlencode


def same_parameter_paper_query(request: dict[str, Any]) -> str:
    request_id = request.get("same_parameter_request_id") or request.get("request_id")
    pairs = [
        ("source", request.get("source")),
        ("market", request.get("market")),
        ("factor", request.get("factor") or request.get("factor_name")),
        ("factor_windows", request.get("factor_windows")),
        ("top_n", request.get("top_n")),
        ("rebalance_interval", request.get("rebalance_interval")),
        ("start_date", request.get("start_date")),
        ("end_date", request.get("end_date")),
        ("as_of_date", request.get("as_of_date")),
        ("run_date", request.get("as_of_date")),
        ("initial_cash", request.get("initial_cash")),
        ("commission_bps", request.get("commission_bps")),
        ("slippage_bps", request.get("slippage_bps")),
        ("max_asset_weight", request.get("max_asset_weight")),
        ("max_market_weight", request.get("max_market_weight")),
        ("max_gross_exposure", request.get("max_gross_exposure")),
        ("min_cash_weight", request.get("min_cash_weight")),
        ("risk_profile_id", request.get("risk_profile_id")),
        ("same_parameter_lock_id", request.get("same_parameter_lock_id")),
        ("same_parameter_request_id", request_id),
        ("case_id", request.get("case_id")),
    ]
    return urlencode([(key, str(value)) for key, value in pairs if value is not None and str(value) != ""])
