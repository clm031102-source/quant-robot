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

from quant_robot.ops.cn_stock_tradeability_mask_join_smoke import run_cn_stock_tradeability_mask_join_smoke


DEFAULT_OUTPUT_DIR = Path("data/reports/cn_stock_tradeability_mask_join_smoke")


def run_cn_stock_tradeability_mask_join_smoke_cli(
    *,
    factors_path: str | Path,
    bars_path: str | Path,
    stock_basic_path: str | Path | None = None,
    stk_limit_path: str | Path | None = None,
    suspension_path: str | Path | None = None,
    namechange_path: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    top_n: int = 10,
    holding_period: int = 1,
    execution_lag: int = 1,
    cost_bps: float = 0.0,
    portfolio_scope: str = "market",
) -> dict[str, Any]:
    return run_cn_stock_tradeability_mask_join_smoke(
        factors=_read_frame(factors_path),
        bars=_read_frame(bars_path),
        stock_basic=_read_frame(stock_basic_path) if stock_basic_path is not None else None,
        stk_limit=_read_frame(stk_limit_path) if stk_limit_path is not None else None,
        suspension=_read_frame(suspension_path) if suspension_path is not None else None,
        namechange=_read_frame(namechange_path) if namechange_path is not None else None,
        output_dir=output_dir,
        top_n=top_n,
        holding_period=holding_period,
        execution_lag=execution_lag,
        cost_bps=cost_bps,
        portfolio_scope=portfolio_scope,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Smoke-test official CN stock tradeability masks through factor-matrix joins and portfolio execution."
    )
    parser.add_argument("--factors-path", required=True)
    parser.add_argument("--bars-path", required=True)
    parser.add_argument("--stock-basic-path")
    parser.add_argument("--stk-limit-path")
    parser.add_argument("--suspension-path")
    parser.add_argument("--namechange-path")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--top-n", type=int, default=10)
    parser.add_argument("--holding-period", type=int, default=1)
    parser.add_argument("--execution-lag", type=int, default=1)
    parser.add_argument("--cost-bps", type=float, default=0.0)
    parser.add_argument("--portfolio-scope", default="market")
    args = parser.parse_args()
    report = run_cn_stock_tradeability_mask_join_smoke_cli(
        factors_path=args.factors_path,
        bars_path=args.bars_path,
        stock_basic_path=args.stock_basic_path,
        stk_limit_path=args.stk_limit_path,
        suspension_path=args.suspension_path,
        namechange_path=args.namechange_path,
        output_dir=args.output_dir,
        top_n=args.top_n,
        holding_period=args.holding_period,
        execution_lag=args.execution_lag,
        cost_bps=args.cost_bps,
        portfolio_scope=args.portfolio_scope,
    )
    print(json.dumps(report, indent=2, sort_keys=True))


def _read_frame(path: str | Path | None) -> pd.DataFrame:
    if path is None:
        return pd.DataFrame()
    source = Path(path)
    if source.is_dir():
        files = sorted(source.rglob("*.parquet")) or sorted(source.rglob("*.csv"))
        if not files:
            raise ValueError(f"No parquet or csv files found under {source}")
        return pd.concat([_read_frame(file) for file in files], ignore_index=True)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(source)
    if suffix == ".parquet":
        return pd.read_parquet(source)
    raise ValueError(f"Unsupported input file type for {source}")


if __name__ == "__main__":
    main()
