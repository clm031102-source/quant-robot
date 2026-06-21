from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.bottom_exclusion_walk_forward import (  # noqa: E402
    run_bottom_exclusion_walk_forward,
    write_bottom_exclusion_walk_forward,
)
from scripts.run_bottom_exclusion_portfolio_backtest import (  # noqa: E402
    _build_frames_from_grid,
    _load_frame,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/bottom_exclusion_walk_forward")


def run_bottom_exclusion_walk_forward_cli(
    *,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    factors: str | Path | None = None,
    labels: str | Path | None = None,
    bars: str | Path | None = None,
    grid_config: str | Path | None = None,
    source: str = "authority-processed-bars",
    data_root: str | Path = "data/processed",
    authority_bars_config: str | Path | None = "configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json",
    rolling_train_days: int = 756,
    rolling_test_days: int = 252,
    rolling_step_days: int = 252,
    min_accepted_folds: int = 2,
    bottom_quantile: float = 0.2,
    rebalance_interval: int | None = None,
    holding_period: int | None = None,
    cost_bps: float = 10.0,
    market_impact_bps: float = 20.0,
    max_participation_rate: float | None = 0.01,
    min_entry_amount: float | None = None,
    portfolio_value: float = 1_000_000.0,
    target_gross_exposure: float = 1.0,
    min_positive_relative_fold_rate: float = 0.6,
    min_test_overlap_adjusted_sharpe: float = 0.5,
    max_test_drawdown_limit: float | None = 0.5,
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
        resolved_holding = holding_period or _infer_holding_period(label_frame)
        source_report = (
            f"factors={Path(factors)} labels={Path(labels)} bars={Path(bars)} "
            f"rebalance_interval={resolved_rebalance} holding_period={resolved_holding}"
        )
    result = run_bottom_exclusion_walk_forward(
        factor_frame,
        label_frame,
        bar_frame,
        source_report=source_report,
        rolling_train_days=rolling_train_days,
        rolling_test_days=rolling_test_days,
        rolling_step_days=rolling_step_days,
        min_accepted_folds=min_accepted_folds,
        bottom_quantile=bottom_quantile,
        rebalance_interval=resolved_rebalance,
        holding_period=resolved_holding,
        cost_bps=cost_bps,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        min_entry_amount=min_entry_amount,
        portfolio_value=portfolio_value,
        target_gross_exposure=target_gross_exposure,
        min_positive_relative_fold_rate=min_positive_relative_fold_rate,
        min_test_overlap_adjusted_sharpe=min_test_overlap_adjusted_sharpe,
        max_test_drawdown_limit=max_test_drawdown_limit,
    )
    write_bottom_exclusion_walk_forward(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rolling walk-forward validation for bottom-exclusion risk filters.")
    parser.add_argument("--grid-config")
    parser.add_argument("--factors")
    parser.add_argument("--labels")
    parser.add_argument("--bars")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--source", choices=["fixture", "processed-bars", "authority-processed-bars"], default="authority-processed-bars")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--authority-bars-config", default="configs/cn_stock_authority_bars_2015_2025_adjusted_ratio_clean.json")
    parser.add_argument("--rolling-train-days", type=int, default=756)
    parser.add_argument("--rolling-test-days", type=int, default=252)
    parser.add_argument("--rolling-step-days", type=int, default=252)
    parser.add_argument("--min-accepted-folds", type=int, default=2)
    parser.add_argument("--bottom-quantile", type=float, default=0.2)
    parser.add_argument("--rebalance-interval", type=int)
    parser.add_argument("--holding-period", type=int)
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--market-impact-bps", type=float, default=20.0)
    parser.add_argument("--max-participation-rate", type=float, default=0.01)
    parser.add_argument("--min-entry-amount", type=float)
    parser.add_argument("--portfolio-value", type=float, default=1_000_000.0)
    parser.add_argument("--target-gross-exposure", type=float, default=1.0)
    parser.add_argument("--min-positive-relative-fold-rate", type=float, default=0.6)
    parser.add_argument("--min-test-overlap-adjusted-sharpe", type=float, default=0.5)
    parser.add_argument("--max-test-drawdown-limit", type=float, default=0.5)
    args = parser.parse_args()
    result = run_bottom_exclusion_walk_forward_cli(
        output_dir=Path(args.output_dir),
        factors=Path(args.factors) if args.factors else None,
        labels=Path(args.labels) if args.labels else None,
        bars=Path(args.bars) if args.bars else None,
        grid_config=Path(args.grid_config) if args.grid_config else None,
        source=args.source,
        data_root=Path(args.data_root),
        authority_bars_config=Path(args.authority_bars_config) if args.authority_bars_config else None,
        rolling_train_days=args.rolling_train_days,
        rolling_test_days=args.rolling_test_days,
        rolling_step_days=args.rolling_step_days,
        min_accepted_folds=args.min_accepted_folds,
        bottom_quantile=args.bottom_quantile,
        rebalance_interval=args.rebalance_interval,
        holding_period=args.holding_period,
        cost_bps=args.cost_bps,
        market_impact_bps=args.market_impact_bps,
        max_participation_rate=args.max_participation_rate,
        min_entry_amount=args.min_entry_amount,
        portfolio_value=args.portfolio_value,
        target_gross_exposure=args.target_gross_exposure,
        min_positive_relative_fold_rate=args.min_positive_relative_fold_rate,
        min_test_overlap_adjusted_sharpe=args.min_test_overlap_adjusted_sharpe,
        max_test_drawdown_limit=args.max_test_drawdown_limit,
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


def _infer_holding_period(labels: pd.DataFrame) -> int:
    if "horizon" not in labels.columns or labels.empty:
        return 1
    horizons = pd.to_numeric(labels["horizon"], errors="coerce").dropna()
    return int(horizons.iloc[0]) if not horizons.empty else 1


if __name__ == "__main__":
    main()
