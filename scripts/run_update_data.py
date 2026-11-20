"""Incrementally update local daily OHLCV market cache (CN_ETF via Tushare, US_ETF & CRYPTO via yfinance)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from quant_robot.config.settings import load_backtest_presets, load_portfolios_config, resolve_data_root
from quant_robot.data.updater import update_universe_cache
from quant_robot.storage.market_cache import MarketCache


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Update local daily market data cache.")
    parser.add_argument("--market", help="Optional filter: CN_ETF, US_ETF, or CRYPTO")
    parser.add_argument("--symbols", help="Optional comma-separated symbols (requires --market)")
    parser.add_argument("--start", default="2020-01-01", help="Default history start date (YYYY-MM-DD)")
    parser.add_argument("--full-refresh", action="store_true", help="Ignore existing cache and re-fetch full range")
    parser.add_argument("--data-root", help="Override data directory")
    args = parser.parse_args(argv)

    data_root = Path(args.data_root) if args.data_root else resolve_data_root(ROOT)
    cache = MarketCache(data_root / "market_cache")

    by_market: dict[str, set[str]] = {}
    if args.symbols:
        if not args.market:
            parser.error("--symbols requires --market")
        by_market[args.market.upper()] = {s.strip().upper() for s in args.symbols.split(",") if s.strip()}
    else:
        for loader, path in (
            (load_portfolios_config, ROOT / "configs" / "portfolios.json"),
            (load_backtest_presets, ROOT / "configs" / "backtest_presets.json"),
        ):
            if not path.is_file():
                continue
            cfg = loader(path)
            items = getattr(cfg, "portfolios", None) or getattr(cfg, "presets", [])
            for item in items:
                m = item.market.upper()
                if args.market and m != args.market.upper():
                    continue
                by_market.setdefault(m, set()).update(s.strip().upper() for s in item.symbols)

    reports = {}
    had_errors = False
    for market, syms in sorted(by_market.items()):
        rep = update_universe_cache(
            cache,
            market,
            sorted(syms),
            default_start=args.start,
            full_refresh=args.full_refresh,
        )
        reports[market] = rep
        if rep["error_count"] > 0:
            had_errors = True

    print(json.dumps(reports, ensure_ascii=False, indent=2))
    return 1 if had_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
