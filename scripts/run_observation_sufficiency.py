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

from quant_robot.ops.observation_sufficiency import build_observation_sufficiency_pack, write_observation_sufficiency_pack


DEFAULT_POST_REFRESH_REPLAY_PACK = Path("data/reports/post_refresh_replay/post_refresh_replay_pack.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/observation_sufficiency")


def run_observation_sufficiency(
    post_refresh_replay_pack: str | Path = DEFAULT_POST_REFRESH_REPLAY_PACK,
    profile_observation_pack: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    minimum_relaxation_fills: int = 10,
) -> dict[str, Any]:
    post_refresh = _read_json(Path(post_refresh_replay_pack))
    observation_path = Path(profile_observation_pack) if profile_observation_pack else _default_observation_pack_path(post_refresh)
    observation = _read_optional_json(observation_path) if observation_path else {}
    pack = build_observation_sufficiency_pack(
        post_refresh,
        profile_observation_pack=observation,
        minimum_relaxation_fills=minimum_relaxation_fills,
    )
    write_observation_sufficiency_pack(output_dir, pack)
    return pack


def main() -> None:
    parser = argparse.ArgumentParser(description="Plan observation sample sufficiency after post-refresh replay.")
    parser.add_argument("--post-refresh-replay-pack", default=str(DEFAULT_POST_REFRESH_REPLAY_PACK))
    parser.add_argument("--profile-observation-pack")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--minimum-relaxation-fills", default=10, type=int)
    args = parser.parse_args()
    pack = run_observation_sufficiency(
        post_refresh_replay_pack=Path(args.post_refresh_replay_pack),
        profile_observation_pack=Path(args.profile_observation_pack) if args.profile_observation_pack else None,
        output_dir=Path(args.output_dir),
        minimum_relaxation_fills=args.minimum_relaxation_fills,
    )
    print(
        json.dumps(
            {
                "stage": pack["stage"],
                "status": pack["status"],
                "fills": pack["fills"],
                "recommendation": pack["recommendation"],
                "decision": pack["decision"],
                "output_dir": str(Path(args.output_dir)),
            },
            indent=2,
            sort_keys=True,
        )
    )


def _default_observation_pack_path(post_refresh: dict[str, Any]) -> Path | None:
    output_dir = post_refresh.get("profile_observation_output_dir")
    if not output_dir:
        return None
    return Path(str(output_dir)) / "profile_observation_pack.json"


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _read_optional_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return _read_json(path)


if __name__ == "__main__":
    main()
