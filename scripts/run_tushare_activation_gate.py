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

from quant_robot.data.readiness import check_tushare_readiness
from quant_robot.ops.recent_data_refresh import build_recent_data_refresh_pack, write_recent_data_refresh_pack
from quant_robot.ops.tushare_activation_gate import (
    build_tushare_activation_gate_pack,
    write_tushare_activation_gate_pack,
)

try:
    from scripts.run_iterative_observation_expansion import run_iterative_observation_expansion
    from scripts.run_observation_sufficiency import run_observation_sufficiency
    from scripts.run_post_refresh_replay import run_post_refresh_replay
    from scripts.run_recent_data_refresh import run_recent_data_refresh
except ModuleNotFoundError:  # pragma: no cover - exercised when this file is run directly
    from run_iterative_observation_expansion import run_iterative_observation_expansion
    from run_observation_sufficiency import run_observation_sufficiency
    from run_post_refresh_replay import run_post_refresh_replay
    from run_recent_data_refresh import run_recent_data_refresh


DEFAULT_PROFILE_OBSERVATION_PACK = Path("data/reports/profile_observation/profile_observation_pack.json")
DEFAULT_REPORT_DIR = Path("data/reports/tushare_activation_gate")


def run_tushare_activation_gate(
    profile_observation_pack: str | Path = DEFAULT_PROFILE_OBSERVATION_PACK,
    report_dir: str | Path = DEFAULT_REPORT_DIR,
    source: str = "tushare",
    market: str = "CN_ETF",
    execute: bool = False,
    max_rounds: int = 3,
    readiness: dict[str, Any] | None = None,
    recent_data_refresh_runner: Callable[..., dict[str, Any]] | None = None,
    post_refresh_replay_runner: Callable[..., dict[str, Any]] | None = None,
    observation_sufficiency_runner: Callable[..., dict[str, Any]] | None = None,
    iterative_observation_expansion_runner: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    profile_path = Path(profile_observation_pack)
    profile_pack = _read_json(profile_path)
    output_path = Path(report_dir)
    recent_report_dir = output_path / "recent_data_refresh"
    recent_output_dir = output_path / "processed"
    post_report_dir = output_path / "post_refresh_replay"
    sufficiency_dir = output_path / "observation_sufficiency"
    iterative_dir = output_path / "iterative_observation_expansion"
    source_name = source.strip().lower()
    readiness_pack = readiness if readiness is not None else _readiness_for_source(source_name)

    recent_pack = _build_readiness_probe_recent_pack(
        profile_pack,
        readiness=readiness_pack,
        source=source_name,
        market=market,
        output_dir=recent_output_dir,
        execute=execute,
    )
    write_recent_data_refresh_pack(recent_report_dir, recent_pack)
    post_pack: dict[str, Any] = {}
    sufficiency_pack: dict[str, Any] = {}
    iterative_pack: dict[str, Any] = {}
    chain_error: dict[str, Any] | None = None

    if _readiness_blocks(readiness_pack, source_name) or not execute:
        pack = build_tushare_activation_gate_pack(
            readiness=readiness_pack,
            source=source_name,
            market=market,
            execute=execute,
            recent_data_refresh=recent_pack,
        )
        write_tushare_activation_gate_pack(output_path, pack)
        return pack

    recent_runner = recent_data_refresh_runner or run_recent_data_refresh
    post_runner = post_refresh_replay_runner or run_post_refresh_replay
    sufficiency_runner = observation_sufficiency_runner or run_observation_sufficiency
    iterative_runner = iterative_observation_expansion_runner or run_iterative_observation_expansion
    try:
        recent_pack = recent_runner(
            profile_observation_pack=profile_path,
            source=source_name,
            market=market,
            output_dir=recent_output_dir,
            report_dir=recent_report_dir,
            execute=True,
            readiness=readiness_pack,
        )
        post_pack = post_runner(
            recent_data_refresh_pack=recent_report_dir / "recent_data_refresh_pack.json",
            report_dir=post_report_dir,
        )
        sufficiency_pack = sufficiency_runner(
            post_refresh_replay_pack=post_report_dir / "post_refresh_replay_pack.json",
            output_dir=sufficiency_dir,
        )
        if not _sufficiency_cleared(sufficiency_pack):
            iterative_pack = iterative_runner(
                observation_sufficiency_pack=sufficiency_dir / "observation_sufficiency_pack.json",
                profile_observation_pack=profile_path,
                report_dir=iterative_dir,
                source=source_name,
                market=market,
                max_rounds=max_rounds,
                execute=True,
            )
    except Exception as exc:  # pragma: no cover - exact exception depends on downstream workflow
        chain_error = {"stage": "tushare_activation_downstream", "error": str(exc)}

    pack = build_tushare_activation_gate_pack(
        readiness=readiness_pack,
        source=source_name,
        market=market,
        execute=execute,
        recent_data_refresh=recent_pack,
        post_refresh_replay=post_pack,
        observation_sufficiency=sufficiency_pack,
        iterative_observation_expansion=iterative_pack,
        chain_error=chain_error,
    )
    write_tushare_activation_gate_pack(output_path, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Phase 5.12 local-only Tushare activation gate.")
    parser.add_argument("--profile-observation-pack", default=str(DEFAULT_PROFILE_OBSERVATION_PACK))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--source", choices=["tushare", "tushare-fixture"], default="tushare")
    parser.add_argument("--market", default="CN_ETF")
    parser.add_argument("--max-rounds", default=3, type=int)
    parser.add_argument("--execute", action="store_true", help="Execute the paper-only local activation chain after readiness passes.")
    args = parser.parse_args()
    pack = run_tushare_activation_gate(
        profile_observation_pack=Path(args.profile_observation_pack),
        report_dir=Path(args.report_dir),
        source=args.source,
        market=args.market,
        max_rounds=args.max_rounds,
        execute=args.execute,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "mode": pack["mode"],
                "source": pack["source"],
                "decision": pack["decision"],
                "report_dir": str(Path(args.report_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _build_readiness_probe_recent_pack(
    profile_pack: dict[str, Any],
    *,
    readiness: dict[str, Any],
    source: str,
    market: str,
    output_dir: Path,
    execute: bool,
) -> dict[str, Any]:
    return build_recent_data_refresh_pack(
        profile_pack,
        readiness=readiness,
        execute=execute,
        source=source,
        market=market,
        output_dir=output_dir,
    )


def _readiness_for_source(source: str) -> dict[str, Any]:
    if source == "tushare-fixture":
        return {"source": source, "ready": True, "missing": []}
    return check_tushare_readiness()


def _readiness_blocks(readiness: dict[str, Any], source: str) -> bool:
    return source == "tushare" and not bool(readiness.get("ready", False))


def _sufficiency_cleared(pack: dict[str, Any]) -> bool:
    decision = pack.get("decision", {}) if isinstance(pack.get("decision"), dict) else {}
    return bool(decision.get("observation_sufficiency_cleared", False))


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


if __name__ == "__main__":
    main()
