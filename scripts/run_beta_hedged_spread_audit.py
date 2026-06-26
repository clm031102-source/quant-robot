from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from scripts.run_bottom_exclusion_portfolio_backtest import _build_frames_from_grid, _load_frame  # noqa: E402
from quant_robot.ops.beta_hedged_spread_audit import (  # noqa: E402
    run_beta_hedged_spread_audit,
    write_beta_hedged_spread_audit,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/beta_hedged_spread_audit")


def run_beta_hedged_spread_audit_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    factors: str | Path | None = None,
    labels: str | Path | None = None,
    bars: str | Path | None = None,
    grid_config: str | Path | None = None,
    source: str = "authority-processed-bars",
    data_root: str | Path = "data/processed",
    authority_bars_config: str | Path | None = "configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json",
    bottom_quantile: float = 0.2,
    rebalance_interval: int | None = None,
    holding_period: int | None = None,
    cost_bps: float = 10.0,
    market_impact_bps: float = 20.0,
    max_participation_rate: float | None = 0.01,
    min_entry_amount: float | None = None,
    portfolio_value: float = 1_000_000.0,
    target_gross_exposure: float = 0.6,
    hedge_ratio: float = 1.0,
    min_positive_fold_rate: float = 0.6,
    min_overlap_adjusted_sharpe: float = 0.5,
    max_drawdown_limit: float | None = 0.5,
) -> dict[str, Any]:
    if grid_config is not None:
        factor_frame, label_frame, bar_frame, source_report, resolved_rebalance, resolved_holding = _build_frames_from_grid(
            Path(grid_config),
            source=source,
            data_root=Path(data_root),
            authority_bars_config=Path(authority_bars_config) if authority_bars_config else None,
            rebalance_interval=rebalance_interval,
            holding_period=holding_period,
        )
    else:
        if factors is None or labels is None or bars is None:
            raise ValueError("Either --grid-config or --factors, --labels, and --bars are required")
        factor_frame = _load_frame(Path(factors))
        label_frame = _load_frame(Path(labels))
        bar_frame = _load_frame(Path(bars))
        resolved_rebalance = rebalance_interval or 1
        resolved_holding = holding_period or 1
        source_report = f"factors={Path(factors)} labels={Path(labels)} bars={Path(bars)}"

    result = run_beta_hedged_spread_audit(
        factor_frame,
        label_frame,
        bar_frame,
        source_report=source_report,
        bottom_quantile=bottom_quantile,
        rebalance_interval=resolved_rebalance,
        holding_period=resolved_holding,
        cost_bps=cost_bps,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        min_entry_amount=min_entry_amount,
        portfolio_value=portfolio_value,
        target_gross_exposure=target_gross_exposure,
        hedge_ratio=hedge_ratio,
        min_positive_fold_rate=min_positive_fold_rate,
        min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
        max_drawdown_limit=max_drawdown_limit,
    )
    write_beta_hedged_spread_audit(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit a fixed-ratio beta-hedged spread between kept basket and equal-weight benchmark.")
    parser.add_argument("--grid-config")
    parser.add_argument("--factors")
    parser.add_argument("--labels")
    parser.add_argument("--bars")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--source", choices=["fixture", "processed-bars", "authority-processed-bars"], default="authority-processed-bars")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--authority-bars-config", default="configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json")
    parser.add_argument("--bottom-quantile", type=float, default=0.2)
    parser.add_argument("--rebalance-interval", type=int)
    parser.add_argument("--holding-period", type=int)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--market-impact-bps", type=float, default=20.0)
    parser.add_argument("--max-participation-rate", type=float, default=0.01)
    parser.add_argument("--min-entry-amount", type=float)
    parser.add_argument("--portfolio-value", type=float, default=1_000_000.0)
    parser.add_argument("--target-gross-exposure", type=float, default=0.6)
    parser.add_argument("--hedge-ratio", type=float, default=1.0)
    parser.add_argument("--min-positive-fold-rate", type=float, default=0.6)
    parser.add_argument("--min-overlap-adjusted-sharpe", type=float, default=0.5)
    parser.add_argument("--max-drawdown-limit", type=float, default=0.5)
    args = parser.parse_args()

    result = run_beta_hedged_spread_audit_cli(
        output_dir=Path(args.output_dir),
        factors=Path(args.factors) if args.factors else None,
        labels=Path(args.labels) if args.labels else None,
        bars=Path(args.bars) if args.bars else None,
        grid_config=Path(args.grid_config) if args.grid_config else None,
        source=args.source,
        data_root=Path(args.data_root),
        authority_bars_config=Path(args.authority_bars_config) if args.authority_bars_config else None,
        bottom_quantile=args.bottom_quantile,
        rebalance_interval=args.rebalance_interval,
        holding_period=args.holding_period,
        cost_bps=args.cost_bps,
        market_impact_bps=args.market_impact_bps,
        max_participation_rate=args.max_participation_rate,
        min_entry_amount=args.min_entry_amount,
        portfolio_value=args.portfolio_value,
        target_gross_exposure=args.target_gross_exposure,
        hedge_ratio=args.hedge_ratio,
        min_positive_fold_rate=args.min_positive_fold_rate,
        min_overlap_adjusted_sharpe=args.min_overlap_adjusted_sharpe,
        max_drawdown_limit=args.max_drawdown_limit,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "top": result["leaderboard"][:10],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
