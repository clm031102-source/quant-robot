from __future__ import annotations


def calendar_for_market(market: str, exchange: str) -> str:
    market_upper = market.upper()
    exchange_upper = exchange.upper()
    if market_upper == "CRYPTO":
        return "24/7"
    if market_upper == "US":
        return "XNYS"
    if market_upper in {"CN", "CN_ETF"}:
        return exchange_upper
    if market_upper == "HK":
        return "XHKG"
    raise ValueError(f"Unsupported market: {market}")
