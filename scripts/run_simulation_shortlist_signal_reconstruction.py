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

from quant_robot.ops.simulation_shortlist_signal_reconstruction import (  # noqa: E402
    build_simulation_shortlist_signal_reconstruction,
    write_simulation_shortlist_signal_reconstruction,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/simulation_shortlist_signal_reconstruction")


def run_simulation_shortlist_signal_reconstruction_cli(
    *,
    trades: str | Path,
    event_source: str | Path,
    dragon_tiger_source: str | Path,
    public_factor_source: str | Path,
    public_factor_name: str,
    public_factor_side: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    candidate_name: str = "simulation_shortlist_candidate",
    dragon_candidate: str = "dragon_hot_chase_20d",
    public_factor_quantile: float = 0.10,
    public_factor_exposure_multiplier: float = 1.50,
    trade_return_column: str = "entry_cash_proxy_weighted_return",
    weight_column: str = "target_weight",
    event_return_column: str = "period_return",
    event_exposure_column: str = "final_exposure",
    reconciliation_tolerance: float = 1e-10,
) -> dict[str, Any]:
    result = build_simulation_shortlist_signal_reconstruction(
        trades_source=Path(trades),
        event_source=Path(event_source),
        dragon_tiger_source=Path(dragon_tiger_source),
        public_factor_source=Path(public_factor_source),
        candidate_name=candidate_name,
        dragon_candidate=dragon_candidate,
        public_factor_name=public_factor_name,
        public_factor_side=public_factor_side,
        public_factor_quantile=public_factor_quantile,
        public_factor_exposure_multiplier=public_factor_exposure_multiplier,
        trade_return_column=trade_return_column,
        weight_column=weight_column,
        event_return_column=event_return_column,
        event_exposure_column=event_exposure_column,
        reconciliation_tolerance=reconciliation_tolerance,
    )
    write_simulation_shortlist_signal_reconstruction(Path(output_dir), result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reconstruct asset-level rows for a simulation-shortlist event-return candidate."
    )
    parser.add_argument("--trades", required=True)
    parser.add_argument("--event-source", required=True)
    parser.add_argument("--dragon-tiger-source", required=True)
    parser.add_argument("--public-factor-source", required=True)
    parser.add_argument("--public-factor-name", required=True)
    parser.add_argument("--public-factor-side", choices=("top", "bottom"), required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--candidate-name", default="simulation_shortlist_candidate")
    parser.add_argument("--dragon-candidate", default="dragon_hot_chase_20d")
    parser.add_argument("--public-factor-quantile", type=float, default=0.10)
    parser.add_argument("--public-factor-exposure-multiplier", type=float, default=1.50)
    parser.add_argument("--trade-return-column", default="entry_cash_proxy_weighted_return")
    parser.add_argument("--weight-column", default="target_weight")
    parser.add_argument("--event-return-column", default="period_return")
    parser.add_argument("--event-exposure-column", default="final_exposure")
    parser.add_argument("--reconciliation-tolerance", type=float, default=1e-10)
    args = parser.parse_args()

    result = run_simulation_shortlist_signal_reconstruction_cli(
        trades=Path(args.trades),
        event_source=Path(args.event_source),
        dragon_tiger_source=Path(args.dragon_tiger_source),
        public_factor_source=Path(args.public_factor_source),
        public_factor_name=args.public_factor_name,
        public_factor_side=args.public_factor_side,
        output_dir=Path(args.output_dir),
        candidate_name=args.candidate_name,
        dragon_candidate=args.dragon_candidate,
        public_factor_quantile=args.public_factor_quantile,
        public_factor_exposure_multiplier=args.public_factor_exposure_multiplier,
        trade_return_column=args.trade_return_column,
        weight_column=args.weight_column,
        event_return_column=args.event_return_column,
        event_exposure_column=args.event_exposure_column,
        reconciliation_tolerance=args.reconciliation_tolerance,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "paper_readiness": result["paper_readiness"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
