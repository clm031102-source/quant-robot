from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for path in (SRC_ROOT, PROJECT_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from quant_robot.research.alpha_factory import AlphaFactoryConfig, run_tushare_alpha_factory
from quant_robot.ops.cn_stock_data_manifest import validate_cn_stock_data_manifest_packet
from quant_robot.ops.factor_mining_candidate_plan_gate import validate_candidate_plan_gate_packet
from quant_robot.ops.factor_mining_startup import validate_cleared_startup_gate_packet
from scripts.run_research_pipeline import load_research_bars


def run_alpha_factory_cli(
    source: str,
    data_root: str | Path,
    market: str,
    factor_input_root: str | Path | None,
    output_dir: str | Path,
    factor_source: str = "tushare_daily_basic",
    moneyflow_input_root: str | Path | None = None,
    top_n: int = 1,
    cost_bps: float = 5.0,
    execution_lag: int = 1,
    alpha: float = 0.05,
    start_date: str | None = None,
    end_date: str | None = None,
    min_trades: int = 30,
    min_ic_observations: int = 20,
    min_long_short_observations: int = 20,
    portfolio_value: float = 1_000_000.0,
    market_impact_bps: float = 10.0,
    max_participation_rate: float | None = 0.05,
    require_capacity_controls: bool = True,
    startup_gate_packet: str | Path | None = Path("data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json"),
    data_manifest_packet: str | Path | None = Path("data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json"),
    candidate_plan_gate_packet: str | Path | None = Path("data/reports/factor_mining_candidate_plan_gate/factor_mining_candidate_plan_gate.json"),
    allow_missing_startup_gate: bool = False,
    allow_review_required_data_manifest: bool = False,
) -> dict[str, object]:
    _enforce_cn_stock_startup_gate(
        source=source,
        market=market,
        startup_gate_packet=startup_gate_packet,
        data_manifest_packet=data_manifest_packet,
        candidate_plan_gate_packet=candidate_plan_gate_packet,
        allow_missing_startup_gate=allow_missing_startup_gate,
        allow_review_required_data_manifest=allow_review_required_data_manifest,
        data_root=Path(data_root),
    )
    bars = load_research_bars(source, Path(data_root), market)
    config = AlphaFactoryConfig(
        market=market,
        factor_source=factor_source,
        factor_input_root=Path(factor_input_root) if factor_input_root is not None else None,
        moneyflow_input_root=Path(moneyflow_input_root) if moneyflow_input_root is not None else None,
        output_dir=Path(output_dir),
        top_n=top_n,
        cost_bps=cost_bps,
        execution_lag=execution_lag,
        alpha=alpha,
        start_date=start_date,
        end_date=end_date,
        min_trades=min_trades,
        min_ic_observations=min_ic_observations,
        min_long_short_observations=min_long_short_observations,
        portfolio_value=portfolio_value,
        market_impact_bps=market_impact_bps,
        max_participation_rate=max_participation_rate,
        require_capacity_controls=require_capacity_controls,
    )
    return run_tushare_alpha_factory(bars, config)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Tushare alpha factory.")
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="processed-bars")
    parser.add_argument("--data-root", default="data/processed")
    parser.add_argument("--market", default="CN")
    parser.add_argument(
        "--factor-source",
        choices=["tushare_daily_basic", "tushare_moneyflow", "moneyflow_technical_combo"],
        default="tushare_daily_basic",
    )
    parser.add_argument("--factor-input-root", default="data/processed/tushare_factor_inputs")
    parser.add_argument("--moneyflow-input-root", default="data/processed/tushare_moneyflow_inputs")
    parser.add_argument("--output-dir", default="data/reports/tushare_alpha_factory")
    parser.add_argument("--top-n", default=1, type=int)
    parser.add_argument("--cost-bps", default=5.0, type=float)
    parser.add_argument("--execution-lag", default=1, type=int)
    parser.add_argument("--alpha", default=0.05, type=float)
    parser.add_argument("--start-date")
    parser.add_argument("--end-date")
    parser.add_argument("--min-trades", default=30, type=int)
    parser.add_argument("--min-ic-observations", default=20, type=int)
    parser.add_argument("--min-long-short-observations", default=20, type=int)
    parser.add_argument("--portfolio-value", default=1_000_000.0, type=float)
    parser.add_argument("--market-impact-bps", default=10.0, type=float)
    parser.add_argument("--max-participation-rate", default=0.05, type=float)
    parser.add_argument("--allow-missing-capacity-controls", action="store_true")
    parser.add_argument(
        "--startup-gate-packet",
        default="data/reports/factor_mining_startup_gate/factor_mining_startup_gate.json",
        help="Cleared CN stock factor-mining startup gate packet required for processed CN runs.",
    )
    parser.add_argument(
        "--allow-missing-startup-gate",
        action="store_true",
        help="Deprecated. CN processed-bars runs cannot bypass the startup gate.",
    )
    parser.add_argument(
        "--data-manifest-packet",
        default="data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json",
        help="CN stock data manifest packet required for processed CN runs.",
    )
    parser.add_argument(
        "--candidate-plan-gate-packet",
        default="data/reports/factor_mining_candidate_plan_gate/factor_mining_candidate_plan_gate.json",
        help="Cleared CN stock candidate plan gate packet required before processed CN factor generation.",
    )
    parser.add_argument(
        "--allow-review-required-data-manifest",
        action="store_true",
        help="Allow a reviewed CN stock data manifest that has warnings but no blockers.",
    )
    args = parser.parse_args()
    result = run_alpha_factory_cli(
        source=args.source,
        data_root=Path(args.data_root),
        market=args.market,
        factor_input_root=Path(args.factor_input_root),
        factor_source=args.factor_source,
        moneyflow_input_root=Path(args.moneyflow_input_root),
        output_dir=Path(args.output_dir),
        top_n=args.top_n,
        cost_bps=args.cost_bps,
        execution_lag=args.execution_lag,
        alpha=args.alpha,
        start_date=args.start_date,
        end_date=args.end_date,
        min_trades=args.min_trades,
        min_ic_observations=args.min_ic_observations,
        min_long_short_observations=args.min_long_short_observations,
        portfolio_value=args.portfolio_value,
        market_impact_bps=args.market_impact_bps,
        max_participation_rate=args.max_participation_rate,
        require_capacity_controls=not args.allow_missing_capacity_controls,
        startup_gate_packet=Path(args.startup_gate_packet) if args.startup_gate_packet else None,
        data_manifest_packet=Path(args.data_manifest_packet) if args.data_manifest_packet else None,
        candidate_plan_gate_packet=Path(args.candidate_plan_gate_packet) if args.candidate_plan_gate_packet else None,
        allow_missing_startup_gate=args.allow_missing_startup_gate,
        allow_review_required_data_manifest=args.allow_review_required_data_manifest,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "top": result["candidate_leaderboard"][:10],
            },
            indent=2,
            sort_keys=True,
        )
    )


def _enforce_cn_stock_startup_gate(
    *,
    source: str,
    market: str,
    startup_gate_packet: str | Path | None,
    data_manifest_packet: str | Path | None,
    candidate_plan_gate_packet: str | Path | None,
    allow_missing_startup_gate: bool,
    allow_review_required_data_manifest: bool,
    data_root: Path,
) -> None:
    if source != "processed-bars" or market.upper() != "CN":
        return
    if allow_missing_startup_gate:
        raise ValueError("CN processed-bars alpha factory startup gate cannot be bypassed")
    validate_cleared_startup_gate_packet(
        startup_gate_packet,
        context="CN processed-bars alpha factory",
    )
    validate_cn_stock_data_manifest_packet(
        data_manifest_packet,
        expected_source_root=data_root,
        allow_review_required=allow_review_required_data_manifest,
        context="CN processed-bars alpha factory",
    )
    validate_candidate_plan_gate_packet(
        candidate_plan_gate_packet,
        context="CN processed-bars alpha factory",
    )


if __name__ == "__main__":
    main()
