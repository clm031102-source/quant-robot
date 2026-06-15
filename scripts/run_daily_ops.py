from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.ops.daily_ops import DEFAULT_MAX_DRAWDOWN_LIMIT, build_daily_ops_pack, write_daily_ops_pack

try:
    from scripts.run_paper_simulation import run_simulation
    from scripts.run_signal_snapshot import run_signal_snapshot
except ModuleNotFoundError:
    from run_paper_simulation import run_simulation
    from run_signal_snapshot import run_signal_snapshot


DEFAULT_PROMOTION_REVIEW = Path("data/reports/promotion_review/promotion_review_packet.json")
DEFAULT_READINESS_BOARD = Path("data/reports/pre_api_readiness_board/pre_api_readiness_board.json")
DEFAULT_PAPER_PROFILE_PACK = Path("data/reports/paper_profile_optimizer/paper_profile_optimizer_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/daily_ops")
DEFAULT_DATA_ROOT = Path("data/processed/etf_csv")


def run_daily_ops(
    promotion_review: str | Path = DEFAULT_PROMOTION_REVIEW,
    readiness_board: str | Path = DEFAULT_READINESS_BOARD,
    signal_snapshot: str | Path | None = None,
    paper_simulation: str | Path | None = None,
    paper_profile_pack: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    run_date: str | None = None,
    data_root: str | Path = DEFAULT_DATA_ROOT,
    source: str = "processed-bars",
    portfolio_value: float = 100000.0,
    positions_csv: str | Path | None = None,
    max_drawdown_limit: float | None = None,
) -> dict[str, Any]:
    promotion = _read_json(Path(promotion_review))
    readiness = _read_json(Path(readiness_board))
    profile_pack = _read_json(Path(paper_profile_pack)) if paper_profile_pack is not None else {}
    paper_profile = _selected_paper_profile(profile_pack)
    profile_params = _profile_params(paper_profile)
    effective_max_drawdown_limit = _effective_drawdown_limit(max_drawdown_limit, profile_pack, paper_profile)
    candidate = _candidate(promotion, readiness)
    market = str(candidate.get("market") or "CN_ETF")
    factor_name = str(candidate.get("factor_name") or "liquidity_10")
    factor_windows = _factor_windows(candidate, factor_name)
    top_n = _top_n(candidate)
    rebalance_interval = _rebalance_interval(candidate)

    output_path = Path(output_dir)
    signal = (
        _read_signal_artifact(Path(signal_snapshot))
        if signal_snapshot is not None
        else run_signal_snapshot(
            source=source,
            data_root=Path(data_root),
            market=market,
            factor_name=factor_name,
            factor_windows=factor_windows,
            top_n=top_n,
            portfolio_scope="market",
            max_asset_weight=profile_params["max_asset_weight"],
            max_market_weight=profile_params["max_market_weight"],
            max_gross_exposure=profile_params["max_gross_exposure"],
            min_cash_weight=profile_params["min_cash_weight"],
            portfolio_value=portfolio_value,
            positions_csv=Path(positions_csv) if positions_csv else None,
            output_dir=output_path / "signal_snapshot",
        )
    )
    simulation = (
        _read_simulation_artifact(Path(paper_simulation))
        if paper_simulation is not None
        else run_simulation(
            source=source,
            data_root=Path(data_root),
            market=market,
            factor_name=factor_name,
            factor_windows=factor_windows,
            top_n=top_n,
            rebalance_interval=rebalance_interval,
            initial_cash=portfolio_value,
            max_asset_weight=profile_params["max_asset_weight"],
            max_market_weight=profile_params["max_market_weight"],
            max_gross_exposure=profile_params["max_gross_exposure"],
            min_cash_weight=profile_params["min_cash_weight"],
            max_drawdown_guard=profile_params["max_drawdown_guard"],
            guard_cooldown_periods=profile_params["guard_cooldown_periods"],
            positions_csv=Path(positions_csv) if positions_csv else None,
            output_dir=output_path / "paper_simulation",
        )
    )
    pack = build_daily_ops_pack(
        promotion,
        readiness,
        signal,
        simulation,
        paper_profile=paper_profile,
        run_date=run_date,
        max_drawdown_limit=effective_max_drawdown_limit,
    )
    write_daily_ops_pack(output_path, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a research-to-paper daily ops pack. No broker connection or order placement.")
    parser.add_argument("--promotion-review", default=str(DEFAULT_PROMOTION_REVIEW))
    parser.add_argument("--readiness-board", default=str(DEFAULT_READINESS_BOARD))
    parser.add_argument("--signal-snapshot")
    parser.add_argument("--paper-simulation")
    parser.add_argument("--paper-profile-pack")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--run-date")
    parser.add_argument("--data-root", default=str(DEFAULT_DATA_ROOT))
    parser.add_argument("--source", choices=["fixture", "processed-bars"], default="processed-bars")
    parser.add_argument("--portfolio-value", default=100000.0, type=float)
    parser.add_argument("--positions-csv")
    parser.add_argument(
        "--max-drawdown-limit",
        default=None,
        type=float,
        help="Maximum tolerated equity drawdown. Positive values are normalized to negative limits.",
    )
    args = parser.parse_args()
    pack = run_daily_ops(
        promotion_review=Path(args.promotion_review),
        readiness_board=Path(args.readiness_board),
        signal_snapshot=Path(args.signal_snapshot) if args.signal_snapshot else None,
        paper_simulation=Path(args.paper_simulation) if args.paper_simulation else None,
        paper_profile_pack=Path(args.paper_profile_pack) if args.paper_profile_pack else None,
        output_dir=Path(args.output_dir),
        run_date=args.run_date,
        data_root=Path(args.data_root),
        source=args.source,
        portfolio_value=args.portfolio_value,
        positions_csv=Path(args.positions_csv) if args.positions_csv else None,
        max_drawdown_limit=args.max_drawdown_limit,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "run_date": pack["run_date"],
                "candidate": pack["candidate"],
                "decision": pack["decision"],
                "advisory_tickets": len(pack["advisory_tickets"]),
                "paper_profile": pack.get("paper_profile", {}),
                "risk": pack["risk"],
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


def _selected_paper_profile(profile_pack: dict[str, Any]) -> dict[str, Any]:
    selected = profile_pack.get("selected_profile") if isinstance(profile_pack, dict) else None
    return selected if isinstance(selected, dict) else {}


def _profile_params(paper_profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "max_asset_weight": _float(paper_profile.get("max_asset_weight"), 1.0),
        "max_market_weight": _float(paper_profile.get("max_market_weight"), 1.0),
        "max_gross_exposure": _float(paper_profile.get("max_gross_exposure"), 1.0),
        "min_cash_weight": _float(paper_profile.get("min_cash_weight"), 0.0),
        "max_drawdown_guard": paper_profile.get("max_drawdown_guard"),
        "guard_cooldown_periods": _int(paper_profile.get("guard_cooldown_periods"), 0),
    }


def _effective_drawdown_limit(
    explicit_limit: float | None,
    profile_pack: dict[str, Any],
    paper_profile: dict[str, Any],
) -> float:
    if explicit_limit is not None:
        return float(explicit_limit)
    tier_limit = _profile_tier_drawdown_limit(profile_pack, paper_profile)
    return tier_limit if tier_limit is not None else DEFAULT_MAX_DRAWDOWN_LIMIT


def _profile_tier_drawdown_limit(profile_pack: dict[str, Any], paper_profile: dict[str, Any]) -> float | None:
    tier_id = paper_profile.get("risk_tier")
    if not tier_id:
        return None
    policy = profile_pack.get("policy") if isinstance(profile_pack, dict) else None
    tiers = policy.get("risk_tiers") if isinstance(policy, dict) else None
    if not isinstance(tiers, list):
        return None
    for tier in tiers:
        if isinstance(tier, dict) and tier.get("tier_id") == tier_id and tier.get("max_drawdown_limit") is not None:
            return -abs(_float(tier.get("max_drawdown_limit"), DEFAULT_MAX_DRAWDOWN_LIMIT))
    return None


def _read_signal_artifact(path: Path) -> dict[str, Any]:
    if path.is_dir():
        manifest = _read_json(path / "manifest.json")
        targets = _read_csv_records(path / "targets.csv")
        rebalance = _read_csv_records(path / "rebalance_plan.csv")
        return {**manifest, "targets": targets, "rebalance_plan": rebalance}
    return _read_json(path)


def _read_simulation_artifact(path: Path) -> dict[str, Any]:
    if path.is_dir():
        manifest = _read_json(path / "manifest.json")
        return {
            **manifest,
            "fills": _read_csv_records(path / "fills.csv"),
            "guard_events": _read_csv_records(path / "guard_events.csv"),
            "execution_events": _read_csv_records(path / "execution_events.csv"),
        }
    return _read_json(path)


def _read_csv_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    frame = pd.read_csv(path)
    return frame.to_dict(orient="records") if not frame.empty else []


def _candidate(promotion: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    candidate = promotion.get("selected_candidate")
    if not isinstance(candidate, dict):
        candidate = readiness.get("selected_candidate")
    return candidate if isinstance(candidate, dict) else {}


def _factor_windows(candidate: dict[str, Any], factor_name: str) -> tuple[int, ...]:
    value = candidate.get("factor_windows")
    if isinstance(value, list):
        return tuple(int(item) for item in value)
    suffix = factor_name.rsplit("_", 1)[-1]
    return (int(suffix),) if suffix.isdigit() else (2, 3)


def _top_n(candidate: dict[str, Any]) -> int:
    case_id = str(candidate.get("case_id", ""))
    for part in case_id.split("_"):
        if part.startswith("top") and part[3:].isdigit():
            return int(part[3:])
    return int(candidate.get("top_n", 1) or 1)


def _rebalance_interval(candidate: dict[str, Any]) -> int:
    case_id = str(candidate.get("case_id", ""))
    for part in case_id.split("_"):
        if part.startswith("reb") and part[3:].isdigit():
            return int(part[3:])
    return int(candidate.get("rebalance_interval", 1) or 1)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


if __name__ == "__main__":
    main()
