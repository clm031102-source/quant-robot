from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.shortlist_trade_attribute_cash_filter import (  # noqa: E402
    parse_attribute_filter_spec,
)
from quant_robot.ops.simulation_shortlist_cohort_entry_timed import (  # noqa: E402
    build_simulation_shortlist_cohort_entry_timed,
    write_simulation_shortlist_cohort_entry_timed,
)


DEFAULT_OUTPUT_DIR = Path("data/reports/simulation_shortlist_cohort_entry_timed")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a cohort-level entry-timed candidate from trade rows."
    )
    parser.add_argument("--trades", required=True)
    parser.add_argument("--dragon-tiger-source", required=True)
    parser.add_argument("--public-factor-source", required=True)
    parser.add_argument("--public-factor-name", required=True)
    parser.add_argument("--public-factor-side", choices=("top", "bottom"), required=True)
    parser.add_argument("--candidate-name", required=True)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--dragon-candidate", default="dragon_hot_chase_20d")
    parser.add_argument("--public-factor-quantile", type=float, default=0.10)
    parser.add_argument("--public-factor-exposure-multiplier", type=float, default=1.50)
    parser.add_argument("--public-factor-tilt-risk-cap-column", default=None)
    parser.add_argument("--public-factor-tilt-risk-cap-operator", default="gt")
    parser.add_argument("--public-factor-tilt-risk-cap-value", type=float, default=None)
    parser.add_argument("--public-factor-tilt-risk-cap-multiplier", type=float, default=1.0)
    parser.add_argument("--trade-return-column", default="entry_cash_proxy_weighted_return")
    parser.add_argument("--trade-signal-date-column", default="signal_date")
    parser.add_argument("--trade-entry-date-column", default="entry_date")
    parser.add_argument("--trade-exit-date-column", default="exit_date")
    parser.add_argument("--weight-column", default="target_weight")
    parser.add_argument("--disable-dragon-cash-filter", action="store_true")
    parser.add_argument("--entry-attribute-cash-rule", action="append", default=[])
    parser.add_argument("--target-annual-vol", type=float, default=0.08)
    parser.add_argument("--lookback-events", type=int, default=84)
    parser.add_argument("--min-exposure", type=float, default=0.25)
    parser.add_argument("--max-exposure", type=float, default=1.0)
    parser.add_argument("--self-risk-window", type=int, default=21)
    parser.add_argument("--self-risk-threshold", type=float, default=0.0)
    parser.add_argument("--self-risk-exposure", type=float, default=0.8)
    args = parser.parse_args()

    result = build_simulation_shortlist_cohort_entry_timed(
        trades_source=Path(args.trades),
        dragon_tiger_source=Path(args.dragon_tiger_source),
        public_factor_source=Path(args.public_factor_source),
        public_factor_name=args.public_factor_name,
        public_factor_side=args.public_factor_side,
        candidate_name=args.candidate_name,
        dragon_candidate=args.dragon_candidate,
        public_factor_quantile=args.public_factor_quantile,
        public_factor_exposure_multiplier=args.public_factor_exposure_multiplier,
        public_factor_tilt_risk_cap_column=args.public_factor_tilt_risk_cap_column,
        public_factor_tilt_risk_cap_operator=args.public_factor_tilt_risk_cap_operator,
        public_factor_tilt_risk_cap_value=args.public_factor_tilt_risk_cap_value,
        public_factor_tilt_risk_cap_multiplier=args.public_factor_tilt_risk_cap_multiplier,
        trade_return_column=args.trade_return_column,
        trade_signal_date_column=args.trade_signal_date_column,
        trade_entry_date_column=args.trade_entry_date_column,
        trade_exit_date_column=args.trade_exit_date_column,
        weight_column=args.weight_column,
        apply_dragon_cash_filter=not args.disable_dragon_cash_filter,
        entry_attribute_cash_rules=tuple(
            parse_attribute_filter_spec(value) for value in args.entry_attribute_cash_rule
        ),
        target_annual_vol=args.target_annual_vol,
        lookback_events=args.lookback_events,
        min_exposure=args.min_exposure,
        max_exposure=args.max_exposure,
        self_risk_window=args.self_risk_window,
        self_risk_threshold=args.self_risk_threshold,
        self_risk_exposure=args.self_risk_exposure,
    )
    write_simulation_shortlist_cohort_entry_timed(args.output_dir, result)
    print(
        json.dumps(
            {
                "output_dir": str(Path(args.output_dir)),
                "summary": result["summary"],
                "paper_readiness": result["paper_readiness"],
                "metrics": result["metrics"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
