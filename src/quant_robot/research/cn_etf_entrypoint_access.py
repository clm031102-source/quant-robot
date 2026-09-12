"""Reject unregistered CN_ETF work at generic processed-data entrypoints."""
from __future__ import annotations

from collections.abc import Iterable


def require_registered_cn_etf_entrypoint(source: str, market: str) -> None:
    """No generic CLI argument currently binds the required ETF authorization.

    CN stock startup/manifest/readiness packets do not authorize ETF research.
    ALL also contains CN_ETF. Use the reviewed, fingerprint-bound dedicated
    research entrypoint; this check neither issues nor consumes authorization.
    Fixture runs and existing non-ETF checks retain their own behavior.
    """
    source_name = source.strip().lower().replace('_', '-')
    if source_name in {'processed-bars', 'authority-bars'} and market.strip().upper() in {'CN_ETF', 'ALL'}:
        raise ValueError(
            'CN_ETF processed data requires a registered dedicated research entrypoint; '
            'generic research, signal, paper, grid and validation commands do not carry the required '
            'source, preregistration, research-run and holdout authorization. '
            'CN stock packets and rotation membership do not grant ETF access.'
        )


def require_registered_cn_etf_markets(source: str, markets: Iterable[str]) -> None:
    """Check the entire market selection before any source is loaded."""
    for market in markets:
        require_registered_cn_etf_entrypoint(source, market)
