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

from quant_robot.ops.historical_lead_recovery_audit import (  # noqa: E402
    build_historical_lead_recovery_audit,
    write_historical_lead_recovery_audit,
)


DEFAULT_TURNOVER_CONVERSION_JSON = Path(
    "data/reports/turnover_repair_champion_portfolio_conversion_round126_20260622/"
    "turnover_repair_champion_portfolio_conversion.json"
)
DEFAULT_MARKET_RESIDUAL_DEDUP_JSON = Path(
    "data/reports/market_residual_lead_exposure_dedup_round112_20260622/"
    "market_residual_lead_exposure_dedup.json"
)
DEFAULT_PUBLIC_ALPHA101_DEDUP_JSON = Path(
    "data/reports/public_alpha101_reference_exposure_dedup_round116_20260622/"
    "public_alpha101_reference_exposure_dedup.json"
)
DEFAULT_PUBLIC_REFERENCE_REPLAY_JSON = Path(
    "data/reports/round252_public_reference_multi_family_full_2015_2025_20260625/"
    "public_reference_multi_family_prescreen.json"
)
DEFAULT_OUTPUT_DIR = Path("data/reports/round263_historical_lead_recovery_audit_20260626")


def run_historical_lead_recovery_audit_cli(
    *,
    turnover_conversion_json: str | Path = DEFAULT_TURNOVER_CONVERSION_JSON,
    market_residual_dedup_json: str | Path = DEFAULT_MARKET_RESIDUAL_DEDUP_JSON,
    public_alpha101_dedup_json: str | Path = DEFAULT_PUBLIC_ALPHA101_DEDUP_JSON,
    public_reference_replay_json: str | Path = DEFAULT_PUBLIC_REFERENCE_REPLAY_JSON,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    user_drawdown_soft_floor: float = -0.30,
) -> dict[str, Any]:
    audit = build_historical_lead_recovery_audit(
        turnover_conversion=_read_json(turnover_conversion_json),
        market_residual_dedup=_read_json(market_residual_dedup_json),
        public_alpha101_dedup=_read_json(public_alpha101_dedup_json),
        public_reference_replay=_read_json(public_reference_replay_json),
        source_reports={
            "turnover_conversion": turnover_conversion_json,
            "market_residual_dedup": market_residual_dedup_json,
            "public_alpha101_dedup": public_alpha101_dedup_json,
            "public_reference_replay": public_reference_replay_json,
        },
        user_drawdown_soft_floor=user_drawdown_soft_floor,
    )
    write_historical_lead_recovery_audit(output_dir, audit)
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit whether old bright CN-stock factor leads are recoverable.")
    parser.add_argument("--turnover-conversion-json", default=str(DEFAULT_TURNOVER_CONVERSION_JSON))
    parser.add_argument("--market-residual-dedup-json", default=str(DEFAULT_MARKET_RESIDUAL_DEDUP_JSON))
    parser.add_argument("--public-alpha101-dedup-json", default=str(DEFAULT_PUBLIC_ALPHA101_DEDUP_JSON))
    parser.add_argument("--public-reference-replay-json", default=str(DEFAULT_PUBLIC_REFERENCE_REPLAY_JSON))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--user-drawdown-soft-floor", type=float, default=-0.30)
    args = parser.parse_args()
    audit = run_historical_lead_recovery_audit_cli(
        turnover_conversion_json=args.turnover_conversion_json,
        market_residual_dedup_json=args.market_residual_dedup_json,
        public_alpha101_dedup_json=args.public_alpha101_dedup_json,
        public_reference_replay_json=args.public_reference_replay_json,
        output_dir=args.output_dir,
        user_drawdown_soft_floor=args.user_drawdown_soft_floor,
    )
    print(
        json.dumps(
            {
                "stage": audit["stage"],
                "status": audit["status"],
                "summary": audit["summary"],
                "decision": audit["decision"],
                "live_boundary_allowed": audit["live_boundary_allowed"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
