from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.ops.risk_candidate_selector import (
    DEFAULT_MAX_DRAWDOWN_LIMIT,
    DEFAULT_MIN_PAPER_SHARPE,
    DEFAULT_MIN_RELATIVE_RETURN,
    DEFAULT_MIN_TRADES,
    DEFAULT_MIN_WALK_FORWARD_SHARPE,
    build_risk_candidate_pack,
    write_risk_candidate_pack,
)


DEFAULT_PROMOTION_REPORT = Path("data/reports/promotion_gate_cn_etf_candidate_search/promotion_report.json")
DEFAULT_DAILY_OPS_PACK = Path("data/reports/daily_ops/daily_ops_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/risk_candidate_selector")


def run_risk_candidate_selector(
    promotion_report: str | Path = DEFAULT_PROMOTION_REPORT,
    daily_ops_pack: str | Path = DEFAULT_DAILY_OPS_PACK,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    max_drawdown_limit: float = DEFAULT_MAX_DRAWDOWN_LIMIT,
    min_walk_forward_sharpe: float = DEFAULT_MIN_WALK_FORWARD_SHARPE,
    min_relative_return: float = DEFAULT_MIN_RELATIVE_RETURN,
    min_paper_sharpe: float = DEFAULT_MIN_PAPER_SHARPE,
    min_trades: int = DEFAULT_MIN_TRADES,
) -> dict[str, Any]:
    promotion = _read_json(Path(promotion_report))
    daily = _read_json(Path(daily_ops_pack))
    pack = build_risk_candidate_pack(
        promotion,
        daily,
        max_drawdown_limit=max_drawdown_limit,
        min_walk_forward_sharpe=min_walk_forward_sharpe,
        min_relative_return=min_relative_return,
        min_paper_sharpe=min_paper_sharpe,
        min_trades=min_trades,
    )
    write_risk_candidate_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a Phase 5.1 risk-constrained candidate selector pack.")
    parser.add_argument("--promotion-report", default=str(DEFAULT_PROMOTION_REPORT))
    parser.add_argument("--daily-ops-pack", default=str(DEFAULT_DAILY_OPS_PACK))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--max-drawdown-limit", default=DEFAULT_MAX_DRAWDOWN_LIMIT, type=float)
    parser.add_argument("--min-walk-forward-sharpe", default=DEFAULT_MIN_WALK_FORWARD_SHARPE, type=float)
    parser.add_argument("--min-relative-return", default=DEFAULT_MIN_RELATIVE_RETURN, type=float)
    parser.add_argument("--min-paper-sharpe", default=DEFAULT_MIN_PAPER_SHARPE, type=float)
    parser.add_argument("--min-trades", default=DEFAULT_MIN_TRADES, type=int)
    args = parser.parse_args()
    pack = run_risk_candidate_selector(
        promotion_report=Path(args.promotion_report),
        daily_ops_pack=Path(args.daily_ops_pack),
        output_dir=Path(args.output_dir),
        max_drawdown_limit=args.max_drawdown_limit,
        min_walk_forward_sharpe=args.min_walk_forward_sharpe,
        min_relative_return=args.min_relative_return,
        min_paper_sharpe=args.min_paper_sharpe,
        min_trades=args.min_trades,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "selection_status": pack["selection_status"],
                "summary": pack["summary"],
                "selected_candidate": pack["selected_candidate"],
                "paper_trading_allowed": pack["paper_trading_allowed"],
                "live_boundary_allowed": pack["live_boundary_allowed"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
