from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable

from quant_robot.ops.iterative_observation_expansion import (
    build_iterative_observation_expansion_pack,
    write_iterative_observation_expansion_pack,
)

try:
    from scripts.run_expanded_observation_replay import run_expanded_observation_replay
except ModuleNotFoundError:  # pragma: no cover - exercised when this file is run directly
    from run_expanded_observation_replay import run_expanded_observation_replay


DEFAULT_OBSERVATION_SUFFICIENCY_PACK = Path("data/reports/observation_sufficiency/observation_sufficiency_pack.json")
DEFAULT_PROFILE_OBSERVATION_PACK = Path("data/reports/profile_observation/profile_observation_pack.json")
DEFAULT_REPORT_DIR = Path("data/reports/iterative_observation_expansion")


def run_iterative_observation_expansion(
    observation_sufficiency_pack: str | Path = DEFAULT_OBSERVATION_SUFFICIENCY_PACK,
    profile_observation_pack: str | Path = DEFAULT_PROFILE_OBSERVATION_PACK,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    source: str = "tushare",
    market: str = "CN_ETF",
    max_rounds: int = 3,
    execute: bool = True,
    expanded_observation_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    initial_sufficiency = _read_json(Path(observation_sufficiency_pack))
    output_path = Path(report_dir)
    if not _can_extend(initial_sufficiency):
        pack = build_iterative_observation_expansion_pack(initial_sufficiency, max_rounds=max_rounds)
        write_iterative_observation_expansion_pack(output_path, pack)
        return pack

    runner = expanded_observation_runner or run_expanded_observation_replay
    current_sufficiency_path = Path(observation_sufficiency_pack)
    rounds: list[dict[str, Any]] = []
    expansion_error: dict[str, Any] | None = None
    for round_index in range(1, max_rounds + 1):
        round_dir = output_path / f"round_{round_index:02d}"
        try:
            expanded_pack = runner(
                observation_sufficiency_pack=current_sufficiency_path,
                profile_observation_pack=Path(profile_observation_pack),
                report_dir=round_dir,
                source=source,
                market=market,
                execute=execute,
            )
        except Exception as exc:  # pragma: no cover - exact exception depends on downstream workflow
            expansion_error = {"stage": "iterative_expansion_round", "error": str(exc), "round": round_index}
            break
        _write_round_sufficiency_pack(round_dir / "observation_sufficiency_pack.json", expanded_pack)
        rounds.append({"round": round_index, "report_dir": str(round_dir), "expanded_observation_replay": expanded_pack})
        if _expanded_cleared(expanded_pack):
            break
        final_sufficiency = _final_sufficiency(expanded_pack)
        if not _can_extend(final_sufficiency):
            break
        current_sufficiency_path = round_dir / "observation_sufficiency_pack.json"

    pack = build_iterative_observation_expansion_pack(
        initial_sufficiency,
        rounds=rounds,
        max_rounds=max_rounds,
        expansion_error=expansion_error,
    )
    write_iterative_observation_expansion_pack(output_path, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Iteratively expand the paper observation window until sample sufficiency clears or a round limit is reached.")
    parser.add_argument("--observation-sufficiency-pack", default=str(DEFAULT_OBSERVATION_SUFFICIENCY_PACK))
    parser.add_argument("--profile-observation-pack", default=str(DEFAULT_PROFILE_OBSERVATION_PACK))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--source", choices=["tushare", "tushare-fixture"], default="tushare")
    parser.add_argument("--market", default="CN_ETF")
    parser.add_argument("--max-rounds", default=3, type=int)
    parser.add_argument("--dry-run", action="store_true", help="Do not execute expanded recent-data refresh rounds.")
    args = parser.parse_args()
    pack = run_iterative_observation_expansion(
        observation_sufficiency_pack=Path(args.observation_sufficiency_pack),
        profile_observation_pack=Path(args.profile_observation_pack),
        report_dir=Path(args.report_dir),
        source=args.source,
        market=args.market,
        max_rounds=args.max_rounds,
        execute=not args.dry_run,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "round_count": pack["round_count"],
                "decision": pack["decision"],
                "report_dir": str(Path(args.report_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _can_extend(pack: dict[str, Any]) -> bool:
    recommendation = pack.get("recommendation", {}) if isinstance(pack.get("recommendation"), dict) else {}
    return (
        pack.get("status") == "needs_more_observation_data"
        and recommendation.get("priority") == "extend_recent_data_window"
        and bool(recommendation.get("suggested_start_date"))
        and bool(recommendation.get("suggested_end_date"))
    )


def _expanded_cleared(pack: dict[str, Any]) -> bool:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    return bool(decision.get("expanded_observation_cleared", False))


def _final_sufficiency(pack: dict[str, Any]) -> dict[str, Any]:
    final = pack.get("final_observation_sufficiency")
    return final if isinstance(final, dict) else {}


def _write_round_sufficiency_pack(path: Path, expanded_pack: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    final_sufficiency = _final_sufficiency(expanded_pack)
    path.write_text(json.dumps(final_sufficiency, indent=2, sort_keys=True), encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
