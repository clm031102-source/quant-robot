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

from quant_robot.ops.financial_pit_post_announcement_gap_reversal_walk_forward_preflight import (  # noqa: E402
    DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD,
    DEFAULT_MIN_CORR_CROSS_SECTION,
    DEFAULT_MIN_IC_T_STAT,
    DEFAULT_MIN_PAIR_OBSERVATIONS,
    DEFAULT_REFERENCE_HIGH_CORR_THRESHOLD,
    DEFAULT_REFERENCE_MEAN_ABS_CORR_THRESHOLD,
    build_financial_pit_post_announcement_gap_reversal_walk_forward_preflight,
    write_financial_pit_post_announcement_gap_reversal_walk_forward_preflight,
)


DEFAULT_FINANCIAL_ROOT = Path("data/processed/round202_financial_pit_signal_filtered_20260623")
DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_PREREGISTRATION_JSON = Path(
    "data/reports/financial_pit_post_announcement_gap_reversal_preregistration_round223_20260624/"
    "financial_pit_post_announcement_gap_reversal_preregistration.json"
)
DEFAULT_RESIDUAL_PRESCREEN_JSON = Path(
    "data/reports/financial_pit_post_announcement_gap_reversal_residual_prescreen_round223_20260624/"
    "financial_pit_post_announcement_gap_reversal_residual_prescreen.json"
)
DEFAULT_STARTUP_GATE_JSON = Path(
    "data/reports/factor_mining_startup_gate_round224_gap_reversal_wf_confirmed_20260624/"
    "factor_mining_startup_gate.json"
)
DEFAULT_PORTFOLIO_POLICY_JSON = Path("configs/portfolio_construction_policy_cn_stock.json")
DEFAULT_REGIME_POLICY_JSON = Path("configs/china_market_regime_control_policy_cn_stock.json")
DEFAULT_OUTPUT_DIR = Path(
    "data/reports/financial_pit_post_announcement_gap_reversal_walk_forward_preflight_round224_20260624"
)


def run_financial_pit_post_announcement_gap_reversal_walk_forward_preflight_cli(
    *,
    financial_root: str | Path = DEFAULT_FINANCIAL_ROOT,
    bars_roots: list[str | Path] | tuple[str | Path, ...] = DEFAULT_BARS_ROOTS,
    preregistration_json: str | Path = DEFAULT_PREREGISTRATION_JSON,
    residual_prescreen_json: str | Path = DEFAULT_RESIDUAL_PRESCREEN_JSON,
    startup_gate_json: str | Path | None = DEFAULT_STARTUP_GATE_JSON,
    portfolio_policy_json: str | Path | None = DEFAULT_PORTFOLIO_POLICY_JSON,
    regime_policy_json: str | Path | None = DEFAULT_REGIME_POLICY_JSON,
    candidate_plan_gate_json: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    min_pair_observations: int = DEFAULT_MIN_PAIR_OBSERVATIONS,
    min_corr_cross_section: int = DEFAULT_MIN_CORR_CROSS_SECTION,
    candidate_high_corr_threshold: float = DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD,
    reference_high_corr_threshold: float = DEFAULT_REFERENCE_HIGH_CORR_THRESHOLD,
    reference_mean_abs_corr_threshold: float = DEFAULT_REFERENCE_MEAN_ABS_CORR_THRESHOLD,
    min_ic_t_stat: float = DEFAULT_MIN_IC_T_STAT,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(
        financial_root=Path(financial_root),
        bars_roots=[Path(root) for root in bars_roots],
        preregistration_json=Path(preregistration_json),
        residual_prescreen_json=Path(residual_prescreen_json),
        startup_gate_json=Path(startup_gate_json) if startup_gate_json else None,
        portfolio_policy_json=Path(portfolio_policy_json) if portfolio_policy_json else None,
        regime_policy_json=Path(regime_policy_json) if regime_policy_json else None,
        candidate_plan_gate_json=Path(candidate_plan_gate_json) if candidate_plan_gate_json else None,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        min_pair_observations=min_pair_observations,
        min_corr_cross_section=min_corr_cross_section,
        candidate_high_corr_threshold=candidate_high_corr_threshold,
        reference_high_corr_threshold=reference_high_corr_threshold,
        reference_mean_abs_corr_threshold=reference_mean_abs_corr_threshold,
        min_ic_t_stat=min_ic_t_stat,
    )
    write_financial_pit_post_announcement_gap_reversal_walk_forward_preflight(output_dir, result)
    if not allow_not_ready and result.get("status") != "cleared":
        blockers = ", ".join(result.get("decision", {}).get("blockers", []) or [])
        raise RuntimeError(f"Financial PIT gap reversal walk-forward preflight is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Round224 financial PIT post-announcement gap reversal reference-dedup walk-forward preflight."
    )
    parser.add_argument("--financial-root", default=str(DEFAULT_FINANCIAL_ROOT))
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--preregistration-json", default=str(DEFAULT_PREREGISTRATION_JSON))
    parser.add_argument("--residual-prescreen-json", default=str(DEFAULT_RESIDUAL_PRESCREEN_JSON))
    parser.add_argument("--startup-gate-json", default=str(DEFAULT_STARTUP_GATE_JSON))
    parser.add_argument("--portfolio-policy-json", default=str(DEFAULT_PORTFOLIO_POLICY_JSON))
    parser.add_argument("--regime-policy-json", default=str(DEFAULT_REGIME_POLICY_JSON))
    parser.add_argument("--candidate-plan-gate-json")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--min-pair-observations", type=int, default=DEFAULT_MIN_PAIR_OBSERVATIONS)
    parser.add_argument("--min-corr-cross-section", type=int, default=DEFAULT_MIN_CORR_CROSS_SECTION)
    parser.add_argument("--candidate-high-corr-threshold", type=float, default=DEFAULT_CANDIDATE_HIGH_CORR_THRESHOLD)
    parser.add_argument("--reference-high-corr-threshold", type=float, default=DEFAULT_REFERENCE_HIGH_CORR_THRESHOLD)
    parser.add_argument("--reference-mean-abs-corr-threshold", type=float, default=DEFAULT_REFERENCE_MEAN_ABS_CORR_THRESHOLD)
    parser.add_argument("--min-ic-t-stat", type=float, default=DEFAULT_MIN_IC_T_STAT)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_financial_pit_post_announcement_gap_reversal_walk_forward_preflight_cli(
        financial_root=Path(args.financial_root),
        bars_roots=[Path(root) for root in (args.bars_root or DEFAULT_BARS_ROOTS)],
        preregistration_json=Path(args.preregistration_json),
        residual_prescreen_json=Path(args.residual_prescreen_json),
        startup_gate_json=Path(args.startup_gate_json) if args.startup_gate_json else None,
        portfolio_policy_json=Path(args.portfolio_policy_json) if args.portfolio_policy_json else None,
        regime_policy_json=Path(args.regime_policy_json) if args.regime_policy_json else None,
        candidate_plan_gate_json=Path(args.candidate_plan_gate_json) if args.candidate_plan_gate_json else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        min_pair_observations=args.min_pair_observations,
        min_corr_cross_section=args.min_corr_cross_section,
        candidate_high_corr_threshold=args.candidate_high_corr_threshold,
        reference_high_corr_threshold=args.reference_high_corr_threshold,
        reference_mean_abs_corr_threshold=args.reference_mean_abs_corr_threshold,
        min_ic_t_stat=args.min_ic_t_stat,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "summary": result.get("summary", {}),
                "decision": result.get("decision", {}),
                "preflight_policy": result.get("preflight_policy", {}),
                "promotion_policy": result.get("promotion_policy", {}),
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
