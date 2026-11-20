"""Daily fault-tolerant paper-trading orchestrator across all enabled portfolios."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.config.settings import PortfoliosConfig, load_portfolios_config, resolve_data_root
from quant_robot.data.updater import update_universe_cache
from quant_robot.paper.ledger import PaperLedger
from quant_robot.storage.atomic import atomic_write_json
from quant_robot.storage.market_cache import MarketCache


def run_daily_paper_update(
    *,
    config_path: str | Path = "configs/portfolios.json",
    data_root: str | Path | None = None,
    skip_fetch: bool = False,
    portfolio_ids: list[str] | None = None,
    config: PortfoliosConfig | None = None,
) -> dict[str, Any]:
    """Update market data (with retries) and catch up every enabled paper portfolio."""
    cfg = config or load_portfolios_config(config_path)
    root = Path(data_root) if data_root is not None else resolve_data_root()
    cache = MarketCache(root / "market_cache")
    paper_root = root / "paper"
    paper_root.mkdir(parents=True, exist_ok=True)

    enabled = [
        p for p in cfg.portfolios
        if p.enabled and (portfolio_ids is None or p.portfolio_id in portfolio_ids)
    ]

    # 1) Fetch/update market bars per market (grouped to avoid duplicate API calls)
    fetch_reports: dict[str, Any] = {}
    if not skip_fetch and enabled:
        by_market: dict[str, set[str]] = defaultdict(set)
        earliest_by_market: dict[str, str] = {}
        for spec in enabled:
            m = spec.market.upper()
            by_market[m].update(s.strip().upper() for s in spec.symbols)
            # Fetch at least 260 calendar days of warmup prior to start_date for lookback/MA indicators
            warm = (pd.to_datetime(spec.start_date).date() - timedelta(days=320)).isoformat()
            prev = earliest_by_market.get(m)
            if prev is None or warm < prev:
                earliest_by_market[m] = warm
        for market, syms in sorted(by_market.items()):
            fetch_reports[market] = update_universe_cache(
                cache,
                market,
                sorted(syms),
                default_start=earliest_by_market[market],
            )

    # 2) Sync every enabled paper portfolio chronologically
    portfolio_summaries: list[dict[str, Any]] = []
    for spec in enabled:
        bars = cache.load_universe(spec.market, spec.symbols)
        ledger = PaperLedger(spec, paper_root)
        res = ledger.sync_bars(bars)
        st = res["state"]
        init_cash = float(st["initial_cash"])
        nav = float(st["nav"])
        total_ret = (nav / init_cash - 1.0) if init_cash > 0 else 0.0
        portfolio_summaries.append(
            {
                "portfolio_id": spec.portfolio_id,
                "name": spec.name,
                "description": spec.description,
                "market": spec.market,
                "currency": spec.currency,
                "strategy_kind": spec.strategy.kind,
                "symbols": spec.symbols,
                "status": res["status"],
                "new_days": res.get("new_days", 0),
                "new_trades": res.get("new_trades", 0),
                "days_recorded": st["days_recorded"],
                "first_date": st["first_date"],
                "last_date": st["last_date"],
                "initial_cash": init_cash,
                "nav": round(nav, 2),
                "cash": round(float(st["cash"]), 2),
                "market_value": round(float(st["market_value"]), 2),
                "net_pnl": round(nav - init_cash, 2),
                "total_return": round(total_ret, 6),
                "max_drawdown": float(st["max_drawdown"]),
                "trade_count": int(st["trade_count"]),
                "total_fees": round(float(st["total_commission"]) + float(st["total_slippage"]), 2),
                "positions_count": len(st["positions"]),
            }
        )

    overview = {
        "updated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "asof_date": date.today().isoformat(),
        "paper_only": True,
        "live_trading_allowed": False,
        "safety_notice": "Research-to-paper only: no broker connection, no live account reads, no live order placement.",
        "fetch_reports": fetch_reports,
        "portfolios": portfolio_summaries,
    }
    atomic_write_json(paper_root / "overview.json", overview)
    return overview
