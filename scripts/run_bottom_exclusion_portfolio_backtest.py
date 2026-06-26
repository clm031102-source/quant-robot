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

from quant_robot.data.fixtures import load_demo_market_bars  # noqa: E402
from quant_robot.experiments.runner import (  # noqa: E402
    _filter_bars_for_asset_universe,
    _filter_bars_for_precompute,
    _precompute_factor_matrix,
    load_experiment_grid_config,
)
from quant_robot.ops.bottom_exclusion_portfolio_backtest import (  # noqa: E402
    run_bottom_exclusion_portfolio_backtest,
    write_bottom_exclusion_portfolio_backtest,
)
from quant_robot.research.labels import make_forward_returns  # noqa: E402
from quant_robot.storage.authority_bars import load_authority_processed_bars_from_config  # noqa: E402
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402


DEFAULT_OUTPUT_DIR = Path("data/reports/bottom_exclusion_portfolio_backtest")


def run_bottom_exclusion_portfolio_backtest_cli(
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
    target_gross_exposure: float = 1.0,
    min_positive_relative_fold_rate: float = 0.6,
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
        resolved_holding = holding_period or _infer_holding_period(label_frame)
        source_report = (
            f"factors={Path(factors)} labels={Path(labels)} bars={Path(bars)} "
            f"rebalance_interval={resolved_rebalance} holding_period={resolved_holding}"
        )

    result = run_bottom_exclusion_portfolio_backtest(
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
        min_positive_relative_fold_rate=min_positive_relative_fold_rate,
        min_overlap_adjusted_sharpe=min_overlap_adjusted_sharpe,
        max_drawdown_limit=max_drawdown_limit,
    )
    write_bottom_exclusion_portfolio_backtest(output_dir, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a costed bottom-exclusion risk-filter portfolio backtest.")
    parser.add_argument("--grid-config", help="Experiment-grid config used to precompute factors, labels, and bars.")
    parser.add_argument("--factors", help="Factor matrix CSV/JSON/Parquet path. Requires --labels and --bars.")
    parser.add_argument("--labels", help="Forward-return labels CSV/JSON/Parquet path. Requires --factors and --bars.")
    parser.add_argument("--bars", help="Bars CSV/JSON/Parquet path with amount. Requires --factors and --labels.")
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
    parser.add_argument("--target-gross-exposure", type=float, default=1.0)
    parser.add_argument("--min-positive-relative-fold-rate", type=float, default=0.6)
    parser.add_argument("--min-overlap-adjusted-sharpe", type=float, default=0.5)
    parser.add_argument("--max-drawdown-limit", type=float, default=0.5)
    args = parser.parse_args()

    result = run_bottom_exclusion_portfolio_backtest_cli(
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
        min_positive_relative_fold_rate=args.min_positive_relative_fold_rate,
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


def _build_frames_from_grid(
    config_path: Path,
    *,
    source: str,
    data_root: Path,
    authority_bars_config: Path | None,
    rebalance_interval: int | None,
    holding_period: int | None,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str, int, int]:
    config = load_experiment_grid_config(config_path)
    bars = _load_bars(
        source,
        data_root,
        config.markets,
        authority_bars_config=authority_bars_config,
    )
    bars = _filter_bars_for_asset_universe(bars, config)
    filtered = _filter_bars_for_precompute(bars, config)
    factors = _precompute_factor_matrix(filtered, config)
    if factors is None or factors.empty:
        raise ValueError(f"Grid config produced no factor matrix: {config_path}")
    labels = make_forward_returns(
        filtered,
        horizons=(config.forward_horizon,),
        execution_lag=config.execution_lag,
    )
    resolved_rebalance = rebalance_interval or int(config.rebalance_intervals[0])
    resolved_holding = holding_period or int(config.forward_horizon)
    source_report = f"grid_config={config_path} rebalance_interval={resolved_rebalance} holding_period={resolved_holding}"
    return factors, labels, filtered, source_report, resolved_rebalance, resolved_holding


def _load_bars(
    source: str,
    data_root: Path,
    markets: tuple[str, ...],
    *,
    authority_bars_config: Path | None,
) -> pd.DataFrame:
    if source == "fixture":
        return load_demo_market_bars()
    if source == "authority-processed-bars":
        if authority_bars_config is None:
            raise ValueError("authority_bars_config is required for authority-processed-bars source")
        return load_authority_processed_bars_from_config(authority_bars_config, markets=markets)
    if source != "processed-bars":
        raise ValueError(f"Unsupported source: {source}")
    frames = [load_processed_bars(data_root, market) for market in markets if market.upper() != "ALL"]
    if not frames:
        raise ValueError("processed-bars source requires at least one specific market")
    return pd.concat(frames, ignore_index=True)


def _load_frame(path: Path) -> pd.DataFrame:
    if path.is_dir():
        files = sorted([*path.rglob("*.parquet"), *path.rglob("*.csv"), *path.rglob("*.json"), *path.rglob("*.jsonl")])
        if not files:
            raise FileNotFoundError(f"No tabular files found under {path}")
        return pd.concat([_load_frame(file) for file in files], ignore_index=True)
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".jsonl", ".ndjson"}:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return pd.DataFrame(rows)
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return pd.DataFrame(data)
        if isinstance(data, dict):
            for key in ("rows", "factors", "labels", "bars", "data"):
                value = data.get(key)
                if isinstance(value, list):
                    return pd.DataFrame(value)
        raise ValueError(f"JSON file does not contain a supported row list: {path}")
    raise ValueError(f"Unsupported frame file type: {path}")


def _infer_holding_period(labels: pd.DataFrame) -> int:
    if "horizon" not in labels.columns or labels.empty:
        return 1
    horizons = pd.to_numeric(labels["horizon"], errors="coerce").dropna()
    if horizons.empty:
        return 1
    return int(horizons.iloc[0])


if __name__ == "__main__":
    main()
