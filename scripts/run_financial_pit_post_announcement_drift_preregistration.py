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

from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (  # noqa: E402
    build_financial_pit_post_announcement_drift_preregistration,
    write_financial_pit_post_announcement_drift_preregistration,
)


DEFAULT_FINANCIAL_ROOT = Path("data/processed/round202_financial_pit_signal_filtered_20260623")
DEFAULT_BARS_ROOTS = (
    Path("data/processed/cn_stock_long_history_2015_202306"),
    Path("data/processed/office_desktop_20260616_combined_research"),
)
DEFAULT_CANDIDATE_SEED = Path("configs/family_rotation_seed_round222_financial_pit_post_announcement_drift_20260624.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/financial_pit_post_announcement_drift_preregistration_round222_20260624")


def run_financial_pit_post_announcement_drift_preregistration_cli(
    *,
    financial_root: str | Path = DEFAULT_FINANCIAL_ROOT,
    bars_roots: list[str | Path] | tuple[str | Path, ...] = DEFAULT_BARS_ROOTS,
    candidate_seed_json: str | Path | None = DEFAULT_CANDIDATE_SEED,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    analysis_start_date: str = "2015-01-01",
    analysis_end_date: str = "2025-12-31",
    include_final_holdout: bool = False,
    min_assets: int = 50,
    min_signal_dates: int = 20,
    min_event_reaction_coverage: float = 0.80,
    allow_not_ready: bool = False,
) -> dict[str, Any]:
    result = build_financial_pit_post_announcement_drift_preregistration(
        financial_root=Path(financial_root),
        bars_roots=[Path(root) for root in bars_roots],
        candidate_seed_json=Path(candidate_seed_json) if candidate_seed_json else None,
        analysis_start_date=analysis_start_date,
        analysis_end_date=analysis_end_date,
        include_final_holdout=include_final_holdout,
        min_assets=min_assets,
        min_signal_dates=min_signal_dates,
        min_event_reaction_coverage=min_event_reaction_coverage,
    )
    write_financial_pit_post_announcement_drift_preregistration(output_dir, result)
    if not allow_not_ready and not result["summary"].get("passes", False):
        blockers = ", ".join(result["summary"].get("blockers", []) or [])
        raise RuntimeError(f"Financial PIT post-announcement drift preregistration is not ready: {blockers}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Round222 financial PIT post-announcement drift preregistration.")
    parser.add_argument("--financial-root", default=str(DEFAULT_FINANCIAL_ROOT))
    parser.add_argument("--bars-root", action="append", default=None)
    parser.add_argument("--candidate-seed-json", default=str(DEFAULT_CANDIDATE_SEED))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--analysis-start-date", default="2015-01-01")
    parser.add_argument("--analysis-end-date", default="2025-12-31")
    parser.add_argument("--include-final-holdout", action="store_true")
    parser.add_argument("--min-assets", type=int, default=50)
    parser.add_argument("--min-signal-dates", type=int, default=20)
    parser.add_argument("--min-event-reaction-coverage", type=float, default=0.80)
    parser.add_argument("--allow-not-ready", action="store_true")
    args = parser.parse_args()
    result = run_financial_pit_post_announcement_drift_preregistration_cli(
        financial_root=Path(args.financial_root),
        bars_roots=[Path(root) for root in (args.bars_root or DEFAULT_BARS_ROOTS)],
        candidate_seed_json=Path(args.candidate_seed_json) if args.candidate_seed_json else None,
        output_dir=Path(args.output_dir),
        analysis_start_date=args.analysis_start_date,
        analysis_end_date=args.analysis_end_date,
        include_final_holdout=args.include_final_holdout,
        min_assets=args.min_assets,
        min_signal_dates=args.min_signal_dates,
        min_event_reaction_coverage=args.min_event_reaction_coverage,
        allow_not_ready=args.allow_not_ready,
    )
    print(
        json.dumps(
            {
                "summary": result["summary"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
