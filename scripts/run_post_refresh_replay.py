from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.post_refresh_replay import build_post_refresh_replay_pack, write_post_refresh_replay_pack

try:
    from scripts.run_daily_ops import run_daily_ops
    from scripts.run_profile_observation import run_profile_observation
except ModuleNotFoundError:  # pragma: no cover - exercised when this file is run directly
    from run_daily_ops import run_daily_ops
    from run_profile_observation import run_profile_observation


DEFAULT_RECENT_DATA_REFRESH_PACK = Path("data/reports/recent_data_refresh/recent_data_refresh_pack.json")
DEFAULT_REPORT_DIR = Path("data/reports/post_refresh_replay")
DEFAULT_PROMOTION_REVIEW = Path("data/reports/promotion_review/promotion_review_packet.json")
DEFAULT_READINESS_BOARD = Path("data/reports/pre_api_readiness_board/pre_api_readiness_board.json")
DEFAULT_PAPER_PROFILE_PACK = Path("data/reports/paper_profile_optimizer/paper_profile_optimizer_pack.json")


def run_post_refresh_replay(
    recent_data_refresh_pack: str | Path = DEFAULT_RECENT_DATA_REFRESH_PACK,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    promotion_review: str | Path = DEFAULT_PROMOTION_REVIEW,
    readiness_board: str | Path = DEFAULT_READINESS_BOARD,
    paper_profile_pack: str | Path = DEFAULT_PAPER_PROFILE_PACK,
    run_date: str | None = None,
    portfolio_value: float = 100000.0,
    positions_csv: str | Path | None = None,
    max_drawdown_limit: float | None = None,
    daily_ops_runner: Callable[..., dict[str, Any]] | None = None,
    profile_observation_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    recent_pack = _read_json(Path(recent_data_refresh_pack))
    output_path = Path(report_dir)
    daily_ops_output_dir = output_path / "daily_ops"
    observation_output_dir = output_path / "profile_observation"
    if not _recent_refresh_ready(recent_pack):
        pack = build_post_refresh_replay_pack(
            recent_pack,
            daily_ops_output_dir=daily_ops_output_dir,
            profile_observation_output_dir=observation_output_dir,
        )
        write_post_refresh_replay_pack(output_path, pack)
        return pack

    daily_runner = daily_ops_runner or run_daily_ops
    observation_runner = profile_observation_runner or run_profile_observation
    effective_run_date = run_date or _target_end(recent_pack)
    daily_ops_pack: dict[str, Any] = {}
    observation_pack: dict[str, Any] = {}
    replay_error: dict[str, Any] | None = None
    try:
        daily_ops_pack = daily_runner(
            promotion_review=Path(promotion_review),
            readiness_board=Path(readiness_board),
            paper_profile_pack=Path(paper_profile_pack),
            output_dir=daily_ops_output_dir,
            run_date=effective_run_date,
            data_root=Path(str(recent_pack.get("output_dir", ""))),
            source="processed-bars",
            portfolio_value=portfolio_value,
            positions_csv=Path(positions_csv) if positions_csv else None,
            max_drawdown_limit=max_drawdown_limit,
        )
        observation_pack = observation_runner(
            daily_ops_pack=daily_ops_output_dir / "daily_ops_pack.json",
            simulation_dir=daily_ops_output_dir / "paper_simulation",
            output_dir=observation_output_dir,
            run_date=effective_run_date,
        )
    except Exception as exc:  # pragma: no cover - exact exception type depends on downstream workflow
        replay_error = {"stage": "post_refresh_downstream", "error": str(exc)}

    pack = build_post_refresh_replay_pack(
        recent_pack,
        daily_ops=daily_ops_pack,
        profile_observation=observation_pack,
        daily_ops_output_dir=daily_ops_output_dir,
        profile_observation_output_dir=observation_output_dir,
        replay_error=replay_error,
    )
    write_post_refresh_replay_pack(output_path, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay paper Daily Ops and profile observation after recent data refresh clears.")
    parser.add_argument("--recent-data-refresh-pack", default=str(DEFAULT_RECENT_DATA_REFRESH_PACK))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--promotion-review", default=str(DEFAULT_PROMOTION_REVIEW))
    parser.add_argument("--readiness-board", default=str(DEFAULT_READINESS_BOARD))
    parser.add_argument("--paper-profile-pack", default=str(DEFAULT_PAPER_PROFILE_PACK))
    parser.add_argument("--run-date")
    parser.add_argument("--portfolio-value", default=100000.0, type=float)
    parser.add_argument("--positions-csv")
    parser.add_argument("--max-drawdown-limit", default=None, type=float)
    args = parser.parse_args()
    pack = run_post_refresh_replay(
        recent_data_refresh_pack=Path(args.recent_data_refresh_pack),
        report_dir=Path(args.report_dir),
        promotion_review=Path(args.promotion_review),
        readiness_board=Path(args.readiness_board),
        paper_profile_pack=Path(args.paper_profile_pack),
        run_date=args.run_date,
        portfolio_value=args.portfolio_value,
        positions_csv=Path(args.positions_csv) if args.positions_csv else None,
        max_drawdown_limit=args.max_drawdown_limit,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "decision": pack["decision"],
                "daily_ops_output_dir": pack["daily_ops_output_dir"],
                "profile_observation_output_dir": pack["profile_observation_output_dir"],
                "report_dir": str(Path(args.report_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _recent_refresh_ready(pack: dict[str, Any]) -> bool:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    return bool(decision.get("recent_data_ready", False) and decision.get("signal_data_stale_cleared", False))


def _target_end(pack: dict[str, Any]) -> str | None:
    target = pack.get("target_window", {}) if isinstance(pack.get("target_window"), dict) else {}
    value = target.get("end_date")
    return str(value)[:10] if value else None


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
