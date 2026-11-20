"""Run backtest presets (or a specific preset) on cached real market data and write Markdown/SVG/JSON reports."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from quant_robot.backtest.simulator import BacktestReport, run_portfolio_backtest
from quant_robot.config.settings import load_backtest_presets, resolve_data_root
from quant_robot.reports.markdown import render_comparison_markdown, write_comparison_svg
from quant_robot.storage.atomic import atomic_write_json, atomic_write_text
from quant_robot.storage.market_cache import MarketCache


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run strategy backtests from configs/backtest_presets.json.")
    parser.add_argument("--config", default=str(ROOT / "configs" / "backtest_presets.json"))
    parser.add_argument("--preset", help="Optional single preset_id to run")
    parser.add_argument("--market", help="Optional market filter (CN_ETF or US_ETF)")
    parser.add_argument("--data-root", help="Override data directory")
    parser.add_argument("--output-dir", help="Override report output directory")
    args = parser.parse_args(argv)

    data_root = Path(args.data_root) if args.data_root else resolve_data_root(ROOT)
    out_dir = Path(args.output_dir) if args.output_dir else data_root / "reports" / "backtests"
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = MarketCache(data_root / "market_cache")

    cfg = load_backtest_presets(args.config)
    selected = [
        p
        for p in cfg.presets
        if (not args.preset or p.preset_id == args.preset)
        and (not args.market or p.market.upper() == args.market.upper())
    ]
    if not selected:
        raise SystemExit("No matching presets found.")

    reports: list[BacktestReport] = []
    for preset in selected:
        bars = cache.load_universe(preset.market, preset.symbols)
        if bars.empty:
            raise SystemExit(
                f"No cached bars for {preset.market} {preset.symbols}. Run scripts/run_update_data.py first."
            )
        rep = run_portfolio_backtest(
            bars,
            name=preset.name,
            market=preset.market,
            currency=preset.currency,
            symbols=preset.symbols,
            strategy=preset.strategy,
            cost=preset.cost,
            risk=preset.risk,
            initial_cash=preset.initial_cash,
            lot_size=preset.lot_size,
            execution_price=preset.execution_price,
            start_date=preset.start_date,
            end_date=preset.end_date,
        )
        reports.append(rep)
        p_dir = out_dir / preset.preset_id
        p_dir.mkdir(parents=True, exist_ok=True)
        rep.equity_curve.to_csv(p_dir / "equity_curve.csv", index=False)
        rep.trades.to_csv(p_dir / "trades.csv", index=False)
        atomic_write_json(p_dir / "summary.json", rep.to_summary_dict())
        write_comparison_svg(rep.equity_curve, p_dir / "equity_curve.svg", f"{rep.name} ({rep.start_date} ~ {rep.end_date})")

    md = render_comparison_markdown(reports)
    atomic_write_text(out_dir / "comparison.md", md)
    atomic_write_json(out_dir / "comparison.json", [r.to_summary_dict() for r in reports])
    print(md)
    print(f"\nSaved full reports to: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
